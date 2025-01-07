import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_api_keys():
    """
    Load API keys from environment variables.
    Returns a dictionary containing the OpenRouter API key.
    """
    # Only need OpenRouter API key now
    required_keys = {
        'openrouter_api_key': 'OPENROUTER_API_KEY'
    }
    
    config = {}
    
    # Get keys from environment variables
    missing_keys = []
    for config_key, env_key in required_keys.items():
        env_value = os.getenv(env_key)
        if env_value:
            config[config_key] = env_value
        else:
            missing_keys.append(env_key)
            logger.error(f"Required environment variable {env_key} not found")
    
    # Raise error if any required keys are missing
    if missing_keys:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_keys)}")
    
    return config