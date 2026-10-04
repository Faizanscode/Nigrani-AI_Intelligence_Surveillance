import cv2
import numpy as np
import re
from abc import ABC, abstractmethod
from typing import Optional, List
from .models import OCRResult
from .plate_validator import PlateValidator
from backend.app.core.logger import get_logger
import random
import string

logger = get_logger("OCREngine")

class BaseOCREngine(ABC):
    @abstractmethod
    def read(self, image: np.ndarray, seed: int = None) -> OCRResult:
        pass

class EasyOCREngine(BaseOCREngine):
    """
    Real OCR engine using EasyOCR for reading license plates from image crops.
    Shares a single reader instance across threads and cameras.
    """
    _reader = None

    def __init__(self):
        self.validator = PlateValidator()
        self._init_reader()

    @classmethod
    def _init_reader(cls):
        if cls._reader is None:
            try:
                import easyocr
                logger.info("Initializing EasyOCR reader (CPU mode)...")
                cls._reader = easyocr.Reader(['en'], gpu=False)
                logger.info("EasyOCR reader initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize EasyOCR: {e}")
                cls._reader = None

    def read(self, image: np.ndarray, seed: int = None) -> OCRResult:
        if image is None or image.size == 0:
            return OCRResult(raw_text="", normalized_text="", confidence=0.0)

        if self._reader is None:
            self._init_reader()
            if self._reader is None:
                # Fallback to empty if easyocr failed
                return OCRResult(raw_text="", normalized_text="", confidence=0.0)

        h, w = image.shape[:2]
        if h < 20 or w < 30:
            return OCRResult(raw_text="", normalized_text="", confidence=0.0)

        # ── Preprocess crop for OCR ──────────────────────────────────────────
        # 1. Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # 2. Resize: EasyOCR works best when text height is 30-70 pixels
        if h < 60:
            scale = max(2.0, 70.0 / h)
            resized = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
        else:
            resized = gray

        # 3. Contrast enhancement using CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(resized)

        # 4. Run EasyOCR
        try:
            # Allowlist: uppercase English letters and numbers
            results = self._reader.readtext(enhanced, detail=1, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
            if not results:
                # Try raw image crop as fallback
                results = self._reader.readtext(image, detail=1, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        except Exception as e:
            logger.warning(f"EasyOCR read error: {e}")
            results = []

        if not results:
            return OCRResult(raw_text="", normalized_text="", confidence=0.0)

        # 5. Extract and evaluate candidate texts
        candidates = []
        for item in results:
            _, text, conf = item
            clean = self.validator.normalize(text)
            if len(clean) >= 3:
                status = self.validator.validate(clean)
                # Score higher if matching valid license plate format
                val_score = 2 if status == 'VALID' else (1 if status == 'UNKNOWN' else 0)
                candidates.append((text, clean, conf, val_score))

        # Check multi-line or multi-box plate: e.g. "MP04" and "TB1506"
        if len(results) > 1:
            combined_raw = "".join(item[1] for item in results)
            combined_clean = self.validator.normalize(combined_raw)
            if len(combined_clean) >= 4:
                status = self.validator.validate(combined_clean)
                avg_conf = sum(item[2] for item in results) / len(results)
                val_score = 3 if status == 'VALID' else (1 if status == 'UNKNOWN' else 0)
                candidates.append((combined_raw, combined_clean, avg_conf, val_score))

        if not candidates:
            # Return the highest confidence raw text found
            best = max(results, key=lambda x: x[2])
            clean = self.validator.normalize(best[1])
            return OCRResult(raw_text=best[1], normalized_text=clean, confidence=best[2])

        # Prioritize: format validity first, length (8-10 chars typical for plates), then confidence
        def sort_key(c):
            raw, clean, conf, val_score = c
            len_bonus = 1 if 8 <= len(clean) <= 10 else 0
            return (val_score, len_bonus, conf)

        candidates.sort(key=sort_key, reverse=True)
        best_raw, best_clean, best_conf, _ = candidates[0]

        return OCRResult(
            raw_text=best_raw,
            normalized_text=best_clean,
            confidence=best_conf
        )

class MockOCREngine(BaseOCREngine):
    """
    Simulates OCR. Used as fallback or for unit testing.
    """
    def __init__(self):
        self.validator = PlateValidator()
        self.mock_plates = ["CG04AB1234", "MH12DE1234", "DL01CA1234", "KA51YZ9876", "UP32MN4321"]

    def read(self, image: np.ndarray, seed: int = None) -> OCRResult:
        if seed is None:
            seed = random.randint(0, 1000)
            
        base_plate = self.mock_plates[seed % len(self.mock_plates)]
        chars = list(base_plate)
        conf = random.uniform(0.5, 0.99)
        
        if random.random() < 0.3:
            idx = random.randint(0, len(chars) - 1)
            if chars[idx].isdigit():
                chars[idx] = random.choice("0123456789")
            else:
                chars[idx] = random.choice(string.ascii_uppercase)
                
        raw_text = "".join(chars)
        normalized = self.validator.normalize(raw_text)
        
        return OCRResult(
            raw_text=raw_text,
            normalized_text=normalized,
            confidence=conf
        )

