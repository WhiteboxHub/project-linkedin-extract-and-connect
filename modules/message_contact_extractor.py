# # modules/message_contact_extractor.py
# """
# MessageContactExtractor — NER orchestrator (Phase 2b)

# Reads a raw conversation dict (produced by InboxScraper Phase 1) and
# extracts a rich contact record using a field-level fallback chain:

#     sender_name  : linkedin_profile → gliner → spacy
#     company      : linkedin_profile → gliner → spacy
#     job_title    : linkedin_profile → gliner → spacy
#     location     : linkedin_profile → gliner → spacy
#     email        : regex  (from OfflineExtractor)
#     phone        : regex  (from OfflineExtractor)

# Output dict matches the OfflineExtractor contact schema so both pipelines
# can be merged or used interchangeably.

# Usage
# -----
#     from modules.message_contact_extractor import MessageContactExtractor

#     mce = MessageContactExtractor()

#     # single conversation
#     contact = mce.extract(conv_dict)

#     # batch
#     contacts = mce.extract_batch(list_of_conv_dicts)
# """

# from __future__ import annotations

# import logging
# import re
# from datetime import datetime
# from typing import Any, Optional

# logger = logging.getLogger(__name__)

# # ---------------------------------------------------------------------------
# # Lazy engine imports — engines are only instantiated on first use
# # ---------------------------------------------------------------------------

# _spacy_engine = None
# _gliner_engine = None


# def _get_spacy():
#     global _spacy_engine
#     if _spacy_engine is None:
#         from modules.nlp_spacy import SpacyNERExtractor
#         _spacy_engine = SpacyNERExtractor()
#     return _spacy_engine


# def _get_gliner():
#     global _gliner_engine
#     if _gliner_engine is None:
#         from modules.nlp_gliner import GLiNERExtractor
#         _gliner_engine = GLiNERExtractor()
#     return _gliner_engine


# # ---------------------------------------------------------------------------
# # Regex patterns (user-specified)
# # ---------------------------------------------------------------------------

# # Email — specified pattern
# _EMAIL_RE = re.compile(
#     r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
#     re.IGNORECASE,
# )

# # Phone — broad match (10-15 significant chars), normalised to E.164 on output
# _PHONE_RE = re.compile(
#     r"\+?[\d\s\-\(\)]{10,15}"
# )

# # LinkedIn profile URL — captures the slug (e.g. 'johndoe' from /in/johndoe)
# _LINKEDIN_URL_RE = re.compile(
#     r"linkedin\.com/in/([a-zA-Z0-9\-]+)",
#     re.IGNORECASE,
# )

# _PERSONAL_DOMAINS = {
#     "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.uk", "ymail.com",
#     "hotmail.com", "outlook.com", "live.com", "icloud.com", "me.com",
#     "aol.com", "protonmail.com", "proton.me", "mail.com", "zoho.com",
#     "fastmail.com", "hey.com", "inbox.com", "msn.com",
# }

# _IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".ico"}


# def _regex_emails(text: str, exclude_personal: bool = True) -> list[str]:
#     """Return unique, validated email addresses from text."""
#     seen: set[str] = set()
#     results: list[str] = []
#     for m in _EMAIL_RE.findall(text):
#         email = m.lower()
#         if email in seen:
#             continue
#         seen.add(email)
#         # Reject image file false-positives (e.g. icon@bar.com.png)
#         if any(email.endswith(ext) for ext in _IMAGE_EXTS):
#             continue
#         domain = email.split("@", 1)[1]
#         if exclude_personal and domain in _PERSONAL_DOMAINS:
#             continue
#         results.append(email)
#     return results


# def _to_e164(digits: str) -> str:
#     """
#     Convert a 10-digit US number to E.164 format (+1XXXXXXXXXX).
#     If already 11 digits starting with 1, just prepend +.
#     """
#     if len(digits) == 10:
#         return f"+1{digits}"
#     if len(digits) == 11 and digits[0] == "1":
#         return f"+{digits}"
#     return f"+{digits}"   # international — best-effort


# def _normalize_phone(raw: str) -> str | None:
#     """
#     Extract only the digit characters from a broad phone match and return the
#     number in E.164 format. Returns None if the digit count is out of range.
#     """
#     digits = re.sub(r"\D", "", raw)
#     # US: strip leading country code for dedup, keep 10 core digits
#     core = digits[1:] if (len(digits) == 11 and digits[0] == "1") else digits
#     if len(core) != 10:
#         return None   # too short or too long to be a real US number
#     return _to_e164(core)


