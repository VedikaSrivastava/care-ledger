$ErrorActionPreference = 'Stop'

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python 3.11+ is required and was not found on PATH.'
}

python -m pip install -e '.[dev]'

$reviewed = 'artifacts/reviewed.sqlite'
Remove-Item -LiteralPath @(
    $reviewed, "$reviewed-wal", "$reviewed-shm",
    'artifacts/care_ledger.sqlite', 'artifacts/care_ledger.sqlite-wal', 'artifacts/care_ledger.sqlite-shm',
    'artifacts/execution.log', 'artifacts/answers.md', 'artifacts/answers.json', 'artifacts/benchmark.json'
) -ErrorAction SilentlyContinue
if (Test-Path -LiteralPath '.pytest-tmp') {
    Remove-Item -LiteralPath '.pytest-tmp' -Recurse -Force
}

python -m care_ledger.cli --db $reviewed --version reviewed ingest documents
python -m care_ledger.cli --db $reviewed --version reviewed load-reviewed
python -m care_ledger.cli --db $reviewed --version reviewed report --out artifacts
python -m care_ledger.cli --db $reviewed --version reviewed benchmark --patient HG-M042 --start 2026-01-05 --end 2026-01-30 --date 2026-01-19 --date 2026-01-21 --out artifacts/benchmark.json
python -m pytest -q

Write-Host 'Reviewed abstraction is in artifacts/reviewed.sqlite. Live extraction (optional): care-ledger --db artifacts/care_ledger.sqlite ingest documents; care-ledger extract'
