"""
Transformer PII Detector
GPU-accelerated accurate PII detection using transformer models.
Uses pre-trained models fine-tuned specifically for PII detection.
"""

import torch
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    pipeline
)
from typing import List, Dict, Optional
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

@dataclass
class Detection:
    """Represents a detected PII entity"""
    text: str
    start: int
    end: int
    entity_type: str
    confidence: float = 1.0

class TransformerDetector:
    """
    Accurate transformer-based PII detector.
    
    Supports multiple models:
    - lakshyakh93/deberta_finetuned_pii (recommended)
    - betterdataai/PII_DETECTION_MODEL (Qwen-based)
    - obi/deid_roberta_i2b2 (medical PII)
    """
    
    # Entity type mappings
    ENTITY_MAPPING = {
        'B-NAME_STUDENT': 'PERSON',
        'I-NAME_STUDENT': 'PERSON',
        'B-EMAIL': 'EMAIL',
        'I-EMAIL': 'EMAIL',
        'B-PHONE_NUM': 'PHONE',
        'I-PHONE_NUM': 'PHONE',
        'B-ID_NUM': 'ID_NUMBER',
        'I-ID_NUM': 'ID_NUMBER',
        'B-STREET_ADDRESS': 'ADDRESS',
        'I-STREET_ADDRESS': 'ADDRESS',
        'B-URL_PERSONAL': 'URL',
        'I-URL_PERSONAL': 'URL',
        'B-USERNAME': 'USERNAME',
        'I-USERNAME': 'USERNAME',
        # Add more mappings as needed
        'PERSON': 'PERSON',
        'EMAIL': 'EMAIL',
        'PHONE': 'PHONE',
        'LOCATION': 'LOCATION',
        'ORG': 'ORGANIZATION',
        'ORGANIZATION': 'ORGANIZATION',
    }
    
    def __init__(
        self,
        model_name: str = "lakshyakh93/deberta_finetuned_pii",
        use_gpu: bool = True,
        batch_size: int = 8,
        use_fp16: bool = False  # Disable fp16 by default to avoid dtype issues
    ):
        """
        Initialize transformer detector.
        
        Args:
            model_name: Hugging Face model identifier
            use_gpu: Whether to use GPU if available
            batch_size: Batch size for inference
            use_fp16: Use float16 precision (faster but may have issues)
        """
        self.model_name = model_name
        self.device = "cuda" if (use_gpu and torch.cuda.is_available()) else "cpu"
        self.batch_size = batch_size
        
        print(f"Loading transformer model: {model_name}")
        print(f"Device: {self.device}")
        
        try:
            # Load model and tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            # Use float32 by default for better compatibility
            # Float16 can be enabled for speed but may have compatibility issues
            dtype = torch.float32
            if use_fp16 and self.device == "cuda":
                dtype = torch.float16
                print("  Using FP16 precision")
            
            self.model = AutoModelForTokenClassification.from_pretrained(
                model_name,
                use_safetensors=True  # Use safetensors format to avoid torch.load vulnerability
            )
            self.model.to(self.device)
            
            # Convert to desired dtype after loading
            if dtype == torch.float16:
                self.model.half()
            
            self.model.eval()
            
            # Create pipeline for easier inference
            self.pipeline = pipeline(
                "token-classification",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" else -1,
                aggregation_strategy="simple"  # Merge subword tokens
            )
            
            print("✓ Transformer model loaded successfully")
            if self.device == "cuda":
                print(f"  GPU: {torch.cuda.get_device_name(0)}")
                print(f"  VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
        
        except Exception as e:
            print(f"✗ Error loading model: {e}")
            raise
    
    def detect(self, text: str, confidence_threshold: float = 0.5) -> List[Detection]:
        """
        Detect PII entities in text using transformer model.
        
        Args:
            text: Input text to analyze
            confidence_threshold: Minimum confidence score (0-1)
            
        Returns:
            List of Detection objects
        """
        if not text or len(text.strip()) == 0:
            return []
        
        # Run inference
        try:
            results = self.pipeline(text)
        except Exception as e:
            print(f"Warning: Inference failed: {e}")
            return []
        
        # Convert results to Detection objects
        detections = []
        for result in results:
            # Filter by confidence
            if result['score'] < confidence_threshold:
                continue
            
            # Map entity type
            entity_type = self.ENTITY_MAPPING.get(
                result['entity_group'],
                result['entity_group']
            )
            
            detections.append(Detection(
                text=result['word'].strip(),
                start=result['start'],
                end=result['end'],
                entity_type=entity_type,
                confidence=result['score']
            ))
        
        return detections
    
    def batch_detect(
        self,
        texts: List[str],
        confidence_threshold: float = 0.5
    ) -> List[List[Detection]]:
        """
        Process multiple texts in batch.
        
        Args:
            texts: List of input texts
            confidence_threshold: Minimum confidence score
            
        Returns:
            List of detection lists
        """
        all_detections = []
        
        for text in texts:
            detections = self.detect(text, confidence_threshold)
            all_detections.append(detections)
        
        return all_detections


class QwenPIIDetector:
    """
    Alternative detector using Qwen model for PII detection.
    This uses a causal language model approach.
    """
    
    def __init__(self, model_name: str = "Qwen/Qwen2-0.5B-Instruct", use_gpu: bool = True):
        """Initialize Qwen-based detector"""
        self.device = "cuda" if (use_gpu and torch.cuda.is_available()) else "cpu"
        
        print(f"Loading Qwen model: {model_name}")
        print(f"Device: {self.device}")
        
        from transformers import AutoModelForCausalLM
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="auto" if self.device == "cuda" else None
        )
        
        print("✓ Qwen model loaded successfully")
    
    def detect(self, text: str) -> List[Detection]:
        """
        Detect PII using Qwen model with prompt engineering.
        
        Args:
            text: Input text
            
        Returns:
            List of Detection objects
        """
        import json
        import re
        
        # Use a simpler approach - ask model to extract PII directly
        messages = [
            {
                "role": "system",
                "content": "You are a PII detection assistant. Extract all personally identifiable information from the text."
            },
            {
                "role": "user",
                "content": f"Extract all PII from this text and list each item on a new line with its type:\n\n{text}"
            }
        ]
        
        # Format prompt
        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # Generate
        model_inputs = self.tokenizer([prompt], return_tensors="pt").to(self.model.device)
        
        # Set pad token if not set
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        with torch.no_grad():
            generated_ids = self.model.generate(
                model_inputs.input_ids,
                attention_mask=model_inputs.attention_mask,
                max_new_tokens=256,
                do_sample=False,
                pad_token_id=self.tokenizer.pad_token_id
            )
        
        response = self.tokenizer.batch_decode(
            generated_ids[:, model_inputs.input_ids.shape[1]:],
            skip_special_tokens=True
        )[0]
        
        # Parse response using regex patterns
        detections = []
        
        # Common PII patterns
        patterns = {
            'EMAIL': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'PHONE': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'SSN': r'\b\d{3}-\d{2}-\d{4}\b',
        }
        
        # Search for patterns in original text
        for entity_type, pattern in patterns.items():
            for match in re.finditer(pattern, text):
                detections.append(Detection(
                    text=match.group(),
                    start=match.start(),
                    end=match.end(),
                    entity_type=entity_type,
                    confidence=0.85
                ))
        
        # Also try to find names mentioned in response
        # Look for capitalized words that might be names
        name_pattern = r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
        for match in re.finditer(name_pattern, text):
            # Check if it's in the model's response
            if match.group() in response:
                # Avoid duplicates
                if not any(d.text == match.group() for d in detections):
                    detections.append(Detection(
                        text=match.group(),
                        start=match.start(),
                        end=match.end(),
                        entity_type='PERSON',
                        confidence=0.75
                    ))
        
        return detections


