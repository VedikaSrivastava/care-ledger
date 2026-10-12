import json
import shutil
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from care_ledger.db import ingest_directory, open_db
from care_ledger.models import Interval, Patient
from care_ledger.persist import AlreadyExtracted, EvidenceError, persist_extraction, persist_fixtures, fixture_envelope
from care_ledger.queries import StaleAbstraction, run_query
from care_ledger.reconcile import EncounterClaim, resolve, reconcile

DOCUMENTS = Path(__file__).parents[1] / "documents"
GOLD = json.loads((Path(__file__).parent / "fixtures" / "fixture_extractions.json").read_text(encoding="utf-8"))
PATIENT = Patient(mrn="HG-M042", name="Rowan Mercer", birth_date=date(1991, 4, 12))
VERSION = "fixture"
WINDOW = {"patient": "HG-M042", "start": date(2026, 1, 5), "end": date(2026, 1, 30)}


def envelope(claims: dict):
    return fixture_envelope(PATIENT, claims)


def document_id(db, name: str) -> int:
    return db.execute(
        "SELECT document_id FROM document_sources WHERE locator = ?", ((DOCUMENTS / name).as_posix(),)
    ).fetchone()[0]


def load_fixtures(db, names=None) -> int:
    persist_fixtures(
        db, DOCUMENTS, {n: GOLD[n] for n in (names or GOLD)},
        patient=PATIENT, version=VERSION,
    )
    return reconcile(db, VERSION)


def fresh_db(path: Path, names=None):
    db = open_db(path)
    ingest_directory(db, DOCUMENTS)
    load_fixtures(db, names)
    return db


@pytest.fixture
def db(tmp_path):
    db = fresh_db(tmp_path / "ledger.sqlite")
    yield db
    db.close()


def query(db, name, **params):
    return run_query(db, VERSION, name, **params)


def claim(id, kind, extraction_id=1, authored_on="2026-01-19", status="final", **values):
    return EncounterClaim(id, extraction_id, kind, status, authored_on, **values)


def at(clock: str) -> str:
    return f"2026-01-19T{clock}"


# --- end-to-end on the fixture extraction -----------------------------------

def test_fixture_extraction_covers_every_document():
    assert set(GOLD) == {p.name for p in DOCUMENTS.glob("*.txt")}


def test_attendance_counts_encounters_not_documents(db):
    a = query(db, "attendance", **WINDOW)
    assert a["sessions"] == {"min": 12, "max": 12}
    assert {t: v["sessions"]["min"] for t, v in a["by_service_type"].items()} == {
        "family_therapy": 2, "group_therapy": 5, "individual_therapy": 5}
    assert a["distinct_therapy_days"] == {"min": 11, "max": 11}
    assert {r["encounter"] for r in a["excluded"]} == {
        "HG-E103", "HG-E106", "HG-E108", "HG-E109", "HG-E114", "HG-E116", "HG-E117", "HG-E120"}
    assert a["undetermined"] == [] and a["unplaced"] == []
    family = next(r for r in a["included"] if r["encounter"] == "HG-E104")
    assert len(family["documents"]) == 3 and family["minutes"] == {"min": 45, "max": 45}


def test_minutes_keep_the_unresolved_duration(db):
    m = query(db, "minutes", **WINDOW)
    assert m["minutes"] == {"min": 585, "max": 595}
    assert [w["minutes"] for w in m["weeks"]] == [
        {"min": 140, "max": 140}, {"min": 120, "max": 120}, {"min": 180, "max": 180}, {"min": 145, "max": 155}]
    assert m["weeks"][-1]["partial_week"] is True
    assert [r["encounter"] for r in m["unresolved"]] == ["HG-E115"]


def test_compliance_propagates_uncertainty_only_where_it_matters(db):
    c = query(db, "compliance", **WINDOW)["patients"][0]
    assert [w["status"] for w in c["weeks"]] == ["not_met", "not_met", "met", "cannot_determine"]
    assert c["weeks"][-1]["depends_on"] == ["HG-E115"]
    assert c["consecutive_weeks_below_goal"]["definite"] == [["2026-01-05", "2026-01-12"]]


def test_collection_wide_compliance(db):
    c = query(db, "compliance", start=WINDOW["start"], end=WINDOW["end"])
    assert c["patients_with_consecutive_weeks_below_goal"]["definite"] == ["HG-M042"]


