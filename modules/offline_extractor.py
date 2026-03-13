# # modules/offline_extractor.py
# """
# Phase 2 — Offline Contact Extractor

# Reads raw conversation JSON files produced by InboxScraper (Phase 1),
# mines every message bubble for emails and phone numbers using regex,
# derives name and company heuristics from the email address, and writes
# deduplicated contact records to:

#     data/output/<YYYY-MM-DD>/inbox_contacts.json
#     data/output/<YYYY-MM-DD>/inbox_contacts.csv
# """

# from __future__ import annotations

# import csv
# import json
# import logging
# import os
# import re
# from datetime import date, datetime
# from pathlib import Path
# from typing import Any, Dict, List, Optional, Set, Tuple

# logger = logging.getLogger(__name__)

# # ---------------------------------------------------------------------------
# # Configuration constants
# # ---------------------------------------------------------------------------

# # Free/personal email providers — contacts from these are unlikely to be
# # business leads, so we exclude them from the extracted contact list.
# PERSONAL_DOMAINS: Set[str] = {
#     "gmail.com", "googlemail.com",
#     "yahoo.com", "yahoo.co.uk", "yahoo.co.in", "ymail.com",
#     "hotmail.com", "hotmail.co.uk",
#     "outlook.com", "live.com", "msn.com",
#     "icloud.com", "me.com",
#     "aol.com",
#     "protonmail.com", "proton.me",
#     "mail.com",
#     "zoho.com",
#     "fastmail.com", "fastmail.fm",
#     "hey.com",
#     "inbox.com",
# }

# # File extensions that sometimes appear inside URLs — skip emails that end
# # with these (e.g. "noreply@example.com.png" from inline images).
# IMAGE_EXTENSIONS: Set[str] = {
#     ".png", ".jpg", ".jpeg", ".gif", ".svg",
#     ".webp", ".bmp", ".ico", ".tif", ".tiff",
# }

# # ---------------------------------------------------------------------------
# # Compiled regex patterns
# # ---------------------------------------------------------------------------

# _EMAIL_RE = re.compile(
#     r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
#     re.IGNORECASE,
# )

# # US phone patterns — ordered most-specific → least-specific:
# #   +1-800-555-1234 | +1 (800) 555-1234 | (800) 555-1234 | 800-555-1234 | 8005551234
# _PHONE_RE = re.compile(
#     r"""
#     (?:
#         # +1 variants
#         \+1[\s.\-]?              # +1 with optional separator
#         (?:\(\d{3}\)|\d{3})     # area code, with or without parens
#         [\s.\-]?
#         \d{3}
#         [\s.\-]?
#         \d{4}
#     |
#         # US local variants  (NXX) NXX-XXXX or NXX-NXX-XXXX
#         \(?\d{3}\)?             # area code
#         [\s.\-]
#         \d{3}
#         [\s.\-]
#         \d{4}
#     |
#         # Plain 10-digit run (no punctuation)
#         \b(?<![\d\-.])\d{10}(?![\d\-.])
#     )
#     """,
#     re.VERBOSE,
# )

# # ---------------------------------------------------------------------------
# # Name / company derivation helpers
# # ---------------------------------------------------------------------------

# def _derive_name_from_email(local_part: str) -> Optional[str]:
#     """
#     Turn the local part of an email address into a human-readable name.

#     Examples
#     --------
#     john.doe      → John Doe
#     j.doe         → J Doe
#     john_doe      → John Doe
#     johndoe       → Johndoe   (single token — caller should prefer fallback)
#     """
#     # Replace separators with spaces
#     name = re.sub(r"[._\-+]", " ", local_part).strip()

#     # Strip trailing digits (e.g. "john.doe2")
#     name = re.sub(r"\s*\d+$", "", name).strip()

#     if not name:
#         return None

#     parts = name.split()
#     if len(parts) == 1 and len(parts[0]) <= 2:
#         # Single very-short token (likely just initials) — not useful
#         return None

#     return " ".join(p.capitalize() for p in parts)


# def _derive_company_from_domain(domain: str) -> Optional[str]:
#     """
#     Extract a best-guess company name from an email domain.

#     Examples
#     --------
#     google.com       → Google
#     acmecorp.io      → Acmecorp
#     mail.bigco.com   → Bigco
#     """
#     # Strip known mail sub-domains (mail., smtp., em., ...)
#     domain = re.sub(r"^(?:mail|smtp|em\d*|send|reply|bounce|mg)\.", "", domain, flags=re.IGNORECASE)

#     # Take the second-level domain label (everything before the last TLD)
#     parts = domain.split(".")
#     if len(parts) >= 2:
#         company_slug = parts[-2]
#     else:
#         company_slug = parts[0]

#     # Humanise: separate CamelCase, strip digits suffix
#     company_slug = re.sub(r"([a-z])([A-Z])", r"\1 \2", company_slug)
#     company_slug = re.sub(r"\d+$", "", company_slug).strip()

#     return company_slug.capitalize() if company_slug else None


# def _clean_phone(raw: str) -> str:
#     """
#     Normalise a raw phone match to its 10-digit local form for dedup.
#     Strips all non-digits and removes a leading US country code (1).
#     e.g.  '+1-800-555-6789' -> '8005556789'
#           '(800) 555-6789'  -> '8005556789'
#           '8005556789'      -> '8005556789'
#     """
#     digits = re.sub(r"\D", "", raw)
#     if len(digits) == 11 and digits[0] == "1":
#         digits = digits[1:]   # strip leading US country code
#     return digits


