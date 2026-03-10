"""
run_inbox_extraction.py
=======================
Entry point for the LinkedIn Inbox Message Extractor (Phase 1 + Phase 2).

Phase 1 — Live Scraping (browser open)
    Login → navigate to /messaging/ → scroll sidebar → extract every
    conversation's message bubbles → save raw JSON per conversation.

Phase 2 — Offline Extraction (browser closed)
    Read raw JSON files → regex-mine emails & phones from message text →
    derive name / company → deduplicate → write JSON + CSV contacts.

Usage
-----
    # Run both phases (default)
    python run_inbox_extraction.py

    # Phase 1 only (scrape, skip contact extraction)
    python run_inbox_extraction.py --phase 1

    # Phase 2 only (process already-scraped JSON for today)
    python run_inbox_extraction.py --phase 2

    # Phase 2 for a specific date's JSON folder
    python run_inbox_extraction.py --phase 2 --date 2026-02-20

    # Limit to first 20 conversations, account index 0
    python run_inbox_extraction.py --max-conversations 20 --account 0

Output
------
    data/raw_messages/<YYYY-MM-DD>/<conversation_id>.json   ← Phase 1
    data/output/<YYYY-MM-DD>/inbox_contacts.json            ← Phase 2
    data/output/<YYYY-MM-DD>/inbox_contacts.csv             ← Phase 2
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
import random

import yaml

# Ensure the project root is on sys.path when run from any working directory
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from modules import BrowserManager, InboxScraper, OfflineExtractor
from stealth import HumanBehavior
from utils.exceptions import BrowserException
from utils.email_reporter import EmailReporter, RunSummary, AccountResult
from modules.persistence import PersistenceModule

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(_ROOT, "logs", "inbox_extraction.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("inbox_extraction")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ACCOUNTS_YAML = os.path.join(_ROOT, "credentials", "accounts.yaml")
DEFAULT_RAW_DIR    = os.path.join(_ROOT, "data", "raw_messages")  # Phase 1 output
DEFAULT_OUTPUT_DIR = os.path.join(_ROOT, "data", "output")        # Phase 2 output

# Delay range (seconds) between processing different accounts
INTER_ACCOUNT_DELAY = (15, 30)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_accounts(yaml_path: str) -> list[dict]:
    """Load and validate the accounts list from accounts.yaml."""
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"accounts.yaml not found: {yaml_path}")

    with open(yaml_path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    accounts = raw.get("accounts", [])
    if not accounts:
        raise ValueError("No accounts found in accounts.yaml — add at least one entry.")

    # Basic validation
    valid = []
    for i, acc in enumerate(accounts):
        if not acc.get("username") or not acc.get("password"):
            logger.warning("Account %d has missing credentials — skipping", i)
            continue
        if not acc.get("chrome_profile"):
            logger.warning("Account %d has no chrome_profile — skipping", i)
            continue
        valid.append(acc)

    if not valid:
        raise ValueError("No valid (fully-configured) accounts in accounts.yaml.")

    return valid


def _login(bot_driver, bot_wait, username: str, password: str, human: HumanBehavior) -> None:
    """
    Perform LinkedIn login using the same logic as LinkedInBot.login().
    Reused directly here to keep the entry point self-contained.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException

    logger.info("[LOGIN] Navigating to feed to check session for %s …", username)
    bot_driver.get("https://www.linkedin.com/feed/")
    time.sleep(5)

    # Check if already logged in
    login_indicators = [
        (By.ID, "global-nav"),
        (By.CLASS_NAME, "global-nav__me"),
        (By.CLASS_NAME, "global-nav__primary-items"),
    ]
    logged_in = any(
        bot_driver.find_elements(by, sel)
        for by, sel in login_indicators
    )

    if logged_in:
        logger.info("[LOGIN] Already logged in — session active")
        return

    logger.info("[LOGIN] No active session — performing full login …")
    bot_driver.get("https://www.linkedin.com/login")
    time.sleep(3)

    try:
        username_field = bot_wait.until(EC.presence_of_element_located((By.ID, "username")))
        human.human_type(username_field, username)
    except TimeoutException:
        logger.error("[LOGIN] Username field not found — check the login page")
        raise

    password_field = bot_wait.until(EC.presence_of_element_located((By.ID, "password")))
    human.human_type(password_field, password)

    submit = bot_driver.find_element(By.XPATH, "//button[@type='submit']")
    human.human_click(bot_driver, submit)

    # Wait for redirect to feed (up to 30 s)
    for _ in range(30):
        url = bot_driver.current_url
        if "feed" in url and "login" not in url:
            logger.info("[LOGIN] Login successful")
            return
        if "challenge" in url or "checkpoint" in url:
            logger.warning("[LOGIN] Verification required — complete it in the browser window")
            while "feed" not in bot_driver.current_url:
                time.sleep(3)
            return
        time.sleep(1)

    logger.warning("[LOGIN] Login may not have completed (timeout waiting for /feed/)")


