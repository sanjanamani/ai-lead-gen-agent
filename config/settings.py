"""
Configuration management for Convexia CRM Agent
Handles environment variables, validation, and defaults
"""

import os
from pathlib import Path
from typing import Literal, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator

# Load environment variables from .env file
load_dotenv()

class Config(BaseModel):
    """Main configuration for the CRM agent"""
    
    # Project paths
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    cache_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "data" / "cache")
    output_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "data" / "output")
    log_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "data" / "logs")
    
    # LLM Configuration
    llm_provider: Literal["gemini", "anthropic", "openai"] = Field(
        default="gemini",
        description="Which LLM provider to use"
    )
    google_api_key: Optional[str] = Field(default=None)
    anthropic_api_key: Optional[str] = Field(default=None)
    openai_api_key: Optional[str] = Field(default=None)
    
    # Search Configuration
    search_provider: Literal["serpapi", "serper"] = Field(
        default="serpapi",
        description="Which search API to use"
    )
    serpapi_key: Optional[str] = Field(default=None)
    serper_api_key: Optional[str] = Field(default=None)
    
    # Optional services
    hunter_api_key: Optional[str] = Field(default=None)
    
    # Agent settings
    max_companies: int = Field(default=10, ge=1, le=50)
    max_decision_makers_per_company: int = Field(default=5, ge=1, le=20)
    max_retries: int = Field(default=3, ge=0, le=10)
    rate_limit_rpm: int = Field(default=10, ge=1, le=60)
    
    # Caching
    enable_cache: bool = Field(default=True)
    cache_expiry_hours: int = Field(default=24, ge=1, le=168)
    
    # LLM settings
    llm_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=4000, ge=100, le=8000)
    
    # Clinical trials API
    ctgov_base_url: str = "https://clinicaltrials.gov/api/v2/studies"
    
    class Config:
        env_prefix = ""
        case_sensitive = False
        
    @validator("llm_provider")
    def validate_llm_provider(cls, v, values):
        """Ensure required API key is present for selected provider"""
        if v == "gemini" and not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("GOOGLE_API_KEY required for Gemini provider")
        elif v == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY required for Anthropic provider")
        elif v == "openai" and not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY required for OpenAI provider")
        return v
    
    @validator("search_provider")
    def validate_search_provider(cls, v, values):
        """Ensure required API key is present for selected search provider"""
        if v == "serpapi" and not os.getenv("SERPAPI_KEY"):
            raise ValueError("SERPAPI_KEY required for SerpAPI provider")
        elif v == "serper" and not os.getenv("SERPER_API_KEY"):
            raise ValueError("SERPER_API_KEY required for Serper provider")
        return v
    
    def __init__(self, **data):
        # Load from environment variables
        if "google_api_key" not in data:
            data["google_api_key"] = os.getenv("GOOGLE_API_KEY")
        if "anthropic_api_key" not in data:
            data["anthropic_api_key"] = os.getenv("ANTHROPIC_API_KEY")
        if "openai_api_key" not in data:
            data["openai_api_key"] = os.getenv("OPENAI_API_KEY")
        if "serpapi_key" not in data:
            data["serpapi_key"] = os.getenv("SERPAPI_KEY")
        if "serper_api_key" not in data:
            data["serper_api_key"] = os.getenv("SERPER_API_KEY")
        if "hunter_api_key" not in data:
            data["hunter_api_key"] = os.getenv("HUNTER_API_KEY")
        if "llm_provider" not in data:
            data["llm_provider"] = os.getenv("LLM_PROVIDER", "gemini")
        if "search_provider" not in data:
            data["search_provider"] = os.getenv("SEARCH_PROVIDER", "serpapi")
        if "enable_cache" not in data:
            cache_env = os.getenv("ENABLE_CACHE", "true")
            data["enable_cache"] = cache_env.lower() in ("true", "1", "yes")
        if "cache_expiry_hours" not in data:
            data["cache_expiry_hours"] = int(os.getenv("CACHE_EXPIRY_HOURS", "24"))
        if "max_retries" not in data:
            data["max_retries"] = int(os.getenv("MAX_RETRIES", "3"))
        if "rate_limit_rpm" not in data:
            data["rate_limit_rpm"] = int(os.getenv("RATE_LIMIT_RPM", "10"))
            
        super().__init__(**data)
        
        # Create directories if they don't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

# Global config instance
config = Config()