# # ---------------------------------------------------------------------------
# # Main class
# # ---------------------------------------------------------------------------

# class OfflineExtractor:
#     """
#     Phase 2 — reads raw JSON produced by InboxScraper and extracts contacts.

#     Parameters
#     ----------
#     input_dir  : directory containing <conversation_id>.json files
#     output_dir : directory where inbox_contacts.json / .csv are written
#     date_str   : ISO date string used in output paths (default: today)
#     exclude_personal : whether to filter out personal email domains (default: True)
#     """

#     def __init__(
#         self,
#         input_dir: str,
#         output_dir: str,
#         date_str: Optional[str] = None,
#         exclude_personal: bool = True,
#         validate_emails: bool = True,
#     ) -> None:
#         self.input_dir        = Path(input_dir)
#         self.output_dir       = Path(output_dir)
#         self.date_str         = date_str or date.today().isoformat()
#         self.exclude_personal = exclude_personal
#         self.validate_emails  = validate_emails   # syntax + MX gate before dedup

#         self.output_dir.mkdir(parents=True, exist_ok=True)

#         logger.info(
#             "OfflineExtractor initialised\n  input : %s\n  output: %s\n  validate_emails: %s",
#             self.input_dir, self.output_dir, self.validate_emails,
#         )

#     # ------------------------------------------------------------------
#     # Public entry point
#     # ------------------------------------------------------------------

#     def run(self) -> List[Dict[str, Any]]:
#         """
#         Execute the full offline extraction pipeline.

#         Pipeline:
#           1. Read all conversation JSON files
#           2. Extract emails / phones via regex  
#           3. Validate each email (syntax + MX)   ← NEW
#           4. Deduplicate
#           5. Save JSON + CSV

#         Returns the list of deduplicated, email-validated contact dicts.
#         """
#         conversations = self._read_conversations()
#         logger.info("[OFFLINE] Read %d conversation file(s)", len(conversations))

#         raw_contacts: List[Dict[str, Any]] = []
#         for conv in conversations:
#             raw_contacts.extend(self._extract_contacts_from_conversation(conv))

#         logger.info("[OFFLINE] %d raw contact(s) extracted before validation", len(raw_contacts))

#         # ── Email validation gate (syntax + MX) ────────────────────────────
#         if self.validate_emails:
#             try:
#                 from utils.email_validator import validate_email
#             except ImportError:
#                 logger.warning(
#                     "[OFFLINE] utils.email_validator not found — skipping email validation."
#                     " Install dnspython: pip install dnspython"
#                 )
#                 validate_email = None

#             if validate_email is not None:
#                 passed: List[Dict[str, Any]] = []
#                 rejected = 0
#                 for contact in raw_contacts:
#                     email = contact.get("email", "")
#                     result = validate_email(email, check_mx=True, check_smtp=False)
#                     if result["valid"]:
#                         # Stamp validation metadata on the record
#                         contact["email_syntax_valid"] = True
#                         contact["email_mx_valid"]     = True
#                         passed.append(contact)
#                     else:
#                         reason = "syntax" if not result["syntax_valid"] else "MX"
#                         logger.warning(
#                             "[OFFLINE] Rejected email (%s failed): %s", reason, email
#                         )
#                         rejected += 1

#                 logger.info(
#                     "[OFFLINE] Email validation: %d passed, %d rejected (syntax/MX)",
#                     len(passed), rejected,
#                 )
#                 raw_contacts = passed
#         # ───────────────────────────────────────────────────────────────────

#         contacts = self._deduplicate(raw_contacts)
#         logger.info("[OFFLINE] %d unique contact(s) after dedup", len(contacts))

#         json_path, csv_path = self._save_results(contacts)
#         logger.info("[OFFLINE] Saved → %s", json_path)
#         logger.info("[OFFLINE] Saved → %s", csv_path)

#         return contacts

#     # ------------------------------------------------------------------
#     # Reading
#     # ------------------------------------------------------------------

#     def _read_conversations(self) -> List[Dict[str, Any]]:
#         """Load all .json files in input_dir."""
#         if not self.input_dir.exists():
#             logger.warning("[OFFLINE] Input directory does not exist: %s", self.input_dir)
#             return []

#         convs = []
#         for path in sorted(self.input_dir.glob("*.json")):
#             try:
#                 with open(path, encoding="utf-8") as fh:
#                     convs.append(json.load(fh))
#             except (json.JSONDecodeError, OSError) as exc:
#                 logger.warning("[OFFLINE] Skipping %s — %s", path.name, exc)

#         return convs

#     # ------------------------------------------------------------------
#     # Extraction
#     # ------------------------------------------------------------------

#     def _extract_contacts_from_conversation(self, conv: Dict[str, Any]) -> List[Dict[str, Any]]:
#         """
#         Produce one contact dict per unique email found in the conversation.
#         """
#         conv_id: str = conv.get("conversation_id", "unknown")
#         participant_name: Optional[str] = conv.get("participant_name")
#         participant_url: Optional[str] = conv.get("participant_profile_url")
#         messages: List[Dict] = conv.get("messages", [])

