# utils/email_reporter.py
"""
SMTP Email Report System for the LinkedIn Extraction Bot.

Sends a rich HTML summary email after each bot run, including:
  - Overall stats: accounts processed, total contacts, API inserts
  - Per-account breakdown table
  - Top contacts preview (first 10)
  - Error log excerpt
  - Attached CSV of all contacts

Configuration (via .env):
  SMTP_HOST       — e.g. smtp.gmail.com  (default: smtp.gmail.com)
  SMTP_PORT       — e.g. 587             (default: 587)
  SMTP_USER       — your email address
  SMTP_PASSWORD   — app password (Gmail) or real password
  SMTP_FROM       — display name + address, e.g. "LinkedIn Bot <you@gmail.com>"
  SMTP_TO         — comma-separated recipient list
  SMTP_ENABLED    — true / false          (default: true)

Usage:
    from utils.email_reporter import EmailReporter, RunSummary, AccountResult

    summary = RunSummary(date_str="2026-02-27")
    summary.add_account(AccountResult(
        username="user@gmail.com",
        status="done",
        conversations=58,
        contacts_found=22,
        api_inserted=20,
        api_duplicates=2,
        api_failed=0,
        errors=[],
    ))
    summary.contacts_sample = [...]          # list of contact dicts
    summary.csv_path = "data/output/.../inbox_contacts.csv"
    EmailReporter().send_run_report(summary)
"""

from __future__ import annotations

import csv
import io
import logging
import os
import smtplib
import time
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class AccountResult:
    """Stores the per-account run outcome."""
    username:        str
    status:          str   # "done" | "partial" | "failed" | "skipped"
    conversations:   int   = 0
    contacts_found:  int   = 0
    api_inserted:    int   = 0
    api_duplicates:  int   = 0
    api_failed:      int   = 0
    runtime_seconds: float = 0.0
    errors:          List[str] = field(default_factory=list)


@dataclass
class RunSummary:
    """Aggregated summary of a complete bot run."""
    date_str:        str
    start_time:      float            = field(default_factory=time.time)
    accounts:        List[AccountResult] = field(default_factory=list)
    contacts_sample: List[dict]       = field(default_factory=list)
    csv_path:        Optional[str]    = None
    global_errors:   List[str]        = field(default_factory=list)

    def add_account(self, result: AccountResult) -> None:
        self.accounts.append(result)

    # ── Computed properties ──────────────────────────────────────────────

    @property
    def total_accounts(self) -> int:
        return len(self.accounts)

    @property
    def accounts_done(self) -> int:
        return sum(1 for a in self.accounts if a.status in ("done", "partial"))

    @property
    def accounts_failed(self) -> int:
        return sum(1 for a in self.accounts if a.status == "failed")

    @property
    def total_contacts(self) -> int:
        return sum(a.contacts_found for a in self.accounts)

    @property
    def total_inserted(self) -> int:
        return sum(a.api_inserted for a in self.accounts)

    @property
    def total_duplicates(self) -> int:
        return sum(a.api_duplicates for a in self.accounts)

    @property
    def total_api_failed(self) -> int:
        return sum(a.api_failed for a in self.accounts)

    @property
    def runtime_str(self) -> str:
        secs = int(time.time() - self.start_time)
        m, s = divmod(secs, 60)
        return f"{m}m {s}s"

    @property
    def all_errors(self) -> List[str]:
        errors = list(self.global_errors)
        for a in self.accounts:
            for e in a.errors:
                errors.append(f"[{a.username}] {e}")
        return errors


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

def _status_badge(status: str) -> str:
    colours = {
        "done":    ("#d4edda", "#155724", "✅ Done"),
        "partial": ("#fff3cd", "#856404", "⚠️ Partial"),
        "failed":  ("#f8d7da", "#721c24", "❌ Failed"),
        "skipped": ("#e2e3e5", "#383d41", "⏭️ Skipped"),
    }
    bg, fg, label = colours.get(status, ("#e2e3e5", "#383d41", status.title()))
    return (
        f'<span style="background:{bg};color:{fg};padding:2px 8px;'
        f'border-radius:12px;font-size:12px;font-weight:600;">{label}</span>'
    )


