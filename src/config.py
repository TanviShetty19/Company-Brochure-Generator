"""
Configuration Module

Supports multiple LLM providers:
- Ollama (default, free, local)
- OpenAI (paid)
- Google Gemini (paid)
"""

import os
from dotenv import load_dotenv
from typing import Dict, Optional

# Load environment variables
load_dotenv(override=True)

# ============================================
# Provider Selection
# ============================================

LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'ollama').lower()

# ============================================
# Provider Configurations
# ============================================

# Ollama (Free, Local)
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434/v1')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2:1b')

# OpenAI (Paid)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')

# Google Gemini (Paid)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-lite')
GEMINI_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/openai/'

# ============================================
# Application Settings
# ============================================

MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', '5000'))
CACHE_ENABLED = os.getenv('CACHE_ENABLED', 'true').lower() == 'true'
CACHE_EXPIRY_DAYS = int(os.getenv('CACHE_EXPIRY_DAYS', '7'))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output')
CACHE_DIR = os.getenv('CACHE_DIR', 'cache')
LOG_DIR = os.getenv('LOG_DIR', 'logs')


def get_provider_config() -> Dict[str, Optional[str]]:
    """
    Get configuration for the selected provider.
    
    Returns:
        Dict with keys: 'base_url', 'api_key', 'model', 'provider'
        
    Raises:
        ValueError: If configuration is invalid
    """
    config = {'provider': LLM_PROVIDER}
    
    if LLM_PROVIDER == 'ollama':
        config.update({
            'base_url': OLLAMA_BASE_URL,
            'api_key': 'ollama',  # Any string works
            'model': OLLAMA_MODEL
        })
    elif LLM_PROVIDER == 'openai':
        if not OPENAI_API_KEY:
            raise ValueError(
                "OpenAI API key not found. "
                "Set OPENAI_API_KEY in .env file"
            )
        config.update({
            'base_url': None,
            'api_key': OPENAI_API_KEY,
            'model': OPENAI_MODEL
        })
    elif LLM_PROVIDER == 'gemini':
        if not GEMINI_API_KEY:
            raise ValueError(
                "Gemini API key not found. "
                "Set GEMINI_API_KEY in .env file"
            )
        config.update({
            'base_url': GEMINI_BASE_URL,
            'api_key': GEMINI_API_KEY,
            'model': GEMINI_MODEL
        })
    else:
        raise ValueError(f"Unsupported provider: {LLM_PROVIDER}")
    
    return config


def get_provider_summary() -> str:
    """Get a human-readable configuration summary."""
    config = get_provider_config()
    return f"""
Provider Configuration
---------------------
Provider : {LLM_PROVIDER.upper()}
Model    : {config['model']}
Base URL : {config['base_url'] or 'Default'}
"""


# ============================================
# Model Registry
# ============================================

AVAILABLE_MODELS = {
    'ollama': {
        'llama3.2:1b': 'Recommended for most users, fast, 1B params',
        'llama3.2': 'Full version, better quality, 3B params',
        'deepseek-r1:1.5b': 'Reasoning-focused, 1.5B params',
        'phi3:mini': 'Microsoft Phi-3, good balance'
    },
    'openai': {
        'gpt-4.1-mini': 'Fast, cheap, good quality',
        'gpt-5-nano': 'Smallest OpenAI model'
    },
    'gemini': {
        'gemini-2.5-flash-lite': 'Google\'s fast, cheap option'
    }
}


# ============================================
# Version Information
# ============================================

__version__ = '0.1.0'
__author__ = 'Tanvi Shetty'


if __name__ == "__main__":
    # Test configuration
    print(get_provider_summary())
    print("\nAvailable models:")
    for model, desc in AVAILABLE_MODELS.get(LLM_PROVIDER, {}).items():
        print(f"  - {model}: {desc}")