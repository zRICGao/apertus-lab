Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$env:LLM_BASE_URL = 'https://api.inference.cscs.ch/v1'
$secureKey = Read-Host 'CSCS Inference API key (input is hidden)' -AsSecureString
$credential = [System.Net.NetworkCredential]::new('', $secureKey)
$env:LLM_API_KEY = $credential.Password
Remove-Variable credential, secureKey

$headers = @{ Authorization = "Bearer $env:LLM_API_KEY" }
$models = Invoke-RestMethod -Uri "$env:LLM_BASE_URL/models" `
    -Headers $headers -Method Get -TimeoutSec 30

$apertusModels = @($models.data | Where-Object { $_.id -match 'Apertus' } | Select-Object -ExpandProperty id)
if ($apertusModels.Count -eq 0) {
    Write-Warning 'The endpoint returned no Apertus model IDs. Check project access and current model availability.'
} else {
    Write-Host 'Apertus model IDs returned by CSCS:'
    $apertusModels | ForEach-Object { Write-Host "  $_" }
}

$targetId = 'swiss-ai/Apertus-v1.5-70B'
if ($apertusModels -contains $targetId) {
    $env:LLM_NAME = $targetId
    Write-Host "Configured this PowerShell session for $targetId. No generation request was sent."
} else {
    Remove-Item Env:LLM_NAME -ErrorAction SilentlyContinue
    Write-Warning "The exact target '$targetId' is not in the returned list; LLM_NAME was left unset."
}

Write-Host "Base URL: $env:LLM_BASE_URL"
Write-Host 'API key remains hidden in this PowerShell process only.'
