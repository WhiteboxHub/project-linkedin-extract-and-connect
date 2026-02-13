# utils/multi_account_manager.py
import logging
import time
import yaml
import os
from datetime import datetime
from typing import List, Dict, Optional

from utils.linkedin_bot import LinkedInBot
from config.secrets import get_execution_config

# Configure logging
logger = logging.getLogger(__name__)

class MultiAccountManager:
    """
    Manages sequential execution of multiple LinkedIn accounts.
    Ensures proper cleanup between accounts to prevent resource exhaustion.
    """
    
    def __init__(self, accounts_file: str = "credentials/accounts.yaml", delay_between_accounts: int = 300):
        """
        Initialize the manager.
        
        Args:
            accounts_file: Path to accounts YAML file
            delay_between_accounts: Seconds to wait between accounts (default 5 mins)
        """
        self.accounts_file = accounts_file
        self.delay_between_accounts = delay_between_accounts
        self.accounts = []
        self.processed_accounts = []
        self.failed_accounts = []
        self.results = {}
        
        # Load accounts immediately
        self.load_accounts()

    def load_accounts(self) -> List[Dict]:
        """Load accounts from YAML file."""
        try:
            if not os.path.exists(self.accounts_file):
                logger.error(f"Accounts file not found: {self.accounts_file}")
                return []
                
            with open(self.accounts_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
                
            self.accounts = data.get('accounts', [])
            logger.info(f"Loaded {len(self.accounts)} accounts from {self.accounts_file}")
            return self.accounts
            
        except Exception as e:
            logger.error(f"Failed to load accounts: {e}")
            return []

    def _validate_account(self, account: Dict, index: int) -> bool:
        """Validate account configuration."""
        required_fields = ['username', 'password', 'chrome_profile', 'employee_id', 'candidate_id']
        missing = [f for f in required_fields if not account.get(f)]
        
        if missing:
            logger.warning(f"Account #{index+1} missing required fields: {missing} - SKIPPING")
            return False
        return True

    def run_all(self):
        """Run extraction for all loaded accounts sequentially."""
        logger.info("=" * 60)
        logger.info(f"STARTING MULTI-ACCOUNT RUN: {len(self.accounts)} Accounts")
        logger.info("=" * 60)
        
        if not self.accounts:
            logger.warning("No accounts found to process.")
            return

        for i, account in enumerate(self.accounts):
            username = account.get('username')
            profile = account.get('chrome_profile')
            
            logger.info("\n" + "-" * 60)
            logger.info(f"PROCESSING ACCOUNT {i+1}/{len(self.accounts)}: {username} ({profile})")
            logger.info("-" * 60)
            
            # Validate
            if not self._validate_account(account, i):
                self.failed_accounts.append(f"#{i+1} (Invalid Config)")
                continue

            try:
                # Run extraction for this account
                # Using 'with' block (context manager) is CRITICAL for cleanup
                with LinkedInBot(
                    username=username,
                    password=account.get('password'),
                    chrome_profile=profile,
                    employee_id=account.get('employee_id'),
                    candidate_id=account.get('candidate_id'),
                    proxy=account.get('proxy') # Pass optional proxy
                ) as bot:
                    bot.run()
                    result_summary = bot.metrics.get_summary() if hasattr(bot, 'metrics') else {}
                    self.results[username] = result_summary
                
                # If we get here without exception, it succeeded
                self.processed_accounts.append(username)
                logger.info(f"✅ Account {username} COMPLETED successfully")
                
            except Exception as e:
                logger.error(f"❌ Account {username} FAILED: {e}", exc_info=True)
                self.failed_accounts.append(username)
            
            # Delay before next account (if not last)
            if i < len(self.accounts) - 1:
                logger.info(f"Waiting {self.delay_between_accounts}s before next account...")
                time.sleep(self.delay_between_accounts)

        self._print_final_summary()

    def get_summary(self) -> Dict:
        """Return execution summary."""
        total = len(self.accounts)
        processed = len(self.processed_accounts)
        failed = len(self.failed_accounts)
        success_rate = (processed / total * 100) if total > 0 else 0
        
        return {
            "total_accounts": total,
            "processed": processed,
            "failed": failed,
            "success_rate": success_rate,
            "details": self.results
        }

    def _print_final_summary(self):
        """Print final execution report."""
        summary = self.get_summary()
        
        logger.info("\n" + "=" * 60)
        logger.info("MULTI-ACCOUNT EXECUTION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total Accounts: {summary['total_accounts']}")
        logger.info(f"Successful:     {summary['processed']}")
        logger.info(f"Failed:         {summary['failed']}")
        logger.info(f"Success Rate:   {summary['success_rate']:.1f}%")
        logger.info("-" * 60)
        
        if self.failed_accounts:
            logger.info("Failed Accounts:")
            for acc in self.failed_accounts:
                logger.info(f" - {acc}")
        logger.info("=" * 60)
