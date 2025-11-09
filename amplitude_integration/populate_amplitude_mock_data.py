"""
Populate Amplitude with Mock Data
Generates and sends comprehensive mock PII detection events to Amplitude
"""

import sys
import time
import random
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from amplitude_integration.amplitude_tracker import get_tracker

def generate_mock_data(tracker, days=30, events_per_day=50):
    """
    Generate comprehensive mock data for Amplitude
    
    Args:
        tracker: AmplitudeTracker instance
        days: Number of days of historical data to generate
        events_per_day: Average number of events per day
    """
    print("=" * 70)
    print("  PII Guard - Amplitude Mock Data Generator")
    print("=" * 70)
    print(f"\nGenerating {days} days of mock data...")
    print(f"Average {events_per_day} events per day")
    print(f"Total: ~{days * events_per_day} events\n")
    
    # Entity types and their frequencies
    entity_types = {
        'EMAIL': 0.40,
        'PERSON': 0.25,
        'PHONE': 0.15,
        'SSN': 0.10,
        'CREDIT_CARD': 0.05,
        'API_KEY': 0.03,
        'PASSWORD': 0.02
    }
    
    # Sources and their frequencies
    sources = {
        'clipboard': 0.50,
        'typing': 0.35,
        'image': 0.15
    }
    
    # Applications and their risk levels
    apps = {
        'ChatGPT': {'risk': 'HIGH', 'weight': 0.30},
        'Gmail': {'risk': 'MEDIUM', 'weight': 0.25},
        'Slack': {'risk': 'LOW', 'weight': 0.20},
        'Teams': {'risk': 'LOW', 'weight': 0.10},
        'chrome.exe': {'risk': 'MEDIUM', 'weight': 0.05},
        'outlook.exe': {'risk': 'LOW', 'weight': 0.05},
        'discord.exe': {'risk': 'MEDIUM', 'weight': 0.03},
        'pastebin.com': {'risk': 'HIGH', 'weight': 0.02}
    }
    
    # Users and departments
    users = [
        {'name': 'john.doe', 'dept': 'Engineering', 'risk': 'HIGH'},
        {'name': 'alice.wang', 'dept': 'Sales', 'risk': 'MEDIUM'},
        {'name': 'bob.smith', 'dept': 'Engineering', 'risk': 'HIGH'},
        {'name': 'charlie.brown', 'dept': 'Finance', 'risk': 'MEDIUM'},
        {'name': 'diana.prince', 'dept': 'HR', 'risk': 'LOW'},
        {'name': 'eve.jones', 'dept': 'Sales', 'risk': 'MEDIUM'},
        {'name': 'frank.miller', 'dept': 'Engineering', 'risk': 'LOW'},
        {'name': 'grace.lee', 'dept': 'Finance', 'risk': 'LOW'},
        {'name': 'henry.wilson', 'dept': 'Sales', 'risk': 'HIGH'},
        {'name': 'ivy.taylor', 'dept': 'HR', 'risk': 'LOW'}
    ]
    
    # Protection methods
    protection_methods = {
        'clipboard': 'placeholder',
        'typing': 'placeholder',
        'image': 'blur'
    }
    
    total_events = 0
    start_time = datetime.now() - timedelta(days=days)
    
    print("Generating events...")
    
    for day in range(days):
        current_date = start_time + timedelta(days=day)
        
        # Vary events per day (more on weekdays)
        is_weekday = current_date.weekday() < 5
        day_events = int(events_per_day * (1.5 if is_weekday else 0.5))
        
        for event_num in range(day_events):
            # Random time during the day
            hour = random.randint(8, 18) if is_weekday else random.randint(10, 16)
            minute = random.randint(0, 59)
            event_time = current_date.replace(hour=hour, minute=minute, second=random.randint(0, 59))
            
            # Select random user
            user = random.choice(users)
            
            # Select entity type based on frequency
            entity_type = random.choices(
                list(entity_types.keys()),
                weights=list(entity_types.values())
            )[0]
            
            # Select source based on frequency
            source = random.choices(
                list(sources.keys()),
                weights=list(sources.values())
            )[0]
            
            # Select app based on weight
            app_name = random.choices(
                list(apps.keys()),
                weights=[a['weight'] for a in apps.values()]
            )[0]
            
            # Generate detection event
            confidence = round(random.uniform(0.85, 0.99), 2)
            num_entities = random.randint(1, 5) if entity_type == 'EMAIL' else 1
            detection_time = round(random.uniform(30, 200), 1)
            
            # Create event with timestamp
            # Note: We can't set exact timestamps in the tracker, but we'll send them in order
            # The tracker will use current time, but Amplitude will receive them sequentially
            
            # Track PII detection
            tracker.track_pii_detection(
                entity_type=entity_type,
                source=source,
                app_name=app_name,
                confidence_score=confidence,
                num_entities=num_entities,
                detection_time_ms=detection_time
            )
            
            # Track PII protection (90% of detections are protected)
            if random.random() < 0.90:
                protection_method = protection_methods.get(source, 'placeholder')
                tracker.track_pii_protection(
                    entity_type=entity_type,
                    source=source,
                    app_name=app_name,
                    protection_method=protection_method
                )
            
            # Track user undo (10% of protections are undone)
            if random.random() < 0.10:
                time_to_undo = round(random.uniform(5, 60), 1)
                tracker.track_user_undo(
                    source=source,
                    time_to_undo_seconds=time_to_undo
                )
            
            total_events += 1
            
            # Small delay to avoid rate limiting
            if event_num % 10 == 0:
                time.sleep(0.1)
        
        # Progress update
        if (day + 1) % 5 == 0:
            print(f"  Day {day + 1}/{days}: {total_events} events generated...")
    
    # Track system start events (one per day)
    print("\nGenerating system start events...")
    for day in range(days):
        current_date = start_time + timedelta(days=day)
        detectors = ['regex', 'spacy', 'transformer']
        sources_enabled = ['clipboard', 'typing']
        tracker.track_system_start(detectors, sources_enabled)
    
    # Track some whitelist events
    print("Generating whitelist events...")
    whitelist_apps = ['excel.exe', 'word.exe', 'notepad.exe', 'internal-app.company.com']
    for _ in range(20):
        app = random.choice(whitelist_apps)
        reason = random.choice(['Internal tool', 'Approved application', 'Policy exception'])
        tracker.track_whitelist_applied(app, reason)
    
    print(f"\n✓ Generated {total_events} detection events")
    print(f"✓ Generated {days} system start events")
    print(f"✓ Generated 20 whitelist events")
    print(f"\nTotal events sent: ~{total_events + days + 20}")
    print("\nFlushing events to Amplitude...")
    
    # Flush all events
    tracker.flush()
    tracker.stop()
    
    print("\n✓ All events sent to Amplitude!")
    print("=" * 70)
    print("\nYou can now view this data in Amplitude dashboard:")
    print("  https://analytics.amplitude.com")
    print("\nOr use Amplitude's Query API to fetch real data for the dashboard.")
    print("=" * 70)


def main():
    """Main entry point"""
    print("\nInitializing Amplitude tracker...")
    
    # Get tracker (will use config from amplitude_config.json)
    tracker = get_tracker()
    
    if not tracker:
        print("❌ Error: Could not initialize Amplitude tracker")
        print("   Check amplitude_config.json for API key")
        return
    
    print("✓ Tracker initialized\n")
    
    # Ask user for parameters
    try:
        days = int(input("Days of historical data to generate (default 30): ") or "30")
        events_per_day = int(input("Events per day (default 50): ") or "50")
    except (ValueError, KeyboardInterrupt):
        print("\nUsing defaults: 30 days, 50 events/day")
        days = 30
        events_per_day = 50
    
    # Generate mock data
    try:
        generate_mock_data(tracker, days=days, events_per_day=events_per_day)
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        tracker.stop()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        tracker.stop()


if __name__ == '__main__':
    main()

