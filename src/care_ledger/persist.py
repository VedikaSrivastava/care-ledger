from __future__ import annotations

import re
import sqlite3
from datetime import date, datetime, time
from pathlib import Path

from .models import Claim, EncounterSection, ExtractionEnvelope, Patient


class EvidenceError(ValueError):
    pass


class CompletenessError(ValueError):
    pass


class AlreadyExtracted(RuntimeError):
    def __init__(self, extraction_id: int):
        super().__init__(f"document already extracted as {extraction_id}")
        self.extraction_id = extraction_id


def _quote_problem(content: str, quote: str) -> str | None:
    start = content.find(quote)
    if start < 0:
        return f"not found verbatim: {quote!r}"
    if content.find(quote, start + 1) >= 0:
        return f"occurs more than once: {quote!r}"
    return None


def _find_all(content: str, quote: str) -> list[int]:
    starts: list[int] = []
    pos = 0
    while True:
        i = content.find(quote, pos)
        if i < 0:
            return starts
        starts.append(i)
        pos = i + 1


def _expand_occurrence(content: str, start: int, length: int) -> str:
    """Grow a quote by whole lines (then characters) until it occurs exactly once."""
    end = start + length
    while True:
        snippet = content[start:end]
        if _quote_problem(content, snippet) is None:
            return snippet
        if start > 0:
            prev_nl = content.rfind("\n", 0, start)
            line_start = 0 if prev_nl < 0 else prev_nl + 1
            if line_start < start:
                start = line_start
            elif prev_nl < 0:
                start = 0
            else:
                prior_nl = content.rfind("\n", 0, prev_nl)
                start = 0 if prior_nl < 0 else prior_nl + 1
        elif end < len(content):
            next_nl = content.find("\n", end)
            end = len(content) if next_nl < 0 else max(end + 1, next_nl)
        else:
            return snippet


def _section_region(content: str, section: EncounterSection) -> tuple[int, int] | None:
    """Locate the document span owned by this encounter section."""
    starts = _find_all(content, section.encounter_id)
    if len(starts) != 1:
        starts = []
        for quote in section.evidence_quotes:
            hits = _find_all(content, quote)
            if len(hits) == 1:
                starts = hits
                break
    if len(starts) != 1:
        return None
    start = starts[0]
    later = [m.start() for m in re.finditer(r"\bHG-E\d+\b", content) if m.start() > start]
    return start, (later[0] if later else len(content))


def _resolve_quote(content: str, quote: str, region: tuple[int, int] | None) -> str:
    if _quote_problem(content, quote) is None:
        return quote
    hits = _find_all(content, quote)
    if not hits:
        return quote
    if len(hits) == 1:
        return _expand_occurrence(content, hits[0], len(quote))
    if region is None:
        return quote
    lo, hi = region
    in_region = [h for h in hits if lo <= h < hi]
    if len(in_region) != 1:
        return quote
    return _expand_occurrence(content, in_region[0], len(quote))


def _fix_quotes(claim: Claim, content: str, region: tuple[int, int] | None) -> Claim:
    return claim.model_copy(update={
        "evidence_quotes": [_resolve_quote(content, q, region) for q in claim.evidence_quotes],
    })


def disambiguate_evidence_quotes(content: str, envelope: ExtractionEnvelope) -> ExtractionEnvelope:
    """When a quote repeats under different encounter headings, bind it to its section and expand."""
    encounters = []
    for section in envelope.encounters:
        region = _section_region(content, section)
        attendance = _fix_quotes(section.attendance, content, region) if section.attendance else None
        encounters.append(section.model_copy(update={
            "evidence_quotes": [_resolve_quote(content, q, region) for q in section.evidence_quotes],
            "attendance": attendance,
            "patient_presence": [_fix_quotes(i, content, region) for i in section.patient_presence],
            "breaks": [_fix_quotes(i, content, region) for i in section.breaks],
            "charges": [_fix_quotes(c, content, region) for c in section.charges],
        }))
    return envelope.model_copy(update={
        "encounters": encounters,
        "corrections": [_fix_quotes(c, content, None) for c in envelope.corrections],
        "assessments": [_fix_quotes(a, content, None) for a in envelope.assessments],
        "observations": [_fix_quotes(o, content, None) for o in envelope.observations],
        "plans": [_fix_quotes(p, content, None) for p in envelope.plans],
    })


