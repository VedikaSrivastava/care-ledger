param([switch]$Live, [switch]$Resume)
$ErrorActionPreference = 'Stop'
python -m pip install -e '.[dev]'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$pipelineArgs = @('scripts/run_pipeline.py')
if ($Live) { $pipelineArgs += '--live' }
if ($Resume) { $pipelineArgs += '--resume' }
python @pipelineArgs
exit $LASTEXITCODE
