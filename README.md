# PII Guard - Desktop Data Exfiltration Guard

A powerful, local-first PII (Personally Identifiable Information) detection and obfuscation system for Windows. Protects sensitive data from being leaked through ChatGPT, Claude, email, or any web application.

## 🎯 What It Does

- **Text Obfuscation**: Automatically detects and replaces PII in text with placeholders
- **Image Obfuscation**: Extracts text from images and blurs/redacts PII
- **Reversible**: Uses escrow system to restore original values when needed
- **Multi-Layer Detection**: Combines regex, spaCy NER, and transformer models
- **Local-First**: Everything runs on your machine - no cloud, no telemetry
- **Fast**: Optimized for real-time use (30-50ms for text detection)

## 📊 What It Detects

### Structured Data (Regex)
- Email addresses
- Phone numbers (US format)
- Social Security Numbers (SSN)
- Credit card numbers (with Luhn validation)
- IP addresses
- URLs
- API keys (high entropy detection)
- Dates
- ZIP codes

### Named Entities (spaCy + Transformers)
- Person names
- Locations (cities, states, countries)
- Organizations (companies, institutions)
- Dates and times
- Addresses

## 🚀 Quick Start

### 1. Follow Setup Guide

Complete the installation steps in `SETUP_GUIDE.md`:
- Install Python 3.11
- Install Tesseract OCR
- Install CUDA (optional, for GPU)
- Create virtual environment
- Install dependencies

### 2. Test the System

Run the verification script:
```powershell
python verify_installation.py
```

### 3. Try Basic Text Obfuscation

```powershell
# Interactive mode - easiest way to start!
python cli.py interactive

# Or obfuscate specific text
python cli.py text --text "Contact John Smith at john@email.com or call 555-123-4567"
```

### 4. Test Each Component

```powershell
# Test regex detector
python src/detectors/regex_detector.py

# Test spaCy detector
python src/detectors/spacy_detector.py

# Test escrow database
python src/escrow_db.py

# Test full obfuscator
python src/obfuscator.py

# Test image obfuscator
python src/image_obfuscator.py
```

## 📖 Usage Examples

### Text Obfuscation

#### From Command Line
```powershell
# Simple text
python cli.py text --text "My name is Alice and my email is alice@company.com"

# From file
python cli.py text --file input.txt --output obfuscated.txt

# Show deobfuscated version too
python cli.py text --text "Contact John at john@email.com" --deobfuscate

# Use transformer for better accuracy (slower)
python cli.py text --text "..." --transformer
```

#### Interactive Mode
```powershell
python cli.py interactive
```

Then just type or paste text:
```
Enter text: John Smith works at Google, contact at john@gmail.com
Obfuscated: {PERSON_1} works at {ORGANIZATION_1}, contact at {EMAIL_1}
Found 3 PII items
```

#### From Python
```python
from src.obfuscator import PIIObfuscator

# Create obfuscator
obfuscator = PIIObfuscator(
    use_regex=True,
    use_spacy=True,
    use_transformer=False  # Set True for better accuracy
)

# Obfuscate text
text = "Contact John Smith at john.smith@email.com or (555) 123-4567"
result = obfuscator.obfuscate(text)

print(f"Original: {result.original_text}")
print(f"Obfuscated: {result.obfuscated_text}")
print(f"Found {result.num_redactions} PII items")

# Deobfuscate
original = obfuscator.deobfuscate(result.obfuscated_text)
print(f"Restored: {original}")

obfuscator.close()
```

### Image Obfuscation

```powershell
# Blur PII in image
python cli.py image --input photo.png --output redacted.png --method blur

# Black rectangles instead
python cli.py image --input scan.jpg --output redacted.jpg --method black

# Pixelate effect
python cli.py image --input document.png --output redacted.png --method pixelate
```

From Python:
```python
from src.obfuscator import PIIObfuscator
from src.image_obfuscator import ImagePIIObfuscator

# Create obfuscators
text_obf = PIIObfuscator()
img_obf = ImagePIIObfuscator(text_obfuscator=text_obf)

# Process image
result = img_obf.obfuscate_image(
    "input.png",
    "output.png",
    method='blur'
)

print(f"Redacted {result['num_redactions']} items")
```

### View Statistics

```powershell
# Basic stats
python cli.py stats

# Show all entries
python cli.py stats --show-entries

# Limit entries shown
python cli.py stats --show-entries --limit 10
```

## 🔧 Configuration

### Detection Layers

You can enable/disable detection layers based on your needs:

```python
obfuscator = PIIObfuscator(
    use_regex=True,        # Fast pattern matching (recommended)
    use_spacy=True,        # Fast NER (recommended)
    use_transformer=False, # Slow but accurate (optional)
    spacy_model="en_core_web_lg"  # or "en_core_web_sm" for speed
)
```

