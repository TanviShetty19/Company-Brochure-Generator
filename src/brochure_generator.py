"""
Brochure Generator Module - Creates company brochures using LLM
"""

import logging
from typing import Dict, Any
from datetime import datetime

from openai import OpenAI
from .config import get_provider_config, MAX_CONTENT_LENGTH
from .scraper import fetch_website_contents
from .link_analyzer import select_relevant_links

logger = logging.getLogger(__name__)

# Initialize client
provider_config = get_provider_config()
client = OpenAI(
    base_url=provider_config['base_url'],
    api_key=provider_config['api_key']
)
MODEL = provider_config['model']
PROVIDER_NAME = provider_config.get('provider', 'ollama')

def get_brochure_system_prompt() -> str:
    """Get the system prompt for brochure generation."""
    return """
You are a professional brochure writer. Your task is to create compelling company brochures.

Based on the provided company information, create a professional brochure that includes:

1. **Company Overview**: What the company does, its mission, and values
2. **Products/Services**: What they offer to customers
3. **Company Culture**: Work environment, values, team
4. **Achievements**: Key milestones, awards, recognition
5. **Customer Success**: Testimonials, case studies, or customer base
6. **Career Opportunities**: If there are job openings or career information
7. **Contact Information**: How to reach the company

Style Guidelines:
- Write in an engaging, professional tone
- Use clear headings and sections
- Include bullet points for key features
- Keep paragraphs concise and readable
- Highlight unique selling points

Format the response in Markdown. Do not wrap in code blocks.
"""

def get_brochure_user_prompt(company_name: str, url: str) -> str:
    """
    Build the user prompt for brochure generation.
    Includes website content and page analysis.
    """
    prompt = f"""
Company Name: {company_name}
Website: {url}

Please create a professional brochure for this company based on the information from their website.

"""
    try:
        # Get relevant links and content
        relevant_links = select_relevant_links(url)
        
        if relevant_links and 'links' in relevant_links and relevant_links['links']:
            prompt += "\n## Website Content\n"
            
            for link_info in relevant_links['links']:
                page_type = link_info.get('type', 'page')
                page_url = link_info.get('url')
                
                if not page_url:
                    continue
                
                try:
                    content = fetch_website_contents(page_url)
                    prompt += f"\n### {page_type.upper()} ({page_url})\n"
                    prompt += content[:MAX_CONTENT_LENGTH] + "\n"
                except Exception as e:
                    logger.warning(f"Could not fetch {page_url}: {e}")
        else:
            # Fallback: Just use the homepage
            content = fetch_website_contents(url)
            prompt += f"\n## Homepage Content\n{content[:MAX_CONTENT_LENGTH]}"
            
    except Exception as e:
        logger.error(f"Error gathering website content: {e}")
        prompt += f"\n## Website Content\nUnable to fetch detailed content. Please create a general brochure about {company_name}."
    
    return prompt

def generate_brochure(company_name: str, url: str, max_retries: int = 3) -> Dict[str, Any]:
    """
    Generate a company brochure using LLM.
    
    Args:
        company_name: Name of the company
        url: Website URL
        max_retries: Number of retry attempts
    
    Returns:
        Dictionary with brochure content and metadata
    """
    logger.info(f"Generating brochure for {company_name} using {PROVIDER_NAME} model: {MODEL}")
    
    metadata = {
        "company_name": company_name,
        "url": url,
        "model": MODEL,
        "provider": PROVIDER_NAME,
        "generated_at": datetime.now().isoformat(),
        "tokens_used": 0
    }
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": get_brochure_system_prompt()},
                    {"role": "user", "content": get_brochure_user_prompt(company_name, url)}
                ],
                temperature=0.7,  # Slightly creative but not too random
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            metadata['content'] = content
            
            # Extract token usage if available
            if hasattr(response, 'usage'):
                metadata['tokens_used'] = {
                    'prompt': response.usage.prompt_tokens,
                    'completion': response.usage.completion_tokens,
                    'total': response.usage.total_tokens
                }
            
            logger.info(f"Brochure generated successfully")
            return metadata
            
        except Exception as e:
            logger.error(f"Brochure generation failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                continue
            metadata['error'] = str(e)
            return metadata
    
    metadata['error'] = "Max retries exceeded"
    return metadata

# For testing
if __name__ == "__main__":
    result = generate_brochure("Edward Donner", "https://edwarddonner.com")
    print(f"Generated brochure for {result['company_name']}")
    print(f"Model used: {result['model']}")
    print("\nContent preview:")
    print(result.get('content', '')[:500])