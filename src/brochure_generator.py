"""
Brochure Generator Module with Error Handling
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from openai import OpenAI
from config import get_provider_config, OUTPUT_DIR, MAX_CONTENT_LENGTH
from scraper import fetch_website_contents
from link_analyzer import select_relevant_links
from logger import logger
from retry_utils import retry_on_error

# Initialize client with error handling
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

def get_brochure_system_prompt() -> str:
    """Get the system prompt for brochure generation."""
    return """You are a professional brochure writer. Create a compelling company brochure.

Based on the provided company information, create a professional brochure that includes:

1. **Company Overview**: What they do, mission, and values
2. **Products/Services**: What they offer to customers
3. **Company Culture**: Work environment, values, team
4. **Achievements**: Key milestones, awards, recognition
5. **Career Opportunities**: If there are job openings or career information

Style Guidelines:
- Write in an engaging, professional tone
- Use clear headings and sections
- Include bullet points for key features
- Keep paragraphs concise and readable

Format the response in Markdown. Do not wrap in code blocks."""

@retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
def generate_brochure(company_name: str, url: str) -> Dict[str, Any]:
    """
    Generate a company brochure using LLM.
    
    Args:
        company_name: Name of the company
        url: Website URL
        
    Returns:
        Dictionary with brochure content and metadata
    """
    logger.info(f"Generating brochure for {company_name} using {MODEL}")
    
    # Gather content
    content = _gather_website_content(url)
    if not content:
        logger.warning("No website content available, using minimal prompt")
        content = "Unable to fetch website content. Please create a general brochure based on the company name."
    
    # Build prompt
    user_prompt = f"Company Name: {company_name}\nWebsite: {url}\n\n## Website Content\n{content}"
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": get_brochure_system_prompt()},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        result = {
            "company_name": company_name,
            "url": url,
            "model": MODEL,
            "provider": PROVIDER_NAME,
            "generated_at": datetime.now().isoformat(),
            "content": response.choices[0].message.content,
            "success": True
        }
        
        # Extract token usage
        if hasattr(response, 'usage'):
            result['tokens'] = {
                'prompt': response.usage.prompt_tokens,
                'completion': response.usage.completion_tokens,
                'total': response.usage.total_tokens
            }
        
        logger.info(f"Brochure generated successfully")
        return result
        
    except Exception as e:
        logger.error(f"Brochure generation failed: {e}")
        return {
            "company_name": company_name,
            "url": url,
            "model": MODEL,
            "provider": PROVIDER_NAME,
            "generated_at": datetime.now().isoformat(),
            "content": f"# Brochure Generation Failed\n\nSorry, I couldn't generate a brochure for {company_name}.\n\nError: {str(e)}",
            "success": False,
            "error": str(e)
        }

def _gather_website_content(url: str, max_pages: int = 5) -> str:
    """
    Gather content from relevant website pages.
    
    Args:
        url: Website URL
        max_pages: Maximum pages to fetch
        
    Returns:
        Combined content from all pages
    """
    combined_content = ""
    
    try:
        # Get relevant links
        relevant_links = select_relevant_links(url)
        
        if relevant_links and 'links' in relevant_links:
            pages_fetched = 0
            for link_info in relevant_links['links']:
                if pages_fetched >= max_pages:
                    break
                    
                page_url = link_info.get('url')
                page_type = link_info.get('type', 'page')
                
                if not page_url:
                    continue
                
                try:
                    content = fetch_website_contents(page_url, max_length=MAX_CONTENT_LENGTH)
                    combined_content += f"\n\n### {page_type.upper()} ({page_url})\n\n{content}"
                    pages_fetched += 1
                    logger.debug(f"Fetched page: {page_url}")
                except Exception as e:
                    logger.warning(f"Could not fetch {page_url}: {e}")
        
        # Fallback: use homepage only
        if not combined_content:
            logger.info("No relevant links found, using homepage only")
            homepage_content = fetch_website_contents(url, max_length=MAX_CONTENT_LENGTH)
            combined_content = f"\n\n### Homepage ({url})\n\n{homepage_content}"
            
    except Exception as e:
        logger.error(f"Error gathering content: {e}")
        combined_content = "Error gathering website content."
    
    return combined_content[:8000]  # Limit total content length

def save_brochure(result: Dict[str, Any]) -> Path:
    """
    Save brochure to file.
    
    Args:
        result: Brochure generation result
        
    Returns:
        Path to saved file
    """
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(exist_ok=True)
    
    # Create filename
    company_name = result['company_name'].replace(' ', '_').lower()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{company_name}_{timestamp}.md"
    filepath = output_dir / filename
    
    # Write content with metadata
    content = result['content']
    metadata = f"""
<!-- Generated Brochure -->
<!-- Company: {result['company_name']} -->
<!-- Generated: {result['generated_at']} -->
<!-- Model: {result['model']} -->
<!-- Provider: {result['provider']} -->
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(metadata + content)
    
    logger.info(f"Brochure saved to {filepath}")
    return filepath