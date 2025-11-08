# 🏗️ System Architecture

This document explains how all the pieces fit together.

## 📊 High-Level Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                         USER INPUT                             │
│  • Text from keyboard                                          │
│  • Text from file                                              │
│  • Image with text                                             │
└────────────────┬───────────────────────────────────────────────┘
                 │
                 v
┌────────────────────────────────────────────────────────────────┐
│                    DETECTION LAYER                             │
│                                                                │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐      │
│  │   Regex     │  │    spaCy     │  │  Transformer   │      │
│  │  Detector   │  │   Detector   │  │   Detector     │      │
│  │             │  │              │  │  (Optional)    │      │
│  │  ~1-5ms     │  │  ~30-50ms    │  │  ~200-400ms    │      │
│  │             │  │              │  │                │      │
│  │ • Emails    │  │ • Names      │  │ • Context-     │      │
│  │ • Phones    │  │ • Locations  │  │   aware        │      │
│  │ • SSNs      │  │ • Companies  │  │ • Best         │      │
│  │ • Cards     │  │ • Dates      │  │   accuracy     │      │
│  └─────────────┘  └──────────────┘  └─────────────────┘      │
│         │                │                    │                │
│         └────────────────┴────────────────────┘                │
│                          │                                     │
└──────────────────────────┼─────────────────────────────────────┘
                           │
                           v
┌────────────────────────────────────────────────────────────────┐
│                  OBFUSCATION ENGINE                            │
│                                                                │
│  1. Merge detections (remove overlaps)                        │
│  2. Sort by position                                          │
│  3. Generate placeholders                                     │
│  4. Replace in text                                           │
│  5. Store in escrow                                           │
└────────────────┬───────────────────────────────────────────────┘
                 │
                 v
┌────────────────────────────────────────────────────────────────┐
│                    ESCROW DATABASE                             │
│                      (SQLite)                                  │
│                                                                │
│  PERSON_1   → "John Smith"                                    │
│  EMAIL_1    → "john@email.com"                                │
│  PHONE_1    → "555-123-4567"                                  │
│  SSN_1      → "123-45-6789"                                   │
│                                                                │
│  • Salted hashing                                             │
│  • Source tracking                                            │
│  • Timestamp                                                  │
│  • Reversible                                                 │
└────────────────┬───────────────────────────────────────────────┘
                 │
                 v
┌────────────────────────────────────────────────────────────────┐
│                      OUTPUT                                    │
│                                                                │
│  "Contact {PERSON_1} at {EMAIL_1} or {PHONE_1}"              │
│                                                                │
│  Can be deobfuscated back to original:                        │
│  "Contact John Smith at john@email.com or 555-123-4567"      │
└────────────────────────────────────────────────────────────────┘
```

## 🔄 Data Flow: Text Processing

```
TEXT INPUT
    │
    ├─→ Regex Detector
    │   └─→ [EMAIL, PHONE, SSN, CARD, ...]
    │
    ├─→ spaCy Detector  
    │   └─→ [PERSON, LOCATION, ORG, ...]
    │
    └─→ Transformer Detector (optional)
        └─→ [Context-aware entities]
                │
                v
        MERGE & DEDUPLICATE
                │
                v
        FOR EACH DETECTION:
            1. Check escrow for existing placeholder
            2. If not found, generate new placeholder
            3. Store original → placeholder mapping
            4. Replace in text
                │
                v
        OBFUSCATED TEXT
```

## 🖼️ Data Flow: Image Processing

```
IMAGE INPUT
    │
    v
TESSERACT OCR
(Extract text + bounding boxes)
    │
    v
TEXT PROCESSING
(Use standard detection pipeline)
    │
    v
MATCH DETECTIONS TO BOXES
    │
    v
FOR EACH PII REGION:
    ├─→ BLUR (Gaussian)
    ├─→ BLACK (Rectangle)
    └─→ PIXELATE (Downsample)
    │
    v
OBFUSCATED IMAGE
```

## 🗂️ File Organization

```
pii-guard/
│
├── Core Interface Files
│   ├── cli.py                    # Command-line interface
│   ├── quickstart.py             # Setup verification
│   └── verify_installation.py   # Dependency checker
│
├── Documentation
│   ├── README.md                 # Main documentation
│   ├── SETUP_GUIDE.md           # Installation steps
│   ├── GETTING_STARTED.md       # First steps guide
│   ├── CHECKLIST.md             # Setup checklist
│   └── ARCHITECTURE.md          # This file
│
├── src/                         # Core engine
│   ├── obfuscator.py           # Main orchestrator
│   ├── escrow_db.py            # Database layer
│   ├── image_obfuscator.py     # Image processing
│   │
│   └── detectors/              # Detection modules
│       ├── regex_detector.py    # Pattern matching
│       ├── spacy_detector.py    # Named entities
│       └── transformer_detector.py  # ML models
│
├── data/
│   └── escrow/                  # SQLite databases
│
└── tests/
    └── test_data/               # Test files
