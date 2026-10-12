PRAGMA foreign_keys = ON;

-- Sources -------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS documents(
    id INTEGER PRIMARY KEY,
    sha256 TEXT NOT NULL UNIQUE CHECK (length(sha256) = 64),
    content TEXT NOT NULL,
    ingested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_sources(
    document_id INTEGER NOT NULL REFERENCES documents(id),
    locator TEXT NOT NULL,
    PRIMARY KEY (document_id, locator)
);

CREATE TABLE IF NOT EXISTS evidence_spans(
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id),
    start_offset INTEGER NOT NULL CHECK (start_offset >= 0),
    end_offset INTEGER NOT NULL CHECK (end_offset > start_offset),
    UNIQUE (document_id, start_offset, end_offset)
);

CREATE TRIGGER IF NOT EXISTS evidence_within_document
BEFORE INSERT ON evidence_spans
WHEN NEW.end_offset > (SELECT length(content) FROM documents WHERE id = NEW.document_id)
BEGIN SELECT RAISE(ABORT, 'evidence span exceeds document length'); END;

-- Extraction ----------------------------------------------------------------

CREATE TABLE IF NOT EXISTS model_calls(
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id),
    extraction_version TEXT NOT NULL,
    model TEXT NOT NULL,
    reasoning_effort TEXT NOT NULL,
    started_at TEXT NOT NULL,
    elapsed_ms REAL NOT NULL CHECK (elapsed_ms >= 0),
    status TEXT NOT NULL CHECK (status IN ('succeeded', 'failed')),
    error TEXT,
    request_id TEXT,
    input_tokens INTEGER CHECK (input_tokens >= 0),
    cached_input_tokens INTEGER CHECK (cached_input_tokens <= input_tokens),
    output_tokens INTEGER CHECK (output_tokens >= 0),
    reasoning_tokens INTEGER CHECK (reasoning_tokens <= output_tokens),
    CHECK ((status = 'failed') = (error IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS extractions(
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id),
    version TEXT NOT NULL,
    producer TEXT NOT NULL,
    model_call_id INTEGER UNIQUE REFERENCES model_calls(id),
    output_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (document_id, version)
);

-- Identity ------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS patients(
    id INTEGER PRIMARY KEY,
    mrn TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    birth_date TEXT
);

CREATE TABLE IF NOT EXISTS encounters(
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    external_id TEXT NOT NULL,
    UNIQUE (patient_id, external_id),
    UNIQUE (id, patient_id)
);

CREATE TABLE IF NOT EXISTS assessments(
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    instrument TEXT NOT NULL,
    completed_on TEXT NOT NULL,
    form_key TEXT NOT NULL DEFAULT '',
    UNIQUE (patient_id, instrument, completed_on, form_key),
    UNIQUE (id, patient_id)
);

-- Claims: what one document asserts ----------------------------------------

CREATE TABLE IF NOT EXISTS assertions(
    id INTEGER PRIMARY KEY,
    extraction_id INTEGER NOT NULL REFERENCES extractions(id),
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    encounter_id INTEGER,
    assessment_id INTEGER,
    kind TEXT NOT NULL CHECK (kind IN (
        'encounter_detail', 'attendance', 'presence', 'break', 'correction',
        'charge', 'assessment_score', 'observation')),
    source_status TEXT NOT NULL CHECK (source_status IN ('final', 'draft')),
    authored_on TEXT NOT NULL,
    service_date TEXT,
    service_type TEXT CHECK (service_type IN (
        'individual_therapy', 'group_therapy', 'family_therapy', 'medication_management',
        'collateral_contact', 'care_coordination', 'other')),
    attendance TEXT CHECK (attendance IN (
        'attended', 'no_show', 'cancelled_by_patient', 'cancelled_by_clinic', 'patient_absent')),
    starts_at TEXT,
    ends_at TEXT,
    corrected_field TEXT CHECK (corrected_field IN ('presence_start', 'presence_end')),
    replaced_value TEXT,
    replacement_value TEXT,
    external_ref TEXT,
    score INTEGER CHECK (score >= 0),
    category TEXT CHECK (category IN (
        'symptom', 'functioning', 'safety', 'visit_reason', 'clinical_assessment')),
    reporter TEXT CHECK (reporter IN ('patient', 'clinician', 'collateral')),
    statement TEXT,
    FOREIGN KEY (encounter_id, patient_id) REFERENCES encounters(id, patient_id),
    FOREIGN KEY (assessment_id, patient_id) REFERENCES assessments(id, patient_id),
    CHECK (encounter_id IS NULL OR assessment_id IS NULL),
    CHECK (CASE kind
        WHEN 'encounter_detail' THEN encounter_id IS NOT NULL AND service_date IS NOT NULL AND service_type IS NOT NULL
        WHEN 'attendance' THEN encounter_id IS NOT NULL AND attendance IS NOT NULL
        WHEN 'presence' THEN encounter_id IS NOT NULL AND coalesce(starts_at < ends_at, 0)
        WHEN 'break' THEN encounter_id IS NOT NULL AND coalesce(starts_at < ends_at, 0)
        WHEN 'correction' THEN encounter_id IS NOT NULL AND corrected_field IS NOT NULL
            AND coalesce(replaced_value <> replacement_value, 0)
        WHEN 'charge' THEN encounter_id IS NOT NULL AND external_ref IS NOT NULL
        WHEN 'assessment_score' THEN assessment_id IS NOT NULL AND score IS NOT NULL
        WHEN 'observation' THEN category IS NOT NULL AND reporter IS NOT NULL AND statement IS NOT NULL
    END)
);

CREATE INDEX IF NOT EXISTS idx_assertions_encounter ON assertions(encounter_id);
CREATE INDEX IF NOT EXISTS idx_assertions_patient_kind ON assertions(patient_id, kind);

CREATE TABLE IF NOT EXISTS assertion_evidence(
    assertion_id INTEGER NOT NULL REFERENCES assertions(id),
    evidence_id INTEGER NOT NULL REFERENCES evidence_spans(id),
    PRIMARY KEY (assertion_id, evidence_id)
);

CREATE TRIGGER IF NOT EXISTS assertion_evidence_same_document
BEFORE INSERT ON assertion_evidence
WHEN (SELECT document_id FROM evidence_spans WHERE id = NEW.evidence_id) IS NOT
     (SELECT x.document_id FROM assertions a JOIN extractions x ON x.id = a.extraction_id WHERE a.id = NEW.assertion_id)
BEGIN SELECT RAISE(ABORT, 'evidence must come from the asserting document'); END;

CREATE TABLE IF NOT EXISTS plans(
    id INTEGER PRIMARY KEY,
    extraction_id INTEGER NOT NULL REFERENCES extractions(id),
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    effective_start TEXT NOT NULL,
    effective_end TEXT NOT NULL CHECK (effective_end >= effective_start),
    min_therapy_days INTEGER NOT NULL CHECK (min_therapy_days BETWEEN 0 AND 7),
    min_therapy_minutes INTEGER NOT NULL CHECK (min_therapy_minutes >= 0)
);

CREATE TABLE IF NOT EXISTS plan_services(
    plan_id INTEGER NOT NULL REFERENCES plans(id),
    service_type TEXT NOT NULL CHECK (service_type IN (
        'individual_therapy', 'group_therapy', 'family_therapy', 'medication_management',
        'collateral_contact', 'care_coordination', 'other')),
    PRIMARY KEY (plan_id, service_type)
);

CREATE TABLE IF NOT EXISTS plan_evidence(
    plan_id INTEGER NOT NULL REFERENCES plans(id),
    evidence_id INTEGER NOT NULL REFERENCES evidence_spans(id),
    PRIMARY KEY (plan_id, evidence_id)
);

CREATE TRIGGER IF NOT EXISTS plan_evidence_same_document
BEFORE INSERT ON plan_evidence
WHEN (SELECT document_id FROM evidence_spans WHERE id = NEW.evidence_id) IS NOT
     (SELECT x.document_id FROM plans p JOIN extractions x ON x.id = p.extraction_id WHERE p.id = NEW.plan_id)
BEGIN SELECT RAISE(ABORT, 'evidence must come from the planning document'); END;

-- Reconciliation: versioned decisions over claims ---------------------------

CREATE TABLE IF NOT EXISTS reconciliation_runs(
    id INTEGER PRIMARY KEY,
    extraction_version TEXT NOT NULL,
    through_extraction_id INTEGER NOT NULL REFERENCES extractions(id),
    policy_version TEXT NOT NULL,
    elapsed_ms REAL NOT NULL CHECK (elapsed_ms >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS encounter_resolutions(
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES reconciliation_runs(id),
    encounter_id INTEGER NOT NULL REFERENCES encounters(id),
    detail_status TEXT NOT NULL CHECK (detail_status IN ('established', 'disputed', 'unknown')),
    service_date TEXT,
    service_type TEXT,
    attendance_status TEXT NOT NULL CHECK (attendance_status IN ('established', 'disputed', 'unknown')),
    attendance TEXT,
    duration_status TEXT NOT NULL CHECK (duration_status IN (
        'established', 'corrected', 'disputed', 'unknown', 'not_applicable')),
    UNIQUE (run_id, encounter_id),
    CHECK ((detail_status = 'established') = (service_date IS NOT NULL AND service_type IS NOT NULL)),
    CHECK ((attendance_status = 'established') = (attendance IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS duration_alternatives(
    id INTEGER PRIMARY KEY,
    resolution_id INTEGER NOT NULL REFERENCES encounter_resolutions(id),
    minutes INTEGER NOT NULL CHECK (minutes >= 0),
    derivation TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alternative_assertions(
    alternative_id INTEGER NOT NULL REFERENCES duration_alternatives(id),
    assertion_id INTEGER NOT NULL REFERENCES assertions(id),
    PRIMARY KEY (alternative_id, assertion_id)
);

CREATE TABLE IF NOT EXISTS resolution_members(
    resolution_id INTEGER NOT NULL REFERENCES encounter_resolutions(id),
    assertion_id INTEGER NOT NULL REFERENCES assertions(id),
    role TEXT NOT NULL CHECK (role IN (
        'accepted', 'corrected', 'disputed', 'applied_correction', 'unmatched_correction',
        'rejected', 'context')),
    note TEXT,
    PRIMARY KEY (resolution_id, assertion_id)
);

CREATE TRIGGER IF NOT EXISTS resolution_member_same_encounter
BEFORE INSERT ON resolution_members
WHEN (SELECT encounter_id FROM assertions WHERE id = NEW.assertion_id) IS NOT
     (SELECT encounter_id FROM encounter_resolutions WHERE id = NEW.resolution_id)
BEGIN SELECT RAISE(ABORT, 'resolution member belongs to another encounter'); END;

-- Answers -------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS calculation_runs(
    id INTEGER PRIMARY KEY,
    reconciliation_run_id INTEGER NOT NULL REFERENCES reconciliation_runs(id),
    query TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    result_json TEXT NOT NULL,
    elapsed_ms REAL NOT NULL CHECK (elapsed_ms >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- A later review of a sealed claim. The assertion row is not updated.
CREATE TABLE IF NOT EXISTS assertion_reviews(
    id INTEGER PRIMARY KEY,
    assertion_id INTEGER NOT NULL REFERENCES assertions(id),
    field TEXT NOT NULL CHECK (field = 'reporter'),
    previous_value TEXT NOT NULL,
    replacement_value TEXT NOT NULL CHECK (replacement_value IN ('patient', 'clinician', 'collateral')),
    basis TEXT NOT NULL,
    reviewer TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (previous_value <> replacement_value)
);

-- Sealed extractions and reconciliations reject additional child rows.
CREATE TABLE IF NOT EXISTS extraction_seals(
    extraction_id INTEGER PRIMARY KEY REFERENCES extractions(id)
);
CREATE TRIGGER IF NOT EXISTS seal_requires_evidence
BEFORE INSERT ON extraction_seals
WHEN EXISTS (SELECT 1 FROM assertions a WHERE a.extraction_id=NEW.extraction_id
             AND NOT EXISTS (SELECT 1 FROM assertion_evidence e WHERE e.assertion_id=a.id))
  OR EXISTS (SELECT 1 FROM plans p WHERE p.extraction_id=NEW.extraction_id
             AND (NOT EXISTS (SELECT 1 FROM plan_evidence e WHERE e.plan_id=p.id)
               OR NOT EXISTS (SELECT 1 FROM plan_services s WHERE s.plan_id=p.id)))
BEGIN SELECT RAISE(ABORT, 'finalization requires evidence and plan services'); END;

CREATE TRIGGER IF NOT EXISTS assertions_sealed BEFORE INSERT ON assertions
WHEN EXISTS (SELECT 1 FROM extraction_seals WHERE extraction_id=NEW.extraction_id)
BEGIN SELECT RAISE(ABORT, 'extraction is sealed'); END;

CREATE TRIGGER IF NOT EXISTS plans_sealed BEFORE INSERT ON plans
WHEN EXISTS (SELECT 1 FROM extraction_seals WHERE extraction_id=NEW.extraction_id)
BEGIN SELECT RAISE(ABORT, 'extraction is sealed'); END;

CREATE TRIGGER IF NOT EXISTS assertion_evidence_sealed BEFORE INSERT ON assertion_evidence
WHEN EXISTS (SELECT 1 FROM extraction_seals WHERE extraction_id=(SELECT extraction_id FROM assertions WHERE id=NEW.assertion_id))
BEGIN SELECT RAISE(ABORT, 'extraction is sealed'); END;

CREATE TRIGGER IF NOT EXISTS plan_evidence_sealed BEFORE INSERT ON plan_evidence
WHEN EXISTS (SELECT 1 FROM extraction_seals WHERE extraction_id=(SELECT extraction_id FROM plans WHERE id=NEW.plan_id))
BEGIN SELECT RAISE(ABORT, 'extraction is sealed'); END;

CREATE TRIGGER IF NOT EXISTS plan_services_sealed BEFORE INSERT ON plan_services
WHEN EXISTS (SELECT 1 FROM extraction_seals WHERE extraction_id=(SELECT extraction_id FROM plans WHERE id=NEW.plan_id))
BEGIN SELECT RAISE(ABORT, 'extraction is sealed'); END;

CREATE TABLE IF NOT EXISTS reconciliation_seals(run_id INTEGER PRIMARY KEY REFERENCES reconciliation_runs(id));

CREATE TRIGGER IF NOT EXISTS encounter_resolutions_sealed BEFORE INSERT ON encounter_resolutions
WHEN EXISTS (SELECT 1 FROM reconciliation_seals WHERE run_id=NEW.run_id)
BEGIN SELECT RAISE(ABORT, 'reconciliation is sealed'); END;

CREATE TRIGGER IF NOT EXISTS resolution_members_sealed BEFORE INSERT ON resolution_members
WHEN EXISTS (SELECT 1 FROM reconciliation_seals WHERE run_id=(SELECT run_id FROM encounter_resolutions WHERE id=NEW.resolution_id))
BEGIN SELECT RAISE(ABORT, 'reconciliation is sealed'); END;

CREATE TRIGGER IF NOT EXISTS duration_alternatives_sealed BEFORE INSERT ON duration_alternatives
WHEN EXISTS (SELECT 1 FROM reconciliation_seals WHERE run_id=(SELECT run_id FROM encounter_resolutions WHERE id=NEW.resolution_id))
BEGIN SELECT RAISE(ABORT, 'reconciliation is sealed'); END;

CREATE TRIGGER IF NOT EXISTS alternative_assertions_sealed BEFORE INSERT ON alternative_assertions
WHEN EXISTS (SELECT 1 FROM reconciliation_seals WHERE run_id=(SELECT r.run_id FROM duration_alternatives a JOIN encounter_resolutions r ON r.id=a.resolution_id WHERE a.id=NEW.alternative_id))
BEGIN SELECT RAISE(ABORT, 'reconciliation is sealed'); END;
