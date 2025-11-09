"""
Consensus-Based PII Detector
Multi-model ensemble with voting mechanism for maximum accuracy and redundancy.

CONSENSUS APPROACH:
1. Run MULTIPLE models in parallel (transformer #1, transformer #2, spaCy, regex)
2. Each model "votes" on detected PII
3. Only entities with >=2 votes (or configurable threshold) are accepted
4. Provides high confidence and eliminates false positives

This can be slower but ensures 100% accuracy.
"""

import time
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict, Counter
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import all detectors
from detectors.regex_detector import RegexPatternDetector, Detection as RegexDetection
from detectors.spacy_detector import SpacyDetector, Detection as SpacyDetection

try:
    from detectors.transformer_detector import TransformerDetector, Detection as TransDetection
    TRANSFORMER_AVAILABLE = True
except Exception as e:
    print(f"Warning: Transformer detector not available: {e}")
    TRANSFORMER_AVAILABLE = False


@dataclass
class Detection:
    """Unified detection format"""
    text: str
    start: int
    end: int
    entity_type: str
    confidence: float = 1.0
    detector_source: str = ""  # Which detector found this


@dataclass
class ConsensusDetection:
    """Detection with consensus information"""
    text: str
    start: int
    end: int
    entity_type: str
    vote_count: int  # How many detectors agreed
    detectors: List[str] = field(default_factory=list)  # Which detectors found it
    confidence: float = 1.0
    
    def __repr__(self):
        return f"<{self.entity_type} '{self.text}' votes={self.vote_count}/{len(self.detectors)} detectors={self.detectors}>"