def locate_quote(content: str, quote: str) -> tuple[int, int]:
    if problem := _quote_problem(content, quote):
        raise EvidenceError(problem)
    start = content.find(quote)
    return start, start + len(quote)


def validate_evidence(content: str, envelope: ExtractionEnvelope) -> None:
    problems = sorted({p for claim in envelope.claims() for q in claim.evidence_quotes
                       if (p := _quote_problem(content, q))})
    if problems:
        raise EvidenceError("; ".join(problems))


_CLOCK_SPAN = r"(?<![\d:])([01]?\d|2[0-3]):([0-5]\d)\s*(?:–|-|to)\s*([01]?\d|2[0-3]):([0-5]\d)"
_STATED_BREAKS = (
    re.compile(rf"(?i)(?:nontherapeutic\s+)?(?:group\s+)?\bbreaks?\b[:\s,]*(?:from\s+)?{_CLOCK_SPAN}"),
    re.compile(rf"(?i)(?:connection was lost|disconnected|disconnection)\b.{{0,40}}{_CLOCK_SPAN}"),
)


def _hhmm(hour: str, minute: str) -> str:
    return f"{int(hour):02d}:{minute}"


def stated_break_clocks(content: str) -> list[tuple[str, str]]:
    """Timed breaks or lost-connection intervals the document itself states."""
    found: list[tuple[str, str]] = []
    for pattern in _STATED_BREAKS:
        found.extend((_hhmm(h1, m1), _hhmm(h2, m2)) for h1, m1, h2, m2 in pattern.findall(content))
    return found


def omitted_stated_breaks(content: str, envelope: ExtractionEnvelope) -> list[str]:
    claimed = [
        (interval.start.isoformat(timespec="minutes"), interval.end.isoformat(timespec="minutes"))
        for section in envelope.encounters
        for interval in section.breaks
    ]
    remaining = list(claimed)
    omitted = []
    for pair in stated_break_clocks(content):
        if pair in remaining:
            remaining.remove(pair)
        else:
            omitted.append(f"{pair[0]}-{pair[1]}")
    return omitted


def validate_stated_breaks(content: str, envelope: ExtractionEnvelope) -> None:
    omitted = omitted_stated_breaks(content, envelope)
    if omitted:
        raise CompletenessError(
            "document states timed nontherapeutic interval(s) that were not recorded as breaks: "
            + ", ".join(omitted)
        )


def _at(day: date, clock: time) -> str:
    return datetime.combine(day, clock).isoformat(timespec="minutes")


