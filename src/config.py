"""
Configuration for the Company Brochure Generator.
Supports multiple LLM providers with Ollama as the default.
"""
import os
from dotenv import load_dotenv
load_dotenv(override=True)

# ============================================
# Provider Configuration
# ============================================

# Choose your provider: 'ollama', 'openai', or 'gemini'
LLM_PROVIDER=os.getenv("LLM_PROVIDER","OLLAMA").lower()

# Ollama Configuration (Default - Free & Local)
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434/v1')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama3.2:1b')  # or 'deepseek-r1:1.5b'
# OpenAI Configuration (Paid - Optional)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')

# Google Gemini Configuration (Paid - Optional)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-lite')
GEMINI_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/openai/'

# ============================================
# Provider Resolution
# ============================================
def get_provider__config():
    if LLM_PROVIDER == "ollama":
        return {
            "base_url": OLLAMA_BASE_URL,,
            "api_key":"ollama",
            "model": OLLAMA_MODEL
        }
    elif LLM_PROVIDER == "openai":
        return {
            "base_url": None,
            "api_key": OPENAI_API_KEY,
            "model": OPENAI_MODEL
        }
    elif LLM_PROVIDER == "gemini":
        return {
            "base_url": GEMINI_BASE_URL,
            "api_key": GEMINI_API_KEY,
            "model": GEMINI_MODEL
        }
    else:
        raise ValueError(f"Unsupported LLM provider: {LLM_PROVIDER}. Please choose 'ollama', 'openai', or 'gemini'.")

# ============================================
# Application Configuration
# ============================================
#Content limits for the brochure generation
MAX_CONTETNT_LENGTH = 5000  # Max characters for input content
MAX_TOTAL_TOKENS=8000  # Max tokens for the entire response (adjust based on provider limits)
#Caching
CACHE_ENABLED =True
CACHE_EXPIRY_DAYS=7
#Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
#Output
OUTPUT_DIR = os.getenv("OUTPUT_DIR","output")
CACHE_DIR = os.getenv("CACHE_DIR","cache")
LOG_DIR = os.getenv("LOG_DIR","logs")

# ============================================
# Model Registry - Document which models work
# ============================================
# This registry helps users understand which models are available for each provider, their characteristics, and recommendations.
# You can add or remove models as needed. Also you could update  recommendations based on your testing and user feedback. This is meant to be a living document that evolves with the project.

MODEL_REGISTRY = {
    'ollama': {
        'llama3.2:1b': {
            'description': 'Lightweight Llama 3.2 (1B) - Fast, works on most computers',
            'recommended': True
        },
        'llama3.2': {
            'description': 'Full Llama 3.2 (3B) - Better quality, needs more RAM',
            'recommended': False
        },
        'deepseek-r1:1.5b': {
            'description': 'DeepSeek distilled (1.5B) - Good for reasoning tasks',
            'recommended': False
        },
        'phi3:mini': {
            'description': 'Microsoft Phi-3 Mini - Good balance of quality/speed',
            'recommended': False
        }
    },
    'openai': {
        'gpt-4.1-mini': {'description': 'OpenAI\'s latest small model', 'recommended': True},
        'gpt-5-nano': {'description': 'OpenAI\'s smallest model', 'recommended': False}
    },
    'gemini': {
        'gemini-2.5-flash-lite': {'description': 'Google\'s fast, cheap model', 'recommended': True}
    }
}

# ============================================
# Helper Functions
# ============================================

def get_provider_summary():
    """Get a human-readable summary of the current configuration."""
    config = get_provider_config()
    return f"""
Provider: {LLM_PROVIDER.upper()}
Model: {config['model']}
Base URL: {config['base_url'] or 'Default OpenAI URL'}
"""

def list_available_models():
    """List all available models for the current provider."""
    if LLM_PROVIDER in MODEL_REGISTRY:
        return MODEL_REGISTRY[LLM_PROVIDER]
    return {}

if __name__ == "__main__":
    print("Current Configuration:")
    print(get_provider_summary())
    print("\nAvailable models for this provider:")
    for model, info in list_available_models().items():
        print(f"  - {model}: {info['description']}")