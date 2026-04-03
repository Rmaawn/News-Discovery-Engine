import time
import requests

def retry_on_error(func, max_retries=3, logger=None):
    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.RequestException as e: # Catches all network/timeout errors
                if attempt < max_retries - 1:
                    wait = (attempt + 1) * 10
                    if logger:
                        logger.warning(f"Network error, retry in {wait}s ({attempt + 1}/{max_retries})")
                    time.sleep(wait)
                else:
                    if logger:
                        logger.error(f"Max retries reached for {func.__name__}")
                    raise
            except Exception as e:
                if logger:
                    logger.error(f"Error in {func.__name__}: {str(e)}")
                raise
    return wrapper
