from __future__ import annotations

import sqlite3
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from itertools import groupby, product

POLICY_VERSION = "2026-10-12"
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


def _agreement(values: dict[int, object]) -> tuple[str, object]:
    distinct = set(values.values())
    if not distinct:
        return "unknown", None
    if len(distinct) == 1:
        return "established", distinct.pop()
    return "disputed", None


def _duration_alternatives(
    presence: list[EncounterClaim],
    breaks: list[EncounterClaim],
    effective: dict[int, Span],
) -> list[Alternative]:
    """One scenario per source document.

    A document's own presence and breaks stay together. Presence-only documents
    may use another document's breaks (complementary evidence). Presence+break
    documents are never crossed with a different presence account.
    """
    by_presence: dict[int, list[EncounterClaim]] = defaultdict(list)
    by_break: dict[int, list[EncounterClaim]] = defaultdict(list)
    for p in presence:
        by_presence[p.extraction_id].append(p)
    for b in breaks:
        by_break[b.extraction_id].append(b)

    break_accounts = {
        doc_id: (
            _merge((c.starts_at, c.ends_at) for c in claims),
            [c.id for c in claims],
        )
        for doc_id, claims in by_break.items()
    }
    scenarios = []
    for doc_id, p_claims in by_presence.items():
        p_spans = _merge(effective[c.id] for c in p_claims)
        p_ids = [c.id for c in p_claims]
        if doc_id in break_accounts:
            b_spans, b_ids = break_accounts[doc_id]
            scenarios.append((p_spans, b_spans, [*p_ids, *b_ids], True, doc_id))
        else:
            scenarios.append((p_spans, (), p_ids, False, doc_id))

    if not scenarios:
        return []

    alternatives: list[Alternative] = []
    for p_spans, b_spans, ids, has_own_breaks, doc_id in scenarios:
        if has_own_breaks:
            alternatives.append(_alternative(p_spans, b_spans, ids))
            continue
        others = [(spans, bids) for other_id, (spans, bids) in break_accounts.items() if other_id != doc_id]
        if not others:
            alternatives.append(_alternative(p_spans, (), ids))
        else:
            for cb_spans, cb_ids in others:
                alternatives.append(_alternative(p_spans, cb_spans, [*ids, *cb_ids]))
    return alternatives


def _apply_corrections(
    presence: list[EncounterClaim],
    corrections: list[EncounterClaim],
    members: dict[int, tuple[str, str | None]],
) -> tuple[list[dict[int, Span]], dict[int, list[str]]]:
    """Follow dated correction edges, preserving forks and validating complete intervals.

    Choices are shared across matching claims. Each edge retains its authorship
    cutoff. Cycles or invalid combined endpoints leave duration unknown.
    """
    original = {c.id: (c.starts_at, c.ends_at) for c in presence}
    notes: dict[int, list[str]] = defaultdict(list)
    groups = defaultdict(list)
    for c in corrections:
        groups[(c.corrected_field, c.replaced_value)].append(c)
    keys = sorted(groups)
    choices = [sorted({c.replacement_value for c in groups[k]}) for k in keys]
    used, disputed = set(), set()
    maps = []
    invalid = False
    for replacements in product(*choices):
        selected = dict(zip(keys, replacements))
        effective = {}
        for p in presence:
            span = list(original[p.id])
            for index, field_name in enumerate(("presence_start", "presence_end")):
                value, since, visited = span[index], p.authored_on, set()
                while (field_name, value) in groups:
                    key = (field_name, value)
                    eligible = [c for c in groups[key] if c.authored_on >= since]
                    if not eligible:
                        break
                    eligible_values = {c.replacement_value for c in eligible}
                    replacement = next(iter(eligible_values)) if len(eligible_values) == 1 else selected[key]
                    edges = [c for c in eligible if c.replacement_value == replacement]
                    if not edges:
                        break
                    if value in visited or replacement in visited:
                        invalid = True
                        disputed.update(c.id for c in edges)
                        break
                    visited.add(value)
                    used.update(c.id for c in edges)
                    if len(eligible_values) > 1:
                        disputed.update(c.id for c in eligible)
                    note = f"{field_name} {value[11:16]} -> {replacement[11:16]}"
                    if note not in notes[p.id]:
                        notes[p.id].append(note)
                    since = min(c.authored_on for c in edges)
                    value = replacement
                span[index] = value
            if span[0] >= span[1]:
                invalid = True
            effective[p.id] = tuple(span)
        if effective not in maps:
            maps.append(effective)
    for c in corrections:
        if c.id in disputed or (invalid and c.id in used):
            members[c.id] = ("disputed", "competing, cyclic, or jointly invalid correction chain")
        elif c.id in used:
            members[c.id] = ("applied_correction", "applied through a matching dated correction chain")
        else:
            members[c.id] = ("unmatched_correction", "no eligible claim or correction chain records the replaced time")
    return ([] if invalid else maps), notes


