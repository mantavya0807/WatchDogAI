# Test Native Messaging Protocol
# This script tests if the native host can be invoked correctly

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$nativeHostPath = Join-Path $scriptDir "native_host.bat"

Write-Host "Testing native host: $nativeHostPath" -ForegroundColor Cyan
Write-Host ""

# Create a test message
$testMessage = @{
    text = "test@example.com"
    tabId = 123
    context = @{}
} | ConvertTo-Json -Compress

Write-Host "Test message: $testMessage" -ForegroundColor Yellow
Write-Host ""

# Native messaging uses length-prefixed messages
# Format: [4 bytes length][message]
$messageBytes = [System.Text.Encoding]::UTF8.GetBytes($testMessage)
$lengthBytes = [System.BitConverter]::GetBytes($messageBytes.Length)

# Start the native host process
$processInfo = New-Object System.Diagnostics.ProcessStartInfo
$processInfo.FileName = $nativeHostPath
$processInfo.UseShellExecute = $false
$processInfo.RedirectStandardInput = $true
$processInfo.RedirectStandardOutput = $true
$processInfo.RedirectStandardError = $true
$processInfo.CreateNoWindow = $true

$process = New-Object System.Diagnostics.Process
$process.StartInfo = $processInfo

try {
    $process.Start() | Out-Null
    
    # Write length + message
    $process.StandardInput.BaseStream.Write($lengthBytes, 0, 4)
    $process.StandardInput.BaseStream.Write($messageBytes, 0, $messageBytes.Length)
    $process.StandardInput.BaseStream.Flush()
    
    # Read response (length-prefixed)
    $responseLengthBytes = New-Object byte[] 4
    $bytesRead = $process.StandardInput.BaseStream.Read($responseLengthBytes, 0, 4)
    
    if ($bytesRead -eq 4) {
        $responseLength = [System.BitConverter]::ToInt32($responseLengthBytes, 0)
        Write-Host "Response length: $responseLength" -ForegroundColor Green
        
        if ($responseLength -gt 0) {
            $responseBytes = New-Object byte[] $responseLength
            $bytesRead = $process.StandardInput.BaseStream.Read($responseBytes, 0, $responseLength)
            $response = [System.Text.Encoding]::UTF8.GetString($responseBytes, 0, $bytesRead)
            
            Write-Host "Response: $response" -ForegroundColor Green
        }
    } else {
        Write-Host "Failed to read response length" -ForegroundColor Red
    }
    
    # Wait a bit for the process to finish
    Start-Sleep -Milliseconds 500
    
    if (-not $process.HasExited) {
        $process.Kill()
    }
    
    $stderr = $process.StandardError.ReadToEnd()
    if ($stderr) {
        Write-Host "Stderr: $stderr" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
} finally {
    if (-not $process.HasExited) {
        $process.Kill()
    }
    $process.Dispose()
}

Write-Host ""
Write-Host "Test complete" -ForegroundColor Cyan