```

## 🔌 Component Integration

### Regex Detector
**Purpose:** Fast detection of structured patterns  
**Input:** Text string  
**Output:** List of Detection objects  
**Speed:** 1-5ms  
**Used For:** Emails, phones, SSNs, credit cards, URLs, API keys

```python
detector = RegexPatternDetector()
detections = detector.detect(text)
# Returns: [Detection(text="john@email.com", type="EMAIL", ...)]
```

### spaCy Detector
**Purpose:** Named Entity Recognition  
**Input:** Text string  
**Output:** List of Detection objects  
**Speed:** 30-50ms  
**Used For:** Person names, locations, organizations, dates

```python
detector = SpacyDetector(model_name="en_core_web_lg")
detections = detector.detect(text)
# Returns: [Detection(text="John Smith", type="PERSON", ...)]
```

### Transformer Detector
**Purpose:** Context-aware ML detection  
**Input:** Text string  
**Output:** List of Detection objects  
**Speed:** 200-400ms (GPU: 50-100ms)  
**Used For:** Best accuracy, catches edge cases

```python
detector = TransformerDetector(use_gpu=True)
detections = detector.detect(text)
# Returns: [Detection with confidence scores]
```

### Escrow Database
**Purpose:** Store original values for reversal  
**Interface:** store(), retrieve()  
**Storage:** SQLite (local, encrypted)  
**Features:** Salted hashing, deduplication, timestamps

```python
db = EscrowDatabase()
placeholder = db.store("John Smith", "PERSON", "cli")
# Returns: "PERSON_1"

original = db.retrieve("PERSON_1")
# Returns: "John Smith"
```

### Main Obfuscator
**Purpose:** Orchestrate everything  
**Interface:** obfuscate(), deobfuscate()  
**Combines:** All detectors + escrow  
**Features:** Merge overlaps, handle conflicts

```python
obfuscator = PIIObfuscator(
    use_regex=True,
    use_spacy=True,
    use_transformer=False
)

result = obfuscator.obfuscate(text)
# Returns: ObfuscationResult with obfuscated text
```

### Image Obfuscator
**Purpose:** Process images with PII  
**Uses:** Tesseract OCR + Text Obfuscator + OpenCV  
**Methods:** blur, black, pixelate

```python
img_obf = ImagePIIObfuscator(text_obfuscator)
result = img_obf.obfuscate_image(
    "input.png",
    "output.png",
    method='blur'
)
```

## 🎯 Decision Tree: Which Detectors to Use?

```
Need real-time performance?
├─ YES → Use Regex + spaCy only
│        (~30-50ms total)
│
└─ NO → Need best accuracy?
    ├─ YES → Use all three detectors
    │        (~200-400ms total)
    │
    └─ NO → Just patterns?
        └─ YES → Use Regex only
                 (~1-5ms)
```

## 🔐 Security Model

```
┌─────────────────────────────────────────────────────────┐
│                   SECURITY LAYERS                       │
│                                                         │
│  1. Local Processing                                   │
│     ✓ No cloud, no API calls                          │
│     ✓ All data stays on device                        │
│                                                         │
│  2. Encrypted Storage                                  │
│     ✓ SQLite database with encryption                 │
│     ✓ Salted hashes for values                        │
│                                                         │
│  3. Access Control                                     │
│     ✓ File permissions on database                    │
│     ✓ No network access required                      │
│                                                         │
│  4. User Control                                       │
│     ✓ Can delete entries                              │
│     ✓ Can export data                                 │
│     ✓ Can disable detectors                           │
│                                                         │
│  5. Audit Trail                                        │
│     ✓ Timestamps on all entries                       │
│     ✓ Source tracking                                 │
│     ✓ Can review all detections                       │
└─────────────────────────────────────────────────────────┘
```

## 🚀 Performance Characteristics

### Memory Usage
- **Regex Detector:** ~1 MB (compiled patterns)
- **spaCy Small:** ~50 MB (model in memory)
- **spaCy Large:** ~800 MB (model in memory)
- **Transformer:** ~500 MB - 2 GB (depends on model)
- **Escrow DB:** ~1 KB per entry

### Speed
- **Regex:** 1-5ms per text
- **spaCy:** 30-50ms per text
- **Transformer (GPU):** 50-100ms per text
- **Transformer (CPU):** 200-400ms per text
- **OCR:** 1-2 seconds per image

### Accuracy
- **Regex:** High precision, lower recall (only patterns)
- **spaCy:** Good balance, fast
- **Transformer:** Best overall, slower

## 🔗 Future Integration Points

### Windows Clipboard
```
User copies text
    │
    v
Windows Hook
    │
    v
Clipboard Monitor
    │
    v
Obfuscation Engine
    │
    v
Replace Clipboard Content
```

### Chrome Extension
```
User types in browser
    │
    v
Content Script (JS)
    │
    v
Native Messaging
    │
    v
Python Backend
    │
    v
Return Obfuscated Text
    │
    v
Replace in DOM
```

---

This architecture is designed to be:
- ✅ **Modular**: Each component is independent
- ✅ **Testable**: Each module has its own tests
- ✅ **Extensible**: Easy to add new detectors
- ✅ **Fast**: Optimized for real-time use
- ✅ **Secure**: Local-first, no external dependencies