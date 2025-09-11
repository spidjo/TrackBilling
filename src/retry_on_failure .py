import logging
import time
import traceback
from functools import wraps
from typing import Callable, Any, Tuple

logger = logging.getLogger(__name__)

def retry_on_failure(max_retries: int = 3, initial_delay: int = 60, backoff_factor: int = 2):
    """
    Decorator to retry a function on failure with exponential backoff.

    Args:
        max_retries (int): Maximum retry attempts.
        initial_delay (int): Initial delay in seconds before retrying.
        backoff_factor (int): Multiplier for delay after each failure.

    Returns:
        Callable: Wrapped function with retry logic.
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            for attempt in range(1, max_retries + 1):
                try:
                    logger.info(f"[Retry Wrapper] Attempt {attempt}/{max_retries}")
                    return func(*args, **kwargs)  # Return immediately if successful
                except Exception as e:
                    logger.error(f"Error in attempt {attempt}: {str(e)}")
                    logger.debug(traceback.format_exc())

                    if attempt < max_retries:
                        logger.warning(f"Retrying in {delay} seconds...")
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.critical("Max retries reached. Aborting.")
                        raise  # Re-raise last exception after final attempt
        return wrapper
    return decorator