#         # Combine all message texts into one blob for regex search
#         combined_text = "\n".join(
#             m.get("text", "") for m in messages if m.get("text")
#         )

#         emails = self._extract_emails(combined_text)
#         phones = self._extract_phones(combined_text)

#         if not emails:
#             logger.debug("[OFFLINE] conv %s — no emails found", conv_id)
#             return []

#         contacts: List[Dict[str, Any]] = []

#         # Map the first (most prominent) phone to each email; rest share it too.
#         primary_phone = phones[0] if phones else None
#         extraction_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

#         for email in emails:
#             local_part, domain = email.rsplit("@", 1)

#             # --- Name ---
#             derived_name = _derive_name_from_email(local_part)
#             full_name = derived_name or participant_name or ""

#             # --- Company ---
#             company = _derive_company_from_domain(domain)

#             contacts.append({
#                 "full_name": full_name,
#                 "email": email.lower(),
#                 "phone": primary_phone,
#                 "linkedin_id": participant_url or "",
#                 "company": company or "",
#                 "conversation_url": (
#                     f"https://www.linkedin.com/messaging/thread/{conv_id}/"
#                     if conv_id != "unknown" else ""
#                 ),
#                 "source": "inbox",
#                 "extraction_date": extraction_ts,
#             })

#         return contacts

#     def _extract_emails(self, text: str) -> List[str]:
#         """
#         Return a list of business email addresses found in text.

#         Filters out:
#         - Personal/free email domains (if exclude_personal=True)
#         - Addresses whose TLD looks like an image extension
#         """
#         raw = _EMAIL_RE.findall(text)
#         seen: Set[str] = set()
#         results: List[str] = []

#         for email in raw:
#             email_lower = email.lower()

#             # Skip duplicates within this call
#             if email_lower in seen:
#                 continue
#             seen.add(email_lower)

#             # Skip image-extension false positives (e.g. foo@bar.com.png)
#             if any(email_lower.endswith(ext) for ext in IMAGE_EXTENSIONS):
#                 continue

#             domain = email_lower.split("@", 1)[1]

#             if self.exclude_personal and domain in PERSONAL_DOMAINS:
#                 logger.debug("[EMAIL] Skipped personal domain: %s", email)
#                 continue

#             results.append(email_lower)

#         return results

#     def _extract_phones(self, text: str) -> List[str]:
#         """
#         Return unique phone number strings found in text, most-specific first.
#         Deduplicates by 10-digit normalised form so +1-800-555-6789 and
#         (800) 555-6789 are treated as the same number.
#         """
#         raw_matches = _PHONE_RE.findall(text)
#         seen_digits: Set[str] = set()
#         results: List[str] = []

#         for match in raw_matches:
#             match = match.strip()
#             digits = _clean_phone(match)   # always 10-digit normalised

#             # Must be exactly 10 digits after normalisation
#             if len(digits) != 10:
#                 continue

#             if digits in seen_digits:
#                 continue
#             seen_digits.add(digits)

#             results.append(match)

#         return results

#     # ------------------------------------------------------------------
#     # Deduplication
#     # ------------------------------------------------------------------

#     @staticmethod
#     def _deduplicate(contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
#         """
#         Deduplicate by email (case-insensitive).
#         When duplicates exist, prefer the record with the most data filled in.
#         """
#         best: Dict[str, Dict[str, Any]] = {}

#         for c in contacts:
#             key = c["email"]
#             if key not in best:
#                 best[key] = c
#             else:
#                 # Prefer the record with more non-empty fields
#                 existing_score = sum(1 for v in best[key].values() if v)
#                 new_score = sum(1 for v in c.values() if v)
#                 if new_score > existing_score:
#                     best[key] = c

#         return list(best.values())

#     # ------------------------------------------------------------------
#     # Saving
#     # ------------------------------------------------------------------

#     def _save_results(self, contacts: List[Dict[str, Any]]) -> Tuple[str, str]:
#         """Write contacts to JSON and CSV. Returns (json_path, csv_path)."""
#         json_path = self.output_dir / "inbox_contacts.json"
#         csv_path = self.output_dir / "inbox_contacts.csv"

#         # JSON
#         with open(json_path, "w", encoding="utf-8") as fh:
#             json.dump(contacts, fh, ensure_ascii=False, indent=2)

#         # CSV
#         if contacts:
#             fieldnames = list(contacts[0].keys())
#             with open(csv_path, "w", encoding="utf-8", newline="") as fh:
#                 writer = csv.DictWriter(fh, fieldnames=fieldnames)
#                 writer.writeheader()
#                 writer.writerows(contacts)
#         else:
#             # Write an empty CSV with headers
#             fieldnames = [
#                 "full_name", "email", "phone", "linkedin_id",
#                 "company", "conversation_url", "source", "extraction_date",
#             ]
#             with open(csv_path, "w", encoding="utf-8", newline="") as fh:
#                 csv.DictWriter(fh, fieldnames=fieldnames).writeheader()

#         return str(json_path), str(csv_path)





