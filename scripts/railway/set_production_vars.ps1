#requires -Version 5.1
<#
.SYNOPSIS
    Seed or rotate the UbuntuCare production variables on Railway.

.DESCRIPTION
    Sets the backend, Keycloak, and MinIO variables that are required for a
    production deployment without committing any secrets to the repository.

    Secrets are generated locally with a cryptographically secure RNG and sent
    to Railway through stdin (never through the process arguments). Existing
    secrets are left untouched unless -RotateSecrets is supplied, so re-running
    the script is safe.

    Nothing is changed unless -Apply is passed. The default is a dry run that
    prints which keys would be written and to which service.

    This script deliberately uses `--skip-deploys`. After it succeeds, apply the
    IaC partial and deploy the services as described in deploy/railway/README.md.

.PARAMETER ProjectId
    Railway project ID. Defaults to the UbuntuCare production project.

.PARAMETER EnvironmentName
    Railway environment name. Defaults to "production".

.PARAMETER PublicAppUrl
    Public origin of the frontend, used for CORS and Keycloak redirect URIs.

.PARAMETER BootstrapAdminEmail
    Email of the first real administrator. Required with -Apply.

.PARAMETER BootstrapAdminUsername
    Username of the first real administrator. Defaults to BootstrapAdminEmail.

.PARAMETER BootstrapAdminPassword
    Password for the first real administrator. Generated when omitted and no
    password is stored yet. Pass -SkipBootstrapAdmin after the account exists.

.PARAMETER SkipBootstrapAdmin
    Do not write the bootstrap administrator variables. Use this on later runs
    once the real administrator exists, especially after removing the password
    variable from Railway.

.PARAMETER RotateSecrets
    Generate new values for SECRET_KEY, the Keycloak admin password, the
    api-gateway client secret, and the MinIO root password. Rotating invalidates
    existing sessions and requires the Keycloak admin/client and MinIO to be
    updated in the same operation (this script does both).

.PARAMETER EnableDemoPurge
    Set UBUNTUCARE_PURGE_DEMO_DATA=1 and UBUNTUCARE_PURGE_DEMO_USERS=1 for the
    next backend deploy so the one-off purge removes seeded demo patients/users
    from PostgreSQL and demo accounts from Keycloak. Remember to run the script
    again without this switch afterwards.

.PARAMETER Apply
    Actually write the variables. Without it the script only prints the plan.

.EXAMPLE
    .\scripts\railway\set_production_vars.ps1 -BootstrapAdminEmail admin@example.org `
        -BootstrapAdminUsername admin

.EXAMPLE
    .\scripts\railway\set_production_vars.ps1 -Apply -RotateSecrets `
        -BootstrapAdminEmail admin@example.org -EnableDemoPurge
#>
[CmdletBinding()]
param(
    [string]$ProjectId = "d6c33d80-8a9e-4ae8-a7d6-daff3f21068a",
    [string]$EnvironmentName = "production",
    [string]$PublicAppUrl = "https://ubuntucare.up.railway.app",
    [string]$BootstrapAdminEmail = "",
    [string]$BootstrapAdminUsername = "",
    [string]$BootstrapAdminPassword = "",
    [switch]$SkipBootstrapAdmin,
    [switch]$RotateSecrets,
    [switch]$EnableDemoPurge,
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$localCli = Join-Path $repoRoot "node_modules\.bin\railway.cmd"
$railway = if (Test-Path $localCli) { $localCli } else { "railway" }

function New-RandomSecret {
    param([int]$Bytes = 48)
    $buffer = New-Object byte[] $Bytes
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($buffer) } finally { $rng.Dispose() }
    return [Convert]::ToBase64String($buffer).Replace("+", "-").Replace("/", "_").TrimEnd("=")
}

function New-Password {
    # Guarantees the production realm password policy: length >= 12, upper,
    # lower, digit, and special character.
    return "$(New-RandomSecret -Bytes 36)Aa1!"
}

function Assert-AdminPassword {
    param([string]$Value)
    $problems = @()
    if ($Value.Length -lt 12) { $problems += "at least 12 characters" }
    if ($Value -cnotmatch "[a-z]") { $problems += "a lowercase letter" }
    if ($Value -cnotmatch "[A-Z]") { $problems += "an uppercase letter" }
    if ($Value -notmatch "[0-9]") { $problems += "a digit" }
    if ($Value -notmatch "[^A-Za-z0-9]") { $problems += "a special character" }
    if ($problems.Count -gt 0) {
        throw "BootstrapAdminPassword needs $($problems -join ', ')."
    }
}

