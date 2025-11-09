"""
Main Obfuscation Engine
Combines regex, spaCy, and transformer detectors to obfuscate PII in text.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from src.detectors.regex_detector import RegexPatternDetector, Detection as RegexDetection
from src.detectors.spacy_detector import SpacyDetector, Detection as SpacyDetection
try:
    from src.detectors.transformer_detector import TransformerDetector, Detection as TransDetection
    TRANSFORMER_AVAILABLE = True
except Exception as e:
    print(f"Warning: Transformer detector not available: {e}")
    TRANSFORMER_AVAILABLE = False

# NEW: Consensus detector for multi-model ensemble
try:
    from src.detectors.consensus_detector import ConsensusDetector, ConsensusDetection
    CONSENSUS_AVAILABLE = True
except Exception as e:
    print(f"Warning: Consensus detector not available: {e}")
    CONSENSUS_AVAILABLE = False

from src.escrow_db import EscrowDatabase

@dataclass
class ObfuscationResult:
    """Result of obfuscation operation"""
    original_text: str
    obfuscated_text: str
    replacements: Dict[str, str]  # placeholder -> original
    num_redactions: int
    detection_time_ms: float
    obfuscation_time_ms: float

class PIIObfuscator:
    """
    Main PII obfuscation engine.
    
    DETECTION ORDER (for validation and redundancy):
    1. Transformer (most accurate, context-aware) - PRIMARY
    2. spaCy (validates transformer, catches missed entities)
    3. Regex (ensures structured patterns never slip through)
    
    This layered approach provides:
    - Best accuracy from transformer's context understanding
    - Validation and fallback from spaCy NER
    - Guaranteed detection of structured data via regex
    """
    
    def __init__(
        self,
        use_regex: bool = True,  # ENABLED - catches structured data
        use_spacy: bool = True,  # ENABLED - validation layer
        use_transformer: bool = True,  # ENABLED - primary detection
        transformer_model: str = "lakshyakh93/deberta_finetuned_pii",
        escrow_db_path: str = "data/escrow/pii_escrow.db",
        spacy_model: str = "en_core_web_lg",
        confidence_threshold: float = 0.5,
        # NEW: Consensus mode parameters
        use_consensus: bool = False,  # Enable consensus/voting system
        consensus_mode: str = 'any_two',  # 'any_two', 'majority', 'strict', 'unanimous_structured'
        consensus_transformer_models: Optional[List[str]] = None  # List of transformer models for ensemble
    ):
        """
        Initialize obfuscator with MULTI-LAYER detection or CONSENSUS mode.
        
        Args:
            use_regex: Enable regex detector (default: True)
            use_spacy: Enable spaCy detector (default: True)
            use_transformer: Enable transformer detector (default: True)
            transformer_model: Transformer model to use
            escrow_db_path: Path to escrow database
            spacy_model: spaCy model name
            confidence_threshold: Minimum confidence for detections
            use_consensus: Enable consensus/voting system (multi-model ensemble)
            consensus_mode: Consensus threshold ('any_two', 'majority', 'strict', 'unanimous_structured')
            consensus_transformer_models: List of transformer models for consensus ensemble
        """
        print("Initializing PII Obfuscator...")
        print("=" * 60)
        
        # Check if using consensus mode
        self.use_consensus = use_consensus
        
        if use_consensus and CONSENSUS_AVAILABLE:
            print("CONSENSUS MODE - Multi-Model Ensemble with Voting")
            print("=" * 60)
            print(f"Consensus threshold: {consensus_mode.upper()}")
            print("This mode runs multiple models and requires agreement")
            print("Higher accuracy, slower performance")
            print("-" * 60)
            
            # Initialize consensus detector
            self.consensus_detector = ConsensusDetector(
                consensus_mode=consensus_mode,
                use_parallel=True,
                confidence_threshold=confidence_threshold,
                transformer_models=consensus_transformer_models or [
                    "lakshyakh93/deberta_finetuned_pii",
                    "obi/deid_roberta_i2b2"  # Use 2 models for better consensus
                ],
                spacy_model=spacy_model
            )
            
            # Don't initialize individual detectors in consensus mode
            self.detectors = []
            
        else:
            print("MULTI-LAYER DETECTION MODE")
            print("=" * 60)
            print("Sequential detection with validation")
            print("-" * 60)
        
            # Initialize detectors IN ORDER
            self.detectors = []
            self.confidence_threshold = confidence_threshold
            
            # Layer 1: TRANSFORMER (most accurate, context-aware)
            if use_transformer:
                if TRANSFORMER_AVAILABLE:
                    print(f"[OK] Loading transformer detector: {transformer_model}")
                    try:
                        self.transformer_detector = TransformerDetector(
                            model_name=transformer_model,
                            use_gpu=True
                        )
                        self.detectors.append(('transformer', self.transformer_detector))
                        print("[OK] Transformer detector loaded successfully!")
                    except Exception as e:
                        print(f"[WARN] Failed to load {transformer_model}: {e}")
                        print("  Trying alternative models...")
                        
                        # Fallback models
                        fallback_models = [
                            "obi/deid_roberta_i2b2",
                            "StanfordAIMI/stanford-deidentifier-base"
                        ]
                        
                        for fallback_model in fallback_models:
                            try:
                                print(f"  Attempting: {fallback_model}")
                                self.transformer_detector = TransformerDetector(
                                    model_name=fallback_model,
                                    use_gpu=True
                                )
                                self.detectors.append(('transformer', self.transformer_detector))
                                print(f"[OK] Fallback model loaded: {fallback_model}")
                                break
                            except Exception as fe:
                                print(f"  [ERROR] Failed: {fe}")
                                continue
                else:
                    print("[WARN] Transformer detector not available - check installation")
                    print("  Run: pip install transformers torch")
            
            # Layer 2: SPACY (validation and fallback)
            if use_spacy:
                print(f"[OK] Loading spaCy detector: {spacy_model}")
                self.spacy_detector = SpacyDetector(model_name=spacy_model)
                self.detectors.append(('spacy', self.spacy_detector))
                print("[OK] spaCy detector loaded!")
            
            # Layer 3: REGEX (structured data backup)
            if use_regex:
                print("[OK] Loading regex detector")
                self.regex_detector = RegexPatternDetector()
                self.detectors.append(('regex', self.regex_detector))
                print("[OK] Regex detector loaded!")
            
            # Ensure at least one detector is loaded
            if len(self.detectors) == 0:
                raise RuntimeError("No detectors available! Cannot initialize obfuscator.")
        
        # Initialize escrow database (common for both modes)
        print(f"[OK] Loading escrow database: {escrow_db_path}")
        self.escrow_db = EscrowDatabase(escrow_db_path)
        
        print("=" * 60)
        print(f"[OK] Obfuscator initialized with {len(self.detectors)} detector(s)")
        print("Detection order:")
        for i, (detector_name, _) in enumerate(self.detectors, 1):
            print(f"  {i}. {detector_name}")
        print("=" * 60 + "\n")
    
    def obfuscate(
        self,
        text: str,
        source: str = "cli",
        merge_overlaps: bool = True
    ) -> ObfuscationResult:
        """
        Obfuscate PII in text using multi-layer detection OR consensus mode.
        
        MULTI-LAYER MODE (Sequential validation):
        1. Transformer (most accurate, context-aware) - PRIMARY
        2. spaCy (validates transformer, catches missed entities)
        3. Regex (ensures structured patterns never slip through)
        
        CONSENSUS MODE (Multi-model voting):
        - Runs multiple models in parallel
        - Requires agreement between models
        - Higher accuracy, eliminates false positives
        
        Args:
            text: Input text to obfuscate
            source: Source identifier (for escrow)
            merge_overlaps: Whether to merge overlapping detections
            
        Returns:
            ObfuscationResult with obfuscated text and metadata
        """
        import time
        
        start_time = time.time()
        
        # CONSENSUS MODE - use voting system
        if self.use_consensus and hasattr(self, 'consensus_detector'):
            consensus_detections = self.consensus_detector.detect(text)
            
            # Convert consensus detections to standard format
            all_detections = []
            for cdet in consensus_detections:
                # Create a detection object
                from dataclasses import dataclass
                @dataclass
                class Detection:
                    text: str
                    start: int
                    end: int
                    entity_type: str
                    confidence: float = 1.0
                
                all_detections.append(Detection(
                    text=cdet.text,
                    start=cdet.start,
                    end=cdet.end,
                    entity_type=cdet.entity_type,
                    confidence=cdet.confidence
                ))
            
            detection_time = (time.time() - start_time) * 1000
        
        # STANDARD MODE - sequential with validation
        else:
            # Run detectors in priority order: transformer → spacy → regex
            # This ensures: 1) Best accuracy from transformer
            #               2) Validation from spaCy
            #               3) Structured pattern backup from regex
            all_detections = []
            
            # Priority 1: Transformer (most accurate, context-aware)
            for detector_name, detector in self.detectors:
                if detector_name == 'transformer':
                    detections = detector.detect(text)
                    all_detections.extend(detections)
                    break
            
            # Priority 2: spaCy (validates and catches what transformer missed)
            for detector_name, detector in self.detectors:
                if detector_name == 'spacy':
                    detections = detector.detect(text)
                    all_detections.extend(detections)
                    break
            
            # Priority 3: Regex (ensures structured data never slips through)
            for detector_name, detector in self.detectors:
                if detector_name == 'regex':
                    detections = detector.detect(text)
                    all_detections.extend(detections)
                    break
            
            detection_time = (time.time() - start_time) * 1000  # ms
            
            # Merge and deduplicate detections
            if merge_overlaps:
                all_detections = self._merge_detections(all_detections)
        
        # Sort by position
        all_detections.sort(key=lambda d: d.start)
        
        # Obfuscate text
        obfuscate_start = time.time()
        obfuscated_text, replacements = self._replace_with_placeholders(
            text,
            all_detections,
            source
        )
        obfuscation_time = (time.time() - obfuscate_start) * 1000  # ms
        
        return ObfuscationResult(
            original_text=text,
            obfuscated_text=obfuscated_text,
            replacements=replacements,
            num_redactions=len(replacements),
            detection_time_ms=detection_time,
            obfuscation_time_ms=obfuscation_time
        )
    
    def deobfuscate(self, obfuscated_text: str) -> str:
        """
        Restore original text from obfuscated version.
        
        Args:
            obfuscated_text: Text with placeholders
            
        Returns:
            Original text with PII restored
        """
        import re
        
        # Find all placeholders in text
        placeholder_pattern = r'\{([A-Z_]+)_(\d+)\}'
        matches = re.finditer(placeholder_pattern, obfuscated_text)
        
        # Build replacement map
        replacements = {}
        for match in matches:
            placeholder = match.group(0)  # {PERSON_1}
            placeholder_id = f"{match.group(1)}_{match.group(2)}"  # PERSON_1
            
            original = self.escrow_db.retrieve(placeholder_id)
            if original:
                replacements[placeholder] = original
        
        # Replace placeholders with originals
        result = obfuscated_text
        for placeholder, original in replacements.items():
            result = result.replace(placeholder, original)
        
        return result
    
    def _merge_detections(self, detections: List) -> List:
        """
        Merge overlapping detections.
        Keeps the longer detection when overlaps occur.
        """
        if not detections:
            return []
        
        # Sort by start position
        sorted_dets = sorted(detections, key=lambda d: d.start)
        
        merged = []
        current = sorted_dets[0]
        
        for detection in sorted_dets[1:]:
            # Check if overlaps
            if detection.start < current.end:
                # Keep the longer one, or the more confident one
                if (detection.end - detection.start) > (current.end - current.start):
                    current = detection
                elif (detection.end - detection.start) == (current.end - current.start):
                    # Same length - keep higher confidence
                    if detection.confidence > current.confidence:
                        current = detection
            else:
                merged.append(current)
                current = detection
        
        merged.append(current)
        return merged
    
    def _replace_with_placeholders(
        self,
        text: str,
        detections: List,
        source: str
    ) -> Tuple[str, Dict[str, str]]:
        """
        Replace detected PII with placeholders.
        
        Args:
            text: Original text
            detections: List of detections
            source: Source identifier
            
        Returns:
            (obfuscated_text, replacements_dict)
        """
        if not detections:
            return text, {}
        
        replacements = {}
        result_parts = []
        last_end = 0
        
        for detection in detections:
            # Add text before this detection
            result_parts.append(text[last_end:detection.start])
            
            # Get or create placeholder
            placeholder_id = self.escrow_db.store(
                original_value=detection.text,
                entity_type=detection.entity_type,
                source=source,
                context=text[max(0, detection.start-50):min(len(text), detection.end+50)]
            )
            
            # Add placeholder with braces
            placeholder = f"{{{placeholder_id}}}"
            result_parts.append(placeholder)
            replacements[placeholder] = detection.text
            
            last_end = detection.end
        
        # Add remaining text
        result_parts.append(text[last_end:])
        
        obfuscated = ''.join(result_parts)
        return obfuscated, replacements
    
    def get_stats(self) -> Dict:
        """Get statistics about obfuscations"""
        return self.escrow_db.get_stats()
    
    def close(self):
        """Clean up resources"""
        self.escrow_db.close()


if __name__ == "__main__":
    # Test the obfuscator
    print("\nTesting PII Obfuscator")
    print("=" * 60)
    
    # Create obfuscator with ALL detectors enabled
    obfuscator = PIIObfuscator(
        use_regex=True,  # Enabled for structured data
        use_spacy=True,  # Enabled for validation
        use_transformer=True,  # Enabled as primary
        transformer_model="lakshyakh93/deberta_finetuned_pii",
        confidence_threshold=0.5
    )
    
    # Test texts
    test_cases = [
        """
        John Smith works at Google in Mountain View.
        Contact him at john.smith@gmail.com or (555) 123-4567.
        His SSN is 123-45-6789.
        """,
        """
        Meeting with Alice Johnson (alice@microsoft.com) and Bob Chen
        scheduled for next Tuesday at 10 AM PST.
        """,
        """
        Customer data: Sarah Williams, DOB 01/15/1985,
        Credit card: 4532-0151-1283-0366
        Address: 123 Main St, Seattle, WA 98101
        """
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n{'=' * 60}")
        print(f"Test Case {i}:")
        print(f"{'=' * 60}")
        print(f"Original:\n{text.strip()}\n")
        
        # Obfuscate
        result = obfuscator.obfuscate(text, source=f"test_case_{i}")
        
        print(f"Obfuscated:\n{result.obfuscated_text.strip()}\n")
        print(f"Detections: {result.num_redactions}")
        print(f"Detection time: {result.detection_time_ms:.2f}ms")
        print(f"Obfuscation time: {result.obfuscation_time_ms:.2f}ms")
        print(f"Total time: {result.detection_time_ms + result.obfuscation_time_ms:.2f}ms")
        
        # Test deobfuscation
        print(f"\nDeobfuscated:\n{obfuscator.deobfuscate(result.obfuscated_text).strip()}")
        
        # Show replacements
        print(f"\nReplacements:")
        for placeholder, original in result.replacements.items():
            print(f"  {placeholder:20} -> {original}")
    
    # Show overall stats
    print(f"\n{'=' * 60}")
    print("Overall Statistics:")
    print(f"{'=' * 60}")
    stats = obfuscator.get_stats()
    print(f"Total entries in escrow: {stats['total_entries']}")
    print(f"By type:")
    for type_, count in stats['by_type'].items():
        print(f"  {type_:15}: {count}")
    
    obfuscator.close()
    print("\n✓ Obfuscator test complete!")