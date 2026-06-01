# Phase 16 — AI and Algorithm Recognition: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 12 AI/algorithm workers — image classification, OCR, NSFW, face detection, speech-to-text, audio language detection, document topic classification, summarization, text language detection, PE metadata parsing, installer detection, and malware heuristics. All local, zero cloud, AI output always suggestions.

**Architecture:** 4 parallel domains (A: image, B: audio, C: document, D: executable) × 3 workers each. Each domain creates a sub-package under `apps/backend/app/workers/`. Models stored in `apps/backend/data/models/` (gitignored). API endpoints added to existing route files. All workers follow the same Request → Process → Suggestion pattern.

**Tech Stack:** Python 3.12, ONNX Runtime, Tesseract OCR, whisper-cpp, fasttext, pefile, scikit-learn (TF-IDF), httpx (model download)

---

## Batch A: Image Recognition (4 tasks)

### Task A1: Image content classifier

**Files:**
- Create: `apps/backend/app/workers/vision/__init__.py`
- Create: `apps/backend/app/workers/vision/classifier.py`
- Create: `apps/backend/tests/test_vision_classifier.py`

- [ ] **Step 1: Create classifier with stub (no model dependency at test time)**

```python
# apps/backend/app/workers/vision/classifier.py
class ImageClassifier:
    """Content classification using ONNX MobileNetV3."""
    
    CATEGORIES = ["anime_manga", "photo", "screenshot", "meme", "document_scan", "chart", "blank_solid"]
    
    def classify(self, image_path: str) -> list[dict]:
        """Returns [{label, confidence}] sorted descending."""
        # Stub: return mock results when model not loaded
        if not self._model_loaded():
            return self._fallback_classify(image_path)
        # Real: run ONNX inference
        ...
    
    def _model_loaded(self) -> bool:
        model_path = Path(settings.data_dir) / "models" / "image_classify.onnx"
        return model_path.exists()
    
    def _fallback_classify(self, image_path: str) -> list[dict]:
        # Heuristic: check exif, dimensions, file extension
        from PIL import Image
        img = Image.open(image_path)
        w, h = img.size
        suggestions = []
        if min(w, h) < 200:
            suggestions.append({"label": "meme", "confidence": 0.6})
        if w == h:
            suggestions.append({"label": "screenshot", "confidence": 0.5})
        suggestions.append({"label": "photo", "confidence": 0.3})
        return sorted(suggestions, key=lambda x: x["confidence"], reverse=True)
```

- [ ] **Step 2: Add API endpoint**

In `apps/backend/app/api/routes/files.py`:

```python
from app.workers.vision.classifier import ImageClassifier

@router.get("/files/{file_id}/classify-image")
def classify_image(file_id: int, db=Depends(get_db)):
    f = files_service.get_file(db, file_id)
    if f.file_type != "image":
        raise BadRequestError("File is not an image")
    result = ImageClassifier().classify(f.path)
    return {"item": {"file_id": file_id, "prediction": result}}
```

- [ ] **Step 3: Run tests, commit**

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/workers/vision/ apps/backend/app/api/routes/files.py apps/backend/tests/test_vision_classifier.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add image content classifier with ONNX MobileNetV3 stub"
```

---

### Task A2: OCR text extraction

**Files:**
- Create: `apps/backend/app/workers/vision/ocr.py`
- Create: `apps/backend/tests/test_vision_ocr.py`

```python
# apps/backend/app/workers/vision/ocr.py
import subprocess

class OcrEngine:
    def extract_text(self, image_path: str, languages: str = "eng+chi_sim") -> dict:
        """Returns {text, language, confidence}."""
        exe = self._tesseract_path()
        if not exe:
            return {"text": None, "error": "Tesseract not found"}
        result = subprocess.run(
            [exe, image_path, "-", "-l", languages, "--psm", "3"],
            capture_output=True, text=True, timeout=30
        )
        text = result.stdout.strip()
        return {"text": text[:5000], "language": languages, "confidence": None}

    def _tesseract_path(self) -> str | None:
        import shutil
        tesseract = shutil.which("tesseract")
        if tesseract:
            return tesseract
        bundled = Path(settings.data_dir) / "models" / "tesseract" / "tesseract.exe"
        return str(bundled) if bundled.exists() else None
