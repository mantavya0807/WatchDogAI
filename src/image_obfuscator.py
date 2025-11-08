"""
OCR Module
Extract text from images and obfuscate PII.
Uses Tesseract OCR and OpenCV for image processing.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
import numpy as np
from PIL import Image
import pytesseract
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass

@dataclass
class TextBox:
    """Represents text detected in an image"""
    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: float

class ImagePIIObfuscator:
    """
    Obfuscate PII in images using OCR.
    
    Process:
    1. Extract text from image using Tesseract OCR
    2. Detect PII in extracted text
    3. Find bounding boxes for PII text
    4. Blur/redact those regions
    """
    
    def __init__(self, text_obfuscator=None, blur_strength: int = 25):
        """
        Initialize image obfuscator.
        
        Args:
            text_obfuscator: PIIObfuscator instance for text analysis
            blur_strength: Strength of blur effect (odd number)
        """
        self.text_obfuscator = text_obfuscator
        self.blur_strength = blur_strength if blur_strength % 2 == 1 else blur_strength + 1
        
        # Try to set Tesseract path if needed (Windows)
        try:
            pytesseract.get_tesseract_version()
        except Exception:
            # Try common Windows installation path
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    
    def extract_text_boxes(self, image_path: str) -> List[TextBox]:
        """
        Extract text and bounding boxes from image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            List of TextBox objects
        """
        # Load image
        img = Image.open(image_path)
        
        # Use pytesseract to get detailed data
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        
        text_boxes = []
        n_boxes = len(data['text'])
        
        for i in range(n_boxes):
            # Filter out low confidence and empty text
            if int(data['conf'][i]) > 0 and data['text'][i].strip():
                text_boxes.append(TextBox(
                    text=data['text'][i],
                    x=data['left'][i],
                    y=data['top'][i],
                    width=data['width'][i],
                    height=data['height'][i],
                    confidence=float(data['conf'][i]) / 100.0
                ))
        
        return text_boxes
    
    def extract_text(self, image_path: str) -> str:
        """
        Extract all text from image as single string.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Extracted text
        """
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return text
    
    def obfuscate_image(
        self,
        image_path: str,
        output_path: str,
        method: str = 'blur'  # 'blur' or 'black'
    ) -> Dict:
        """
        Obfuscate PII in image.
        
        Args:
            image_path: Path to input image
            output_path: Path to save obfuscated image
            method: Obfuscation method ('blur' or 'black')
            
        Returns:
            Dict with stats
        """
        if not self.text_obfuscator:
            raise ValueError("text_obfuscator is required for PII detection")
        
        # Extract text
        print(f"Extracting text from {image_path}...")
        text_boxes = self.extract_text_boxes(image_path)
        full_text = ' '.join([box.text for box in text_boxes])
        
        print(f"Extracted {len(text_boxes)} text boxes")
        print(f"Full text: {full_text[:200]}...")
        
        # Detect PII in text
        print("Detecting PII...")
        result = self.text_obfuscator.obfuscate(full_text, source=f"image:{image_path}")
        
        if result.num_redactions == 0:
            print("No PII detected in image")
            # Copy original image
            import shutil
            shutil.copy(image_path, output_path)
            return {
                'num_redactions': 0,
                'redacted_texts': [],
                'method': method
            }
        
        print(f"Found {result.num_redactions} PII items")
        
        # Load image with OpenCV
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        # Find text boxes containing PII
        redacted_texts = []
        for placeholder, original_text in result.replacements.items():
            print(f"Looking for: {original_text}")
            
            # Split the PII text into words for partial matching
            pii_words = original_text.lower().split()
            matched_boxes = []
            
            # Strategy 1: Try exact match first
            for text_box in text_boxes:
                if original_text.lower() == text_box.text.lower().strip():
                    matched_boxes.append(text_box)
                    print(f"  Exact match in box at ({text_box.x}, {text_box.y})")
            
            # Strategy 2: Try substring match
            if not matched_boxes:
                for text_box in text_boxes:
                    if original_text.lower() in text_box.text.lower():
                        matched_boxes.append(text_box)
                        print(f"  Substring match in box at ({text_box.x}, {text_box.y})")
            
            # Strategy 3: Try word-by-word match for multi-word entities
            if not matched_boxes and len(pii_words) > 1:
                for word in pii_words:
                    if len(word) < 2:  # Skip very short words
                        continue
                    for text_box in text_boxes:
                        if word in text_box.text.lower():
                            if text_box not in matched_boxes:
                                matched_boxes.append(text_box)
                                print(f"  Word match '{word}' in box at ({text_box.x}, {text_box.y})")
            
            # Strategy 4: Partial match (for phone numbers, SSNs with formatting)
            if not matched_boxes:
                # Remove special characters and try again
                clean_pii = ''.join(c for c in original_text if c.isalnum())
                for text_box in text_boxes:
                    clean_box = ''.join(c for c in text_box.text if c.isalnum())
                    if len(clean_pii) > 3 and clean_pii.lower() in clean_box.lower():
                        matched_boxes.append(text_box)
                        print(f"  Partial match in box at ({text_box.x}, {text_box.y})")
            
            # If we found matching boxes, blur the entire region
            if matched_boxes:
                # Calculate bounding box that encompasses all matched boxes
                min_x = min(box.x for box in matched_boxes)
                min_y = min(box.y for box in matched_boxes)
                max_x = max(box.x + box.width for box in matched_boxes)
                max_y = max(box.y + box.height for box in matched_boxes)
                
                # Add padding
                padding = 5
                x1 = max(0, min_x - padding)
                y1 = max(0, min_y - padding)
                x2 = min(img.shape[1], max_x + padding)
                y2 = min(img.shape[0], max_y + padding)
                
                print(f"  Blurring region: ({x1}, {y1}) to ({x2}, {y2})")
                
                # Apply obfuscation
                if method == 'blur':
                    # Extract region
                    roi = img[y1:y2, x1:x2]
                    if roi.size > 0:  # Make sure region is valid
                        # Apply Gaussian blur
                        blurred = cv2.GaussianBlur(roi, (self.blur_strength, self.blur_strength), 0)
                        # Replace region
                        img[y1:y2, x1:x2] = blurred
                elif method == 'black':
                    # Black rectangle
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 0), -1)
                elif method == 'pixelate':
                    # Pixelate effect
                    roi = img[y1:y2, x1:x2]
                    if roi.size > 0:
                        h, w = roi.shape[:2]
                        if h > 0 and w > 0:
                            # Shrink then enlarge to create pixelation
                            small = cv2.resize(roi, (max(1, w // 10), max(1, h // 10)), interpolation=cv2.INTER_LINEAR)
                            pixelated = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
                            img[y1:y2, x1:x2] = pixelated
                
                redacted_texts.append({
                    'text': original_text,
                    'box': (x1, y1, x2, y2),
                    'matched_boxes': len(matched_boxes)
                })
            else:
                print(f"  ⚠ Could not find boxes for: {original_text}")
        
        # Save obfuscated image
        cv2.imwrite(output_path, img)
        print(f"✓ Saved obfuscated image to {output_path}")
        
        return {
            'num_redactions': len(redacted_texts),
            'redacted_texts': redacted_texts,
            'method': method
        }
    
    def preview_text_boxes(self, image_path: str, output_path: str):
        """
        Draw boxes around all detected text (for debugging).
        
        Args:
            image_path: Input image
            output_path: Output image with boxes
        """
        text_boxes = self.extract_text_boxes(image_path)
        
        img = cv2.imread(image_path)
        
        for box in text_boxes:
            # Draw rectangle
            cv2.rectangle(
                img,
                (box.x, box.y),
                (box.x + box.width, box.y + box.height),
                (0, 255, 0),  # Green
                2
            )
            
            # Draw text
            cv2.putText(
                img,
                box.text,
                (box.x, box.y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1
            )
        
        cv2.imwrite(output_path, img)
        print(f"✓ Saved preview to {output_path}")


if __name__ == "__main__":
    import tempfile
    from obfuscator import PIIObfuscator
    
    print("\nTesting Image PII Obfuscator")
    print("=" * 60)
    
    # Create text obfuscator
    text_obfuscator = PIIObfuscator(
        use_regex=True,
        use_spacy=True,
        use_transformer=False
    )
    
    # Create image obfuscator
    img_obfuscator = ImagePIIObfuscator(text_obfuscator=text_obfuscator)
    
    # Test with a simple generated image (since we don't have test images)
    print("\nGenerating test image with PII...")
    
    # Create a test image with text
    from PIL import Image, ImageDraw, ImageFont
    
    # Create image
    img = Image.new('RGB', (800, 400), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a larger font
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        font = ImageFont.load_default()
    
    # Add test text with PII
    test_text = """
    Name: John Smith
    Email: john.smith@email.com
    Phone: (555) 123-4567
    SSN: 123-45-6789
    Address: 123 Main Street
    """
    
    draw.text((50, 50), test_text, fill='black', font=font)
    
    # Save test image
    test_img_path = "tests/test_data/test_pii_image.png"
    Path(test_img_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(test_img_path)
    print(f"✓ Created test image: {test_img_path}")
    
    # Test text extraction
    print("\n1. Testing text extraction:")
    extracted_text = img_obfuscator.extract_text(test_img_path)
    print(f"Extracted text:\n{extracted_text}")
    
    # Test text boxes
    print("\n2. Testing text box detection:")
    text_boxes = img_obfuscator.extract_text_boxes(test_img_path)
    print(f"Found {len(text_boxes)} text boxes:")
    for i, box in enumerate(text_boxes[:10], 1):  # Show first 10
        print(f"  {i}. '{box.text}' at ({box.x}, {box.y})")
    
    # Test image obfuscation
    print("\n3. Testing image obfuscation:")
    output_paths = {
        'blur': "tests/test_data/test_pii_image_blurred.png",
        'black': "tests/test_data/test_pii_image_redacted.png",
        'pixelate': "tests/test_data/test_pii_image_pixelated.png"
    }
    
    for method, output_path in output_paths.items():
        print(f"\n  Testing {method} method...")
        result = img_obfuscator.obfuscate_image(
            test_img_path,
            output_path,
            method=method
        )
        print(f"  ✓ Redacted {result['num_redactions']} items")
        print(f"  ✓ Saved to {output_path}")
    
    # Test preview
    print("\n4. Creating text box preview:")
    img_obfuscator.preview_text_boxes(
        test_img_path,
        "tests/test_data/test_pii_image_preview.png"
    )
    
    text_obfuscator.close()
    
    print("\n" + "=" * 60)
    print("✓ Image obfuscator test complete!")
    print("\nGenerated files:")
    print("  - tests/test_data/test_pii_image.png (original)")
    print("  - tests/test_data/test_pii_image_blurred.png")
    print("  - tests/test_data/test_pii_image_redacted.png")
    print("  - tests/test_data/test_pii_image_pixelated.png")
    print("  - tests/test_data/test_pii_image_preview.png")