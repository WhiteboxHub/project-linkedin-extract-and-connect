# config/__init__.py
"""Configuration package for LinkedIn Bot."""

from .secrets import load_env_config, validate_secrets, get_config

# Import WBL_CONFIG from root config.py if it exists
# We need to use importlib to avoid circular import issues
try:
    import os
    import importlib.util
    
    # Get the path to the root config.py file
    root_dir = os.path.dirname(os.path.dirname(__file__))
    config_file_path = os.path.join(root_dir, 'config.py')
    
    if os.path.exists(config_file_path):
        # Load config.py as a module
        spec = importlib.util.spec_from_file_location("root_config", config_file_path)
        root_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(root_config)
        
        # Extract WBL_CONFIG
        WBL_CONFIG = root_config.WBL_CONFIG
        __all__ = ['load_env_config', 'validate_secrets', 'get_config', 'WBL_CONFIG']
    else:
        # config.py doesn't exist yet (needs setup.py to be run)
        __all__ = ['load_env_config', 'validate_secrets', 'get_config']
except Exception as e:
    # If anything fails, just don't export WBL_CONFIG
    __all__ = ['load_env_config', 'validate_secrets', 'get_config']
