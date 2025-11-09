# Quick test script for Edge DLP Extension
# Run this to check if everything is set up correctly

Write-Host "=== Edge DLP Extension - Quick Test ===" -ForegroundColor Cyan
Write-Host ""

# Test 1: Check Python
Write-Host "[1] Testing Python..." -ForegroundColor Yellow
$pythonVer = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ $pythonVer" -ForegroundColor Green
} else {
    Write-Host "  ✗ Python not found" -ForegroundColor Red
    exit 1
}

# Test 2: Check native host script
Write-Host "[2] Testing native host script..." -ForegroundColor Yellow
$nativeHost = Join-Path $PSScriptRoot "native_host.py"
if (Test-Path $nativeHost) {
    Write-Host "  ✓ native_host.py found" -ForegroundColor Green
} else {
    Write-Host "  ✗ native_host.py not found" -ForegroundColor Red
    exit 1
}

# Test 3: Test native host directly
Write-Host "[3] Testing native host detection..." -ForegroundColor Yellow
$testScript = Join-Path $PSScriptRoot "test_native_host.py"
if (Test-Path $testScript) {
    $output = python $testScript 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Native host test passed" -ForegroundColor Green
        $output | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
    } else {
        Write-Host "  ✗ Native host test failed" -ForegroundColor Red
        $output | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
    }
} else {
    Write-Host "  ⚠ test_native_host.py not found" -ForegroundColor Yellow
}

# Test 4: Check extension files
Write-Host "[4] Checking extension files..." -ForegroundColor Yellow
$files = @("manifest.json", "content_script.js", "service_worker.js")
$allGood = $true
foreach ($file in $files) {
    $path = Join-Path $PSScriptRoot $file
    if (Test-Path $path) {
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file missing" -ForegroundColor Red
        $allGood = $false
    }
}

# Test 5: Check registry (Windows only)
Write-Host "[5] Checking Windows registry..." -ForegroundColor Yellow
$regPath = "HKCU:\SOFTWARE\Microsoft\Edge\NativeMessagingHosts\com.edge_dlp.nativehost"
$reg = Get-ItemProperty -Path $regPath -ErrorAction SilentlyContinue
if ($reg) {
    Write-Host "  ✓ Native host registered" -ForegroundColor Green
    Write-Host "    Path: $($reg.'(Default)')" -ForegroundColor Gray
} else {
    Write-Host "  ⚠ Native host not registered in registry" -ForegroundColor Yellow
    Write-Host "    You may need to register it first" -ForegroundColor Gray
}

# Test 6: Check log file
Write-Host "[6] Checking for log file..." -ForegroundColor Yellow
$logFile = Join-Path $PSScriptRoot "native_host.log"
if (Test-Path $logFile) {
    Write-Host "  ✓ Log file exists" -ForegroundColor Green
    Write-Host "    Last 5 lines:" -ForegroundColor Gray
    Get-Content $logFile -Tail 5 | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
} else {
    Write-Host "  ⚠ No log file yet (will be created when extension runs)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Next Steps ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Load extension in browser:" -ForegroundColor White
Write-Host "   - Go to edge://extensions/ or chrome://extensions/" -ForegroundColor Gray
Write-Host "   - Enable Developer mode" -ForegroundColor Gray
Write-Host "   - Click 'Load unpacked' and select: $PSScriptRoot" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Get Extension ID and update com.edge_dlp.nativehost.json" -ForegroundColor White
Write-Host ""
Write-Host "3. Test on a webpage:" -ForegroundColor White
Write-Host "   - Open any webpage with text input" -ForegroundColor Gray
Write-Host "   - Type: 'My email is test@example.com'" -ForegroundColor Gray
Write-Host "   - Press Enter" -ForegroundColor Gray
Write-Host "   - Check if text is redacted" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Check for errors:" -ForegroundColor White
Write-Host "   - Service worker: edge://extensions/ → click 'service worker'" -ForegroundColor Gray
Write-Host "   - Browser console: F12 on any webpage" -ForegroundColor Gray
Write-Host "   - Native host log: $logFile" -ForegroundColor Gray
Write-Host ""

