# utils/email_validator.py
"""
EmailListValidator — validate email addresses (syntax, MX, SMTP mailbox)
before they are inserted into any data store.

Two interfaces:
  1. validate_email(email, check_mx, check_smtp)
       — lightweight single-email check; used inline by offline_extractor and db.py.

  2. EmailListValidator(filepath).run(...)
       — batch CSV pipeline (syntax → MX → SMTP → export).
       Run standalone:
           python utils/email_validator.py emails.csv --output validated.csv
"""
from __future__ import annotations

import logging
import re
import smtplib
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Module-level MX cache (shared across all validator instances
# in the same process, so we never look up the same domain twice)
# ──────────────────────────────────────────────────────────────
_MX_CACHE: Dict[str, bool] = {}

EMAIL_REGEX = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._%+\-]*@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$"
)

# ──────────────────────────────────────────────────────────────
# Low-level helpers
# ──────────────────────────────────────────────────────────────

def _check_syntax(email: str) -> bool:
    """Return True if email passes the regex syntax check."""
    return bool(EMAIL_REGEX.match(email.strip()))


def _check_mx(domain: str) -> bool:
    """
    Return True if the domain has at least one MX record.
    Results are cached for the lifetime of the process.
    """
    if not domain:
        return False
    domain = domain.lower()
    if domain in _MX_CACHE:
        return _MX_CACHE[domain]

    try:
        import dns.resolver
        dns.resolver.resolve(domain, "MX")
        _MX_CACHE[domain] = True
        return True
    except Exception as exc:
        logger.debug("[VALIDATOR] MX lookup failed for %s: %s", domain, exc)
        _MX_CACHE[domain] = False
        return False


def _check_smtp(email: str) -> str:
    """
    Try an SMTP RCPT handshake to verify the mailbox exists.
    Returns: 'valid' | 'invalid' | 'unknown' | 'error'
    """
    if not email or "@" not in email:
        return "error"

    domain = email.split("@", 1)[1]
    try:
        import dns.resolver
        records = dns.resolver.resolve(domain, "MX")
        records = sorted(records, key=lambda r: r.preference)
        mx_host = str(records[0].exchange).rstrip(".")
    except Exception:
        return "error"

    try:
        server = smtplib.SMTP(timeout=5)
        server.connect(mx_host)
        server.helo("talentdirect-connect.com")
        server.mail("outreach@talentdirect-connect.com")
        code, _ = server.rcpt(email)
        server.quit()
        if code == 250:
            return "valid"
        if code == 550:
            return "invalid"
        return "unknown"
    except Exception:
        return "unknown"


# ──────────────────────────────────────────────────────────────
# Primary inline helper — called by offline_extractor & db.py
# ──────────────────────────────────────────────────────────────

def validate_email(
    email: str,
    check_mx: bool = True,
    check_smtp: bool = False,
) -> dict:
    """
    Validate a single email address and return a result dict:

        {
          "email":          "jane@techcorp.com",
          "syntax_valid":   True,
          "mx_valid":       True,
          "mailbox_status": "valid" | "invalid" | "unknown" | "error" | "skipped",
          "valid":          True,   # True iff syntax AND (mx if check_mx) pass
        }

    Parameters
    ----------
    email       : the address to validate
    check_mx    : perform a DNS MX lookup (default True)
    check_smtp  : perform an SMTP RCPT handshake (slow! default False)
    """
    email = (email or "").strip().lower()

    syntax_ok = _check_syntax(email)
    mx_ok     = True  # default to True if not checking

    if syntax_ok and check_mx:
        domain = email.split("@", 1)[1]
        mx_ok  = _check_mx(domain)

    mailbox_status = "skipped"
    if syntax_ok and mx_ok and check_smtp:
        mailbox_status = _check_smtp(email)

    valid = syntax_ok and mx_ok

    return {
        "email":          email,
        "syntax_valid":   syntax_ok,
        "mx_valid":       mx_ok,
        "mailbox_status": mailbox_status,
        "valid":          valid,
    }


# ──────────────────────────────────────────────────────────────
# Batch CSV pipeline (standalone use)
# ──────────────────────────────────────────────────────────────