def test_correction_survives_a_later_received_copy(db):
    jan19 = query(db, "days", patient="HG-M042", dates=[date(2026, 1, 19)])["days"][0]
    assert (jan19["therapy_contacts"], jan19["minutes"]) == ({"min": 2, "max": 2}, {"min": 90, "max": 90})
    group = next(e for e in jan19["encounters"] if e["encounter"] == "HG-E110")
    assert group["duration_status"] == "corrected"
    assert group["derivations"] == ["10:00-11:15 (75) - breaks 10:45-11:00 (15) = 60 min"]
    roles = {(c["kind"], c["evidence"][0]["document"][:7]): c["role"] for c in group["claims"]}
    assert roles[("presence", "BH-D102")] == roles[("presence", "BH-D104")] == "corrected"
    assert roles[("correction", "BH-D103")] == "applied_correction"


def test_telehealth_reconnect_is_one_encounter(db):
    jan21 = query(db, "days", patient="HG-M042", dates=[date(2026, 1, 21)])["days"][0]
    assert (jan21["therapy_contacts"], jan21["minutes"]) == ({"min": 1, "max": 1}, {"min": 45, "max": 45})


def test_draft_and_charge_do_not_establish_care(db):
    e = query(db, "encounter", patient="HG-M042", encounter="HG-E116")
    assert e["status"] == "excluded" and e["attendance"] == "no_show"
    roles = {c["kind"]: c["role"] for c in e["claims"] if c["role"] in ("rejected", "context")}
    assert roles == {"attendance": "rejected", "encounter_detail": "rejected", "charge": "context"}


def test_partial_family_attendance_counts_patient_present_minutes(db):
    assert query(db, "encounter", patient="HG-M042", encounter="HG-E119")["minutes"] == {"min": 30, "max": 30}


def test_imported_assessment_is_not_a_new_assessment(db):
    p = query(db, "progress", **WINDOW)
    assert [(a["completed_on"], a["score"]) for a in p["assessments"]] == [
        ("2026-01-05", 18), ("2026-01-16", 14), ("2026-01-30", 10)]
    assert p["assessments"][1]["source_documents"] == 2
    assert p["trend"]["PHQ-9"]["change_first_to_last"] == -8
    assert any(o["category"] == "visit_reason" and o["encounter"] == "HG-E111" for o in p["observations"])


# --- persistence, duplicates, restart --------------------------------------

def test_duplicate_copy_changes_nothing(db, tmp_path):
    before = query(db, "minutes", **WINDOW)["minutes"]
    copies = tmp_path / "copies"
    copies.mkdir()
    shutil.copy(DOCUMENTS / "BH-D103_attendance_correction_2026-01-20.txt", copies / "renamed_copy.txt")
    result = ingest_directory(db, copies)
    assert (result.added, result.duplicates) == (0, 1)
    assert query(db, "minutes", **WINDOW)["minutes"] == before


def test_results_do_not_depend_on_document_order(tmp_path):
    reversed_db = fresh_db(tmp_path / "reversed.sqlite", names=list(reversed(GOLD)))
    assert query(reversed_db, "minutes", **WINDOW)["minutes"] == {"min": 585, "max": 595}
    assert [w["status"] for w in query(reversed_db, "compliance", **WINDOW)["patients"][0]["weeks"]] == [
        "not_met", "not_met", "met", "cannot_determine"]


def test_restart_reuses_saved_abstraction(tmp_path):
    path = tmp_path / "ledger.sqlite"
    fresh_db(path).close()
    db = open_db(path)
    assert query(db, "attendance", **WINDOW)["sessions"] == {"min": 12, "max": 12}
    assert db.execute("SELECT count(*) FROM reconciliation_runs").fetchone()[0] == 1


def test_new_extraction_makes_abstraction_stale(db, tmp_path):
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    (incoming / "new.txt").write_text("Administrative note without clinical content.", encoding="utf-8")
    ingest_directory(db, incoming)
    new_id = db.execute("SELECT document_id FROM document_sources WHERE locator LIKE '%/new.txt'").fetchone()[0]
    with db:
        persist_extraction(db, new_id, envelope({}), version=VERSION, producer="fixture")
    with pytest.raises(StaleAbstraction):
        query(db, "minutes", **WINDOW)
    reconcile(db, VERSION)
    assert query(db, "minutes", **WINDOW)["minutes"] == {"min": 585, "max": 595}


