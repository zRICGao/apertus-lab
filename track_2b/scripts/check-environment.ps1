$ErrorActionPreference = 'Continue'
$projectRoot = Split-Path $PSScriptRoot -Parent
$evidenceDir = Join-Path $projectRoot 'management/evidence'
New-Item -ItemType Directory -Path $evidenceDir -Force | Out-Null
$reportPath = Join-Path $evidenceDir 'environment.txt'
$report = [System.Collections.Generic.List[string]]::new()
$report.Add('Apertus Lab environment inventory')
$report.Add('Captured UTC: ' + [DateTime]::UtcNow.ToString('o'))
$report.Add('PowerShell: ' + $PSVersionTable.PSVersion.ToString())
foreach ($toolName in @('git', 'bun', 'python', 'node', 'npm', 'docker', 'wsl')) {
    $report.Add("`n[$toolName]")
    $toolCommand = Get-Command $toolName -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $toolCommand) {
        $report.Add('NOT FOUND in current PATH')
        continue
    }
    $report.Add('Path: ' + $toolCommand.Source)
    $versionOutput = & $toolCommand.Source --version 2>&1
    $toolExitCode = $LASTEXITCODE
    $report.Add(($versionOutput | Out-String).Trim())
    $report.Add('Exit code: ' + $toolExitCode)
}
if (Get-Command docker -ErrorAction SilentlyContinue) {
    $report.Add("`n[Docker server OS]")
    $dockerOutput = docker info --format '{{.OSType}}' 2>&1
    $dockerExitCode = $LASTEXITCODE
    $report.Add(($dockerOutput | Out-String).Trim())
    $report.Add('Exit code: ' + $dockerExitCode)
}
if (Get-Command wsl -ErrorAction SilentlyContinue) {
    $report.Add("`n[WSL distributions]")
    $wslOutput = wsl --list --verbose 2>&1
    $wslExitCode = $LASTEXITCODE
    $report.Add((($wslOutput | Out-String) -replace "`0", '').Trim())
    $report.Add('Exit code: ' + $wslExitCode)
}
$report | Set-Content -LiteralPath $reportPath -Encoding utf8
$report
Write-Output "`nSaved: $reportPath"
