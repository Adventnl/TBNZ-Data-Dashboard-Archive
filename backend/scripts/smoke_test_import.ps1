param(
    [string]$ApiBase = "http://localhost:8000",
    [string]$ExcelPath = "../data/sample_import.xlsx",
    [string]$PythonExe = "venv/Scripts/python.exe"
)

$ErrorActionPreference = "Stop"

$backendRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $backendRoot

if (-not (Test-Path $PythonExe)) {
    throw "Python not found: $PythonExe"
}

if (-not (Test-Path $ExcelPath)) {
    Write-Output "Sample Excel not found. Generating..."
    & $PythonExe "scripts/generate_sample_excel.py"
}

Write-Output "Inspecting sample Excel..."
& $PythonExe "scripts/inspect_excel.py" $ExcelPath

$healthUri = "$ApiBase/api/health"
Write-Output "Checking API health: $healthUri"
try {
    $health = Invoke-RestMethod -Method Get -Uri $healthUri -TimeoutSec 8
    Write-Output ("Health: " + ($health | ConvertTo-Json -Compress))
} catch {
    throw "Health check failed. Please start backend first: uvicorn app.main:app --reload --port 8000"
}

Write-Output "Uploading sample Excel..."
$fileItem = Get-Item $ExcelPath

$curl = Get-Command curl.exe -ErrorAction SilentlyContinue
if (-not $curl) {
    throw "curl.exe not found. Install curl or run this script in PowerShell 7+ with form upload support."
}

$uploadUrl = "$ApiBase/api/import/upload"
$rawResponse = & curl.exe -s -X POST -F "file=@$($fileItem.FullName)" $uploadUrl
if ($LASTEXITCODE -ne 0) {
    throw "Upload failed: curl exited with code $LASTEXITCODE"
}

try {
    $result = $rawResponse | ConvertFrom-Json
} catch {
    throw "Upload failed: non-JSON response: $rawResponse"
}

Write-Output "Import result:"
$result | ConvertTo-Json -Depth 10

if ($result.PSObject.Properties.Name -contains "detail") {
    throw "Import API error: $($result.detail)"
}

if (-not ($result.PSObject.Properties.Name -contains "status")) {
    throw "Import response missing status field"
}

if ($result.status -eq "failed") {
    throw "Import status is failed"
}

Write-Output "Smoke test passed."
