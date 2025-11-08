#!/usr/bin/env python3
import sys, struct, json

def send_message(message):
    """Send a message to the native host in the proper format"""
    encoded = json.dumps(message).encode('utf-8')
    sys.stdout.buffer.write(struct.pack('I', len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()

def read_message():
    """Read a response from the native host"""
    raw_len = sys.stdin.buffer.read(4)
    if len(raw_len) == 0:
        return None
    msg_len = struct.unpack('I', raw_len)[0]
    data = sys.stdin.buffer.read(msg_len).decode('utf-8')
    return json.loads(data)

# Test message
test_msg = {"tabId": 1, "text": "my api_key is sk_live_abc123def456ghi789"}
send_message(test_msg)

# Read response
response = read_message()
print("Response:", json.dumps(response, indent=2))