def resolve(claims: list[EncounterClaim]) -> Resolution:
    """Reconcile every claim made about one encounter.

    Draft sources and billing never establish facts. A correction replaces a
    specific recorded time in claims authored on or before the correction;
    receipt order is irrelevant. Competing replacements stay disputed.
    Presence and breaks from the same source stay correlated.
    """
    members: dict[int, tuple[str, str | None]] = {}
    final = [c for c in claims if c.source_status == "final"]
    for c in claims:
        if c.source_status == "draft":
            members[c.id] = ("rejected", "draft or template text does not establish facts")
        elif c.kind == "charge":
            members[c.id] = ("context", "a charge does not establish delivered care")

    date_values = {c.id: c.service_date for c in final if c.kind == "encounter_detail"}
    type_values = {c.id: c.service_type for c in final if c.kind == "encounter_detail"}
    date_status, service_date = _agreement(date_values)
    type_status, service_type = _agreement(type_values)
    if date_status == "established" and type_status == "established":
        detail_status = "established"
    elif date_status == "unknown" and type_status == "unknown":
        detail_status = "unknown"
    else:
        detail_status = "disputed"
    # Retain each established field even when the other is disputed (CHECK allows one null when not established).
    stored_date = service_date if date_status == "established" else None
    stored_type = service_type if type_status == "established" else None
    for claim_id in date_values:
        members[claim_id] = ("accepted" if detail_status == "established" else "disputed", None)

    explicit = {c.id: c.attendance for c in final if c.kind == "attendance"}
    implied = {c.id: "attended" for c in final if c.kind == "presence"}
    attendance_status, attendance = _agreement(explicit | implied)
    for claim_id in explicit:
        members[claim_id] = ("accepted" if attendance_status == "established" else "disputed", None)

    presence = [c for c in final if c.kind == "presence"]
    breaks = [c for c in final if c.kind == "break"]
    corrections = [c for c in final if c.kind == "correction"]

    effective_maps, correction_notes = _apply_corrections(presence, corrections, members)

    alternatives: list[Alternative] = []
    if attendance_status == "established" and attendance != "attended":
        duration_status = "not_applicable"
    elif not presence or not effective_maps:
        duration_status = "unknown"
    else:
        seen: set[tuple[int, str]] = set()
        for effective in effective_maps:
            for alt in _duration_alternatives(presence, breaks, effective):
                key = (alt.minutes, alt.derivation)
                if key not in seen:
                    seen.add(key)
                    alternatives.append(alt)
        if len({a.minutes for a in alternatives}) > 1 or len(effective_maps) > 1:
            duration_status = "disputed"
        elif correction_notes:
            duration_status = "corrected"
        else:
            duration_status = "established"

    if presence:
        if len(effective_maps) == 1:
            by_source: dict[int, list[Span]] = defaultdict(list)
            for p in presence:
                by_source[p.extraction_id].append(effective_maps[0][p.id])
            accounts = {_merge(spans) for spans in by_source.values()}
            for p in presence:
                note = "; ".join(correction_notes.get(p.id, [])) or None
                if len(accounts) > 1:
                    members[p.id] = ("disputed", note)
                elif p.id in correction_notes:
                    members[p.id] = ("corrected", note)
                else:
                    members[p.id] = ("accepted", note)
        else:
            for p in presence:
                note = "; ".join(correction_notes.get(p.id, [])) or None
                members[p.id] = ("disputed", note)
    for b in breaks:
        members.setdefault(b.id, ("accepted", None))

    return Resolution(detail_status, stored_date, stored_type, attendance_status, attendance,
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
    if db.execute("SELECT 1 FROM extractions x WHERE version=? AND NOT EXISTS "
                  "(SELECT 1 FROM extraction_seals s WHERE s.extraction_id=x.id)", (version,)).fetchone():
        raise ValueError("unsealed extractions cannot be reconciled; rebuild from source")
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
        db.execute("INSERT INTO reconciliation_seals(run_id) VALUES (?)", (run_id,))
    return run_id
