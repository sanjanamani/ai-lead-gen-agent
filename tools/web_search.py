"""
Web search tools using SerpAPI
"""

import os
from typing import List, Dict, Optional
import requests
from ratelimit import limits, sleep_and_retry

from config.settings import config


@sleep_and_retry
@limits(calls=config.RATE_LIMIT_CALLS, period=config.RATE_LIMIT_PERIOD)
def search_companies(query: str, num_results: int = 10) -> List[Dict]:
    """
    Search for biotech companies using SerpAPI
    
    Args:
        query: Search query
        num_results: Number of results to return
        
    Returns:
        List of search results
    """
    params = {
        "engine": "google",
        "q": query,
        "api_key": config.SERPAPI_KEY,
        "num": num_results
    }
    
    try:
        response = requests.get(
            "https://serpapi.com/search",
            params=params,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("organic_results", []):
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": item.get("source", "")
            })
        
        return results
    
    except Exception as e:
        print(f"Search error: {e}")
        return []


def find_decision_makers(company_name: str, max_results: int = 5, title_filter: str = None) -> List[Dict]:
    """
    Find decision makers for a company using LinkedIn-focused search
    
    Args:
        company_name: Company to search for
        max_results: Max number of results
        title_filter: Optional title keywords (e.g., "partner OR principal")
        
    Returns:
        List of decision maker profiles
    """
    # Build search query based on type
    if title_filter:
        query = f'"{company_name}" {title_filter} site:linkedin.com/in'
    else:
        query = f'"{company_name}" CEO OR founder OR "chief executive" OR "business development" site:linkedin.com/in'
    
    results = search_companies(query, num_results=max_results)
    
    decision_makers = []
    for result in results:
        # Extract info from LinkedIn URLs
        link = result.get("link", "")
        if "linkedin.com/in/" in link:
            # Parse name and title from snippet
            snippet = result.get("snippet", "")
            title_parts = result.get("title", "").split("-")
            
            name = title_parts[0].strip() if title_parts else ""
            role = title_parts[1].strip() if len(title_parts) > 1 else ""
            
            decision_makers.append({
                "name": name,
                "role": role,
                "linkedin": link,
                "email": "",  # Would need separate enrichment
                "snippet": snippet
            })
    
    return decision_makers


def enrich_with_news(company_name: str) -> List[Dict]:
    """
    Find recent news about a company
    
    Args:
        company_name: Company name
        
    Returns:
        List of news articles
    """
    query = f'"{company_name}" (drug OR trial OR FDA OR clinical) after:2024-01-01'
    
    params = {
        "engine": "google",
        "q": query,
        "api_key": config.SERPAPI_KEY,
        "num": 5,
        "tbm": "nws"  # News search
    }
    
    try:
        response = requests.get(
            "https://serpapi.com/search",
            params=params,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        articles = []
        for item in data.get("news_results", []):
            # Handle source being either a dict or a string
            source = item.get("source", "")
            if isinstance(source, dict):
                source_name = source.get("name", "")
            else:
                source_name = str(source) if source else ""
            
            articles.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "date": item.get("date", ""),
                "source": source_name
            })
        
        return articles
    
    except Exception as e:
        # Return empty list on error
        return []