def run_phase1(account: dict, args: argparse.Namespace, date_str: str) -> AccountResult:
    """Phase 1 — Live scraping: login, navigate, extract, save raw JSON."""
    username = account["username"]
    chrome_profile = account["chrome_profile"]
    candidate_id = account.get("candidate_id", 0)
    proxy = account.get("proxy")
    t_start = time.time()

    logger.info("=" * 60)
    logger.info("[PHASE 1] Account: %s  |  profile: %s", username, chrome_profile)
    logger.info("=" * 60)

    raw_dir = os.path.join(args.raw_dir, date_str)
    acc_errors: list[str] = []
    conversations = 0

    browser_mgr = BrowserManager(
        chrome_profile=chrome_profile,
        headless=False,
        proxy=proxy,
    )

    try:
        driver, wait = browser_mgr.start_browser()
        human = HumanBehavior()

        _login(driver, wait, username, account["password"], human)
        human.random_pause(2, 4)

        scraper = InboxScraper(
            driver=driver,
            wait=wait,
            human=human,
            candidate_id=candidate_id,
            candidate_email=username,
            output_dir=args.raw_dir,
            max_conversations=args.max_conversations,
        )

        results = scraper.scrape_all_conversations()
        conversations = len(results)
        logger.info(
            "[PHASE 1] Account %s — %d conversations saved to %s",
            username, conversations, raw_dir,
        )
        status = "done"

    except BrowserException as exc:
        logger.error("[PHASE 1] Browser error for %s: %s", username, exc)
        acc_errors.append(f"Browser error: {exc}")
        status = "partial"
    except Exception as exc:  # noqa: BLE001
        logger.error("[PHASE 1] Unexpected error for %s: %s", username, exc, exc_info=True)
        acc_errors.append(f"Unexpected error: {exc}")
        status = "failed"
    finally:
        browser_mgr.close_browser()

    return AccountResult(
        username        = username,
        status          = status,
        conversations   = conversations,
        runtime_seconds = time.time() - t_start,
        errors          = acc_errors,
    )


