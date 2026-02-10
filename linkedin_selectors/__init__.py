# linkedin_selectors/__init__.py
"""Selector management package for LinkedIn Bot."""

from .selectors import SELECTORS, get_selector, get_fallback_selectors
from .validator import validate_selectors, SelectorValidator

__all__ = [
    'SELECTORS',
    'get_selector',
    'get_fallback_selectors',
    'validate_selectors',
    'SelectorValidator',
]