if __name__ == "__main__":
    import time
    
    print("Testing Transformer PII Detector")
    print("=" * 60)
    
    # Define test text at module level so it's available to all tests
    test_text = """
    John Smith works at Google in Mountain View. 
    Contact him at john.smith@gmail.com or call 555-123-4567.
    His employee ID is EMP-12345.
    """
    
    # Test with DeBERTa model
    print("\n1. Testing DeBERTa-based detector:")
    try:
        detector = TransformerDetector()
        
        print(f"\nInput: {test_text.strip()}")
        print("-" * 60)
        
        start_time = time.time()
        detections = detector.detect(test_text)
        elapsed = (time.time() - start_time) * 1000
        
        print(f"Found {len(detections)} entities (took {elapsed:.2f}ms):")
        for det in detections:
            print(f"  {det.entity_type:15} | {det.text:30} | conf: {det.confidence:.3f}")
        
        print("\n✓ DeBERTa detector test complete!")
    
    except Exception as e:
        print(f"✗ Error testing DeBERTa detector: {e}")
    
    # Optionally test Qwen
    print("\n" + "=" * 60)
    print("\n2. Testing Qwen-based detector (optional):")
    try:
        qwen_detector = QwenPIIDetector()
        
        start_time = time.time()
        detections = qwen_detector.detect(test_text)
        elapsed = (time.time() - start_time) * 1000
        
        print(f"Found {len(detections)} entities (took {elapsed:.2f}ms):")
        for det in detections:
            print(f"  {det.entity_type:15} | {det.text:30} | conf: {det.confidence:.3f}")
        
        print("\n✓ Qwen detector test complete!")
    except Exception as e:
        print(f"Note: Qwen detector test skipped: {e}")