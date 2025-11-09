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

# Import main obfuscator from project root (like desktop_app_monitor does)
try:
    # Add project root to path
    # From Extension/edge-dlp-ext/native_host.py, go up 2 levels to get to HackPrinceton/
    project_root = script_dir.parent.parent
    # If we're in Extension/edge-dlp-ext/, project_root is Extension/, but we need HackPrinceton/
    # So go up one more level
    if project_root.name == 'Extension':
        project_root = project_root.parent
    
    # Add src to path (like desktop_app_monitor does: sys.path.insert(0, str(Path(__file__).parent / 'src')))
    sys.path.insert(0, str(project_root / 'src'))
    sys.path.insert(0, str(project_root))  # Also add project root for src.detectors imports
    logging.info(f"Project root: {project_root}")
    logging.info(f"Python path: {sys.path[:3]}")
    
    # Import from obfuscator (like desktop_app_monitor: from obfuscator import PIIObfuscator)
    # Note: obfuscator.py uses 'from src.detectors' so we need project_root in path
    from src.obfuscator import PIIObfuscator
    OBFUSCATOR_AVAILABLE = True
    logging.info("Main obfuscator imported successfully")
except Exception as e:
    logging.error(f"Failed to import main obfuscator: {e}")
    logging.error(traceback.format_exc())
    OBFUSCATOR_AVAILABLE = False
    project_root = None

# Fallback regex patterns
PATTERNS = [
    ('API_KEY', re.compile(r'(?:api[_-]?key|secret|sk_live)[\s:=]*[A-Za-z0-9\-_]{20,}', re.I)),
    ('EMAIL', re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}')),
    ('SSN', re.compile(r'\b\d{3}-\d{2}-\d{4}\b')),
    ('JWT', re.compile(r'\beyJ[0-9A-Za-z\-_]+\.[0-9A-Za-z\-_]+\.[0-9A-Za-z\-_]+\b'))
]

# Initialize obfuscator (pre-initialize to avoid delay on first request)
_obfuscator = None
_obfuscator_initializing = False

def get_obfuscator():
    """Get or create obfuscator instance (like desktop_app_monitor)"""
    global _obfuscator, _obfuscator_initializing
    if _obfuscator is None and not _obfuscator_initializing and OBFUSCATOR_AVAILABLE and project_root:
        try:
            _obfuscator_initializing = True
            logging.info("Initializing obfuscator (this may take ~10-15 seconds for first time)...")
            # Use same settings as desktop_app_monitor for consistency
            escrow_path = project_root / "data" / "escrow" / "pii_escrow.db"
            
            # Load config to get consensus settings
            config_path = project_root / "data" / "pii_guard_config.json"
            use_consensus = False
            consensus_mode = 'any_two'
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        use_consensus = config.get('advanced', {}).get('use_consensus', False)
                        consensus_mode = config.get('advanced', {}).get('consensus_mode', 'any_two')
                except Exception as e:
                    logging.warning(f"Failed to load config: {e}, using defaults")
            
            _obfuscator = PIIObfuscator(
                use_regex=True,
                use_spacy=True,
                use_transformer=True,  # Use transformer like desktop_app_monitor
                transformer_model="lakshyakh93/deberta_finetuned_pii",
                escrow_db_path=str(escrow_path),
                confidence_threshold=0.85,  # Higher threshold to avoid false positives
                use_consensus=use_consensus,
                consensus_mode=consensus_mode
            )
            logging.info(f"Obfuscator initialized with transformer - ready for requests (consensus: {use_consensus}, mode: {consensus_mode})")
            _obfuscator_initializing = False
        except Exception as e:
            logging.error(f"Failed to initialize obfuscator: {e}")
            logging.error(traceback.format_exc())
            _obfuscator_initializing = False
            return None
    elif _obfuscator_initializing:
        logging.info("Obfuscator is still initializing, waiting...")
    return _obfuscator

def pre_initialize_obfuscator():
    """Pre-initialize obfuscator in background to avoid delay on first request"""
    if OBFUSCATOR_AVAILABLE and project_root:
        # Start initialization in background (non-blocking)
        import threading
        def init_thread():
            get_obfuscator()
        thread = threading.Thread(target=init_thread, daemon=True)
        thread.start()
        logging.info("Started background obfuscator initialization")

