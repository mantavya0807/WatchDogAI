"""
Amplitude Data Fetcher
Fetches event data from Amplitude Export API and aggregates it for dashboard
"""

import json
import base64
import gzip
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))


class AmplitudeDataFetcher:
    """Fetches and aggregates data from Amplitude Export API"""
    
    # Note: Export API endpoint - may require different authentication
    # Alternative: Use Dashboard REST API instead for aggregated data
    EXPORT_API_ENDPOINT = "https://amplitude.com/api/2/export"
    
    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key
        self.auth_string = base64.b64encode(f"{api_key}:{secret_key}".encode()).decode()
    
    def _make_request(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Make request to Amplitude Export API
        
        Args:
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            
        Returns:
            List of event dictionaries
        """
        url = f"{self.EXPORT_API_ENDPOINT}?start={start_date}&end={end_date}"
        
        # Export API uses Basic Auth with API key:Secret key
        headers = {
            "Authorization": f"Basic {self.auth_string}",
            "Accept": "application/json"
        }
        
        try:
            print(f"  📡 Calling Amplitude API: {url}")
            response = requests.get(url, headers=headers, timeout=30)
            print(f"  📡 Response status: {response.status_code}")
            
            if response.status_code == 200:
                # Export API returns gzipped newline-delimited JSON
                print(f"  📄 Response length: {len(response.content)} bytes")
                print(f"  📄 Content-Encoding: {response.headers.get('Content-Encoding', 'none')}")
                
                # Amplitude Export API always returns gzipped data
                # Try decompression first - if it fails, fall back to plain text
                print("  🔓 Attempting to decompress response...")
                try:
                    decompressed = gzip.decompress(response.content)
                    text = decompressed.decode('utf-8')
                    print(f"  ✓ Successfully decompressed to {len(text)} characters")
                except Exception as e:
                    # If decompression fails, try as plain text
                    print(f"  ⚠ Decompression failed: {e}")
                    print(f"  📄 Trying as plain text...")
                    try:
                        text = response.text
                        print(f"  ✓ Using plain text ({len(text)} characters)")
                    except:
                        print(f"  ❌ Failed to decode response")
                        return []
                
                # Parse newline-delimited JSON
                events = []
                lines = text.strip().split('\n')
                print(f"  📄 Number of lines in response: {len(lines)}")
                
                for i, line in enumerate(lines):
                    if line.strip():
                        try:
                            event = json.loads(line)
                            events.append(event)
                        except json.JSONDecodeError as e:
                            if i < 5:  # Only log first few errors
                                print(f"  ⚠ JSON parse error on line {i+1}: {e}")
                                print(f"     Line content: {line[:100]}")
                            continue
                
                print(f"  ✓ Parsed {len(events)} events from response")
                if len(events) > 0:
                    print(f"  📊 Sample event keys: {list(events[0].keys())}")
                    print(f"  📊 Sample event type: {events[0].get('event_type', 'N/A')}")
                return events
            elif response.status_code == 401:
                print("  ❌ Authentication failed - check API key and secret key")
                return []
            elif response.status_code == 403:
                print("  ❌ Access forbidden - check API key permissions")
                return []
            else:
                print(f"  ❌ API error: {response.status_code} - {response.text[:200]}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Network error: {e}")
            return []
    
    def fetch_events(self, days: int = 7) -> List[Dict]:
        """
        Fetch events from Amplitude for the last N days
        
        Args:
            days: Number of days to fetch (default 7 for recent data)
            
        Returns:
            List of event dictionaries
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        
        print(f"Fetching events from {start_str} to {end_str}...")
        print(f"  (Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})")
        events = self._make_request(start_str, end_str)
        print(f"✓ Fetched {len(events)} events from Amplitude")
        
        return events
    
    def aggregate_stats(self, events: List[Dict]) -> Dict[str, Any]:
        """
        Aggregate events into dashboard statistics
        
        Args:
            events: List of event dictionaries from Amplitude
            
        Returns:
            Dictionary with aggregated statistics
        """
        if not events:
            return self._get_empty_stats()
        
        # Initialize counters
        total_detections = 0
        total_protections = 0
        entity_types = defaultdict(int)
        sources = defaultdict(int)
        apps = defaultdict(int)
        users = defaultdict(int)
        time_series = defaultdict(int)
        undo_count = 0
        
        # Process events
        for event in events:
            event_type = event.get('event_type', '')
            props = event.get('event_properties', {})
            timestamp = event.get('time', 0)
            
            # Convert timestamp to date
            if timestamp:
                try:
                    event_date = datetime.fromtimestamp(timestamp / 1000)
                    date_key = event_date.strftime('%Y-%m-%d')
                    hour_key = event_date.strftime('%H:00')
                except:
                    date_key = None
                    hour_key = None
            else:
                date_key = None
                hour_key = None
            
            if event_type == 'PII Detected':
                total_detections += 1
                entity_type = props.get('entity_type', 'UNKNOWN')
                source = props.get('source', 'unknown')
                app_name = props.get('app_name', 'unknown')
                user_id = event.get('user_id', 'unknown')
                
                entity_types[entity_type] += props.get('num_entities', 1)
                sources[source] += 1
                apps[app_name] += 1
                users[user_id] += 1
                
                if hour_key:
                    time_series[hour_key] += 1
            
            elif event_type == 'PII Protected':
                total_protections += 1
            
            elif event_type == 'User Undo':
                undo_count += 1
        
        # Calculate protection rate
        protection_rate = (total_protections / total_detections * 100) if total_detections > 0 else 0
        
        # Get top entities, sources, apps
        top_entities = dict(sorted(entity_types.items(), key=lambda x: x[1], reverse=True)[:6])
        top_sources = dict(sorted(sources.items(), key=lambda x: x[1], reverse=True)[:5])
        top_apps = dict(sorted(apps.items(), key=lambda x: x[1], reverse=True)[:5])
        top_users = dict(sorted(users.items(), key=lambda x: x[1], reverse=True)[:10])
        
        # Time series data (last 6 hours)
        now = datetime.now()
        hours = []
        counts = []
        for i in range(6):
            hour = (now - timedelta(hours=5-i)).strftime('%H:00')
            hours.append(hour)
            counts.append(time_series.get(hour, 0))
        
        # Risk score calculation (simplified)
        risk_score = min(100, max(0, 50 + (total_detections / 100) - (protection_rate / 2)))
        
        return {
            'total': total_detections,
            'protected': round(protection_rate, 1),
            'users': len(users),
            'apps': len([a for a in apps.values() if a > 0]),
            'time': {
                'hours': hours,
                'counts': counts
            },
            'entities': top_entities,
            'sources': top_sources,
            'apps_data': top_apps,
            'users_data': top_users,
            'undo_count': undo_count,
            'risk_score': round(risk_score, 1)
        }
    
    def _get_empty_stats(self) -> Dict[str, Any]:
        """Return empty stats structure"""
        now = datetime.now()
        hours = []
        for i in range(6):
            hour = (now - timedelta(hours=5-i)).strftime('%H:00')
            hours.append(hour)
        
        return {
            'total': 0,
            'protected': 0,
            'users': 0,
            'apps': 0,
            'time': {
                'hours': hours,
                'counts': [0] * 6
            },
            'entities': {},
            'sources': {},
            'apps_data': {},
            'users_data': {},
            'undo_count': 0,
            'risk_score': 0
        }


def get_fetcher() -> Optional[AmplitudeDataFetcher]:
    """Get AmplitudeDataFetcher instance from config"""
    # Try multiple possible config paths
    possible_paths = [
        Path(__file__).parent / "config" / "amplitude_config.json",  # From amplitude_integration/
        Path(__file__).parent.parent / "amplitude_integration" / "config" / "amplitude_config.json",  # From project root
        Path(__file__).parent / "amplitude_integration" / "config" / "amplitude_config.json",  # Alternative
    ]
    
    config_path = None
    for path in possible_paths:
        if path.exists():
            config_path = path
            break
    
    if not config_path:
        print("⚠ Config file not found")
        return None
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        api_key = config.get('api_key', '')
        secret_key = config.get('secret_key', '')
        
        if not api_key:
            print("⚠ API key not found in config")
            return None
        
        if not secret_key:
            print("⚠ Secret key not found in config (using mock data)")
            return None
        
        return AmplitudeDataFetcher(api_key, secret_key)
    except Exception as e:
        print(f"Error loading config: {e}")
        return None

