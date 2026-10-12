# Care Ledger

Clinical abstraction prototype for the Backbone take-home. Documents are ingested into SQLite, extracted into typed evidence-backed claims, reconciled into encounters, and answered with deterministic Python calculations.

Pipeline: `ingest` → claim source → `reconcile` → `query` / `report`.

### Why two claim sources

The model does the clinical reading. Reconcile and calculate are ordinary code on whatever claims were saved. Those are separate jobs, so the claim source is swappable:

| Source | CLI | Role |
|---|---|---|
| Fixture claims | `--version fixture` + `load-fixtures` | Hand-authored evidence-backed claims in `tests/fixtures/fixture_extractions.json`. Offline, free, deterministic for tests and the default report. |
| Live extraction | `--version llm-v2` + `extract` | Same claim schema, filled by the model from each document. Required for the live path: cost, latency, and a check that extraction reaches the same clinical totals. |

Answers are never hardcoded into the calculators; both paths write claims into the same tables and share reconcile/query.

## Setup

Python 3.11+.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
# Set OPENAI_API_KEY for live extraction.
./scripts/run_pipeline.ps1
```

`run_pipeline.ps1` runs the tests and builds a fresh fixture database before publishing the complete results. The cross-platform equivalent is `python scripts/run_pipeline.py`.

For a fresh live run, keep `OPENAI_API_KEY` in your ignored `.env` file and run:

```powershell
python scripts/run_pipeline.py --live
# Or: ./scripts/run_pipeline.ps1 -Live
```

This publishes `artifacts/live/live.sqlite`, `answers.md`, `answers.json`, `benchmark.json`, and `execution.log`. It starts from an empty database with extraction version `llm-v2`. Existing results remain untouched if a command fails. Commit the complete directory after reviewing the live answers. Every model attempt from the final run remains in the database, including repair attempts, because those tokens and costs belong to the run. Old runs are not carried forward.

### Process documents and answer questions

```powershell
# Fixture claims (offline, reproducible)
care-ledger --db artifacts/fixture.sqlite --version fixture ingest documents
care-ledger --db artifacts/fixture.sqlite --version fixture load-fixtures
care-ledger --db artifacts/fixture.sqlite --version fixture report

# Live model extraction
care-ledger --db artifacts/care_ledger.sqlite --version llm-v2 ingest documents
care-ledger --db artifacts/care_ledger.sqlite --version llm-v2 extract

