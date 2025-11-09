#!/usr/bin/env python3
"""Verification script for PII Guard setup"""

import sys
import importlib

def check_package(package_name, import_name=None):
    """Check if a package is installed"""
    if import_name is None:
        import_name = package_name
    
    try:
        importlib.import_module(import_name)
        print(f"✓ {package_name} is installed")
        return True
    except ImportError:
        print(f"✗ {package_name} is NOT installed")
        return False

def check_tesseract():
    """Check Tesseract OCR"""
    try:
        import pytesseract
        from PIL import Image
        import numpy as np
        
        # Try to get Tesseract version
        version = pytesseract.get_tesseract_version()
        print(f"✓ Tesseract OCR is installed (version {version})")
        return True
    except Exception as e:
        print(f"✗ Tesseract OCR check failed: {e}")
        return False

def check_gpu():
    """Check GPU availability"""
    try:
        import torch
        if torch.cuda.is_available():
            print(f"✓ CUDA is available")
            print(f"  GPU: {torch.cuda.get_device_name(0)}")
            print(f"  CUDA Version: {torch.version.cuda}")
            return True
        else:
            print("⚠ CUDA is not available (will use CPU)")
            return False
    except Exception as e:
        print(f"✗ GPU check failed: {e}")
        return False

def check_spacy_models():
    """Check spaCy models"""
    try:
        import spacy
        
        # Try to load models
        models_to_check = ['en_core_web_sm', 'en_core_web_lg']
        for model_name in models_to_check:
            try:
                nlp = spacy.load(model_name)
                print(f"✓ spaCy model '{model_name}' is installed")
            except OSError:
                print(f"✗ spaCy model '{model_name}' is NOT installed")
        return True
    except Exception as e:
        print(f"✗ spaCy check failed: {e}")
        return False

def main():
    print("=" * 60)
    print("PII GUARD - INSTALLATION VERIFICATION")
    print("=" * 60)
    
    print("\n1. Checking Python Version:")
    print(f"  Python {sys.version}")
    
    print("\n2. Checking Core Packages:")
    packages = [
        'torch',
        'transformers',
        'spacy',
        'PIL',
        'cv2',
        'pytesseract',
        'yaml',
    ]
    
    for pkg in packages:
        check_package(pkg, pkg)
    
    print("\n3. Checking Tesseract OCR:")
    check_tesseract()
    
    print("\n4. Checking GPU:")
    check_gpu()
    
    print("\n5. Checking spaCy Models:")
    check_spacy_models()
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()