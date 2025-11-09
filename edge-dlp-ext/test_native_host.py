#!/usr/bin/env python3
"""
Test script for native host.
This tests the native host by importing and calling its functions directly.
"""
import sys
import os

# Add current directory to path so we can import native_host
sys.path.insert(0, os.path.dirname(__file__))

# Import the detection function from native_host
from native_host import detect, handle_message

# Test cases
test_cases = [
    {"tabId": 1, "text": "my api_key is sk_live_abc123def456ghi789"},
    {"tabId": 1, "text": "Contact me at test@example.com"},
    {"tabId": 1, "text": "My SSN is 123-45-6789"},
    {"tabId": 1, "text": "No sensitive data here"},
]

print("Testing native host detection...")
print("=" * 50)

for i, test_msg in enumerate(test_cases, 1):
    print(f"\nTest {i}: {test_msg['text']}")
    print("-" * 50)
    
    try:
        # Test the handle_message function
        response = handle_message(test_msg)
        print(f"Response: {response}")
        
        if response.get('action') == 'replace':
            print(f"  ✓ PII detected and redacted")
            print(f"  Replacement: {response.get('replacement', 'N/A')[:100]}")
        elif response.get('action') == 'warn':
            print(f"  ⚠ PII detected, warning mode")
            print(f"  Findings: {len(response.get('findings', []))}")
        elif response.get('action') == 'allow':
            print(f"  ✓ No PII detected, allowed")
        else:
            print(f"  ? Unknown action: {response.get('action')}")
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 50)
print("Test complete!")
