from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

from .queries import run_query


def _range(r: dict | None) -> str:
    if r is None:
        return "-"
    if r["max"] is None:
        return f">={r['min']}"
    return str(r["min"]) if r["min"] == r["max"] else f"{r['min']}-{r['max']}"


def _quote(evidence: list[dict]) -> str:
    return "; ".join(f"\"{' '.join(e['quote'].split())}\" ({e['document']} {e['chars'][0]}-{e['chars'][1]})"
                     for e in evidence)


def _encounter_rows(rows: list[dict]) -> list[str]:
    lines = ["| Encounter | Date | Service | Minutes | Basis | Sources |", "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['encounter']} | {r['date']} | {r['service_type']} | {_range(r['minutes'])} | "
                     f"{'<br>'.join(r['derivations']) or r['duration_status']} | {', '.join(r['documents'])} |")
    return lines


def render_attendance(a: dict) -> list[str]:
    types = ", ".join(f"{t.replace('_therapy', '')} {_range(v['sessions'])}" for t, v in a["by_service_type"].items())
    lines = [f"**{_range(a['sessions'])} therapy sessions** ({types}) on **{_range(a['distinct_therapy_days'])} "
             f"distinct days**, {_range(a['minutes'])} minutes.", "", *_encounter_rows(a["included"]), ""]
    lines.append("Encounters documented by several sources are counted once; their sources are listed together.")
    if a["excluded"]:
        lines += ["", "**Excluded:**"]
        lines += [f"- {r['encounter']} ({r['date']}, {r['service_type']}): {r['reason']}. Sources: "
                  f"{', '.join(r['documents'])}" for r in a["excluded"]]
    for key, label in (("undetermined", "Undetermined"), ("unplaced", "Without an established date")):
        if a[key]:
            lines += ["", f"**{label}:**"] + [f"- {r['encounter']}: {r['reason']}" for r in a[key]]
    return lines


def render_minutes(m: dict) -> list[str]:
    lines = [f"**{_range(m['minutes'])} minutes** ({_range(m['hours'])} hours).", "",
             "| Week of | Reviewed | Minutes | Encounters |", "|---|---|---|---|"]
    for w in m["weeks"]:
        encounters = ", ".join(f"{e['encounter']} ({_range(e['minutes'])})" for e in w["encounters"])
        partial = " (partial)" if w["partial_week"] else ""
        lines.append(f"| {w['week_of']} | {w['reviewed'][0]} to {w['reviewed'][1]}{partial} | "
                     f"{_range(w['minutes'])} | {encounters} |")
    if m["unresolved"]:
        lines += ["", "**Not settled by the record:**"]
        for r in m["unresolved"]:
            lines.append(f"- {r['encounter']} ({r['date']}): {_range(r['minutes'])} minutes, "
                         f"{r['duration_status']}. Alternatives: {' | '.join(r['derivations'])}. "
                         f"Sources: {', '.join(r['documents'])}")
    return lines


def render_compliance(c: dict) -> list[str]:
    lines = []
    for p in c["patients"]:
        for plan in p["plans"]:
            lines.append(f"**Goal** ({plan['start']} to {plan['end']}): at least {plan['min_days']} therapy days and "
                         f"{plan['min_minutes']} minutes per Monday-Sunday week; counted services: "
                         f"{', '.join(plan['services'])}. Source: " + "; ".join(f"\"{q}\"" for q in plan["evidence"]))
        lines += ["", "| Week of | Reviewed | Therapy days | Minutes | Result | Depends on |", "|---|---|---|---|---|---|"]
        for w in p["weeks"]:
            lines.append(f"| {w['week_of']} | {w['reviewed'][0]} to {w['reviewed'][1]} | "
                         f"{_range(w.get('therapy_days'))} | {_range(w.get('minutes'))} | {w['status']} | "
                         f"{', '.join(w.get('depends_on', [])) or w.get('reason', '')} |")
        below = p["consecutive_weeks_below_goal"]
        lines += ["", f"Consecutive weeks below goal: definite {below['definite'] or 'none'}; "
                      f"dependent on unresolved documentation {below['depends_on_unresolved'] or 'none'}."]
    return lines


def render_days(d: dict) -> list[str]:
    lines = []
    for day in d["days"]:
        lines += [f"### {day['date']}: {_range(day['therapy_contacts'])} therapy contact(s), "
                  f"{_range(day['minutes'])} minutes", ""]
        for e in day["encounters"]:
            lines.append(f"**{e['encounter']}** ({e['service_type']}, {e['status']}: {e['reason']}); "
                         f"duration {e['duration_status']}: {' | '.join(e['derivations']) or '-'}")
            for c in e["claims"]:
                note = f" ({c['note']})" if c["note"] else ""
                value = ", ".join(f"{k}={v}" for k, v in c["value"].items())
                lines.append(f"- {c['role']}{note}: {c['kind']} {value} [{c['source_status']}, authored "
                             f"{c['authored_on']}] {_quote(c['evidence'])}")
            lines.append("")
    return lines


def render_progress(p: dict) -> list[str]:
    lines = ["| Instrument | Completed | Score | Status | Sources |", "|---|---|---|---|---|"]
    for a in p["assessments"]:
        sources = "<br>".join(_quote(s["evidence"]) for s in a["sources"])
        lines.append(f"| {a['instrument']} | {a['completed_on']} | {a['score']} | {a['status']} "
                     f"({a['source_documents']} document(s)) | {sources} |")
    for instrument, t in p["trend"].items():
        points = " -> ".join(f"{x['score']} ({x['completed_on']})" for x in t["points"])
        lines += ["", f"{instrument}: {points}; change first to last: {t['change_first_to_last']}."]
    lines += ["", "**Documented observations:**"]
    for o in p["observations"]:
        encounter = f" {o['encounter']}" if o["encounter"] else ""
        lines.append(f"- {o['date']}{encounter} [{o['reporter']} / {o['category']}] {o['statement']} "
                     f"{_quote(o['evidence'])}")
    lines += ["", "**Limits:**"] + [f"- {limit}" for limit in p["limits"]]
    return lines


RENDERERS = {"attendance": render_attendance, "minutes": render_minutes, "compliance": render_compliance,
             "days": render_days, "progress": render_progress}


def _params(spec: dict) -> dict:
    params = {k: v for k, v in spec.items() if k != "query"}
    for key in ("start", "end"):
        if key in params:
            params[key] = date.fromisoformat(params[key])
    if "dates" in params:
        params["dates"] = [date.fromisoformat(d) for d in params["dates"]]
    return params


def write_report(db: sqlite3.Connection, version: str, questions: Path, parameters: Path, out_dir: Path) -> Path:
    asked = {q["id"]: q["question"] for q in json.loads(questions.read_text(encoding="utf-8-sig"))}
    specs = json.loads(parameters.read_text(encoding="utf-8"))
    results = {qid: run_query(db, version, spec["query"], **_params(spec)) for qid, spec in specs.items()}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "answers.json").write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    abstraction = next(iter(results.values()))["abstraction"]
    lines = ["# Answers", "",
             f"Generated from reconciliation run {abstraction['reconciliation_run']} "
             f"(extraction version `{abstraction['extraction_version']}`, "
             f"{abstraction['documents_reconciled']} documents reconciled, "
             f"{abstraction['documents_not_extracted']} not extracted). Full structured results: `answers.json`.", ""]
    for qid, spec in specs.items():
        lines += [f"## {qid}", "", f"> {asked[qid]}", "", *RENDERERS[spec["query"]](results[qid]), ""]
    path = out_dir / "answers.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
