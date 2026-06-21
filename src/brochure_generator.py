"""
Brochure Generator Module with Flexible Prompts
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
    """Get the flexible system prompt for brochure generation."""
    return """You are a professional brochure writer who adapts to different types of companies.

Your task is to create a compelling, professional brochure based on the company's website content.

First, analyze the company type from the content provided:
- If it's a product company, focus on products and features
- If it's a service company, focus on services and expertise
- If it's a retail/store, focus on shopping experience and products
- If it's a restaurant/food, focus on cuisine, ambiance, and dining experience
- If it's a non-profit, focus on mission and impact
- If it's a technology company, focus on innovation and solutions
- If it's a manufacturer, focus on quality and production
- If it's a creative agency, focus on portfolio and creativity

Then create a brochure with these sections (adapt based on company type):

1. **Company Overview**: What they do, their mission, and unique value
2. **Key Offerings**: Products, services, or experiences they provide
3. **What Makes Them Special**: Unique selling points, competitive advantages
4. **Customer Experience**: What customers can expect
5. **About the Team/Culture**: Company values, work environment
6. **Contact and Call to Action**: How to get in touch or take action

Style Guidelines:
- Write in an engaging, professional tone appropriate for the company type
- Use clear headings and sections
- Include bullet points for key features
- Keep paragraphs concise and readable
- Be enthusiastic but authentic
- Highlight what makes this company unique

Format the response in Markdown. Do not wrap in code blocks."""

def detect_company_type(content: str) -> str:
    """
    Detect the type of company based on content.
    
    Args:
        content: Website content to analyze
        
    Returns:
        Company type as a string
    """
    content_lower = content.lower()
    
    # Patterns for different company types
    patterns = {
        'restaurant': ['restaurant', 'cafe', 'dining', 'cuisine', 'menu', 'chef', 'food', 'drink'],
        'retail': ['shop', 'store', 'shopping', 'buy', 'product', 'merchandise', 'retail'],
        'nonprofit': ['donate', 'nonprofit', 'charity', 'volunteer', 'foundation', 'non-profit', 'mission'],
        'technology': ['software', 'tech', 'platform', 'digital', 'api', 'cloud', 'saas', 'innovation'],
        'manufacturing': ['manufacture', 'produce', 'factory', 'industrial', 'production', 'quality control'],
        'creative': ['creative', 'design', 'studio', 'agency', 'portfolio', 'creative services'],
        'professional': ['consulting', 'advisory', 'professional', 'expertise', 'services']
    }
    
    scores = {}
    for company_type, keywords in patterns.items():
        score = sum(content_lower.count(keyword) for keyword in keywords)
        if score > 0:
            scores[company_type] = score
    
    if not scores:
        return 'general'
    
    # Return the type with the highest score
    return max(scores, key=scores.get)

@retry_on_error(max_retries=3, delay=1.0, backoff=2.0)
def generate_brochure(company_name: str, url: str) -> Dict[str, Any]:
    """
    Generate a company brochure using LLM with adaptive prompts.
    
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
    
    # Detect company type
    company_type = detect_company_type(content)
    logger.info(f"Detected company type: {company_type}")
    
    # Build user prompt with company type awareness
    user_prompt = _build_user_prompt(company_name, url, content, company_type)
    
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
            "company_type": company_type,
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
        
        logger.info(f"Brochure generated successfully for {company_type} company")
        return result
        
    except Exception as e:
        logger.error(f"Brochure generation failed: {e}")
        return {
            "company_name": company_name,
            "url": url,
            "model": MODEL,
            "provider": PROVIDER_NAME,
            "company_type": company_type,
            "generated_at": datetime.now().isoformat(),
            "content": f"# Brochure Generation Failed\n\nSorry, I couldn't generate a brochure for {company_name}.\n\nError: {str(e)}",
            "success": False,
            "error": str(e)
        }

def _build_user_prompt(company_name: str, url: str, content: str, company_type: str) -> str:
    """
    Build the user prompt based on company type.
    
    Args:
        company_name: Name of the company
        url: Website URL
        content: Website content
        company_type: Detected company type
        
    Returns:
        User prompt string
    """
    # Type-specific guidance
    type_guidance = {
        'restaurant': "Focus on the dining experience, cuisine type, ambiance, menu highlights, and what makes this restaurant special. Include information about the chef, opening hours, and reservations if available.",
        'retail': "Focus on the shopping experience, product quality, selection, customer service, and any unique shopping features. Include information about store locations or online shopping if available.",
        'nonprofit': "Focus on the organization's mission, impact, how donations help, volunteer opportunities, and success stories. Include information about programs and how to get involved.",
        'technology': "Focus on innovation, product features, technology stack, solutions to customer problems, and market position. Include information about technical advantages and future roadmap.",
        'manufacturing': "Focus on product quality, production processes, quality control, industry standards, and expertise. Include information about capabilities and facilities.",
        'creative': "Focus on creativity, design approach, portfolio highlights, client success stories, and creative process. Include information about the team and services offered.",
        'professional': "Focus on expertise, team credentials, client results, methodology, and professional services. Include information about industries served and case studies.",
        'general': "Create a comprehensive overview that covers what the company does, who they serve, and why they're unique. Adapt based on the content provided."
    }
    
    guidance = type_guidance.get(company_type, type_guidance['general'])
    
    prompt = f"""
Company Name: {company_name}
Website: {url}
Detected Company Type: {company_type}

Website Content:
{content}

Guidance for this company type:
{guidance}

Create a professional brochure that captures the essence of this company. Make it engaging, informative, and well-structured. Highlight what makes them unique and why someone would want to engage with them.

Remember to:
1. Adapt the content to fit the specific company type
2. Focus on practical, useful information
3. Write in a tone appropriate for their audience
4. Make it visually appealing in Markdown format
"""
    
    return prompt[:8000]  # Limit prompt length

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
<!-- Type: {result.get('company_type', 'unknown')} -->
<!-- Generated: {result['generated_at']} -->
<!-- Model: {result['model']} -->
<!-- Provider: {result['provider']} -->
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(metadata + content)
    
    logger.info(f"Brochure saved to {filepath}")
    return filepath