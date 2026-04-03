import time
import requests


def retry_on_error(max_retries=3, logger=None):
    """
    Decorator factory برای retry کردن تابع‌هایی که ممکن است خطاهای شبکه‌ای داشته باشند.

    استفاده:
    @retry_on_error(max_retries=5, logger=my_logger)
    def my_func(...):
        ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:  # خطاهای شبکه/timeout
                    if attempt < max_retries - 1:
                        wait = (attempt + 1) * 10
                        if logger:
                            logger.warning(
                                f"Network error in {func.__name__}: {e}. "
                                f"Retrying in {wait}s ({attempt + 1}/{max_retries})"
                            )
                        time.sleep(wait)
                    else:
                        if logger:
                            logger.error(
                                f"Max retries reached for {func.__name__}: {e}"
                            )
                        raise
                except Exception as e:
                    # خطاهای غیرشبکه‌ای را retry نمی‌کنیم
                    if logger:
                        logger.error(
                            f"Error in {func.__name__}: {str(e)}"
                        )
                    raise
        return wrapper
    return decorator
