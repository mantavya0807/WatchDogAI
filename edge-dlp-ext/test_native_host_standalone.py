#!/usr/bin/env python3
"""
Test script for native host - sends a proper native messaging protocol message
This simulates what the browser does when calling the native host
"""
import sys
import struct
import json
import subprocess
from pathlib import Path

# Get the native host script path
script_dir = Path(__file__).parent
native_host_path = script_dir / "native_host.py"
python_exe = r"C:\Users\manta\AppData\Local\Programs\Python\Python311\python.exe"

# Test message
test_message = {
    "text": "test@example.com",
    "tabId": 123,
    "context": {}
}

print("=" * 60)
print("Testing Native Host")
print("=" * 60)
print(f"Test message: {test_message['text']}")
print()

# Convert message to JSON
message_json = json.dumps(test_message)
message_bytes = message_json.encode('utf-8')

# Create the native messaging protocol message
# Format: [4-byte little-endian length][message bytes]
length_bytes = struct.pack('<I', len(message_bytes))
full_message = length_bytes + message_bytes

print(f"Message length: {len(message_bytes)} bytes")
print(f"Full message (first 50 bytes): {full_message[:50]}")
print()

# Start the native host process
print("Starting native host process...")
process = subprocess.Popen(
    [python_exe, str(native_host_path)],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=False  # Binary mode for stdin/stdout
)

# Send the message
print("Sending message...")
process.stdin.write(full_message)
process.stdin.flush()
process.stdin.close()

# Read response (native messaging protocol)
print("Reading response...")
try:
    # Read 4-byte length
    response_length_bytes = process.stdout.read(4)
    if len(response_length_bytes) < 4:
        print("ERROR: Could not read response length")
        stderr = process.stderr.read().decode('utf-8', errors='ignore')
        print(f"Stderr: {stderr}")
        sys.exit(1)
    
    response_length = struct.unpack('<I', response_length_bytes)[0]
    print(f"Response length: {response_length} bytes")
    
    # Read the actual response
    response_bytes = process.stdout.read(response_length)
    if len(response_bytes) < response_length:
        print(f"ERROR: Incomplete response (got {len(response_bytes)}/{response_length} bytes)")
        stderr = process.stderr.read().decode('utf-8', errors='ignore')
        print(f"Stderr: {stderr}")
        sys.exit(1)
    
    response_json = response_bytes.decode('utf-8')
    response = json.loads(response_json)
    
    print()
    print("=" * 60)
    print("RESPONSE:")
    print("=" * 60)
    print(json.dumps(response, indent=2))
    print()
    
    if response.get('action') == 'replace':
        print("[SUCCESS] PII detected and redacted!")
        print(f"  Original: {test_message['text']}")
        print(f"  Replacement: {response.get('replacement', 'N/A')}")
    elif response.get('action') == 'allow':
        if response.get('error'):
            print(f"[ERROR] {response.get('error')}")
        else:
            print("[INFO] No PII detected (or error occurred)")
    
    # Wait for process to finish
    process.wait()
    if process.returncode != 0:
        print(f"\n⚠ Process exited with code: {process.returncode}")
        stderr = process.stderr.read().decode('utf-8', errors='ignore')
        if stderr:
            print(f"Stderr: {stderr}")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    process.kill()
    sys.exit(1)

print()
print("=" * 60)
print("Test complete!")
print("=" * 60)
print()
print("NOTE: The native host does NOT run continuously.")
print("The browser launches it automatically when needed.")
print("Check native_host.log for detailed logs.")

