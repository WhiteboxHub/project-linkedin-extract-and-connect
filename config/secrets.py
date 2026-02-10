# config/secrets.py
"""
Secure credential and configuration management using environment variables.
Replaces hardcoded values in config.py with environment-based configuration.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env file from project root
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / '.env'

def load_env_config() -> None:
    """Load environment variables from .env file."""
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)
        logger.info(f"✅ Loaded environment from: {ENV_FILE}")
    else:
        logger.warning(f"⚠️  No .env file found at: {ENV_FILE}")
        logger.warning("   Using environment variables or defaults")


def get_env(key: str, default: Any = None, required: bool = False) -> Any:
    """
    Get environment variable with validation.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        required: If True, raise error if not found
        
    Returns:
        Environment variable value or default
        
    Raises:
        ValueError: If required=True and variable not found
    """
    value = os.getenv(key, default)
    
    if required and value is None:
        raise ValueError(f"❌ Required environment variable '{key}' not found!")
    
    return value


def get_config() -> Dict[str, Any]:
    """
    Get complete configuration from environment variables.
    Falls back to config.py values if environment variables not set.
    
    Returns:
        Configuration dictionary
    """
    # Try to import existing config.py as fallback
    fallback_config = {}
    try:
        import config as legacy_config
        if hasattr(legacy_config, 'WBL_CONFIG'):
            fallback_config = legacy_config.WBL_CONFIG
            logger.info("📋 Loaded fallback config from config.py")
    except ImportError:
        logger.warning("⚠️  config.py not found, using environment only")

def get_wbl_config():
    """
    Get WBL (website backend) configuration from environment.
    
    Returns:
        dict: WBL configuration with API URL and secret token
    """
    load_dotenv()
    
    config = {
        'WBL_API_URL': os.getenv('WBL_API_URL', ''),
        'WBL_SECRET_TOKEN': os.getenv('WBL_SECRET_TOKEN', ''),
    }
    
    return config


def get_stealth_config():
    """
    Get stealth configuration from environment variables.
    
    Returns:
        dict: Stealth configuration with all timing parameters
    """
    load_dotenv()
    
    def get_bool(key, default='true'):
        """Helper to parse boolean environment variables."""
        value = os.getenv(key, default).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def get_int(key, default):
        """Helper to parse integer environment variables."""
        try:
            return int(os.getenv(key, str(default)))
        except (ValueError, TypeError):
            return default
    
    config = {
        # Feature flags
        'STEALTH_ENABLED': get_bool('STEALTH_ENABLED', 'true'),
        'RANDOMIZE_FINGERPRINT': get_bool('RANDOMIZE_FINGERPRINT', 'true'),
        'HUMAN_BEHAVIOR_ENABLED': get_bool('HUMAN_BEHAVIOR_ENABLED', 'true'),
        
        # Timing parameters (in milliseconds)
        'MIN_ACTION_DELAY_MS': get_int('MIN_ACTION_DELAY_MS', 500),
        'MAX_ACTION_DELAY_MS': get_int('MAX_ACTION_DELAY_MS', 3000),
        
        'TYPING_SPEED_MIN_MS': get_int('TYPING_SPEED_MIN_MS', 50),
        'TYPING_SPEED_MAX_MS': get_int('TYPING_SPEED_MAX_MS', 150),
        
        'CLICK_DELAY_MIN_MS': get_int('CLICK_DELAY_MIN_MS', 100),
        'CLICK_DELAY_MAX_MS': get_int('CLICK_DELAY_MAX_MS', 500),
        
        'SCROLL_DELAY_MIN_MS': get_int('SCROLL_DELAY_MIN_MS', 200),
        'SCROLL_DELAY_MAX_MS': get_int('SCROLL_DELAY_MAX_MS', 800),
        
        'PAGE_LOAD_DELAY_MIN_MS': get_int('PAGE_LOAD_DELAY_MIN_MS', 1000),
        'PAGE_LOAD_DELAY_MAX_MS': get_int('PAGE_LOAD_DELAY_MAX_MS', 3000),
        
        'READING_SPEED_MIN_WPM': get_int('READING_SPEED_MIN_WPM', 200),
        'READING_SPEED_MAX_WPM': get_int('READING_SPEED_MAX_WPM', 300),
    }
    
    return config


def get_execution_config():
    """
    Get execution control configuration from environment variables.
    Used for Phase 4 - contact extraction limits and rate limiting.
    
    Returns:
        dict: Execution configuration with limits and delays
    """
    load_dotenv()
    
    def get_int(key, default):
        """Helper to parse integer environment variables."""
        try:
            return int(os.getenv(key, str(default)))
        except (ValueError, TypeError):
            return default
    
    def get_bool(key, default='true'):
        """Helper to parse boolean environment variables."""
        value = os.getenv(key, default).lower()
        return value in ('true', '1', 'yes', 'on')
    
    config = {
        # Contact extraction limits
        'MAX_CONTACTS_PER_RUN': get_int('MAX_CONTACTS_PER_RUN', 50),
        'MIN_THREAD_DELAY_MS': get_int('MIN_THREAD_DELAY_MS', 2000),
        'MAX_THREAD_DELAY_MS': get_int('MAX_THREAD_DELAY_MS', 5000),
        
        # Error handling
        'SKIP_ON_ERROR': get_bool('SKIP_ON_ERROR', 'true'),
        'MAX_CONSECUTIVE_ERRORS': get_int('MAX_CONSECUTIVE_ERRORS', 5),
    }
    
    return config


def validate_execution_config(config=None):
    """
    Validate execution configuration values.
    
    Args:
        config: Optional config dict. If None, loads from environment.
        
    Returns:
        tuple: (is_valid, error_messages)
    """
    if config is None:
        config = get_execution_config()
    
    errors = []
    
    # Validate max contacts
    if config['MAX_CONTACTS_PER_RUN'] < 1:
        errors.append("MAX_CONTACTS_PER_RUN must be >= 1")
    
    if config['MAX_CONTACTS_PER_RUN'] > 1000:
        errors.append("MAX_CONTACTS_PER_RUN should be <= 1000 (safety limit)")
    
    # Validate delays
    if config['MIN_THREAD_DELAY_MS'] < 0:
        errors.append("MIN_THREAD_DELAY_MS must be >= 0")
    
    if config['MAX_THREAD_DELAY_MS'] < config['MIN_THREAD_DELAY_MS']:
        errors.append("MAX_THREAD_DELAY_MS must be >= MIN_THREAD_DELAY_MS")
    
    if config['MAX_THREAD_DELAY_MS'] > 60000:
        errors.append("MAX_THREAD_DELAY_MS should be <= 60000ms (1 minute)")
    
    # Validate error limits
    if config['MAX_CONSECUTIVE_ERRORS'] < 1:
        errors.append("MAX_CONSECUTIVE_ERRORS must be >= 1")
    
    return (len(errors) == 0, errors)


def validate_stealth_config(config=None):
    """
    Validate stealth configuration values.
    
    Args:
        config: Optional config dict. If None, loads from environment.
        
    Returns:
        tuple: (is_valid, error_messages)
    """
    if config is None:
        config = get_stealth_config()
    
    errors = []
    
    # Validate timing ranges
    if config['MIN_ACTION_DELAY_MS'] > config['MAX_ACTION_DELAY_MS']:
        errors.append("MIN_ACTION_DELAY_MS must be <= MAX_ACTION_DELAY_MS")
    
    if config['TYPING_SPEED_MIN_MS'] > config['TYPING_SPEED_MAX_MS']:
        errors.append("TYPING_SPEED_MIN_MS must be <= TYPING_SPEED_MAX_MS")
    
    if config['CLICK_DELAY_MIN_MS'] > config['CLICK_DELAY_MAX_MS']:
        errors.append("CLICK_DELAY_MIN_MS must be <= CLICK_DELAY_MAX_MS")
    
    if config['SCROLL_DELAY_MIN_MS'] > config['SCROLL_DELAY_MAX_MS']:
        errors.append("SCROLL_DELAY_MIN_MS must be <= SCROLL_DELAY_MAX_MS")
    
    if config['PAGE_LOAD_DELAY_MIN_MS'] > config['PAGE_LOAD_DELAY_MAX_MS']:
        errors.append("PAGE_LOAD_DELAY_MIN_MS must be <= PAGE_LOAD_DELAY_MAX_MS")
    
    if config['READING_SPEED_MIN_WPM'] > config['READING_SPEED_MAX_WPM']:
        errors.append("READING_SPEED_MIN_WPM must be <= READING_SPEED_MAX_WPM")
    
    # Validate reasonable ranges
    if config['TYPING_SPEED_MIN_MS'] < 10 or config['TYPING_SPEED_MAX_MS'] > 1000:
        errors.append("Typing speed should be between 10-1000ms")
    
    if config['READING_SPEED_MIN_WPM'] < 50 or config['READING_SPEED_MAX_WPM'] > 1000:
        errors.append("Reading speed should be between 50-1000 WPM")
    
    return (len(errors) == 0, errors)
    
    # Build configuration from environment with fallbacks
    config = {
        # API Configuration
        "API_URL": get_env("WBL_API_URL", fallback_config.get("API_URL", "http://localhost:8000/api")),
        "TOKEN": get_env("WBL_API_TOKEN", fallback_config.get("TOKEN")),
        
        # User Configuration
        "EMAIL": get_env("WBL_EMAIL", fallback_config.get("EMAIL")),
        "EMPLOYEE_ID": int(get_env("WBL_EMPLOYEE_ID", fallback_config.get("EMPLOYEE_ID", 0))),
        "CANDIDATE_ID": int(get_env("WBL_CANDIDATE_ID", fallback_config.get("CANDIDATE_ID", 0))),
        "CANDIDATE_NAME": get_env("WBL_CANDIDATE_NAME", fallback_config.get("CANDIDATE_NAME", "")),
        
        # Job Configuration
        "EXTRACTION_JOB_ID": int(get_env("WBL_EXTRACTION_JOB_ID", fallback_config.get("EXTRACTION_JOB_ID", 120))),
        
        # Browser Configuration
        "CHROME_PROFILE_PATH": get_env("CHROME_PROFILE_PATH", ""),
        "HEADLESS_MODE": get_env("HEADLESS_MODE", "false").lower() == "true",
        
        # Execution Limits
        "MAX_MESSAGES_TO_PROCESS": get_env("MAX_MESSAGES_TO_PROCESS", "20"),
        "MAX_APPLICATIONS_PER_RUN": int(get_env("MAX_APPLICATIONS_PER_RUN", 50)),
        "SUBMISSION_COOLDOWN_SECONDS": int(get_env("SUBMISSION_COOLDOWN_SECONDS", 30)),
        
        # Stealth Configuration
        "ENABLE_STEALTH_MODE": get_env("ENABLE_STEALTH_MODE", "true").lower() == "true",
        "ENABLE_FINGERPRINT_RANDOMIZATION": get_env("ENABLE_FINGERPRINT_RANDOMIZATION", "true").lower() == "true",
        "ENABLE_HUMAN_BEHAVIOR": get_env("ENABLE_HUMAN_BEHAVIOR", "true").lower() == "true",
        
        # Proxy Configuration
        "PROXY_ENABLED": get_env("PROXY_ENABLED", "false").lower() == "true",
        "PROXY_URL": get_env("PROXY_URL"),
        "PROXY_ROTATION_ENABLED": get_env("PROXY_ROTATION_ENABLED", "false").lower() == "true",
        
        # Logging Configuration
        "LOG_LEVEL": get_env("LOG_LEVEL", "INFO"),
        "LOG_TO_FILE": get_env("LOG_TO_FILE", "true").lower() == "true",
        "LOG_FILE_PATH": get_env("LOG_FILE_PATH", "logs/extraction_debug.log"),
        
        # Dry Run Mode
        "DRY_RUN_MODE": get_env("DRY_RUN_MODE", "false").lower() == "true",
        
        # Database Configuration
        "USE_DUCKDB": get_env("USE_DUCKDB", "false").lower() == "true",
        "DUCKDB_PATH": get_env("DUCKDB_PATH", "data/linkedin_bot.duckdb"),
        
        # Environment
        "ENVIRONMENT": get_env("ENVIRONMENT", fallback_config.get("ENVIRONMENT", "local")),
    }
    
    return config


def validate_secrets() -> bool:
    """
    Validate that all required secrets are present.
    
    Returns:
        True if all required secrets are valid, False otherwise
    """
    logger.info("=" * 60)
    logger.info("🔒 VALIDATING SECRETS")
    logger.info("=" * 60)
    
    errors = []
    warnings = []
    
    # Required secrets
    required_secrets = {
        "WBL_API_URL": "WBL API URL",
        "WBL_API_TOKEN": "WBL API Token",
        "WBL_EMPLOYEE_ID": "Employee ID",
    }
    
    for env_var, description in required_secrets.items():
        value = os.getenv(env_var)
        if not value:
            # Try fallback from config.py
            try:
                import config as legacy_config
                if hasattr(legacy_config, 'WBL_CONFIG'):
                    fallback_key = env_var.replace("WBL_", "").replace("_", "_")
                    if fallback_key in legacy_config.WBL_CONFIG:
                        warnings.append(f"⚠️  {description}: Using fallback from config.py (consider moving to .env)")
                        continue
            except ImportError:
                pass
            
            errors.append(f"❌ {description} ({env_var}): Not found in environment or config.py")
    
    # Optional but recommended
    optional_secrets = {
        "WBL_EMAIL": "WBL Email",
    }
    
    for env_var, description in optional_secrets.items():
        value = os.getenv(env_var)
        if not value:
            warnings.append(f"ℹ️  {description} ({env_var}): Not set (optional)")
    
    # Print results
    if errors:
        logger.error("❌ SECRET VALIDATION FAILED:")
        for error in errors:
            logger.error(f"   {error}")
        logger.error("")
        logger.error("💡 TIP: Copy .env.example to .env and fill in your values")
        return False
    
    if warnings:
        logger.warning("⚠️  WARNINGS:")
        for warning in warnings:
            logger.warning(f"   {warning}")
    
    logger.info("✅ All required secrets validated")
    logger.info("=" * 60)
    return True


def print_config_summary(config: Dict[str, Any]) -> None:
    """
    Print a summary of the current configuration (without sensitive data).
    
    Args:
        config: Configuration dictionary
    """
    logger.info("=" * 60)
    logger.info("📋 CONFIGURATION SUMMARY")
    logger.info("=" * 60)
    
    # Safe to print
    safe_config = {
        "API_URL": config.get("API_URL"),
        "EMPLOYEE_ID": config.get("EMPLOYEE_ID"),
        "CANDIDATE_ID": config.get("CANDIDATE_ID"),
        "EXTRACTION_JOB_ID": config.get("EXTRACTION_JOB_ID"),
        "HEADLESS_MODE": config.get("HEADLESS_MODE"),
        "MAX_MESSAGES_TO_PROCESS": config.get("MAX_MESSAGES_TO_PROCESS"),
        "ENABLE_STEALTH_MODE": config.get("ENABLE_STEALTH_MODE"),
        "DRY_RUN_MODE": config.get("DRY_RUN_MODE"),
        "LOG_LEVEL": config.get("LOG_LEVEL"),
        "ENVIRONMENT": config.get("ENVIRONMENT"),
    }
    
    for key, value in safe_config.items():
        logger.info(f"   {key}: {value}")
    
    # Sensitive data - show only if present
    if config.get("TOKEN"):
        logger.info(f"   TOKEN: {'*' * 20} (present)")
    if config.get("EMAIL"):
        logger.info(f"   EMAIL: {config.get('EMAIL')}")
    
    logger.info("=" * 60)


# Initialize on import
load_env_config()
