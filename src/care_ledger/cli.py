from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import replace
from datetime import date
from pathlib import Path

from .benchmark import run_benchmark
from .config import load_settings
from .db import ingest_directory, open_db
from .extract import extract_pending
from .models import Patient
from .persist import persist_fixtures
from .queries import QUERIES, run_query
from .reconcile import reconcile
from .report import write_report

log = logging.getLogger("care_ledger")


def _dump(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))


def _parser(settings) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="care-ledger", description="Auditable clinical abstraction")
    p.add_argument("--db", type=Path, default=settings.database_path)
    p.add_argument("--version", dest="extraction_version", default=settings.extraction_version,
                   help="extraction version to write or query (default: %(default)s)")
    sub = p.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="register new documents (content-addressed)")
    ingest.add_argument("directory", type=Path)

    extract = sub.add_parser("extract", help="extract claims from documents not yet extracted, then reconcile")
    extract.add_argument("--workers", type=int, default=8)

    load = sub.add_parser("load-fixtures", help="persist fixture claims through the same writer, then reconcile")
    load.add_argument("fixtures", type=Path, nargs="?", default=Path("tests/fixtures/fixture_extractions.json"))
    load.add_argument("--documents", type=Path, default=Path("documents"))
    load.add_argument("--patient-mrn", default="HG-M042")
    load.add_argument("--patient-name", default="Rowan Mercer")
    load.add_argument("--birth-date", default="1991-04-12")

    sub.add_parser("reconcile", help="rebuild resolutions from saved claims as a new run")
    sub.add_parser("status", help="show ingestion, extraction and reconciliation state")

    query = sub.add_parser("query", help="answer a question from the saved abstraction")
    query.add_argument("name", choices=sorted(QUERIES))
    query.add_argument("--patient", help="MRN or full name; omit for collection-wide compliance")
    query.add_argument("--start", type=date.fromisoformat)
    query.add_argument("--end", type=date.fromisoformat)
    query.add_argument("--date", dest="dates", action="append", type=date.fromisoformat)
    query.add_argument("--encounter")

    report = sub.add_parser("report", help="answer questions.json using question_parameters.json")
    report.add_argument("--questions", type=Path, default=Path("questions.json"))
    report.add_argument("--parameters", type=Path, default=Path("question_parameters.json"))
    report.add_argument("--out", type=Path, default=Path("artifacts"))

    bench = sub.add_parser("benchmark", help="measure the saved abstraction and query latency")
    bench.add_argument("--patient", required=True)
    bench.add_argument("--start", type=date.fromisoformat, required=True)
    bench.add_argument("--end", type=date.fromisoformat, required=True)
    bench.add_argument("--date", dest="dates", action="append", type=date.fromisoformat, required=True)
    bench.add_argument("--out", type=Path, default=Path("artifacts/benchmark.json"))
    return p


def _status(db, version: str) -> dict:
    scalar = lambda sql, *a: db.execute(sql, a).fetchone()[0]
    run = db.execute("SELECT * FROM reconciliation_runs WHERE extraction_version = ? ORDER BY id DESC LIMIT 1",
                     (version,)).fetchone()
    latest = scalar("SELECT max(id) FROM extractions WHERE version = ?", version)
    return {
        "extraction_version": version,
        "documents": scalar("SELECT count(*) FROM documents"),
        "document_sources": scalar("SELECT count(*) FROM document_sources"),
        "extracted": scalar("SELECT count(*) FROM extractions WHERE version = ?", version),
        "failed_model_calls": scalar("SELECT count(*) FROM model_calls WHERE status = 'failed' AND extraction_version = ?", version),
        "assertions": scalar("SELECT count(*) FROM assertions a JOIN extractions x ON x.id = a.extraction_id WHERE x.version = ?", version),
        "latest_reconciliation_run": run["id"] if run else None,
        "abstraction_current": bool(run) and latest == run["through_extraction_id"],
    }


def _query_params(args) -> dict:
    return {k: getattr(args, k) for k in ("patient", "start", "end", "dates", "encounter") if getattr(args, k)}


def main(argv: list[str] | None = None) -> int:
    settings = load_settings()
    args = _parser(settings).parse_args(argv)
    args.db.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.StreamHandler(sys.stderr),
                  logging.FileHandler(args.db.with_name(args.db.stem + ".log"), encoding="utf-8", delay=True)],
    )
    db = open_db(args.db)
    version = args.extraction_version
    settings = replace(settings, extraction_version=version)
    try:
        if args.command == "ingest":
            result = ingest_directory(db, args.directory)
            log.info("ingest %s: added=%d duplicates=%d", args.directory, result.added, result.duplicates)
            _dump({"added": result.added, "duplicates": result.duplicates})
        elif args.command == "extract":
            summary = extract_pending(db, settings, args.workers)
            log.info("extract version=%s model=%s effort=%s pending=%d succeeded=%d failed=%d elapsed=%.1fs",
                     version, settings.model, settings.reasoning_effort, summary.pending,
                     summary.succeeded, len(summary.failed), summary.elapsed_s)
            if summary.succeeded:
                run_id = reconcile(db, version)
                log.info("reconcile run=%d", run_id)
            if summary.failed:
                _dump({"failed": summary.failed, **_status(db, version)})
                return 1
            _dump(_status(db, version))
        elif args.command == "load-fixtures":
            fixtures = json.loads(args.fixtures.read_text(encoding="utf-8"))
            patient = Patient(mrn=args.patient_mrn, name=args.patient_name,
                              birth_date=date.fromisoformat(args.birth_date))
            persisted, skipped = persist_fixtures(
                db, args.documents, fixtures, patient=patient, version=version, producer="fixture"
            )
            log.info("load-fixtures persisted=%d skipped=%d version=%s", persisted, skipped, version)
            if persisted or skipped:
                run_id = reconcile(db, version)
                log.info("reconcile run=%d", run_id)
            _dump({"persisted": persisted, "skipped": skipped, **_status(db, version)})
        elif args.command == "reconcile":
            run_id = reconcile(db, version)
            log.info("reconcile run=%d", run_id)
            _dump(_status(db, version))
        elif args.command == "status":
            _dump(_status(db, version))
        elif args.command == "query":
            result = run_query(db, version, args.name, **_query_params(args))
            _dump(result)
        elif args.command == "report":
            path = write_report(db, version, args.questions, args.parameters, args.out)
            log.info("report written to %s", path)
        elif args.command == "benchmark":
            result = run_benchmark(db, args.db, version, args.patient, args.start, args.end, args.dates)
            args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
            log.info("benchmark written to %s", args.out)
            _dump(result)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