def test_reload_fixtures_does_not_duplicate_extractions(db):
    before = db.execute("SELECT count(*) FROM extractions").fetchone()[0]
    persist_fixtures(db, DOCUMENTS, GOLD, patient=PATIENT, version=VERSION)
    assert db.execute("SELECT count(*) FROM extractions").fetchone()[0] == before
    assert query(db, "minutes", **WINDOW)["minutes"] == {"min": 585, "max": 595}


def test_second_persist_of_same_document_is_rejected(db):
    doc = document_id(db, "BH-D105_individual_2026-01-19.txt")
    with pytest.raises(AlreadyExtracted):
        with db:
            persist_extraction(db, doc, envelope({}), version=VERSION, producer="fixture")


@pytest.mark.parametrize("clock", ["10:45:00-11:00", "11:00:00.000000000Z", "10:45Z", "10:45:30", "9:00"])
def test_clock_times_reject_ranges_offsets_and_precision_loss(clock):
    with pytest.raises(ValueError):
        Interval(start=clock, end="12:00", evidence_quotes=["quoted"])


def test_local_clock_round_trip():
    interval = Interval(start="10:45", end="11:00", evidence_quotes=["quoted"])
    assert Interval.model_validate_json(interval.model_dump_json()) == interval


def test_unlocatable_evidence_is_rejected_atomically(db):
    doc = document_id(db, "BH-D105_individual_2026-01-19.txt")
    bad = envelope({"observations": [{
        "encounter_id": None, "category": "symptom", "reporter": "patient", "statement": "x",
        "source_status": "final", "authored_on": "2026-01-19", "evidence_quotes": ["not in the document"]}]})
    before = db.execute("SELECT count(*) FROM extractions").fetchone()[0]
    with pytest.raises(EvidenceError):
        with db:
            persist_extraction(db, doc, bad, version="other", producer="test")
    assert db.execute("SELECT count(*) FROM extractions").fetchone()[0] == before


# --- database invariants ----------------------------------------------------

def test_tables_are_append_only(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE assertions SET score = 0")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("DELETE FROM encounter_resolutions")


def test_assertion_cannot_cross_patients(db):
    other = db.execute("INSERT INTO patients(mrn, name) VALUES ('X-1', 'Other Patient')").lastrowid
    encounter_id = db.execute("SELECT id FROM encounters LIMIT 1").fetchone()[0]
    extraction_id = db.execute("SELECT id FROM extractions LIMIT 1").fetchone()[0]
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO assertions(extraction_id, patient_id, encounter_id, kind, source_status, authored_on, attendance) "
            "VALUES (?, ?, ?, 'attendance', 'final', '2026-01-01', 'attended')",
            (extraction_id, other, encounter_id),
        )


def test_evidence_must_come_from_asserting_document(db):
    assertion = db.execute(
        "SELECT a.id, x.document_id FROM assertions a JOIN extractions x ON x.id = a.extraction_id LIMIT 1").fetchone()
    foreign_span = db.execute("SELECT id FROM evidence_spans WHERE document_id <> ? LIMIT 1", (assertion[1],)).fetchone()[0]
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO assertion_evidence(assertion_id, evidence_id) VALUES (?, ?)", (assertion[0], foreign_span))


# --- reconciliation rules ---------------------------------------------------

def test_claim_authored_after_a_correction_is_a_conflict_not_corrected():
    r = resolve([
        claim(1, "presence", 1, "2026-01-19", starts_at=at("10:00"), ends_at=at("11:30")),
        claim(2, "correction", 2, "2026-01-20", corrected_field="presence_end",
              replaced_value=at("11:30"), replacement_value=at("11:15")),
        claim(3, "presence", 3, "2026-01-21", starts_at=at("10:00"), ends_at=at("11:30")),
    ])
    assert r.duration_status == "disputed"
    assert sorted(a.minutes for a in r.alternatives) == [75, 90]
    assert r.members[1][0] == "disputed" and r.members[2][0] == "applied_correction"


def test_overlaps_are_not_double_counted_and_outside_breaks_are_ignored():
    r = resolve([
        claim(1, "presence", starts_at=at("09:00"), ends_at=at("10:00")),
        claim(2, "presence", starts_at=at("09:30"), ends_at=at("10:30")),
        claim(3, "break", starts_at=at("09:45"), ends_at=at("10:00")),
        claim(4, "break", starts_at=at("09:50"), ends_at=at("10:05")),
        claim(5, "break", starts_at=at("11:00"), ends_at=at("11:15")),
    ])
    assert [a.minutes for a in r.alternatives] == [70]


