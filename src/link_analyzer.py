"""
Link Analyzer Module with Better Prompts
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

Your task is to review the provided list of links from a company website and identify which ones are most relevant for creating a comprehensive brochure.

Common relevant page types for any company:
- "about" or "about us" - Company history, mission, team
- "products" or "solutions" - What they offer
- "services" - Services they provide
- "careers" or "jobs" - Employment opportunities
- "contact" - How to reach them
- "news" or "blog" - Latest updates
- "portfolio" or "work" - Past projects or work
- "team" or "leadership" - Key people
- "locations" - Office locations

Rules:
- Ignore links to privacy policy, terms of service, or legal pages
- Ignore social media links (LinkedIn, Twitter, Facebook, Instagram)
- Ignore login/registration pages
- Ignore links that are clearly not relevant to the company
- Prioritize pages that provide substantive information about the company

Respond in JSON format with this structure:
{
    "links": [
        {"type": "about page", "url": "https://company.com/about"},
        {"type": "services", "url": "https://company.com/services"},
        {"type": "careers", "url": "https://company.com/careers"}
    ]
}

Only include links you believe are truly relevant. If no links are relevant, return an empty array."""

def get_link_analysis_user_prompt(url: str, links: List[str]) -> str:
    """Build the user prompt for link analysis."""
    prompt = f"Website URL: {url}\n\n"
    
    if not links:
        prompt += "No links found on this website."
        return prompt
    
    prompt += "Here are all the links found on the website (please analyze each one):\n\n"
    
    # Group links by domain for better context
    import urllib.parse
    base_domain = urllib.parse.urlparse(url).netloc
    
    internal_links = []
    external_links = []
    
    for link in links:
        parsed = urllib.parse.urlparse(link)
        if parsed.netloc == base_domain or not parsed.netloc:
            internal_links.append(link)
        else:
            external_links.append(link)
    
    if internal_links:
        prompt += "Internal Links (same domain):\n"
        for link in internal_links:
            prompt += f"  - {link}\n"
        prompt += "\n"
    
    if external_links:
        prompt += "External Links (different domains - usually less relevant):\n"
        for link in external_links[:10]:  # Limit external links
            prompt += f"  - {link}\n"
        prompt += "\n"
    
    prompt += """
Please identify the most relevant internal pages for creating a comprehensive company brochure.
Focus on pages that contain substantive information about the company, its offerings, and its people.
Consider the company type and what information would be most valuable for a brochure.

Return your analysis in JSON format."""
    
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
                # Try to recover
                return _recover_links(all_links)
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            # Try to extract links from raw text
            extracted = _extract_links_from_text(result)
            if extracted:
                return {"links": extracted}
            else:
                # Fallback: use common page names
                return _recover_links(all_links)
            
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        # Fallback: use common page names
        return _recover_links(all_links)

def _recover_links(all_links: List[str]) -> Dict[str, Any]:
    """
    Fallback: Try to find relevant links using common patterns.
    
    Args:
        all_links: List of all links
        
    Returns:
        Dictionary with recovered links
    """
    import urllib.parse
    
    relevant_types = {
        'about': ['about', 'about-us', 'aboutus', 'who-we-are', 'company'],
        'services': ['services', 'solutions', 'offerings'],
        'products': ['products', 'product', 'merchandise'],
        'careers': ['careers', 'jobs', 'join-us', 'work-with-us'],
        'contact': ['contact', 'contact-us', 'get-in-touch'],
        'news': ['news', 'blog', 'press', 'updates'],
        'portfolio': ['portfolio', 'work', 'projects', 'case-studies'],
        'team': ['team', 'leadership', 'people', 'staff']
    }
    
    links = []
    base_domain = urllib.parse.urlparse(all_links[0] if all_links else '').netloc
    
    for link in all_links:
        link_lower = link.lower()
        for page_type, keywords in relevant_types.items():
            if any(keyword in link_lower for keyword in keywords):
                links.append({"type": page_type, "url": link})
                break
    
    return {"links": links}

def _extract_links_from_text(text: str) -> List[Dict[str, str]]:
    """Fallback: Extract links from raw text response."""
    import re
    links = []
    
    # Look for URL patterns
    url_pattern = r'https?://[^\s\'"]+'
    urls = re.findall(url_pattern, text)
    
    for url in urls[:10]:  # Limit to 10 links
        # Try to determine page type from URL
        url_lower = url.lower()
        page_type = 'page'
        if 'about' in url_lower:
            page_type = 'about'
        elif 'service' in url_lower or 'solution' in url_lower:
            page_type = 'services'
        elif 'product' in url_lower:
            page_type = 'products'
        elif 'career' in url_lower or 'job' in url_lower:
            page_type = 'careers'
        elif 'contact' in url_lower:
            page_type = 'contact'
        elif 'news' in url_lower or 'blog' in url_lower:
            page_type = 'news'
        
        links.append({"type": page_type, "url": url})
    
    return links

def is_ollama_running() -> bool:
    """Check if Ollama server is running."""
    import requests
    try:
        response = requests.get("http://localhost:11434", timeout=2)
        return response.status_code == 200
    except:
        return False