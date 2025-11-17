"""
Unified LLM client supporting multiple providers
Supports: Google Gemini (FREE), Anthropic Claude (FREE tier), OpenAI (Paid)
"""

import json
from typing import Optional, Literal
from abc import ABC, abstractmethod

from config.settings import config
from config.utils import logger, retry_with_backoff, rate_limiter, parse_llm_json


class BaseLLMClient(ABC):
    """Base class for LLM clients"""
    
    @abstractmethod
    def chat(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        """Send a chat request and return response"""
        pass
    
    def chat_json(self, system_prompt: str, user_prompt: str) -> dict:
        """
        Send chat request and parse JSON response
        Automatically handles JSON extraction from LLM output
        """
        response = self.chat(system_prompt, user_prompt, json_mode=True)
        return parse_llm_json(response, default={})


class GeminiClient(BaseLLMClient):
    """Google Gemini client (FREE tier: 15 RPM, 1M requests/day)"""
    
    def __init__(self, api_key: Optional[str] = None):
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError(
                "google-generativeai not installed. "
                "Run: pip install google-generativeai"
            )
        
        self.api_key = api_key or config.google_api_key
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not set")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash-001')  # Free tier model
        logger.info("Initialized Gemini client (gemini-1.5-flash)")
    
    @retry_with_backoff(exceptions=(Exception,))
    def chat(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        """Send chat request to Gemini"""
        rate_limiter.wait()
        
        # Combine system and user prompts
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        if json_mode:
            combined_prompt += "\n\nYou MUST respond with ONLY valid JSON, no other text."
        
        try:
            response = self.model.generate_content(
                combined_prompt,
                generation_config={
                    "temperature": config.llm_temperature,
                    "max_output_tokens": config.llm_max_tokens,
                }
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude client (FREE tier available)"""
    
    def __init__(self, api_key: Optional[str] = None):
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "anthropic not installed. "
                "Run: pip install anthropic"
            )
        
        self.api_key = api_key or config.anthropic_api_key
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        
        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-3-haiku-20240307"  # Most cost-effective model
        logger.info(f"Initialized Anthropic client ({self.model})")
    
    @retry_with_backoff(exceptions=(Exception,))
    def chat(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        """Send chat request to Claude"""
        rate_limiter.wait()
        
        if json_mode:
            user_prompt += "\n\nYou MUST respond with ONLY valid JSON, no other text."
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=config.llm_max_tokens,
                temperature=config.llm_temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise


class OpenAIClient(BaseLLMClient):
    """OpenAI client (Paid, but reliable)"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4-turbo-preview"):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai not installed. "
                "Run: pip install openai"
            )
        
        self.api_key = api_key or config.openai_api_key
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        logger.info(f"Initialized OpenAI client ({self.model})")
    
    @retry_with_backoff(exceptions=(Exception,))
    def chat(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        """Send chat request to OpenAI"""
        rate_limiter.wait()
        
        kwargs = {
            "model": self.model,
            "temperature": config.llm_temperature,
            "max_tokens": config.llm_max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }
        
        # Use JSON mode if supported
        if json_mode and "gpt-4" in self.model:
            kwargs["response_format"] = {"type": "json_object"}
            user_prompt += "\n\nYou MUST respond with valid JSON."
            kwargs["messages"][-1]["content"] = user_prompt
        
        try:
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


class LLMClient:
    """
    Unified LLM client that routes to the appropriate provider
    Automatically selects provider based on config
    """
    
    def __init__(
        self,
        provider: Optional[Literal["gemini", "anthropic", "openai"]] = None
    ):
        provider = provider or config.llm_provider
        
        if provider == "gemini":
            self.client = GeminiClient()
        elif provider == "anthropic":
            self.client = AnthropicClient()
        elif provider == "openai":
            self.client = OpenAIClient()
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
        
        self.provider = provider
        logger.info(f"LLM client initialized with provider: {provider}")
    
    def chat(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        """Send chat request"""
        return self.client.chat(system_prompt, user_prompt, json_mode)
    
    def chat_json(self, system_prompt: str, user_prompt: str) -> dict:
        """Send chat request and parse JSON response"""
        return self.client.chat_json(system_prompt, user_prompt)


# Example usage and testing
if __name__ == "__main__":
    # Test the LLM client
    llm = LLMClient()
    
    response = llm.chat(
        system_prompt="You are a helpful assistant.",
        user_prompt="Say hello in a friendly way.",
    )
    print(f"Response: {response}")
    
    # Test JSON mode
    json_response = llm.chat_json(
        system_prompt="You return JSON only.",
        user_prompt='Return {"greeting": "hello", "language": "english"}',
    )
    print(f"JSON Response: {json_response}")
