"""URL shortener utility."""
import os
from typing import Optional

def create_short_url(long_url: str) -> Optional[str]:
    """Create a short URL using various URL shortening services.
    
    Args:
        long_url: The URL to shorten
        
    Returns:
        str: The shortened URL, or None if shortening failed or requests module is not installed
    """
    try:
        import requests
    except ImportError:
        return None
    try:
        # First try TinyURL API
        response = requests.get(
            f"https://tinyurl.com/api-create.php?url={long_url}",
            timeout=5
        )
        if response.status_code == 200:
            return response.text.strip()
    except:
        pass

    try:
        # Fallback to is.gd API
        response = requests.get(
            f"https://is.gd/create.php?format=simple&url={long_url}",
            timeout=5
        )
        if response.status_code == 200:
            return response.text.strip()
    except:
        pass

    try:
        # Fallback to v.gd API
        response = requests.get(
            f"https://v.gd/create.php?format=simple&url={long_url}",
            timeout=5
        )
        if response.status_code == 200:
            return response.text.strip()
    except:
        pass

    return None