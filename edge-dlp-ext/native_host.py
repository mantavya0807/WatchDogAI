#!/usr/bin/env python3
import sys
import struct
import json
import re
import logging
import traceback
import os
import time
from pathlib import Path

# Setup logging - cross-platform
script_dir = Path(__file__).parent
if sys.platform == 'win32':
    log_path = script_dir / 'native_host.log'
    # IPC file for communicating with system clipboard monitor
    ipc_file = Path.home() / 'AppData' / 'Local' / 'EdgeDLP' / 'extension_status.json'
else:
    log_path = Path('/tmp/native_host.log')
    ipc_file = Path('/tmp/edgedlp_extension_status.json')

# Create directory if needed
if sys.platform == 'win32':
    ipc_file.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(log_path),
    level=logging.DEBUG,
    format='%(asctime)s - %(message)s'
)

logging.info("="*50)
logging.info("Native host starting...")

# Patterns for detection
PATTERNS = [
    ('API_KEY', re.compile(r'(?:api[_-]?key|secret|sk_live)[\s:=]*[A-Za-z0-9\-_]{20,}', re.I)),
    ('EMAIL', re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}')),
    ('SSN', re.compile(r'\b\d{3}-\d{2}-\d{4}\b')),
    ('JWT', re.compile(r'\beyJ[0-9A-Za-z\-_]+\.[0-9A-Za-z\-_]+\.[0-9A-Za-z\-_]+\b'))
]

def detect(text):
    findings = []
    for t, pat in PATTERNS:
        for m in pat.finditer(text):
            findings.append({'type': t, 'match': m.group(0), 'start': m.start(), 'end': m.end()})
    return findings

def send_message(message_obj):
    """Send a message to the extension"""
    try:
        message_json = json.dumps(message_obj)
        message_bytes = message_json.encode('utf-8')
        
        # Write length as 4-byte little-endian integer (explicit little-endian)
        sys.stdout.buffer.write(struct.pack('<I', len(message_bytes)))
        # Write the message
        sys.stdout.buffer.write(message_bytes)
        sys.stdout.buffer.flush()
        
        logging.info(f"Sent: {message_json}")
        return True
    except Exception as e:
        logging.error(f"Error sending message: {e}")
        logging.error(traceback.format_exc())
        return False

def read_message():
    """Read a single message from stdin"""
    try:
        # Read the message length (4 bytes)
        raw_length = sys.stdin.buffer.read(4)
        
        if len(raw_length) == 0:
            logging.info("No input received (EOF)")
            return None
        
        if len(raw_length) < 4:
            logging.error(f"Incomplete length header: {len(raw_length)} bytes")
            return None
        
        # Native messaging uses little-endian format
        message_length = struct.unpack('<I', raw_length)[0]
        logging.info(f"Expecting message of length: {message_length}")
        
        # Sanity check
        if message_length > 1024 * 1024:  # 1MB limit
            logging.error(f"Message too large: {message_length} bytes")
            return None
        
        # Read the message
        message_bytes = sys.stdin.buffer.read(message_length)
        
        if len(message_bytes) < message_length:
            logging.error(f"Incomplete message: got {len(message_bytes)}/{message_length} bytes")
            return None
        
        message_json = message_bytes.decode('utf-8')
        logging.info(f"Received: {message_json[:200]}...")
        
        return json.loads(message_json)
    except Exception as e:
        logging.error(f"Error reading message: {e}")
        logging.error(traceback.format_exc())
        return None

def notify_clipboard_monitor(is_risky, hostname):
    """Write extension status to IPC file for system clipboard monitor"""
    try:
        # Ensure directory exists
        ipc_file.parent.mkdir(parents=True, exist_ok=True)
        
        status = {
            'is_risky_domain': is_risky,
            'hostname': hostname,
            'timestamp': int(time.time())
        }
        
        with open(ipc_file, 'w') as f:
            json.dump(status, f)
        
        logging.info(f"Notified clipboard monitor: risky={is_risky}, hostname={hostname}")
        logging.info(f"IPC file written to: {ipc_file}")
        return True
    except Exception as e:
        logging.error(f"Error notifying clipboard monitor: {e}")
        logging.error(traceback.format_exc())
        return False

def handle_message(msg):
    """Process a message and return a response"""
    try:
        msg_type = msg.get('type', '')
        
        # Handle clipboard monitor notification
        if msg_type == 'notify-clipboard-monitor':
            is_risky = msg.get('isRiskyDomain', False)
            hostname = msg.get('hostname', '')
            logging.info(f"Handling notify-clipboard-monitor: risky={is_risky}, hostname={hostname}")
            success = notify_clipboard_monitor(is_risky, hostname)
            if success:
                return {'status': 'ok', 'notified': True}
            else:
                return {'status': 'error', 'notified': False, 'error': 'Failed to write IPC file'}
        
        # Handle text obfuscation (existing functionality)
        text = msg.get('text', '')
        tab_id = msg.get('tabId')
        
        logging.info(f"Processing text for tab {tab_id}: {text[:50]}...")
        
        if not text:
            logging.warning("Empty text received")
            return {'tabId': tab_id, 'action': 'allow', 'error': 'No text provided'}
        
        findings = detect(text)
        logging.info(f"Found {len(findings)} potential issues")
        
        if not findings:
            return {'tabId': tab_id, 'action': 'allow'}
        
        # Determine action based on findings
        types = {f['type'] for f in findings}
        
        if 'API_KEY' in types or 'JWT' in types:
            # Create replacement
            replacement = text
            for f in sorted(findings, key=lambda x: x['start'], reverse=True):
                replacement = replacement[:f['start']] + f'[REDACTED:{f["type"]}]' + replacement[f['end']:]
            
            return {
                'tabId': tab_id,
                'action': 'replace',
                'replacement': replacement,
                'findings': findings
            }
        else:
            return {
                'tabId': tab_id,
                'action': 'warn',
                'findings': findings
            }
    except Exception as e:
        logging.error(f"Error handling message: {e}")
        logging.error(traceback.format_exc())
        return {'tabId': msg.get('tabId'), 'action': 'allow', 'error': str(e)}

def main():
    """Main entry point - handles a single message for sendNativeMessage"""
    try:
        logging.info("Entering main - reading one message...")
        
        # Read exactly ONE message (sendNativeMessage pattern)
        message = read_message()
        
        if message is None:
            logging.error("Failed to read message")
            # Try to send error response anyway
            send_message({'action': 'allow', 'error': 'Failed to read message'})
            sys.exit(1)
        
        logging.info(f"Processing message: {message}")
        
        # Handle the message
        response = handle_message(message)
        
        logging.info(f"Response to send: {response}")
        
        # Send response
        if send_message(response):
            logging.info("Response sent successfully")
            sys.exit(0)
        else:
            logging.error("Failed to send response")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Fatal error in main: {e}")
        logging.error(traceback.format_exc())
        # Try to send error response
        try:
            send_message({'action': 'allow', 'error': str(e)})
        except:
            pass
        sys.exit(1)

if __name__ == '__main__':
    main()

