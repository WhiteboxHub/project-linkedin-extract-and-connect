# modules/__init__.py
"""
LinkedIn Bot Modules Package

Modular architecture for LinkedIn bot with clear separation of concerns:
- BrowserManager: Browser lifecycle and health management
- DiscoveryModule: Message thread discovery and filtering
- WorkflowModule: Contact extraction workflow orchestration
- PersistenceModule: Database operations and data validation
"""

from .browser_manager import BrowserManager
from .discovery import DiscoveryModule
from .workflow import WorkflowModule
from .persistence import PersistenceModule

__all__ = [
    'BrowserManager',
    'DiscoveryModule',
    'WorkflowModule',
    'PersistenceModule',
]

