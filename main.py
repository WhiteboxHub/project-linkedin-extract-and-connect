# main.py
# ============================================
# LINKEDIN CONTACT EXTRACTION - ENTRY POINT
# WITH FULL DEBUG LOGGING
# ============================================

import time
import random
import yaml
import logging
import sys
import os

# ============================================
# LOGGING SETUP - DEBUG LEVEL
# ============================================

os.makedirs('logs', exist_ok=True)

# Create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# File handler (DEBUG level - captures everything)
file_handler = logging.FileHandler('logs/extraction_debug.log', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Console handler (INFO level)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# Root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)

# ============================================
# IMPORTS
# ============================================

logger.info("Importing modules...")

try:
    from utils.linkedin_bot import LinkedInBot
    logger.info("LinkedInBot imported successfully")
except Exception as e:
    logger.error(f"Failed to import LinkedInBot: {e}", exc_info=True)
    sys.exit(1)

# ============================================
# LOADERS
# ============================================

def load_accounts(path):
    """Load accounts from YAML."""
    logger.info(f"Loading accounts from: {path}")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        accounts = data.get('accounts', [])
        logger.info(f"Loaded {len(accounts)} accounts")
        return accounts
    except FileNotFoundError:
        logger.error(f"File not found: {path}")
        return []
    except Exception as e:
        logger.error(f"Error loading accounts: {e}", exc_info=True)
        return []

def load_wbl_config():
    """Load WBL config from config.py."""
    logger.info("Loading WBL config from config.py...")
    try:
        from config import WBL_CONFIG
        logger.info(f"WBL Config loaded successfully")
        logger.info(f"   API_URL: {WBL_CONFIG.get('API_URL')}")
        logger.info(f"   EMPLOYEE_ID: {WBL_CONFIG.get('EMPLOYEE_ID')}")
        logger.info(f"   CANDIDATE_ID: {WBL_CONFIG.get('CANDIDATE_ID')}")
        logger.info(f"   EXTRACTION_JOB_ID: {WBL_CONFIG.get('EXTRACTION_JOB_ID')}")
        return WBL_CONFIG
    except ImportError:
        logger.warning("config.py not found. Run 'python setup.py' first.")
        return None
    except Exception as e:
        logger.error(f"Error loading config.py: {e}", exc_info=True)
        return None

# ============================================
# MAIN
# ============================================

def main():
    print("=" * 60)
    print(" LINKEDIN CONTACT EXTRACTION BOT (DEBUG MODE)")
    print("=" * 60)
    
    logger.info("=" * 60)
    logger.info("STARTING EXTRACTION BOT")
    logger.info("=" * 60)
    
    # Load WBL config
    wbl_config = load_wbl_config()
    
    if wbl_config:
        employee_id = wbl_config.get('EMPLOYEE_ID', 0)
        default_candidate_id = wbl_config.get('CANDIDATE_ID', 0)
        print(f"WBL Config loaded - Employee ID: {employee_id}")
    else:
        employee_id = 0
        default_candidate_id = 0
        print("WARNING: No config.py found. Run 'python setup.py' first.")
    
    # Load accounts
    accounts = load_accounts("credentials/accounts.yaml")
    
    if not accounts:
        print("\nERROR: No accounts in credentials/accounts.yaml")
        logger.error("No accounts found")
        sys.exit(1)
    
    print(f"Accounts found: {len(accounts)}")
    print("=" * 60)
    
    # Process each account
    for i, acc in enumerate(accounts, 1):
        username = acc.get('username', '')
        password = acc.get('password', '')
        chrome_profile = acc.get('chrome_profile', 'Default')
        candidate_id = acc.get('candidate_id', default_candidate_id)
        
        print(f"\n[{i}/{len(accounts)}] {username}")
        print(f"   Profile: {chrome_profile}")
        print(f"   Candidate ID: {candidate_id}")
        print("-" * 40)
        
        logger.info(f"Processing account {i}/{len(accounts)}: {username}")
        
        if not username or not password:
            print("   SKIPPED: Missing credentials")
            logger.warning(f"Skipping {username}: missing credentials")
            continue

        try:
            bot = LinkedInBot(
                username=username,
                password=password,
                chrome_profile=chrome_profile,
                employee_id=employee_id,
                candidate_id=candidate_id
            )
            
            bot.run()
            
            print(f"   Extracted: {bot.extracted_count} contacts")
            logger.info(f"Account {username} completed: {bot.extracted_count} contacts")
            
        except Exception as e:
            logger.error(f"Error processing {username}: {e}", exc_info=True)
            print(f"   ERROR: {e}")
        
        # Delay between accounts
        if i < len(accounts):
            delay = random.uniform(10, 20)
            print(f"\nWaiting {delay:.1f}s...")
            time.sleep(delay)
    
    print("\n" + "=" * 60)
    print(" EXTRACTION COMPLETE")
    print("=" * 60)
    print("\nOutput files:")
    print("   - logs/extracted_contacts.csv")
    print("   - logs/extraction_debug.log (full debug log)")
    
    logger.info("EXTRACTION BOT FINISHED")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        logger.info("Cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)