function Invoke-Railway {
    param([string[]]$Arguments)
    & $railway @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "railway $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

function Set-RailwayVariable {
    param(
        [string]$Service,
        [string]$Key,
        [string]$Value
    )
    $common = @(
        "variable", "set",
        "--service", $Service,
        "--environment", $EnvironmentName,
        "--project", $ProjectId,
        "--skip-deploys",
        "--json"
    )
    if (-not $Apply) {
        Write-Host ("  [plan] {0,-12} {1}" -f $Service, $Key)
        return
    }
    # Secrets go through stdin so they never appear in the process list. Retry
    # transient Railway API connection failures without logging CLI output.
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        $null = $Value | & $railway @common $Key --stdin 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host ("  [set]  {0,-12} {1}" -f $Service, $Key)
            return
        }
        if ($attempt -lt 3) {
            Write-Warning "Railway did not accept $Key on $Service (attempt $attempt); retrying."
            Start-Sleep -Seconds (3 * $attempt)
        }
    }
    throw "Failed to set $Key on $Service after 3 attempts."
}

function Set-RailwayVariables {
    param(
        [string]$Service,
        [System.Collections.IDictionary]$Values
    )
    foreach ($key in $Values.Keys) {
        if (-not $Apply) {
            Write-Host ("  [plan] {0,-12} {1}" -f $Service, $key)
        }
    }
    if (-not $Apply) { return }

    $arguments = @(
        "variable", "set",
        "--service", $Service,
        "--environment", $EnvironmentName,
        "--project", $ProjectId,
        "--skip-deploys",
        "--json"
    )
    foreach ($entry in $Values.GetEnumerator()) {
        $arguments += "{0}={1}" -f $entry.Key, $entry.Value
    }

    for ($attempt = 1; $attempt -le 3; $attempt++) {
        $null = & $railway @arguments 2>&1
        if ($LASTEXITCODE -eq 0) {
            foreach ($key in $Values.Keys) {
                Write-Host ("  [set]  {0,-12} {1}" -f $Service, $key)
            }
            return
        }
        if ($attempt -lt 3) {
            Write-Warning "Railway did not accept variables on $Service (attempt $attempt); retrying."
            Start-Sleep -Seconds (3 * $attempt)
        }
    }
    throw "Failed to set variables on $Service after 3 attempts."
}

function Get-RailwayVariableNames {
    param([string]$Service)
    $cliArgs = @(
        "variable", "list",
        "--service", $Service,
        "--environment", $EnvironmentName,
        "--project", $ProjectId,
        "--json"
    )
    $raw = & $railway @cliArgs 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "railway variable list --service $Service failed with exit code $LASTEXITCODE"
    }
    $text = ($raw | Out-String).Trim()
    if ([string]::IsNullOrWhiteSpace($text)) { return @() }
    $object = $text | ConvertFrom-Json
    return @($object.PSObject.Properties.Name)
}

if ($Apply -and -not $SkipBootstrapAdmin -and [string]::IsNullOrWhiteSpace($BootstrapAdminEmail)) {
    throw "BootstrapAdminEmail is required with -Apply so the first real administrator can be created."
}
if (-not $SkipBootstrapAdmin -and [string]::IsNullOrWhiteSpace($BootstrapAdminUsername)) {
    $BootstrapAdminUsername = $BootstrapAdminEmail
}

$generatedAdminPassword = $false
if (-not $SkipBootstrapAdmin -and [string]::IsNullOrWhiteSpace($BootstrapAdminPassword)) {
    $existingBackendVars = Get-RailwayVariableNames -Service "backend"
    if ($existingBackendVars -contains "KEYCLOAK_BOOTSTRAP_ADMIN_PASSWORD") {
        Write-Host "Keeping the existing bootstrap administrator password." -ForegroundColor DarkGray
    } else {
        $BootstrapAdminPassword = New-Password
        $generatedAdminPassword = $true
    }
}
if (-not [string]::IsNullOrWhiteSpace($BootstrapAdminPassword)) {
    Assert-AdminPassword -Value $BootstrapAdminPassword
}

$generated = @{}
if ($RotateSecrets) {
    $generated["SECRET_KEY"] = New-RandomSecret -Bytes 48
    $generated["KEYCLOAK_ADMIN_PASSWORD"] = New-RandomSecret -Bytes 36
    $generated["KEYCLOAK_CLIENT_SECRET"] = New-RandomSecret -Bytes 36
    $generated["MINIO_ROOT_PASSWORD"] = New-RandomSecret -Bytes 36
}

Write-Host ""
Write-Host "UbuntuCare production variables" -ForegroundColor Cyan
Write-Host "  Project:     $ProjectId"
Write-Host "  Environment: $EnvironmentName"
Write-Host "  Public URL:  $PublicAppUrl"
Write-Host "  Mode:        $(if ($Apply) { 'APPLY' } else { 'DRY RUN (pass -Apply to write)' })"
Write-Host ""

