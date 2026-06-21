"""
Cache Manager Module for Storing and Retrieving Cached Data
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

from config import CACHE_DIR, CACHE_EXPIRY_DAYS, CACHE_ENABLED
from logger import logger

class CacheManager:
    """
    Manages caching of website content and API responses.
    """
    
    def __init__(self, cache_dir: str = None, expiry_days: int = None):
        """
        Initialize the cache manager.
        
        Args:
            cache_dir: Directory to store cache files
            expiry_days: Number of days until cache expires
        """
        self.cache_dir = Path(cache_dir or CACHE_DIR)
        self.expiry_days = expiry_days or CACHE_EXPIRY_DAYS
        self.enabled = CACHE_ENABLED
        
        # Create cache directory if it doesn't exist
        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Cache directory initialized at {self.cache_dir}")
    
    def _get_cache_key(self, url: str) -> str:
        """
        Generate a unique cache key from a URL.
        
        Args:
            url: URL to generate key for
            
        Returns:
            MD5 hash of the URL
        """
        return hashlib.md5(url.encode()).hexdigest()
    
    def _get_cache_file_path(self, key: str) -> Path:
        """
        Get the file path for a cache key.
        
        Args:
            key: Cache key
            
        Returns:
            Path to the cache file
        """
        return self.cache_dir / f"{key}.json"
    
    def get(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached data for a URL.
        
        Args:
            url: URL to retrieve cache for
            
        Returns:
            Cached data or None if not found or expired
        """
        if not self.enabled:
            return None
        
        key = self._get_cache_key(url)
        file_path = self._get_cache_file_path(key)
        
        if not file_path.exists():
            logger.debug(f"Cache miss for {url}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if cache has expired
            cached_time = datetime.fromisoformat(data.get('cached_at', ''))
            if datetime.now() - cached_time > timedelta(days=self.expiry_days):
                logger.debug(f"Cache expired for {url}")
                file_path.unlink()  # Delete expired cache
                return None
            
            logger.debug(f"Cache hit for {url}")
            return data.get('content', '')
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Error reading cache for {url}: {e}")
            # Delete corrupted cache file
            try:
                file_path.unlink()
            except:
                pass
            return None
    
    def set(self, url: str, content: str) -> bool:
        """
        Store data in cache.
        
        Args:
            url: URL to cache
            content: Content to cache
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        key = self._get_cache_key(url)
        file_path = self._get_cache_file_path(key)
        
        data = {
            'url': url,
            'content': content,
            'cached_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=self.expiry_days)).isoformat()
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Cached content for {url}")
            return True
        except Exception as e:
            logger.error(f"Error caching content for {url}: {e}")
            return False
    
    def clear(self, url: str = None) -> int:
        """
        Clear cache for a specific URL or all cache.
        
        Args:
            url: URL to clear, or None to clear all
            
        Returns:
            Number of cache files cleared
        """
        count = 0
        
        if url:
            key = self._get_cache_key(url)
            file_path = self._get_cache_file_path(key)
            if file_path.exists():
                file_path.unlink()
                count = 1
        else:
            # Clear all cache files
            for file_path in self.cache_dir.glob('*.json'):
                file_path.unlink()
                count += 1
        
        logger.info(f"Cleared {count} cache files")
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        if not self.cache_dir.exists():
            return {'total_files': 0, 'total_size': 0}
        
        files = list(self.cache_dir.glob('*.json'))
        total_size = sum(f.stat().st_size for f in files)
        
        return {
            'total_files': len(files),
            'total_size': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'cache_dir': str(self.cache_dir)
        }

# Create a global cache instance
cache = CacheManager()