# New questions reuse the saved abstraction after restart
care-ledger --db artifacts/fixture.sqlite --version fixture query attendance --patient HG-M042 --start 2026-01-05 --end 2026-01-30
care-ledger --db artifacts/fixture.sqlite --version fixture query compliance --patient HG-M042 --start 2026-01-05 --end 2026-01-30
```

Byte-identical files are deduplicated by content hash. Successful extractions are cached per `(document, extraction_version)`. Evidence quotes must occur verbatim and uniquely in the source document.

## Approach

Eligible therapy is patient-present individual, group, or family psychotherapy. Session minutes are presence intervals minus overlapping nontherapeutic breaks. Multiple documents about one encounter contribute claims to one encounter record.

Reconciliation rules that matter for this corpus:

- Explicit corrections replace a specific arrival or departure time on claims authored on or before the correction. A later resent copy of the original roster does not undo the correction.
- Correction chains follow explicit replaced values and authorship cutoffs. Competing replacements remain alternatives; cycles or jointly invalid endpoints leave duration unknown. Document order is not precedence.
- Presence and break intervals from the same source stay correlated; accounts are not crossed arbitrarily.
- Service date and type are resolved independently. Disputed dates remain in window calculations: an encounter contributes definitely when every candidate date is inside the window and possibly when only some are. Distinct days count date assignments without counting one encounter twice.
- Draft notes, charges, authorizations, medication-only visits, patient-absent collateral, care coordination, cancellations, and no-shows remain in the ledger with exclusion reasons.
- Assessments with the same source form identifier share one assessment; imports are additional sources. Results without a form identifier are not merged across documents.
- If any ingested document has not been extracted, answers are marked provisional and definitive plan-compliance labels are withheld.

Clock fields require `HH:MM`; offsets, ranges, and seconds are rejected rather than silently stripped. Schema or evidence failures receive one recorded repair attempt.

Extractions are sealed only after their assertions and plans have evidence. Sealed extractions and reconciliations reject additional child rows as well as updates/deletes. Older unsealed databases must be rebuilt from source for this prototype; migration support is outside this change.

Unknown is stored as null, not zero. Numerical answers are computed in code from saved resolutions.

## Design decision tested

Represent each service as one encounter with many claims, not one row per note.

That prevents co-facilitator notes, telehealth reconnects, and retransmitted rosters from inflating session counts, while still preserving the January 26 duration disagreement as correlated alternatives (40 vs 50 minutes) instead of averaging or silently picking a winner.

## Results

Full answers with sources: [artifacts/answers.md](artifacts/answers.md).

For Rowan Mercer (HG-M042), January 5–30:

- 12 eligible therapy encounters on 11 distinct days
- Individual 5 (210–220 min), group 5 (300 min), family 2 (75 min)
- Total 585–595 minutes (9.75–9.92 hours)
- Weekly minutes (Monday–Sunday): 140, 120, 180, 145–155
- Plan goal (≥3 therapy days and ≥150 minutes): not met, not met, met, cannot determine
- Two consecutive below-goal weeks: January 5 and January 12
- PHQ-9: 18 (Jan 5), 14 (Jan 16), 10 (Jan 30); the January 26 import is not a fourth assessment

Hard cases handled: January 19 correction and resent roster; January 21 disconnect/reconnect; January 26 unresolved duration; January 27 draft/charge vs signed no-show; January 30 partial family attendance.

## Observed limitation

The assignment overview describes multiple patients, inpatient care, and treatment-plan amendments. The supplied records cover one outpatient patient and one effective plan. The schema retains patient identity and effective-dated requirements, but cohort analysis and before/after plan-change comparison are not demonstrated on this dataset. Next step: add a parameterized plan-change query and synthetic multi-patient fixtures, without inventing a clinical prorating rule for midweek amendments.

## Performance

Fresh offline verification on the supplied 31 documents (50,137 bytes): all 47 tests pass. See the committed benchmark for fresh processing time, checkpointed database size, and query latency measured on this machine.

Reproducible evidence: [database](artifacts/fixture.sqlite), [answers](artifacts/answers.json), [benchmark](artifacts/benchmark.json), and [execution log](artifacts/execution.log). `reconciliation_ms` measures resolution computation before persistence; `fresh_processing_wall_s` measures the complete fresh processing step through CLI exit.

**Live verification is pending.** No API key was available for this revision. The earlier standalone live benchmark was removed because its database and answers were unavailable for independent verification. No live accuracy or cost claim is made for this revision; use the fresh live command above to produce that evidence.

Cost estimates use a configured pricing snapshot dated 2026-10-11 ([pricing source](https://developers.openai.com/api/docs/models/gpt-5.4-mini)): $0.75 / $0.075 / $4.50 per million input / cached input / output tokens, standard tier. Rates are not fetched automatically; verify/update the snapshot before a live benchmark. Each call is priced separately. Missing usage or an unpriced model leaves total cost unknown, with a separately labeled known subtotal. Cached input is a subset of input; reasoning is a subset of output, so neither is charged twice. Usage is captured before local validation, and SDK retries are disabled so repair calls are individually recorded.

At 500k–1M documents, the first bottleneck is per-document model extraction (cost and latency) in `extract.py`, then SQLite’s single-writer ingest path. Planned changes: queue by content hash, cache `(sha256, extraction_version)`, and move write-heavy tables to PostgreSQL. Those scale remarks are estimates, not measurements from this corpus.

## Disclosure

Source records are under `documents/`. Fixture claims are independently authored for offline evaluation; answers are not hardcoded into calculation logic. AI coding assistance (Cursor and Codex) was used while building and reviewing the prototype.