# def _regex_phones(text: str) -> list[str]:
#     """Return unique phone numbers in E.164 format found in text."""
#     seen: set[str] = set()
#     results: list[str] = []
#     for m in _PHONE_RE.findall(text):
#         m = m.strip()
#         normalized = _normalize_phone(m)
#         if normalized is None:
#             continue
#         if normalized in seen:
#             continue
#         seen.add(normalized)
#         results.append(normalized)   # always return E.164
#     return results


# def _regex_linkedin_urls(text: str) -> list[str]:
#     """
#     Extract LinkedIn profile slugs from any linkedin.com/in/<slug> URLs
#     found in the message text. Returns full canonical URLs.
#     e.g. 'linkedin.com/in/johndoe' -> 'https://www.linkedin.com/in/johndoe'
#     """
#     results = []
#     seen: set[str] = set()
#     for slug in _LINKEDIN_URL_RE.findall(text):
#         slug = slug.lower()
#         if slug in seen:
#             continue
#         seen.add(slug)
#         results.append(f"https://www.linkedin.com/in/{slug}")
#     return results


# # ---------------------------------------------------------------------------
# # Main class
# # ---------------------------------------------------------------------------

# class MessageContactExtractor:
#     """
#     Orchestrates SpaCy + GLiNER NER engines with a field-level fallback chain
#     to extract contact info from LinkedIn inbox conversation dicts.

#     Parameters
#     ----------
#     use_gliner : bool
#         Whether to use the GLiNER engine (default True). Set to False to
#         skip downloading the ~500 MB model during development/testing.
#     use_spacy : bool
#         Whether to use the SpaCy engine (default True).
#     exclude_personal_emails : bool
#         Whether to filter out gmail/yahoo/etc addresses (default True).
#     """

#     FALLBACK_CHAIN = {
#         # sender_name: LinkedIn profile > message UI display name > GLiNER > spaCy > signature regex
#         "sender_name": ["linkedin_profile", "metadata", "gliner", "spacy", "signature"],
#         # company: LinkedIn profile > GLiNER org/employer > spaCy ORG > body intro pattern
#         "company":     ["linkedin_profile", "gliner", "spacy", "intro_pattern"],
#         "job_title":   ["linkedin_profile", "gliner", "spacy"],
#         "location":    ["linkedin_profile", "gliner", "spacy"],
#         "email":       ["regex"],
#         "phone":       ["regex"],
#     }

#     def __init__(
#         self,
#         use_gliner: bool = True,
#         use_spacy: bool = True,
#         exclude_personal_emails: bool = True,
#     ) -> None:
#         self.use_gliner = use_gliner
#         self.use_spacy  = use_spacy
#         self.exclude_personal_emails = exclude_personal_emails

#     # ------------------------------------------------------------------
#     # Public entry points
#     # ------------------------------------------------------------------

#     def extract(self, conversation: dict[str, Any]) -> dict[str, Any]:
#         """
#         Extract a contact record from a raw conversation dict.

#         The input should be a dict as produced by InboxScraper:
#           {
#             "conversation_id": "2-abc",
#             "participant_name": "John Doe",
#             "participant_profile_url": "https://linkedin.com/in/johndoe",
#             "messages": [{"sender_name": ..., "text": ..., "timestamp": ...}],
#             "extraction_date": "2026-02-23",
#             "candidate_id": 101,
#             "candidate_email": "me@example.com",
#           }

#         Returns a contact dict with keys:
#           sender_name, company, job_title, location, email, phone,
#           linkedin_id, conversation_url, source, extraction_date,
#           conversation_id, candidate_id, candidate_email
#         """
#         conv_id        = conversation.get("conversation_id", "unknown")
#         participant    = conversation.get("participant_name") or ""
#         profile_url    = conversation.get("participant_profile_url") or ""
#         messages       = conversation.get("messages", [])
#         candidate_id   = conversation.get("candidate_id")
#         candidate_email= conversation.get("candidate_email", "")

#         # Combine all message texts
#         combined_text = "\n".join(
#             m.get("text", "") for m in messages if m.get("text")
#         )

#         # Gather sources
#         linkedin_data  = self._from_linkedin_profile(participant, profile_url)
#         metadata_data  = self._from_metadata(messages)
#         regex_data     = self._from_regex(combined_text)
#         gliner_data    = {}
#         spacy_data     = {}
#         signature_data = {}
#         intro_data     = {}