def detect_with_obfuscator(text):
    """Use main obfuscator for detection (like desktop_app_monitor)"""
    obfuscator = get_obfuscator()
    if obfuscator:
        try:
            result = obfuscator.obfuscate(text, source="browser_extension")
            logging.info(f"Obfuscator result: {result.num_redactions} redactions")
            return {
                'has_pii': result.num_redactions > 0,
                'num_redactions': result.num_redactions,
                'obfuscated_text': result.obfuscated_text,
                'original_text': result.original_text,
                'replacements': result.replacements
            }
        except Exception as e:
            logging.error(f"Obfuscation error: {e}")
            logging.error(traceback.format_exc())
            return None
    return None

def detect_fallback(text):
    """Fallback regex detection"""
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

def handle_file_obfuscation(content, file_type, file_name):
    """Obfuscate file content using MCP servers"""
    try:
        logging.info(f"Starting file obfuscation: {file_name}, type: {file_type}, content length: {len(content) if content else 0}")
        
        # Add mcp_servers to path
        if not project_root:
            logging.error("Project root not set - cannot obfuscate file")
            return None
            
        # Add project root and src to path
        sys.path.insert(0, str(project_root))
        sys.path.insert(0, str(project_root / 'src'))
        mcp_servers_path = project_root / 'mcp_servers'
        if not mcp_servers_path.exists():
            logging.error(f"MCP servers path does not exist: {mcp_servers_path}")
            return None
        
        # Import MCP server functions
        try:
            from mcp_servers.unified_server import check_file
            from mcp_servers.code_server import check_code
            from mcp_servers.docx_server import check_docx
            from mcp_servers.pdf_server import check_pdf
            logging.info("MCP server functions imported successfully")
        except ImportError as e:
            logging.error(f"Failed to import MCP servers: {e}")
            logging.error(traceback.format_exc())
            return None
        
        # Create temporary file
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_file = Path(temp_dir) / f"pii_guard_{file_name}"
        
        # Write content to temp file
        try:
            if file_type in ['pdf', 'docx']:
                # Binary file - content is base64 encoded string
                import base64
                if isinstance(content, str):
                    # Decode base64 to bytes
                    binary_content = base64.b64decode(content)
                else:
                    # Already bytes
                    binary_content = content
                with open(temp_file, 'wb') as f:
                    f.write(binary_content)
                logging.info(f"Temp binary file created: {temp_file}, size: {temp_file.stat().st_size} bytes")
            else:
                # Text file - always use UTF-8
                with open(temp_file, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(content if isinstance(content, str) else content.decode('utf-8', errors='replace'))
                logging.info(f"Temp text file created: {temp_file}, size: {temp_file.stat().st_size} bytes")
        except Exception as e:
            logging.error(f"Failed to write temp file: {e}")
            logging.error(traceback.format_exc())
            return None
        
        # Obfuscate based on file type
        result = None
        if file_type == 'code':
            result = check_code(str(temp_file), use_tree_sitter=True)
        elif file_type == 'docx':
            result = check_docx(str(temp_file))
        elif file_type == 'pdf':
            result = check_pdf(str(temp_file))
        elif file_type == 'text':
            # For text files, use unified server or direct obfuscator
            # Use unified server which will handle text files
            result = check_file(str(temp_file))
        else:
            # Use unified server for unknown types
            result = check_file(str(temp_file))
        
        # Clean up temp file
        try:
            temp_file.unlink()
        except:
            pass
        
        # Check for errors first
        if not result:
            logging.error("Obfuscation returned None")
            return None
            
        if isinstance(result, dict) and 'error' in result:
            logging.error(f"Obfuscation error: {result['error']}")
            return None
        
        # IMPORTANT: Check for binary files FIRST (PDF/DOCX) before checking safe_text
        # This ensures we return the binary file, not just the text
        if isinstance(result, dict) and 'safe_pdf' in result and result['safe_pdf']:
            # For PDF, save and read back as base64
            import base64
            safe_file = Path(temp_dir) / f"pii_guard_safe_{file_name}"
            try:
                result['safe_pdf'].save(str(safe_file))
                with open(safe_file, 'rb') as f:
                    content = f.read()
                result['safe_pdf'].close()
                safe_file.unlink()
                # Convert to base64 for JSON transmission
                base64_content = base64.b64encode(content).decode('utf-8')
                logging.info(f"PDF obfuscation successful: {len(base64_content)} chars (base64), {len(content)} bytes (binary)")
                return base64_content
            except Exception as e:
                logging.error(f"Error saving PDF: {e}")
                logging.error(traceback.format_exc())
                if safe_file.exists():
                    safe_file.unlink()
                return None
        elif isinstance(result, dict) and 'safe_docx' in result and result['safe_docx']:
            # For DOCX, we need to save and read back as base64
            import base64
            safe_file = Path(temp_dir) / f"pii_guard_safe_{file_name}"
            try:
                result['safe_docx'].save(str(safe_file))
                with open(safe_file, 'rb') as f:
                    content = f.read()
                safe_file.unlink()
                # Convert to base64 for JSON transmission
                base64_content = base64.b64encode(content).decode('utf-8')
                logging.info(f"DOCX obfuscation successful: {len(base64_content)} chars (base64), {len(content)} bytes (binary)")
                return base64_content
            except Exception as e:
                logging.error(f"Error saving DOCX: {e}")
                logging.error(traceback.format_exc())
                if safe_file.exists():
                    safe_file.unlink()
                return None
        elif isinstance(result, dict) and 'safe_text' in result:
            # For text/code files, return obfuscated text directly
            obfuscated_text = result['safe_text']
            logging.info(f"Text obfuscation successful: {len(obfuscated_text)} chars")
            return obfuscated_text
        
        logging.warning(f"No obfuscated content in result: {result.keys() if isinstance(result, dict) else type(result)}")
        return None
        
    except Exception as e:
        logging.error(f"Error obfuscating file: {e}")
        logging.error(traceback.format_exc())
        return None

def handle_message(msg):
    """Process a message and return a response (like desktop_app_monitor)"""
    try:
        msg_type = msg.get('type', '')
        
        # Handle file obfuscation
        if msg_type == 'obfuscate-file':
            content = msg.get('content', '')
            file_type = msg.get('fileType', '')
            file_name = msg.get('fileName', 'file')
            
            logging.info(f"Obfuscating file: {file_name} (type: {file_type})")
            
            obfuscated = handle_file_obfuscation(content, file_type, file_name)
            
            if obfuscated:
                return {'obfuscated': obfuscated, 'success': True}
            else:
                return {'obfuscated': None, 'success': False, 'error': 'Failed to obfuscate file'}
        
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
        
        # Handle text obfuscation (use obfuscator like desktop_app_monitor)
        text = msg.get('text', '')
        tab_id = msg.get('tabId')
        
        logging.info(f"Processing text for tab {tab_id}: {text[:50]}...")
        
        if not text:
            logging.warning("Empty text received")
            return {'tabId': tab_id, 'action': 'allow', 'error': 'No text provided'}
        
        # Try main obfuscator first (like desktop_app_monitor)
        obf_result = detect_with_obfuscator(text)
        
        if obf_result and obf_result['has_pii']:
            logging.info(f"PII detected via obfuscator: {obf_result['num_redactions']} items")
            # Convert replacements to findings format for compatibility
            findings = []
            if obf_result.get('replacements'):
                for placeholder, original in obf_result['replacements'].items():
                    # Extract entity type from placeholder like {EMAIL_123}
                    entity_type = placeholder.replace('{', '').split('_')[0]
                    # Find position in original text
                    idx = text.find(original)
                    if idx >= 0:
                        findings.append({
                            'type': entity_type,
                            'match': original,
                            'start': idx,
                            'end': idx + len(original)
                        })
            
            return {
                'tabId': tab_id,
                'action': 'replace',
                'replacement': obf_result['obfuscated_text'],
                'findings': findings,
                'num_redactions': obf_result['num_redactions']
            }
        
        # Fallback to regex detection if obfuscator didn't find anything
        findings = detect_fallback(text) if not obf_result or not obf_result.get('has_pii') else []
        
        if findings:
            logging.info(f"Found {len(findings)} potential issues via regex fallback")
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
        
        # No PII detected
        return {'tabId': tab_id, 'action': 'allow'}
        
    except Exception as e:
        logging.error(f"Error handling message: {e}")
        logging.error(traceback.format_exc())
        return {'tabId': msg.get('tabId'), 'action': 'allow', 'error': str(e)}

def main():
    """Main entry point - handles a single message for sendNativeMessage"""
    try:
        logging.info("Entering main - reading one message...")
        
        # Pre-initialize obfuscator in background to avoid delay on first request
        # Note: Since sendNativeMessage spawns new process each time, we initialize
        # immediately when process starts so it's ready when message arrives
        if OBFUSCATOR_AVAILABLE and project_root and _obfuscator is None:
            logging.info("Pre-initializing obfuscator for faster first request...")
            # Initialize synchronously since we're in a new process anyway
            # This way the model is ready when we process the message
            get_obfuscator()
        
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

