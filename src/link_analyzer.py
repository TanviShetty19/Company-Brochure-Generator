"""
Link Analyzer Module - Uses LLM to identify relevant company pages
Supports multiple providers (Ollama, OpenAI, Gemini)
"""

import json
import logging
from typing import Dict, List, Any

from openai import OpenAI
from .config import get_provider_config, MAX_CONTENT_LENGTH
from .scraper import fetch_website_links

# Set up logging
logger = logging.getLogger(__name__)

# Initialize client with provider configuration
provider_config = get_provider_config()
client = OpenAI(
    base_url=provider_config['base_url'],
    api_key=provider_config['api_key']
)
MODEL = provider_config['model']
PROVIDER_NAME = provider_config.get('provider', 'ollama')

def get_link_analysis_system_prompt() -> str:
    """Get the system prompt for link analysis."""
    return """
You are an AI assistant that analyzes website links to identify relevant pages for a company brochure.

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
- Ignore links that are clearly not relevant to the company (e.g., external links, ads)
- Combine similar pages if they appear to serve the same purpose

Respond in JSON format with this structure:
{
    "links": [
        {"type": "about page", "url": "https://company.com/about"},
        {"type": "careers page", "url": "https://company.com/careers"},
        {"type": "products", "url": "https://company.com/products"}
    ]
}

Only include links you believe are relevant. If no links are relevant, return an empty array.
"""

def get_link_analysis_user_prompt(url: str, links: List[str]) -> str:
    """Build the user prompt for link analysis."""
    prompt = f"""
Website URL: {url}

Here are all the links found on the website:
"""
    for link in links:
        prompt += f"\n- {link}"
    
    prompt += "\n\nPlease analyze these links and identify which ones are most relevant for a company brochure."
    return prompt

def select_relevant_links(url: str, max_retries: int = 3) -> Dict[str, Any]:
    """
    Use LLM to identify relevant links from a website.
    
    Args:
        url: Website URL to analyze
        max_retries: Number of retry attempts for failed calls
    
    Returns:
        Dictionary with 'links' key containing relevant links
    """
    logger.info(f"Analyzing links for {url} using {PROVIDER_NAME} model: {MODEL}")
    
    # Get all links
    all_links = fetch_website_links(url)
    if not all_links:
        logger.warning(f"No links found for {url}")
        return {"links": []}
    
    # Build prompts
    system_prompt = get_link_analysis_system_prompt()
    user_prompt = get_link_analysis_user_prompt(url, all_links)
    
    # Try with retries
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent results
                response_format={"type": "json_object"}
            )
            
            result = response.choices[0].message.content
            
            # Parse JSON
            try:
                links_data = json.loads(result)
                if isinstance(links_data, dict) and 'links' in links_data:
                    logger.info(f"Found {len(links_data['links'])} relevant links")
                    return links_data
                else:
                    logger.warning(f"Unexpected JSON format: {result[:200]}")
                    if attempt < max_retries - 1:
                        continue
                    return {"links": []}
            
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    continue
                # Try to extract links from the raw text
                return extract_links_from_text(result)
        
        except Exception as e:
            logger.error(f"LLM call failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                continue
            return {"links": []}
    
    return {"links": []}

def extract_links_from_text(text: str) -> Dict[str, Any]:
    """Fallback: Try to extract links from raw text response."""
    import re
    links = []
    
    # Look for URL patterns in the text
    url_pattern = r'https?://[^\s\'"]+'
    urls = re.findall(url_pattern, text)
    
    for url in urls:
        links.append({"type": "page", "url": url})
    
    return {"links": links}

# For testing
if __name__ == "__main__":
    # Test with a known website
    result = select_relevant_links("https://edwarddonner.com")
    print(json.dumps(result, indent=2))