param(
    [string]$ApiBase = "http://localhost:8000",
    [string]$ExcelPath = "../data/sample_import_small.xlsx",
    [string]$PythonExe = "venv/Scripts/python.exe"
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Output "[SMALL-DATA] $Message"
}

function Assert-Api {
    param(
        [string]$Uri,
        [string]$Label
    )

    try {
        $resp = Invoke-RestMethod -Method Get -Uri $Uri -TimeoutSec 10
        Write-Output ("[OK] " + $Label)
        return $resp
    }
    catch {
        throw "API check failed: $Label ($Uri)"
    }
}

$backendRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $backendRoot

if (-not (Test-Path $PythonExe)) {
    throw "Python not found: $PythonExe"
}

Write-Step "Generating small test dataset..."
& $PythonExe "scripts/generate_small_test_dataset.py"

Write-Step "Inspecting generated Excel..."
& $PythonExe "scripts/inspect_excel.py" $ExcelPath

$healthUri = "$ApiBase/api/health"
Write-Step "Checking health endpoint: $healthUri"
try {
    $health = Invoke-RestMethod -Method Get -Uri $healthUri -TimeoutSec 8
    Write-Output ("Health: " + ($health | ConvertTo-Json -Compress))
}
catch {
    throw "Health check failed. Start backend first: uvicorn app.main:app --reload --port 8000"
}

Write-Step "Uploading small dataset..."
$fileItem = Get-Item $ExcelPath
$rawResponse = & curl.exe -s -X POST -F "file=@$($fileItem.FullName)" "$ApiBase/api/import/upload"
if ($LASTEXITCODE -ne 0) {
    throw "Upload failed: curl exited with code $LASTEXITCODE"
}

try {
    $importResult = $rawResponse | ConvertFrom-Json
}
catch {
    throw "Upload failed: non-JSON response: $rawResponse"
}

Write-Output "Import result:"
$importResult | ConvertTo-Json -Depth 10

if ($importResult.PSObject.Properties.Name -contains "detail") {
    throw "Import API error: $($importResult.detail)"
}
if ($importResult.status -eq "failed") {
    throw "Import status is failed"
}

Write-Step "Calling key APIs for completed modules..."
Assert-Api -Uri "$ApiBase/api/clients/overview?market=all" -Label "clients overview" | Out-Null
Assert-Api -Uri "$ApiBase/api/clients/signals?page=1&page_size=5&signal_type=all&client_type=all&market=all" -Label "clients signals" | Out-Null
Assert-Api -Uri "$ApiBase/api/clients/20001/detail" -Label "client detail" | Out-Null
Assert-Api -Uri "$ApiBase/api/trading/overview?period=30d&market=all&trade_type=all" -Label "trading overview" | Out-Null
Assert-Api -Uri "$ApiBase/api/trading/trends?period=30d&market=all&trade_type=all" -Label "trading trends" | Out-Null
Assert-Api -Uri "$ApiBase/api/auc/overview?month=2026-03" -Label "auc overview" | Out-Null
Assert-Api -Uri "$ApiBase/api/rankings/overview?month=2026-03&dimension=auc" -Label "rankings overview" | Out-Null
Assert-Api -Uri "$ApiBase/api/activities?page=1&page_size=5" -Label "activities list" | Out-Null
Assert-Api -Uri "$ApiBase/api/activities/A001" -Label "activity detail" | Out-Null
Assert-Api -Uri "$ApiBase/api/activities/A001/trend" -Label "activity trend" | Out-Null
Assert-Api -Uri "$ApiBase/api/activities/A001/tracking?page=1&page_size=5&sort_by=registration_date&sort_order=descend" -Label "activity tracking" | Out-Null

Write-Step "Verifying MongoDB collection counts..."
& $PythonExe "scripts/check_mongo_counts.py"

Write-Step "Small dataset smoke test passed."
