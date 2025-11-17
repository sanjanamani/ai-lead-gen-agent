"""
Utility functions for caching, logging, retries, and data processing
"""

import json
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional
from functools import wraps
import time

from diskcache import Cache
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import colorlog

from config.settings import config


# ============================================
# Logging Setup
# ============================================

def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Setup colored console logger with file output"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler with colors
    console_handler = colorlog.StreamHandler()
    console_handler.setLevel(level)
    console_format = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s%(reset)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        }
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler
    log_file = config.log_dir / f"convexia_crm_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    return logger


# Global logger
logger = setup_logger("convexia_crm")


# ============================================
# Caching
# ============================================

# Initialize cache
cache = Cache(str(config.cache_dir)) if config.enable_cache else None


def cache_key(*args, **kwargs) -> str:
    """Generate a cache key from function arguments"""
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
    return hashlib.sha256(key_data.encode()).hexdigest()


def cached(expire: Optional[int] = None):
    """
    Decorator to cache function results
    
    Args:
        expire: Cache expiry in seconds (None = use config default)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not config.enable_cache or cache is None:
                return func(*args, **kwargs)
            
            # Generate cache key
            key = f"{func.__module__}.{func.__name__}:{cache_key(*args, **kwargs)}"
            
            # Check cache
            result = cache.get(key)
            if result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return result
            
            # Call function and cache result
            logger.debug(f"Cache miss for {func.__name__}")
            result = func(*args, **kwargs)
            
            # Calculate expiry
            expiry = expire if expire is not None else config.cache_expiry_hours * 3600
            cache.set(key, result, expire=expiry)
            
            return result
        return wrapper
    return decorator


def clear_cache():
    """Clear all cached data"""
    if cache:
        cache.clear()
        logger.info("Cache cleared")


# ============================================
# Retry Logic
# ============================================

def retry_with_backoff(
    max_attempts: Optional[int] = None,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying functions with exponential backoff
    
    Args:
        max_attempts: Maximum retry attempts (None = use config default)
        exceptions: Tuple of exceptions to retry on
    """
    max_attempts = max_attempts or config.max_retries
    
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(exceptions),
        before_sleep=lambda retry_state: logger.warning(
            f"Retrying {retry_state.fn.__name__} after failure "
            f"(attempt {retry_state.attempt_number}/{max_attempts})"
        )
    )


# ============================================
# Rate Limiting
# ============================================

class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, calls_per_minute: int):
        self.calls_per_minute = calls_per_minute
        self.interval = 60.0 / calls_per_minute
        self.last_call = 0
    
    def wait(self):
        """Wait if necessary to respect rate limit"""
        elapsed = time.time() - self.last_call
        if elapsed < self.interval:
            sleep_time = self.interval - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self.last_call = time.time()


# Global rate limiter
rate_limiter = RateLimiter(config.rate_limit_rpm)


# ============================================
# JSON Utilities
# ============================================

def clean_json_string(text: str) -> str:
    """
    Clean JSON from LLM output (remove markdown fences, extra text)
    """
    text = text.strip()
    
    # Remove markdown code fences
    if text.startswith("```"):
        # Remove opening fence
        text = text.lstrip("`")
        # Remove language hint (json, JSON, etc.)
        for lang in ["json", "JSON", "python", "PYTHON"]:
            if text.startswith(lang):
                text = text[len(lang):].strip()
        # Remove closing fence
        if text.endswith("```"):
            text = text[:-3].strip()
    
    # Find first JSON object/array
    start_chars = ["{", "["]
    start_idx = -1
    for i, char in enumerate(text):
        if char in start_chars:
            start_idx = i
            break
    
    if start_idx >= 0:
        text = text[start_idx:]
    
    return text


def parse_llm_json(raw_output: str, default: Any = None) -> Any:
    """
    Safely parse JSON from LLM output with fallback
    
    Args:
        raw_output: Raw text output from LLM
        default: Default value to return on error
    
    Returns:
        Parsed JSON or default value
    """
    try:
        cleaned = clean_json_string(raw_output)
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        logger.debug(f"Raw output: {raw_output[:500]}...")
        return default
    except Exception as e:
        logger.error(f"Unexpected error parsing JSON: {e}")
        return default


# ============================================
# File Utilities
# ============================================

def save_json(data: Any, filename: str, directory: Optional[Path] = None) -> Path:
    """
    Save data as JSON file
    
    Args:
        data: Data to save
        filename: Name of file (without extension)
        directory: Directory to save in (default: output_dir)
    
    Returns:
        Path to saved file
    """
    directory = directory or config.output_dir
    
    # Sanitize filename
    safe_filename = "".join(c for c in filename if c.isalnum() or c in ("-", "_")).strip()
    if not safe_filename:
        safe_filename = "output"
    
    filepath = directory / f"{safe_filename}.json"
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    logger.info(f"Saved JSON to {filepath}")
    return filepath


def load_json(filepath: Path) -> Any:
    """Load JSON from file"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================
# Data Deduplication
# ============================================

def deduplicate_companies(companies: list) -> list:
    """
    Deduplicate companies by name (case-insensitive)
    
    Args:
        companies: List of company dicts
    
    Returns:
        Deduplicated list
    """
    seen = set()
    deduped = []
    
    for company in companies:
        name = (company.get("company_name") or "").strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        deduped.append(company)
    
    logger.info(f"Deduplicated {len(companies)} -> {len(deduped)} companies")
    return deduped


# ============================================
# Timestamp Utilities
# ============================================

def timestamp_now() -> str:
    """Get current UTC timestamp as ISO8601 string"""
    return datetime.utcnow().isoformat()


def timestamp_to_datetime(ts: str) -> datetime:
    """Parse ISO8601 timestamp to datetime"""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


# ============================================
# Validation Utilities
# ============================================

def is_valid_nct_id(nct_id: str) -> bool:
    """Check if string is a valid NCT ID"""
    return bool(nct_id and nct_id.startswith("NCT") and len(nct_id) >= 11)


def normalize_phase(phase: str) -> str:
    """Normalize clinical trial phase string"""
    if not phase:
        return "unknown"
    
    phase = phase.lower().strip()
    
    # Map variations to standard format
    phase_map = {
        "phase1": "phase 1",
        "phase 1": "phase 1",
        "phase i": "phase 1",
        "phase2": "phase 2",
        "phase 2": "phase 2",
        "phase ii": "phase 2",
        "phase3": "phase 3",
        "phase 3": "phase 3",
        "phase iii": "phase 3",
        "phase4": "phase 4",
        "phase 4": "phase 4",
        "phase iv": "phase 4",
    }
    
    for key, value in phase_map.items():
        if key in phase:
            return value
    
    return phase