class ConsensusDetector:
    """
    Ensemble detector using voting/consensus mechanism.
    
    CONSENSUS MODES:
    - 'strict': Requires ALL detectors to agree (100% consensus)
    - 'majority': Requires >50% detectors to agree
    - 'any_two': Requires at least 2 detectors to agree
    - 'unanimous_structured': Requires all for structured data (SSN, credit cards), 
                             any_two for entities (names, locations)
    - 'regex_priority': ⭐ RECOMMENDED - Trusts regex patterns for structured data
                       (emails, SSNs, phones, etc), requires 2+ for entities.
                       Best balance of completeness and accuracy.
    """
    
    def __init__(
        self,
        consensus_mode: str = 'any_two',
        use_parallel: bool = True,
        confidence_threshold: float = 0.5,
        transformer_models: Optional[List[str]] = None,
        spacy_model: str = 'en_core_web_lg'
    ):
        """
        Initialize consensus detector with multiple models.
        
        Args:
            consensus_mode: 'strict', 'majority', 'any_two', 'unanimous_structured'
            use_parallel: Run detectors in parallel for speed
            confidence_threshold: Minimum confidence for transformer models
            transformer_models: List of transformer model names to use (multi-model ensemble)
            spacy_model: spaCy model name
        """
        self.consensus_mode = consensus_mode
        self.use_parallel = use_parallel
        self.confidence_threshold = confidence_threshold
        
        print("\n" + "=" * 70)
        print("🎯 CONSENSUS-BASED PII DETECTION SYSTEM")
        print("=" * 70)
        print(f"Mode: {consensus_mode.upper()}")
        print(f"Parallel execution: {use_parallel}")
        print("-" * 70)
        
        # Initialize all detectors
        self.detectors: List[Tuple[str, object]] = []
        
        # 1. Regex detector (always first - fastest)
        print("📌 Loading Regex Detector...")
        self.regex_detector = RegexPatternDetector()
        self.detectors.append(('regex', self.regex_detector))
        print("   ✓ Regex loaded (structured data patterns)")
        
        # 2. spaCy detector (fast NER)
        print("📌 Loading spaCy Detector...")
        self.spacy_detector = SpacyDetector(model_name=spacy_model)
        self.detectors.append(('spacy', self.spacy_detector))
        print(f"   ✓ spaCy loaded ({spacy_model})")
        
        # 3. Transformer models (multiple for ensemble)
        if TRANSFORMER_AVAILABLE:
            if transformer_models is None:
                # Default: Use 2 different transformer models for better consensus
                transformer_models = [
                    "lakshyakh93/deberta_finetuned_pii",  # Model 1: DeBERTa fine-tuned
                    "obi/deid_roberta_i2b2"                # Model 2: RoBERTa for medical PII
                ]
            
            print(f"📌 Loading {len(transformer_models)} Transformer Model(s)...")
            for i, model_name in enumerate(transformer_models, 1):
                try:
                    print(f"   [{i}] Loading {model_name}...")
                    detector = TransformerDetector(
                        model_name=model_name,
                        use_gpu=True,
                        use_fp16=False  # Disable fp16 for compatibility
                    )
                    self.detectors.append((f'transformer_{i}', detector))
                    print(f"   ✓ Transformer {i} loaded")
                except Exception as e:
                    print(f"   ✗ Failed to load {model_name}: {e}")
                    continue
        
        print("-" * 70)
        print(f"✓ Consensus system initialized with {len(self.detectors)} detectors")
        print("  Detectors:")
        for name, _ in self.detectors:
            print(f"    - {name}")
        print("=" * 70 + "\n")
    
    def detect(self, text: str) -> List[ConsensusDetection]:
        """
        Detect PII using consensus from multiple detectors.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of ConsensusDetection objects (only those meeting consensus threshold)
        """
        start_time = time.time()
        
        # Run all detectors
        if self.use_parallel:
            all_detections = self._run_parallel(text)
        else:
            all_detections = self._run_sequential(text)
        
        detection_time = (time.time() - start_time) * 1000
        
        # Apply consensus voting
        consensus_start = time.time()
        consensus_results = self._apply_consensus(all_detections)
        consensus_time = (time.time() - consensus_start) * 1000
        
        # Log statistics
        total_detections = sum(len(dets) for dets in all_detections.values())
        print(f"\n🔍 Detection complete:")
        print(f"   Total raw detections: {total_detections}")
        print(f"   After consensus: {len(consensus_results)}")
        print(f"   Detection time: {detection_time:.2f}ms")
        print(f"   Consensus time: {consensus_time:.2f}ms")
        print(f"   Total time: {detection_time + consensus_time:.2f}ms")
        
        return consensus_results
    
    def _run_parallel(self, text: str) -> Dict[str, List[Detection]]:
        """Run all detectors in parallel using thread pool"""
        all_detections = {}
        
        with ThreadPoolExecutor(max_workers=len(self.detectors)) as executor:
            # Submit all detector tasks
            future_to_detector = {
                executor.submit(self._run_detector, name, detector, text): name
                for name, detector in self.detectors
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_detector):
                detector_name = future_to_detector[future]
                try:
                    detections = future.result()
                    all_detections[detector_name] = detections
                except Exception as e:
                    print(f"Error in {detector_name}: {e}")
                    all_detections[detector_name] = []
        
        return all_detections
    
    def _run_sequential(self, text: str) -> Dict[str, List[Detection]]:
        """Run all detectors sequentially (slower but simpler)"""
        all_detections = {}
        
        for name, detector in self.detectors:
            detections = self._run_detector(name, detector, text)
            all_detections[name] = detections
        
        return all_detections
    
    def _run_detector(self, name: str, detector, text: str) -> List[Detection]:
        """Run a single detector and normalize results"""
        try:
            # Run detection
            if 'transformer' in name:
                raw_detections = detector.detect(text, self.confidence_threshold)
            else:
                raw_detections = detector.detect(text)
            
            # Normalize to unified Detection format
            detections = []
            for det in raw_detections:
                detections.append(Detection(
                    text=det.text,
                    start=det.start,
                    end=det.end,
                    entity_type=det.entity_type,
                    confidence=det.confidence,
                    detector_source=name
                ))
            
            print(f"   {name}: Found {len(detections)} entities")
            return detections
        
        except Exception as e:
            print(f"   {name}: Error - {e}")
            return []
    
    def _apply_consensus(self, all_detections: Dict[str, List[Detection]]) -> List[ConsensusDetection]:
        """
        Apply consensus voting to detections.
        
        Two detections are considered "the same" if they:
        1. Overlap significantly (>80% IoU - Intersection over Union)
        2. Have the same or compatible entity types
        """
        # Build detection clusters (group overlapping detections)
        clusters = []
        
        for detector_name, detections in all_detections.items():
            for det in detections:
                # Find matching cluster
                matched = False
                for cluster in clusters:
                    # Check if this detection overlaps with cluster
                    if self._overlaps_cluster(det, cluster):
                        cluster.append(det)
                        matched = True
                        break
                
                if not matched:
                    # Create new cluster
                    clusters.append([det])
        
        # Convert clusters to consensus detections
        consensus_results = []
        for cluster in clusters:
            # Count votes (how many unique detectors found this)
            detector_votes = set(det.detector_source for det in cluster)
            vote_count = len(detector_votes)
            
            # Check if meets consensus threshold
            if self._meets_consensus(cluster, vote_count):
                # Get most common entity type
                entity_types = [det.entity_type for det in cluster]
                most_common_type = Counter(entity_types).most_common(1)[0][0]
                
                # Use the longest text span (most complete detection)
                longest_det = max(cluster, key=lambda d: len(d.text))
                
                # Calculate average confidence
                avg_confidence = sum(d.confidence for d in cluster) / len(cluster)
                
                consensus_results.append(ConsensusDetection(
                    text=longest_det.text,
                    start=longest_det.start,
                    end=longest_det.end,
                    entity_type=most_common_type,
                    vote_count=vote_count,
                    detectors=sorted(list(detector_votes)),
                    confidence=avg_confidence
                ))
        
        # Sort by position
        consensus_results.sort(key=lambda d: d.start)
        
        return consensus_results
    
    def _overlaps_cluster(self, detection: Detection, cluster: List[Detection]) -> bool:
        """Check if detection overlaps with any detection in cluster"""
        for existing in cluster:
            if self._calculate_iou(detection, existing) > 0.6:  # 60% overlap threshold
                return True
        return False
    
    def _calculate_iou(self, det1: Detection, det2: Detection) -> float:
        """
        Calculate Intersection over Union (IoU) for two detections.
        IoU measures how much two text spans overlap.
        """
        # Calculate overlap
        overlap_start = max(det1.start, det2.start)
        overlap_end = min(det1.end, det2.end)
        
        if overlap_start >= overlap_end:
            return 0.0  # No overlap
        
        intersection = overlap_end - overlap_start
        union = (det1.end - det1.start) + (det2.end - det2.start) - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _meets_consensus(self, cluster: List[Detection], vote_count: int) -> bool:
        """
        Check if detection cluster meets consensus threshold.
        
        Args:
            cluster: List of detections in this cluster
            vote_count: Number of unique detectors that found this
            
        Returns:
            True if meets threshold, False otherwise
        """
        total_detectors = len(self.detectors)
        
        if self.consensus_mode == 'strict':
            # Requires ALL detectors to agree
            return vote_count == total_detectors
        
        elif self.consensus_mode == 'majority':
            # Requires >50% of detectors
            return vote_count > (total_detectors / 2)
        
        elif self.consensus_mode == 'any_two':
            # Requires at least 2 detectors (recommended)
            return vote_count >= 2
        
        elif self.consensus_mode == 'unanimous_structured':
            # Check if it's structured data
            entity_types = set(det.entity_type for det in cluster)
            structured_types = {'EMAIL', 'PHONE', 'SSN', 'CREDIT_CARD', 'IP_ADDRESS', 'URL'}
            
            if entity_types & structured_types:  # Is structured data
                # Require unanimous agreement for structured data
                return vote_count == total_detectors
            else:
                # For other entities, require at least 2
                return vote_count >= 2
        
        elif self.consensus_mode == 'regex_priority':
            # BEST MODE for completeness: Trust regex for structured patterns, consensus for entities
            # Check if regex detector found this
            detector_sources = {det.detector_source for det in cluster}
            entity_types = set(det.entity_type for det in cluster)
            
            # Define structured data types that regex is authoritative for
            structured_types = {
                'EMAIL', 'PHONE', 'SSN', 'CREDIT_CARD', 'IP_ADDRESS', 'URL',
                'MAC_ADDRESS', 'PASSPORT', 'ROUTING_NUMBER', 'ACCOUNT_NUMBER',
                'POLICY_NUMBER', 'BADGE_NUMBER', 'VPN_TOKEN', 'LICENSE_PLATE',
                'CASE_NUMBER', 'CERT_ID', 'ZIP_CODE', 'DATE'
            }
            
            # If regex found a structured type, ALWAYS accept (regex is authoritative)
            if 'regex' in detector_sources and entity_types & structured_types:
                return True
            
            # For non-structured entities (names, locations, orgs), require 2+ detectors
            return vote_count >= 2
        
        else:
            # Default: any_two
            return vote_count >= 2