def build_html_report(summary: RunSummary) -> str:
    """Return a fully-formed HTML email body."""

    # ── Colour coding for header banner ─────────────────────────────────
    if summary.accounts_failed == 0:
        banner_bg = "#1a73e8"
    elif summary.accounts_failed < summary.total_accounts:
        banner_bg = "#f9ab00"
    else:
        banner_bg = "#d93025"

    # ── Per-account table rows ───────────────────────────────────────────
    acc_rows = ""
    for a in summary.accounts:
        err_cell = (
            f'<span style="color:#dc3545">{len(a.errors)} error(s)</span>'
            if a.errors else
            '<span style="color:#28a745">None</span>'
        )
        acc_rows += f"""
        <tr>
          <td style="padding:8px 12px;">{a.username}</td>
          <td style="padding:8px 12px;text-align:center;">{_status_badge(a.status)}</td>
          <td style="padding:8px 12px;text-align:center;">{a.conversations}</td>
          <td style="padding:8px 12px;text-align:center;">{a.contacts_found}</td>
          <td style="padding:8px 12px;text-align:center;color:#28a745;font-weight:600;">{a.api_inserted}</td>
          <td style="padding:8px 12px;text-align:center;color:#17a2b8;">{a.api_duplicates}</td>
          <td style="padding:8px 12px;text-align:center;">{a.api_failed}</td>
          <td style="padding:8px 12px;text-align:center;">{err_cell}</td>
        </tr>"""

    # ── Top contacts preview ─────────────────────────────────────────────
    preview_rows = ""
    for c in summary.contacts_sample[:10]:
        preview_rows += f"""
        <tr>
          <td style="padding:6px 10px;">{c.get('full_name') or c.get('sender_name') or '—'}</td>
          <td style="padding:6px 10px;">{c.get('company') or c.get('company_name') or '—'}</td>
          <td style="padding:6px 10px;">{c.get('job_title') or '—'}</td>
          <td style="padding:6px 10px;">{c.get('email') or '—'}</td>
          <td style="padding:6px 10px;">{c.get('phone') or '—'}</td>
        </tr>"""
    if not preview_rows:
        preview_rows = '<tr><td colspan="5" style="padding:10px;text-align:center;color:#6c757d;">No contacts extracted</td></tr>'

    # ── Error log ────────────────────────────────────────────────────────
    all_errors = summary.all_errors
    error_section = ""
    if all_errors:
        error_lines = "\n".join(f"  • {e}" for e in all_errors[:20])
        if len(all_errors) > 20:
            error_lines += f"\n  … and {len(all_errors) - 20} more (see log file)"
        error_section = f"""
        <h3 style="color:#dc3545;margin-top:30px;">⚠️ Errors ({len(all_errors)})</h3>
        <pre style="background:#fff5f5;border:1px solid #f5c6cb;border-radius:6px;
                    padding:14px;font-size:12px;color:#721c24;white-space:pre-wrap;">{error_lines}</pre>"""

    # ── API summary boxes ────────────────────────────────────────────────
    def stat_box(label, value, colour):
        return f"""
        <div style="background:#f8f9fa;border-left:4px solid {colour};
                    border-radius:6px;padding:12px 16px;text-align:center;min-width:100px;">
          <div style="font-size:28px;font-weight:700;color:{colour};">{value}</div>
          <div style="font-size:12px;color:#6c757d;margin-top:2px;">{label}</div>
        </div>"""

    stat_boxes = "".join([
        stat_box("Contacts Found",      summary.total_contacts,    "#1a73e8"),
        stat_box("API Inserted",        summary.total_inserted,    "#28a745"),
        stat_box("Duplicates Skipped",  summary.total_duplicates,  "#17a2b8"),
        stat_box("API Insert Failures", summary.total_api_failed,  "#dc3545"),
        stat_box("Accounts Run",        f"{summary.accounts_done}/{summary.total_accounts}", "#6f42c1"),
    ])

    # ── Full HTML ────────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LinkedIn Bot Report — {summary.date_str}</title></head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:'Segoe UI',Arial,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f2f5;padding:20px 0;">
