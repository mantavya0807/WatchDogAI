"""
Quickstart Script
Run this after installation to verify everything works!
"""

import sys
from pathlib import Path

def print_header(title):
    """Print a nice header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")

def print_success(message):
    """Print success message"""
    print(f"✓ {message}")

def print_error(message):
    """Print error message"""
    print(f"✗ {message}")

def test_dependencies():
    """Test that all dependencies are installed"""
    print_header("TESTING DEPENDENCIES")
    
    packages = [
        ('torch', 'PyTorch'),
        ('transformers', 'Transformers'),
        ('spacy', 'spaCy'),
        ('PIL', 'Pillow'),
        ('cv2', 'OpenCV'),
        ('pytesseract', 'pytesseract'),
    ]
    
    all_ok = True
    for module, name in packages:
        try:
            __import__(module)
            print_success(f"{name} is installed")
        except ImportError:
            print_error(f"{name} is NOT installed")
            all_ok = False
    
    return all_ok

def test_tesseract():
    """Test Tesseract OCR"""
    print_header("TESTING TESSERACT OCR")
    
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        print_success(f"Tesseract is working (version {version})")
        return True
    except Exception as e:
        print_error(f"Tesseract test failed: {e}")
        print("\nTry setting the path manually:")
        print("  import pytesseract")
        print("  pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'")
        return False

def test_spacy_models():
    """Test spaCy models"""
    print_header("TESTING SPACY MODELS")
    
    import spacy
    
    models = ['en_core_web_sm', 'en_core_web_lg']
    found_models = []
    
    for model_name in models:
        try:
            nlp = spacy.load(model_name)
            print_success(f"spaCy model '{model_name}' is installed")
            found_models.append(model_name)
        except OSError:
            print_error(f"spaCy model '{model_name}' is NOT installed")
            print(f"  Install with: python -m spacy download {model_name}")
    
    return len(found_models) > 0

def test_gpu():
    """Test GPU availability"""
    print_header("TESTING GPU")
    
    import torch
    
    if torch.cuda.is_available():
        print_success("CUDA is available")
        print(f"  GPU: {torch.cuda.get_device_name(0)}")
        print(f"  CUDA Version: {torch.version.cuda}")
        print(f"  VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
        return True
    else:
        print("⚠ CUDA is not available (will use CPU)")
        print("  This is OK - the system will work, just slower for transformers")
        return False

def test_regex_detector():
    """Test regex detector"""
    print_header("TESTING REGEX DETECTOR")
    
    try:
        sys.path.insert(0, str(Path(__file__).parent / 'src'))
        from detectors.regex_detector import RegexPatternDetector
        
        detector = RegexPatternDetector()
        test_text = "Contact john@email.com or 555-123-4567. SSN: 123-45-6789"
        
        detections = detector.detect(test_text)
        print_success(f"Regex detector works! Found {len(detections)} PII items:")
        for det in detections:
            print(f"  - {det.entity_type}: {det.text}")
        
        return len(detections) > 0
    except Exception as e:
        print_error(f"Regex detector failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_spacy_detector():
    """Test spaCy detector"""
    print_header("TESTING SPACY DETECTOR")
    
    try:
        from detectors.spacy_detector import SpacyDetector
        
        detector = SpacyDetector()
        test_text = "John Smith works at Google in Mountain View."
        
        detections = detector.detect(test_text)
        print_success(f"spaCy detector works! Found {len(detections)} entities:")
        for det in detections:
            print(f"  - {det.entity_type}: {det.text}")
        
        return len(detections) > 0
    except Exception as e:
        print_error(f"spaCy detector failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_escrow_db():
    """Test escrow database"""
    print_header("TESTING ESCROW DATABASE")
    
    try:
        from escrow_db import EscrowDatabase
        
        # Create test database
        db = EscrowDatabase("data/escrow/quickstart_test.db")
        
        # Store some values
        p1 = db.store("John Smith", "PERSON", "quickstart_test")
        e1 = db.store("john@email.com", "EMAIL", "quickstart_test")
        
        # Retrieve
        restored_person = db.retrieve(p1)
        restored_email = db.retrieve(e1)
        
        if restored_person == "John Smith" and restored_email == "john@email.com":
            print_success("Escrow database works!")
            print(f"  Stored and retrieved: {restored_person}, {restored_email}")
            
            stats = db.get_stats()
            print(f"  Total entries in database: {stats['total_entries']}")
        else:
            print_error("Escrow database retrieval failed")
            return False
        
        db.close()
        return True
    except Exception as e:
        print_error(f"Escrow database failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_obfuscator():
    """Test main obfuscator"""
    print_header("TESTING MAIN OBFUSCATOR")
    
    try:
        from obfuscator import PIIObfuscator
        
        obfuscator = PIIObfuscator(
            use_regex=True,
            use_spacy=True,
            use_transformer=False  # Skip for speed
        )
        
        test_text = """
        Contact John Smith at john.smith@email.com or call (555) 123-4567.
        His SSN is 123-45-6789 and he works at Google in Mountain View.
        """
        
        result = obfuscator.obfuscate(test_text, source="quickstart_test")
        
        print_success(f"Obfuscator works! Found {result.num_redactions} PII items")
        print(f"\nOriginal:\n{test_text.strip()}")
        print(f"\nObfuscated:\n{result.obfuscated_text.strip()}")
        
        # Test deobfuscation
        restored = obfuscator.deobfuscate(result.obfuscated_text)
        if restored.strip() == test_text.strip():
            print_success("Deobfuscation works!")
        else:
            print("⚠ Deobfuscation might have issues")
        
        print(f"\nPerformance:")
        print(f"  Detection: {result.detection_time_ms:.2f}ms")
        print(f"  Obfuscation: {result.obfuscation_time_ms:.2f}ms")
        
        obfuscator.close()
        return True
    except Exception as e:
        print_error(f"Obfuscator failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_cli():
    """Test CLI interface"""
    print_header("TESTING CLI INTERFACE")
    
    try:
        import subprocess
        
        # Test help command
        result = subprocess.run(
            ['python', 'cli.py', '--help'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print_success("CLI interface is working")
            print("\nAvailable commands:")
            print("  python cli.py text --text 'your text here'")
            print("  python cli.py image --input image.png --output redacted.png")
            print("  python cli.py stats")
            print("  python cli.py interactive")
            return True
        else:
            print_error(f"CLI test failed with return code {result.returncode}")
            return False
    except Exception as e:
        print_error(f"CLI test failed: {e}")
        return False

def main():
    print("\n" + "╔" + "=" * 68 + "╗")
    print("║" + " " * 20 + "PII GUARD QUICKSTART" + " " * 28 + "║")
    print("║" + " " * 15 + "Verify Your Installation" + " " * 28 + "║")
    print("╚" + "=" * 68 + "╝")
    
    tests = [
        ("Dependencies", test_dependencies),
        ("Tesseract OCR", test_tesseract),
        ("spaCy Models", test_spacy_models),
        ("GPU", test_gpu),
        ("Regex Detector", test_regex_detector),
        ("spaCy Detector", test_spacy_detector),
        ("Escrow Database", test_escrow_db),
        ("Main Obfuscator", test_obfuscator),
        ("CLI Interface", test_cli),
    ]
    
    results = {}
    
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except KeyboardInterrupt:
            print("\n\nTest interrupted by user")
            sys.exit(1)
        except Exception as e:
            print_error(f"Test '{name}' crashed: {e}")
            results[name] = False
    
    # Summary
    print_header("SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}\n")
    
    for name, result in results.items():
        status = "✓" if result else "✗"
        print(f"  {status} {name}")
    
    if passed == total:
        print("\n" + "=" * 70)
        print("  🎉 ALL TESTS PASSED! 🎉")
        print("=" * 70)
        print("\nYou're ready to use PII Guard!")
        print("\nNext steps:")
        print("  1. Try interactive mode: python cli.py interactive")
        print("  2. Read the README.md for usage examples")
        print("  3. Start building your Chrome extension integration!")
    else:
        print("\n" + "=" * 70)
        print("  ⚠ SOME TESTS FAILED ⚠")
        print("=" * 70)
        print("\nPlease fix the failing tests before proceeding.")
        print("Check SETUP_GUIDE.md for troubleshooting help.")
    
    print("\n")

if __name__ == "__main__":
    main()