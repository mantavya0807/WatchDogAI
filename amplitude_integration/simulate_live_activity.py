"""
Simulate Live Activity for Amplitude Dashboard Demo
Sends random PII detection events to Amplitude every 15 seconds
"""

import time
import random
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from amplitude_integration.amplitude_tracker import AmplitudeTracker
from amplitude_integration.integration_helper import get_amplitude_tracker


def generate_random_event():
    """Generate a random PII detection event"""
    # Random entity types
    entity_types = ['EMAIL', 'PHONE', 'SSN', 'PERSON', 'CREDIT_CARD', 'IP_ADDRESS', 'LOCATION']
    entity_type = random.choice(entity_types)
    
    # Random sources
    sources = ['clipboard', 'typing', 'image']
    source = random.choice(sources)
    
    # Random apps
    apps = ['chrome.exe', 'slack.exe', 'teams.exe', 'discord.exe', 'notepad.exe', 'word.exe', 'excel.exe']
    app_name = random.choice(apps)
    
    # Random number of entities (1-5)
    num_entities = random.randint(1, 5)
    
    # Random user ID
    user_ids = ['user1', 'user2', 'user3', 'user4', 'user5', 'admin', 'demo_user']
    user_id = random.choice(user_ids)
    
    return {
        'entity_type': entity_type,
        'source': source,
        'app_name': app_name,
        'num_entities': num_entities,
        'user_id': user_id
    }


def main():
    """Main loop to send events every 15 seconds"""
    print("=" * 70)
    print("  PII GUARD - Live Activity Simulator")
    print("=" * 70)
    print()
    print("📡 Connecting to Amplitude...")
    
    # Get Amplitude tracker
    tracker = get_amplitude_tracker()
    
    if not tracker:
        print("❌ Failed to initialize Amplitude tracker")
        print("   Make sure amplitude_config.json is properly configured")
        return
    
    print("✓ Amplitude tracker initialized")
    print()
    print("🔄 Starting live activity simulation...")
    print("   Sending random events every 15 seconds")
    print("   Press CTRL+C to stop")
    print()
    print("-" * 70)
    
    event_count = 0
    
    try:
        while True:
            # Generate random event
            event_data = generate_random_event()
            
            # Track PII detection
            tracker.track_pii_detection(
                entity_type=event_data['entity_type'],
                source=event_data['source'],
                app_name=event_data['app_name'],
                confidence_score=random.uniform(0.7, 1.0),
                num_entities=event_data['num_entities'],
                detection_time_ms=random.uniform(10, 100)
            )
            
            event_count += 1
            
            # Print event info
            print(f"[{event_count}] 📊 PII Detected:")
            print(f"     Entity: {event_data['entity_type']}")
            print(f"     Source: {event_data['source']}")
            print(f"     App: {event_data['app_name']}")
            print(f"     Entities: {event_data['num_entities']}")
            print(f"     User: {event_data['user_id']}")
            print()
            
            # Sometimes also send a protection event (30% chance)
            if random.random() < 0.3:
                protection_methods = ['obfuscation', 'redaction', 'encryption', 'blocking']
                protection_method = random.choice(protection_methods)
                tracker.track_pii_protection(
                    entity_type=event_data['entity_type'],
                    source=event_data['source'],
                    app_name=event_data['app_name'],
                    protection_method=protection_method
                )
                print(f"     ✓ Protected ({protection_method})")
                print()
            
            # Wait 15 seconds
            print("⏳ Waiting 15 seconds until next event...")
            print("-" * 70)
            time.sleep(15)
            
    except KeyboardInterrupt:
        print()
        print("-" * 70)
        print(f"✓ Simulation stopped")
        print(f"  Total events sent: {event_count}")
        print()
        print("💡 Note: Events are queued and sent in batches.")
        print("   It may take a few seconds for all events to appear in Amplitude.")
        print("=" * 70)


if __name__ == "__main__":
    main()

