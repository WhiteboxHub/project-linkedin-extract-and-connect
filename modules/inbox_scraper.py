# modules/inbox_scraper.py
"""
LinkedIn Inbox Scraper — Phase 1 (Live Scraping)

Navigates to https://www.linkedin.com/messaging/, scrolls the conversation
list to discover all threads, opens each one, scrolls up to load older
messages, extracts every message bubble, and saves the result as a JSON
file under:
    data/raw_messages/<YYYY-MM-DD>/<conversation_id>.json
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import random
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LinkedIn Messaging CSS / XPath selectors
# (single place to update when LinkedIn changes its markup)
# ---------------------------------------------------------------------------
SEL = {
    # =========================
    # CONVERSATION SIDEBAR
    # =========================
    "conv_list":       "ul.msg-conversations-container__conversations-list",
    "conv_item":       "li.msg-conversation-listitem",
    "conv_name":       ".msg-conversation-listitem__participant-names .truncate",
    "conv_timestamp":  ".msg-conversation-listitem__time-stamp",
    # Sidebar snippet (last message preview)
    "conv_snippet":    "p.msg-conversation-card__message-snippet",

    # =========================
    # ACTIVE THREAD HEADER
    # =========================
    # Link to conversation partner's profile
    "thread_header":   "a.msg-thread__link-to-profile",
    # Partner name in header (preferred selector — LinkedIn redesign)
    "thread_name":     ".msg-entity-lockup__entity-title, .msg-thread__participant-names .truncate",
    # Old/fallback-only selector kept for reference
    "thread_name_old": ".msg-thread__participant-names .truncate",
    # Header subtitle (e.g., job title / industry)
    "thread_subtitle": ".msg-entity-lockup__entity-info",
    # Alias used in the latest scraper version
    "thread_subheader": ".msg-entity-lockup__entity-info",
    # Banner "You haven't connected with X"
    "thread_nonconnection_banner": ".msg-s-thread-actions-tray__item-nonconnection-banner",

    # =========================
    # MESSAGE LIST + EVENTS
    # =========================
    "msg_list":        "ul.msg-s-message-list-content",
    "msg_list_wrapper":"div.msg-s-message-list.full-width.scrollable",
    # Specific targeted message selector, backed up by the old broad <ul> > <li> rule per request
    "msg_event":       "li.msg-s-message-list__event, ul.msg-s-message-list-content > li",
    "msg_group":       ".msg-s-message-group, .msg-s-message-group__content-container",
    "msg_top_of_list": "li.msg-s-message-list__top-of-list",
    "msg_loader":      "li.msg-s-message-list__loader",
    "msg_typing_indicator": "li.msg-s-message-list__typing-indicator-container--without-seen-receipt",
    "msg_quick_replies_item": "li.msg-s-message-list__quick-replies-container",
    "msg_bottom_of_list": "li.msg-s-message-list__bottom-of-list",
    # Date heading inside message list (e.g., Today, Nov 5, 2025)
    "msg_date_heading": "time.msg-s-message-list__time-heading",

    # =========================
    # SENDER META (NAME, LINK, TIME)
    # =========================
    "msg_meta":        "div.msg-s-message-group__meta",
    # Alias for msg_meta (used in newer scraper versions)
    "msg_group_meta":  "div.msg-s-message-group__meta",
    # Sender name — most specific first, plain class as last fallback
    "msg_sender_name": (
        "div.msg-s-message-group__meta span.msg-s-message-group__name, "
        "div.msg-s-message-group__meta a.msg-s-message-group__name, "
        ".msg-s-message-group__name"
    ),
    # Stricter sender name (full class chain)
    "msg_sender_name_strict": "span.msg-s-message-group__profile-link.msg-s-message-group__name",
    # Old selector (kept for reference; do NOT rely on as primary)
    "msg_sender_name_old": "div.msg-s-message-group__meta a.msg-s-message-group__name",
    # Sender profile link inside event (profile picture/link)
    "msg_sender_link": (
        "a.msg-s-event-listitem__link, "
        ".msg-s-message-group__profile-link, "
        "a.app-aware-link[href*='/in/']"
    ),
    # Pronouns, e.g., (He/Him)
    "msg_sender_pronouns": "div.msg-s-message-group__meta span.t-12.t-black--light.t-normal",
    # Sender avatar / profile link (profile picture anchor)
    "msg_sender_avatar": "a.msg-s-event-listitem__link",
    # Timestamp
    "msg_timestamp":   "time.msg-s-message-group__timestamp, .msg-s-message-group__timestamp",

    # =========================
    # MESSAGE BODY TEXT
    # =========================
    "msg_with_indicator": "div.msg-s-event-with-indicator",
    "msg_content":     "div.msg-s-event__content",
    # Primary text body
    "msg_body":        (
        "p.msg-s-event-listitem__body, "
        "div.msg-s-event-listitem__unrolled-update-v2, "
        ".msg-s-event-listitem__body"
    ),
    # Strict body variant (with extra styling classes)
    "msg_body_strict": "p.msg-s-event-listitem__body.t-14.t-black--light.t-normal",
    # Combined primary + unrolled selector
    "msg_body_combined": "p.msg-s-event-listitem__body, div.msg-s-event-listitem__unrolled-update-v2",

    # =========================
    # EMBEDDED LINKEDIN CARDS (UNROLLED UPDATE)
    # =========================
    "msg_body_unrolled":  "div.msg-s-event-listitem__unrolled-update-v2",
    "msg_unrolled":       "div.msg-s-event-listitem__unrolled-update-v2",
    "msg_unrolled_card":  "div.msg-s-event-listitem__unrolled-update-v2.artdeco-card",
    "unrolled_article":       "article.update-components-article",
    "unrolled_article_large": "article.update-components-article.update-components-article--large-image-content",
    "unrolled_image_link":    "a.update-components-article__image-link",
    "unrolled_image":         "img.update-components-article__image",
    "unrolled_description_container": "div.update-components-article__description-container",
    "unrolled_meta_link":     "a.update-components-article__meta",
    "unrolled_title":         "div.update-components-article__title",
    "unrolled_subtitle":      "span.update-components-article__subtitle--inset",
    # Short aliases for the same unrolled card elements
    "card_title":    "div.update-components-article__title",
    "card_subtitle": "span.update-components-article__subtitle",
    "card_link":     "a.update-components-article__meta",
    "card_image":    "img.update-components-article__image",

    # =========================
    # EMBEDDED CONTACT LINKS (Inside msg_body)
    # =========================
    # Extract recruiter email from message signature
    "extracted_email":    "p.msg-s-event-listitem__body a[href^='mailto:']",
    # Extract recruiter LinkedIn profile from message
    "extracted_linkedin": "p.msg-s-event-listitem__body a[href*='linkedin.com/in/']",
    # Generic external links in message body
    "extracted_link":     "p.msg-s-event-listitem__body a[href^='http']",

    # =========================
    # PROFILE THUMBNAIL IN EVENT
    # =========================
    "event_profile_link": "a.msg-s-event-listitem__link",
    "event_profile_img":  "img.msg-s-event-listitem__profile-picture",

    # =========================
    # UTILITY
    # =========================
    # "Load earlier messages" button
    "load_earlier":    "button.msg-s-message-list__load-convo-trigger",
    # Safety: confirm we are on /messaging
    "messaging_nav":   "#messaging-nav",
}



class InboxScraper:
    """
    Extracts raw message data from every LinkedIn inbox conversation.

    Usage
    -----
    scraper = InboxScraper(
        driver=driver,
        wait=wait,
        human=human_behavior,
        candidate_id=101,
        candidate_email="me@example.com",
        output_dir="data/raw_messages",
        max_conversations=None,          # None = all
    )
    results = scraper.scrape_all_conversations()
    """

    MESSAGING_URL = "https://www.linkedin.com/messaging/"

    def __init__(
        self,
        driver,
        wait: WebDriverWait,
        human,
        candidate_id: int,
        candidate_email: str,
        output_dir: str = "data/raw_messages",
        max_conversations: Optional[int] = None,
    ) -> None:
        self.driver = driver
        self.wait = wait
        self.human = human
        self.candidate_id = candidate_id
        self.candidate_email = candidate_email
        self.output_dir = output_dir
        self.max_conversations = max_conversations

        self._today = date.today().isoformat()          # "YYYY-MM-DD"
        # Create a safe folder name from the email
        safe_email = re.sub(r"[^\w\-@.]", "_", candidate_email) if candidate_email else "unknown_user"
        self._date_dir = os.path.join(output_dir, self._today, safe_email)
        os.makedirs(self._date_dir, exist_ok=True)

        logger.info("InboxScraper initialised → output: %s", self._date_dir)

    # ------------------------------------------------------------------
    # Main orchestrator
    # ------------------------------------------------------------------

    def scrape_all_conversations(self) -> List[Dict[str, Any]]:
        """
        Full pipeline: navigate → scroll sidebar → iterate threads → save.

        Returns a list of conversation dicts that were saved.
        """
        self._navigate_to_messaging()

        total = self._scroll_conversation_list()
        logger.info("[INBOX] Conversation sidebar loaded — %d items visible", total)

        conversations = self._get_conversation_items()
        if self.max_conversations:
            conversations = conversations[: self.max_conversations]

        logger.info("[INBOX] Processing %d conversations", len(conversations))

        results: List[Dict[str, Any]] = []

        for idx, item in enumerate(conversations, start=1):
            conv_id = "unknown"
            try:
                conv_id = self._get_conversation_id(item)
                logger.info("[INBOX] (%d/%d) Opening conversation: %s", idx, len(conversations), conv_id)

                # Skip already-saved conversations
                out_path = self._json_path(conv_id)
                if os.path.exists(out_path):
                    logger.info("[INBOX]   → Skipped (already saved)")
                    continue

                if not self._click_conversation(item):
                    logger.warning("[INBOX]   → Could not click; skipping")
                    continue

                self.human.random_pause(1.5, 3.0)

                participant_name, participant_url = self._get_participant_info(item)
                self._load_earlier_messages()
                messages = self._extract_messages()

                data: Dict[str, Any] = {
                    "conversation_id": conv_id,
                    "participant_name": participant_name,
                    "participant_profile_url": participant_url,
                    "messages": messages,
                    "extraction_date": self._today,
                    "candidate_id": self.candidate_id,
                    "candidate_email": self.candidate_email,
                }

                saved_path = self._save_conversation(conv_id, data)
                results.append(data)
                logger.info(
                    "[INBOX]   → Saved %d messages → %s", len(messages), saved_path
                )

                # Human-like pause between conversations
                self._inter_conversation_pause()

            except StaleElementReferenceException:
                logger.warning("[INBOX] (%d) Stale element for conv %s — refreshing list", idx, conv_id)
                # Re-fetch the list and re-index (LinkedIn re-renders the sidebar)
                conversations = self._get_conversation_items()
                if self.max_conversations:
                    conversations = conversations[: self.max_conversations]

            except Exception as exc:  # noqa: BLE001
                logger.error("[INBOX] (%d) Error on conv %s: %s", idx, conv_id, exc, exc_info=True)
                continue

        logger.info("[INBOX] Done. %d conversations saved.", len(results))
        return results

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _navigate_to_messaging(self) -> None:
        """Go to the LinkedIn Messaging page and wait for it to load."""
        logger.info("[NAV] Navigating to %s", self.MESSAGING_URL)
        self.driver.get(self.MESSAGING_URL)

        try:
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, SEL["conv_list"]))
            )
            logger.info("[NAV] Messaging page loaded")
        except TimeoutException:
            logger.warning("[NAV] Conversation list not visible — page may still be loading")

        self.human.random_pause(2.0, 4.0)

    # ------------------------------------------------------------------
    # Sidebar scrolling
    # ------------------------------------------------------------------

    def _scroll_conversation_list(self, max_scrolls: int = 50) -> int:
        """
        Scroll the conversation sidebar until no new items appear or
        max_scrolls is reached.

        Returns the final number of conversation items visible.
        """
        try:
            container = self.driver.find_element(By.CSS_SELECTOR, SEL["conv_list"])
        except NoSuchElementException:
            logger.error("[SCROLL] Conversation list container not found")
            return 0

        prev_count = 0
        no_new_count = 0

        for scroll_n in range(max_scrolls):
            items = self.driver.find_elements(By.CSS_SELECTOR, SEL["conv_item"])
            cur_count = len(items)

            logger.debug("[SCROLL] Scroll #%d — %d conversations visible", scroll_n + 1, cur_count)

            # Stop if limit already reached
            if self.max_conversations and cur_count >= self.max_conversations:
                logger.info("[SCROLL] Reached max_conversations limit (%d)", self.max_conversations)
                break

            # Scroll the sidebar container
            self.driver.execute_script(
                "arguments[0].scrollTop += arguments[0].offsetHeight;", container
            )
            time.sleep(random.uniform(0.8, 1.5))

            if cur_count == prev_count:
                no_new_count += 1
                if no_new_count >= 3:
                    logger.info("[SCROLL] No new conversations after 3 scrolls — stopping")
                    break
            else:
                no_new_count = 0

            prev_count = cur_count

        final_items = self.driver.find_elements(By.CSS_SELECTOR, SEL["conv_item"])
        return len(final_items)

    # ------------------------------------------------------------------
    # Conversation list helpers
    # ------------------------------------------------------------------

    def _get_conversation_items(self):
        """Return all conversation <li> elements currently in the sidebar."""
        return self.driver.find_elements(By.CSS_SELECTOR, SEL["conv_item"])

    def _get_conversation_id(self, item) -> str:
        """
        Extract a stable conversation ID from the sidebar item.

        Strategy:
        1. Try the `data-conversation-id` attribute on the <li>.
        2. Fall back to the thread URL that is set when the item is active.
        3. Final fallback: hash the participant name.
        """
        # 1. data-conversation-id attribute
        cid = item.get_attribute("data-conversation-id")
        if cid:
            return cid

        # 2. Inspect any child link href for a numeric ID
        try:
            links = item.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute("href") or ""
                m = re.search(r"/messaging/thread/(\d[\w-]+)", href)
                if m:
                    return m.group(1)
        except Exception:
            pass

        # 3. Use participant name as fallback key
        try:
            name_el = item.find_element(By.CSS_SELECTOR, SEL["conv_name"])
            slug = re.sub(r"\W+", "_", name_el.text.strip().lower())
            return f"name_{slug}"
        except Exception:
            pass

        return f"unknown_{int(time.time())}"

    def _click_conversation(self, item) -> bool:
        """Click a conversation item to open it. Returns True on success."""
        try:
            self.human.human_click(self.driver, item)
            # Wait 1: message list container must appear
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, SEL["msg_list"]))
            )
            # Wait 2: at least one <p> body must have non-empty text
            # (LinkedIn lazy-renders message text — grabbing before this gives empty strings)
            try:
                self.wait.until(
                    EC.text_to_be_present_in_element(
                        (By.CSS_SELECTOR, "p.msg-s-event-listitem__body"), "a"
                    )
                )
            except TimeoutException:
                # Soft timeout — the conversation might be media-only or have a card only
                import time as _time
                _time.sleep(1.5)
            return True
        except TimeoutException:
            logger.warning("[CLICK] Thread message list didn't load in time")
            return False
        except Exception as exc:
            logger.warning("[CLICK] Failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Thread header — participant info
    # ------------------------------------------------------------------

    def _get_participant_info(self, item) -> Tuple[Optional[str], Optional[str]]:
        """
        Return (participant_name, participant_profile_url) from the open thread.

        IMPORTANT: We must scope the name lookup to the *active* thread only.
        LinkedIn keeps multiple thread headers in the DOM; a global find_element
        always returns the first one (which may belong to a different conversation).
        Strategy:
          1. Find the active thread container element.
          2. Look for the name INSIDE it — never globally.
          3. Fallback: read the name directly from the sidebar <li> item.
        """
        name: Optional[str] = None
        url: Optional[str] = None

        # ── Step 1: find the active/focused thread container ────────────────
        # LinkedIn marks the open thread with one of these wrappers
        thread_container = None
        for container_sel in [
            "div.msg-thread",
            "div.msg-s-message-list-container",
            "section.msg-thread",
        ]:
            try:
                thread_container = self.driver.find_element(By.CSS_SELECTOR, container_sel)
                break
            except NoSuchElementException:
                continue

        # ── Step 2: scope the name lookup inside the container ──────────────
        # Try h2 first (confirmed working), then SEL fallbacks
        search_root = thread_container if thread_container else self.driver
        for name_sel in [
            "h2.msg-entity-lockup__entity-title",          # confirmed working selector
            SEL["thread_name"],                             # .msg-entity-lockup__entity-title, ...
            ".msg-entity-lockup__entity-title",             # bare class fallback
            ".msg-thread__participant-names .truncate",     # legacy fallback
        ]:
            try:
                el = search_root.find_element(By.CSS_SELECTOR, name_sel)
                text = el.text.strip()
                if text:
                    name = text
                    break
            except NoSuchElementException:
                continue

        # ── Step 3: fallback — read the name from the sidebar item itself ───
        if not name:
            try:
                el = item.find_element(By.CSS_SELECTOR, SEL["conv_name"])
                text = el.text.strip()
                if text:
                    name = text
                    logger.debug("[PARTICIPANT] Used sidebar fallback for name: %r", name)
            except Exception:
                pass

        # ── Profile URL from the header link ────────────────────────────────
        try:
            link_root = thread_container if thread_container else self.driver
            link = link_root.find_element(By.CSS_SELECTOR, SEL["thread_header"])
            href = link.get_attribute("href") or ""
            if "/in/" in href:
                url = href.split("?")[0]  # strip query params
        except NoSuchElementException:
            pass

        logger.debug("[PARTICIPANT] name=%r  url=%r", name, url)
        return name, url

    # ------------------------------------------------------------------
    # Load earlier messages
    # ------------------------------------------------------------------

    def _load_earlier_messages(self, max_clicks: int = 30) -> None:
        """
        Click "Load earlier messages" until there are no more, or max_clicks
        is reached. Also scrolls the message panel to the top between clicks.
        """
        try:
            msg_list_el = self.driver.find_element(By.CSS_SELECTOR, SEL["msg_list"])
        except NoSuchElementException:
            logger.warning("[LOAD_EARLIER] Message list element not found")
            return

        for attempt in range(max_clicks):
            # Scroll the message panel to the top
            self.driver.execute_script(
                "arguments[0].scrollTop = 0;", msg_list_el
            )
            time.sleep(random.uniform(0.5, 1.0))

            try:
                btn = self.driver.find_element(By.CSS_SELECTOR, SEL["load_earlier"])
                if btn.is_displayed() and btn.is_enabled():
                    logger.debug("[LOAD_EARLIER] Clicking (attempt %d)", attempt + 1)
                    self.human.human_click(self.driver, btn)
                    time.sleep(random.uniform(1.0, 2.0))
                else:
                    break
            except NoSuchElementException:
                logger.debug("[LOAD_EARLIER] No more 'Load earlier' button after %d clicks", attempt)
                break
            except Exception as exc:
                logger.warning("[LOAD_EARLIER] Error: %s", exc)
                break

    # ------------------------------------------------------------------
    # Message extraction
    # ------------------------------------------------------------------

    def _extract_messages(self) -> List[Dict[str, Any]]:
        """
        Extract every message bubble from the currently open thread.

        Iterates ALL <li> elements in the message list so we can:
          1. Track date-heading <li>s (e.g. "Today", "Mon, Feb 3") to build a
             full "date + time" timestamp for each message.
          2. Classify each message event as incoming/outgoing via its DOM structure.

        Each returned message dict contains:
        {
            "sender_name":        str | None,
            "sender_profile_url": str | None,
            "is_outgoing":        bool,
            "date_heading":       str,          # e.g. "Mon, Feb 3" (LinkedIn date divider)
            "timestamp":          str | None,   # time from DOM, e.g. "8:44 AM"
            "msg_timestamp":      str | None,   # full "Mon, Feb 3 8:44 AM" (date + time)
            "text":               str,
            "card_text":          str,
            "email_links":        list[str],
            "linkedin_links":     list[str],
        }
        """
        messages: List[Dict[str, Any]] = []
        current_date: str = ""          # most recently seen date-heading text

        try:
            # By asking for both the event `li`s AND the time-heading `time` elements,
            # querySelectorAll returns them exactly in document order.
            # This completely bypasses the brittle `ul` parent class wrapper.
            selector = f"{SEL['msg_event']}, {SEL['msg_date_heading']}"
            all_els = self.driver.find_elements(By.CSS_SELECTOR, selector)
        except Exception as exc:
            logger.warning("[EXTRACT] Could not find message elements: %s", exc)
            return messages

        for el in all_els:
            try:
                tag = el.tag_name.lower()

                # ── Date heading ─────────────────────────────────────────
                if tag == "time":
                    current_date = el.text.strip()
                    logger.debug("[EXTRACT] Date heading: %r", current_date)
                    continue

                # ── Message event ─────────────────────────────────────────
                if tag == "li":
                    msg = self._parse_message_event(el, current_date=current_date)
                    if msg:
                        messages.append(msg)

            except StaleElementReferenceException:
                logger.debug("[EXTRACT] Stale element in message list — skipping item")
            except Exception as exc:
                logger.debug("[EXTRACT] Error parsing message event: %s", exc)

        logger.debug("[EXTRACT] Extracted %d message(s)", len(messages))
        return messages

    def _parse_message_event(self, event, current_date: str = "") -> Optional[Dict[str, Any]]:
        """
        Parse a single <li class='msg-s-message-list__event'> element.

        current_date: the date string from the most recent date-heading <li>
                      e.g. "Today", "Mon, Feb 3". Used to build a full timestamp.
        """
        # --- sender name ---
        sender_name: Optional[str] = None
        try:
            sender_name = event.find_element(
                By.CSS_SELECTOR, SEL["msg_sender_name"]
            ).text.strip() or None
        except NoSuchElementException:
            pass

        # --- sender profile URL ---
        sender_url: Optional[str] = None
        try:
            link = event.find_element(By.CSS_SELECTOR, SEL["msg_sender_link"])
            href = link.get_attribute("href") or ""
            if "/in/" in href:
                sender_url = href.split("?")[0]
        except NoSuchElementException:
            pass

        # --- timestamp ---
        # For INCOMING messages the timestamp lives INSIDE div.msg-s-message-group__meta.
        # For OUTGOING messages it lives directly inside the event li (no meta div).
        # We pick it up with the existing broad selector — it finds both positions —
        # then combine it with current_date to get a full sortable timestamp.
        timestamp: Optional[str] = None
        try:
            ts_el = event.find_element(By.CSS_SELECTOR, SEL["msg_timestamp"])
            timestamp = ts_el.text.strip() or None
        except NoSuchElementException:
            pass

        # Full timestamp = "<date_heading> <time>" e.g. "Mon, Feb 3 8:44 AM"
        msg_timestamp: Optional[str] = None
        if timestamp:
            msg_timestamp = f"{current_date} {timestamp}".strip() if current_date else timestamp
        elif current_date:
            msg_timestamp = current_date  # date only fallback

        # --- message body (real text only — NOT the LinkedIn card preview) ---
        body_text: Optional[str] = None
        card_text: Optional[str] = None

        # Stage 2 first: grab the LinkedIn card — we need it to filter it out below
        try:
            card_els = event.find_elements(By.CSS_SELECTOR, SEL["msg_body_unrolled"])
            ctexts = [c.text.strip() for c in card_els if c.text.strip()]
            if ctexts:
                card_text = "\n".join(ctexts)
        except Exception:
            pass

        # Stage 1: try <p>, <div>, <span> variants of the body class
        # LinkedIn has changed tag at least twice; try all three
        for tag_sel in [
            "p.msg-s-event-listitem__body",
            "div.msg-s-event-listitem__body",
            "span.msg-s-event-listitem__body",
        ]:
            try:
                els = event.find_elements(By.CSS_SELECTOR, tag_sel)
                texts = []
                for el in els:
                    t = el.text.strip()
                    if not t:
                        continue
                    # Skip if this element IS the card element
                    if card_text and t == card_text:
                        continue
                    # Strip card text from element text if it wraps both
                    if card_text and card_text in t:
                        t = t.replace(card_text, "").strip()
                    if t:
                        texts.append(t)
                if texts:
                    body_text = "\n".join(texts)
                    break
            except Exception:
                continue

        # Fallback: bare class selector (any tag) - subtract card text
        if not body_text:
            try:
                gen_els = event.find_elements(By.CSS_SELECTOR, ".msg-s-event-listitem__body")
                texts = []
                for g in gen_els:
                    t = g.text.strip()
                    if not t:
                        continue
                    if card_text:
                        if t == card_text:
                            continue
                        if card_text in t:
                            t = t.replace(card_text, "").strip()
                    if t:
                        texts.append(t)
                if texts:
                    body_text = "\n".join(texts)
            except Exception:
                pass

        # --- extract href links directly from <a> tags inside the message ---
        # These are more reliable than regex — mailto: and linkedin.com/in/ hrefs
        # are the raw values, unaffected by display text formatting.
        email_links: list = []
        linkedin_links: list = []
        try:
            for a in event.find_elements(By.CSS_SELECTOR, "p.msg-s-event-listitem__body a[href]"):
                href = (a.get_attribute("href") or "").strip()
                if href.startswith("mailto:"):
                    addr = href[len("mailto:"):].split("?")[0].strip()
                    if addr and addr not in email_links:
                        email_links.append(addr)
                elif "linkedin.com/in/" in href:
                    clean = href.split("?")[0].rstrip("/")
                    if clean and clean not in linkedin_links:
                        linkedin_links.append(clean)
        except Exception:
            pass

        # --- is_outgoing: DOM-level detection (most reliable signal) ---
        # LinkedIn renders `div.msg-s-message-group__meta` ONLY for INCOMING
        # messages (other person's) — it contains the sender name + profile link.
        # Your own (outgoing) messages never have this block.
        # So: meta present → recruiter message; meta absent → your message.
        is_outgoing: bool = True   # assume outgoing until we find the meta block
        try:
            meta_els = event.find_elements(By.CSS_SELECTOR, SEL["msg_meta"])
            if meta_els:
                is_outgoing = False  # sender meta found → this is an incoming message
        except Exception:
            pass

        # Skip events that have neither real text nor card text nor links
        if not body_text and not card_text and not email_links and not linkedin_links:
            return None

        return {
            "sender_name":        sender_name,
            "sender_profile_url": sender_url,
            "is_outgoing":        is_outgoing,     # True = candidate sent this
            "date_heading":       current_date,    # e.g. "Mon, Feb 3" (from date divider)
            "timestamp":          timestamp,        # raw time, e.g. "8:44 AM"
            "msg_timestamp":      msg_timestamp,    # full "Mon, Feb 3 8:44 AM" (unique per msg)
            "text":               body_text or "",
            "card_text":          card_text or "",
            "email_links":        email_links,
            "linkedin_links":     linkedin_links,
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _json_path(self, conv_id: str) -> str:
        """Return the output file path for a given conversation ID."""
        safe_id = re.sub(r"[^\w\-]", "_", str(conv_id))
        return os.path.join(self._date_dir, f"{safe_id}.json")

    def _save_conversation(self, conv_id: str, data: Dict[str, Any]) -> str:
        """Write conversation data as pretty-printed JSON. Returns the file path."""
        path = self._json_path(conv_id)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        return path

    # ------------------------------------------------------------------
    # Pacing
    # ------------------------------------------------------------------

    def _inter_conversation_pause(self) -> None:
        """Human-like random pause between opening conversations."""
        delay = random.uniform(2.0, 5.0)
        logger.debug("[PACE] Waiting %.1fs before next conversation", delay)
        time.sleep(delay)
