"""
Integration helper for adding Amplitude tracking to monitors
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from amplitude_tracker import get_tracker
    AMPLITUDE_AVAILABLE = True
except Exception as e:
    AMPLITUDE_AVAILABLE = False


def get_amplitude_tracker():
    """Get Amplitude tracker instance if available"""
    if not AMPLITUDE_AVAILABLE:
        return None
    
    try:
        config_path = Path(__file__).parent / "config" / "amplitude_config.json"
        use_mock_data = True
        mock_interval = 5
        
        if config_path.exists():
            try:
                import json
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    use_mock_data = config.get('use_mock_data', True)
                    mock_interval = config.get('mock_data_interval_seconds', 5)
            except:
                pass
        
        return get_tracker(use_mock_data=use_mock_data, mock_interval=mock_interval)
    except Exception as e:
        return None


def track_pii_detection_from_result(tracker, result, source: str, app_name: str = "unknown", detection_time_ms: float = 0):
    """Track PII detection from obfuscation result"""
    if not tracker or not result or result.num_redactions == 0:
        return
    
    entity_types = {}
    for placeholder, original in result.replacements.items():
        entity_type = placeholder.split('_')[0].replace('{', '').replace('}', '')
        if entity_type not in entity_types:
            entity_types[entity_type] = []
        entity_types[entity_type].append(original)
    
    if entity_types:
        primary_type = max(entity_types.keys(), key=lambda k: len(entity_types[k]))
        confidence = 0.9
        
        dt_ms = detection_time_ms
        if not dt_ms and hasattr(result, 'detection_time_ms'):
            dt_ms = result.detection_time_ms
        if not dt_ms:
            dt_ms = 0.0
        
        tracker.track_pii_detection(
            entity_type=primary_type,
            source=source,
            app_name=app_name,
            confidence_score=confidence,
            num_entities=result.num_redactions,
            detection_time_ms=dt_ms
        )
        
        protection_method = "placeholder"
        if source == "clipboard_image":
            protection_method = "blur"
        
        tracker.track_pii_protection(
            entity_type=primary_type,
            source=source,
            app_name=app_name,
            protection_method=protection_method
        )
        
        tracker.flush()


def track_user_undo(tracker, source: str, time_to_undo_seconds: float = 0):
    """Track user undo event"""
    if not tracker:
        return
    
    tracker.track_user_undo(source=source, time_to_undo_seconds=time_to_undo_seconds)
    tracker.flush()
