param([switch]$Live)
$ErrorActionPreference = 'Stop'
python -m pip install -e '.[dev]'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($Live) { python scripts/run_pipeline.py --live }
else { python scripts/run_pipeline.py }
exit $LASTEXITCODE
