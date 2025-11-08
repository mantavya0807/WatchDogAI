"""
Regex Pattern Detector
Fast pattern matching for structured PII like emails, SSNs, credit cards, etc.
"""

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class Detection:
    """Represents a detected PII entity"""
    text: str
    start: int
    end: int
    entity_type: str
    confidence: float = 1.0

class RegexPatternDetector:
    """
    Fast regex-based detector for structured PII.
    This is the fastest layer (~1-5ms) for patterns like:
    - Email addresses
    - Phone numbers
    - SSNs
    - Credit cards
    - IP addresses
    - URLs
    """
    
    def __init__(self):
        # Compile regex patterns for speed
        self.patterns = {
            'EMAIL': re.compile(
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ),
            'PHONE': re.compile(
                r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
            ),
            'SSN': re.compile(
                r'\b(?!000|666)([0-9]{3})-(?!00)([0-9]{2})-(?!0000)([0-9]{4})\b'
            ),
            'CREDIT_CARD': re.compile(
                r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12}|(?:[0-9]{4}[-\s]?){3}[0-9]{4})\b'
            ),
            'IP_ADDRESS': re.compile(
                r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
            ),
            'MAC_ADDRESS': re.compile(
                r'\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b'
            ),
            'URL': re.compile(
                r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b[-a-zA-Z0-9()@:%_\+.~#?&/=]*'
            ),
            'PASSPORT': re.compile(
                r'\b[A-Z]{1,2}[0-9]{6,9}\b|\b[0-9]{9}\b(?=\s*(?:Passport|passport))|(?:Passport|passport)\s*(?:Number|#|No\.?)?\s*:?\s*([A-Z0-9]{6,9})'
            ),
            'ROUTING_NUMBER': re.compile(
                r'\b0[0-9]{8}\b'  # US routing numbers start with 0, 9 digits total
            ),
            'ACCOUNT_NUMBER': re.compile(
                r'\b[0-9]{10,18}\b'  # Bank account numbers
            ),
            'POLICY_NUMBER': re.compile(
                r'\b[A-Z]{2,4}-[0-9]{6,12}-[0-9]{1,3}\b'  # Insurance policy format
            ),
            'BADGE_NUMBER': re.compile(
                r'\b[A-Z]-[0-9]{4,6}\b'  # Badge format like A-7651
            ),
            'VPN_TOKEN': re.compile(
                r'\bVPN-[0-9]{4}-[0-9]{4}-[0-9]{4}\b',
                re.IGNORECASE
            ),
            'LICENSE_PLATE': re.compile(
                r'\b[A-Z]{2}-[A-Z]+-[0-9]{3}-[0-9]{4}\b'  # Driver's license format
            ),
            'CASE_NUMBER': re.compile(
                r'\b(?:DOD|FBI|CIA|NSA|DHS)-[0-9]{4}-[0-9]{6,8}\b',
                re.IGNORECASE
            ),
            'CERT_ID': re.compile(
                r'\b(?:AWS|CISSP|PMP|PMI|MIT)-[A-Z]{0,3}-?[0-9]{4,8}\b',
                re.IGNORECASE
            ),
            'API_KEY': re.compile(
                r'\b[A-Za-z0-9_-]{32,}\b'  # Generic API key pattern
            ),
            'ID_NUMBER': re.compile(
                r'\b(?:EMP|ID|EMPID|EMPLOYEE)-?[0-9]{4,10}\b',
                re.IGNORECASE
            ),
            'DATE': re.compile(
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b'
            ),
            'ZIP_CODE': re.compile(
                r'\b\d{5}(?:-\d{4})?\b'
            ),
        }
    
    def detect(self, text: str) -> List[Detection]:
        """
        Detect all PII patterns in text.
        
        Args:
            text: Input text to scan
            
        Returns:
            List of Detection objects
        """
        detections = []
        
        for entity_type, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                # Additional validation for some patterns
                if entity_type == 'CREDIT_CARD':
                    # Extract just digits for Luhn check
                    card_digits = re.sub(r'[-\s]', '', match.group())
                    if len(card_digits) >= 13 and not self._validate_luhn(card_digits):
                        continue
                
                if entity_type == 'API_KEY':
                    # Check if it looks like gibberish (high entropy)
                    if not self._is_high_entropy(match.group()):
                        continue
                
                if entity_type == 'ROUTING_NUMBER':
                    # Validate routing number checksum
                    if not self._validate_routing(match.group()):
                        continue
                
                if entity_type == 'ACCOUNT_NUMBER':
                    # Skip if it looks like a date or other common number pattern
                    if self._looks_like_date(match.group()):
                        continue
                
                detections.append(Detection(
                    text=match.group(),
                    start=match.start(),
                    end=match.end(),
                    entity_type=entity_type,
                    confidence=1.0
                ))
        
        # Sort by start position
        detections.sort(key=lambda x: x.start)
        
        # Remove overlaps (keep longer matches)
        return self._remove_overlaps(detections)
    
    def _validate_luhn(self, card_number: str) -> bool:
        """Validate credit card number using Luhn algorithm"""
        def digits_of(n):
            return [int(d) for d in str(n)]
        
        digits = digits_of(card_number)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))
        return checksum % 10 == 0
    
    def _is_high_entropy(self, text: str, threshold: float = 3.5) -> bool:
        """Check if string has high entropy (looks random/gibberish)"""
        if len(text) < 16:  # Too short to be a real API key
            return False
        
        import math
        from collections import Counter
        
        # Calculate Shannon entropy
        counter = Counter(text)
        length = len(text)
        entropy = -sum((count / length) * math.log2(count / length) 
                      for count in counter.values())
        
        return entropy > threshold
    
    def _validate_routing(self, routing: str) -> bool:
        """Validate US routing number using checksum algorithm"""
        if len(routing) != 9:
            return False
        
        # Routing number checksum: 3*(d1+d4+d7) + 7*(d2+d5+d8) + (d3+d6+d9) mod 10 = 0
        weights = [3, 7, 1, 3, 7, 1, 3, 7, 1]
        checksum = sum(int(d) * w for d, w in zip(routing, weights))
        return checksum % 10 == 0
    
    def _looks_like_date(self, text: str) -> bool:
        """Check if number looks like a date or timestamp"""
        # Skip very long sequences that might be dates/timestamps
        if len(text) >= 16:  # Likely a timestamp
            return True
        # Skip if it matches common date formats
        if len(text) == 8:  # YYYYMMDD or MMDDYYYY
            return True
        return False
    
    def _remove_overlaps(self, detections: List[Detection]) -> List[Detection]:
        """Remove overlapping detections, keeping longer ones"""
        if not detections:
            return []
        
        result = []
        current = detections[0]
        
        for detection in detections[1:]:
            # Check if overlaps
            if detection.start < current.end:
                # Keep the longer one
                if (detection.end - detection.start) > (current.end - current.start):
                    current = detection
            else:
                result.append(current)
                current = detection
        
        result.append(current)
        return result


if __name__ == "__main__":
    # Test the detector
    detector = RegexPatternDetector()
    
    test_text = """
    Contact John at john.doe@email.com or call (555) 123-4567.
    His SSN is 123-45-6789 and his credit card is 4532015112830366.
    IP address: 192.168.1.1
    Website: https://example.com
    Date of birth: 01/15/1990
    API Key: sk_test_4eC39HqLyjWDarjtT1zdp7dc
    """
    
    print("Testing Regex Pattern Detector")
    print("=" * 60)
    print(f"Input text:\n{test_text}\n")
    
    detections = detector.detect(test_text)
    
    print(f"Found {len(detections)} PII entities:")
    print("-" * 60)
    for det in detections:
        print(f"{det.entity_type:15} | {det.text:30} | pos: {det.start}-{det.end}")
    
    print("\n✓ Regex detector test complete!")