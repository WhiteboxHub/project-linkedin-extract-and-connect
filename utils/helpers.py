# utils/helper.py
# ============================================
# UTILITY FUNCTIONS
# ============================================

def load_message(path):
    """Load message content from file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"Error loading message: {e}")
        return None

def truncate_string(text, max_length=50):
    """Truncate string with ellipsis."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def clean_linkedin_url(url):
    """Clean and normalize LinkedIn URL."""
    if not url:
        return None
    
    # Remove query parameters
    url = url.split('?')[0]
    
    # Remove trailing slash
    url = url.rstrip('/')
    
    return url