param(
    [switch]$Bootstrap,
    [switch]$SkipInstall,
    [switch]$UseLocalMongo,
    [switch]$SkipBackendTests,
    [switch]$SetupOnly,
    [switch]$Elevated
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "[TBNZ] $Message" -ForegroundColor Cyan
}

function Test-CommandExists {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Refresh-PathFromRegistry {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($machinePath -or $userPath) {
        $env:Path = @($machinePath, $userPath) -join ";"
    }
}

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Restart-ScriptAsAdmin {
    param([string]$Reason)

    if (Test-IsAdministrator) {
        return
    }

    if ($Elevated) {
        throw "Administrator privileges are required, but elevation failed. Please run this script as administrator manually."
    }

    Write-Step $Reason

    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $PSCommandPath
    )

    foreach ($entry in $script:PSBoundParameters.GetEnumerator()) {
        if ($entry.Key -eq "Elevated") {
            continue
        }

        $value = $entry.Value
        if ($value -is [System.Management.Automation.SwitchParameter]) {
            if ($value.IsPresent) {
                $args += "-$($entry.Key)"
            }
        }
        elseif ($null -ne $value) {
            $args += "-$($entry.Key)"
            $args += "$value"
        }
    }

    $args += "-Elevated"

    Start-Process -FilePath "powershell" -Verb RunAs -ArgumentList $args | Out-Null
    exit 0
}

function Ensure-WingetAvailable {
    if (-not (Test-CommandExists "winget")) {
        throw "winget command not found. Please install 'App Installer' from Microsoft Store, then rerun this script."
    }
}

function Test-WingetPackageInstalled {
    param([string]$PackageId)

    try {
        $output = & winget list --id $PackageId --exact --accept-source-agreements 2>&1 | Out-String
        if ([string]::IsNullOrWhiteSpace($output)) {
            return $false
        }
        return $output -match [regex]::Escape($PackageId)
    }
    catch {
        return $false
    }
}

function Install-WingetPackage {
    param(
        [string]$PackageId,
        [string]$DisplayName,
        [string]$Scope = "user",
        [switch]$RequiresAdmin
    )

    Ensure-WingetAvailable

    if ($RequiresAdmin -and -not (Test-IsAdministrator)) {
        Restart-ScriptAsAdmin -Reason "Installing $DisplayName requires administrator privileges. Relaunching with elevation..."
    }

    if (Test-WingetPackageInstalled -PackageId $PackageId) {
        Write-Step "$DisplayName already installed."
        return
    }

    Write-Step "Installing $DisplayName via winget..."
    $args = @(
        "install",
        "--id", $PackageId,
        "--exact",
        "--silent",
        "--accept-source-agreements",
        "--accept-package-agreements"
    )

    if ($Scope) {
        $args += @("--scope", $Scope)
    }

    & winget @args | Out-Host

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install $DisplayName (winget id: $PackageId)."
    }

    Refresh-PathFromRegistry
}

function Resolve-PythonExecutable {
    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($command) {
        try {
            & $command.Source --version *> $null
            if ($LASTEXITCODE -eq 0) {
                return $command.Source
            }
        }
        catch {
            # continue fallback
        }
    }

    $candidates = @(
        "$env:LocalAppData\Programs\Python\Python312\python.exe",
        "$env:ProgramFiles\Python312\python.exe",
        "$env:ProgramFiles\Python311\python.exe"
    )

    foreach ($candidate in $candidates) {
        if (-not (Test-Path $candidate)) {
            continue
        }

        try {
            & $candidate --version *> $null
            if ($LASTEXITCODE -eq 0) {
                return $candidate
            }
        }
        catch {
            # continue fallback
        }
    }

    return $null
}

function Resolve-NpmExecutable {
    $command = Get-Command npm -ErrorAction SilentlyContinue
    if ($command) {
        try {
            & $command.Source --version *> $null
            if ($LASTEXITCODE -eq 0) {
                return $command.Source
            }
        }
        catch {
            # continue fallback
        }
    }

    $candidates = @(
        "$env:ProgramFiles\nodejs\npm.cmd",
        "$env:LocalAppData\Programs\nodejs\npm.cmd"
    )

    foreach ($candidate in $candidates) {
        if (-not (Test-Path $candidate)) {
            continue
        }

        try {
            & $candidate --version *> $null
            if ($LASTEXITCODE -eq 0) {
                return $candidate
            }
        }
        catch {
            # continue fallback
        }
    }

    return $null
}

function Ensure-MongoService {
    param([switch]$AllowInstall)

    $mongoService = Get-Service -Name "MongoDB" -ErrorAction SilentlyContinue
    if ($null -eq $mongoService -and $AllowInstall) {
        Install-WingetPackage -PackageId "MongoDB.Server" -DisplayName "MongoDB Server" -Scope "machine" -RequiresAdmin
        $mongoService = Get-Service -Name "MongoDB" -ErrorAction SilentlyContinue
    }

    if ($null -eq $mongoService) {
        Write-Warning "Local MongoDB service not found. Please install MongoDB Server manually or run with Docker."
        return $false
    }

    if ($mongoService.Status -ne "Running") {
        Write-Step "Starting local MongoDB service..."
        Start-Service -Name "MongoDB"
    }
    else {
        Write-Step "Local MongoDB service is already running."
    }

    return $true
}

$repoRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$venvPython = Join-Path $backendDir "venv\Scripts\python.exe"
$backendEnvFile = Join-Path $backendDir ".env"
$backendEnvExample = Join-Path $backendDir ".env.example"

if ($Bootstrap) {
    Write-Step "Bootstrap mode enabled: script will auto-install missing runtime components."
}