class EmailListValidator:
    """
    Batch email list validator. Operates on a CSV file.

    Usage
    -----
        validator = EmailListValidator("emails.csv")
        validator.run(output_file="validated.csv", workers=20)
    """

    EMAIL_REGEX = r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$"

    def __init__(self, filepath: str) -> None:
        self.filepath        = filepath
        self.df              = None
        self.domain_mx_cache = _MX_CACHE   # share the module-level cache

    # ── I/O ──────────────────────────────────────────────────

    def load_data(self) -> None:
        """Load email data from CSV."""
        try:
            import pandas as pd
            self.df = pd.read_csv(self.filepath)
            logger.info("[VALIDATOR] Loaded %d rows from %s", len(self.df), self.filepath)
        except Exception as exc:
            logger.error("[VALIDATOR] Failed to load file: %s", exc)
            raise

    def export_results(self, output_path: str) -> None:
        """Export validated DataFrame to CSV."""
        self.df.to_csv(output_path, index=False)
        logger.info("[VALIDATOR] Results exported to %s", output_path)

    # ── Pipeline steps ────────────────────────────────────────

    def normalize_emails(self, column_name: str = "email") -> None:
        """Strip whitespace and lowercase the email column."""
        if column_name not in self.df.columns:
            raise ValueError(f"Column '{column_name}' not found in CSV.")
        self.df[column_name] = self.df[column_name].astype(str).str.strip().str.lower()
        logger.info("[VALIDATOR] Normalised '%s' column.", column_name)

    def validate_syntax(self, column_name: str = "email") -> None:
        """Add syntax_valid column using regex."""
        logger.info("[VALIDATOR] Starting syntax validation…")
        self.df["syntax_valid"] = self.df[column_name].apply(
            lambda x: bool(re.match(self.EMAIL_REGEX, x))
        )
        n = self.df["syntax_valid"].sum()
        logger.info("[VALIDATOR] Syntax: %d/%d valid.", n, len(self.df))

    def _has_mx(self, domain: str) -> bool:
        return _check_mx(domain)

    def validate_mx(self, column_name: str = "email", max_workers: int = 20) -> None:
        """Add mx_valid column via concurrent DNS lookups."""
        logger.info("[VALIDATOR] Starting MX validation…")
        self.df["domain"] = self.df[column_name].apply(
            lambda x: x.split("@")[-1] if isinstance(x, str) and "@" in x else None
        )
        unique_domains = self.df["domain"].dropna().unique()
        logger.info("[VALIDATOR] Checking %d unique domains…", len(unique_domains))

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(self._has_mx, d): d for d in unique_domains}
            done = 0
            for fut in as_completed(futures):
                done += 1
                if done % 100 == 0:
                    logger.info("[VALIDATOR] MX: %d/%d done", done, len(unique_domains))

        self.df["mx_valid"] = self.df["domain"].map(self.domain_mx_cache)
        n = self.df["mx_valid"].sum()
        logger.info("[VALIDATOR] MX: %d valid domains.", n)

    def verify_mailbox(self, email: str) -> str:
        return _check_smtp(email)

    def validate_mailbox(self, column_name: str = "email", max_workers: int = 20) -> None:
        """Add mailbox_status column via concurrent SMTP handshakes."""
        logger.info("[VALIDATOR] Starting SMTP mailbox validation…")
        emails = self.df[column_name].tolist()
        unique = list(set(emails))
        status_map: dict = {}

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(self.verify_mailbox, e): e for e in unique}
            done = 0
            for fut in as_completed(futures):
                email_addr = futures[fut]
                try:
                    status_map[email_addr] = fut.result()
                except Exception:
                    status_map[email_addr] = "error"
                done += 1
                if done % 100 == 0:
                    logger.info("[VALIDATOR] SMTP: %d/%d done", done, len(unique))

        self.df["mailbox_status"] = self.df[column_name].map(status_map)
        valid   = (self.df["mailbox_status"] == "valid").sum()
        invalid = (self.df["mailbox_status"] == "invalid").sum()
        logger.info("[VALIDATOR] SMTP: %d valid, %d invalid.", valid, invalid)

    def run(
        self,
        input_col: str = "email",
        output_file: str = "validated_emails.csv",
        workers: int = 20,
    ) -> None:
        """Run full pipeline: load → normalize → syntax → MX → SMTP → export."""
        self.load_data()
        self.normalize_emails(input_col)
        self.validate_syntax(input_col)
        self.validate_mx(input_col, max_workers=workers)
        self.validate_mailbox(input_col, max_workers=workers)
        self.export_results(output_file)

        # Export invalid-only CSV
        failed_file = output_file.replace(".csv", "_failed_mailbox.csv")
        failed_df   = self.df[self.df["mailbox_status"] == "invalid"]
        failed_df.to_csv(failed_file, index=False)
        logger.info("[VALIDATOR] %d invalid mailboxes → %s", len(failed_df), failed_file)

        total          = len(self.df)
        valid_syntax   = self.df["syntax_valid"].sum()
        valid_mx       = self.df["mx_valid"].sum()
        valid_mailbox  = (self.df["mailbox_status"] == "valid").sum()

        print("\n--- Validation Summary ---")
        print(f"Total Emails:   {total}")
        print(f"Syntax Valid:   {valid_syntax} ({valid_syntax/total*100:.1f}%)")
        print(f"MX Valid:       {valid_mx} ({valid_mx/total*100:.1f}%)")
        print(f"Mailbox Valid:  {valid_mailbox} ({valid_mailbox/total*100:.1f}%)")
        print(f"Output:         {output_file}")
        print(f"Failed:         {failed_file}")


# ──────────────────────────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Validate email lists for syntax, MX records, and SMTP mailbox."
    )
    parser.add_argument("input_file", help="Path to input CSV file.")
    parser.add_argument("--col",     default="email",                 help="Email column name.")
    parser.add_argument("--output",  default="validated_emails.csv",  help="Output CSV path.")
    parser.add_argument("--workers", type=int, default=50,            help="Concurrent workers.")

    args = parser.parse_args()
    EmailListValidator(args.input_file).run(
        input_col=args.col,
        output_file=args.output,
        workers=args.workers,
    )
