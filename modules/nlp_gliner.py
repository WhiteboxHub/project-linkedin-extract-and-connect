# modules/nlp_gliner.py
"""
GLiNER NER Extractor — Engine 2 of the dual-engine NER pipeline.

Zero-shot entity extraction using `urchade/gliner_base`.
No fine-tuning required — predicts any label you provide at inference time.

Extracts:
  sender_name  — via "person name" / "full name" labels
  company      — via "company name" / "organization" / "employer" labels
  job_title    — via "job title" / "position" / "role" labels
  location     — via "city" / "location" labels
  email        — via "email address" label
  phone        — via "phone number" label

Confidence threshold: 0.6
Focus window: last 500 chars of text (signatures/sign-offs most useful)
Model loaded lazily on first call.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Label definitions
# ---------------------------------------------------------------------------

GLINER_LABELS = [
    "person name",
    "full name",
    "company name",
    "organization",
    "employer",
    "city",
    "location",
    "job title",
    "position",
    "role",
    "email address",
    "phone number",
]

# How each GLiNER label maps to our output field
_LABEL_TO_FIELD = {
    "person name":    "sender_name",
    "full name":      "sender_name",
    "company name":   "company",
    "organization":   "company",
    "employer":       "company",
    "city":           "location",
    "location":       "location",
    "job title":      "job_title",
    "position":       "job_title",
    "role":           "job_title",
    "email address":  "email",
    "phone number":   "phone",
}

CONFIDENCE_THRESHOLD = 0.6
FOCUS_WINDOW_CHARS   = 500   # analyse the last N chars (signatures live here)

# Strict email validator — GLiNER sometimes returns bare domains ("shopify.com")
# A real email address must contain exactly one @.
import re as _re
_VALID_EMAIL_RE = _re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)

# Regex fallbacks: scan FULL text for email/phone when GLiNER misses them
# (GLiNER only sees the last 500 chars)
_EMAIL_FALLBACK_RE = _re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)
_PHONE_FALLBACK_RE = _re.compile(
    r"(?:\+?1[-. ]?)?(?:\(?\d{3}\)?[-. ]?)\d{3}[-. ]?\d{4}(?:[ \t]*(?:ext|x|ext\.)[ \t]*\d{1,6})?"
    r"|(?:\+\d{1,3}[-. ]?)(?:\d[-. ]?){6,14}\d"
)

# Greeting-name detector: "Hi Jessica," -> 'Jessica' is the RECIPIENT, not sender
_GLINER_GREETING_RE = _re.compile(
    r"^(?:Hi|Hello|Hey|Dear|Good morning|Good afternoon)[,!]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*[,!]?\s*$",
    _re.MULTILINE,
)

# Signature location: "City, ST" or "City, Country"
_GLINER_LOCATION_LINE_RE = _re.compile(
    r"^([A-Z][a-zA-Z .]+),\s*([A-Z]{2}|[A-Z][a-zA-Z ]+)$"
)


class GLiNERExtractor:
    """
    Zero-shot NER backed by GLiNER (urchade/gliner_base).

    The model is loaded lazily on first call. If the library or model is
    unavailable, extract() returns an empty dict gracefully.
    """

    def __init__(self) -> None:
        self._model = None  # loaded on first use

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, text: str) -> dict:
        """
        Run GLiNER on `text` and return a dict with fields:
          sender_name, company, job_title, location, email, phone
        Any field not found is None.
        """
        result: dict = {
            "sender_name": None,
            "company":     None,
            "job_title":   None,
            "location":    None,
            "email":       None,
            "phone":       None,
        }

        if not text or not text.strip():
            return result

        # --- Detect greeting recipient so we don't mistake them for the sender ---
        greeting_names: set = set()
        for gm in _GLINER_GREETING_RE.finditer(text):
            greeting_names.add(gm.group(1).lower())

        # Focus on the last FOCUS_WINDOW_CHARS of each message:
        # signatures, sign-offs, and final lines contain most NER-useful content.
        focus_text = text[-FOCUS_WINDOW_CHARS:].strip()
        if not focus_text:
            return result

        try:
            model = self._load_model()
        except Exception as exc:
            logger.warning("[GLINER] Model not available: %s", exc)
            return result

        try:
            raw_preds = model.predict_entities(
                focus_text,
                GLINER_LABELS,
                threshold=CONFIDENCE_THRESHOLD,
            )
        except Exception as exc:
            logger.warning("[GLINER] Prediction error: %s", exc)
            return result

        result = self._parse_entities(raw_preds)

        # --- Suppress greeting name if GLiNER mistook the recipient for sender ---
        if result["sender_name"] and result["sender_name"].lower() in greeting_names:
            result["sender_name"] = None

        # --- Signature-block location overrides body-text location ---
        sig_location = self._extract_signature_location(text)
        if sig_location:
            result["location"] = sig_location

        # --- Regex fallbacks for email and phone ---
        # GLiNER only scans the last 500 chars; regex scans the full text.
        if not result["email"]:
            m = _EMAIL_FALLBACK_RE.search(text)
            if m:
                result["email"] = m.group(0).lower()
        if not result["phone"]:
            for m in _PHONE_FALLBACK_RE.finditer(text):
                raw = m.group(0).strip()
                digits = _re.sub(r"\D", "", raw)
                if len(digits) >= 7:
                    result["phone"] = raw
                    break

        return result

    def _extract_signature_location(self, text: str) -> Optional[str]:
        """Extract signature-block location line bottom-up (City, State/Country)."""
        for line in reversed(text.splitlines()):
            line = line.strip()
            if not line or len(line) > 50 or "@" in line:
                continue
            m = _GLINER_LOCATION_LINE_RE.match(line)
            if m:
                return m.group(1).strip()
        return None

    # ------------------------------------------------------------------
    # Entity parsing
    # ------------------------------------------------------------------

    def _parse_entities(self, raw_preds: list[dict]) -> dict:
        """
        Group predictions by output field and pick the highest-scored
        prediction per field.

        raw_preds format (from GLiNER):
          [{"text": "John Doe", "label": "person name", "score": 0.91}, ...]
        """
        # bucket: field -> list of (score, text)
        buckets: dict[str, list[tuple[float, str]]] = {
            "sender_name": [],
            "company":     [],
            "job_title":   [],
            "location":    [],
            "email":       [],
            "phone":       [],
        }

        for pred in raw_preds:
            label = pred.get("label", "").lower()
            field = _LABEL_TO_FIELD.get(label)
            if field is None:
                continue
            text  = (pred.get("text") or "").strip()
            score = float(pred.get("score", 0.0))
            if text and score >= CONFIDENCE_THRESHOLD:
                buckets[field].append((score, text))

        result: dict = {}
        for field, candidates in buckets.items():
            if candidates:
                # Pick the highest-scored candidate
                best = max(candidates, key=lambda x: x[0])
                value = best[1]
                # --- Email sanity check: must contain '@' ---
                if field == "email" and not _VALID_EMAIL_RE.match(value):
                    value = None
                result[field] = value
            else:
                result[field] = None

        return result

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _load_model(self):
        """Lazy-load urchade/gliner_base on first call."""
        if self._model is None:
            try:
                from gliner import GLiNER
                logger.info("[GLINER] Loading urchade/gliner_base (may download ~500 MB on first run)...")
                self._model = GLiNER.from_pretrained("urchade/gliner_base")
                logger.info("[GLINER] Model loaded")
            except ImportError:
                raise RuntimeError(
                    "GLiNER not installed. Run: pip install gliner"
                )
            except Exception as exc:
                raise RuntimeError(f"GLiNER model load failed: {exc}")
        return self._model