```

Add endpoint: `GET /files/{file_id}/ocr`. Commit:

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/workers/vision/ocr.py apps/backend/app/api/routes/files.py apps/backend/tests/test_vision_ocr.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add OCR text extraction with Tesseract"
```

---

### Task A3: NSFW detection

**Files:**
- Create: `apps/backend/app/workers/vision/nsfw.py`

```python
class NsfwDetector:
    def check(self, image_path: str) -> dict:
        """Returns {sfw_score, nsfw_score}."""
        if not self._model_loaded():
            return {"sfw_score": 1.0, "nsfw_score": 0.0, "source": "fallback"}
        # Real: ONNX inference
        ...
    
    def _model_loaded(self) -> bool:
        return Path(settings.data_dir, "models", "nsfw.onnx").exists()
```

Add endpoint: `GET /files/{file_id}/nsfw-check`. Commit:

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/workers/vision/nsfw.py apps/backend/app/api/routes/files.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add NSFW image detection stub"
```

---

### Task A4: Face detection

**Files:**
- Create: `apps/backend/app/workers/vision/face_detect.py`

```python
class FaceDetector:
    def detect(self, image_path: str) -> dict:
        """Returns {face_count, faces: [{x, y, w, h, confidence}]}."""
        if not self._model_loaded():
            return {"face_count": 0, "faces": [], "source": "fallback"}
        # Real: ONNX UltraFace inference
        ...
```

Add endpoint: `GET /files/{file_id}/detect-faces`. Commit:

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/workers/vision/face_detect.py apps/backend/app/api/routes/files.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add face detection with ONNX UltraFace stub"
```

---

## Batch B: Audio Recognition (2 tasks)

### Task B1: Speech-to-text (Whisper)

**Files:**
- Create: `apps/backend/app/workers/audio/__init__.py`
- Create: `apps/backend/app/workers/audio/transcribe.py`

```python
class WhisperTranscriber:
    SUPPORTED_FORMATS = frozenset({".mp3", ".wav", ".m4a", ".ogg", ".flac"})
    
    def transcribe(self, audio_path: str, model_size: str = "base") -> dict:
        """Returns {text, language, segments}."""
        import subprocess
        exe = self._whisper_path()
        if not exe:
            return {"text": None, "error": "Whisper not installed"}
        model = Path(settings.data_dir, "models", f"ggml-{model_size}.bin")
        result = subprocess.run(
            [exe, "-m", str(model), "-f", audio_path, "-l", "auto", "-otxt"],
            capture_output=True, text=True, timeout=300
        )
        return {"text": result.stdout.strip()[:20000], "language": "auto", "model_size": model_size}
    
    def _whisper_path(self) -> str | None:
        import shutil
        return shutil.which("whisper") or shutil.which("whisper-cpp")
```

Add endpoint: `POST /files/{file_id}/transcribe` (async task, returns task_id). Commit:

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/workers/audio/ apps/backend/app/api/routes/files.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add speech-to-text transcription with whisper-cpp"
```

---

### Task B2: Audio language detection

**Files:**
- Create: `apps/backend/app/workers/audio/lang_detect.py`

```python
class AudioLangDetector:
    def detect(self, audio_path: str) -> dict:
        """Uses whisper to detect language from first 30s."""
        # Reuse B1's whisper binary
        transcriber = WhisperTranscriber()
        # Whisper detects language during transcription
        result = transcriber.transcribe(audio_path, model_size="tiny")
        return {"language": result.get("language", "unknown"), "confidence": None}
```

Add endpoint: `GET /files/{file_id}/detect-audio-language`. Commit:

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/workers/audio/lang_detect.py apps/backend/app/api/routes/files.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add audio language detection via Whisper"
```

---

## Batch C: Document Recognition (3 tasks)

### Task C1: Document topic classifier

**Files:**
- Create: `apps/backend/app/workers/nlp/__init__.py`
- Create: `apps/backend/app/workers/nlp/classifier.py`

