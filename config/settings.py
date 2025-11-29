"""
Configuration for Convexia CRM v2
Uses Anthropic Claude for better, more human-like outputs
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Keys
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    SERPAPI_KEY = os.getenv("SERPAPI_KEY")
    
    # Model settings
    CLAUDE_MODEL = "claude-sonnet-4-20250514"  # Latest Sonnet
    MAX_TOKENS = 4000
    TEMPERATURE = 0.7
    
    # Pipeline settings
    MAX_COMPANIES = 10
    MAX_SEARCHES_PER_QUERY = 5
    MAX_DECISION_MAKERS_PER_COMPANY = 5
    
    # Directories
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    OUTPUT_DIR = DATA_DIR / "output"
    CACHE_DIR = DATA_DIR / "cache"
    
    # Create directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Sender info (UPDATE THIS WITH YOUR INFO)
    FROM_NAME = "Sanjana"
    FROM_TITLE = "Business Development"
    FROM_COMPANY = "Convexia Bio"
    FROM_EMAIL = "sanjana@convexia.bio"
    
    # Features
    ENABLE_CACHE = True
    ENABLE_HUMAN_REVIEW = True  # NEW: Require human review
    ENABLE_RESEARCH_LAYER = True  # NEW: Add manual research step
    
    # Rate limits
    RATE_LIMIT_CALLS = 10
    RATE_LIMIT_PERIOD = 60  # seconds

config = Config()

# Validate required keys
if not config.ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY not found in environment")
if not config.SERPAPI_KEY:
    raise ValueError("SERPAPI_KEY not found in environment")
