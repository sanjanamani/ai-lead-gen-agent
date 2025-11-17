"""
Web search tools with multiple provider support
Supports: SerpAPI (FREE tier: 100/month), Serper (Paid)
"""

import requests
from typing import List, Dict, Any, Optional, Literal
from abc import ABC, abstractmethod

from config.settings import config
from config.models import SearchResult
from config.utils import logger, retry_with_backoff, cached, rate_limiter


class BaseSearchClient(ABC):
    """Base class for search clients"""
    
    @abstractmethod
    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Perform web search and return results"""
        pass


class SerpAPIClient(BaseSearchClient):
    """
    SerpAPI client (FREE tier: 100 searches/month)
    Get key: https://serpapi.com/manage-api-key
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.serpapi_key
        if not self.api_key:
            raise ValueError("SERPAPI_KEY not set")
        
        self.base_url = "https://serpapi.com/search"
        logger.info("Initialized SerpAPI client")
    
    @retry_with_backoff(exceptions=(requests.RequestException,))
    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Search using SerpAPI"""
        rate_limiter.wait()
        
        params = {
            "q": query,
            "api_key": self.api_key,
            "num": num_results,
            "engine": "google"
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            results = []
            
            # Parse organic results
            for item in data.get("organic_results", [])[:num_results]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source="serpapi"
                ))
            
            # Parse news results if available
            for item in data.get("news_results", [])[:max(0, num_results - len(results))]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source="serpapi_news"
                ))
            
            logger.info(f"SerpAPI returned {len(results)} results for query: {query[:50]}...")
            return results[:num_results]
            
        except requests.RequestException as e:
            logger.error(f"SerpAPI request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"SerpAPI unexpected error: {e}")
            return []


class SerperClient(BaseSearchClient):
    """
    Serper client (Paid: $50/month for 5000 searches)
    Get key: https://serper.dev
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.serper_api_key
        if not self.api_key:
            raise ValueError("SERPER_API_KEY not set")
        
        self.base_url = "https://google.serper.dev/search"
        logger.info("Initialized Serper client")
    
    @retry_with_backoff(exceptions=(requests.RequestException,))
    @cached(expire=86400)  # Cache for 24 hours
    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Search using Serper"""
        rate_limiter.wait()
        
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "q": query,
            "num": num_results
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            
            # Parse organic results
            for item in data.get("organic", [])[:num_results]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source="serper"
                ))
            
            # Parse news results
            for item in data.get("news", [])[:max(0, num_results - len(results))]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source="serper_news"
                ))
            
            logger.info(f"Serper returned {len(results)} results for query: {query[:50]}...")
            return results[:num_results]
            
        except requests.RequestException as e:
            logger.error(f"Serper request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Serper unexpected error: {e}")
            return []


class SearchClient:
    """
    Unified search client that routes to the appropriate provider
    """
    
    def __init__(
        self,
        provider: Optional[Literal["serpapi", "serper"]] = None
    ):
        provider = provider or config.search_provider
        
        if provider == "serpapi":
            self.client = SerpAPIClient()
        elif provider == "serper":
            self.client = SerperClient()
        else:
            raise ValueError(f"Unknown search provider: {provider}")
        
        self.provider = provider
        logger.info(f"Search client initialized with provider: {provider}")
    
    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Perform web search"""
        return self.client.search(query, num_results)
    
    def search_companies(
        self,
        query: str,
        num_results: int = 10,
        biotech_focus: bool = True
    ) -> List[SearchResult]:
        """
        Search specifically for biotech companies
        Automatically enhances query for better results
        """
        # Enhance query for biotech company discovery
        if biotech_focus and "biotech" not in query.lower():
            query = f"{query} biotech company"
        
        return self.search(query, num_results)
    
    def search_decision_makers(
        self,
        company_name: str,
        roles: Optional[List[str]] = None,
        max_results: int = 5
    ) -> List[SearchResult]:
        """
        Search for decision makers at a company via LinkedIn
        
        Args:
            company_name: Name of the company
            roles: List of roles to search for (CEO, CFO, etc.)
            max_results: Maximum number of results
        """
        if roles is None:
            roles = [
                "CEO", "Chief Executive Officer",
                "Founder", "Co-founder",
                "CMO", "Chief Medical Officer",
                "CSO", "Chief Scientific Officer",
                "VP Clinical Development",
                "Head of R&D"
            ]
        
        # Build search query
        role_query = " OR ".join([f'"{role}"' for role in roles])
        query = f'site:linkedin.com/in "{company_name}" ({role_query}) biotech'
        
        return self.search(query, max_results)


# Convenience functions for direct use
def web_search_companies(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Search for biotech companies (backwards compatible with original code)
    
    Returns:
        List of dicts with title, url, snippet, source
    """
    client = SearchClient()
    results = client.search_companies(query, max_results)
    
    # Convert to dict format for backwards compatibility
    return [
        {
            "title": r.title,
            "url": r.url,
            "snippet": r.snippet,
            "source": r.source
        }
        for r in results
    ]


def find_decision_makers_for_company(
    company_name: str,
    website: Optional[str] = None,
    max_people: int = 5
) -> List[Dict[str, Any]]:
    """
    Find decision makers via LinkedIn search (backwards compatible)
    
    Returns:
        List of dicts with name, role, linkedin_url, snippet, source
    """
    client = SearchClient()
    results = client.search_decision_makers(company_name, max_results=max_people)
    
    people = []
    for result in results:
        # Parse LinkedIn profile data from search result
        name = result.title
        role = None
        
        # Try to extract name and role from title
        # Format is usually: "Name - Role at Company | LinkedIn"
        if " - " in result.title:
            parts = result.title.split(" - ", 1)
            name = parts[0].strip()
            role = parts[1].replace(" | LinkedIn", "").strip()
        
        people.append({
            "name": name,
            "role": role,
            "linkedin_url": result.url,
            "snippet": result.snippet,
            "source": result.source
        })
    
    return people


# Testing
if __name__ == "__main__":
    # Test search
    client = SearchClient()
    
    results = client.search_companies(
        "small oncology biotech failed phase 2 trials",
        num_results=5
    )
    
    print(f"Found {len(results)} results")
    for r in results:
        print(f"- {r.title}")
        print(f"  {r.url}")