```python
class DocTopicClassifier:
    TOPICS = ["contract_legal", "thesis_academic", "resume_cv", "manual_guide", "financial_invoice", "fiction_literary", "news_blog", "other"]
    
    def classify(self, text: str) -> list[dict]:
        """Returns [{topic, confidence}] sorted."""
        # TF-IDF + keyword heuristic as fallback (no model needed)
        text_lower = text.lower()
        scores = {t: 0.0 for t in self.TOPICS}
        
        keyword_map = {
            "contract_legal": ["agreement", "party", "hereby", "termination", "clause", "jurisdiction"],
            "thesis_academic": ["abstract", "methodology", "conclusion", "references", "citation"],
            "resume_cv": ["experience", "education", "skills", "linkedin", "university", "degree"],
            "manual_guide": ["click", "select", "button", "menu", "settings", "configure"],
            "financial_invoice": ["invoice", "payment", "due date", "total", "subtotal", "tax"],
            "fiction_literary": ["said", "she", "looked", "felt", "walked", "door", "room"],
            "news_blog": ["published", "reported", "according", "million", "percent", "yesterday"],
        }
        for topic, keywords in keyword_map.items():
            scores[topic] = sum(1 for kw in keywords if kw in text_lower) / len(keywords)
        
        results = [{"topic": t, "confidence": round(s, 3)} for t, s in scores.items() if s > 0]
        return sorted(results, key=lambda x: x["confidence"], reverse=True)
```

Add endpoint: `POST /files/{file_id}/classify-document` (extracts text from PDF/DOCX/EPUB, then classifies). Commit:

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/workers/nlp/ apps/backend/app/api/routes/files.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add document topic classifier with keyword heuristic"
```

---

### Task C2: Document summarization

**Files:**
- Create: `apps/backend/app/workers/nlp/summarizer.py`

```python
import re
from collections import Counter
from math import log

