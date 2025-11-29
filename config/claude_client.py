"""
Claude API client for Convexia CRM
Handles all LLM interactions with proper error handling and caching
"""

import json
import hashlib
from typing import Dict, Any, Optional, List
import anthropic
from diskcache import Cache

from config.settings import config

# Initialize cache
cache = Cache(str(config.CACHE_DIR)) if config.ENABLE_CACHE else None


class ClaudeClient:
    """
    Wrapper for Anthropic's Claude API
    Handles JSON responses, caching, and error handling
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(
            api_key=api_key or config.ANTHROPIC_API_KEY
        )
        self.model = config.CLAUDE_MODEL
    
    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = None,
        max_tokens: int = None
    ) -> str:
        """
        Send a chat request to Claude
        
        Args:
            system_prompt: System instructions
            user_prompt: User message
            temperature: Sampling temperature (0-1)
            max_tokens: Max tokens to generate
            
        Returns:
            Claude's text response
        """
        # Check cache
        if cache:
            cache_key = self._make_cache_key(system_prompt, user_prompt)
            cached = cache.get(cache_key)
            if cached:
                return cached
        
        # Make API call
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens or config.MAX_TOKENS,
            temperature=temperature or config.TEMPERATURE,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        result = response.content[0].text
        
        # Cache result
        if cache:
            cache.set(cache_key, result, expire=86400)  # 24 hours
        
        return result
    
    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = None,
        max_tokens: int = None
    ) -> Dict[str, Any]:
        """
        Send a chat request expecting JSON response
        
        Returns:
            Parsed JSON dict
        """
        # Add JSON instruction to prompts
        system_with_json = f"{system_prompt}\n\nYou MUST return valid JSON only. No markdown, no explanations."
        user_with_json = f"{user_prompt}\n\nReturn ONLY valid JSON."
        
        response_text = self.chat(
            system_prompt=system_with_json,
            user_prompt=user_with_json,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Parse JSON (handle markdown code blocks)
        response_text = response_text.strip()
        if response_text.startswith("```"):
            # Remove markdown code blocks
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Claude returned invalid JSON: {e}\n\nResponse:\n{response_text}")
    
    def _make_cache_key(self, system_prompt: str, user_prompt: str) -> str:
        """Generate cache key from prompts"""
        combined = f"{system_prompt}|{user_prompt}|{self.model}"
        return hashlib.md5(combined.encode()).hexdigest()


# Singleton instance
claude = ClaudeClient()
