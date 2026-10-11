import json
import shutil
import sqlite3
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from care_ledger.db import ingest_directory, open_db
from care_ledger.models import Interval, Patient
from care_ledger.persist import AlreadyExtracted, EvidenceError, persist_extraction, persist_reviewed, reviewed_envelope
from care_ledger.queries import StaleAbstraction, run_query
from care_ledger.reconcile import EncounterClaim, resolve, reconcile

DOCUMENTS = Path(__file__).parents[1] / "documents"
GOLD = json.loads((Path(__file__).parent / "fixtures" / "reviewed_extractions.json").read_text(encoding="utf-8"))
PATIENT = Patient(mrn="HG-M042", name="Rowan Mercer", birth_date=date(1991, 4, 12))
VERSION = "reviewed"
WINDOW = {"patient": "HG-M042", "start": date(2026, 1, 5), "end": date(2026, 1, 30)}


def envelope(claims: dict):
    return reviewed_envelope(PATIENT, claims)


def document_id(db, name: str) -> int:
    return db.execute(
        "SELECT document_id FROM document_sources WHERE locator = ?", ((DOCUMENTS / name).as_posix(),)
    ).fetchone()[0]


def load_reviewed(db, names=None) -> int:
    persist_reviewed(
        db, DOCUMENTS, {n: GOLD[n] for n in (names or GOLD)},
        patient=PATIENT, version=VERSION,
    )
    return reconcile(db, VERSION)


def fresh_db(path: Path, names=None):
    db = open_db(path)
    ingest_directory(db, DOCUMENTS)
    load_reviewed(db, names)
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


# --- end-to-end on the reviewed extraction ----------------------------------

def test_reviewed_extraction_covers_every_document():
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
        persist_extraction(db, new_id, envelope({}), version=VERSION, producer="human-review")
    with pytest.raises(StaleAbstraction):
        query(db, "minutes", **WINDOW)
    reconcile(db, VERSION)
    assert query(db, "minutes", **WINDOW)["minutes"] == {"min": 585, "max": 595}


def test_reload_reviewed_does_not_duplicate_extractions(db):
    before = db.execute("SELECT count(*) FROM extractions").fetchone()[0]
    persist_reviewed(db, DOCUMENTS, GOLD, patient=PATIENT, version=VERSION)
    assert db.execute("SELECT count(*) FROM extractions").fetchone()[0] == before
    assert query(db, "minutes", **WINDOW)["minutes"] == {"min": 585, "max": 595}


def test_second_persist_of_same_document_is_rejected(db):
    doc = document_id(db, "BH-D105_individual_2026-01-19.txt")
    with pytest.raises(AlreadyExtracted):
        with db:
            persist_extraction(db, doc, envelope({}), version=VERSION, producer="human-review")


def test_timezone_offset_is_not_a_clock_time():
    with pytest.raises(ValidationError, match="timezone"):
        Interval(start="10:45:00-11:00", end="11:00", evidence_quotes=["quoted"])


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