class TextSummarizer:
    def summarize(self, text: str, sentence_count: int = 3) -> dict:
        """Extractive summarization using TF-IDF sentence scoring."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        if len(sentences) <= sentence_count:
            return {"summary": text, "sentence_count": len(sentences)}
        
        # Simple TF-IDF
        words = [re.findall(r"\w+", s.lower()) for s in sentences]
        word_freq = Counter(w for ws in words for w in ws)
        total_docs = len(sentences)
        
        def tfidf(sentence_idx: int) -> float:
            score = 0.0
            for word in set(words[sentence_idx]):
                tf = words[sentence_idx].count(word) / max(len(words[sentence_idx]), 1)
                idf = log(total_docs / (1 + sum(1 for ws in words if word in ws)))
                score += tf * idf
            return score
        
        scored = [(tfidf(i), s) for i, s in enumerate(sentences)]
        scored.sort(key=lambda x: x[0], reverse=True)
        top_sentences = sorted(scored[:sentence_count], key=lambda x: sentences.index(x[1]))
        return {"summary": " ".join(s for _, s in top_sentences), "sentence_count": len(top_sentences)}
```

Add endpoint: `GET /files/{file_id}/summarize`. Commit:

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/workers/nlp/summarizer.py apps/backend/app/api/routes/files.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add extractive text summarization with TF-IDF"
```

---

### Task C3: Document language detection

**Files:**
- Create: `apps/backend/app/workers/nlp/lang_detect.py`

```python
class DocLangDetector:
    # Common stopwords in major languages
    STOPWORDS = {
        "en": {"the", "is", "at", "which", "on", "and", "or", "but", "in", "with", "to", "for", "of", "a", "an"},
        "zh": {"的", "是", "在", "和", "了", "有", "不", "人", "这", "中", "大", "为", "上", "个", "我"},
        "ja": {"の", "に", "は", "を", "た", "が", "で", "て", "と", "し", "れ", "さ", "ある", "いる", "から"},
        "ko": {"이", "가", "는", "에", "의", "로", "을", "다", "고", "서", "한", "은", "그", "하", "있"},
        "fr": {"le", "la", "les", "des", "est", "et", "en", "un", "une", "du", "dans", "pour", "pas", "que"},
        "de": {"der", "die", "das", "ist", "und", "ein", "eine", "in", "zu", "auf", "mit"},
        "es": {"el", "la", "los", "las", "es", "en", "un", "una", "que", "por", "para", "con", "del"},
    }
    
    def detect(self, text: str) -> dict:
        text_lower = text.lower()
        words = set(re.findall(r"\w+", text_lower))
        scores = {}
        for lang, stopwords in self.STOPWORDS.items():
            overlap = words & stopwords
            scores[lang] = len(overlap) / len(stopwords) if stopwords else 0
        best = max(scores, key=scores.get)
        return {"language": best, "confidence": round(scores[best], 3), "scores": scores}
```

Add endpoint: `GET /files/{file_id}/detect-document-language`. Commit:

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/workers/nlp/lang_detect.py apps/backend/app/api/routes/files.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add document language detection with stopword analysis"
```

---

## Batch D: Application Recognition (3 tasks)

### Task D1: PE metadata parser

**Files:**
- Create: `apps/backend/app/workers/executable/__init__.py`
- Create: `apps/backend/app/workers/executable/pe_parser.py`

```python
class PeMetadataParser:
    def parse(self, file_path: str) -> dict:
        try:
            import pefile
            pe = pefile.PE(file_path)
            info = {}
            if hasattr(pe, "FileInfo"):
                for entry in pe.FileInfo:
                    for st in entry.get("StringFileInfo", {}).get("StringTable", []):
                        for k, v in st.entries.items():
                            info[k.decode()] = v.decode() if isinstance(v, bytes) else str(v)
            
            machine_map = {0x14c: "x86", 0x8664: "x64", 0xAA64: "ARM64"}
            machine = machine_map.get(pe.FILE_HEADER.Machine, "unknown")
            ts = pe.FILE_HEADER.TimeDateStamp
            
            return {
                "original_filename": info.get("OriginalFilename"),
                "file_description": info.get("FileDescription"),
                "product_name": info.get("ProductName"),
                "company_name": info.get("CompanyName"),
                "file_version": info.get("FileVersion"),
                "product_version": info.get("ProductVersion"),
                "machine_type": machine,
                "timestamp": ts,
            }
        except ImportError:
            return {"error": "pefile library not installed"}
        except Exception as e:
            return {"error": str(e)}
```

Add endpoint: `GET /files/{file_id}/pe-metadata`. Commit:

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/workers/executable/ apps/backend/app/api/routes/files.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add PE file metadata parser with pefile"
```

---

### Task D2: Installer detector

**Files:**
- Create: `apps/backend/app/workers/executable/installer_detect.py`

```python
class InstallerDetector:
    # Known installer signatures (magic bytes at known offsets)
    SIGNATURES = {
        "NSIS": [b"Nullsoft", b"nsis", b"NullSoftInst"],
        "Inno Setup": [b"Inno", b"innosetup"],
        "WiX": [b"WiX", b"Windows Installer XML"],
        "MSI": [b"\xd0\xcf\x11\xe0"],  # OLE compound document header
        "InstallShield": [b"InstallShield", b"InstallShield\x20"],
    }
    
    def detect(self, file_path: str) -> dict:
        try:
            with open(file_path, "rb") as f:
                header = f.read(8192)
            results = []
            for itype, sigs in self.SIGNATURES.items():
                for sig in sigs:
                    if sig in header:
                        results.append({"installer_type": itype, "confidence": 0.9})
                        break
                    
            # Script installer check
            ext = Path(file_path).suffix.lower()
            if ext in {".bat", ".cmd", ".ps1"}:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read(4096).lower()
                    if any(kw in content for kw in ["setup", "install", "installdir", "program files"]):
                        results.append({"installer_type": "Script", "confidence": 0.7})
                except Exception:
                    pass
            
            return {"items": results or []}
        except Exception as e:
            return {"items": [], "error": str(e)}
```

Add endpoint: `GET /files/{file_id}/detect-installer`. Commit:

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/workers/executable/installer_detect.py apps/backend/app/api/routes/files.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add installer type detection via binary signature scanning"
```

---

### Task D3: Malware heuristic scorer

**Files:**
- Create: `apps/backend/app/workers/executable/malware_heuristic.py`

```python
class MalwareHeuristic:
    SUSPICIOUS_DLLS = {"kernel32.dll", "advapi32.dll", "user32.dll"}
    SUSPICIOUS_APIS = {"CreateRemoteThread", "WriteProcessMemory", "VirtualAllocEx", "LoadLibraryA", "GetProcAddress", "WinExec"}
    PACKER_SIGNS = [b"UPX0", b"UPX1", b"UPX2", b"ASPack", b".aspack", b"Themida"]
    
    def score(self, file_path: str) -> dict:
        risk = 0
        findings = []
        
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            
            # Check for packer signatures
            for sig in self.PACKER_SIGNS:
                if sig in content:
                    risk += 25
                    findings.append(f"Packer detected: {sig.decode('ascii', errors='ignore')}")
                    break
            
            # Check for suspicious API imports
            text = content.decode("ascii", errors="ignore")
            found_apis = [api for api in self.SUSPICIOUS_APIS if api in text]
            if len(found_apis) >= 3:
                risk += 20
                findings.append(f"Suspicious APIs: {', '.join(found_apis[:3])}")
            
            # Double extension check
            name = Path(file_path).name.lower()
            double_ext = re.findall(r"\.\w+\.\w{2,4}$", name)
            if double_ext and double_ext[0].count(".") >= 2:
                risk += 15
                findings.append(f"Double extension: {name}")
            
            risk = min(risk, 100)
            return {"risk_score": risk, "findings": findings, "verdict": "high" if risk > 50 else "medium" if risk > 20 else "low"}
        except Exception as e:
            return {"risk_score": 0, "findings": [], "error": str(e)}
```

Add endpoint: `GET /files/{file_id}/malware-heuristic`. Commit:

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/workers/executable/malware_heuristic.py apps/backend/app/api/routes/files.py
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add malware heuristic risk scoring"
```

---

## Model Download Infrastructure

Create `apps/backend/app/workers/model_manager.py`:

```python
import httpx
from pathlib import Path

class ModelManager:
    MODELS = {
        "image_classify": {"url": "https://huggingface.co/.../mobilenetv3.onnx", "sha256": "..."},
        "nsfw": {"url": "https://huggingface.co/.../nsfw.onnx", "sha256": "..."},
        "face_detect": {"url": "https://huggingface.co/.../ultraface.onnx", "sha256": "..."},
        "whisper_base": {"url": "https://huggingface.co/.../ggml-base.bin", "sha256": "...", "size_mb": 150},
    }
    
    def ensure_model(self, key: str) -> Path | None:
        model_dir = Path(settings.data_dir) / "models"
        model_dir.mkdir(parents=True, exist_ok=True)
        
        model_info = self.MODELS.get(key)
        if not model_info:
            return None
        
        filename = model_info["url"].rsplit("/", 1)[-1]
        local_path = model_dir / filename
        
        if local_path.exists():
            # Verify SHA-256
            if self._verify_sha256(local_path, model_info["sha256"]):
                return local_path
        
        # Download
        self._download(model_info["url"], local_path)
        return local_path if local_path.exists() else None
    
    def _download(self, url: str, dest: Path) -> None:
        with httpx.stream("GET", url, follow_redirects=True, timeout=600) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_bytes(chunk_size=65536):
                    f.write(chunk)
    
    def _verify_sha256(self, path: Path, expected: str) -> bool:
        import hashlib
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest() == expected
```

Update `.gitignore`:

```
# AI/ML model files
apps/backend/data/models/*
!apps/backend/data/models/.gitkeep
```

Commit model manager:

```bash
git -C "T:\Windows\Documents\GitHub\w" add apps/backend/app/workers/model_manager.py .gitignore apps/backend/data/models/.gitkeep
git -C "T:\Windows\Documents\GitHub\w" commit -m "feat: add model download manager with SHA-256 verification"
```

---

## Final Verification

```powershell
# Backend — all tests pass
& "T:\Windows\Documents\GitHub\w\.venv\Scripts\python.exe" -m pytest "T:\Windows\Documents\GitHub\w\apps\backend\tests/" -q --tb=line

# Frontend — all tests pass
Set-Location "T:\Windows\Documents\GitHub\w\apps\frontend"; npx vitest run
```

Expected: All tests pass. New workers can be imported. Stub/fallback paths work when models not loaded.