def test_presence_contradicting_a_no_show_leaves_attendance_disputed():
    r = resolve([
        claim(1, "attendance", 1, attendance="no_show"),
        claim(2, "presence", 2, starts_at=at("10:00"), ends_at=at("10:45")),
    ])
    assert (r.attendance_status, r.attendance) == ("disputed", None)
    assert [a.minutes for a in r.alternatives] == [45]


def test_correction_without_a_matching_claim_is_retained_unapplied():
    r = resolve([
        claim(1, "presence", 1, starts_at=at("10:00"), ends_at=at("11:00")),
        claim(2, "correction", 2, "2026-01-20", corrected_field="presence_end",
              replaced_value=at("11:30"), replacement_value=at("11:15")),
    ])
    assert r.members[2][0] == "unmatched_correction"
    assert (r.duration_status, [a.minutes for a in r.alternatives]) == ("established", [60])


def test_presence_and_breaks_stay_correlated_by_source():
    r = resolve([
        claim(1, "presence", 1, starts_at=at("10:00"), ends_at=at("11:00")),
        claim(2, "break", 1, starts_at=at("10:45"), ends_at=at("10:55")),
        claim(3, "presence", 2, starts_at=at("10:00"), ends_at=at("11:10")),
        claim(4, "break", 2, starts_at=at("10:40"), ends_at=at("11:00")),
    ])
    assert sorted(a.minutes for a in r.alternatives) == [50, 50]
    assert r.duration_status == "established"


def test_presence_only_roster_uses_other_documents_breaks():
    """Activity note may record breaks (and optional split presence); roster has continuous presence."""
    r = resolve([
        claim(1, "presence", 1, starts_at=at("10:00"), ends_at=at("11:30")),
        claim(2, "presence", 2, starts_at=at("10:00"), ends_at=at("10:40")),
        claim(3, "presence", 2, starts_at=at("10:55"), ends_at=at("11:30")),
        claim(4, "break", 2, starts_at=at("10:40"), ends_at=at("10:55")),
    ])
    assert sorted({a.minutes for a in r.alternatives}) == [75]
    assert r.duration_status == "established"


def test_competing_corrections_are_disputed_not_order_dependent():
    first = resolve([
        claim(1, "presence", 1, starts_at=at("10:00"), ends_at=at("11:30")),
        claim(2, "correction", 2, "2026-01-20", corrected_field="presence_end",
              replaced_value=at("11:30"), replacement_value=at("11:15")),
        claim(3, "correction", 3, "2026-01-20", corrected_field="presence_end",
              replaced_value=at("11:30"), replacement_value=at("11:20")),
    ])
    second = resolve([
        claim(1, "presence", 1, starts_at=at("10:00"), ends_at=at("11:30")),
        claim(2, "correction", 2, "2026-01-20", corrected_field="presence_end",
              replaced_value=at("11:30"), replacement_value=at("11:20")),
        claim(3, "correction", 3, "2026-01-20", corrected_field="presence_end",
              replaced_value=at("11:30"), replacement_value=at("11:15")),
    ])
    assert first.duration_status == second.duration_status == "disputed"
    assert sorted(a.minutes for a in first.alternatives) == sorted(a.minutes for a in second.alternatives) == [75, 80]
    assert {first.members[2][0], first.members[3][0]} == {"disputed"}


def test_disputed_service_type_keeps_the_date_in_weekly_totals(db):
    assert query(db, "minutes", **WINDOW)["weeks"][-1]["minutes"] == {"min": 145, "max": 155}
    add_detail(db, "2026-01-26", "group_therapy")
    reconcile(db, VERSION)
    after = query(db, "compliance", **WINDOW)["patients"][0]["weeks"][-1]
    assert after["status"] == "cannot_determine"
    assert after["minutes"] == {"min": 105, "max": 155}
    assert after["therapy_days"] == {"min": 2, "max": 3}
    assert "HG-E115" in after["depends_on"]


