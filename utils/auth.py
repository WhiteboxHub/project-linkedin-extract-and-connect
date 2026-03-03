import os
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

def get_wbl_token_from_env() -> str:
    """
    Attempts to log into the WBL API directly using credentials found in the .env file.
    Returns the JWT token on success, or raises an Exception on failure.
    """
    load_dotenv()
    
    api_url = os.getenv("WBL_API_URL")
    email = os.getenv("WBL_EMAIL")
    password = os.getenv("WBL_PASSWORD")
    
    if not api_url or not email or not password:
        logger.error("[AUTH] Missing WBL_API_URL, WBL_EMAIL, or WBL_PASSWORD in .env")
        raise ValueError("Missing required WBL API credentials in .env file.")
        
    logger.info(f"[AUTH] Attempting to acquire fresh token for {email} ...")
    
    try:
        response = requests.post(
            f"{api_url}/login",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        token = data.get("access_token")
        if not token:
            raise ValueError("No access_token found in WBL login response.")
            
        logger.info("[AUTH] Successfully acquired new WBL token!")
        return token
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"[AUTH] Login rejected: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"[AUTH] Connection error during login: {e}")
        raise

def refresh_wbl_token_in_config() -> str:
    """
    Acquires a new token using .env credentials and saves it persistently to config.py.
    Returns the new token string on success.
    """
    # 1. Get the new token via `.env` credentials
    new_token = get_wbl_token_from_env()
    
    try:
        from config import WBL_CONFIG
    except ImportError:
        logger.error("[AUTH] Failed to import config.py. Make sure setup.py was run at least once.")
        raise
        
    # 2. Re-write the config file preserving old IDs
    content = f'''# ============================================
# WBL BOT CONFIGURATION
# Auto-Refreshed by utils/auth.py on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
# ============================================
# DO NOT COMMIT THIS FILE TO VERSION CONTROL
# ============================================

WBL_CONFIG = {{
    # API Configuration
    "API_URL": "{WBL_CONFIG.get('API_URL')}",
    "TOKEN": "{new_token}",
    
    # User Configuration
    "EMAIL": "{WBL_CONFIG.get('EMAIL')}",
    "EMPLOYEE_ID": {WBL_CONFIG.get('EMPLOYEE_ID')},
    "CANDIDATE_ID": {WBL_CONFIG.get('CANDIDATE_ID')},
    "CANDIDATE_NAME": "{WBL_CONFIG.get('CANDIDATE_NAME', '')}",
    
    # Job Configuration (for activity logging)
    "EXTRACTION_JOB_ID": {WBL_CONFIG.get('EXTRACTION_JOB_ID')},
    
    # Token Metadata
    "TOKEN_GENERATED_AT": "{datetime.now().isoformat()}",
    
    # Environment
    "ENVIRONMENT": "{WBL_CONFIG.get('ENVIRONMENT')}"
}}
'''

    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.py")
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"[AUTH] config.py has been successfully updated with the fresh token.")
    except Exception as e:
        logger.error(f"[AUTH] Failed writing new token to config.py: {e}")
        raise
        
    return new_token