class _Writer:
    """Writes one extraction's claims; the caller owns the transaction."""

    def __init__(self, db: sqlite3.Connection, document_id: int, extraction_id: int, patient_id: int):
        self.db = db
        self.document_id = document_id
        self.extraction_id = extraction_id
        self.patient_id = patient_id
        self.content = db.execute("SELECT content FROM documents WHERE id = ?", (document_id,)).fetchone()[0]

    def evidence(self, claim: Claim) -> list[int]:
        ids = []
        for quote in claim.evidence_quotes:
            start, end = locate_quote(self.content, quote)
            self.db.execute(
                "INSERT OR IGNORE INTO evidence_spans(document_id, start_offset, end_offset) VALUES (?, ?, ?)",
                (self.document_id, start, end),
            )
            ids.append(self.db.execute(
                "SELECT id FROM evidence_spans WHERE document_id = ? AND start_offset = ? AND end_offset = ?",
                (self.document_id, start, end),
            ).fetchone()[0])
        return ids

    def encounter(self, external_id: str) -> int:
        self.db.execute(
            "INSERT OR IGNORE INTO encounters(patient_id, external_id) VALUES (?, ?)",
            (self.patient_id, external_id),
        )
        return self.db.execute(
            "SELECT id FROM encounters WHERE patient_id = ? AND external_id = ?", (self.patient_id, external_id)
        ).fetchone()[0]

    def assessment(self, instrument: str, completed_on: date, form_id: str | None = None) -> int:
        # Same source form id merges (including imports). No form id: do not merge across documents.
        form_key = form_id if form_id else f"anon:{self.extraction_id}"
        self.db.execute(
            "INSERT OR IGNORE INTO assessments(patient_id, instrument, completed_on, form_key) VALUES (?, ?, ?, ?)",
            (self.patient_id, instrument, completed_on.isoformat(), form_key),
        )
        return self.db.execute(
            "SELECT id FROM assessments WHERE patient_id = ? AND instrument = ? AND completed_on = ? AND form_key = ?",
            (self.patient_id, instrument, completed_on.isoformat(), form_key),
        ).fetchone()[0]

    def assertion(self, claim: Claim, kind: str, source_status: str, authored_on: date, **values) -> None:
        columns = {
            "extraction_id": self.extraction_id,
            "patient_id": self.patient_id,
            "kind": kind,
            "source_status": source_status,
            "authored_on": authored_on.isoformat(),
            **values,
        }
        assertion_id = self.db.execute(
            f"INSERT INTO assertions({', '.join(columns)}) VALUES ({', '.join('?' * len(columns))})",
            tuple(columns.values()),
        ).lastrowid
        self.db.executemany(
            "INSERT INTO assertion_evidence(assertion_id, evidence_id) VALUES (?, ?)",
            [(assertion_id, evidence_id) for evidence_id in self.evidence(claim)],
        )


def _patient(db: sqlite3.Connection, patient: Patient) -> int:
    birth_date = patient.birth_date.isoformat() if patient.birth_date else None
    row = db.execute("SELECT id, name, birth_date FROM patients WHERE mrn = ?", (patient.mrn,)).fetchone()
    if row is None:
        return db.execute(
            "INSERT INTO patients(mrn, name, birth_date) VALUES (?, ?, ?)", (patient.mrn, patient.name, birth_date)
        ).lastrowid
    if row["name"] != patient.name or (birth_date and row["birth_date"] and row["birth_date"] != birth_date):
        raise ValueError(
            f"patient identity conflict for MRN {patient.mrn}: "
            f"{row['name']}/{row['birth_date']} versus {patient.name}/{birth_date}"
        )
    return row["id"]


