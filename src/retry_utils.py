"""
Retry Utilities for Robust API Calls
"""

import time
import logging
from functools import wraps
from typing import Type, Tuple, Optional, Callable, Any
from openai import RateLimitError, APIError, APIConnectionError

logger = logging.getLogger(__name__)

def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (
        RateLimitError,
        APIError,
        APIConnectionError,
        ConnectionError,
        TimeoutError,
    ),
    on_retry: Optional[Callable] = None
):
    """
    Decorator to retry a function when certain exceptions occur.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry (exponential backoff)
        exceptions: Tuple of exception types to retry on
        on_retry: Optional callback function called before each retry
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(
                            f"Max retries ({max_retries}) exceeded for {func.__name__}: {e}"
                        )
                        break
                    
                    # Wait before retrying
                    logger.warning(
                        f"Error in {func.__name__} (attempt {attempt + 1}/{max_retries + 1}): {e}"
                    )
                    logger.info(f"Retrying in {current_delay:.2f} seconds...")
                    
                    # Call the retry callback if provided
                    if on_retry:
                        on_retry(attempt + 1, e)
                    
                    time.sleep(current_delay)
                    current_delay *= backoff  # Exponential backoff
            
            # If we exhausted retries, raise the last exception
            if last_exception:
                raise last_exception
            
            return None
        
        return wrapper
    return decorator