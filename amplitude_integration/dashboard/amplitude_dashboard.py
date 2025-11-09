"""
Amplitude Dashboard - Flask Web Application
Custom dashboard with centered content and proper chart ratios
Uses Amplitude Export API to fetch real event data
"""

import os
import json
from pathlib import Path
from flask import Flask, render_template, jsonify
from datetime import datetime, timedelta
import random
import sys

# Add parent directories to path
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
amplitude_integration_dir = current_dir.parent

# Add paths in order: project root, amplitude_integration, current dir
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(amplitude_integration_dir))
sys.path.insert(0, str(current_dir))

try:
    # Try importing from amplitude_integration package
    from amplitude_integration.amplitude_data_fetcher import get_fetcher
    AMPLITUDE_FETCHER_AVAILABLE = True
except ImportError:
    try:
        # Fallback: try direct import
        from amplitude_data_fetcher import get_fetcher
        AMPLITUDE_FETCHER_AVAILABLE = True
    except Exception as e:
        AMPLITUDE_FETCHER_AVAILABLE = False
        print(f"⚠ Amplitude fetcher not available: {e}")

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

CONFIG_PATH = Path(__file__).parent.parent / "config" / "amplitude_config.json"
DEFAULT_PORT = 5000

# Cache for fetched data
_data_cache = None
_cache_timestamp = None
CACHE_DURATION = 60  # Cache for 60 seconds


def load_config():
    """Load configuration from JSON file"""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
        except:
            pass
    
    return {
        "embed_url": "",
        "dashboard_title": "PII Guard Enterprise Analytics"
    }


def get_mock_stats():
    """Generate mock stats as fallback"""
    now = datetime.now()
    hours = []
    counts = []
    
    for i in range(6):
        date = now - timedelta(hours=5-i)
        hours.append(date.strftime('%H:00'))
        counts.append(random.randint(2, 8))
    
    return {
        'total': sum(counts),
        'protected': 98,
        'users': 8,
        'apps': 3,
        'time': {
            'hours': hours,
            'counts': counts
        },
        'entities': {
            'EMAIL': random.randint(15, 25),
            'PHONE': random.randint(10, 18),
            'SSN': random.randint(4, 10),
            'PERSON': random.randint(6, 14)
        },
        'sources': {
            'clipboard': random.randint(20, 30),
            'typing': random.randint(12, 20),
            'image': random.randint(4, 10)
        },
        'apps_data': {
            'slack.exe': random.randint(12, 18),
            'teams.exe': random.randint(8, 15),
            'chrome.exe': random.randint(6, 12)
        },
        'risk_score': 73,
        'risk_trend': {
            'days': [f'Day {i+1}' for i in range(30)],
            'scores': [random.randint(65, 85) for _ in range(30)]
        },
        'users_data': {
            'user1': random.randint(20, 30),
            'user2': random.randint(15, 25),
            'user3': random.randint(10, 20)
        }
    }


def fetch_amplitude_stats():
    """Fetch stats from Amplitude Export API"""
    global _data_cache, _cache_timestamp
    
    # Check cache
    if _data_cache and _cache_timestamp:
        age = (datetime.now() - _cache_timestamp).total_seconds()
        if age < CACHE_DURATION:
            print("📊 Using cached data (from Amplitude)" if _data_cache.get('_source') == 'amplitude' else "📊 Using cached data (mock)")
            return _data_cache
    
    # Try to fetch from Amplitude
    if AMPLITUDE_FETCHER_AVAILABLE:
        try:
            fetcher = get_fetcher()
            if fetcher:
                print("🔄 Fetching data from Amplitude Export API...")
                events = fetcher.fetch_events(days=7)  # Fetch last 7 days for recent data
                if events and len(events) > 0:
                    print(f"✓ Fetched {len(events)} events from Amplitude")
                    stats = fetcher.aggregate_stats(events)
                    stats['_source'] = 'amplitude'
                    stats['_event_count'] = len(events)
                    _data_cache = stats
                    _cache_timestamp = datetime.now()
                    print(f"✓ Aggregated stats: {stats['total']} detections, {stats['protected']}% protected")
                    print(f"📊 Stats breakdown: entities={len(stats.get('entities', {}))}, sources={len(stats.get('sources', {}))}, apps={len(stats.get('apps_data', {}))}")
                    return stats
                else:
                    print("⚠ No events found in Amplitude (using mock data)")
            else:
                print("⚠ Amplitude fetcher not available (check config for secret_key)")
        except Exception as e:
            print(f"❌ Error fetching from Amplitude: {e}")
            import traceback
            traceback.print_exc()
    
    # Fallback to mock data
    print("📊 Using mock data (Amplitude unavailable or no events)")
    stats = get_mock_stats()
    stats['_source'] = 'mock'
    stats['_event_count'] = 0
    _data_cache = stats
    _cache_timestamp = datetime.now()
    return stats


@app.route('/')
def index():
    """Main dashboard page"""
    config = load_config()
    return render_template('dashboard.html', config=config)


@app.route('/api/stats')
def api_stats():
    """API endpoint for dashboard statistics"""
    stats = fetch_amplitude_stats()
    # Add source info for frontend
    stats['data_source'] = stats.get('_source', 'unknown')
    stats['event_count'] = stats.get('_event_count', 0)
    return jsonify(stats)


@app.route('/api/config')
def api_config():
    """API endpoint for configuration"""
    config = load_config()
    return jsonify(config)


def run_server(port: int = None, debug: bool = False):
    """Run the Flask dashboard server"""
    port = port or DEFAULT_PORT
    
    print("=" * 70)
    print("  PII GUARD - Amplitude Dashboard")
    print("=" * 70)
    print(f"\n🌐 Starting server on http://localhost:{port}")
    print(f"🔗 Access dashboard: http://localhost:{port}")
    print("=" * 70)
    print()
    
    app.run(host='0.0.0.0', port=port, debug=debug)


if __name__ == '__main__':
    import sys
    
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except:
            pass
    
    try:
        run_server(port=port, debug=True)
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()
