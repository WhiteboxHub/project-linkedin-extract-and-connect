# modules/__init__.py
"""
LinkedIn Bot Modules Package

- BrowserManager: Browser lifecycle and health management
- DiscoveryModule: Message thread discovery and filtering
- WorkflowModule: Contact extraction workflow orchestration
- PersistenceModule: Database operations and data validation
- InboxScraper: LinkedIn Inbox message extraction (Phase 1 – live scraping)
- OfflineExtractor: Regex-based contact mining from raw JSON (Phase 2a – offline)
- SpacyNERExtractor: spaCy NER engine for contact fields (Phase 2b)
- GLiNERExtractor: GLiNER zero-shot NER engine for contact fields (Phase 2b)
- MessageContactExtractor: NER orchestrator with field-level fallback chain (Phase 2b)
"""

from .browser_manager import BrowserManager
from .discovery import DiscoveryModule
from .workflow import WorkflowModule
from .persistence import PersistenceModule
from .inbox_scraper import InboxScraper
from .offline_extractor import OfflineExtractor
from .nlp_spacy import SpacyNERExtractor
from .nlp_gliner import GLiNERExtractor
from .message_contact_extractor import MessageContactExtractor

__all__ = [
    'BrowserManager',
    'DiscoveryModule',
    'WorkflowModule',
    'PersistenceModule',
    'InboxScraper',
    'OfflineExtractor',
    'SpacyNERExtractor',
    'GLiNERExtractor',
    'MessageContactExtractor',
]

