# Desktop Data Exfiltration Guard - Setup Guide
## Complete Setup from Scratch (Windows)

### Prerequisites
- Windows 10/11
- Python 3.10 or 3.11 (NOT 3.12+ as some packages aren't compatible yet)
- VSCode with PowerShell terminal
- NVIDIA GPU with CUDA support (RTX 4060 mentioned) - Optional but recommended
- At least 8GB RAM (16GB+ recommended)

---

## PHASE 1: Install Core Dependencies

### Step 1: Install Python
1. Download Python 3.11.x from https://www.python.org/downloads/windows/
2. **CRITICAL**: Check "Add Python to PATH" during installation
3. Verify installation:
```powershell
python --version
# Should show Python 3.11.x
```

### Step 2: Install Tesseract OCR
1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Download the latest installer (e.g., `tesseract-ocr-w64-setup-5.3.x.exe`)
3. Install to default location: `C:\Program Files\Tesseract-OCR\`
4. **CRITICAL**: During installation, check "Add to PATH"
5. Verify:
```powershell
tesseract --version
# Should show Tesseract version info
```

If Tesseract is not in PATH, add manually:
```powershell
# Add to PATH (run as Administrator)
$env:Path += ";C:\Program Files\Tesseract-OCR"
# Make permanent
[System.Environment]::SetEnvironmentVariable("Path", $env:Path, [System.EnvironmentVariableTarget]::Machine)
```

### Step 3: Install CUDA (for GPU acceleration)
1. Check your NVIDIA driver version:
```powershell
nvidia-smi
```
2. Download CUDA Toolkit 12.x from: https://developer.nvidia.com/cuda-downloads
3. Install with default settings
4. Verify:
```powershell
nvcc --version
```

---

## PHASE 2: Project Setup

### Step 1: Create Project Directory
```powershell
# Navigate to your desired location
cd C:\Users\YourName\Documents
mkdir pii-guard
cd pii-guard
```

### Step 2: Create Python Virtual Environment
```powershell
# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# If you get execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Then try activating again
```

### Step 3: Upgrade pip
```powershell
python -m pip install --upgrade pip
```

---

## PHASE 3: Install Python Dependencies

### Step 1: Install PyTorch with CUDA support
```powershell
# For CUDA 12.1 (check your CUDA version with nvcc --version)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Verify PyTorch sees your GPU
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}')"
```

### Step 2: Install Core NLP Libraries
```powershell
# Install transformers and dependencies
pip install transformers>=4.51.0
pip install accelerate
pip install sentencepiece
pip install protobuf

# Install spaCy
pip install spacy

# Download spaCy English model (small for speed)
python -m spacy download en_core_web_sm

# Or large for better accuracy (recommended)
python -m spacy download en_core_web_lg
```

### Step 3: Install OCR Dependencies
```powershell
pip install pytesseract
pip install Pillow
pip install opencv-python
```

### Step 4: Install Database and Utilities
```powershell
pip install sqlite3  # Usually comes with Python
pip install pyyaml
pip install python-dotenv
```

### Step 5: Install Optional but Recommended
```powershell
# For better regex
pip install regex

# For progress bars during model downloads
pip install tqdm

# For JSON handling
pip install ujson
```

---

## PHASE 4: Download AI Models

### Step 1: Test Transformers Installation
Create a test script to download the Qwen model:

```powershell
# Create test file
New-Item -Path "test_model_download.py" -ItemType File
```

Add this content to `test_model_download.py`:
```python
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

print("Testing model download and GPU availability...")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")

# Download Qwen2-0.5B model for PII detection
# This is a small model that can detect PII well
model_name = "Qwen/Qwen2-0.5B-Instruct"
print(f"\nDownloading {model_name}...")

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device_map="auto" if torch.cuda.is_available() else None
)

print("\nModel downloaded successfully!")
print(f"Model device: {model.device}")
print("\nTesting inference...")

# Simple test
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
]
text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True
)
model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

generated_ids = model.generate(
    model_inputs.input_ids,
    max_new_tokens=50
)
response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
print(f"Test response: {response}\n")
print("✓ Everything is working!")
```

Run it:
```powershell
python test_model_download.py
```

This will download the Qwen2-0.5B model (~1GB) to your cache.

---

## PHASE 5: Verify Everything Works

Create a comprehensive verification script:

```powershell
New-Item -Path "verify_installation.py" -ItemType File
```

Add this to `verify_installation.py`:
```python
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
```

Run it:
```powershell
python verify_installation.py
```

---

## PHASE 6: Project Structure

Create the project structure:

```powershell
# Create directory structure
mkdir src
mkdir src\models
mkdir src\detectors
mkdir data
mkdir data\escrow
mkdir tests
mkdir tests\test_data
mkdir config

# Create __init__ files
New-Item -Path "src\__init__.py" -ItemType File
New-Item -Path "src\models\__init__.py" -ItemType File
New-Item -Path "src\detectors\__init__.py" -ItemType File
```

Your project structure should look like:
```
pii-guard/
├── venv/                 # Virtual environment
├── src/
│   ├── __init__.py
│   ├── models/
│   │   └── __init__.py
│   ├── detectors/
│   │   └── __init__.py
├── data/
│   └── escrow/          # Escrow database storage
├── tests/
│   └── test_data/       # Test images and text
├── config/              # Configuration files
└── verify_installation.py
```

---

## PHASE 7: Next Steps

After completing all phases above, you should have:
- ✓ Python 3.11 with virtual environment
- ✓ Tesseract OCR installed and working
- ✓ CUDA and GPU support (optional)
- ✓ All Python packages installed
- ✓ Qwen2-0.5B model downloaded
- ✓ spaCy models installed
- ✓ Project structure created

**Now you're ready to build the core obfuscation engine!**

The next steps will be:
1. Create regex pattern detector
2. Create spaCy NER detector  
3. Create transformer-based detector using Qwen
4. Build the obfuscation engine with escrow system
5. Add image OCR and obfuscation
6. Create CLI interface for testing

---

## Troubleshooting

### Issue: "Tesseract is not installed"
```powershell
# Set tesseract path manually in Python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

### Issue: "CUDA out of memory"
```python
# Use CPU instead
device = "cpu"
# Or use smaller batch sizes
```

### Issue: "Module not found"
```powershell
# Make sure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Reinstall package
pip install --force-reinstall package_name
```

### Issue: "spaCy model not found"
```powershell
# Download model again
python -m spacy download en_core_web_lg
```