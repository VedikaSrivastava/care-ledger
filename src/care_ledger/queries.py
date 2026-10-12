from __future__ import annotations

import json
import sqlite3
import time
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date, timedelta

from .models import THERAPY_SERVICES


class StaleAbstraction(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Range:
    """An integer quantity bounded by the documented alternatives; hi=None means no upper bound is documented."""

    lo: int
    hi: int | None

    def __add__(self, other: Range) -> Range:
        hi = None if self.hi is None or other.hi is None else self.hi + other.hi
        return Range(self.lo + other.lo, hi)

    def json(self) -> dict:
        return {"min": self.lo, "max": self.hi}


ZERO = Range(0, 0)


@dataclass(frozen=True, slots=True)
class Outcome:
    resolution_id: int
    encounter: str
    service_date: str | None
    service_type: str | None
    detail_status: str
    attendance: str | None
    attendance_status: str
    duration_status: str
    alternatives: tuple[tuple[int, str], ...]
    documents: tuple[str, ...]
    possible_dates: tuple[str, ...] = ()
    wholly_in_window: bool = True

    @property
    def minutes(self) -> Range:
        if self.alternatives:
            values = [m for m, _ in self.alternatives]
            return Range(min(values), max(values))
        return Range(0, None) if self.duration_status == "unknown" else ZERO

    def classify(self, eligible: frozenset[str]) -> tuple[str, str]:
        if self.service_type is None:
            return "undetermined", f"service type is {self.detail_status}"
        if self.service_type not in eligible:
            return "excluded", f"{self.service_type.replace('_', ' ')} is not an eligible therapy service"
        if self.attendance_status != "established":
            return "undetermined", f"attendance is {self.attendance_status}"
        if self.attendance != "attended":
            return "excluded", self.attendance.replace('_', ' ')
        return "included", "patient attended eligible therapy"

    def contribution(self, eligible: frozenset[str]) -> tuple[Range, Range]:
        """(session count, minutes) this encounter can contribute."""
        status, _ = self.classify(eligible)
        if status == "included" and self.wholly_in_window:
            return Range(1, 1), self.minutes
        if status == "included":
            return Range(0, 1), Range(0, self.minutes.hi)
        if status == "undetermined":
            return Range(0, 1), Range(0, self.minutes.hi)
        return ZERO, ZERO

    def summary(self, eligible: frozenset[str]) -> dict:
        status, reason = self.classify(eligible)
        return {
            "encounter": self.encounter,
            "date": self.service_date,
            "possible_dates": list(self.possible_dates),
            "date_certain_in_window": self.wholly_in_window,
            "service_type": self.service_type,
            "attendance": self.attendance or self.attendance_status,
            "status": status,
            "reason": reason,
            "minutes": self.minutes.json() if status != "excluded" else None,
            "duration_status": self.duration_status,
            "derivations": [d for _, d in self.alternatives],
            "documents": list(self.documents),
        }


# --- abstraction access -------------------------------------------------------

def current_run(db: sqlite3.Connection, version: str) -> sqlite3.Row:
    if db.execute("SELECT 1 FROM extractions x WHERE version=? AND NOT EXISTS "
                  "(SELECT 1 FROM extraction_seals s WHERE s.extraction_id=x.id)", (version,)).fetchone():
        raise StaleAbstraction("unsealed extractions exist; rebuild from source")
    run = db.execute(
        "SELECT * FROM reconciliation_runs WHERE extraction_version = ? ORDER BY id DESC LIMIT 1", (version,)
    ).fetchone()
    if run is None:
        raise LookupError(f"no reconciliation run for extraction version {version!r}; run `care-ledger reconcile`")
    if not db.execute("SELECT 1 FROM reconciliation_seals WHERE run_id=?", (run["id"],)).fetchone():
        raise StaleAbstraction("reconciliation is not sealed; run `care-ledger reconcile`")
    latest = db.execute("SELECT max(id) FROM extractions WHERE version = ?", (version,)).fetchone()[0]
    if latest > run["through_extraction_id"]:
        raise StaleAbstraction("new extractions exist since the last reconciliation; run `care-ledger reconcile`")
    return run


def _abstraction(db: sqlite3.Connection, run: sqlite3.Row) -> dict:
    reconciled = db.execute(
        "SELECT count(*) FROM extractions WHERE version = ? AND id <= ?",
        (run["extraction_version"], run["through_extraction_id"]),
    ).fetchone()[0]
    total = db.execute("SELECT count(*) FROM documents").fetchone()[0]
    pending = db.execute(
        "SELECT count(*) FROM documents d WHERE NOT EXISTS "
        "(SELECT 1 FROM extractions x WHERE x.document_id = d.id AND x.version = ?)",
        (run["extraction_version"],),
    ).fetchone()[0]
    return {
        "reconciliation_run": run["id"],
        "extraction_version": run["extraction_version"],
        "documents_total": total,
        "documents_reconciled": reconciled,
        "documents_not_extracted": pending,
        "coverage_status": "complete" if pending == 0 else "provisional",
    }


def _gate_incomplete_coverage(result: dict) -> dict:
    """Definitive clinical classifications require a fully extracted corpus."""
    abstraction = result["abstraction"]
    if abstraction["coverage_status"] == "complete":
        return result
    pending = abstraction["documents_not_extracted"]
    reason = f"{pending} document(s) not yet extracted; answer is provisional"
    result["coverage_status"] = "provisional"
    result["coverage_reason"] = reason
    for patient in result.get("patients", []):
        for week in patient.get("weeks", []):
            if week.get("status") in ("met", "not_met"):
                week["status"] = "cannot_determine"
                week["reason"] = reason
                week["depends_on"] = week.get("depends_on") or ["incomplete_extraction"]
        below = patient.get("consecutive_weeks_below_goal")
        if below:
            below["definite"] = []
            below["depends_on_unresolved"] = below.get("depends_on_unresolved") or []
    if "patients_with_consecutive_weeks_below_goal" in result:
        result["patients_with_consecutive_weeks_below_goal"] = {
            "definite": [],
            "depends_on_unresolved": [
                p["patient"] for p in result.get("patients", [])
                if p.get("consecutive_weeks_below_goal", {}).get("depends_on_unresolved")
                or any(w.get("status") == "cannot_determine" for w in p.get("weeks", []))
            ],
        }
    return result


def _patient(db: sqlite3.Connection, ref: str) -> sqlite3.Row:
    rows = db.execute(
        "SELECT * FROM patients WHERE mrn = ? OR lower(name) = lower(?)", (ref, ref)
    ).fetchall()
    if len(rows) != 1:
        raise LookupError(f"patient {ref!r} matched {len(rows)} records")
    return rows[0]


def _documents_by_resolution(db: sqlite3.Connection, run_id: int) -> dict[int, tuple[str, ...]]:
    rows = db.execute(
        """SELECT DISTINCT m.resolution_id, s.locator
           FROM resolution_members m
           JOIN encounter_resolutions r ON r.id = m.resolution_id
           JOIN assertions a ON a.id = m.assertion_id
           JOIN extractions x ON x.id = a.extraction_id
           JOIN (SELECT document_id, min(locator) AS locator FROM document_sources GROUP BY document_id) s
             ON s.document_id = x.document_id
           WHERE r.run_id = ? ORDER BY s.locator""",
        (run_id,),
    )
    documents: dict[int, list[str]] = defaultdict(list)
    for resolution_id, locator in rows:
        documents[resolution_id].append(locator.rsplit("/", 1)[-1])
    return {k: tuple(v) for k, v in documents.items()}


def _outcomes(db: sqlite3.Connection, run_id: int, patient_id: int) -> list[Outcome]:
    alternatives: dict[int, list[tuple[int, str]]] = defaultdict(list)
    for row in db.execute(
        """SELECT a.resolution_id, a.minutes, a.derivation FROM duration_alternatives a
           JOIN encounter_resolutions r ON r.id = a.resolution_id WHERE r.run_id = ? ORDER BY a.minutes, a.id""",
        (run_id,),
    ):
        alternatives[row[0]].append((row[1], row[2]))
    possible_dates = defaultdict(set)
    for row in db.execute(
        "SELECT m.resolution_id, a.service_date FROM resolution_members m "
        "JOIN encounter_resolutions r ON r.id=m.resolution_id "
        "JOIN assertions a ON a.id=m.assertion_id "
        "WHERE r.run_id=? AND a.kind='encounter_detail' AND a.source_status='final'", (run_id,)
    ):
        possible_dates[row[0]].add(row[1])
    documents = _documents_by_resolution(db, run_id)
    rows = db.execute(
        """SELECT r.*, e.external_id FROM encounter_resolutions r JOIN encounters e ON e.id = r.encounter_id
           WHERE r.run_id = ? AND e.patient_id = ? ORDER BY r.service_date, e.external_id""",
        (run_id, patient_id),
    )
    return [
        Outcome(r["id"], r["external_id"], r["service_date"], r["service_type"], r["detail_status"],
                r["attendance"], r["attendance_status"], r["duration_status"],
                tuple(alternatives[r["id"]]), documents.get(r["id"], ()),
                tuple(sorted(possible_dates[r["id"]])))
        for r in rows
    ]


def _evidence(db: sqlite3.Connection, assertion_ids) -> dict[int, list[dict]]:
    ids = list(assertion_ids)
    if not ids:
        return {}
    rows = db.execute(
        f"""SELECT ae.assertion_id, s.locator, es.start_offset, es.end_offset,
                   substr(d.content, es.start_offset + 1, es.end_offset - es.start_offset) AS quote
            FROM assertion_evidence ae
            JOIN evidence_spans es ON es.id = ae.evidence_id
            JOIN documents d ON d.id = es.document_id
            JOIN (SELECT document_id, min(locator) AS locator FROM document_sources GROUP BY document_id) s
              ON s.document_id = d.id
            WHERE ae.assertion_id IN ({', '.join('?' * len(ids))})
            ORDER BY ae.assertion_id, es.start_offset""",
        ids,
    )
    evidence: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        evidence[r["assertion_id"]].append({
            "document": r["locator"].rsplit("/", 1)[-1],
            "chars": [r["start_offset"], r["end_offset"]],
            "quote": r["quote"],
        })
    return evidence


def _weeks(start: date, end: date):
    monday = start - timedelta(days=start.weekday())
    while monday <= end:
        yield monday, max(monday, start), min(monday + timedelta(days=6), end)
        monday += timedelta(days=7)


def _in_window(outcomes: list[Outcome], start: date, end: date) -> list[Outcome]:
    result = []
    for o in outcomes:
        candidates = o.possible_dates or ((o.service_date,) if o.service_date else ())
        if not candidates:
            candidates = tuple((start + timedelta(days=i)).isoformat() for i in range((end-start).days + 1))
            o = replace(o, wholly_in_window=False)
        inside = tuple(d for d in candidates if start.isoformat() <= d <= end.isoformat())
        if inside:
            result.append(replace(o, possible_dates=inside,
                                  wholly_in_window=o.wholly_in_window and len(inside) == len(candidates)))
    return result


def _days(outcomes: list[Outcome], eligible: frozenset[str]) -> Range:
    # Reachable date sets avoid counting one encounter on multiple possible days.
    states = {frozenset()}
    for o in outcomes:
        status, _ = o.classify(eligible)
        if status == "excluded":
            continue
        options = list(o.possible_dates or ((o.service_date,) if o.service_date else ()))
        if status == "undetermined" or not o.wholly_in_window or not options:
            options.append(None)
        states = {days | ({d} if d else set()) for days in states for d in options}
        if len(states) > 10000:
            # Conservative bounds for unusually large disputed-date collections.
            certain = {v.service_date for v in outcomes if v.service_date
                       and v.wholly_in_window and v.classify(eligible)[0] == "included"}
            possible = set().union(*(set(v.possible_dates) for v in outcomes
                                   if v.classify(eligible)[0] != "excluded"))
            return Range(len(certain), max(len(certain), len(possible)))
    sizes = [len(days) for days in states]
    return Range(min(sizes), max(sizes))


def _total(outcomes: list[Outcome], eligible: frozenset[str]) -> tuple[Range, Range]:
    sessions, minutes = ZERO, ZERO
    for o in outcomes:
        s, m = o.contribution(eligible)
        sessions, minutes = sessions + s, minutes + m
    return sessions, minutes


def _hours(minutes: Range) -> dict:
    return {"min": round(minutes.lo / 60, 2), "max": None if minutes.hi is None else round(minutes.hi / 60, 2)}


# --- queries -----------------------------------------------------------------

def attendance(db, run, *, patient: str, start: date, end: date) -> dict:
    p = _patient(db, patient)
    outcomes = _outcomes(db, run["id"], p["id"])
    window = _in_window(outcomes, start, end)
    eligible = THERAPY_SERVICES
    by_type = {}
    for service_type in sorted(THERAPY_SERVICES):
        sessions, minutes = _total([o for o in window if o.service_type == service_type], eligible)
        by_type[service_type] = {"sessions": sessions.json(), "minutes": minutes.json()}
    sessions, minutes = _total(window, eligible)
    groups = defaultdict(list)
    for o in window:
        groups[o.classify(eligible)[0]].append(o.summary(eligible))
    return {
        "patient": p["mrn"], "window": [start.isoformat(), end.isoformat()],
        "sessions": sessions.json(), "by_service_type": by_type,
        "distinct_therapy_days": _days(window, eligible).json(),
        "minutes": minutes.json(),
        "included": groups["included"], "excluded": groups["excluded"], "undetermined": groups["undetermined"],
        "unplaced": [o.summary(eligible) for o in outcomes if not o.service_date],
    }


def minutes(db, run, *, patient: str, start: date, end: date) -> dict:
    p = _patient(db, patient)
    window = _in_window(_outcomes(db, run["id"], p["id"]), start, end)
    eligible = THERAPY_SERVICES
    _, total = _total(window, eligible)
    weeks = []
    for monday, first, last in _weeks(start, end):
        week = _in_window(window, first, last)
        _, week_minutes = _total(week, eligible)
        weeks.append({
            "week_of": monday.isoformat(), "period": [first.isoformat(), last.isoformat()],
            "partial_week": (last - first).days < 6,
            "minutes": week_minutes.json(), "hours": _hours(week_minutes),
            "encounters": [o.summary(eligible) for o in week if o.classify(eligible)[0] != "excluded"],
        })
    unresolved = [o.summary(eligible) for o in window
                  if o.classify(eligible)[0] != "excluded" and o.minutes.lo != o.minutes.hi]
    return {
        "patient": p["mrn"], "window": [start.isoformat(), end.isoformat()],
        "minutes": total.json(), "hours": _hours(total), "weeks": weeks, "unresolved": unresolved,
    }


def _plans(db, run, patient_id: int) -> list[dict]:
    rows = db.execute(
        """SELECT p.* FROM plans p JOIN extractions x ON x.id = p.extraction_id
           WHERE p.patient_id = ? AND x.version = ? AND x.id <= ?""",
        (patient_id, run["extraction_version"], run["through_extraction_id"]),
    ).fetchall()
    plans = []
    for r in rows:
        services = frozenset(s for (s,) in db.execute("SELECT service_type FROM plan_services WHERE plan_id = ?", (r["id"],)))
        quotes = db.execute(
            """SELECT substr(d.content, es.start_offset + 1, es.end_offset - es.start_offset)
               FROM plan_evidence pe JOIN evidence_spans es ON es.id = pe.evidence_id
               JOIN documents d ON d.id = es.document_id WHERE pe.plan_id = ? ORDER BY es.start_offset""",
            (r["id"],),
        ).fetchall()
        plans.append({
            "start": r["effective_start"], "end": r["effective_end"],
            "min_days": r["min_therapy_days"], "min_minutes": r["min_therapy_minutes"],
            "services": services, "evidence": [q[0] for q in quotes],
        })
    return plans


def _week_compliance(plans: list[dict], outcomes: list[Outcome], first: date, last: date) -> dict:
    period = (first.isoformat(), last.isoformat())
    active = [pl for pl in plans if pl["start"] <= period[1] and pl["end"] >= period[0]]
    requirements = {(pl["min_days"], pl["min_minutes"], pl["services"]) for pl in active}
    base = {"period": list(period), "partial_week": (last - first).days < 6}
    if not requirements:
        return base | {"status": "no_plan", "reason": "no treatment-plan requirement is documented for this week"}
    if len(requirements) > 1:
        return base | {"status": "cannot_determine", "reason": "different plan requirements apply within this week"}
    plan = active[0]
    if any(pl["start"] > period[0] or pl["end"] < period[1] for pl in active):
        return base | {"status": "cannot_determine", "reason": "the plan is in effect for only part of this week"}
    eligible = plan["services"]
    days = _days(outcomes, eligible)
    _, mins = _total(outcomes, eligible)
    if days.lo >= plan["min_days"] and mins.lo >= plan["min_minutes"]:
        status = "met"
    elif (days.hi is not None and days.hi < plan["min_days"]) or (mins.hi is not None and mins.hi < plan["min_minutes"]):
        status = "not_met"
    else:
        status = "cannot_determine"
    depends_on = [o.encounter for o in outcomes
                  if o.classify(eligible)[0] == "undetermined" or not o.wholly_in_window
                  or (o.classify(eligible)[0] == "included" and o.minutes.lo != o.minutes.hi)]
    return base | {
        "status": status,
        "goal": {"min_days": plan["min_days"], "min_minutes": plan["min_minutes"], "services": sorted(eligible)},
        "therapy_days": days.json(), "minutes": mins.json(),
        "depends_on": depends_on if status == "cannot_determine" else [],
    }


def _consecutive_below(weeks: list[dict]) -> dict:
    definite, dependent = [], []
    for a, b in zip(weeks, weeks[1:]):
        statuses = {a["status"], b["status"]}
        pair = [a["week_of"], b["week_of"]]
        if statuses == {"not_met"}:
            definite.append(pair)
        elif statuses <= {"not_met", "cannot_determine"}:
            dependent.append(pair)
    return {"definite": definite, "depends_on_unresolved": dependent}


def compliance(db, run, *, start: date, end: date, patient: str | None = None) -> dict:
    patients = [_patient(db, patient)] if patient else db.execute("SELECT * FROM patients ORDER BY mrn").fetchall()
    results = []
    for p in patients:
        plans = _plans(db, run, p["id"])
        window = _in_window(_outcomes(db, run["id"], p["id"]), start, end)
        weeks = [
            {"week_of": monday.isoformat()} | _week_compliance(plans, _in_window(window, first, last), first, last)
            for monday, first, last in _weeks(start, end)
        ]
        results.append({
            "patient": p["mrn"], "name": p["name"],
            "plans": [{k: (sorted(v) if k == "services" else v) for k, v in pl.items()} for pl in plans],
            "weeks": weeks, "consecutive_weeks_below_goal": _consecutive_below(weeks),
        })
    return {
        "window": [start.isoformat(), end.isoformat()], "patients": results,
        "patients_with_consecutive_weeks_below_goal": {
            "definite": [r["patient"] for r in results if r["consecutive_weeks_below_goal"]["definite"]],
            "depends_on_unresolved": [r["patient"] for r in results
                                      if not r["consecutive_weeks_below_goal"]["definite"]
                                      and r["consecutive_weeks_below_goal"]["depends_on_unresolved"]],
        },
    }


def _encounter_detail(db, outcome: Outcome) -> dict:
    members = db.execute(
        """SELECT m.assertion_id, m.role, m.note, a.kind, a.source_status, a.authored_on, a.service_date,
                  a.service_type, a.attendance, a.starts_at, a.ends_at, a.corrected_field, a.replaced_value,
                  a.replacement_value, a.external_ref
           FROM resolution_members m JOIN assertions a ON a.id = m.assertion_id
           WHERE m.resolution_id = ? ORDER BY a.kind, a.id""",
        (outcome.resolution_id,),
    ).fetchall()
    evidence = _evidence(db, (m["assertion_id"] for m in members))
    claims = []
    for m in members:
        value = {k: m[k] for k in ("service_date", "service_type", "attendance", "starts_at", "ends_at",
                                   "corrected_field", "replaced_value", "replacement_value", "external_ref")
                 if m[k] is not None}
        claims.append({"assertion": m["assertion_id"], "kind": m["kind"], "role": m["role"], "note": m["note"],
                       "source_status": m["source_status"], "authored_on": m["authored_on"], "value": value,
                       "evidence": evidence[m["assertion_id"]]})
    return outcome.summary(THERAPY_SERVICES) | {"claims": claims}


def days(db, run, *, patient: str, dates: list[date]) -> dict:
    p = _patient(db, patient)
    outcomes = _outcomes(db, run["id"], p["id"])
    result = []
    for day in dates:
        on_day = _in_window(outcomes, day, day)
        sessions, mins = _total(on_day, THERAPY_SERVICES)
        result.append({"date": day.isoformat(), "therapy_contacts": sessions.json(), "minutes": mins.json(),
                       "encounters": [_encounter_detail(db, o) for o in on_day]})
    return {"patient": p["mrn"], "days": result}


def encounter(db, run, *, patient: str, encounter: str) -> dict:
    p = _patient(db, patient)
    matches = [o for o in _outcomes(db, run["id"], p["id"]) if o.encounter == encounter]
    if not matches:
        raise LookupError(f"encounter {encounter!r} has no resolution for patient {p['mrn']}")
    return {"patient": p["mrn"]} | _encounter_detail(db, matches[0])


def progress(db, run, *, patient: str, start: date, end: date) -> dict:
    p = _patient(db, patient)
    scope = (run["extraction_version"], run["through_extraction_id"])
    window = (start.isoformat(), end.isoformat())
    scores = db.execute(
        """SELECT s.id AS assessment_id, s.instrument, s.completed_on, s.form_key,
                  a.id, a.score, a.external_ref, a.authored_on
           FROM assessments s JOIN assertions a ON a.assessment_id = s.id
           JOIN extractions x ON x.id = a.extraction_id
           WHERE s.patient_id = ? AND x.version = ? AND x.id <= ? AND a.source_status = 'final'
             AND s.completed_on BETWEEN ? AND ?
           ORDER BY s.instrument, s.completed_on, s.form_key, a.id""",
        (p["id"], *scope, *window),
    ).fetchall()
    observations = db.execute(
        """SELECT a.id, a.authored_on, a.category, a.reporter, a.statement, e.external_id AS encounter,
                  rev.previous_value AS reviewed_from, rev.replacement_value AS reviewed_reporter, rev.basis AS review_basis
           FROM assertions a JOIN extractions x ON x.id = a.extraction_id
           LEFT JOIN encounters e ON e.id = a.encounter_id
           LEFT JOIN assertion_reviews rev ON rev.id = (
               SELECT max(id) FROM assertion_reviews WHERE assertion_id = a.id AND field = 'reporter')
           WHERE a.patient_id = ? AND a.kind = 'observation' AND a.source_status = 'final'
             AND x.version = ? AND x.id <= ? AND a.authored_on BETWEEN ? AND ?
           ORDER BY a.authored_on, a.id""",
        (p["id"], *scope, *window),
    ).fetchall()
    evidence = _evidence(db, [r["id"] for r in scores] + [r["id"] for r in observations])

    assessments: dict[int, dict] = {}
    for r in scores:
        form_id = r["external_ref"] or (None if r["form_key"].startswith("anon:") else r["form_key"] or None)
        entry = assessments.setdefault(r["assessment_id"], {
            "instrument": r["instrument"], "completed_on": r["completed_on"], "form_id": form_id, "sources": []})
        entry["sources"].append({"score": r["score"], "form_id": r["external_ref"], "authored_on": r["authored_on"],
                                 "evidence": evidence[r["id"]]})
    trajectories: dict[str, list] = defaultdict(list)
    for entry in assessments.values():
        distinct = {s["score"] for s in entry["sources"]}
        entry["status"] = "established" if len(distinct) == 1 else "disputed"
        entry["score"] = distinct.pop() if entry["status"] == "established" else None
        entry["source_documents"] = len({e["document"] for s in entry["sources"] for e in s["evidence"]})
        trajectories[entry["instrument"]].append((entry["completed_on"], entry["score"]))
    trend = {}
    for instrument, points in trajectories.items():
        known = [(d, s) for d, s in points if s is not None]
        trend[instrument] = {
            "points": [{"completed_on": d, "score": s} for d, s in points],
            "change_first_to_last": known[-1][1] - known[0][1] if len(known) >= 2 else None,
        }
    return {
        "patient": p["mrn"], "window": list(window),
        "assessments": list(assessments.values()), "trend": trend,
        "observations": [
            {"date": r["authored_on"], "encounter": r["encounter"], "category": r["category"],
             "reporter": r["reviewed_reporter"] or r["reporter"], "statement": r["statement"],
             "evidence": evidence[r["id"]],
             **({"attribution_review": {"previous": r["reviewed_from"], "replacement": r["reviewed_reporter"],
                                        "basis": r["review_basis"]}} if r["reviewed_reporter"] else {})}
            for r in observations
        ],
        "limits": [
            "Assessments with the same source form identifier and completion date are one assessment; imported copies are additional sources. Distinct form identifiers are distinct assessments. Results without a form identifier are not merged across documents.",
            "Scores and observations are reported as documented and attributed to their reporter; remission, recovery, work readiness, and treatment causation are not inferred.",
        ],
    }


QUERIES = {
    "attendance": attendance,
    "minutes": minutes,
    "compliance": compliance,
    "days": days,
    "encounter": encounter,
    "progress": progress,
}


def run_query(db: sqlite3.Connection, version: str, name: str, persist: bool = True, **params) -> dict:
    run = current_run(db, version)
    started = time.perf_counter()
    result = _gate_incomplete_coverage(QUERIES[name](db, run, **params) | {"abstraction": _abstraction(db, run)})
    elapsed = (time.perf_counter() - started) * 1000
    if persist:
        with db:
            db.execute(
                "INSERT INTO calculation_runs(reconciliation_run_id, query, parameters_json, result_json, elapsed_ms) "
                "VALUES (?, ?, ?, ?, ?)",
                (run["id"], name, json.dumps(params, default=str, sort_keys=True), json.dumps(result, default=str), elapsed),
            )
    return result
