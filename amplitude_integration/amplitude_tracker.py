"""
Amplitude Event Tracking System for PII Guard
Sends PII detection events to Amplitude Analytics HTTP V2 API
"""

import json
import time
import threading
import uuid
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from queue import Queue
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.escrow_db import EscrowDatabase
except:
    EscrowDatabase = None


class AmplitudeTracker:
    """Event tracking system for Amplitude Analytics"""
    
    API_ENDPOINT = "https://api2.amplitude.com/2/httpapi"
    
    def __init__(self, api_key: str, device_id: Optional[str] = None, user_id: Optional[str] = None, use_mock_data: bool = False, mock_interval: int = 5):
        self.api_key = api_key
        self.device_id = device_id or self._generate_device_id()
        self.user_id = user_id or os.getenv('USERNAME', os.getenv('USER', 'unknown'))
        self.use_mock_data = use_mock_data
        self.mock_interval = mock_interval
        self.mock_data_thread = None
        
        self.event_queue = Queue(maxsize=1000)
        self.batch_size = 10
        self.flush_interval = 30
        
        self.rate_limit = 30
        self.last_send_time = 0
        self.events_sent_this_second = 0
        self.rate_limit_lock = threading.Lock()
        
        self.retry_attempts = 3
        self.retry_backoff_base = 2
        
        self.stats = {
            'events_queued': 0,
            'events_sent': 0,
            'events_failed': 0,
            'batches_sent': 0,
            'batches_failed': 0,
            'rate_limits_hit': 0,
            'errors': []
        }
        
        self.running = False
        self.send_thread = None
        
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.retry_attempts,
            backoff_factor=self.retry_backoff_base,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        
        if self.use_mock_data:
            print(f"✓ Amplitude Tracker (Mock Data Mode: {mock_interval}s)")
        else:
            print(f"✓ Amplitude Tracker initialized")
    
    def _generate_device_id(self) -> str:
        """Generate or retrieve persistent device ID"""
        config_path = Path(__file__).parent / "config" / "amplitude_config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    if config.get('device_id'):
                        return config['device_id']
            except:
                pass
        
        device_id = str(uuid.uuid4())
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
            else:
                config = {}
            config['device_id'] = device_id
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except:
            pass
        
        return device_id
    
    def _check_rate_limit(self) -> bool:
        """Check if we can send events (rate limiting)"""
        with self.rate_limit_lock:
            current_time = time.time()
            if current_time - self.last_send_time >= 1.0:
                self.events_sent_this_second = 0
                self.last_send_time = current_time
            if self.events_sent_this_second >= self.rate_limit:
                return False
            return True
    
    def _increment_rate_limit(self):
        """Increment rate limit counter"""
        with self.rate_limit_lock:
            self.events_sent_this_second += 1
    
    def _create_event(self, event_type: str, event_properties: Dict[str, Any], insert_id: Optional[str] = None) -> Dict[str, Any]:
        """Create an Amplitude event"""
        return {
            "event_type": event_type,
            "user_id": self.user_id,
            "device_id": self.device_id,
            "event_properties": event_properties,
            "time": int(time.time() * 1000),
            "insert_id": insert_id or str(uuid.uuid4()),
            "platform": "Windows",
            "os_name": "Windows",
            "app_version": "1.0.0"
        }
    
    def _send_batch(self, events: List[Dict[str, Any]]) -> bool:
        """Send a batch of events to Amplitude"""
        if not events:
            return True
        
        if self.api_key == "MOCK_API_KEY_FOR_DEMO":
            self._increment_rate_limit()
            self.stats['events_sent'] += len(events)
            self.stats['batches_sent'] += 1
            return True
        
        if not self._check_rate_limit():
            self.stats['rate_limits_hit'] += 1
            time.sleep(0.1)
            if not self._check_rate_limit():
                return False
        
        payload = {"api_key": self.api_key, "events": events}
        
        for attempt in range(self.retry_attempts):
            try:
                response = self.session.post(
                    self.API_ENDPOINT,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('code') == 200:
                        self._increment_rate_limit()
                        self.stats['events_sent'] += len(events)
                        self.stats['batches_sent'] += 1
                        return True
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        self.stats['errors'].append(f"API Error: {error_msg}")
                        if response.status_code == 400:
                            break
                
                elif response.status_code == 429:
                    wait_time = (self.retry_backoff_base ** attempt) * 0.5
                    time.sleep(wait_time)
                    self.stats['rate_limits_hit'] += 1
                    continue
                
                elif response.status_code in [401, 403]:
                    self.stats['errors'].append(f"Auth Error: {response.status_code}")
                    break
                
                else:
                    wait_time = (self.retry_backoff_base ** attempt) * 0.5
                    time.sleep(wait_time)
                    continue
                    
            except requests.exceptions.RequestException as e:
                wait_time = (self.retry_backoff_base ** attempt) * 0.5
                time.sleep(wait_time)
                if attempt == self.retry_attempts - 1:
                    self.stats['errors'].append(f"Network Error: {str(e)}")
        
        self.stats['events_failed'] += len(events)
        self.stats['batches_failed'] += 1
        return False
    
    def _send_worker(self):
        """Background worker thread that sends events"""
        batch = []
        last_flush = time.time()
        
        while self.running:
            try:
                try:
                    event = self.event_queue.get(timeout=1.0)
                    batch.append(event)
                    self.stats['events_queued'] += 1
                except:
                    pass
                
                current_time = time.time()
                should_flush = (
                    len(batch) >= self.batch_size or
                    (batch and (current_time - last_flush) >= self.flush_interval)
                )
                
                if should_flush and batch:
                    self._send_batch(batch)
                    batch = []
                    last_flush = current_time
                
                if not self.event_queue.empty():
                    self.event_queue.task_done()
                    
            except Exception as e:
                self.stats['errors'].append(f"Worker Error: {str(e)}")
                time.sleep(1)
        
        if batch:
            self._send_batch(batch)
    
    def _generate_mock_event(self):
        """Generate a random mock PII detection event"""
        import random
        
        entity_types = ["EMAIL", "PHONE", "SSN", "PERSON", "CREDIT_CARD", "LOCATION"]
        sources = ["clipboard", "typing", "image"]
        apps = ["slack.exe", "teams.exe", "chrome.exe", "outlook.exe", "discord.exe"]
        
        entity_type = random.choice(entity_types)
        source = random.choice(sources)
        app_name = random.choice(apps)
        confidence = round(random.uniform(0.85, 0.99), 2)
        num_entities = random.randint(1, 3)
        detection_time = round(random.uniform(50, 300), 1)
        
        self.track_pii_detection(
            entity_type=entity_type,
            source=source,
            app_name=app_name,
            confidence_score=confidence,
            num_entities=num_entities,
            detection_time_ms=detection_time
        )
        
        protection_methods = {
            "clipboard": "placeholder",
            "typing": "placeholder",
            "image": "blur"
        }
        
        self.track_pii_protection(
            entity_type=entity_type,
            source=source,
            app_name=app_name,
            protection_method=protection_methods.get(source, "placeholder")
        )
    
    def _mock_data_worker(self):
        """Background worker that generates mock events periodically"""
        while self.running and self.use_mock_data:
            try:
                self._generate_mock_event()
                time.sleep(self.mock_interval)
            except Exception as e:
                self.stats['errors'].append(f"Mock Data Error: {str(e)}")
                time.sleep(self.mock_interval)
    
    def track_event(self, event_type: str, event_properties: Dict[str, Any], insert_id: Optional[str] = None):
        """Queue an event for sending"""
        if not self.api_key:
            return
        
        event = self._create_event(event_type, event_properties, insert_id)
        
        try:
            self.event_queue.put_nowait(event)
        except:
            try:
                self.event_queue.get_nowait()
                self.event_queue.put_nowait(event)
            except:
                pass
    
    def track_pii_detection(self, entity_type: str, source: str, app_name: str, confidence_score: float, num_entities: int, detection_time_ms: float):
        """Track PII detection event"""
        self.track_event(
            "PII Detected",
            {
                "entity_type": entity_type,
                "source": source,
                "app_name": app_name,
                "confidence_score": confidence_score,
                "num_entities": num_entities,
                "detection_time_ms": detection_time_ms
            }
        )
    
    def track_pii_protection(self, entity_type: str, source: str, app_name: str, protection_method: str):
        """Track PII protection event"""
        self.track_event(
            "PII Protected",
            {
                "entity_type": entity_type,
                "source": source,
                "app_name": app_name,
                "protection_method": protection_method
            }
        )
    
    def track_user_undo(self, source: str, time_to_undo_seconds: float):
        """Track user undo event"""
        self.track_event(
            "User Undo",
            {
                "source": source,
                "time_to_undo_seconds": time_to_undo_seconds
            }
        )
    
    def track_system_start(self, detectors_enabled: List[str], sources_enabled: List[str]):
        """Track system startup event"""
        self.track_event(
            "System Started",
            {
                "detectors_enabled": detectors_enabled,
                "sources_enabled": sources_enabled
            }
        )
    
    def track_whitelist_applied(self, app_name: str, reason: str):
        """Track whitelist application event"""
        self.track_event(
            "Whitelist Applied",
            {
                "app_name": app_name,
                "reason": reason
            }
        )
    
    def flush(self):
        """Force immediate send of queued events"""
        # Wait for queue to be processed
        import time
        max_wait = 30  # seconds
        start = time.time()
        while not self.event_queue.empty() and (time.time() - start) < max_wait:
            time.sleep(0.5)
        # Give worker thread a moment to send final batch
        time.sleep(2)
    
    def start(self):
        """Start background worker thread"""
        if self.running:
            return
        
        self.running = True
        self.send_thread = threading.Thread(target=self._send_worker, daemon=True)
        self.send_thread.start()
        
        if self.use_mock_data:
            self.mock_data_thread = threading.Thread(target=self._mock_data_worker, daemon=True)
            self.mock_data_thread.start()
    
    def stop(self):
        """Stop background worker thread"""
        if not self.running:
            return
        
        self.running = False
        if self.send_thread:
            self.send_thread.join(timeout=5)
        
        batch = []
        while not self.event_queue.empty():
            try:
                event = self.event_queue.get_nowait()
                batch.append(event)
            except:
                break
        
        if batch:
            self._send_batch(batch)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get tracking statistics"""
        return {
            **self.stats,
            'queue_size': self.event_queue.qsize(),
            'device_id': self.device_id,
            'user_id': self.user_id
        }


# Singleton instance
_tracker_instance: Optional[AmplitudeTracker] = None
_tracker_lock = threading.Lock()


def get_tracker(api_key: Optional[str] = None, use_mock_data: Optional[bool] = None, mock_interval: Optional[int] = None) -> Optional[AmplitudeTracker]:
    """Get or create singleton tracker instance"""
    global _tracker_instance
    
    if not api_key:
        config_path = Path(__file__).parent / "config" / "amplitude_config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    api_key = config.get('api_key', '')
                    if use_mock_data is None:
                        use_mock_data = config.get('use_mock_data', True)
                    if mock_interval is None:
                        mock_interval = config.get('mock_data_interval_seconds', 5)
                    if not config.get('enabled', False) and not use_mock_data:
                        return None
            except:
                pass
    
    if not api_key and use_mock_data:
        api_key = "MOCK_API_KEY_FOR_DEMO"
    
    if not api_key:
        return None
    
    with _tracker_lock:
        if _tracker_instance is None:
            _tracker_instance = AmplitudeTracker(
                api_key=api_key,
                use_mock_data=use_mock_data if use_mock_data is not None else True,
                mock_interval=mock_interval if mock_interval is not None else 5
            )
            _tracker_instance.start()
        
        return _tracker_instance
