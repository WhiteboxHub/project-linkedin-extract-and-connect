# main.py
# ============================================
# LINKEDIN CONTACT EXTRACTION - ENTRY POINT
# WITH FULL DEBUG LOGGING
# ============================================

import sys
import logging
import os
import argparse
from utils.multi_account_manager import MultiAccountManager

# ============================================
# LOGGING SETUP
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
# MAIN
# ============================================

def main():
    print("=" * 60)
    print(" LINKEDIN CONTACT EXTRACTION BOT")
    print("=" * 60)
    
    # Check if run_multi_account.py is being used (deprecation warning)
    if len(sys.argv) > 1 and sys.argv[0].endswith("run_multi_account.py"):
        logger.warning("run_multi_account.py is deprecated. Use main.py instead.")

    # Parse arguments
    parser = argparse.ArgumentParser(description="Run LinkedIn Extraction Bot")
    parser.add_argument("--account", help="Run only for specific email/username")
    parser.add_argument("--index", type=int, help="Run only specific account index (1-based)")
    args = parser.parse_args()
    
    try:
        logger.info("=" * 60)
        logger.info("STARTING EXTRACTION BOT")
        logger.info("=" * 60)

        # Load manager
        manager = MultiAccountManager(
            accounts_file="credentials/accounts.yaml",
            delay_between_accounts=300 # 5 minutes default
        )
        
        # Check accounts
        if not manager.accounts:
            print("\nERROR: No accounts found in credentials/accounts.yaml")
            logger.error("No accounts found in credentials/accounts.yaml")
            print("Please configure accounts first.")
            sys.exit(1)
            
        # Filter if arguments provided
        if args.account:
            print(f"Filtering for account: {args.account}")
            logger.info(f"Filtering map for account: {args.account}")
            manager.accounts = [a for a in manager.accounts if a.get('username') == args.account]
            if not manager.accounts:
                print(f"ERROR: Account '{args.account}' not found.")
                logger.error(f"Account '{args.account}' not found in configuration")
                sys.exit(1)
        elif args.index:
            print(f"Filtering for account index: {args.index}")
            logger.info(f"Filtering map for index: {args.index}")
            if 1 <= args.index <= len(manager.accounts):
                manager.accounts = [manager.accounts[args.index - 1]]
            else:
                print(f"ERROR: Index {args.index} out of range (1-{len(manager.accounts)})")
                logger.error(f"Index {args.index} out of range")
                sys.exit(1)
            
        print(f"\nLoaded {len(manager.accounts)} accounts to run.")
        print("Starting execution...")
        
        # Run
        manager.run_all()
        
        print("\n" + "=" * 60)
        print(" EXTRACTION COMPLETE")
        print("=" * 60)
        print("\nOutput files:")
        print("   - logs/extracted_contacts.csv")
        print("   - logs/extraction_debug.log")
        
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        logger.info("Cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\nFATAL ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()