#         if combined_text.strip():
#             if self.use_gliner:
#                 try:
#                     gliner_data = _get_gliner().extract(combined_text)
#                 except Exception as exc:
#                     logger.warning("[MCE] GLiNER failed for conv %s: %s", conv_id, exc)

#             if self.use_spacy:
#                 try:
#                     spacy_data = _get_spacy().extract(combined_text)
#                 except Exception as exc:
#                     logger.warning("[MCE] SpaCy failed for conv %s: %s", conv_id, exc)

#                 try:
#                     sig_name = _get_spacy().extract_name_from_signature(combined_text)
#                     if sig_name:
#                         signature_data = {"sender_name": sig_name}
#                 except Exception as exc:
#                     logger.warning("[MCE] SpaCy signature failed for conv %s: %s", conv_id, exc)

#                 try:
#                     intro_company = _get_spacy().extract_company_from_intro(combined_text)
#                     if intro_company:
#                         intro_data = {"company": intro_company}
#                 except Exception as exc:
#                     logger.warning("[MCE] SpaCy intro failed for conv %s: %s", conv_id, exc)

#         source_map = {
#             "linkedin_profile": linkedin_data,
#             "metadata":         metadata_data,
#             "gliner":           gliner_data,
#             "spacy":            spacy_data,
#             "signature":        signature_data,
#             "intro_pattern":    intro_data,
#             "regex":            regex_data,
#         }

#         # Apply fallback chain per field
#         contact: dict[str, Any] = {}
#         for field, chain in self.FALLBACK_CHAIN.items():
#             contact[field] = None
#             for source_name in chain:
#                 value = source_map.get(source_name, {}).get(field)
#                 if value:
#                     contact[field] = value
#                     logger.debug("[MCE] conv %s  %-12s <- %s: %r", conv_id, field, source_name, value)
#                     break

#         # Metadata
#         contact["linkedin_id"]       = profile_url
#         contact["conversation_url"]  = (
#             f"https://www.linkedin.com/messaging/thread/{conv_id}/"
#             if conv_id != "unknown" else ""
#         )
#         contact["source"]            = "inbox_ner"
#         contact["extraction_date"]   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         contact["conversation_id"]   = conv_id
#         contact["candidate_id"]      = candidate_id
#         contact["candidate_email"]   = candidate_email

#         return contact

#     def extract_batch(
#         self, conversations: list[dict[str, Any]]
#     ) -> list[dict[str, Any]]:
#         """
#         Process a list of conversation dicts and return a list of contact dicts.
#         Conversations with no extractable data (no name, no email, no phone)
#         are still included but with None values for missing fields.
#         """
#         results = []
#         total = len(conversations)
#         for i, conv in enumerate(conversations, start=1):
#             try:
#                 contact = self.extract(conv)
#                 results.append(contact)
#                 logger.debug("[MCE] Processed %d/%d: %s", i, total, conv.get("conversation_id"))
#             except Exception as exc:
#                 logger.error(
#                     "[MCE] Error processing conv %s: %s",
#                     conv.get("conversation_id", "?"), exc,
#                     exc_info=True,
#                 )
#         logger.info("[MCE] Batch complete: %d/%d conversations processed", len(results), total)
#         return results

#     # ------------------------------------------------------------------
#     # Source extractors
#     # ------------------------------------------------------------------

#     def _from_linkedin_profile(self, participant_name: str, profile_url: str) -> dict:
#         """
#         Highest-confidence source: data scraped directly from the LinkedIn
#         profile in the conversation sidebar.
#         participant_name  → sender_name
#         (company/title/location from the profile are not yet scraped in Phase 1;
#         they can be added here when Phase 1 is extended)
#         """
#         data: dict = {}
#         if participant_name and participant_name.strip():
#             data["sender_name"] = participant_name.strip()
#         return data

#     def _from_metadata(self, messages: list[dict]) -> dict:
#         """
#         Second-priority source: the display name shown in the message thread UI.
#         InboxScraper stores this as `sender_name` on each message object.
#         We pick the first non-'Me' sender name we see.
#         """
#         data: dict = {}
#         for msg in messages:
#             name = (msg.get("sender_name") or "").strip()
#             if name and name.lower() not in ("me", "you", ""):
#                 data["sender_name"] = name
#                 break
#         return data