def test_distinct_form_ids_are_distinct_assessments(db, tmp_path):
    quote = "PHQ-9 form HG-Q999 completed 2026-01-16 with total score 12."
    incoming = tmp_path / "second_form.txt"
    incoming.write_text(f"Harbor Grove measure export\n{quote}\n", encoding="utf-8")
    ingest_directory(db, tmp_path)
    doc_id = db.execute(
        "SELECT document_id FROM document_sources WHERE locator = ?", (incoming.as_posix(),)
    ).fetchone()[0]
    with db:
        persist_extraction(db, doc_id, envelope({
            "assessments": [{
                "instrument": "PHQ-9", "completed_on": "2026-01-16", "form_id": "HG-Q999",
                "score": 12, "source_status": "final", "authored_on": "2026-01-16",
                "evidence_quotes": [quote],
            }]
        }), version=VERSION, producer="test")
    reconcile(db, VERSION)
    forms = {(a["completed_on"], a.get("form_id"), a["score"]) for a in query(db, "progress", **WINDOW)["assessments"]}
    assert ("2026-01-16", "HG-Q116", 14) in forms
    assert ("2026-01-16", "HG-Q999", 12) in forms


def test_partial_corpus_makes_compliance_provisional(tmp_path):
    db = open_db(tmp_path / "partial.sqlite")
    ingest_directory(db, DOCUMENTS)
    # Only the treatment plan and first week of notes.
    subset = ["signed_treatment_plan_jan05.txt", "intake_and_individual_jan05.txt",
              "early_group_attendance_roster.txt", "group_facilitator_jan06.txt",
              "family_primary_jan09.txt", "family_cofacilitator_jan09.txt"]
    persist_fixtures(db, DOCUMENTS, {n: GOLD[n] for n in subset}, patient=PATIENT, version=VERSION)
    reconcile(db, VERSION)
    result = query(db, "compliance", **WINDOW)
    assert result["abstraction"]["coverage_status"] == "provisional"
    assert result["coverage_status"] == "provisional"
    assert all(w["status"] == "cannot_determine" for w in result["patients"][0]["weeks"])
    db.close()


# Regression cases use new evidence in new sealed extractions.
def add_detail(db, service_date, service_type="individual_therapy"):
    quote = f"HG-E115 service date {service_date}, type {service_type}."
    import hashlib
    with db:
        doc = db.execute("INSERT INTO documents(sha256,content) VALUES (?,?)",
                         (hashlib.sha256(quote.encode()).hexdigest(), quote)).lastrowid
        db.execute("INSERT INTO document_sources VALUES (?,?)", (doc, f"synthetic-{doc}.txt"))
        persist_extraction(db, doc, envelope({"encounters": [{
            "encounter_id": "HG-E115", "service_date": service_date, "service_type": service_type,
            "source_status": "final", "authored_on": "2026-01-30", "attendance": None,
            "patient_presence": [], "breaks": [], "charges": [], "evidence_quotes": [quote]
        }]}), version=VERSION, producer="test")


def correction(id, old, new, field="presence_end", day="2026-01-20"):
    return claim(id, "correction", id, day, corrected_field=field,
                 replaced_value=at(old), replacement_value=at(new))


def test_correction_chain_follows_replacement():
    r = resolve([claim(1, "presence", starts_at=at("10:00"), ends_at=at("11:30")),
                 correction(2, "11:30", "11:15"), correction(3, "11:15", "11:10", day="2026-01-21")])
    assert [a.minutes for a in r.alternatives] == [70]
    assert r.duration_status == "corrected"


@pytest.mark.parametrize("corrections", [
    [correction(2, "10:00", "10:45", "presence_start"), correction(3, "11:00", "10:30")],
    [correction(2, "11:00", "11:15"), correction(3, "11:15", "11:00", day="2026-01-21")],
])
def test_invalid_or_cyclic_corrections_leave_unknown_duration(corrections):
    r = resolve([claim(1, "presence", starts_at=at("10:00"), ends_at=at("11:00")), *corrections])
    assert r.duration_status == "unknown" and r.alternatives == []
    assert any(role == "disputed" for role, _ in r.members.values())


def test_duplicate_correction_edges_keep_their_own_target_cutoffs():
    from itertools import permutations
    claims = [claim(1, "presence", 1, "2026-01-19", starts_at=at("10:00"), ends_at=at("11:30")),
              claim(2, "presence", 2, "2026-01-21", starts_at=at("10:00"), ends_at=at("11:30")),
              correction(3, "11:30", "11:15"), correction(4, "11:30", "11:15", day="2026-01-22")]
    for order in permutations(claims):
        assert {a.minutes for a in resolve(list(order)).alternatives} == {75}


