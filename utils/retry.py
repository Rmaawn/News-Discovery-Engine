import time
import requests

def _is_retryable_http_error(exc: requests.exceptions.RequestException) -> bool:
    resp = getattr(exc, "response", None)
    if resp is None:
        return True  # timeout/dns/connection
    code = resp.status_code
    # فقط 5xx و 429 قابل retry
    return code >= 500 or code == 429

def retry_on_error(max_retries=8, logger=None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    retryable = _is_retryable_http_error(e)
                    if (attempt < max_retries - 1) and retryable:
                        wait = min((attempt + 1) * 10, 60)
                        if logger:
                            logger.warning(
                                f"Retryable network/http error in {func.__name__}: {e}. "
                                f"Retrying in {wait}s ({attempt+1}/{max_retries})"
                            )
                        time.sleep(wait)
                        continue

                    if logger:
                        logger.error(f"Non-retryable or max-retries reached in {func.__name__}: {e}")
                    raise
                except Exception as e:
                    if logger:
                        logger.error(f"Error in {func.__name__}: {e}")
                    raise
        return wrapper
    return decorator
