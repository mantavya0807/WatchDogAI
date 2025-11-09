#!/usr/bin/env python3
"""Test if full obfuscator is working - should detect names, phones, etc."""
import sys
import struct
import json
import subprocess
from pathlib import Path

script_dir = Path(__file__).parent
native_host_path = script_dir / "native_host.py"
python_exe = r"C:\Users\manta\AppData\Local\Programs\Python\Python311\python.exe"

# Test message with multiple PII types
test_message = {
    "text": "hello my name is mantavya and my contact is 5645444219 and my email is test@example.com",
    "tabId": 123,
    "context": {}
}

print("=" * 60)
print("Testing Full Obfuscator")
print("=" * 60)
print(f"Test message: {test_message['text']}")
print()

message_json = json.dumps(test_message)
message_bytes = message_json.encode('utf-8')
length_bytes = struct.pack('<I', len(message_bytes))
full_message = length_bytes + message_bytes

process = subprocess.Popen(
    [python_exe, str(native_host_path)],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=False
)

process.stdin.write(full_message)
process.stdin.flush()
process.stdin.close()

response_length_bytes = process.stdout.read(4)
response_length = struct.unpack('<I', response_length_bytes)[0]
response_bytes = process.stdout.read(response_length)
response_json = response_bytes.decode('utf-8')
response = json.loads(response_json)

print("RESPONSE:")
print(json.dumps(response, indent=2))
print()

if response.get('action') == 'replace':
    print("[SUCCESS] PII detected!")
    print(f"  Original: {test_message['text']}")
    print(f"  Replacement: {response.get('replacement', 'N/A')}")
    print(f"  Findings: {len(response.get('findings', []))}")
    if response.get('num_redactions'):
        print(f"  Redactions: {response.get('num_redactions')}")
else:
    print("[INFO] No PII detected or using fallback")

stderr = process.stderr.read().decode('utf-8', errors='ignore')
if stderr:
    print(f"\nStderr: {stderr}")

process.wait()


