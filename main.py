"""
Example usage of the Convexia CRM Agent
Demonstrates the refactored, production-ready implementation
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agent import ConvexiaCRMAgent
from config.utils import logger, deduplicate_companies
from config.settings import config
import pandas as pd


def example_single_query():
    """Example: Run a single query"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Single Query")
    print("="*80 + "\n")
    
    agent = ConvexiaCRMAgent(max_companies=5)
    
    query = "small to mid-size US oncology biotech companies with failed phase 2 trials"
    
    print(f"Query: {query}\n")
    companies, companies_df, dms_df, _ = agent.run_query_with_outputs(query)
    
    print(f"\n✅ Found {len(companies)} companies:")
    print(companies_df[['company_name', 'fit_score', 'num_phase2_failed']].to_string())
    
    print(f"\n✅ Found {len(dms_df)} decision makers")
    
    return companies


def example_multiple_queries():
    """Example: Run multiple related queries and deduplicate"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Multiple Queries with Deduplication")
    print("="*80 + "\n")
    
    agent = ConvexiaCRMAgent(max_companies=5)
    
    queries = [
        "US oncology biotechs with failed phase 2 trials in solid tumors 2020-2024",
        "immuno-oncology companies with terminated checkpoint inhibitor trials",
        "small biotech companies with suspended phase 2 cancer trials"
    ]
    
    all_companies = []
    
    for query in queries:
        print(f"\n📋 Query: {query}")
        companies = agent.run_query(query)
        print(f"   → Found {len(companies)} companies")
        all_companies.extend([c.dict() for c in companies])
    
    # Deduplicate
    deduped = deduplicate_companies(all_companies)
    
    print(f"\n✅ Total: {len(all_companies)} → {len(deduped)} after deduplication")
    print("\nCompany Names:")
    for c in deduped:
        print(f"  - {c['company_name']}")
    
    return deduped


def example_with_emails():
    """Example: Generate personalized outreach emails"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Generate Personalized Emails")
    print("="*80 + "\n")
    
    agent = ConvexiaCRMAgent(max_companies=3)
    
    query = "oncology biotech with failed phase 2 trials"
    
    companies, companies_df, dms_df, emails_df = agent.run_query_with_outputs(
        query,
        generate_emails=True
    )
    
    if emails_df is not None and not emails_df.empty:
        print(f"\n✅ Generated {len(emails_df)} personalized emails")
        print("\nExample email:")
        print("-" * 80)
        first_email = emails_df.iloc[0]
        print(f"To: {first_email['contact_name']} ({first_email['contact_role']})")
        print(f"Company: {first_email['company_name']}")
        print(f"Subject: {first_email['subject']}")
        print(f"\n{first_email['body']}")
        print("-" * 80)
    else:
        print("⚠️  No emails generated")
    
    return companies, emails_df


def example_export_to_csv():
    """Example: Export results to CSV for further analysis"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Export to CSV")
    print("="*80 + "\n")
    
    agent = ConvexiaCRMAgent(max_companies=5)
    
    query = "biotech with failed trials"
    
    companies, companies_df, dms_df, emails_df = agent.run_query_with_outputs(query)
    
    # Export to CSV
    output_dir = config.output_dir
    
    companies_csv = output_dir / "companies.csv"
    dms_csv = output_dir / "decision_makers.csv"
    
    companies_df.to_csv(companies_csv, index=False)
    dms_df.to_csv(dms_csv, index=False)
    
    print(f"✅ Exported to:")
    print(f"   - {companies_csv}")
    print(f"   - {dms_csv}")
    
    if emails_df is not None:
        emails_csv = output_dir / "emails.csv"
        emails_df.to_csv(emails_csv, index=False)
        print(f"   - {emails_csv}")


def example_custom_config():
    """Example: Use custom configuration"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Custom Configuration")
    print("="*80 + "\n")
    
    # You can override config settings
    from config.settings import Config
    from config.llm_client import LLMClient
    from tools.web_search import SearchClient
    
    # Custom config
    custom_config = Config(
        max_companies=3,
        max_decision_makers_per_company=3,
        llm_temperature=0.2,
    )
    
    # Custom clients
    llm = LLMClient(provider="gemini")  # Force specific provider
    search = SearchClient(provider="serpapi")  # Force specific provider
    
    agent = ConvexiaCRMAgent(
        llm_client=llm,
        search_client=search,
        max_companies=custom_config.max_companies
    )
    
    query = "neurology biotech with failed trials"
    companies = agent.run_query(query)
    
    print(f"✅ Found {len(companies)} companies with custom config")


def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("CONVEXIA CRM AGENT - PRODUCTION-READY VERSION")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"  LLM Provider: {config.llm_provider}")
    print(f"  Search Provider: {config.search_provider}")
    print(f"  Max Companies: {config.max_companies}")
    print(f"  Cache Enabled: {config.enable_cache}")
    print(f"  Output Dir: {config.output_dir}")
    
    try:
        # Run examples
        # Uncomment the examples you want to run:
        
        companies = example_single_query()
        
        # deduped = example_multiple_queries()
        
        # companies, emails = example_with_emails()
        
        # example_export_to_csv()
        
        # example_custom_config()
        
        print("\n" + "="*80)
        print("✅ ALL EXAMPLES COMPLETED")
        print("="*80 + "\n")
        
    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        print("\nPlease ensure you have:")
        print("  1. Created .env file from .env.example")
        print("  2. Added your API keys")
        print("  3. Installed dependencies: pip install -r requirements.txt")


if __name__ == "__main__":
    main()