def test_disputed_dates_inside_week_keep_session_and_minutes(db):
    add_detail(db, "2026-01-27")
    reconcile(db, VERSION)
    result = query(db, "attendance", **WINDOW)
    assert result["sessions"] == {"min": 12, "max": 12}
    assert result["minutes"] == {"min": 585, "max": 595}
    last = query(db, "compliance", **WINDOW)["patients"][0]["weeks"][-1]
    assert last["minutes"] == {"min": 145, "max": 155}
    assert last["therapy_days"] == {"min": 3, "max": 3}
    assert last["status"] == "cannot_determine"
    day = query(db, "days", patient="HG-M042", dates=[date(2026, 1, 26)])["days"][0]
    assert day["therapy_contacts"] == {"min": 0, "max": 1}
    assert day["minutes"] == {"min": 0, "max": 50}


def test_disputed_date_crosses_week_and_window(db):
    add_detail(db, "2026-02-02")
    reconcile(db, VERSION)
    assert query(db, "minutes", **WINDOW)["minutes"] == {"min": 545, "max": 595}
    last = query(db, "compliance", **WINDOW)["patients"][0]["weeks"][-1]
    assert last["status"] == "cannot_determine"
    assert last["minutes"] == {"min": 105, "max": 155}
    assert last["therapy_days"] == {"min": 2, "max": 3}


def test_sealed_extraction_rejects_new_children(db):
    x = db.execute("SELECT id FROM extractions LIMIT 1").fetchone()[0]
    patient = db.execute("SELECT id FROM patients LIMIT 1").fetchone()[0]
    with pytest.raises(sqlite3.IntegrityError, match="sealed"):
        db.execute("INSERT INTO assertions(extraction_id,patient_id,kind,source_status,authored_on,category,reporter,statement) "
                   "VALUES (?,?,'observation','final','2026-01-19','symptom','patient','Injected')", (x,patient))
    with pytest.raises(sqlite3.IntegrityError, match="sealed"):
        db.execute("INSERT INTO plans(extraction_id,patient_id,effective_start,effective_end,min_therapy_days,min_therapy_minutes) "
                   "VALUES (?,?,'2026-01-01','2026-01-31',3,150)", (x,patient))
    for table, parent, column in [("assertion_evidence", "assertions", "assertion_id"),
                                  ("plan_evidence", "plans", "plan_id")]:
        parent_id = db.execute(f"SELECT id FROM {parent} LIMIT 1").fetchone()[0]
        evidence = db.execute(f"SELECT evidence_id FROM {table} WHERE {column}=?", (parent_id,)).fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError, match="sealed"):
            db.execute(f"INSERT INTO {table} VALUES (?,?)", (parent_id,evidence))
    plan = db.execute("SELECT id FROM plans LIMIT 1").fetchone()[0]
    with pytest.raises(sqlite3.IntegrityError, match="sealed"):
        db.execute("INSERT INTO plan_services VALUES (?,'other')", (plan,))


def test_unsealed_evidence_free_claims_cannot_be_published(db):
    with db:
        x = db.execute("INSERT INTO extractions(document_id,version,producer,output_json) "
                       "SELECT id,'unsealed','test','{}' FROM documents LIMIT 1").lastrowid
        patient = db.execute("SELECT id FROM patients LIMIT 1").fetchone()[0]
        db.execute("INSERT INTO assertions(extraction_id,patient_id,kind,source_status,authored_on,category,reporter,statement) "
                   "VALUES (?,?,'observation','final','2026-01-19','symptom','patient','Injected')", (x,patient))
    with pytest.raises(sqlite3.IntegrityError, match="evidence"):
        db.execute("INSERT INTO extraction_seals VALUES (?)", (x,))
    with pytest.raises(ValueError, match="unsealed"):
        reconcile(db, "unsealed")


def test_sealed_reconciliation_rejects_new_results(db):
    resolution = db.execute('SELECT id FROM encounter_resolutions LIMIT 1').fetchone()[0]
    with pytest.raises(sqlite3.IntegrityError, match='sealed'):
        db.execute("INSERT INTO duration_alternatives(resolution_id,minutes,derivation) VALUES (?,999,'Injected')",
                   (resolution,))
    member = db.execute('SELECT resolution_id,assertion_id FROM resolution_members LIMIT 1').fetchone()
    with pytest.raises(sqlite3.IntegrityError, match='sealed'):
        db.execute("INSERT INTO resolution_members VALUES (?,?,'accepted',NULL)", tuple(member))
