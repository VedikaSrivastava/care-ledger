from __future__ import annotations

import sqlite3
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from itertools import groupby, product

POLICY_VERSION = "2026-10-11"
ENCOUNTER_KINDS = ("encounter_detail", "attendance", "presence", "break", "correction", "charge")

Span = tuple[str, str]


@dataclass(frozen=True, slots=True)
class EncounterClaim:
    id: int
    extraction_id: int
    kind: str
    source_status: str
    authored_on: str
    service_date: str | None = None
    service_type: str | None = None
    attendance: str | None = None
    starts_at: str | None = None
    ends_at: str | None = None
    corrected_field: str | None = None
    replaced_value: str | None = None
    replacement_value: str | None = None


@dataclass(frozen=True, slots=True)
class Alternative:
    minutes: int
    derivation: str
    assertion_ids: tuple[int, ...]


@dataclass(slots=True)
class Resolution:
    detail_status: str
    service_date: str | None
    service_type: str | None
    attendance_status: str
    attendance: str | None
    duration_status: str
    alternatives: list[Alternative]
    members: dict[int, tuple[str, str | None]] = field(default_factory=dict)


def _minutes(span: Span) -> int:
    start, end = (datetime.fromisoformat(v) for v in span)
    return int((end - start).total_seconds() // 60)


def _merge(spans) -> tuple[Span, ...]:
    merged: list[list[str]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return tuple((s, e) for s, e in merged)


def _clip(breaks: tuple[Span, ...], presence: tuple[Span, ...]) -> tuple[Span, ...]:
    return _merge(
        (max(bs, ps), min(be, pe)) for bs, be in breaks for ps, pe in presence if max(bs, ps) < min(be, pe)
    )


def _clock(span: Span) -> str:
    return f"{span[0][11:16]}-{span[1][11:16]}"


def _alternative(presence: tuple[Span, ...], breaks: tuple[Span, ...], assertion_ids) -> Alternative:
    deducted = _clip(breaks, presence)
    present = sum(map(_minutes, presence))
    removed = sum(map(_minutes, deducted))
    derivation = " + ".join(f"{_clock(s)} ({_minutes(s)})" for s in presence)
    if deducted:
        derivation += " - breaks " + " + ".join(f"{_clock(s)} ({_minutes(s)})" for s in deducted)
    return Alternative(present - removed, f"{derivation} = {present - removed} min", tuple(sorted(assertion_ids)))


def _accounts(claims: list[EncounterClaim], span_of) -> dict[tuple[Span, ...], list[int]]:
    """Group interval claims into one account per source document; identical accounts merge."""
    by_document: dict[int, list[EncounterClaim]] = defaultdict(list)
    for c in claims:
        by_document[c.extraction_id].append(c)
    accounts: dict[tuple[Span, ...], list[int]] = defaultdict(list)
    for group in by_document.values():
        accounts[_merge(span_of(c) for c in group)].extend(c.id for c in group)
    return accounts


def _agreement(values: dict[int, object]) -> tuple[str, object]:
    distinct = set(values.values())
    if not distinct:
        return "unknown", None
    if len(distinct) == 1:
        return "established", distinct.pop()
    return "disputed", None


def resolve(claims: list[EncounterClaim]) -> Resolution:
    """Reconcile every claim made about one encounter.

    Draft sources and billing never establish facts. A correction replaces a
    specific recorded time in claims authored on or before the correction;
    receipt order is irrelevant. Remaining disagreement is kept as alternatives.
    """
    members: dict[int, tuple[str, str | None]] = {}
    final = [c for c in claims if c.source_status == "final"]
    for c in claims:
        if c.source_status == "draft":
            members[c.id] = ("rejected", "draft or template text does not establish facts")
        elif c.kind == "charge":
            members[c.id] = ("context", "a charge does not establish delivered care")

    details = {c.id: (c.service_date, c.service_type) for c in final if c.kind == "encounter_detail"}
    detail_status, detail = _agreement(details)
    for claim_id in details:
        members[claim_id] = ("accepted" if detail_status == "established" else "disputed", None)

    explicit = {c.id: c.attendance for c in final if c.kind == "attendance"}
    implied = {c.id: "attended" for c in final if c.kind == "presence"}
    attendance_status, attendance = _agreement(explicit | implied)
    for claim_id in explicit:
        members[claim_id] = ("accepted" if attendance_status == "established" else "disputed", None)

    presence = [c for c in final if c.kind == "presence"]
    breaks = [c for c in final if c.kind == "break"]
    corrections = sorted((c for c in final if c.kind == "correction"), key=lambda c: (c.authored_on, c.id))

    effective: dict[int, Span] = {c.id: (c.starts_at, c.ends_at) for c in presence}
    correction_notes: dict[int, list[str]] = defaultdict(list)
    for corr in corrections:
        index = 0 if corr.corrected_field == "presence_start" else 1
        targets = [
            p for p in presence
            if effective[p.id][index] == corr.replaced_value and p.authored_on <= corr.authored_on
        ]
        updated = {}
        for p in targets:
            span = list(effective[p.id])
            span[index] = corr.replacement_value
            updated[p.id] = (span[0], span[1])
        if any(s >= e for s, e in updated.values()):
            members[corr.id] = ("rejected", "correction would produce an empty presence interval")
            continue
        if not targets:
            members[corr.id] = ("unmatched_correction", "no claim authored on or before it records the replaced time")
            continue
        effective.update(updated)
        members[corr.id] = ("applied_correction", f"applied to {len(targets)} claim(s)")
        for p in targets:
            correction_notes[p.id].append(
                f"{corr.corrected_field} {corr.replaced_value[11:16]} -> {corr.replacement_value[11:16]}"
            )

    presence_accounts = _accounts(presence, lambda c: effective[c.id])
    break_accounts = _accounts(breaks, lambda c: (c.starts_at, c.ends_at))

    for accounts in (presence_accounts, break_accounts):
        role = "disputed" if len(accounts) > 1 else "accepted"
        for ids in accounts.values():
            for claim_id in ids:
                members[claim_id] = ("corrected" if role == "accepted" and claim_id in correction_notes else role,
                                     "; ".join(correction_notes.get(claim_id, [])) or None)

    alternatives: list[Alternative] = []
    if attendance_status == "established" and attendance != "attended":
        duration_status = "not_applicable"
    elif not presence_accounts:
        duration_status = "unknown"
    else:
        for (p_spans, p_ids), (b_spans, b_ids) in product(presence_accounts.items(), break_accounts.items() or [((), [])]):
            alternatives.append(_alternative(p_spans, b_spans, [*p_ids, *b_ids]))
        if len({a.minutes for a in alternatives}) > 1:
            duration_status = "disputed"
        elif any(claim_id in correction_notes for ids in presence_accounts.values() for claim_id in ids):
            duration_status = "corrected"
        else:
            duration_status = "established"

    service_date, service_type = detail if detail else (None, None)
    return Resolution(detail_status, service_date, service_type, attendance_status, attendance,
                      duration_status, alternatives, members)


def _load_claims(db: sqlite3.Connection, version: str) -> list[tuple[int, EncounterClaim]]:
    rows = db.execute(
        f"""SELECT a.encounter_id, a.id, a.extraction_id, a.kind, a.source_status, a.authored_on,
                   a.service_date, a.service_type, a.attendance, a.starts_at, a.ends_at,
                   a.corrected_field, a.replaced_value, a.replacement_value
            FROM assertions a JOIN extractions x ON x.id = a.extraction_id
            WHERE x.version = ? AND a.kind IN ({', '.join('?' * len(ENCOUNTER_KINDS))})
            ORDER BY a.encounter_id, a.id""",
        (version, *ENCOUNTER_KINDS),
    )
    return [(r[0], EncounterClaim(*r[1:])) for r in rows]


def reconcile(db: sqlite3.Connection, version: str) -> int:
    started = time.perf_counter()
    through = db.execute("SELECT max(id) FROM extractions WHERE version = ?", (version,)).fetchone()[0]
    if through is None:
        raise LookupError(f"no extractions exist for version {version!r}")
    resolutions = {
        encounter_id: resolve([claim for _, claim in group])
        for encounter_id, group in groupby(_load_claims(db, version), key=lambda row: row[0])
    }
    elapsed = (time.perf_counter() - started) * 1000
    with db:
        run_id = db.execute(
            "INSERT INTO reconciliation_runs(extraction_version, through_extraction_id, policy_version, elapsed_ms) "
            "VALUES (?, ?, ?, ?)",
            (version, through, POLICY_VERSION, elapsed),
        ).lastrowid
        for encounter_id, r in resolutions.items():
            resolution_id = db.execute(
                "INSERT INTO encounter_resolutions(run_id, encounter_id, detail_status, service_date, service_type, "
                "attendance_status, attendance, duration_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, encounter_id, r.detail_status, r.service_date, r.service_type,
                 r.attendance_status, r.attendance, r.duration_status),
            ).lastrowid
            for alt in r.alternatives:
                alternative_id = db.execute(
                    "INSERT INTO duration_alternatives(resolution_id, minutes, derivation) VALUES (?, ?, ?)",
                    (resolution_id, alt.minutes, alt.derivation),
                ).lastrowid
                db.executemany("INSERT INTO alternative_assertions(alternative_id, assertion_id) VALUES (?, ?)",
                               [(alternative_id, a) for a in alt.assertion_ids])
            db.executemany(
                "INSERT INTO resolution_members(resolution_id, assertion_id, role, note) VALUES (?, ?, ?, ?)",
                [(resolution_id, claim_id, role, note) for claim_id, (role, note) in r.members.items()],
            )
    return run_id
