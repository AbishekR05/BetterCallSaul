# install_pgvector.ps1
# This script installs pgvector for local PostgreSQL 18.
# RUN THIS SCRIPT IN AN ADMINISTRATOR POWERSHELL TERMINAL.

# Exit if not running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "This script MUST be run as an Administrator. Please reopen PowerShell as Administrator and try again."
    Exit
}

$tempDir = "D:\Full Stack\BetterCallSaul\temp_pgvector"
$zipPath = Join-Path $tempDir "vector.zip"
$extractDir = Join-Path $tempDir "extracted"
$pgDir = "C:\Program Files\PostgreSQL\18"

Write-Host "Checking local PostgreSQL 18 installation..."
if (-not (Test-Path $pgDir)) {
    Write-Error "PostgreSQL 18 not found at $pgDir. Please verify your install path."
    Exit
}

Write-Host "Creating temp directory..."
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

# Download if not already downloaded
if (-not (Test-Path $zipPath)) {
    Write-Host "Downloading pgvector precompiled zip..."
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $url = "https://github.com/andreiramani/pgvector_pgsql_windows/releases/download/0.8.6_18/vector.v0.8.6-pg18.zip"
    Invoke-WebRequest -Uri $url -OutFile $zipPath -Verbose
}

Write-Host "Extracting pgvector zip..."
Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force

Write-Host "Copying extension files to PostgreSQL 18..."

# 1. Copy DLL
$libSource = Join-Path $extractDir "lib\vector.dll"
$libTarget = Join-Path $pgDir "lib\"
Copy-Item -Path $libSource -Destination $libTarget -Force
Write-Host "Copied: vector.dll -> $libTarget"

# 2. Copy Extensions SQL and Control files
$shareSource = Join-Path $extractDir "share\extension\*"
$shareTarget = Join-Path $pgDir "share\extension\"
Copy-Item -Path $shareSource -Destination $shareTarget -Force
Write-Host "Copied: Extension files -> $shareTarget"

# 3. Copy Headers
$includeTargetDir = Join-Path $pgDir "include\server\extension\vector"
New-Item -ItemType Directory -Path $includeTargetDir -Force | Out-Null
$includeSource = Join-Path $extractDir "include\server\extension\vector\*"
Copy-Item -Path $includeSource -Destination $includeTargetDir -Force
Write-Host "Copied: Header files -> $includeTargetDir"

Write-Host "Cleaning up temp files..."
Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "`npgvector installation complete! You can now run 'CREATE EXTENSION vector;' in your PostgreSQL database." -ForegroundColor Green
