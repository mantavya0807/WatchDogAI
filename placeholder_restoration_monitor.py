"""
Placeholder Restoration Monitor - TRANSFORMER-BASED (FIXED v2)
===============================================================

FIXED: SQLite threading issue - initialize DB in monitor thread
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import win32clipboard
import win32con
import time
import re
import threading
import hashlib
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from escrow_db import EscrowDatabase
from detectors.transformer_detector import TransformerDetector


class PlaceholderRestorationMonitor:
    """
    Monitors clipboard for placeholders and restores them using transformer context
    """
    
    # Pattern to detect our placeholders
    PLACEHOLDER_PATTERN = re.compile(r'\{([A-Z_]+_\d+)\}')
    
    # Debouncing to prevent infinite loops
    DEBOUNCE_TIME = 0.5  # 500ms
    
    def __init__(self):
        print("=" * 70)
        print("PLACEHOLDER RESTORATION MONITOR (Transformer-Based)")
        print("=" * 70)
        print()
        
        # FIXED: Don't initialize escrow_db here - will initialize in monitor thread
        self.escrow_db = None
        self.transformer = None  # Lazy load in thread
        
        # State tracking for loop prevention
        self.last_clipboard_hash = None
        self.last_restoration_time = 0
        self.processing = False
        self.running = False
        
        # Track sequence to detect external changes
        self.last_clipboard_seq = 0
        
        # History to detect loops (circular replacements)
        self.recent_hashes = []  # Last 5 clipboard hashes
        self.max_history = 5
        
        print("✓ Restoration monitor initialized")
        print("  Mode: Transformer-based context restoration")
        print("  Loop prevention: Enabled")
        print()
    
    def _get_clipboard_sequence(self) -> int:
        """Get clipboard sequence number (increments on each change)"""
        try:
            return win32clipboard.GetClipboardSequenceNumber()
        except:
            return 0
    
    def _get_clipboard_text(self) -> Optional[str]:
        """Safely get text from clipboard"""
        try:
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                    return win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
            finally:
                win32clipboard.CloseClipboard()
        except:
            pass
        return None
    
    def _set_clipboard_text(self, text: str) -> bool:
        """Safely set clipboard text with retry logic"""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                win32clipboard.OpenClipboard()
                try:
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
                    return True
                finally:
                    win32clipboard.CloseClipboard()
            except Exception as e:
                if attempt == max_attempts - 1:
                    print(f"✗ Failed to set clipboard after {max_attempts} attempts: {e}")
                time.sleep(0.05)  # Small delay before retry
        return False
    
    def _compute_hash(self, text: str) -> str:
        """Compute hash of text for loop detection"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _is_loop_detected(self, text_hash: str) -> bool:
        """Check if we're in an infinite loop"""
        # If we've seen this exact content in last N changes, it's a loop
        return text_hash in self.recent_hashes
    
    def _update_history(self, text_hash: str):
        """Update history of recent clipboard content"""
        self.recent_hashes.append(text_hash)
        if len(self.recent_hashes) > self.max_history:
            self.recent_hashes.pop(0)
    
    def _extract_placeholders(self, text: str) -> List[Tuple[str, str]]:
        """
        Extract placeholders from text with their full match
        
        Returns:
            List of (full_match, placeholder_id) tuples
            e.g., [("{EMAIL_1}", "EMAIL_1"), ("{PERSON_2}", "PERSON_2")]
        """
        matches = []
        for match in self.PLACEHOLDER_PATTERN.finditer(text):
            full_match = match.group(0)  # e.g., "{EMAIL_1}"
            placeholder_id = match.group(1)  # e.g., "EMAIL_1"
            matches.append((full_match, placeholder_id))
        return matches
    
    def _restore_via_escrow(self, text: str, placeholders: List[Tuple[str, str]]) -> Tuple[str, Dict]:
        """
        Restore placeholders using escrow database lookup
        
        Returns:
            (restored_text, metadata)
        """
        restored = text
        restored_count = 0
        missing_placeholders = []
        
        for full_match, placeholder_id in placeholders:
            # Use correct method name 'retrieve'
            original = self.escrow_db.retrieve(placeholder_id)
            if original:
                restored = restored.replace(full_match, original)
                restored_count += 1
            else:
                missing_placeholders.append(placeholder_id)
        
        metadata = {
            'method': 'escrow_db',
            'total_placeholders': len(placeholders),
            'restored_count': restored_count,
            'missing_count': len(missing_placeholders),
            'missing_placeholders': missing_placeholders,
        }
        
        return restored, metadata
    
    def _restore_via_transformer(self, text: str, placeholders: List[Tuple[str, str]], 
                                  missing_placeholders: List[str]) -> Tuple[str, Dict]:
        """
        Use transformer to intelligently restore missing placeholders based on context
        """
        if not missing_placeholders or not self.transformer:
            return text, {'method': 'transformer', 'restored_count': 0}
        
        print(f"  🤖 Using transformer to infer {len(missing_placeholders)} missing placeholder(s)...")
        
        restored = text
        restored_count = 0
        inferences = {}
        
        for placeholder_id in missing_placeholders:
            # Extract placeholder type (e.g., "EMAIL" from "EMAIL_1")
            placeholder_type = placeholder_id.rsplit('_', 1)[0]
            full_match = f"{{{placeholder_id}}}"
            
            # Get context window around placeholder
            placeholder_pos = text.find(full_match)
            if placeholder_pos == -1:
                continue
            
            # Extract context (50 chars before and after)
            context_start = max(0, placeholder_pos - 50)
            context_end = min(len(text), placeholder_pos + len(full_match) + 50)
            context = text[context_start:context_end]
            
            # Use transformer to generate synthetic value based on context
            inferred_value = self._infer_value_from_context(
                context, 
                placeholder_type, 
                full_match
            )
            
            if inferred_value:
                restored = restored.replace(full_match, inferred_value)
                restored_count += 1
                inferences[placeholder_id] = inferred_value
                print(f"    • {{{placeholder_id}}} → {inferred_value[:30]}...")
        
        metadata = {
            'method': 'transformer',
            'restored_count': restored_count,
            'inferences': inferences,
        }
        
        return restored, metadata
    
    def _infer_value_from_context(self, context: str, placeholder_type: str, 
                                   placeholder: str) -> Optional[str]:
        """Use transformer to infer what the placeholder should be"""
        if not self.transformer:
            return None
        
        try:
            # Strategy 1: Use transformer to detect similar PII in context
            result = self.transformer.detect(context)
            
            if result and result.entities:
                # Find entities matching the placeholder type
                matching_entities = [
                    e for e in result.entities 
                    if e.entity_type == placeholder_type
                ]
                
                if matching_entities:
                    # Use the closest entity by position
                    placeholder_pos = context.find(placeholder)
                    closest_entity = min(
                        matching_entities,
                        key=lambda e: abs(e.start - placeholder_pos)
                    )
                    return closest_entity.text
            
            # Strategy 2: Generate synthetic placeholder based on type
            return self._generate_synthetic_value(placeholder_type)
        
        except Exception as e:
            print(f"    ✗ Transformer inference failed: {e}")
            return None
    
    def _generate_synthetic_value(self, placeholder_type: str) -> str:
        """Generate a synthetic placeholder value when we can't infer from context"""
        synthetic_values = {
            'EMAIL': '[REDACTED EMAIL]',
            'PERSON': '[REDACTED NAME]',
            'PHONE': '[REDACTED PHONE]',
            'SSN': '[REDACTED SSN]',
            'CREDIT_CARD': '[REDACTED CARD]',
            'API_KEY': '[REDACTED KEY]',
            'PASSWORD': '[REDACTED PASSWORD]',
            'IP_ADDRESS': '[REDACTED IP]',
            'URL': '[REDACTED URL]',
        }
        return synthetic_values.get(placeholder_type, '[REDACTED]')
    
    def _restore_placeholders(self, text: str) -> Tuple[str, Dict]:
        """Main restoration logic: Try escrow DB first, then transformer"""
        # Extract all placeholders
        placeholders = self._extract_placeholders(text)
        if not placeholders:
            return text, {'has_placeholders': False}
        
        print(f"  📋 Found {len(placeholders)} placeholder(s) in clipboard")
        
        # Step 1: Try escrow DB lookup (fast, exact matches)
        restored_text, escrow_metadata = self._restore_via_escrow(text, placeholders)
        
        print(f"    • Escrow DB: Restored {escrow_metadata['restored_count']}/{escrow_metadata['total_placeholders']}")
        
        # Step 2: If any placeholders missing, try transformer (slower, inferential)
        if escrow_metadata['missing_count'] > 0:
            print(f"    • Missing {escrow_metadata['missing_count']} value(s), trying transformer...")
            
            restored_text, transformer_metadata = self._restore_via_transformer(
                restored_text,
                placeholders,
                escrow_metadata['missing_placeholders']
            )
            
            # Combine metadata
            metadata = {
                'has_placeholders': True,
                'total_placeholders': len(placeholders),
                'escrow_restored': escrow_metadata['restored_count'],
                'transformer_restored': transformer_metadata['restored_count'],
                'fully_restored': (
                    escrow_metadata['restored_count'] + 
                    transformer_metadata['restored_count'] == 
                    len(placeholders)
                ),
            }
        else:
            # All restored via escrow
            metadata = {
                'has_placeholders': True,
                'total_placeholders': len(placeholders),
                'escrow_restored': escrow_metadata['restored_count'],
                'transformer_restored': 0,
                'fully_restored': True,
            }
        
        return restored_text, metadata
    
    def _process_clipboard(self):
        """Process current clipboard content"""
        if self.processing:
            return
        
        self.processing = True
        
        try:
            # Get current clipboard
            text = self._get_clipboard_text()
            if not text or len(text) < 5:
                return
            
            # Compute hash for loop detection
            text_hash = self._compute_hash(text)
            
            # Check if this is same as last processed
            if text_hash == self.last_clipboard_hash:
                return
            
            # Check for infinite loop
            if self._is_loop_detected(text_hash):
                print(f"\n⚠️  LOOP DETECTED - Skipping restoration to prevent infinite loop")
                return
            
            # Check if we're in debounce period
            now = time.time()
            if now - self.last_restoration_time < self.DEBOUNCE_TIME:
                return
            
            # Check if text has placeholders
            if not self.PLACEHOLDER_PATTERN.search(text):
                # No placeholders - existing obfuscation logic will handle this
                return
            
            # Text has placeholders - THIS IS OUR JOB
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔄 RESTORATION TRIGGERED")
            print(f"  Clipboard length: {len(text)} chars")
            
            # Restore placeholders
            restored_text, metadata = self._restore_placeholders(text)
            
            if metadata.get('has_placeholders') and metadata.get('fully_restored'):
                print(f"  ✅ RESTORED: {metadata['escrow_restored']} from DB + {metadata['transformer_restored']} from AI")
                
                # Update clipboard with restored text
                if self._set_clipboard_text(restored_text):
                    # Update state
                    self.last_clipboard_hash = self._compute_hash(restored_text)
                    self.last_restoration_time = now
                    self._update_history(text_hash)
                    self._update_history(self.last_clipboard_hash)
                    
                    print(f"  ✓ Clipboard updated with restored values")
                else:
                    print(f"  ✗ Failed to update clipboard")
            
            elif metadata.get('has_placeholders'):
                print(f"  ⚠️  PARTIAL: Restored {metadata['escrow_restored'] + metadata['transformer_restored']}/{metadata['total_placeholders']}")
                print(f"  → Some placeholders could not be restored")
        
        except Exception as e:
            print(f"✗ Error processing clipboard: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.processing = False
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        print("✓ Restoration monitor started")
        
        # FIXED: Initialize escrow_db in THIS thread (monitor thread)
        print("  Initializing escrow DB in monitoring thread...")
        try:
            self.escrow_db = EscrowDatabase()
            print("✓ Escrow DB initialized")
        except Exception as e:
            print(f"✗ Escrow DB initialization failed: {e}")
            print("  Cannot continue without escrow DB")
            return
        
        # Initialize transformer
        print("  Initializing transformer in monitoring thread...")
        try:
            self.transformer = TransformerDetector(
                model_name='lakshyakh93/deberta_finetuned_pii'
            )
            print("✓ Transformer initialized\n")
        except Exception as e:
            print(f"⚠️  Transformer initialization failed: {e}")
            print("  Will use escrow DB only for restoration\n")
        
        while self.running:
            try:
                # Check if clipboard changed
                current_seq = self._get_clipboard_sequence()
                
                if current_seq != self.last_clipboard_seq:
                    self.last_clipboard_seq = current_seq
                    self._process_clipboard()
                
                # Check every 100ms
                time.sleep(0.1)
            
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error in monitor loop: {e}")
                time.sleep(1)
    
    def start(self):
        """Start monitoring"""
        if self.running:
            print("Already running!")
            return
        
        print("\n" + "=" * 70)
        print("MONITORING ACTIVE")
        print("=" * 70)
        print()
        print("Restoration strategy:")
        print("  1. Detect placeholders in clipboard")
        print("  2. Try escrow DB lookup (fast)")
        print("  3. Try transformer inference (smart)")
        print("  4. Update clipboard with restored values")
        print()
        print("Loop prevention: Enabled")
        print("Press Ctrl+C to stop")
        print()
        
        self.running = True
        
        # Start monitoring in separate thread
        monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        monitor_thread.start()
        
        try:
            # Keep main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n⚠️  Stopping restoration monitor...")
            self.stop()
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        print("✓ Restoration monitor stopped")


def main():
    """Run the restoration monitor"""
    monitor = PlaceholderRestorationMonitor()
    
    print("=" * 70)
    print("TESTING INSTRUCTIONS")
    print("=" * 70)
    print()
    print("This monitor ONLY handles de-obfuscation (placeholder restoration).")
    print("Run clipboard_monitor_paste_based.py separately for obfuscation.")
    print()
    print("Test scenario:")
    print("  1. Run clipboard_monitor_paste_based.py (handles obfuscation)")
    print("  2. Run this file (handles restoration)")
    print("  3. Copy text with PII → Gets obfuscated")
    print("  4. Copy obfuscated text → Gets restored")
    print()
    print("=" * 70)
    print()
    
    monitor.start()


if __name__ == "__main__":
    main()