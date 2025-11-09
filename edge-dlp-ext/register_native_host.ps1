# Register Edge DLP Native Host in Windows Registry
# Run this script to register the native host

Write-Host "=== Registering Edge DLP Native Host ===" -ForegroundColor Cyan
Write-Host ""

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $scriptDir) {
    $scriptDir = $PSScriptRoot
}

# Paths
$manifestPath = Join-Path $scriptDir "com.edge_dlp.nativehost.json"
$nativeHostPath = Join-Path $scriptDir "native_host.py"

# Check if files exist
if (-not (Test-Path $manifestPath)) {
    Write-Host "✗ Manifest file not found: $manifestPath" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $nativeHostPath)) {
    Write-Host "✗ Native host script not found: $nativeHostPath" -ForegroundColor Red
    exit 1
}

# Get absolute paths
$manifestPath = (Resolve-Path $manifestPath).Path
$nativeHostPath = (Resolve-Path $nativeHostPath).Path

# Get Python path
$pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonPath) {
    $pythonPath = (Get-Command python3 -ErrorAction SilentlyContinue).Source
}
if (-not $pythonPath) {
    Write-Host "✗ Python not found in PATH" -ForegroundColor Red
    Write-Host "  Please install Python and add it to PATH" -ForegroundColor Yellow
    exit 1
}

Write-Host "Python found: $pythonPath" -ForegroundColor Green

# Update manifest with absolute paths and Extension ID
Write-Host "Updating manifest with absolute paths..." -ForegroundColor Yellow
$manifestContent = Get-Content $manifestPath -Raw | ConvertFrom-Json
$manifestContent.path = "`"$pythonPath`" `"$nativeHostPath`""
# Check Extension ID
$extIdCheck = $manifestContent.allowed_origins[0]
if ($extIdCheck -like "*YOUR_EXTENSION_ID*") {
    Write-Host "  Extension ID placeholder found - already updated" -ForegroundColor Gray
} else {
    Write-Host "  Extension ID already set: $extIdCheck" -ForegroundColor Green
}
$manifestContent | ConvertTo-Json -Depth 10 | Set-Content $manifestPath -Encoding UTF8
Write-Host "  Manifest updated: $manifestPath" -ForegroundColor Green
Write-Host "  Path: $($manifestContent.path)" -ForegroundColor Gray

# Registry path
$regPath = "HKCU:\SOFTWARE\Microsoft\Edge\NativeMessagingHosts\com.edge_dlp.nativehost"

# Check if already exists
if (Test-Path $regPath) {
    Write-Host "⚠ Registry entry already exists" -ForegroundColor Yellow
    $response = Read-Host "Overwrite? (y/N)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "Cancelled." -ForegroundColor Yellow
        exit 0
    }
    Remove-Item $regPath -Force
}

# Create registry entry
Write-Host "Creating registry entry..." -ForegroundColor Yellow
try {
    New-Item -Path $regPath -Force | Out-Null
    Set-ItemProperty -Path $regPath -Name "(Default)" -Value $manifestPath -Force
    
    Write-Host "  ✓ Registry entry created successfully" -ForegroundColor Green
    Write-Host "    Path: $regPath" -ForegroundColor Gray
    Write-Host "    Value: $manifestPath" -ForegroundColor Gray
} catch {
    Write-Host "  ✗ Failed to create registry entry: $_" -ForegroundColor Red
    exit 1
}

# Verify
Write-Host ""
Write-Host "Verifying registration..." -ForegroundColor Yellow
try {
    $verify = Get-ItemProperty -Path $regPath
    Write-Host "  ✓ Verification successful" -ForegroundColor Green
    Write-Host "    Registered path: $($verify.'(Default)')" -ForegroundColor Gray
} catch {
    Write-Host "  ✗ Verification failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Registration Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Update Extension ID in com.edge_dlp.nativehost.json" -ForegroundColor White
Write-Host "2. Restart browser" -ForegroundColor White
Write-Host ""

