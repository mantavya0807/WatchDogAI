# ✅ YOUR SETUP CHECKLIST

Follow this checklist in order. Check off each item as you complete it!

## Phase 1: Environment Setup (30-45 min)

- [ ] **1.1** Download and install Python 3.11 from python.org
  - Make sure to check "Add Python to PATH"
  - Verify: `python --version` shows 3.11.x

- [ ] **1.2** Download and install Tesseract OCR
  - Get from: https://github.com/UB-Mannheim/tesseract/wiki
  - Install to default location
  - Verify: `tesseract --version` works

- [ ] **1.3** (Optional) Install CUDA for GPU
  - Only if you have NVIDIA GPU
  - Download from: https://developer.nvidia.com/cuda-downloads
  - Verify: `nvcc --version` works

- [ ] **1.4** Create project directory
  ```powershell
  mkdir pii-guard
  cd pii-guard
  ```

- [ ] **1.5** Copy all project files to pii-guard folder
  - All .py files
  - All .md files
  - The src/ directory

## Phase 2: Python Environment (15 min)

- [ ] **2.1** Create virtual environment
  ```powershell
  python -m venv venv
  ```

- [ ] **2.2** Activate virtual environment
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
  - You should see (venv) at start of prompt

- [ ] **2.3** Upgrade pip
  ```powershell
  python -m pip install --upgrade pip
  ```

- [ ] **2.4** Install PyTorch with CUDA (or CPU)
  ```powershell
  # For CUDA 12.1
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
  
  # OR for CPU only
  pip install torch torchvision torchaudio
  ```

- [ ] **2.5** Install core packages
  ```powershell
  pip install transformers>=4.51.0 accelerate sentencepiece protobuf
  pip install spacy
  pip install pytesseract Pillow opencv-python
  pip install pyyaml python-dotenv regex tqdm
  ```

- [ ] **2.6** Download spaCy models
  ```powershell
  python -m spacy download en_core_web_sm
  python -m spacy download en_core_web_lg
  ```

## Phase 3: Verification (10 min)

- [ ] **3.1** Run installation checker
  ```powershell
  python verify_installation.py
  ```
  - Should see mostly ✓ green checkmarks

- [ ] **3.2** Run quickstart tests
  ```powershell
  python quickstart.py
  ```
  - Should pass 8-9 out of 9 tests
  - GPU test can fail if no NVIDIA card

- [ ] **3.3** Test individual components
  ```powershell
  python src/detectors/regex_detector.py
  python src/detectors/spacy_detector.py
  python src/escrow_db.py
  python src/obfuscator.py
  ```
  - Each should run and show test results

## Phase 4: First Real Test (5 min)

- [ ] **4.1** Try interactive mode
  ```powershell
  python cli.py interactive
  ```

- [ ] **4.2** Test with sample text
  ```
  > John Smith at john@email.com, phone: 555-123-4567
  ```
  - Should see placeholders like {PERSON_1}, {EMAIL_1}, {PHONE_1}

- [ ] **4.3** Test text file obfuscation
  ```powershell
  # Create test file
  @"
  Name: Alice Johnson
  Email: alice@company.com
  Phone: (555) 987-6543
  "@ | Out-File test.txt
  
  # Obfuscate it
  python cli.py text --file test.txt --output test_obfuscated.txt
  
  # Check result
  cat test_obfuscated.txt
  ```

- [ ] **4.4** View database stats
  ```powershell
  python cli.py stats --show-entries
  ```

## Phase 5: Understanding (10 min)

- [ ] **5.1** Read README.md
  - Understand what each component does
  - Review the examples

- [ ] **5.2** Read GETTING_STARTED.md
  - Understand the architecture
  - Review next steps

- [ ] **5.3** Browse the code
  - Open `src/obfuscator.py` and read comments
  - Open `src/detectors/regex_detector.py`
  - Understand the flow

## 🎉 DONE!

If all checkboxes are checked, you have:

✅ Complete PII detection engine  
✅ Text obfuscation system  
✅ Image processing capability  
✅ Working CLI interface  
✅ Understanding of the system  

## 🔥 Next Steps

Now you can start building:
1. Windows clipboard monitor
2. Chrome extension
3. Native messaging bridge
4. System tray UI

## ❌ If Something Failed

### Python not found
- Reinstall Python 3.11
- Make sure "Add to PATH" was checked
- Restart PowerShell

### Tesseract not found
- Reinstall Tesseract
- Add to PATH manually:
  - Settings → System → About → Advanced system settings
  - Environment Variables → Path → Add: `C:\Program Files\Tesseract-OCR`

### spaCy model not found
```powershell
python -m spacy download en_core_web_lg --force
```

### Module import errors
```powershell
# Make sure venv is activated (you should see (venv) in prompt)
.\venv\Scripts\Activate.ps1

# Reinstall specific package
pip install --force-reinstall package_name
```

### Everything else
- Check SETUP_GUIDE.md troubleshooting section
- Run `python verify_installation.py` to see what's missing
- Make sure you're in the pii-guard directory
- Make sure virtual environment is activated

## 📞 Emergency Help

1. Run: `python verify_installation.py`
2. Copy the output
3. Check which specific test is failing
4. Look in SETUP_GUIDE.md for that component

---

**Time to complete: 1-2 hours for first-time setup**

Remember: Go step by step. Don't skip steps. Test after each phase!