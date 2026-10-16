$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$env:PYTHONPATH = Join-Path $projectRoot 'track_2b/src'
$env:PYTHONIOENCODING = 'utf-8'
Push-Location $projectRoot
try {
    python scripts/extract_breachweave.py --check
    if ($LASTEXITCODE -ne 0) { throw 'Asset verification failed' }
    & ./.tools/node_modules/.bin/bun.cmd test ./workbench/apertus-workbench/tests
    if ($LASTEXITCODE -ne 0) { throw 'Workbench tests failed' }
    python -m unittest discover -s experiments/tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Experiment tests failed' }
    python scripts/smoke_foundation.py
    if ($LASTEXITCODE -ne 0) { throw 'Cross-runtime smoke failed' }
    python scripts/smoke_mvp.py
    if ($LASTEXITCODE -ne 0) { throw 'MVP package smoke failed' }
} finally {
    Pop-Location
}
