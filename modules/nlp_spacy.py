# modules/nlp_spacy.py
"""
SpaCy NER Extractor — Engine 1 of the dual-engine NER pipeline.

Extracts:
  sender_name  — PERSON entities + signature regex
  company      — ORG entities (validated) + intro patterns
  job_title    — title patterns from intro text
  location     — GPE / LOC entities

Model: en_core_web_sm (fast, lightweight, no GPU needed)
Loaded lazily on first call.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Common word lists for validation
# ---------------------------------------------------------------------------

# Corporate suffixes — company names ending with these get a confidence bonus
_CORP_SUFFIXES = {
    "inc", "inc.", "llc", "llc.", "ltd", "ltd.", "corp", "corp.",
    "co", "co.", "plc", "plc.", "gmbh", "ag", "sa", "bv", "nv",
    "solutions", "technologies", "technology", "systems", "services",
    "consulting", "group", "partners", "associates", "labs", "lab",
    "studio", "studios", "ventures", "capital", "holdings", "enterprises",
    "software", "digital", "global", "international", "networks", "analytics",
}

# Keywords that indicate a span is a job title, not a company
_TITLE_KEYWORDS = {
    "engineer", "developer", "manager", "director", "president", "vp",
    "vice", "head", "lead", "senior", "junior", "principal", "staff",
    "architect", "analyst", "consultant", "specialist", "coordinator",
    "advisor", "officer", "executive", "ceo", "cto", "cfo", "coo",
    "founder", "co-founder", "partner", "associate", "intern", "fellow",
    "researcher", "scientist", "designer", "recruiter", "hr", "talent",
    "sales", "marketing", "product", "program", "project", "operations",
    "software", "hardware", "data", "full", "front", "back", "cloud",
    "devops", "qa", "quality", "assurance", "support", "customer",
}

# US states and common city-like words that could be mistaken for ORGs
_LOCATION_WORDS = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west virginia", "wisconsin", "wyoming",
    # Common abbreviations
    "ca", "ny", "tx", "fl", "wa", "il", "pa", "oh", "ga", "nc",
    # Other common locations
    "usa", "us", "united states", "india", "uk", "canada", "remote",
    "bay area", "silicon valley", "nyc", "los angeles", "chicago",
    "san francisco", "seattle", "austin", "boston", "atlanta", "denver",
}

# Regex patterns for LinkedIn/email signatures
# IMPORTANT: capture group must stay on a single line — use [^\n]+ not .+
_SIGNATURE_PATTERNS = [
    # "Best regards,\nJohn Doe" — stop capture at first newline
    r"(?:regards|best regards|warm regards|kind regards|sincerely|thanks|thank you|cheers|best)[,\s]*\n+([A-Z][a-zA-Z\-'\.]+(?:\s+[A-Z][a-zA-Z\-'\.]+){0,3})(?:\n|$)",
    # "- John Doe" dash-style
    r"\n[-–]\s*([A-Z][a-zA-Z\-'\.]+(?:\s+[A-Z][a-zA-Z\-'\.]+){0,3})\s*(?:\n|$)",
    # Name immediately before a job-title line
    r"\n([A-Z][a-zA-Z\-'\.]+(?:\s+[A-Z][a-zA-Z\-'\.]+){0,3})\s*\n(?:CEO|CTO|CFO|COO|VP|Director|Manager|Engineer|Developer|Founder|Partner|Lead|Analyst|Consultant|Recruiter|President|Co-Founder|Data Scientist|Scientist|Researcher|Architect)",
    # First capitalised line after a single-word goodbye ("Thanks!\nAlex Kim")
    r"(?:^|\n)(?:Thanks|Cheers|Best|Bye|Ciao|Regards)[!.]*\s*\n([A-Z][a-zA-Z\-'\.]+(?:\s+[A-Z][a-zA-Z\-'\.]+){0,3})(?:\n|$)",
]

# Regex: email addresses (robust)
_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

# Regex: phone numbers — supports international, US, dotted, spaced formats
# Requires at least 7 digits; won't match years or short digit strings
_PHONE_RE = re.compile(
    r"(?:\+?1[-. ]?)?(?:\(?\d{3}\)?[-. ]?)\d{3}[-. ]?\d{4}(?:[ \t]*(?:ext|x|ext\.)[ \t]*\d{1,6})?"
    r"|(?:\+\d{1,3}[-. ]?)(?:\d[-. ]?){6,14}\d"
)

# Regex patterns for "I work at X" style intros
_INTRO_COMPANY_PATTERNS = [
    r"(?:i(?:'m| am)\s+(?:currently\s+)?(?:work(?:ing)?|employed)\s+(?:at|with|for|by))\s+([A-Z][A-Za-z0-9\s&\-\.]+?)(?:\s+(?:as|where|and|in|\.|,)|\s*$)",
    r"(?:i(?:'m| am)\s+(?:a|an)?\s*\w+\s+(?:at|@))\s+([A-Z][A-Za-z0-9\s&\-\.]+?)(?:\s+(?:as|where|and|in|\.|,)|\s*$)",
    r"(?:recently\s+joined|joining|recently\s+moved\s+to)\s+([A-Z][A-Za-z0-9\s&\-\.]+?)(?:\s+(?:as|where|and|in|\.|,)|\s*$)",
    r"(?:from|at)\s+([A-Z][A-Za-z0-9\s&\-\.]+?)(?:\s+(?:looking|seeking|interested|open|\.|,)|\s*$)",
]

# Regex patterns for "as a Senior Engineer" / "currently a Product Manager"
_INTRO_TITLE_PATTERNS = [
    r"(?:i(?:'m| am)\s+(?:a|an)\s+)([A-Z][a-zA-Z\s\-]+?(?:Engineer|Developer|Manager|Director|Designer|Analyst|Consultant|Recruiter|Executive|Officer|Lead|Architect|Scientist|Researcher|Specialist|Coordinator|Advisor|Founder|Partner|Associate))",
    r"(?:working\s+as\s+(?:a|an)\s+)([A-Z][a-zA-Z\s\-]+?(?:Engineer|Developer|Manager|Director|Designer|Analyst|Consultant|Recruiter|Executive|Officer|Lead|Architect|Scientist|Researcher|Specialist|Coordinator|Advisor|Founder|Partner|Associate))",
    r"(?:my\s+(?:current\s+)?(?:role|position|title)\s+is\s+)([A-Z][a-zA-Z\s\-]+)",
]

# Signature-block title patterns: the job title is on its own line directly
# after the name line, before the company / location lines.
# Matches things like:  "Sarah Johnson\nSenior Software Engineer\nGoogle LLC"
_TITLE_SUFFIXES = (
    "Engineer|Developer|Manager|Director|Designer|Analyst|Consultant|"
    "Recruiter|Executive|Officer|Lead|Architect|Scientist|Researcher|"
    "Specialist|Coordinator|Advisor|Founder|Co-Founder|Partner|Associate|"
    "President|VP|Head|Principal|Strategist|Producer|Editor|Writer|"
    "Intern|Fellow|Administrator|Entrepreneur|Owner|Champion|Representative|"
    "Nurse|Doctor|Therapist|Professor|Lecturer|Teacher|Coach|Trainer"
)
_SIGNATURE_TITLE_PATTERNS = [
    # Standalone title line between name and company
    # CRITICAL: use [ -] (space + literal chars) NOT [\s-] to prevent crossing newlines
    rf"(?:^|\n)([A-Z][a-zA-Z &/,\-]+?(?:{_TITLE_SUFFIXES}))(?:[ ]+(?:at|@)[ ]+[A-Z][\w ]+)?(?:\n|$)",
    # "VP of Engineering", "Head of Product" style
    r"(?:^|\n)((?:VP|SVP|EVP|Head|Director|Chief)[ ]+of[ ]+[A-Z][a-zA-Z ]+?)(?:\n|$)",
    # "Co-Founder & CTO" style with & or and
    r"(?:^|\n)((?:Co-)?(?:Founder|Owner|Director|Partner)[ ]+(?:&|and)[ ]+[A-Z]+)(?:\n|$)",
]

# Structural pattern: company is the NON-EMPTY line immediately after a job title
# Used by _extract_company_from_signature for high-precision structural matching
_KNOWN_TITLE_WORDS = (
    "engineer", "developer", "manager", "director", "designer", "analyst",
    "consultant", "recruiter", "executive", "officer", "lead", "architect",
    "scientist", "researcher", "specialist", "coordinator", "advisor",
    "founder", "partner", "associate", "president", "vp", "head", "svp",
    "principal", "strategist", "producer", "editor", "writer", "intern",
    "fellow", "administrator", "entrepreneur", "owner", "ceo", "cto",
    "cfo", "coo", "recruiter", "coach", "trainer", "professor",
)

_SIGNATURE_COMPANY_PATTERN = re.compile(
    r"(?P<title_line>(?:^|\n)(?:[A-Z][a-zA-Z &/,\-]+?(?:{}))(?:\s*(?:at|@)\s+[A-Z][\w\s]+)?(?:\n|$))"
    r"(?P<company_line>(?:^|\n)([A-Z][A-Za-z0-9\s&\-\.]+?)(?:\s+(?:looking|seeking|interested|open|\.|,)|\s*$))".format(
        _TITLE_SUFFIXES
    ),
    re.MULTILINE,
)
_GREETING_NAME_RE = re.compile(
    r"^(?:Hi|Hello|Hey|Dear|Good morning|Good afternoon)[,!]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*[,!]?\s*$",
    re.MULTILINE,
)

# Matches a standalone "City, State" or "City, Country" location line in a signature
_LOCATION_LINE_RE = re.compile(
    r"^([A-Z][a-zA-Z .]+),\s*([A-Z]{2}|[A-Z][a-zA-Z ]+)$"
)

# Closing words that start farewell lines (used to anchor signature block)
_CLOSING_LINE_RE = re.compile(
    r"^(?:best|cheers|regards|thanks|sincerely|warm|yours|kind|ciao|bye|take care)[,!.]?$",
    re.IGNORECASE,
)


class SpacyNERExtractor:
    """
    Entity extractor backed by spaCy's en_core_web_sm model.

    Loaded lazily — the model is not imported until extract() is first called,
    so importing this class is always safe even if spaCy is not installed.
    """

    def __init__(self) -> None:
        self._nlp = None  # loaded on first use

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, text: str) -> dict:
        """
        Run NER on `text` and return a dict with fields:
          sender_name, company, job_title, location, email, phone
        Any field not found is None.
        """
        result: dict = {
            "sender_name": None,
            "company": None,
            "job_title": None,
            "location": None,
            "email": None,
            "phone": None,
        }

        if not text or not text.strip():
            return result

        # --- Detect greeting recipient so we don't mistake it for sender ---
        greeting_names = set()
        for m in _GREETING_NAME_RE.finditer(text):
            greeting_names.add(m.group(1).lower())

        # --- Try signature / intro heuristics first (fast, high precision) ---
        raw_name = self.extract_name_from_signature(text)
        if raw_name and raw_name.lower() not in greeting_names:
            result["sender_name"] = raw_name

        company_from_intro = self.extract_company_from_intro(text)
        if company_from_intro:
            result["company"] = company_from_intro

        title_from_intro = self._extract_title_from_intro(text)
        if title_from_intro:
            result["job_title"] = title_from_intro
        else:
            result["job_title"] = self._extract_title_from_signature(text)

        if not result["company"]:
            result["company"] = self._extract_company_from_signature(text)

        # Signature-block location has highest priority (prevents body-text
        # locations like "United States" from overriding "Bangalore, India")
        result["location"] = self._extract_location_from_signature(text)

        # --- run spaCy NER ---
        try:
            nlp = self._load_model()
        except Exception as exc:
            logger.warning("[SPACY] Model not available: %s", exc)
            return result

        doc = nlp(text[:5000])  # cap at 5000 chars for speed

        names, companies, locations = [], [], []

        for ent in doc.ents:
            t = ent.text.strip()
            if not t or len(t) < 2:
                continue

            if ent.label_ == "PERSON":
                names.append(t)
            elif ent.label_ == "ORG":
                if self._is_valid_company(t) and not self._is_job_title(t) and not self._is_location(t):
                    companies.append(t)
            elif ent.label_ in ("GPE", "LOC"):
                locations.append(t)

        # Fill in from NER only where heuristics didn't find anything
        if not result["sender_name"] and names:
            # Filter out any name that appeared in a greeting line
            for n in names:
                if n.lower() not in greeting_names:
                    result["sender_name"] = n
                    break
        if not result["company"] and companies:
            result["company"] = companies[0]
        # Location: signature-block result wins; fall back to first spaCy location
        if not result["location"] and locations:
            result["location"] = locations[0]

        # Regex-based email and phone (en_core_web_sm doesn't handle these)
        result["email"] = self.extract_email(text)
        result["phone"] = self.extract_phone(text)

        return result

    def extract_name_from_signature(self, text: str) -> Optional[str]:
        """
        Extract a person's name from common email/message signature patterns:
        "Regards,\nJohn Doe", "- John Doe", "Thanks,\n Jane Smith"
        """
        for pattern in _SIGNATURE_PATTERNS:
            m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if m:
                # Take only the first line of the capture group (newline guard)
                name = m.group(1).split("\n")[0].split("\r")[0].strip()
                # Basic sanity: 2-50 chars, not all caps (that's usually a company)
                if 2 <= len(name) <= 50 and not name.isupper():
                    return name
        return None

    def extract_email(self, text: str) -> Optional[str]:
        """Extract the first email address found in text using regex."""
        m = _EMAIL_RE.search(text)
        return m.group(0).lower() if m else None

    def extract_phone(self, text: str) -> Optional[str]:
        """
        Extract the first phone-like sequence found in text.
        Filters out short pure-digit matches (e.g. years like '2024').
        """
        for m in _PHONE_RE.finditer(text):
            raw = m.group(0).strip()
            digits = re.sub(r"\D", "", raw)
            if len(digits) >= 7:  # must have at least 7 digits to be a phone
                return raw
        return None

    def _extract_title_from_signature(self, text: str) -> Optional[str]:
        """
        Extract job title from a signature block where the title sits on
        its own line, e.g.:
          Sarah Johnson
          Senior Software Engineer        <-- we want this
          Google LLC
        """
        for pattern in _SIGNATURE_TITLE_PATTERNS:
            m = re.search(pattern, text, re.MULTILINE)
            if m:
                title = m.group(1).strip().rstrip(".,;:")
                if 3 <= len(title) <= 80:
                    return title
        return None

    def _extract_company_from_signature(self, text: str) -> Optional[str]:
        """
        Structural company extractor: walks through the signature lines and
        finds the company name on the line right after the job title.

        Signature structure (each field on its own line):
          [Closing phrase]
          [Name]
          [Job Title]     <-- we find this with _KNOWN_TITLE_WORDS
          [Company]       <-- we want THIS line
          [Location]
          [Email] | [Phone]
        """
        lines = [l.strip() for l in text.splitlines()]
        lines = [l for l in lines if len(l) >= 2]

        for i, line in enumerate(lines):
            lower = line.lower()

            # --- GUARD: skip paragraph/body-text lines ---
            # Signature title lines are SHORT (1-6 words) and don't start
            # with pronouns or common sentence openers
            if len(line.split()) > 8:
                continue   # too many words — body sentence, not a title line
            if _CLOSING_LINE_RE.match(line):
                continue   # skip "Cheers," "Best," etc.
            if re.match(r"^(?:I|We|Our|My|Hi|Hello|Dear|Thanks|Thank|Please|Also|As|With|For|Note)\b", line, re.IGNORECASE):
                continue   # starts like a sentence

            # Check if this line looks like a job title
            has_title_word = any(tw in lower for tw in _KNOWN_TITLE_WORDS)
            is_vp_head = re.match(r"(?:VP|Head|SVP|EVP|Chief|Director)\s+of\b", line)
            if not (has_title_word or is_vp_head):
                continue

            # The NEXT non-empty line should be the company
            if i + 1 >= len(lines):
                break
            candidate = lines[i + 1].strip()

            # Reject candidates that look like emails, phones, locations, or
            # are too long (sentence fragments) or contain @
            if "@" in candidate:
                continue
            if re.match(r"[\d\+\(\)]", candidate):
                continue      # starts with digit / phone char
            if len(candidate.split()) > 6:
                continue       # too many words for a company name
            if len(candidate) < 2 or len(candidate) > 60:
                continue
            if "\n" in candidate or self._is_location(candidate):
                continue
            if self._is_job_title(candidate):
                continue
            if re.match(r"^[a-z]", candidate):
                continue       # company names start with uppercase

            if self._is_valid_company(candidate):
                return candidate

        return None

    def _extract_location_from_signature(self, text: str) -> Optional[str]:
        """
        Find a signature-style location line: 'City, ST' or 'City, Country'.
        We walk from the BOTTOM of the text upward so we anchor to the
        signature block, not locations in the message body.
        """
        lines = [l.strip() for l in text.splitlines()]
        # Walk from the bottom
        for line in reversed(lines):
            if not line or len(line) > 50:
                continue
            m = _LOCATION_LINE_RE.match(line)
            if m:
                # Exclude obvious non-locations (email, phone, company names)
                if "@" in line or re.match(r"[\d\+\(]", line):
                    continue
                return m.group(1).strip()   # return just the city
        return None

    def extract_company_from_intro(self, text: str) -> Optional[str]:
        """
        Extract company name from intros like:
        "I work at Acme Corp", "recently joined Google", "from Microsoft"
        """
        for pattern in _INTRO_COMPANY_PATTERNS:
            m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if m:
                company = m.group(1).strip().rstrip(".,;:")
                if self._is_valid_company(company):
                    return company
        return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_title_from_intro(self, text: str) -> Optional[str]:
        for pattern in _INTRO_TITLE_PATTERNS:
            m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if m:
                title = m.group(1).strip().rstrip(".,;:")
                if 3 <= len(title) <= 80:
                    return title
        return None

    def _is_job_title(self, text: str) -> bool:
        """Return True if the text looks like a job title rather than a company."""
        lower = text.lower()
        words = re.split(r"[\s,\-/]+", lower)
        meaningful = [w for w in words if len(w) > 1 and w not in ("of", "the", "a", "an", "and")]
        matches = [w for w in meaningful if w in _TITLE_KEYWORDS]
        if not meaningful:
            return False
        ratio = len(matches) / len(meaningful)
        # Title if ≥40% of meaningful words are title words, OR
        # starts with a standalone title abbreviation (VP, CEO, CTO, etc.)
        return ratio >= 0.4 or (len(meaningful) >= 1 and meaningful[0] in _TITLE_KEYWORDS)

    def _is_location(self, text: str) -> bool:
        """Return True if the text looks like a geographic location."""
        lower = text.lower().strip()
        if lower in _LOCATION_WORDS:
            return True
        # Multi-word: "San Francisco, CA"
        parts = re.split(r"[,\s]+", lower)
        return all(p in _LOCATION_WORDS or len(p) <= 2 for p in parts if p)

    def _is_valid_company(self, text: str) -> bool:
        """
        Return True if text plausibly looks like a company name.

        Rejection rules:
        - Longer than 50 chars (likely a sentence fragment)
        - Starts with a lowercase letter
        - Contains HTML tags
        - Looks like a timestamp (12:30, 1/2)
        - Pure digits or punctuation
        - Contains a newline (sentence boundary)
        - More than 7 words (too long to be a company name)
        - Matches job title keywords
        - Matches known city/state names
        """
        t = text.strip()
        if not t or len(t) < 2:
            return False
        # Too long (was 80, tightened to 50)
        if len(t) > 50:
            return False
        # Must start with uppercase
        if re.match(r"^[a-z]", t):
            return False
        # HTML tags
        if re.search(r"<[^>]+>", t):
            return False
        # Timestamp / date
        if re.search(r"\d{1,2}[:/]\d{2}", t):
            return False
        # Pure digits / punctuation
        if re.match(r"^[\d\s\-\.\,]+$", t):
            return False
        # Sentence boundary in text
        if "\n" in t:
            return False
        # Too many words
        if len(t.split()) > 7:
            return False
        # Reject if it IS a job title
        if self._is_job_title(t):
            return False
        # Reject if it IS a location
        if self._is_location(t):
            return False
        return True

    def _has_corp_suffix(self, text: str) -> bool:
        """
        Return True if the text ends with a corporate suffix, giving it a
        confidence bonus (use to prefer 'Acme Corp' over 'Acme' when both
        are found).
        """
        last_word = text.strip().rstrip(".").split()[-1].lower() if text.strip() else ""
        return last_word in _CORP_SUFFIXES

    def _score_company(self, text: str) -> int:
        """
        Return a score for a company candidate.
        Higher is more confident.
          0  — valid but no special signals
          1  — ends with a recognised corporate suffix (Inc, LLC, Corp, etc.)
         -1  — fails validation
        """
        if not self._is_valid_company(text):
            return -1
        return 1 if self._has_corp_suffix(text) else 0

    def _best_name(self, names: list[str]) -> Optional[str]:
        """Pick the most plausible name from a list of PERSON entities."""
        # Prefer names with a space (First Last), sort by that
        multi = [n for n in names if " " in n and len(n) <= 50]
        if multi:
            return multi[0]
        single = [n for n in names if len(n) >= 3 and not n.isupper()]
        return single[0] if single else None

    def _load_model(self):
        """Lazy-load spaCy en_core_web_sm on first call."""
        if self._nlp is None:
            try:
                import spacy
                self._nlp = spacy.load("en_core_web_sm")
                logger.info("[SPACY] Loaded en_core_web_sm")
            except OSError:
                raise RuntimeError(
                    "spaCy model not found. Run: python -m spacy download en_core_web_sm"
                )
            except ImportError:
                raise RuntimeError(
                    "spaCy not installed. Run: pip install spacy"
                )
        return self._nlp
