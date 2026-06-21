"""
Web Scraping Module with Caching Support
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from typing import List, Optional, Tuple
import logging

from logger import logger
from retry_utils import retry_on_error
from cache_manager import cache

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

@retry_on_error(max_retries=2, delay=1.0)
def fetch_website_contents(
    url: str, 
    max_length: int = 5000,
    timeout: int = 10,
    use_cache: bool = True
) -> str:
    """
    Fetch and parse website content with caching support.
    
    Args:
        url: Website URL to fetch
        max_length: Maximum characters to return
        timeout: Request timeout in seconds
        use_cache: Whether to use cached content
        
    Returns:
        Cleaned text content from the website
    """
    # Check cache first
    if use_cache:
        cached_content = cache.get(url)
        if cached_content:
            logger.debug(f"Using cached content for {url}")
            return cached_content
    
    try:
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            logger.warning(f"Invalid URL format: {url}")
            return f"[Error: Invalid URL format - {url}]"
        
        # Fetch the page
        logger.debug(f"Fetching: {url}")
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()  # Raise HTTP errors
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()
        
        # Get title
        title = soup.title.string if soup.title else "No title"
        
        # Get main content
        # Try to find main content areas
        main_content = None
        for selector in ['main', 'article', '.content', '#content', '.main']:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if main_content:
            text = main_content.get_text(separator='\n', strip=True)
        else:
            # Fallback: get all text
            text = soup.get_text(separator='\n', strip=True)
        
        # Clean up whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)
        
        # Truncate if needed
        if len(text) > max_length:
            logger.debug(f"Truncating content from {len(text)} to {max_length} characters")
            text = text[:max_length] + "\n...[truncated]"
        
        # Combine title and content
        full_text = f"{title}\n\n{text}"
        
        # Cache the content
        if use_cache and not full_text.startswith('[Error:'):
            cache.set(url, full_text)
        
        return full_text
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching {url}")
        return f"[Error: Request timeout - {url}]"
        
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error fetching {url}")
        return f"[Error: Connection failed - {url}]"
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error fetching {url}: {e}")
        return f"[Error: HTTP {e.response.status_code} - {url}]"
        
    except Exception as e:
        logger.error(f"Unexpected error fetching {url}: {e}")
        return f"[Error: {str(e)} - {url}]"

def fetch_website_links(url: str, timeout: int = 10, use_cache: bool = True) -> List[str]:
    """
    Extract all links from a website with caching support.
    
    Args:
        url: Website URL
        timeout: Request timeout
        use_cache: Whether to use cached content
        
    Returns:
        List of absolute URLs
    """
    # Check cache for links
    if use_cache:
        cache_key = f"_links_{url}"
        cached_links = cache.get(cache_key)
        if cached_links:
            try:
                # Cache stores links as JSON string
                import json
                links = json.loads(cached_links)
                logger.debug(f"Using cached links for {url}")
                return links
            except:
                pass
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Skip empty links and javascript
            if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            
            # Convert relative to absolute URL
            absolute_url = urljoin(url, href)
            
            # Only include http/https links
            if absolute_url.startswith(('http://', 'https://')):
                links.append(absolute_url)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_links = []
        for link in links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)
        
        logger.debug(f"Found {len(unique_links)} links on {url}")
        
        # Cache the links
        if use_cache and unique_links:
            import json
            cache_key = f"_links_{url}"
            cache.set(cache_key, json.dumps(unique_links))
        
        return unique_links
        
    except Exception as e:
        logger.error(f"Error fetching links from {url}: {e}")
        return []