**Performance vs Accuracy:**
- **Fast** (regex + spaCy): ~30-50ms, good accuracy
- **Accurate** (regex + spaCy + transformer): ~200-400ms, best accuracy
- **Fastest** (regex only): ~1-5ms, patterns only

### Obfuscation Methods

For images, choose the obfuscation method:
- `blur`: Gaussian blur (most natural looking)
- `black`: Black rectangles (most secure)
- `pixelate`: Pixelation effect (stylized)

## 📁 Project Structure

```
pii-guard/
├── SETUP_GUIDE.md           # Complete setup instructions
├── README.md                # This file
├── cli.py                   # Command-line interface
├── verify_installation.py   # Installation checker
├── src/
│   ├── obfuscator.py        # Main obfuscation engine
│   ├── escrow_db.py         # Escrow database
│   ├── image_obfuscator.py  # Image processing
│   ├── detectors/
│   │   ├── regex_detector.py       # Pattern matching
│   │   ├── spacy_detector.py       # spaCy NER
│   │   └── transformer_detector.py # Transformer models
├── data/
│   └── escrow/              # Escrow database storage
└── tests/
    └── test_data/           # Test files
```

## 🎓 How It Works

### Three-Layer Detection

1. **Layer 1: Regex Pattern Matching** (~1-5ms)
   - Fast pattern matching for structured data
   - Emails, phones, SSNs, credit cards, etc.
   - Includes validation (e.g., Luhn algorithm for credit cards)

2. **Layer 2: spaCy NER** (~30-50ms)
   - Named Entity Recognition
   - Person names, locations, organizations
   - CPU-based, very fast

3. **Layer 3: Transformer Models** (~200-400ms)
   - Context-aware detection
   - Best accuracy
   - GPU-accelerated
   - Optional - only use when accuracy is critical

### Escrow System

All PII is stored in a local SQLite database:
```
{PERSON_1} -> "John Smith"
{EMAIL_1}  -> "john@email.com"
{PHONE_1}  -> "555-123-4567"
```

Features:
- **Instance tracking**: Same value = same placeholder
- **Reversible**: Can restore original text
- **Salted hashing**: Additional security
- **Source tracking**: Know where data came from
- **Context storage**: Optional surrounding text

### Image Processing

1. Extract text with Tesseract OCR
2. Detect PII in extracted text
3. Find bounding boxes for PII
4. Apply obfuscation (blur/black/pixelate)
5. Save obfuscated image

## 🔒 Privacy & Security

- **100% Local**: No cloud, no API calls, no telemetry
- **Encrypted Storage**: Escrow database can be encrypted
- **Open Source**: Fully auditable code
- **User Control**: You decide what to obfuscate
- **Reversible**: Original data only stored locally, with your consent

## ⚡ Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Text (regex + spaCy) | 30-50ms | Recommended for real-time |
| Text (with transformer) | 200-400ms | Use when accuracy critical |
| Image OCR | 1-2s | Depends on image size |
| Image obfuscation | 1.5-2s | Includes OCR + detection |

**GPU Acceleration:**
- With NVIDIA GPU: 2-3x faster for transformers
- CPU-only: Still very fast for regex + spaCy

## 🐛 Troubleshooting

### Tesseract not found
```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

### spaCy model not found
```powershell
python -m spacy download en_core_web_lg
```

### CUDA out of memory
```python
# Use CPU instead
obfuscator = PIIObfuscator(use_transformer=False)
# Or
import torch
device = "cpu"
```

### Module not found
```powershell
# Make sure venv is activated
.\venv\Scripts\Activate.ps1

# Reinstall
pip install --force-reinstall package_name
```

## 📈 Roadmap

### Current Status: Core Obfuscation Engine ✅
- [x] Regex pattern detection
- [x] spaCy NER detection
- [x] Transformer detection
- [x] Escrow database
- [x] Text obfuscation/deobfuscation
- [x] Image OCR and obfuscation
- [x] CLI interface

### Next Steps: Desktop Integration
- [ ] Windows clipboard monitoring
- [ ] Chrome extension for browser
- [ ] Native messaging bridge
- [ ] System tray UI
- [ ] Real-time typing detection
- [ ] Configuration UI

### Future Enhancements
- [ ] Additional languages support
- [ ] Custom entity patterns
- [ ] Whitelist/blacklist
- [ ] Learning mode
- [ ] Export/import configurations
- [ ] Integration with other tools

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

This is a hackathon project for HackPrinceton. Contributions welcome!

## 📞 Support

For issues or questions, please open a GitHub issue.

## 🙏 Acknowledgments

- spaCy for fast NER
- Hugging Face for transformer models
- Tesseract OCR for text extraction
- Microsoft Presidio for inspiration