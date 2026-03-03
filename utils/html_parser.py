from bs4 import BeautifulSoup
import logging
import re
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class LinkedInParser:
    """
    Parses raw LinkedIn HTML to extract data using BeautifulSoup.
    Reduces reliance on fragile Selenium selectors.
    """

    def __init__(self):
        pass

    def parse_profile(self, html_content: str) -> Dict[str, Any]:
        """
        Parse the main profile page HTML.
        """
        if not html_content:
            return {}

        soup = BeautifulSoup(html_content, 'lxml')
        data = {
            "name": self._extract_name(soup),
            "location": self._extract_location(soup),
            "company": self._extract_company(soup),
        }
        return data

    def parse_contact_modal(self, html_content: str) -> Dict[str, Any]:
        """
        Parse the contact info modal HTML.
        """
        if not html_content:
            return {}

        soup = BeautifulSoup(html_content, 'lxml')
        return {
            "email": self._extract_email(soup),
            "phone": self._extract_phone(soup),
            "linkedin_id": self._extract_linkedin_id(soup)
        }

    def _extract_name(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract name from h1/h2 tags."""
        # Try standard H1 name
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)
        
        # Fallback to visually hidden elements or specific classes if needed
        # But H1 is usually the safest bet for the main profile name
        return None

    def _extract_location(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract location looking for typical structure."""
        # Location is usually in the 'pv-text-details__left-panel' or similar container
        # We can look for the comma pattern often found in locations
        
        # Strategy 1: Look for text with comma in the top card section
        # Limit scope to top card to avoid false positives
        top_card = soup.find(class_='pv-top-card') or soup
        
        potential_locs = top_card.find_all(['span', 'div', 'p'])
        for el in potential_locs:
            text = el.get_text(strip=True)
            if ',' in text and 5 < len(text) < 100:
                # Basic heuristic: contains comma, reasonable length
                # Exclude potential company names if possible, but location usually comes after name
                return text
        
        return None

    def _extract_company(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract company from aria-labels or experience section."""
        # Strategy 1: 'Current company:' aria-label
        # <button aria-label="Current company: Acme Corp. Click to skip...">
        buttons = soup.find_all('button', attrs={'aria-label': True})
        for btn in buttons:
            label = btn['aria-label']
            if 'Current company:' in label:
                # "Current company: Acme Corp. Click to skip..."
                try:
                    return label.split('Current company:')[1].split('.')[0].strip()
                except:
                    pass
        
        # Strategy 2: Inline text
        # Often in 'inline-show-more-text' class
        # This is harder to pinpoint without more context, relying on aria-label is best for HTML parsing
        return None

    def _extract_email(self, soup: BeautifulSoup) -> Optional[str]:
        """Find mailto links."""
        link = soup.find('a', href=re.compile(r'^mailto:'))
        if link:
            # Remove 'mailto:' and params
            href = link.get('href')
            email = href.replace('mailto:', '').split('?')[0]
            return email.strip()
        
        # Fallback: Search text for email pattern
        # email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        # Loop through text nodes? Might be slow. `mailto` is robust.
        return None

    def _extract_phone(self, soup: BeautifulSoup) -> Optional[str]:
        """Find phone numbers in contact modal."""
        # Strategy: Look for the 'Phone' header and get following content
        # BeautifulSoup doesn't have XPath, so we iterate
        
        headers = soup.find_all('h3')
        for h3 in headers:
            if 'Phone' in h3.get_text(strip=True):
                # Look at siblings or parent's siblings
                # The structure is usually h3 -> sibling (ul/div) -> li/span
                
                # Finding the next sibling element
                sibling = h3.find_next_sibling()
                if sibling:
                    return sibling.get_text(strip=True)
                
                # If nested deeply, might need to go up and down
                # But typically it's close.
        
        # Fallback: Regex on the whole modal text for phone-like patterns?
        # Maybe risk of false positives.
        return None

    def _extract_linkedin_id(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract LinkedIn ID from profile links in contact modal."""
        # Look for links to linkedin.com/in/
        links = soup.find_all('a', href=re.compile(r'linkedin\.com/in/'))
        for link in links:
            href = link.get('href')
            if 'overlay' not in href: # Avoid the overlay itself if present
                # /in/username/
                try:
                    return href.split('/in/')[1].split('/')[0].split('?')[0]
                except:
                    pass
        return None