#     def _from_regex(self, text: str) -> dict:
#         """
#         High-precision regex extraction for email, phone (E.164), and
#         LinkedIn profile URLs embedded in message text.
#         """
#         data: dict = {}

#         emails = _regex_emails(text, self.exclude_personal_emails)
#         if emails:
#             data["email"] = emails[0]

#         phones = _regex_phones(text)  # already normalised to E.164
#         if phones:
#             data["phone"] = phones[0]

#         # LinkedIn URLs shared in message body (e.g. 'Check my profile at linkedin.com/in/johndoe')
#         li_urls = _regex_linkedin_urls(text)
#         if li_urls:
#             data["linkedin_id"] = li_urls[0]

#         return data



#updated one
# modules/message_contact_extractor.py
"""
MessageContactExtractor — NER orchestrator (Phase 2b)

Reads a raw conversation dict (produced by InboxScraper Phase 1) and
extracts a rich contact record using a field-level fallback chain:
    sender_name  : linkedin_profile → gliner → spacy
    company      : linkedin_profile → gliner → spacy
    job_title    : linkedin_profile → gliner → spacy
    location     : linkedin_profile → gliner → spacy
    email        : regex  (from OfflineExtractor)
    phone        : regex  (from OfflineExtractor)

Output dict matches both table schemas:
- automation_contact_extracts
- raw_job_listings

Usage
-----
    from modules.message_contact_extractor import MessageContactExtractor

    mce = MessageContactExtractor()
    # single conversation
    contact = mce.extract(conv_dict)
    # batch
    contacts = mce.extract_batch(list_of_conv_dicts)
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Optional, Dict, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy engine imports — engines are only instantiated on first use
# ---------------------------------------------------------------------------

_spacy_engine = None
_gliner_engine = None


def _get_spacy():
    global _spacy_engine
    if _spacy_engine is None:
        from modules.nlp_spacy import SpacyNERExtractor
        _spacy_engine = SpacyNERExtractor()
    return _spacy_engine


def _get_gliner():
    global _gliner_engine
    if _gliner_engine is None:
        from modules.nlp_gliner import GLiNERExtractor
        _gliner_engine = GLiNERExtractor()
    return _gliner_engine


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Email — specified pattern
_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

# Phone — broad match (10-15 significant chars), normalised to E.164 on output
_PHONE_RE = re.compile(
    r"\+?[\d\s\-\(\)]{10,15}"
)

# LinkedIn profile URL — captures the slug
_LINKEDIN_URL_RE = re.compile(
    r"linkedin\.com/in/([a-zA-Z0-9\-]+)",
    re.IGNORECASE,
)

# LinkedIn Internal ID (ACoAA...)
_LINKEDIN_INTERNAL_ID_RE = re.compile(
    r"linkedin\.com/in/([A-Za-z0-9_-]{20,})",
    re.IGNORECASE,
)

_PERSONAL_DOMAINS = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.uk", "ymail.com",
    "hotmail.com", "outlook.com", "live.com", "icloud.com", "me.com",
    "aol.com", "protonmail.com", "proton.me", "mail.com", "zoho.com",
    "fastmail.com", "hey.com", "inbox.com", "msn.com",
}

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".ico"}

# ---------------------------------------------------------------------------
# Name Extraction Fallback
# ---------------------------------------------------------------------------

_GENERIC_EMAIL_PREFIXES = {
    "info", "contact", "admin", "recruiter", "hr", "careers", 
    "support", "sales", "hello", "team", "marketing", "jobs",
    "noreply", "no-reply", "recruitment", "talent", "staff"
}

def _extract_name_from_email(email: Optional[str]) -> Optional[str]:
    """
    Attempt to extract a human name from an email prefix.
    Rejects generic prefixes like 'hr' or 'recruiter'.
    Handles dot or underscore separation (e.g. 'john.doe' -> 'John Doe').
    """
    if not email or "@" not in email:
        return None
        
    prefix = email.split("@")[0].lower()
    
    # Strip trailing numbers (e.g. 'johndoe123' -> 'johndoe')
    prefix = re.sub(r'\d+$', '', prefix)
    
    if prefix in _GENERIC_EMAIL_PREFIXES:
        return None
        
    # Handle explicit separators
    if "." in prefix:
        parts = prefix.split(".")
        return " ".join(p.capitalize() for p in parts if p)
    elif "_" in prefix:
        parts = prefix.split("_")
        return " ".join(p.capitalize() for p in parts if p)
        
    # If it's a single word (e.g. 'dave'), just capitalize it
    if len(prefix) >= 2:
        return prefix.capitalize()
    
    return None

# ---------------------------------------------------------------------------
# Location Parsing
# ---------------------------------------------------------------------------

_US_STATES = {
    "al": "alabama", "ak": "alaska", "az": "arizona", "ar": "arkansas",
    "ca": "california", "co": "colorado", "ct": "connecticut", "de": "delaware",
    "fl": "florida", "ga": "georgia", "hi": "hawaii", "id": "idaho",
    "il": "illinois", "in": "indiana", "ia": "iowa", "ks": "kansas",
    "ky": "kentucky", "la": "louisiana", "me": "maine", "md": "maryland",
    "ma": "massachusetts", "mi": "michigan", "mn": "minnesota", "ms": "mississippi",
    "mo": "missouri", "mt": "montana", "ne": "nebraska", "nv": "nevada",
    "nh": "new hampshire", "nj": "new jersey", "nm": "new mexico", "ny": "new york",
    "nc": "north carolina", "nd": "north dakota", "oh": "ohio", "ok": "oklahoma",
    "or": "oregon", "pa": "pennsylvania", "ri": "rhode island", "sc": "south carolina",
    "sd": "south dakota", "tn": "tennessee", "tx": "texas", "ut": "utah",
    "vt": "vermont", "va": "virginia", "wa": "washington", "wv": "west virginia",
    "wi": "wisconsin", "wy": "wyoming", "dc": "washington dc"
}

_COUNTRY_MAP = {
    "us": "united states", "usa": "united states", "uk": "united kingdom",
    "uae": "united arab emirates", "in": "india", "ca": "canada",
    "au": "australia", "de": "germany", "fr": "france", "jp": "japan",
    "sg": "singapore", "nl": "netherlands"
}


def parse_location(location_str: str) -> Dict[str, Optional[str]]:
    """
    Parse location string into components.
    Example: "San Francisco, CA 94105, US" -> city=San Francisco, state=CA, country=US, postal_code=94105
    """
    result = {
        "city": None,
        "state": None,
        "country": None,
        "postal_code": None
    }
    
    if not location_str:
        return result
    
    # Clean the string
    location_str = location_str.strip()
    
    # Extract postal code (5 digits, possibly with extension)
    zip_match = re.search(r'\b(\d{5}(?:-\d{4})?)\b', location_str)
    if zip_match:
        result["postal_code"] = zip_match.group(1)
        location_str = location_str.replace(zip_match.group(0), "").strip()
    
    # Split by comma
    parts = [p.strip() for p in location_str.split(",")]
    
    if len(parts) >= 1:
        # First part is usually city
        if parts[0]:
            result["city"] = parts[0]
    
    if len(parts) >= 2:
        second = parts[1].strip().upper()
        # Check if it's a US state abbreviation
        if second.lower() in _US_STATES:
            result["state"] = second
        elif second in _US_STATES.values():
            result["state"] = second.upper()
        # Check if it's a country
        elif second.lower() in _COUNTRY_MAP:
            result["country"] = _COUNTRY_MAP[second.lower()]
        else:
            result["state"] = second
    
    if len(parts) >= 3:
        third = parts[2].strip()
        if third.lower() in _COUNTRY_MAP:
            result["country"] = _COUNTRY_MAP[third.lower()]
        else:
            result["country"] = third
    
    # Handle "Remote" case
    if location_str.lower() in ["remote", "work from home", "wfh", "remote - us", "remote (us)"]:
        result["city"] = "Remote"
        result["country"] = "US"
    
    return result


# ---------------------------------------------------------------------------
# Contact Classification
# ---------------------------------------------------------------------------

def classify_contact(email: str, linkedin_id: str) -> str:
    """
    Classify contact type.
    Returns: company_contact, personal_domain_contact, linkedin_only_contact, unknown
    """
    if email:
        domain = email.split("@")[1].lower()
        personal_domains = {
            "gmail.com", "googlemail.com", "yahoo.com", "ymail.com",
            "hotmail.com", "outlook.com", "live.com", "icloud.com",
            "me.com", "aol.com", "protonmail.com", "proton.me",
            "mail.com", "zoho.com", "fastmail.com", "hey.com"
        }
        if domain in personal_domains:
            return "personal_domain_contact"
        return "company_contact"
    
    if linkedin_id:
        return "linkedin_only_contact"
    
    return "unknown"


# ---------------------------------------------------------------------------
# Job Message Classification
# ---------------------------------------------------------------------------

_JOB_KEYWORDS = [
    "job", "opening", "position", "role", "hiring", "career",
    "opportunity", "vacancy", "employ", "recruit", "interview",
    "apply", "application", "candidate", "resume", "cv",
    "hired", "hire", "offer", "salary", "benefits",
    "remote", "onsite", "hybrid", "full-time", "part-time",
    "contract", "permanent", "experience", "requirements",
    "qualifications", "responsibilities", "skills",
    "job description", "job title", "hiring manager"
]


def is_job_message(text: str) -> bool:
    """Check if message is about a job opening."""
    if not text:
        return False
    text_lower = text.lower()
    # Count job-related keywords
    matches = sum(1 for keyword in _JOB_KEYWORDS if keyword in text_lower)
    return matches >= 2


# ---------------------------------------------------------------------------
# Job Details Extraction
# ---------------------------------------------------------------------------

def extract_job_details(text: str) -> Dict[str, Optional[str]]:
    """
    Extract job details from message text.
    Returns: raw_title, raw_company, raw_location, raw_description
    """
    result = {
        "raw_title": None,
        "raw_company": None,
        "raw_location": None,
        "raw_description": None
    }
    
    if not text or not is_job_message(text):
        return result
    
    lines = text.split("\n")
    
    # Extract job title patterns
    title_patterns = [
        r"(?:position|role|title|job)[:\s]+([A-Z][a-zA-Z\s]{3,50})",
        r"(?:hiring|looking for|seeking)[:\s]+([A-Z][a-zA-Z\s]{3,50})",
        r"\b([A-Z][a-zA-Z\s]+(?:Engineer|Developer|Manager|Director|Analyst|Consultant|Designer|Architect|Specialist|Coordinator|Lead|Head|Principal|Scientist|Researcher))\b"
    ]
    
    for pattern in title_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["raw_title"] = match.group(1).strip()
            break
    
    # Extract company patterns
    company_patterns = [
        r"(?:at|@|company|employer)[:\s]+([A-Z][a-zA-Z0-9\s]{2,40})",
        r"\b([A-Z][a-zA-Z0-9\s]+(?:Inc|LLC|Ltd|Corp|Solutions|Technologies|Services|Consulting|Group|Labs))\b"
    ]
    
    for pattern in company_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["raw_company"] = match.group(1).strip()
            break
    
    # Extract location patterns
    location_patterns = [
        r"(?:location|based|located)[:\s]+([A-Z][a-zA-Z0-9\s,]{3,50})",
        r"([A-Z][a-zA-Z]+,\s*[A-Z]{2}\s*\d{5})",
        r"\b(Remote|Hybrid|On-site|Onsite)\b"
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["raw_location"] = match.group(1).strip()
            break
    
    # Get full description (first 1000 chars)
    if is_job_message(text):
        result["raw_description"] = text[:1000] if len(text) > 1000 else text
    
    return result


# ---------------------------------------------------------------------------
# LinkedIn ID Helpers
# ---------------------------------------------------------------------------

def _extract_linkedin_internal_id(profile_url: str) -> Optional[str]:
    """Extract internal ID (ACoAA...) from LinkedIn profile URL."""
    if not profile_url:
        return None
    match = _LINKEDIN_INTERNAL_ID_RE.search(profile_url)
    return match.group(1) if match else None


def _clean_linkedin_url(url: str) -> str:
    """Remove internal ID from URL, keep only username."""
    if not url:
        return ""
    # Remove internal ID part (ACoAA...)
    cleaned = re.sub(r"/in/[A-Za-z0-9_-]{20,}", "", url)
    cleaned = cleaned.rstrip("/")
    return cleaned if cleaned else url


# ---------------------------------------------------------------------------
# Regex Helper Functions
# ---------------------------------------------------------------------------

def _regex_emails(text: str, exclude_personal: bool = True) -> list[str]:
    """Return unique, validated email addresses from text."""
    seen: set[str] = set()
    results: list[str] = []
    for m in _EMAIL_RE.findall(text):
        email = m.lower()
        if email in seen:
            continue
        seen.add(email)
        # Reject image file false-positives
        if any(email.endswith(ext) for ext in _IMAGE_EXTS):
            continue
        domain = email.split("@", 1)[1]
        if exclude_personal and domain in _PERSONAL_DOMAINS:
            continue
        results.append(email)
    return results


def _to_e164(digits: str) -> str:
    """Convert a 10-digit US number to E.164 format (+1XXXXXXXXXX)."""
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits[0] == "1":
        return f"+{digits}"
    return f"+{digits}"


def _normalize_phone(raw: str) -> Optional[str]:
    """Extract digits and return E.164 format."""
    digits = re.sub(r"\D", "", raw)
    core = digits[1:] if (len(digits) == 11 and digits[0] == "1") else digits
    if len(core) != 10:
        return None
    return _to_e164(core)


def _regex_phones(text: str) -> list[str]:
    """Return unique phone numbers in E.164 format."""
    seen: set[str] = set()
    results: list[str] = []
    for m in _PHONE_RE.findall(text):
        m = m.strip()
        normalized = _normalize_phone(m)
        if normalized is None:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        results.append(normalized)
    return results


def _regex_linkedin_urls(text: str) -> list[str]:
    """Extract LinkedIn profile URLs from text."""
    results = []
    seen: set[str] = set()
    for slug in _LINKEDIN_URL_RE.findall(text):
        slug = slug.lower()
        if slug in seen:
            continue
        seen.add(slug)
        results.append(f"https://www.linkedin.com/in/{slug}")
    return results


# ---------------------------------------------------------------------------
# Main Class
# ---------------------------------------------------------------------------

class MessageContactExtractor:
    """
    Orchestrates SpaCy + GLiNER NER engines with a field-level fallback chain
    to extract contact info from LinkedIn inbox conversation dicts.
    """

    FALLBACK_CHAIN = {
        "sender_name": ["linkedin_profile", "metadata", "gliner", "spacy", "signature"],
        "company": ["linkedin_profile", "gliner", "spacy", "intro_pattern"],
        "job_title": ["linkedin_profile", "gliner", "spacy"],
        "location": ["linkedin_profile", "gliner", "spacy"],
        "email": ["regex"],
        "phone": ["regex"],
    }

    def __init__(
        self,
        use_gliner: bool = True,
        use_spacy: bool = True,
        exclude_personal_emails: bool = True,
    ) -> None:
        self.use_gliner = use_gliner
        self.use_spacy = use_spacy
        self.exclude_personal_emails = exclude_personal_emails

    # ------------------------------------------------------------------
    # Public Entry Points
    # ------------------------------------------------------------------

    def extract(self, conversation: dict[str, Any]) -> dict[str, Any]:
        """
        Extract a contact record from a raw conversation dict.
        Returns a dict matching automation_contact_extracts table schema.
        """
        conv_id = conversation.get("conversation_id", "unknown")
        participant = conversation.get("participant_name") or ""
        profile_url = conversation.get("participant_profile_url") or ""
        messages = conversation.get("messages", [])
        candidate_id = conversation.get("candidate_id")
        candidate_email = conversation.get("candidate_email", "")

        # Combine all message texts
        combined_text = "\n".join(
            m.get("text", "") for m in messages if m.get("text")
        )

        # Gather sources
        linkedin_data = self._from_linkedin_profile(participant, profile_url)
        metadata_data = self._from_metadata(messages)
        regex_data = self._from_regex(combined_text)
        gliner_data = {}
        spacy_data = {}
        signature_data = {}
        intro_data = {}

        if combined_text.strip():
            if self.use_gliner:
                try:
                    gliner_data = _get_gliner().extract(combined_text)
                except Exception as exc:
                    logger.warning("[MCE] GLiNER failed for conv %s: %s", conv_id, exc)

            if self.use_spacy:
                try:
                    spacy_data = _get_spacy().extract(combined_text)
                except Exception as exc:
                    logger.warning("[MCE] SpaCy failed for conv %s: %s", conv_id, exc)

                try:
                    sig_name = _get_spacy().extract_name_from_signature(combined_text)
                    if sig_name:
                        signature_data = {"sender_name": sig_name}
                except Exception as exc:
                    logger.warning("[MCE] SpaCy signature failed for conv %s: %s", conv_id, exc)

                try:
                    intro_company = _get_spacy().extract_company_from_intro(combined_text)
                    if intro_company:
                        intro_data = {"company": intro_company}
                except Exception as exc:
                    logger.warning("[MCE] SpaCy intro failed for conv %s: %s", conv_id, exc)

        source_map = {
            "linkedin_profile": linkedin_data,
            "metadata": metadata_data,
            "gliner": gliner_data,
            "spacy": spacy_data,
            "signature": signature_data,
            "intro_pattern": intro_data,
            "regex": regex_data,
        }

        # Apply fallback chain per field
        contact: dict[str, Any] = {}
        for field, chain in self.FALLBACK_CHAIN.items():
            contact[field] = None
            for source_name in chain:
                value = source_map.get(source_name, {}).get(field)
                if value:
                    contact[field] = value
                    logger.debug("[MCE] conv %s  %-12s <- %s: %r", conv_id, field, source_name, value)
                    break

        # ========== NEW: LinkedIn Internal ID Extraction ==========
        linkedin_internal_id = _extract_linkedin_internal_id(profile_url)
        linkedin_id = _clean_linkedin_url(profile_url)
        
        # ========== NEW: Location Parsing ==========
        location_data = parse_location(contact.get("location"))
        
        # ========== NEW: Contact Classification ==========
        classification = classify_contact(contact.get("email"), linkedin_id)
        
        # ========== NEW: Job Details Extraction ==========
        job_details = extract_job_details(combined_text)
        is_job = is_job_message(combined_text)

        # Try to infer a missing name from the email address
        final_name = contact.get("sender_name")
        email_val = contact.get("email")
        if not final_name and email_val:
            final_name = _extract_name_from_email(email_val)
            if final_name:
                logger.debug(f"[MCE] inferred missing name '{final_name}' from email '{email_val}'")

        # Build final contact dict matching table schema
        contact_final = {
            # Contact info
            "full_name": final_name,
            "email": contact.get("email"),
            "phone": contact.get("phone"),
            "company_name": contact.get("company"),
            "job_title": contact.get("job_title"),
            
            # Location
            "city": location_data.get("city"),
            "state": location_data.get("state"),
            "country": location_data.get("country"),
            "postal_code": location_data.get("postal_code"),
            
            # LinkedIn
            "linkedin_id": linkedin_id,
            "linkedin_internal_id": linkedin_internal_id,
            
            # Metadata - FIXED source_type
            "source_type": "bot_linkedin_message_extraction",
            "source_reference": conv_id,
            "classification": classification,
            
            # Additional fields
            "raw_payload": conversation,
            
            # Conversation metadata
            "conversation_url": (
                f"https://www.linkedin.com/messaging/thread/{conv_id}/"
                if conv_id != "unknown" else ""
            ),
            "source": "inbox_ner",
            "extraction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "conversation_id": conv_id,
            "candidate_id": candidate_id,
            "candidate_email": candidate_email,
            
            # Job details
            "is_job_message": is_job,
            "job_details": job_details,
        }

        return contact_final

    def extract_batch(
        self, conversations: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Process a list of conversation dicts."""
        results = []
        total = len(conversations)
        for i, conv in enumerate(conversations, start=1):
            try:
                contact = self.extract(conv)
                results.append(contact)
                logger.debug("[MCE] Processed %d/%d: %s", i, total, conv.get("conversation_id"))
            except Exception as exc:
                logger.error(
                    "[MCE] Error processing conv %s: %s",
                    conv.get("conversation_id", "?"), exc,
                    exc_info=True,
                )
        logger.info("[MCE] Batch complete: %d/%d conversations processed", len(results), total)
        return results

    # ------------------------------------------------------------------
    # Source Extractors
    # ------------------------------------------------------------------

    def _from_linkedin_profile(self, participant_name: str, profile_url: str) -> dict:
        """Highest-confidence source: data from conversation sidebar."""
        data: dict = {}
        if participant_name and participant_name.strip():
            data["sender_name"] = participant_name.strip()
        return data

    def _from_metadata(self, messages: list[dict]) -> dict:
        """Second-priority: display name from message thread UI."""
        data: dict = {}
        for msg in messages:
            name = (msg.get("sender_name") or "").strip()
            if name and name.lower() not in ("me", "you", ""):
                data["sender_name"] = name
                break
        return data

    def _from_regex(self, text: str) -> dict:
        """High-precision regex extraction for email, phone, LinkedIn URLs."""
        data: dict = {}

        emails = _regex_emails(text, self.exclude_personal_emails)
        if emails:
            data["email"] = emails[0]

        phones = _regex_phones(text)
        if phones:
            data["phone"] = phones[0]

        li_urls = _regex_linkedin_urls(text)
        if li_urls:
            data["linkedin_id"] = li_urls[0]

        return data