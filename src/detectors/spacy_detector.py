"""
spaCy NER Detector
Fast CPU-based Named Entity Recognition for PERSON, LOCATION, ORGANIZATION
Uses spaCy's pre-trained models (~30-50ms latency)
"""

import spacy
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class Detection:
    """Represents a detected PII entity"""
    text: str
    start: int
    end: int
    entity_type: str
    confidence: float = 1.0

class SpacyDetector:
    """
    Fast NER-based detector using spaCy.
    Detects:
    - PERSON: Names of people
    - GPE: Countries, cities, states (Geo-Political Entity)
    - LOC: Non-GPE locations, mountain ranges, bodies of water
    - ORG: Companies, agencies, institutions
    - DATE: Absolute or relative dates
    """
    
    # Mapping from spaCy labels to our PII types
    ENTITY_MAPPING = {
        'PERSON': 'PERSON',
        'GPE': 'LOCATION',
        'LOC': 'LOCATION',
        'ORG': 'ORGANIZATION',
        'DATE': 'DATE',
        'TIME': 'TIME',
        'NORP': 'GROUP',  # Nationalities, religious/political groups
    }
    
    def __init__(self, model_name: str = "en_core_web_lg"):
        """
        Initialize spaCy detector.
        
        Args:
            model_name: spaCy model to use
                       - 'en_core_web_sm': Fastest, less accurate
                       - 'en_core_web_lg': Slower, more accurate (recommended)
        """
        print(f"Loading spaCy model: {model_name}...")
        try:
            self.nlp = spacy.load(model_name)
            print("✓ spaCy model loaded successfully")
        except OSError:
            print(f"✗ Model '{model_name}' not found. Downloading...")
            import subprocess
            subprocess.run(['python', '-m', 'spacy', 'download', model_name])
            self.nlp = spacy.load(model_name)
            print("✓ spaCy model downloaded and loaded")
        
        # Disable unnecessary components for speed
        self.nlp.disable_pipes(['tok2vec', 'tagger', 'parser', 'attribute_ruler', 'lemmatizer'])
        # Only keep NER
        
    def detect(self, text: str) -> List[Detection]:
        """
        Detect PII entities using spaCy NER.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of Detection objects
        """
        # Process text with spaCy
        doc = self.nlp(text)
        
        # Common words to ignore (reduce false positives)
        IGNORE_WORDS = {
            'check', 'view', 'obfuscate', 'create', 'file', 'output',
            'start', 'end', 'begin', 'open', 'close', 'save', 'load',
            'test', 'demo', 'example', 'sample', 'run', 'execute'
        }
        
        detections = []
        for ent in doc.ents:
            # Map spaCy label to our PII type
            pii_type = self.ENTITY_MAPPING.get(ent.label_)
            
            if pii_type:
                # Filter out false positives
                entity_text = ent.text.strip()
                
                # Skip very short entities (likely false positives)
                if len(entity_text) < 2:
                    continue
                
                # Skip common command words
                if entity_text.lower() in IGNORE_WORDS:
                    continue
                
                # For PERSON entities, require at least 2 words or 4 chars
                if pii_type == 'PERSON':
                    if ' ' not in entity_text and len(entity_text) < 4:
                        continue
                
                detections.append(Detection(
                    text=entity_text,
                    start=ent.start_char,
                    end=ent.end_char,
                    entity_type=pii_type,
                    confidence=0.8  # spaCy doesn't provide confidence, use fixed value
                ))
        
        return detections
    
    def batch_detect(self, texts: List[str]) -> List[List[Detection]]:
        """
        Process multiple texts efficiently.
        
        Args:
            texts: List of texts to process
            
        Returns:
            List of detection lists (one per input text)
        """
        results = []
        
        # Use spaCy's pipe for efficient batch processing
        for doc in self.nlp.pipe(texts):
            detections = []
            for ent in doc.ents:
                pii_type = self.ENTITY_MAPPING.get(ent.label_)
                if pii_type:
                    detections.append(Detection(
                        text=ent.text,
                        start=ent.start_char,
                        end=ent.end_char,
                        entity_type=pii_type,
                        confidence=0.8
                    ))
            results.append(detections)
        
        return results


if __name__ == "__main__":
    # Test the detector
    import time
    
    detector = SpacyDetector()
    
    test_texts = [
        "John Smith works at Google in Mountain View, California.",
        "Contact Alice Johnson at Microsoft headquarters in Seattle.",
        "Dr. Bob Williams from Stanford University will present on January 15th.",
        "The meeting with Sarah Chen and David Lee is scheduled for next Tuesday.",
    ]
    
    print("\nTesting spaCy NER Detector")
    print("=" * 60)
    
    for i, text in enumerate(test_texts, 1):
        print(f"\nTest {i}: {text}")
        print("-" * 60)
        
        start_time = time.time()
        detections = detector.detect(text)
        elapsed = (time.time() - start_time) * 1000  # Convert to ms
        
        print(f"Found {len(detections)} entities (took {elapsed:.2f}ms):")
        for det in detections:
            print(f"  {det.entity_type:15} | {det.text:30} | pos: {det.start}-{det.end}")
    
    # Test batch processing
    print("\n" + "=" * 60)
    print("Testing batch processing:")
    start_time = time.time()
    batch_results = detector.batch_detect(test_texts)
    elapsed = (time.time() - start_time) * 1000
    
    total_detections = sum(len(r) for r in batch_results)
    print(f"Processed {len(test_texts)} texts in {elapsed:.2f}ms")
    print(f"Found {total_detections} total entities")
    print(f"Average: {elapsed/len(test_texts):.2f}ms per text")
    
    print("\n✓ spaCy detector test complete!")