def persist_extraction(
    db: sqlite3.Connection,
    document_id: int,
    envelope: ExtractionEnvelope,
    *,
    version: str,
    producer: str,
    model_call_id: int | None = None,
) -> int:
    existing = db.execute(
        "SELECT id FROM extractions WHERE document_id = ? AND version = ?", (document_id, version)
    ).fetchone()
    if existing:
        raise AlreadyExtracted(existing[0])
    content = db.execute("SELECT content FROM documents WHERE id = ?", (document_id,)).fetchone()[0]
    envelope = disambiguate_evidence_quotes(content, envelope)
    validate_evidence(content, envelope)
    validate_stated_breaks(content, envelope)
    try:
        extraction_id = db.execute(
            "INSERT INTO extractions(document_id, version, producer, model_call_id, output_json) VALUES (?, ?, ?, ?, ?)",
            (document_id, version, producer, model_call_id, envelope.model_dump_json()),
        ).lastrowid
    except sqlite3.IntegrityError as exc:
        row = db.execute(
            "SELECT id FROM extractions WHERE document_id = ? AND version = ?", (document_id, version)
        ).fetchone()
        if row:
            raise AlreadyExtracted(row[0]) from exc
        raise
    w = _Writer(db, document_id, extraction_id, _patient(db, envelope.patient))

    for s in envelope.encounters:
        encounter_id = w.encounter(s.encounter_id)
        common = {"source_status": s.source_status, "authored_on": s.authored_on, "encounter_id": encounter_id}
        w.assertion(s, "encounter_detail", service_date=s.service_date.isoformat(), service_type=s.service_type, **common)
        if s.attendance:
            w.assertion(s.attendance, "attendance", attendance=s.attendance.status, **common)
        for i in s.patient_presence:
            w.assertion(i, "presence", starts_at=_at(s.service_date, i.start), ends_at=_at(s.service_date, i.end), **common)
        for i in s.breaks:
            w.assertion(i, "break", starts_at=_at(s.service_date, i.start), ends_at=_at(s.service_date, i.end), **common)
        for c in s.charges:
            w.assertion(c, "charge", external_ref=c.charge_id, **common)

    for c in envelope.corrections:
        w.assertion(
            c, "correction", c.source_status, c.authored_on,
            encounter_id=w.encounter(c.encounter_id),
            corrected_field=c.field,
            replaced_value=_at(c.service_date, c.replaced_time),
            replacement_value=_at(c.service_date, c.replacement_time),
        )

    for a in envelope.assessments:
        w.assertion(
            a, "assessment_score", a.source_status, a.authored_on,
            assessment_id=w.assessment(a.instrument, a.completed_on, a.form_id),
            score=a.score, external_ref=a.form_id,
        )

    for o in envelope.observations:
        w.assertion(
            o, "observation", o.source_status, o.authored_on,
            encounter_id=w.encounter(o.encounter_id) if o.encounter_id else None,
            category=o.category, reporter=o.reporter, statement=o.statement,
        )

    for p in envelope.plans:
        plan_id = db.execute(
            "INSERT INTO plans(extraction_id, patient_id, effective_start, effective_end, min_therapy_days, min_therapy_minutes) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (extraction_id, w.patient_id, p.effective_start.isoformat(), p.effective_end.isoformat(),
             p.min_therapy_days_per_week, p.min_therapy_minutes_per_week),
        ).lastrowid
        db.executemany("INSERT INTO plan_services(plan_id, service_type) VALUES (?, ?)",
                       [(plan_id, t) for t in set(p.eligible_service_types)])
        db.executemany("INSERT INTO plan_evidence(plan_id, evidence_id) VALUES (?, ?)",
                       [(plan_id, e) for e in w.evidence(p)])
    db.execute("INSERT INTO extraction_seals(extraction_id) VALUES (?)", (extraction_id,))
    return extraction_id


def fixture_envelope(patient: Patient, claims: dict) -> ExtractionEnvelope:
    return ExtractionEnvelope.model_validate({
        "patient": patient.model_dump(mode="json"),
        "encounters": [], "corrections": [], "assessments": [], "observations": [], "plans": [],
        **claims,
    })


def persist_fixtures(
    db: sqlite3.Connection,
    documents_dir: Path,
    fixtures: dict[str, dict],
    *,
    patient: Patient,
    version: str,
    producer: str = "fixture",
) -> tuple[int, int]:
    """Persist hand-authored fixture claims through the same writer as live extraction."""
    persisted = skipped = 0
    for name, claims in fixtures.items():
        locator = (Path(documents_dir) / name).as_posix()
        row = db.execute("SELECT document_id FROM document_sources WHERE locator = ?", (locator,)).fetchone()
        if row is None:
            raise LookupError(f"{name} is not ingested (expected locator {locator})")
        envelope = fixture_envelope(patient, claims)
        try:
            with db:
                persist_extraction(db, row[0], envelope, version=version, producer=producer)
            persisted += 1
        except AlreadyExtracted:
            skipped += 1
    return persisted, skipped