def run_phase2(args: argparse.Namespace, date_str: str, username: Optional[str] = None) -> list[dict]:
    """Phase 2 — Offline extraction: read raw JSON → mine contacts → save JSON+CSV.
    Returns the extracted contacts list so the email reporter can preview them.
    If username is provided, only extracts for that specific account.
    """
    raw_dir = os.path.join(args.raw_dir, date_str)
    if username:
        import re
        safe_email = re.sub(r"[^\w\-@.]", "_", username)
        user_raw_dir = os.path.join(raw_dir, safe_email)
        
        # Fallback for data scraped before the username subfolder was introduced
        if os.path.exists(user_raw_dir) and any(f.endswith('.json') for f in os.listdir(user_raw_dir)):
            raw_dir = user_raw_dir
        else:
            logger.info("[PHASE 2] Username folder %s not found or empty. Falling back to root date folder: %s", safe_email, raw_dir)

    output_dir = os.path.join(args.output_dir, date_str)

    logger.info("=" * 60)
    logger.info("[PHASE 2] Offline extraction for %s", username or "ALL")
    logger.info("  Input  : %s", raw_dir)
    logger.info("  Output : %s", output_dir)
    logger.info("=" * 60)

    if not os.path.exists(raw_dir) or not any(f.endswith('.json') for f in os.listdir(raw_dir)):
        logger.warning("[PHASE 2] Input directory not found or contains no JSON files: %s. Skipping.", raw_dir)
        return []

    extractor = OfflineExtractor(
        input_dir=raw_dir,
        output_dir=output_dir,
        date_str=date_str,
        exclude_personal=not args.include_personal,
    )

    result = extractor.run()
    # result is {"contacts": [...], "job_listings": [...]}
    contacts     = result.get("contacts", []) if isinstance(result, dict) else (result or [])
    job_listings = result.get("job_listings", []) if isinstance(result, dict) else []

    logger.info(
        "[PHASE 2] Done — %d unique contact(s), %d job listing(s) extracted",
        len(contacts), len(job_listings),
    )

    if contacts:
        logger.info("[PHASE 2] Sample contacts (first 3):")
        for c in contacts[:3]:
            logger.info(
                "  %-30s  %-35s  %s",
                c.get("full_name", ""),
                c.get("email", ""),
                c.get("company_name", ""),
            )

    if job_listings:
        logger.info("[PHASE 2] Sample job listings (first 3):")
        for jl in job_listings[:3]:
            logger.info(
                "  uid=%-40s  %r @ %r",
                jl.get("source_uid", ""),
                jl.get("raw_title", ""),
                jl.get("raw_company", ""),
            )

    return result  # forward the full dict to the caller



# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LinkedIn Inbox Message Extractor — Phase 1 (scraping) + Phase 2 (offline contact extraction)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2],
        default=None,
        help="1=scrape only, 2=offline extract only, omit=run both (default: both)",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="Date folder to process for Phase 2 (default: today)",
    )
    parser.add_argument(
        "--max-conversations",
        type=int,
        default=None,
        metavar="N",
        help="Phase 1: limit to first N conversations per account (default: all)",
    )
    parser.add_argument(
        "--account",
        type=int,
        default=None,
        metavar="INDEX",
        help="Phase 1: process only the account at this zero-based index (default: all)",
    )
    parser.add_argument(
        "--raw-dir",
        type=str,
        default=DEFAULT_RAW_DIR,
        help=f"Root directory for raw Phase 1 JSON files (default: {DEFAULT_RAW_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Root directory for Phase 2 contact output (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--accounts-yaml",
        type=str,
        default=ACCOUNTS_YAML,
        help=f"Path to accounts.yaml (default: {ACCOUNTS_YAML})",
    )
    parser.add_argument(
        "--include-personal",
        action="store_true",
        default=False,
        help="Phase 2: include gmail/yahoo/etc addresses (excluded by default)",
    )
    parser.add_argument(
        "--no-email",
        action="store_true",
        default=False,
        help="Skip sending the SMTP email report after the run",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Run scraping and extraction locally, but SKIP saving to the database/API",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    from datetime import date as _date
    date_str = args.date or _date.today().isoformat()

    # Ensure logs and output dirs exist
    os.makedirs(os.path.join(_ROOT, "logs"), exist_ok=True)
    os.makedirs(args.raw_dir, exist_ok=True)
    os.makedirs(args.output_dir, exist_ok=True)

    run_p1 = args.phase in (None, 1)   # None means both
    run_p2 = args.phase in (None, 2)

    logger.info("LinkedIn Inbox Extractor — date: %s", date_str)
    logger.info("  Phase           : %s", args.phase or "1 + 2")
    logger.info("  Raw dir         : %s", args.raw_dir)
    logger.info("  Output dir      : %s", args.output_dir)
    logger.info("  Max convs/acct  : %s", args.max_conversations or "all")
    logger.info("  Account filter  : %s", args.account if args.account is not None else "all")
    logger.info("  Include personal: %s", args.include_personal)

    # ---------------------------------------------------------------- Execute
    try:
        accounts = load_accounts(args.accounts_yaml)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)

    if args.account is not None:
        if args.account >= len(accounts):
            logger.error(
                "--account %d is out of range (%d valid accounts)",
                args.account, len(accounts),
            )
            sys.exit(1)
        accounts = [accounts[args.account]]

    logger.info("[RUN] Processing %d account(s) …", len(accounts))

    run_summary = RunSummary(date_str=date_str)
    all_extracted_contacts: list[dict] = []

    for i, account in enumerate(accounts):
        username = account["username"]
        acc_result = None

        # --- Phase 1: Scrape ---
        if run_p1:
            acc_result = run_phase1(account, args, date_str)

        # --- Phase 2: Extract ---
        if run_p2:
            result = run_phase2(args, date_str, username=username)
            # run_phase2 now returns {"contacts": [...], "job_listings": [...]}
            # Graceful fallback if still returns a plain list (e.g. old code path)
            if isinstance(result, dict):
                contacts     = result.get("contacts", [])
                job_listings = result.get("job_listings", [])
            else:
                contacts     = result or []
                job_listings = None   # triggers legacy 1-listing-per-contact path

            all_extracted_contacts.extend(contacts)
            
            # --- API Submission ---
            inserted_count = 0
            if contacts or job_listings:
                if args.dry_run:
                    logger.info(
                        "[DRY RUN] Would have inserted %d contacts, %d job listings for %s. Database skipped.",
                        len(contacts),
                        len(job_listings) if job_listings else 0,
                        username,
                    )
                else:
                    try:
                        employee_id  = account.get("employee_id", 0)
                        candidate_id = account.get("candidate_id", 0)
                        persistence  = PersistenceModule(employee_id, candidate_id)
                        inserted_count = persistence.bulk_insert_contacts(
                            contacts,
                            job_listings=job_listings,
                        )
                        logger.info(
                            "[API] Inserted %d contacts, %d job listings for %s",
                            inserted_count,
                            len(job_listings) if job_listings else 0,
                            username,
                        )
                    except Exception as e:
                        logger.error("[API] Failed to insert contacts for %s: %s", username, e)
                        if acc_result:
                            acc_result.errors.append(f"API Insert failed: {e}")

            if acc_result:
                acc_result.contacts_found = len(contacts)
                acc_result.api_inserted = inserted_count
            else:
                # Phase 2-only run, so we synthesize a successful AccountResult
                acc_result = AccountResult(
                    username=username, 
                    status="done", 
                    contacts_found=len(contacts),
                    api_inserted=inserted_count,
                    conversations=0,
                    runtime_seconds=0.0,
                    errors=[]
                )


        if acc_result:
            run_summary.add_account(acc_result)

        # Inter-account delay (only if not the last account)
        if i < len(accounts) - 1:
            delay = random.uniform(*INTER_ACCOUNT_DELAY)
            logger.info("Waiting %.0fs before next account …", delay)
            time.sleep(delay)

    logger.info("[RUN] All accounts processed.")

    # ---------------------------------------------------------------- Email report
    if not args.no_email:
        run_summary.contacts_sample = all_extracted_contacts[:20]

        # Phase 2 output CSV
        csv_path = os.path.join(args.output_dir, date_str, "inbox_contacts.csv")
        if os.path.exists(csv_path):
            run_summary.csv_path = csv_path

        EmailReporter().send_run_report(run_summary)
    else:
        logger.info("[EMAIL] Skipped (--no-email flag)")

    logger.info("Done.")


if __name__ == "__main__":
    main()
