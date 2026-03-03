# utils/validators.py
"""
Production Validation System (Phase 5.2)
Validates environment, configuration, and modules for production deployment.
"""

import os
import logging
from pathlib import Path
from typing import Tuple, List

logger = logging.getLogger(__name__)


def validate_environment() -> Tuple[bool, List[str], List[str]]:
    """
    Validate production environment.
    
    Returns:
        tuple: (is_valid, errors, warnings)
    """
    errors = []
    warnings = []
    
    logger.info("[VALIDATION] Checking environment...")
    
    # Check .env file exists
    if not Path('.env').exists():
        errors.append(".env file not found - copy .env.example to .env")
    else:
        logger.debug("[VALIDATION] .env file found")
    
    # Check required environment variables
    required_vars = [
        'LINKEDIN_USERNAME',
        'LINKEDIN_PASSWORD',
        'CHROME_PROFILE_PATH',
        'WBL_API_URL',
        'WBL_SECRET_TOKEN',
        'WBL_EMPLOYEE_ID',
        'WBL_CANDIDATE_ID',
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            errors.append(f"Required variable {var} not set in .env")
        elif value.strip() == '':
            errors.append(f"Required variable {var} is empty in .env")
        else:
            logger.debug(f"[VALIDATION] {var} is set")
    
    # Check Chrome profile exists (if set)
    chrome_profile = os.getenv('CHROME_PROFILE_PATH')
    if chrome_profile:
        # Extract directory path (handle both full path and profile name)
        if 'User Data' in chrome_profile:
            # Full path like "C:/Users/.../User Data"
            user_data_dir = chrome_profile
        else:
            # Just profile name, need to construct path
            # This is a warning, not an error, as the actual path depends on system
            warnings.append(f"Chrome profile path may need verification: {chrome_profile}")
    
    # Check logs directory exists
    if not Path('logs').exists():
        warnings.append("logs/ directory not found - will be created automatically")
    else:
        logger.debug("[VALIDATION] logs/ directory found")
    
    # Check credentials directory exists
    if not Path('credentials').exists():
        warnings.append("credentials/ directory not found")
    else:
        logger.debug("[VALIDATION] credentials/ directory found")
    
    # Check database connectivity (optional - may not be needed for contact extraction)
    try:
        from utils.db import test_connection
        if hasattr(test_connection, '__call__'):
            if not test_connection():
                warnings.append("Database connection test failed - may not be critical")
    except ImportError:
        logger.debug("[VALIDATION] Database module not available for testing")
    except Exception as e:
        warnings.append(f"Database test failed: {e}")
    
    return (len(errors) == 0, errors, warnings)


def validate_configuration() -> Tuple[bool, List[str]]:
    """
    Validate bot configuration.
    
    Returns:
        tuple: (is_valid, errors)
    """
    errors = []
    
    logger.info("[VALIDATION] Checking configuration...")
    
    try:
        from config.secrets import get_execution_config, validate_execution_config
        
        # Load config
        config = get_execution_config()
        logger.debug(f"[VALIDATION] Loaded execution config: {config}")
        
        # Validate config
        is_valid, config_errors = validate_execution_config(config)
        
        if not is_valid:
            errors.extend(config_errors)
        else:
            logger.debug("[VALIDATION] Execution config is valid")
        
    except ImportError as e:
        errors.append(f"Configuration module import failed: {e}")
    except Exception as e:
        errors.append(f"Configuration validation failed: {e}")
    
    # Check config.yaml exists
    if not Path('config.yaml').exists():
        errors.append("config.yaml not found")
    else:
        logger.debug("[VALIDATION] config.yaml found")
        
        # Try to load it
        try:
            import yaml
            with open('config.yaml', 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Check required fields
            if 'NUM_MESSAGES_TO_PROCESS' not in config_data:
                errors.append("config.yaml missing NUM_MESSAGES_TO_PROCESS")
            else:
                logger.debug(f"[VALIDATION] NUM_MESSAGES_TO_PROCESS = {config_data['NUM_MESSAGES_TO_PROCESS']}")
        except Exception as e:
            errors.append(f"Failed to load config.yaml: {e}")
    
    return (len(errors) == 0, errors)


def validate_modules() -> Tuple[bool, List[str]]:
    """
    Validate all modules can be imported.
    
    Returns:
        tuple: (is_valid, errors)
    """
    errors = []
    
    logger.info("[VALIDATION] Checking modules...")
    
    # Test Phase 3 modules
    try:
        from modules import BrowserManager, DiscoveryModule, WorkflowModule, PersistenceModule
        logger.debug("[VALIDATION] Phase 3 modules imported successfully")
    except ImportError as e:
        errors.append(f"Phase 3 module import failed: {e}")
    
    # Test stealth modules
    try:
        from stealth import HumanBehavior
        logger.debug("[VALIDATION] Stealth modules imported successfully")
    except ImportError as e:
        errors.append(f"Stealth module import failed: {e}")
    

    # Test metrics
    try:
        from utils.metrics import ExtractionMetrics
        logger.debug("[VALIDATION] ExtractionMetrics imported successfully")
    except ImportError as e:
        errors.append(f"ExtractionMetrics import failed: {e}")
    
    # Test exceptions
    try:
        from utils.exceptions import BrowserException, NavigationException, ExtractionException
        logger.debug("[VALIDATION] Custom exceptions imported successfully")
    except ImportError as e:
        errors.append(f"Custom exceptions import failed: {e}")
    
    # Test database utilities
    try:
        from utils.db import bulk_insert_automation_contacts, log_extraction_activity
        logger.debug("[VALIDATION] Database utilities imported successfully")
    except ImportError as e:
        errors.append(f"Database utilities import failed: {e}")
    
    return (len(errors) == 0, errors)


def validate_selectors() -> Tuple[bool, List[str]]:
    """
    Validate selector configuration.
    
    Returns:
        tuple: (is_valid, errors)
    """
    errors = []
    
    logger.info("[VALIDATION] Checking selectors...")
    
    # Check selectors directory exists
    if not Path('selectors').exists():
        errors.append("selectors/ directory not found")
        return (False, errors)
    
    # Check linkedin_selectors.py exists
    if not Path('selectors/linkedin_selectors.py').exists():
        errors.append("selectors/linkedin_selectors.py not found")
        return (False, errors)
    
    # Try to import selectors
    try:
        from selectors.linkedin_selectors import SELECTORS
        logger.debug("[VALIDATION] LinkedIn selectors imported successfully")
        
        # Check required selector categories
        required_categories = ['login', 'messages', 'profile']
        for category in required_categories:
            if category not in SELECTORS:
                errors.append(f"Selector category '{category}' not found in SELECTORS")
            else:
                logger.debug(f"[VALIDATION] Selector category '{category}' found")
        
    except ImportError as e:
        errors.append(f"Selectors import failed: {e}")
    except Exception as e:
        errors.append(f"Selectors validation failed: {e}")
    
    return (len(errors) == 0, errors)


def run_pre_deployment_checks() -> bool:
    """
    Run all pre-deployment validation checks.
    
    Returns:
        bool: True if all checks passed, False otherwise
    """
    logger.info("=" * 70)
    logger.info("PRE-DEPLOYMENT VALIDATION (Phase 5.2)")
    logger.info("=" * 70)
    
    all_passed = True
    
    # Environment validation
    env_valid, env_errors, env_warnings = validate_environment()
    if not env_valid:
        logger.error("❌ Environment validation FAILED:")
        for error in env_errors:
            logger.error(f"   - {error}")
        all_passed = False
    else:
        logger.info("✅ Environment validation PASSED")
    
    if env_warnings:
        logger.warning("⚠️  Environment warnings:")
        for warning in env_warnings:
            logger.warning(f"   - {warning}")
    
    logger.info("-" * 70)
    
    # Configuration validation
    config_valid, config_errors = validate_configuration()
    if not config_valid:
        logger.error("❌ Configuration validation FAILED:")
        for error in config_errors:
            logger.error(f"   - {error}")
        all_passed = False
    else:
        logger.info("✅ Configuration validation PASSED")
    
    logger.info("-" * 70)
    
    # Module validation
    modules_valid, module_errors = validate_modules()
    if not modules_valid:
        logger.error("❌ Module validation FAILED:")
        for error in module_errors:
            logger.error(f"   - {error}")
        all_passed = False
    else:
        logger.info("✅ Module validation PASSED")
    
    logger.info("-" * 70)
    
    # Selector validation
    selectors_valid, selector_errors = validate_selectors()
    if not selectors_valid:
        logger.error("❌ Selector validation FAILED:")
        for error in selector_errors:
            logger.error(f"   - {error}")
        all_passed = False
    else:
        logger.info("✅ Selector validation PASSED")
    
    logger.info("=" * 70)
    
    if all_passed:
        logger.info("✅ ALL PRE-DEPLOYMENT CHECKS PASSED")
        logger.info("   Bot is ready for production deployment")
    else:
        logger.error("❌ PRE-DEPLOYMENT CHECKS FAILED")
        logger.error("   Fix errors before deploying to production")
    
    logger.info("=" * 70)
    
    return all_passed