<tr><td align="center">
<table width="680" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;
       overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.10);">

  <!-- BANNER -->
  <tr><td style="background:{banner_bg};padding:24px 32px;">
    <h1 style="margin:0;color:#fff;font-size:22px;">🤖 LinkedIn Extraction Bot</h1>
    <p style="margin:6px 0 0;color:rgba(255,255,255,.85);font-size:14px;">
      Run Report &nbsp;|&nbsp; {summary.date_str}
    </p>
  </td></tr>

  <!-- STAT BOXES -->
  <tr><td style="padding:24px 32px 0;">
    <div style="display:flex;gap:12px;flex-wrap:wrap;">
      {stat_boxes}
    </div>
  </td></tr>

  <!-- PER-ACCOUNT TABLE -->
  <tr><td style="padding:24px 32px 0;">
    <h2 style="font-size:16px;color:#333;margin:0 0 12px;">Per-Account Breakdown</h2>
    <table width="100%" cellpadding="0" cellspacing="0"
           style="border-collapse:collapse;font-size:13px;">
      <thead>
        <tr style="background:#f8f9fa;">
          <th style="padding:10px 12px;text-align:left;border-bottom:2px solid #dee2e6;">Account</th>
          <th style="padding:10px 12px;text-align:center;border-bottom:2px solid #dee2e6;">Status</th>
          <th style="padding:10px 12px;text-align:center;border-bottom:2px solid #dee2e6;">Convs</th>
          <th style="padding:10px 12px;text-align:center;border-bottom:2px solid #dee2e6;">Contacts</th>
          <th style="padding:10px 12px;text-align:center;border-bottom:2px solid #dee2e6;">Inserted</th>
          <th style="padding:10px 12px;text-align:center;border-bottom:2px solid #dee2e6;">Dupes</th>
          <th style="padding:10px 12px;text-align:center;border-bottom:2px solid #dee2e6;">Failed</th>
          <th style="padding:10px 12px;text-align:center;border-bottom:2px solid #dee2e6;">Errors</th>
        </tr>
      </thead>
      <tbody>{acc_rows}
      </tbody>
    </table>
  </td></tr>

  <!-- TOP CONTACTS PREVIEW -->
  <tr><td style="padding:24px 32px 0;">
    <h2 style="font-size:16px;color:#333;margin:0 0 12px;">
      Top Contacts Preview (first 10)
    </h2>
    <table width="100%" cellpadding="0" cellspacing="0"
           style="border-collapse:collapse;font-size:12px;">
      <thead>
        <tr style="background:#f8f9fa;">
          <th style="padding:8px 10px;text-align:left;border-bottom:2px solid #dee2e6;">Name</th>
          <th style="padding:8px 10px;text-align:left;border-bottom:2px solid #dee2e6;">Company</th>
          <th style="padding:8px 10px;text-align:left;border-bottom:2px solid #dee2e6;">Job Title</th>
          <th style="padding:8px 10px;text-align:left;border-bottom:2px solid #dee2e6;">Email</th>
          <th style="padding:8px 10px;text-align:left;border-bottom:2px solid #dee2e6;">Phone</th>
        </tr>
      </thead>
      <tbody>{preview_rows}
      </tbody>
    </table>
  </td></tr>

  {error_section and f'<tr><td style="padding:0 32px;">{error_section}</td></tr>' or ''}

  <!-- FOOTER -->
  <tr><td style="padding:24px 32px;background:#f8f9fa;border-top:1px solid #dee2e6;
                  font-size:11px;color:#6c757d;text-align:center;">
    LinkedIn Extraction Bot &nbsp;·&nbsp; Auto-generated report &nbsp;·&nbsp; {summary.date_str}<br>
    Full CSV attached · Detailed logs in <code>logs/extraction_debug.log</code>
  </td></tr>