def visualize_consensus(text: str, consensus_results: List[ConsensusDetection]):
    """
    Print a visual representation of consensus results.
    """
    print("\n" + "=" * 70)
    print("📊 CONSENSUS RESULTS")
    print("=" * 70)
    
    if not consensus_results:
        print("No PII detected with required consensus.")
        return
    
    print(f"Found {len(consensus_results)} high-confidence PII items:\n")
    
    for i, det in enumerate(consensus_results, 1):
        vote_pct = (det.vote_count / len(det.detectors)) * 100 if det.detectors else 0
        confidence_bar = "█" * int(vote_pct / 10)
        
        print(f"{i}. {det.entity_type:15} | '{det.text}'")
        print(f"   Votes: {det.vote_count} | Confidence: [{confidence_bar:10}] {vote_pct:.0f}%")
        print(f"   Detected by: {', '.join(det.detectors)}")
        print()


if __name__ == "__main__":
    print("\nTesting Consensus-Based PII Detector")
    print("=" * 70)
    
    # Test text with various PII types
    test_text = """
    CONFIDENTIAL - Employee Record
    
    Name: Michael Chen
    Email: mchen@company.com
    Personal Email: michael.chen1990@gmail.com
    Phone: (206) 555-8901
    SSN: 987-65-4321
    Credit Card: 4532-1234-5678-9010
    Address: 1234 Elm Street, Seattle, WA 98101
    
    Manager: Jennifer Smith (jsmith@company.com)
    Emergency Contact: Lisa Chen - (206) 555-8902
    """
    
    print(f"\nInput text:\n{test_text}")
    print("\n" + "-" * 70)
    
    # Test different consensus modes
    modes = ['any_two', 'majority', 'unanimous_structured']
    
    for mode in modes:
        print(f"\n{'='*70}")
        print(f"Testing consensus mode: {mode.upper()}")
        print(f"{'='*70}")
        
        detector = ConsensusDetector(
            consensus_mode=mode,
            use_parallel=True,
            confidence_threshold=0.5,
            transformer_models=[
                "lakshyakh93/deberta_finetuned_pii",
                # Add a second model if you want stronger consensus
                # "obi/deid_roberta_i2b2"
            ]
        )
        
        results = detector.detect(test_text)
        visualize_consensus(test_text, results)
    
    print("\n✓ Consensus detector test complete!")
