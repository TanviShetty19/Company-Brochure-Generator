"""
Link Analyzer Module with Error Handling
"""

import json
import logging
from typing import Dict, List, Any, Optional

from openai import OpenAI
from config import get_provider_config
from scraper import fetch_website_links
from logger import logger
from retry_utils import retry_on_error

# Initialize client with provider configuration
try:
    provider_config = get_provider_config()
    client = OpenAI(
        base_url=provider_config['base_url'],
        api_key=provider_config['api_key']
    )
    MODEL = provider_config['model']
    PROVIDER_NAME = provider_config['provider']
except Exception as e:
    logger.error(f"Failed to initialize LLM client: {e}")
    raise

def get_link_analysis_system_prompt() -> str:
    """Get the system prompt for link analysis."""
    return """You are an AI assistant that analyzes website links to identify relevant pages for a company brochure.

Your task:
1. Review the provided list of links from a company website
2. Identify which links are most relevant for a professional brochure
3. Categorize each link with a descriptive type

Relevant page types include:
- "about" or "about us" pages
- "careers" or "jobs" pages
- "products" or "solutions" pages
- "services" pages
- "contact" pages
- "news" or "blog" pages

Rules:
- Ignore links to privacy policy, terms of service, or legal pages
- Ignore social media links (LinkedIn, Twitter, Facebook, etc.)
- Ignore login/registration pages
- Ignore links that are clearly not relevant to the company

Respond in JSON format with this structure:
{
    "links": [
        {"type": "about page", "url": "https://company.com/about"},
        {"type": "careers page", "url": "https://company.com/careers"}
    ]
}"""

def get_link_analysis_user_prompt(url: str, links: List[str]) -> str:
    """Build the user prompt for link analysis."""
    prompt = f"Website URL: {url}\n\nHere are all the links found on the website:\n"
    for link in links:
        prompt += f"\n- {link}"
    prompt += "\n\nPlease analyze these links and identify which ones are most relevant for a company brochure."
    return prompt

@retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
def select_relevant_links(url: str) -> Dict[str, Any]:
    """
    Use LLM to identify relevant links from a website.
    
    Args:
        url: Website URL to analyze
        
    Returns:
        Dictionary with 'links' key containing relevant links
    """
    logger.info(f"Analyzing links for {url}")
    
    # Get all links
    all_links = fetch_website_links(url)
    if not all_links:
        logger.warning(f"No links found for {url}")
        return {"links": []}
    
    logger.debug(f"Found {len(all_links)} total links")
    
    # Build prompts
    system_prompt = get_link_analysis_system_prompt()
    user_prompt = get_link_analysis_user_prompt(url, all_links)
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = response.choices[0].message.content
        logger.debug(f"Raw LLM response: {result[:200]}...")
        
        # Parse JSON
        try:
            links_data = json.loads(result)
            if isinstance(links_data, dict) and 'links' in links_data:
                logger.info(f"Found {len(links_data['links'])} relevant links")
                return links_data
            else:
                logger.warning(f"Unexpected JSON format: {result[:200]}")
                return {"links": []}
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            # Try to extract links from raw text
            extracted = _extract_links_from_text(result)
            return {"links": extracted}
            
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise

def _extract_links_from_text(text: str) -> List[Dict[str, str]]:
    """Fallback: Extract links from raw text response."""
    import re
    links = []
    
    # Look for URL patterns
    url_pattern = r'https?://[^\s\'"]+'
    urls = re.findall(url_pattern, text)
    
    for url in urls[:10]:  # Limit to 10 links
        links.append({"type": "page", "url": url})
    
    return links

def is_ollama_running() -> bool:
    """Check if Ollama server is running."""
    import requests
    try:
        response = requests.get("http://localhost:11434", timeout=2)
        return response.status_code == 200
    except:
        return False