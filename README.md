# Care Ledger

A Python/SQLite abstraction for one outpatient episode. Documents become evidence-backed claims; claims are reconciled into encounters; answers are calculated from those resolutions. The LLM extracts claims. Python counts sessions, subtracts breaks, applies corrections, and classifies weekly goals.

There is one write path. Reviewed JSON and live model output both go through `persist_extraction` → `reconcile` → `queries`.

## Setup

Python 3.11+. Copy `.env.example` to `.env` and set `OPENAI_API_KEY` only if you want live extraction.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
./scripts/run_pipeline.ps1
```

The script builds `artifacts/reviewed.sqlite` from the 31 local records and `tests/fixtures/reviewed_extractions.json`, writes `artifacts/answers.md`, measures query latency, and runs `pytest`.

Manual equivalent:

```powershell
care-ledger --db artifacts/reviewed.sqlite --version reviewed ingest documents
care-ledger --db artifacts/reviewed.sqlite --version reviewed load-reviewed
care-ledger --db artifacts/reviewed.sqlite --version reviewed report
care-ledger --db artifacts/reviewed.sqlite --version reviewed query attendance --patient HG-M042 --start 2026-01-05 --end 2026-01-30
```

Live extraction of documents not yet extracted for a version:

```powershell
care-ledger --db artifacts/care_ledger.sqlite ingest documents
care-ledger --db artifacts/care_ledger.sqlite --version llm-v1 extract
```

`extract` records every model call, rejects quotes that are missing or ambiguous, retries evidence failures once, and reconciles whatever persisted. A second extract of the same `(document, version)` is a no-op. Byte-identical files reuse the stored document.

## What the abstraction does

Eligible therapy is patient-present individual, group, or family psychotherapy. Minutes are presence intervals minus overlapping breaks. Several notes about one encounter stay one encounter.

Observed cases:

- January 19 group: explicit departure correction 11:30 → 11:15; the later resent roster repeats the original and does not undo the correction; the activity note supplies the 15-minute break → 60 minutes.
- January 19 individual after group is a second encounter (30 minutes).
- January 21 telehealth: two connection intervals, one encounter; the disconnected 10 minutes do not count → 45 minutes.
- January 26: two full-contact intervals (50 vs 40) remain alternatives. Totals keep both. They are not averaged and fields are not mixed across accounts.
- January 27 draft attendance text and a posted charge do not establish care; the signed no-show does.
- January 30 family: count the 30 minutes Rowan was present, not the therapist's full 45.
- January 16 PHQ-9 imported on January 26 is one assessment.

Drafts, charges, authorizations, medication-only visits, partner-only collateral, care coordination, cancellations, and no-shows stay in the ledger with an exclusion reason.

## Results (reviewed extraction)

12 eligible encounters on 11 days: individual 5 (210–220 min), group 5 (300 min), family 2 (75 min), total 585–595 min. Monday–Sunday weeks from January 5: 140, 120, 180, and 145–155 minutes on 3, 2, 3, and 3 therapy days. Against the signed goal (≥3 days and ≥150 minutes), the weeks are not met, not met, met, and cannot determine. The last week is a partial week through January 30; the duration dispute on HG-E115 is the only reason it is indeterminate. The first two weeks are consecutive below-goal weeks regardless.

PHQ-9: 18 (Jan 5), 14 (Jan 16), 10 (Jan 30). See [answers.md](artifacts/answers.md).

## Design decision tested

An encounter is one event with many claims, not one row per note. That is what keeps co-facilitator notes, reconnects, and retransmitted rosters from inflating counts while still leaving Jan 26 unresolved. Finalized assertions and published resolutions are append-only (SQLite triggers). Corrections replace one recorded clock time on claims authored on or before the correction; receipt order is not precedence. Unknown is null, not zero.

## Limitation

The brief mentions multiple patients, inpatient care, and mid-episode plan amendments. The supplied records are one outpatient patient and one effective plan. The schema keeps patient identity and effective-dated requirements; cohort analysis and prorating a midweek amendment are not demonstrated because the documents do not support them.

## Scale

Measured on this corpus after `load-reviewed` (31 documents, 50,137 bytes; saved database 348 KiB): reconciliation 0.73 ms; question latency median 0.20–0.36 ms (30 warm runs). No model call occurred on the reviewed path, so usage and cost are unknown, not $0. Live extraction records tokens and estimated cost on `model_calls`.

At 500k–1M documents the first cost is per-document model extraction, then SQLite's single writer. I would queue work by content hash, cache `(sha256, extraction_version)`, and move write-heavy tables to PostgreSQL. Those last sentences are estimates, not measurements from this corpus.

Pricing snapshot 2026-10-11: GPT-5.4 mini $0.75 / $0.075 / $4.50 per million input / cached input / output tokens. Cached input is a subset of input; reasoning tokens are a subset of output.

## Disclosure

All 31 Drive records are in `documents/`. Reviewed claims are independently authored JSON, not answers hardcoded into query logic. AI coding assistance was used to implement the prototype.
