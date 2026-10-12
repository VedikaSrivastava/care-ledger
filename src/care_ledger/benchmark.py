from __future__ import annotations

import sqlite3
import statistics
import time
from datetime import datetime, timedelta
from pathlib import Path

from .extract import estimate_cost, PRICING_SNAPSHOT, PRICING_PER_MILLION
from .queries import current_run, run_query


def _latency(fn, runs: int) -> dict:
    samples = []
    for _ in range(runs):
        started = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - started) * 1000)
    samples.sort()
    return {"runs": runs, "median_ms": round(statistics.median(samples), 2),
            "p95_ms": round(samples[int(0.95 * (runs - 1))], 2), "max_ms": round(samples[-1], 2)}


def _extraction(db: sqlite3.Connection, version: str) -> dict:
    calls = db.execute("SELECT * FROM model_calls WHERE extraction_version = ?", (version,)).fetchall()
    if not calls:
        return {"model_calls": 0}
    starts = [datetime.fromisoformat(c["started_at"]) for c in calls]
    ends = [s + timedelta(milliseconds=c["elapsed_ms"]) for s, c in zip(starts, calls)]
    tokens = {k: sum(c[k] or 0 for c in calls)
              for k in ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_tokens")}
    costs = [estimate_cost(c["model"], c["input_tokens"], c["cached_input_tokens"], c["output_tokens"])
             for c in calls]
    missing = sum(v is None for v in costs)
    return {
        "model_calls": len(calls),
        "failed_calls": sum(c["status"] == "failed" for c in calls),
        "models": sorted({f"{c['model']} (reasoning {c['reasoning_effort']})" for c in calls}),
        "wall_clock_s": round((max(ends) - min(starts)).total_seconds(), 1),
        "summed_call_s": round(sum(c["elapsed_ms"] for c in calls) / 1000, 1),
        "tokens": tokens,
        "usage_missing_calls": sum(c["input_tokens"] is None or c["output_tokens"] is None for c in calls),
        "tokens_are_known_subtotals": any(c[k] is None for c in calls for k in tokens),
        "unpriced_calls": missing,
        "estimated_cost_usd": None if missing else round(sum(costs), 6),
        "known_cost_subtotal_usd": round(sum(v for v in costs if v is not None), 6),
        "pricing_snapshot": PRICING_SNAPSHOT | {"rates_per_million": PRICING_PER_MILLION},
        "sdk_retries": 0,
    }


def run_benchmark(db: sqlite3.Connection, db_path: Path, version: str, patient: str, start, end, dates,
                  runs: int = 30) -> dict:
    run = current_run(db, version)
    documents = db.execute("SELECT count(*), sum(length(CAST(content AS BLOB))) FROM documents").fetchone()
    patient_queries = {
        "attendance": dict(patient=patient, start=start, end=end),
        "minutes": dict(patient=patient, start=start, end=end),
        "compliance_patient": dict(patient=patient, start=start, end=end),
        "days": dict(patient=patient, dates=dates),
        "progress": dict(patient=patient, start=start, end=end),
    }
    latency = {
        name: _latency(lambda n=name, p=params: run_query(db, version, n.removesuffix("_patient"), persist=False, **p), runs)
        for name, params in patient_queries.items()
    }
    latency["compliance_collection"] = _latency(
        lambda: run_query(db, version, "compliance", persist=False, start=start, end=end), runs)
    return {
        "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "documents": {"count": documents[0], "bytes": documents[1]},
        "extraction": _extraction(db, version),
        "reconciliation_ms": round(run["elapsed_ms"], 2),
        "query_latency": latency,
        "database_bytes": db_path.stat().st_size,
    }
