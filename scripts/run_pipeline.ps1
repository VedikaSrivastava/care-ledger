$ErrorActionPreference = 'Stop'

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw 'Python 3.11+ is required and was not found on PATH.'
}

python -m pip install -e '.[dev]'

$fixture = 'artifacts/fixture.sqlite'
Remove-Item -LiteralPath @(
    $fixture, "$fixture-wal", "$fixture-shm",
    'artifacts/reviewed.sqlite', 'artifacts/reviewed.sqlite-wal', 'artifacts/reviewed.sqlite-shm',
    'artifacts/execution.log', 'artifacts/answers.md', 'artifacts/answers.json', 'artifacts/benchmark.json'
) -ErrorAction SilentlyContinue
if (Test-Path -LiteralPath '.pytest-tmp') {
    Remove-Item -LiteralPath '.pytest-tmp' -Recurse -Force
}

python -m care_ledger.cli --db $fixture --version fixture ingest documents
python -m care_ledger.cli --db $fixture --version fixture load-fixtures
python -m care_ledger.cli --db $fixture --version fixture report --out artifacts
python -m care_ledger.cli --db $fixture --version fixture benchmark --patient HG-M042 --start 2026-01-05 --end 2026-01-30 --date 2026-01-19 --date 2026-01-21 --out artifacts/benchmark.json
python -m pytest -q

Write-Host 'Fixture abstraction is in artifacts/fixture.sqlite. Live extraction (optional): care-ledger --db artifacts/care_ledger.sqlite ingest documents; care-ledger extract'