if (-not (Test-Path $backendDir)) {
    throw "Backend directory not found: $backendDir"
}

if (-not (Test-Path $frontendDir)) {
    throw "Frontend directory not found: $frontendDir"
}

if (-not (Test-Path $backendEnvFile) -and (Test-Path $backendEnvExample)) {
    Write-Step "Creating backend .env from .env.example..."
    Copy-Item -Path $backendEnvExample -Destination $backendEnvFile
}

$dockerAvailable = Test-CommandExists "docker"
$pythonExecutable = Resolve-PythonExecutable
$npmExecutable = Resolve-NpmExecutable

if ($Bootstrap) {
    $needsPythonInstall = [string]::IsNullOrWhiteSpace($pythonExecutable)
    $needsNodeInstall = [string]::IsNullOrWhiteSpace($npmExecutable)
    $willUseLocalMongo = $UseLocalMongo -or -not $dockerAvailable
    $needsMongoInstall = $false
    if ($willUseLocalMongo) {
        $needsMongoInstall = $null -eq (Get-Service -Name "MongoDB" -ErrorAction SilentlyContinue)
    }

    if ($needsPythonInstall -or $needsNodeInstall -or $needsMongoInstall) {
        Ensure-WingetAvailable
    }

    if ($needsPythonInstall) {
        Install-WingetPackage -PackageId "Python.Python.3.12" -DisplayName "Python 3.12" -Scope "user"
        $pythonExecutable = Resolve-PythonExecutable
    }

    if ($needsNodeInstall) {
        Install-WingetPackage -PackageId "OpenJS.NodeJS.LTS" -DisplayName "Node.js LTS" -Scope "user"
        $npmExecutable = Resolve-NpmExecutable
    }

    if (-not $dockerAvailable) {
        Write-Warning "Docker not found in bootstrap mode. Switching to local MongoDB service mode."
        $UseLocalMongo = $true
    }
}

if ([string]::IsNullOrWhiteSpace($pythonExecutable)) {
    throw "Python not found. Rerun with -Bootstrap to auto-install Python, or install Python 3.10+ manually."
}

if ([string]::IsNullOrWhiteSpace($npmExecutable)) {
    throw "npm not found. Rerun with -Bootstrap to auto-install Node.js, or install Node.js 18+ manually."
}

if (-not $UseLocalMongo) {
    if ($dockerAvailable) {
        Write-Step "Starting MongoDB via docker compose..."
        Push-Location $repoRoot
        try {
            & docker compose up -d mongodb | Out-Host
            if ($LASTEXITCODE -ne 0) {
                throw "docker compose failed"
            }
        }
        catch {
            Write-Warning "Failed to start MongoDB via Docker. Falling back to local MongoDB service mode."
            $UseLocalMongo = $true
        }
        finally {
            Pop-Location
        }
    }
    else {
        Write-Warning "Docker not found. Falling back to local MongoDB service mode."
        $UseLocalMongo = $true
    }
}

if ($UseLocalMongo) {
    $mongoReady = Ensure-MongoService -AllowInstall:$Bootstrap
    if (-not $mongoReady) {
        throw "MongoDB is required but unavailable. Install MongoDB Server manually, or install Docker and rerun."
    }
}

if (-not (Test-Path $venvPython)) {
    Write-Step "Creating backend virtual environment..."
    Push-Location $backendDir
    try {
        & $pythonExecutable -m venv venv
    }
    finally {
        Pop-Location
    }
}

if (-not (Test-Path $venvPython)) {
    throw "Failed to create backend virtual environment."
}

if (-not $SkipInstall) {
    Write-Step "Installing backend dependencies..."
    Push-Location $backendDir
    try {
        & $venvPython -m pip install -r requirements.txt | Out-Host
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Step "Skipping dependency installation because -SkipInstall was provided."
}

if (-not $SkipBackendTests) {
    Write-Step "Running backend tests before starting services..."
    Push-Location $backendDir
    try {
        & $venvPython -m pytest -q | Out-Host
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Step "Skipping backend tests because -SkipBackendTests was provided."
}

$nodeModulesDir = Join-Path $frontendDir "node_modules"
$shouldInstallFrontendDeps = (-not $SkipInstall) -or (-not (Test-Path $nodeModulesDir))

if ($shouldInstallFrontendDeps) {
    if ($SkipInstall -and -not (Test-Path $nodeModulesDir)) {
        Write-Step "Frontend dependencies are missing, installing despite -SkipInstall."
    }
    elseif (-not $SkipInstall) {
        Write-Step "Installing frontend dependencies..."
    }

    Push-Location $frontendDir
    try {
        & $npmExecutable install | Out-Host
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Step "Skipping frontend dependency installation because -SkipInstall was provided and node_modules already exists."
}

if ($SetupOnly) {
    Write-Step "Setup completed. Skipping service launch because -SetupOnly was provided."
    Write-Host "You can launch services later with: start-dev.bat -SkipInstall -SkipBackendTests"
    exit 0
}

Write-Step "Launching backend server in a new PowerShell window..."
$backendCommand = "Set-Location -LiteralPath '$backendDir'; & '$venvPython' -m uvicorn app.main:app --reload --port 8000"
Start-Process -FilePath "powershell" -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backendCommand) | Out-Null

Write-Step "Launching frontend server in a new PowerShell window..."
$frontendCommand = "Set-Location -LiteralPath '$frontendDir'; & '$npmExecutable' run dev"
Start-Process -FilePath "powershell" -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $frontendCommand) | Out-Null

Write-Step "All services started."
Write-Host "Backend docs: http://localhost:8000/docs"
Write-Host "Frontend: http://localhost:5173"