</table>
</td></tr>
</table>
</body></html>"""
    return html


# ---------------------------------------------------------------------------
# EmailReporter
# ---------------------------------------------------------------------------

class EmailReporter:
    """
    Sends HTML run-summary emails via SMTP.

    Config is read from environment variables (loaded from .env automatically).
    All errors are logged as warnings rather than raised, so a broken SMTP
    config can never crash the bot run.
    """

    def __init__(self) -> None:
        self.enabled  = os.getenv("SMTP_ENABLED", "true").lower() == "true"
        self.host     = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.port     = int(os.getenv("SMTP_PORT", "587"))
        self.user     = os.getenv("SMTP_USER", "")
        self.password = os.getenv("SMTP_PASSWORD", "")
        self.from_    = os.getenv("SMTP_FROM", self.user)
        self.to_raw   = os.getenv("SMTP_TO", "")

    # ── Public API ────────────────────────────────────────────────────────

    def send_run_report(self, summary: RunSummary) -> bool:
        """
        Build and send the HTML run-summary email.

        Returns True if the email was sent, False otherwise.
        Never raises.
        """
        if not self.enabled:
            logger.info("[EMAIL] SMTP_ENABLED=false — skipping email report")
            return False

        if not self._config_valid():
            return False

        recipients = [r.strip() for r in self.to_raw.split(",") if r.strip()]
        if not recipients:
            logger.warning("[EMAIL] SMTP_TO is empty — no recipients configured")
            return False

        subject = (
            f"LinkedIn Bot Report — {summary.date_str} — "
            f"{summary.total_contacts} contact(s) extracted"
        )

        # Build message
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"]    = self.from_
        msg["To"]      = ", ".join(recipients)

        # HTML body
        html_body = build_html_report(summary)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # CSV attachment
        csv_attached = self._attach_csv(msg, summary)

        # Send
        return self._send(msg, recipients, csv_attached)

    def test_connection(self) -> bool:
        """
        Quick smoke-test: connect and authenticate only (no email sent).
        Useful for verifying credentials after first setup.
        """
        if not self._config_valid():
            return False
        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as srv:
                srv.ehlo()
                srv.starttls()
                srv.login(self.user, self.password)
            print(f"[EMAIL] Connection test OK — {self.user} @ {self.host}:{self.port}")
            return True
        except Exception as exc:
            print(f"[EMAIL] Connection test FAILED: {exc}")
            return False

    # ── Private helpers ───────────────────────────────────────────────────

    def _config_valid(self) -> bool:
        missing = []
        if not self.host:     missing.append("SMTP_HOST")
        if not self.user:     missing.append("SMTP_USER")
        if not self.password: missing.append("SMTP_PASSWORD")
        if not self.to_raw:   missing.append("SMTP_TO")
        if missing:
            logger.warning(
                "[EMAIL] Missing SMTP config: %s — add to .env to enable reports",
                ", ".join(missing),
            )
            return False
        return True

    def _attach_csv(self, msg: MIMEMultipart, summary: RunSummary) -> bool:
        """Attach CSV file if the path exists, fallback to in-memory CSV."""
        # Try the file path first
        if summary.csv_path and os.path.exists(summary.csv_path):
            try:
                with open(summary.csv_path, "rb") as fh:
                    data = fh.read()
                filename = os.path.basename(summary.csv_path)
                part = MIMEBase("application", "octet-stream")
                part.set_payload(data)
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
                msg.attach(part)
                logger.debug("[EMAIL] Attached CSV file: %s", filename)
                return True
            except Exception as exc:
                logger.warning("[EMAIL] Could not attach CSV file: %s", exc)

        # Build an in-memory CSV from the contacts sample as fallback
        if summary.contacts_sample:
            try:
                buf = io.StringIO()
                fields = ["full_name", "company", "job_title", "email", "phone", "location"]
                writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                for c in summary.contacts_sample:
                    row = {
                        "full_name": c.get("full_name") or c.get("sender_name", ""),
                        "company":   c.get("company") or c.get("company_name", ""),
                        "job_title": c.get("job_title", ""),
                        "email":     c.get("email", ""),
                        "phone":     c.get("phone", ""),
                        "location":  c.get("location") or c.get("city", ""),
                    }
                    writer.writerow(row)
                csv_bytes = buf.getvalue().encode("utf-8")
                part = MIMEBase("text", "csv")
                part.set_payload(csv_bytes)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="contacts_{summary.date_str}.csv"',
                )
                msg.attach(part)
                return True
            except Exception as exc:
                logger.warning("[EMAIL] Could not build in-memory CSV: %s", exc)

        return False

    def _send(self, msg: MIMEMultipart, recipients: list[str], csv_attached: bool) -> bool:
        """Connect to SMTP and send. Returns True on success."""
        try:
            logger.info("[EMAIL] Connecting to %s:%d …", self.host, self.port)
            with smtplib.SMTP(self.host, self.port, timeout=30) as srv:
                srv.ehlo()
                srv.starttls()
                srv.ehlo()
                srv.login(self.user, self.password)
                srv.sendmail(self.from_, recipients, msg.as_string())
            logger.info(
                "[EMAIL] Report sent to %s (CSV: %s)",
                ", ".join(recipients),
                "attached" if csv_attached else "not attached",
            )
            return True
        except smtplib.SMTPAuthenticationError:
            logger.warning(
                "[EMAIL] SMTP authentication failed — check SMTP_USER / SMTP_PASSWORD. "
                "For Gmail use an App Password (not your account password)."
            )
        except smtplib.SMTPConnectError as exc:
            logger.warning("[EMAIL] Cannot connect to %s:%d — %s", self.host, self.port, exc)
        except smtplib.SMTPRecipientsRefused as exc:
            logger.warning("[EMAIL] Recipients refused: %s", exc)
        except Exception as exc:
            logger.warning("[EMAIL] Unexpected SMTP error: %s", exc)
        return False