# ---------------------------------------------------------------------------
# Non-secret application configuration
# ---------------------------------------------------------------------------
$backendPlain = [ordered]@{
    "ENVIRONMENT"                 = "production"
    "DEBUG"                       = "false"
    "CORS_ORIGINS"                = $PublicAppUrl
    "KEYCLOAK_SERVER_URL"         = "http://keycloak.railway.internal:8080"
    "KEYCLOAK_REALM"              = "ubuntucare"
    "KEYCLOAK_CLIENT_ID"          = "api-gateway"
    "KEYCLOAK_FRONTEND_CLIENT_ID" = "frontend"
    "KEYCLOAK_ADMIN_USER"         = "admin"
    "KEYCLOAK_DB_NAME"            = "keycloak"
    "KEYCLOAK_DB_MANAGE"          = "1"
    "UBUNTUCARE_PUBLIC_APP_URL"   = $PublicAppUrl
    "UBUNTUCARE_SEED_DEMO_DATA"   = "0"
    "UBUNTUCARE_SEED_DEMO_USERS"  = "0"
    "UBUNTUCARE_PURGE_DEMO_DATA"  = if ($EnableDemoPurge) { "1" } else { "0" }
    "UBUNTUCARE_PURGE_DEMO_USERS" = if ($EnableDemoPurge) { "1" } else { "0" }
    "MINIO_ENDPOINT"              = "minio.railway.internal:9000"
    "MINIO_ACCESS_KEY"            = "ubuntucare"
    "MINIO_BUCKET"                = "ubuntucare"
}

if (-not $SkipBootstrapAdmin -and -not [string]::IsNullOrWhiteSpace($BootstrapAdminEmail)) {
    $backendPlain["KEYCLOAK_BOOTSTRAP_ADMIN_EMAIL"] = $BootstrapAdminEmail
    $backendPlain["KEYCLOAK_BOOTSTRAP_ADMIN_USERNAME"] = $BootstrapAdminUsername
}

Write-Host "Backend (non-secret)" -ForegroundColor Yellow
Set-RailwayVariables -Service "backend" -Values $backendPlain

# ---------------------------------------------------------------------------
# Secrets
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Secrets" -ForegroundColor Yellow
if ($RotateSecrets) {
    Write-Host "  Rotating all secrets (existing sessions will be invalidated)."
}
foreach ($key in @("SECRET_KEY", "KEYCLOAK_CLIENT_SECRET", "KEYCLOAK_ADMIN_PASSWORD", "MINIO_ROOT_PASSWORD")) {
    if ($generated.ContainsKey($key)) {
        $service = switch ($key) {
            "MINIO_ROOT_PASSWORD" { "minio" }
            "KEYCLOAK_ADMIN_PASSWORD" { "keycloak" }
            default { "backend" }
        }
        Set-RailwayVariable -Service $service -Key $key -Value $generated[$key]
        # The backend also needs the Keycloak admin password and MinIO root
        # password so the startup provisioning can authenticate.
        if ($service -ne "backend") {
            $targetKey = if ($key -eq "MINIO_ROOT_PASSWORD") { "MINIO_SECRET_KEY" } else { $key }
            Set-RailwayVariable -Service "backend" -Key $targetKey -Value $generated[$key]
        }
    } else {
        Write-Host ("  [keep] existing value for {0}" -f $key)
    }
}

if (-not $SkipBootstrapAdmin -and -not [string]::IsNullOrWhiteSpace($BootstrapAdminPassword)) {
    Set-RailwayVariable -Service "backend" -Key "KEYCLOAK_BOOTSTRAP_ADMIN_PASSWORD" -Value $BootstrapAdminPassword
    Write-Host "  [info] The bootstrap password is only needed for the first deploy. Remove"
    Write-Host "         KEYCLOAK_BOOTSTRAP_ADMIN_PASSWORD from Railway after the admin exists"
    Write-Host "         and pass -SkipBootstrapAdmin on later runs."
}

Write-Host ""
if (-not $Apply) {
    Write-Host "Dry run complete. Re-run with -Apply to write the variables." -ForegroundColor Cyan
    exit 0
}

if ($generatedAdminPassword) {
    Write-Host "Bootstrap administrator password (store it in your password manager now):" -ForegroundColor Green
    Write-Host "  $BootstrapAdminPassword"
    Write-Host ""
}
Write-Host "Variables written with --skip-deploys." -ForegroundColor Green
Write-Host "Next:"
Write-Host "  1. Apply the partial:  node .railway/railway.dependencies.ts  (via railway config plan/apply)"
Write-Host "  2. Deploy backend, then keycloak, then frontend."
Write-Host "  3. If you used -EnableDemoPurge, run this script again without it so the"
Write-Host "     purge does not run on every deploy."