#updated code
# modules/offline_extractor.py
"""
Phase 2 — Offline Contact Extractor

Reads raw conversation JSON files produced by InboxScraper (Phase 1),
mines every message bubble for emails and phone numbers using regex,
derives name and company heuristics from the email address, and writes
deduplicated contact records to:
    data/output/<YYYY-MM-DD>/inbox_contacts.json
    data/output/<YYYY-MM-DD>/inbox_contacts.csv

Updated to match table schemas:
- automation_contact_extracts
- raw_job_listings
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration Constants
# ---------------------------------------------------------------------------

PERSONAL_DOMAINS: Set[str] = {
    "gmail.com", "googlemail.com",
    "yahoo.com", "yahoo.co.uk", "yahoo.co.in", "ymail.com",
    "hotmail.com", "hotmail.co.uk",
    "outlook.com", "live.com", "msn.com",
    "icloud.com", "me.com",
    "aol.com",
    "protonmail.com", "proton.me",
    "mail.com",
    "zoho.com",
    "fastmail.com", "fastmail.fm",
    "hey.com",
    "inbox.com",
}

# Known personal email domains to reject as companies
_PERSONAL_EMAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "yahoo.com", "ymail.com",
    "hotmail.com", "outlook.com", "live.com", "icloud.com",
    "me.com", "aol.com", "protonmail.com", "proton.me",
    "mail.com", "zoho.com", "fastmail.com", "hey.com",
    "email.com", "inbox.com", "gmx.com", "yandex.com"
}

IMAGE_EXTENSIONS: Set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".webp", ".bmp", ".ico", ".tif", ".tiff",
}

# ---------------------------------------------------------------------------
# Compiled Regex Patterns
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

_PHONE_RE = re.compile(
    r"""
    (?:
        \+1[\s.\-]?
        (?:\(\d{3}\)|\d{3})
        [\s.\-]?
        \d{3}
        [\s.\-]?
        \d{4}
    |
        \(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}
    |
        \b(?<![\d\-.])\d{10}(?![\d\-.])
    )
    """,
    re.VERBOSE,
)

# LinkedIn Internal ID Pattern
_LINKEDIN_INTERNAL_ID_RE = re.compile(
    r"linkedin\.com/in/([A-Za-z0-9_-]{20,})",
    re.IGNORECASE,
)

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
    """Parse location string into components."""
    result = {"city": None, "state": None, "country": None, "postal_code": None}
    
    if not location_str:
        return result
    
    location_str = location_str.strip()
    
    # Extract postal code
    zip_match = re.search(r'\b(\d{5}(?:-\d{4})?)\b', location_str)
    if zip_match:
        result["postal_code"] = zip_match.group(1)
        location_str = location_str.replace(zip_match.group(0), "").strip()
    
    # Split by comma
    parts = [p.strip() for p in location_str.split(",")]
    
    if len(parts) >= 1 and parts[0]:
        result["city"] = parts[0]
    
    if len(parts) >= 2:
        second = parts[1].strip().upper()
        if second.lower() in _US_STATES:
            result["state"] = second
        elif second in _US_STATES.values():
            result["state"] = second.upper()
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
    
    # Handle Remote
    if location_str.lower() in ["remote", "work from home", "wfh"]:
        result["city"] = "Remote"
        result["country"] = "US"
    
    return result


# ---------------------------------------------------------------------------
# Contact Classification
# ---------------------------------------------------------------------------

def classify_contact(email: str, linkedin_id: str) -> str:
    """Classify contact type."""
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
# Name / Company Derivation Helpers
# ---------------------------------------------------------------------------

def _derive_name_from_email(local_part: str) -> Optional[str]:
    """Turn the local part of an email address into a human-readable name."""
    name = re.sub(r"[._\-+]", " ", local_part).strip()
    name = re.sub(r"\s*\d+$", "", name).strip()
    
    if not name:
        return None
    
    parts = name.split()
    if len(parts) == 1 and len(parts[0]) <= 2:
        return None
    
    return " ".join(p.capitalize() for p in parts)


def _derive_company_from_domain(domain: str) -> Optional[str]:
    """
    FIXED: Extract a best-guess company name from an email domain.
    Now rejects personal domains.
    """
    # Strip known mail sub-domains
    domain = re.sub(
        r"^(?:mail|smtp|em\d*|send|reply|bounce|mg)\.",
        "",
        domain,
        flags=re.IGNORECASE
    )
    
    # REJECT personal domains - return None
    if domain.lower() in _PERSONAL_EMAIL_DOMAINS:
        return None
    
    # Take second-level domain
    parts = domain.split(".")
    if len(parts) >= 2:
        company_slug = parts[-2]
    else:
        company_slug = parts[0]
    
    # Humanise
    company_slug = re.sub(r"([a-z])([A-Z])", r"\1 \2", company_slug)
    company_slug = re.sub(r"\d+$", "", company_slug).strip()
    
    return company_slug.capitalize() if company_slug else None


def _extract_linkedin_internal_id(profile_url: str) -> Optional[str]:
    """Extract internal ID from LinkedIn profile URL."""
    if not profile_url:
        return None
    match = _LINKEDIN_INTERNAL_ID_RE.search(profile_url)
    return match.group(1) if match else None


def _clean_linkedin_url(url: str) -> str:
    """Remove internal ID from URL."""
    if not url:
        return ""
    return re.sub(r"/in/[A-Za-z0-9_-]{20,}", "", url).rstrip("/") or url


def _clean_phone(raw: str) -> str:
    """Normalise a raw phone match to its 10-digit local form."""
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits[0] == "1":
        digits = digits[1:]
    return digits


# ---------------------------------------------------------------------------
# Job Detail Regex Patterns  (recruiter message parsing)
# ---------------------------------------------------------------------------

# "Role: Senior DevOps Engineer"  /  "Position: ..."  /  "Title: ..."
_JOB_TITLE_RE = re.compile(
    r"(?:role|position|title|opening|job title)\s*[:\-]\s*([^\n|,]{3,80})",
    re.IGNORECASE,
)

# "Company: CloudNative Tech"
_COMPANY_LINE_RE = re.compile(
    r"(?:company|employer|client company)\s*[:\-]\s*([^\n|,]{2,80})",
    re.IGNORECASE,
)

# "Location: Remote (Worldwide)"  /  "Location: New York, NY 10001"
_LOCATION_LINE_RE = re.compile(
    r"(?:location|based in|located in)\s*[:\-]\s*([^\n]{2,80})",
    re.IGNORECASE,
)


def _extract_job_details(text: str) -> Dict[str, Optional[str]]:
    """
    Extract job_title, company_name, and location from a recruiter message body.
    Matches patterns like:
        Role: Senior DevOps Engineer
        Company: CloudNative Tech
        Location: Remote (Worldwide)
    """
    result: Dict[str, Optional[str]] = {
        "job_title": None,
        "company_name": None,
        "location": None,
    }

    m = _JOB_TITLE_RE.search(text)
    if m:
        result["job_title"] = m.group(1).strip().rstrip(",;.")

    m = _COMPANY_LINE_RE.search(text)
    if m:
        result["company_name"] = m.group(1).strip().rstrip(",;.")

    m = _LOCATION_LINE_RE.search(text)
    if m:
        result["location"] = m.group(1).strip().rstrip(",;.")

    return result


# ---------------------------------------------------------------------------
# Job Message Detection & Extraction
# ---------------------------------------------------------------------------

_JOB_URL_RE1 = re.compile(
    r"https?://(?:www\.)?linkedin\.com/jobs/view/\d+",
    re.IGNORECASE,
)
_JOB_URL_RE2 = re.compile(
    r"https?://[a-zA-Z0-9.-]+(?:/jobs?|/careers?|/apply)[/\w.-]*",
    re.IGNORECASE,
)

# Structured keywords that strongly signal a job opportunity message
_JOB_SIGNAL_KEYWORDS = [
    "role:", "position:", "title:", "job title:", "opening:",
    "we are hiring", "currently hiring", "i'm hiring", "we're hiring",
    "looking for a", "seeking a", "opportunity for",
    "hiring for", "recruiting for",

    "apply", "application",
    "salary:", "compensation:", "pay range:",
    "requirements:", "responsibilities:", "qualifications:",
    "experience:", "skills:", "stack:",
    "job description", "role description",
]


def _is_job_message(text: str) -> bool:
    """
    Return True if the message text appears to describe a job opportunity.
    Requires at least ONE structured job keyword (high-precision signal).
    """
    if not text:
        return False
    lower = text.lower()
    return any(kw in lower for kw in _JOB_SIGNAL_KEYWORDS)


# ---------------------------------------------------------------------------
# Main Class
# ---------------------------------------------------------------------------

class OfflineExtractor:
    """
    Phase 2 — reads raw JSON produced by InboxScraper and extracts contacts.
    """

    def __init__(
        self,
        input_dir: str,
        output_dir: str,
        date_str: Optional[str] = None,
        exclude_personal: bool = True,
        validate_emails: bool = True,
    ) -> None:
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.date_str = date_str or date.today().isoformat()
        self.exclude_personal = exclude_personal
        self.validate_emails = validate_emails

        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "OfflineExtractor initialised\n  input : %s\n  output: %s\n  validate_emails: %s",
            self.input_dir, self.output_dir, self.validate_emails,
        )

    # ------------------------------------------------------------------
    # Public Entry Point
    # ------------------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        """
        Execute the full offline extraction pipeline.

        Returns
        -------
        dict with keys:
          "contacts"     — deduplicated recruiter contact records
          "job_listings" — one record per job message (N per conversation)
        """
        conversations = self._read_conversations()
        logger.info("[OFFLINE] Read %d conversation file(s)", len(conversations))

        raw_contacts: List[Dict[str, Any]] = []
        raw_job_listings: List[Dict[str, Any]] = []

        for conv in conversations:
            raw_contacts.extend(self._extract_contacts_from_conversation(conv))
            raw_job_listings.extend(self._extract_job_listings_from_conversation(conv))

        logger.info(
            "[OFFLINE] %d raw contact(s), %d job listing(s) extracted",
            len(raw_contacts), len(raw_job_listings),
        )

        # Email validation gate (contacts only)
        if self.validate_emails:
            try:
                from utils.email_validator import validate_email
            except ImportError:
                logger.warning(
                    "[OFFLINE] utils.email_validator not found — skipping email validation."
                )
                validate_email = None

            if validate_email is not None:
                passed: List[Dict[str, Any]] = []
                rejected = 0
                for contact in raw_contacts:
                    email = contact.get("email", "")
                    result = validate_email(email, check_mx=True, check_smtp=False)
                    if result["valid"]:
                        contact["email_syntax_valid"] = True
                        contact["email_mx_valid"] = True
                        passed.append(contact)
                    else:
                        reason = "syntax" if not result["syntax_valid"] else "MX"
                        logger.warning(
                            "[OFFLINE] Rejected email (%s failed): %s", reason, email
                        )
                        rejected += 1
                logger.info(
                    "[OFFLINE] Email validation: %d passed, %d rejected",
                    len(passed), rejected,
                )
                raw_contacts = passed

        contacts = self._deduplicate(raw_contacts)
        logger.info("[OFFLINE] %d unique contact(s) after dedup", len(contacts))

        json_path, csv_path = self._save_results(contacts)
        logger.info("[OFFLINE] Saved → %s", json_path)
        logger.info("[OFFLINE] Saved → %s", csv_path)

        return {"contacts": contacts, "job_listings": raw_job_listings}

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def _read_conversations(self) -> List[Dict[str, Any]]:
        """Load all .json files in input_dir."""
        if not self.input_dir.exists():
            logger.warning("[OFFLINE] Input directory does not exist: %s", self.input_dir)
            return []

        convs = []
        for path in sorted(self.input_dir.glob("*.json")):
            try:
                with open(path, encoding="utf-8") as fh:
                    convs.append(json.load(fh))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("[OFFLINE] Skipping %s — %s", path.name, exc)

        return convs

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    def _extract_contacts_from_conversation(self, conv: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Produce one contact dict per unique email found in the conversation."""
        conv_id: str = conv.get("conversation_id", "unknown")
        participant_name: Optional[str] = conv.get("participant_name")
        participant_url: Optional[str] = conv.get("participant_profile_url")
        messages: List[Dict] = conv.get("messages", [])

        candidate_email = (conv.get("candidate_email") or "").lower().strip()

        # ── Build combined text (for phones only) AND per-message data ──────
        # KEY FIX: track which message each email came from so we can extract
        # job details from THAT message only — not the whole conversation.
        #
        # Also detect and skip outgoing messages: if the ONLY email in a
        # message is the candidate's own email, that message was sent by them.
        combined_parts: List[str] = []
        email_to_msg_data: Dict[str, Dict] = {}     # email → {text, phone, linkedin}
        href_linkedin_urls: List[str] = []
        href_emails: List[str] = []
        skipped_outgoing = 0

        for m in messages:
            msg_email_links = [e.lower() for e in m.get("email_links", []) if e]
            msg_linkedin    = [u for u in m.get("linkedin_links", []) if u]
            msg_text        = (m.get("text") or "") + "\n" + (m.get("card_text") or "")
            msg_text        = msg_text.strip()

            # ── Outgoing detection: trust the DOM flag set by the scraper ────
            # The scraper checks for div.msg-s-message-group__meta:
            #   present  → recruiter (incoming)  → is_outgoing = False
            #   absent   → candidate (outgoing)  → is_outgoing = True
            # For JSON files scraped before this fix, fall back to the old email heuristic.
            if "is_outgoing" in m:
                if m["is_outgoing"]:
                    skipped_outgoing += 1
                    logger.debug("[OFFLINE] conv %s — skipping outgoing msg (DOM flag)", conv_id)
                    continue
            else:
                # ── Legacy fallback for older JSON files ─────────────────
                non_candidate_emails = [e for e in msg_email_links if e != candidate_email]
                all_text_raw = [
                    e.lower() for e in re.findall(
                        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", msg_text
                    ) if e
                ]
                non_candidate_in_text = [e for e in all_text_raw if e != candidate_email]
                candidate_in_text = bool(candidate_email and candidate_email in msg_text.lower())
                outgoing_by_links = bool(msg_email_links and not non_candidate_emails)
                outgoing_by_text  = bool(
                    candidate_in_text and not non_candidate_in_text and not non_candidate_emails
                )
                if outgoing_by_links or outgoing_by_text:
                    skipped_outgoing += 1
                    logger.debug("[OFFLINE] conv %s — skipping outgoing msg (legacy heuristic)", conv_id)
                    continue

            non_candidate_emails = [e for e in msg_email_links if e != candidate_email]

            # ── This is an incoming message ──────────────────────────────
            combined_parts.append(msg_text)

            # collect per-message phones for this recruiter
            msg_phones = self._extract_phones(msg_text)

            # collect linkedin URLs (conversation-wide)
            for lurl in msg_linkedin:
                if lurl not in href_linkedin_urls:
                    href_linkedin_urls.append(lurl)

            # map each recruiter email to THIS message's data
            for addr in non_candidate_emails:
                if addr not in href_emails:
                    href_emails.append(addr)
                if addr not in email_to_msg_data:
                    email_to_msg_data[addr] = {
                        "text":    msg_text,
                        "phone":   msg_phones[0] if msg_phones else None,
                        "linkedin": msg_linkedin[0] if msg_linkedin else None,
                    }

        if skipped_outgoing:
            logger.info(
                "[OFFLINE] conv %s — skipped %d outgoing message(s)",
                conv_id, skipped_outgoing,
            )

        combined_text = "\n".join(combined_parts)

        # ── Regex fallback for emails not found via href ─────────────────
        regex_emails = self._extract_emails(combined_text)

        seen_emails: Set[str] = set(href_emails)
        all_emails: List[str] = list(href_emails)
        for e in regex_emails:
            if e not in seen_emails and e != candidate_email:
                seen_emails.add(e)
                all_emails.append(e)

        # conversation-wide phone fallback (used only if per-message phone is missing)
        phones = self._extract_phones(combined_text)

        if not all_emails:
            logger.debug("[OFFLINE] conv %s — no recruiter emails found", conv_id)
            return []

        emails = all_emails
        linkedin_internal_id = participant_url or ""
        contacts: List[Dict[str, Any]] = []
        extraction_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for email in emails:
            # Belt-and-suspenders: skip candidate's own email
            if email == candidate_email:
                continue

            local_part, domain = email.rsplit("@", 1)

            # ── Per-email message context ──────────────────────────────────
            # Use the specific message that contained this email so job details
            # (title/company/location) match THIS recruiter's message only.
            msg_data = email_to_msg_data.get(email)
            if msg_data is not None:
                msg_text  = msg_data.get("text", "")
                msg_phone = msg_data.get("phone") or (phones[0] if phones else None)
                msg_li    = msg_data.get("linkedin") or ""
            else:
                # Fallback for emails discovered purely via regex across combined text
                msg_text  = combined_text
                msg_phone = phones[0] if phones else None
                msg_li    = href_linkedin_urls[0] if href_linkedin_urls else ""

            # ── Name ───────────────────────────────────────────────────────
            derived_name = _derive_name_from_email(local_part)
            full_name = derived_name or participant_name or ""

            # ── Company & job details ─────────────────────────────────────
            company_from_domain = _derive_company_from_domain(domain)
            job_details = _extract_job_details(msg_text)          # ← per-email text!
            company     = job_details["company_name"] or company_from_domain

            # ── Location ─────────────────────────────────────────────────
            location_str  = job_details["location"] or ""
            location_data = parse_location(location_str) if location_str else {
                "city": None, "state": None, "country": None, "postal_code": None
            }

            # ── Job title ─────────────────────────────────────────────────
            job_title = job_details["job_title"] or ""

            # ── LinkedIn & classification ──────────────────────────────────
            linkedin_id    = msg_li
            classification = classify_contact(email, linkedin_id)



            contacts.append({
                # Contact info
                "full_name": full_name,
                "email": email.lower(),
                "phone": msg_phone,
                "company_name": company or "",
                "job_title": job_title,
                
                # Location (NEW)
                "city": location_data.get("city"),
                "state": location_data.get("state"),
                "country": location_data.get("country"),
                "postal_code": location_data.get("postal_code"),
                
                # LinkedIn (NEW)
                "linkedin_id": linkedin_id,
                "linkedin_internal_id": linkedin_internal_id or "",
                
                # Metadata - FIXED source_type
                "source_type": "bot_linkedin_message_extraction",
                "source_reference": conv_id,
                "classification": classification,
                
                # Additional
                "raw_payload": conv,
                
                # Legacy fields
                "company": company or "",
                "conversation_url": (
                    f"https://www.linkedin.com/messaging/thread/{conv_id}/"
                    if conv_id != "unknown" else ""
                ),
                "source": "inbox",
                "extraction_date": extraction_ts,
            })

        return contacts

    # ------------------------------------------------------------------
    # Per-message Job Listing Extraction
    # ------------------------------------------------------------------

    def _extract_job_listings_from_conversation(
        self, conv: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Scan every INCOMING message individually and create one raw_job_listing
        record for each message that contains a job opportunity.

        Same recruiter, same thread, 4 different job messages:
            Monday msg    → job listing A
            Wednesday msg → job listing B
            Thu AM msg    → job listing C
            Thu PM msg    → job listing D
        """
        conv_id         = conv.get("conversation_id", "unknown")
        participant_url = conv.get("participant_profile_url") or ""
        messages        = conv.get("messages", [])
        candidate_email = (conv.get("candidate_email") or "").lower().strip()

        job_listings: List[Dict[str, Any]] = []
        extraction_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for msg_idx, m in enumerate(messages):
            msg_text = (
                (m.get("text") or "") + "\n" + (m.get("card_text") or "")
            ).strip()

            if not msg_text:
                continue

            # ── Outgoing detection: DOM flag first, email heuristic as fallback ─
            msg_email_links = [e.lower() for e in m.get("email_links", []) if e]
            if "is_outgoing" in m:
                if m["is_outgoing"]:
                    continue  # scraper confirmed this is the candidate's message
            else:
                # Legacy fallback for JSON files scraped before the DOM flag was added
                non_candidate_emails = [e for e in msg_email_links if e != candidate_email]
                all_text_raw = [
                    e.lower() for e in re.findall(
                        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", msg_text
                    ) if e
                ]
                non_candidate_in_text = [e for e in all_text_raw if e != candidate_email]
                candidate_in_text = bool(candidate_email and candidate_email in msg_text.lower())
                if (bool(msg_email_links and not non_candidate_emails) or
                        bool(candidate_in_text and not non_candidate_in_text and not non_candidate_emails)):
                    continue  # skip outgoing

            non_candidate_emails = [e for e in msg_email_links if e != candidate_email]

            # ── Only process messages that contain job opportunity content ─
            if not _is_job_message(msg_text):
                continue

            # ── Extract from THIS message only ────────────────────────────
            job_details       = _extract_job_details(msg_text)
            msg_phones        = self._extract_phones(msg_text)
            msg_linkedin_urls = [u for u in m.get("linkedin_links", []) if u]

            recruiter_email    = next(iter(non_candidate_emails), "")
            recruiter_phone    = msg_phones[0] if msg_phones else ""
            recruiter_linkedin = msg_linkedin_urls[0] if msg_linkedin_urls else participant_url

            # Extract apply/job URLs from this message
            apply_links: List[str] = m.get("external_links", [])[:]
            for pattern in [_JOB_URL_RE1, _JOB_URL_RE2]:
                for url in pattern.findall(msg_text):
                    url = url.rstrip(".,);\"'")
                    if url and url not in apply_links:
                        apply_links.append(url)
            card_text = m.get("card_text") or ""
            if card_text:
                for pattern in [_JOB_URL_RE1, _JOB_URL_RE2]:
                    for url in pattern.findall(card_text):
                        url = url.rstrip(".,);\"'")
                        if url and url not in apply_links:
                            apply_links.append(url)

            # ── Unique uid: conv_id + full timestamp (preferred) or index (fallback) ──
            # msg_timestamp = "Mon, Feb 3 8:44 AM" — stable across re-scrapes.
            # Falls back to msg{index} for JSON files scraped before this change.
            raw_msg_ts = m.get("msg_timestamp") or ""
            if raw_msg_ts:
                # Sanitise for use in a key: replace spaces/commas with underscores
                ts_slug = re.sub(r"[^a-zA-Z0-9]+", "_", raw_msg_ts).strip("_")
                source_uid = f"{conv_id}_{ts_slug}"
            else:
                source_uid = f"{conv_id}_msg{msg_idx}"

            listing = {
                "source":            "bot_linkedin_message_extraction",
                "source_uid":        source_uid,
                "extractor_version": "v2",
                "raw_title":         job_details.get("job_title") or "",
                "raw_company":       job_details.get("company_name") or "",
                "raw_location":      job_details.get("location") or "",
                "raw_zip":           "",
                "raw_description":   msg_text[:3000],
                "raw_contact_info":  f"{recruiter_email} {recruiter_phone}".strip() or None,
                "raw_notes":         "",
                "raw_payload": {
                    "conversation_id":    conv_id,
                    "msg_index":          msg_idx,
                    "timestamp":          m.get("timestamp"),
                    "message_text":       msg_text,
                    "apply_links":        apply_links,
                    "recruiter_email":    recruiter_email,
                    "recruiter_phone":    recruiter_phone,
                    "recruiter_linkedin": recruiter_linkedin,
                    "extraction_date":    extraction_ts,
                },
            }

            job_listings.append(listing)
            logger.debug(
                "[OFFLINE] conv %s msg[%d] → job listing: %r @ %r (apply_links=%d)",
                conv_id, msg_idx,
                job_details.get("job_title"),
                job_details.get("company_name"),
                len(apply_links),
            )

        if job_listings:
            logger.info(
                "[OFFLINE] conv %s → %d job listing(s) from %d message(s)",
                conv_id, len(job_listings), len(messages),
            )

        return job_listings

    def _extract_emails(self, text: str) -> List[str]:
        """Return a list of business email addresses found in text."""
        raw = _EMAIL_RE.findall(text)
        seen: Set[str] = set()
        results: List[str] = []

        for email in raw:
            email_lower = email.lower()

            if email_lower in seen:
                continue
            seen.add(email_lower)

            if any(email_lower.endswith(ext) for ext in IMAGE_EXTENSIONS):
                continue

            domain = email_lower.split("@", 1)[1]

            if self.exclude_personal and domain in PERSONAL_DOMAINS:
                logger.debug("[EMAIL] Skipped personal domain: %s", email)
                continue

            results.append(email_lower)

        return results

    def _extract_phones(self, text: str) -> List[str]:
        """Return unique phone number strings found in text."""
        raw_matches = _PHONE_RE.findall(text)
        seen_digits: Set[str] = set()
        results: List[str] = []

        for match in raw_matches:
            match = match.strip()
            digits = _clean_phone(match)

            if len(digits) != 10:
                continue

            if digits in seen_digits:
                continue
            seen_digits.add(digits)

            results.append(match)

        return results

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    @staticmethod
    def _deduplicate(contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate by email (case-insensitive)."""
        best: Dict[str, Dict[str, Any]] = {}

        for c in contacts:
            key = c["email"]
            if key not in best:
                best[key] = c
            else:
                existing_score = sum(1 for v in best[key].values() if v)
                new_score = sum(1 for v in c.values() if v)
                if new_score > existing_score:
                    best[key] = c

        return list(best.values())

    # ------------------------------------------------------------------
    # Saving
    # ------------------------------------------------------------------

    def _save_results(self, contacts: List[Dict[str, Any]]) -> Tuple[str, str]:
        """Write contacts to JSON and CSV."""
        json_path = self.output_dir / "inbox_contacts.json"
        csv_path = self.output_dir / "inbox_contacts.csv"

        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(contacts, fh, ensure_ascii=False, indent=2)

        if contacts:
            fieldnames = list(contacts[0].keys())
            with open(csv_path, "w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(contacts)
        else:
            fieldnames = [
                "full_name", "email", "phone", "linkedin_id",
                "company", "conversation_url", "source", "extraction_date",
            ]
            with open(csv_path, "w", encoding="utf-8", newline="") as fh:
                csv.DictWriter(fh, fieldnames=fieldnames).writeheader()

        return str(json_path), str(csv_path)