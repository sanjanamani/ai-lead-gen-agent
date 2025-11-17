"""
Convexia CRM - Interactive Search
Enter any therapeutic area or niche to find biotech companies with failed trials
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from agent import ConvexiaCRMAgent
from config.utils import deduplicate_companies, logger
from config.settings import config
from config.llm_client import LLMClient
import pandas as pd
import json

def generate_search_queries(user_input: str, llm: LLMClient) -> list:
    """Use LLM to generate targeted search queries based on user input"""
    
    system_prompt = """You are a biotech deal sourcing expert. 
    Generate 5 specific web search queries to find small-to-mid-size biotech companies with failed, terminated, or suspended clinical trials.
    
    Return ONLY a JSON array of strings, no other text.
    Example: ["query 1", "query 2", "query 3", "query 4", "query 5"]
    """
    
    user_prompt = f"""Generate 5 search queries to find biotech companies matching this criteria:
    
    User's target: {user_input}
    
    Make queries specific and varied to maximize coverage:
    - Include different phases (phase 2, phase 3)
    - Include different failure types (terminated, suspended, discontinued)
    - Include geographic focus (US, specific regions)
    - Include time ranges (2020-2024, recent)
    
    Return ONLY a JSON array of 5 search query strings."""
    
    try:
        response = llm.chat(system_prompt, user_prompt, json_mode=True)
        queries = json.loads(response.strip())
        if isinstance(queries, list):
            return queries[:5]
    except Exception as e:
        logger.warning(f"Could not generate queries with LLM: {e}")
    
    # Fallback: generate basic queries from user input
    base = user_input.lower()
    return [
        f"small to mid-size US {base} biotech companies with failed phase 2 trials",
        f"US {base} biotechs with terminated clinical trials 2020-2024",
        f"{base} biotech companies with suspended phase 3 trials",
        f"small biotech companies discontinued {base} programs",
        f"{base} drug development companies failed trials",
    ]

def run_interactive_search():
    print("\n" + "="*80)
    print("🔍 CONVEXIA CRM - INTERACTIVE SEARCH")
    print("="*80)
    print("\nFind biotech companies with failed trials in ANY therapeutic area.")
    print("Examples: 'diabetes', 'neurology', 'rare diseases', 'gene therapy',")
    print("          'cardiovascular', 'autoimmune', 'CNS disorders'\n")
    
    # Get user input
    print("="*80)
    user_input = input("🎯 Enter your target therapeutic area or niche:\n> ").strip()
    
    if not user_input:
        print("❌ No input provided. Exiting.")
        return
    
    # Get number of companies
    try:
        max_companies = input("\n📊 Max companies per query (default 10): ").strip()
        max_companies = int(max_companies) if max_companies else 10
    except:
        max_companies = 10
    
    # Ask about emails
    generate_emails = input("\n✉️  Generate personalized emails? (y/n, default y): ").strip().lower()
    generate_emails = generate_emails != 'n'
    
    print("\n" + "="*80)
    print(f"🚀 STARTING SEARCH: {user_input}")
    print("="*80)
    
    # Initialize
    agent = ConvexiaCRMAgent(max_companies=max_companies)
    llm = LLMClient()
    
    # Generate queries
    print("\n📝 Generating targeted search queries...")
    queries = generate_search_queries(user_input, llm)
    
    print("\nQueries to run:")
    for i, q in enumerate(queries, 1):
        print(f"  {i}. {q[:70]}{'...' if len(q) > 70 else ''}")
    
    # Run searches
    all_companies = []
    
    for i, query in enumerate(queries, 1):
        print(f"\n🔍 Running query {i}/{len(queries)}...")
        try:
            companies = agent.run_query(query)
            print(f"   ✅ Found {len(companies)} companies")
            all_companies.extend([c.dict() for c in companies])
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue
    
    # Deduplicate
    print(f"\n🔄 Deduplicating results...")
    unique_companies = deduplicate_companies(all_companies)
    print(f"   {len(all_companies)} → {len(unique_companies)} unique companies")
    
    if not unique_companies:
        print("\n❌ No companies found. Try different search terms.")
        return
    
    # Convert to Company objects
    from config.models import Company
    company_objects = []
    for c in unique_companies:
        try:
            company_objects.append(Company(**c))
        except Exception as e:
            continue
    
    # Sort by fit score
    company_objects.sort(key=lambda x: x.fit_score_for_convexia, reverse=True)
    
    # Generate emails if requested
    emails = []
    if generate_emails:
        print(f"\n✉️  Generating personalized emails...")
        
        # Get sender info
        from_name = input("   Your name (default: Ayaan): ").strip() or "Ayaan"
        from_title = input("   Your title (default: Co-founder): ").strip() or "Co-founder"
        
        emails = agent.generate_emails(
            company_objects,
            from_name=from_name,
            from_title=from_title,
            from_company="Convexia Bio"
        )
        print(f"   ✅ Generated {len(emails)} emails")
    
    # Create DataFrames
    companies_df, dms_df, emails_df = agent._to_dataframes(company_objects, emails if emails else None)
    
    # Sort by fit score
    if not companies_df.empty:
        companies_df = companies_df.sort_values('fit_score', ascending=False)
    
    # Display results
    print("\n" + "="*80)
    print("📊 RESULTS")
    print("="*80)
    
    print(f"\n🏢 Companies Found: {len(companies_df)}")
    if not companies_df.empty:
        print("\nCompanies (sorted by fit score):")
        display_cols = ['company_name', 'fit_score', 'therapeutic_areas', 'num_decision_makers']
        available_cols = [c for c in display_cols if c in companies_df.columns]
        print(companies_df[available_cols].to_string())
    
    print(f"\n👥 Decision Makers: {len(dms_df)}")
    
    # Show emails
    if emails_df is not None and not emails_df.empty:
        print(f"\n✉️  Emails Generated: {len(emails_df)}")
        
        show_emails = input("\n📧 Show sample emails? (y/n, default y): ").strip().lower()
        if show_emails != 'n':
            num_to_show = min(3, len(emails_df))
            print(f"\n{'─'*80}")
            print(f"TOP {num_to_show} PERSONALIZED EMAILS")
            print(f"{'─'*80}")
            
            for idx, row in emails_df.head(num_to_show).iterrows():
                print(f"\n{'─'*80}")
                print(f"To: {row['contact_name']}")
                if row.get('contact_role'):
                    print(f"Role: {row['contact_role']}")
                print(f"Company: {row['company_name']}")
                print(f"Subject: {row['subject']}")
                print(f"{'─'*80}")
                print(row['body'])
    
    # Export
    print("\n" + "="*80)
    print("💾 EXPORTING FILES")
    print("="*80)
    
    # Create safe filename from user input
    safe_name = "".join(c for c in user_input if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_name = safe_name.replace(' ', '_')[:30]
    
    output_dir = config.output_dir
    
    companies_csv = output_dir / f"{safe_name}_companies.csv"
    dms_csv = output_dir / f"{safe_name}_decision_makers.csv"
    emails_csv = output_dir / f"{safe_name}_emails.csv"
    
    companies_df.to_csv(companies_csv, index=False)
    print(f"✅ Companies: {companies_csv}")
    
    dms_df.to_csv(dms_csv, index=False)
    print(f"✅ Decision Makers: {dms_csv}")
    
    if emails_df is not None and not emails_df.empty:
        emails_df.to_csv(emails_csv, index=False)
        print(f"✅ Emails: {emails_csv}")
    
    # Full JSON export
    full_data = {
        "search_input": user_input,
        "queries_used": queries,
        "companies": [c.dict() for c in company_objects],
        "summary": {
            "total_companies": len(company_objects),
            "total_decision_makers": len(dms_df),
            "total_emails": len(emails_df) if emails_df is not None else 0,
            "avg_fit_score": companies_df['fit_score'].mean() if not companies_df.empty else 0
        }
    }
    
    full_json = output_dir / f"{safe_name}_full_results.json"
    with open(full_json, 'w') as f:
        json.dump(full_data, f, indent=2, default=str)
    print(f"✅ Full JSON: {full_json}")
    
    print("\n" + "="*80)
    print("🎉 SEARCH COMPLETE!")
    print("="*80)
    print(f"\nFound {len(company_objects)} companies in '{user_input}'")
    print(f"Check your files in: {output_dir}\n")
    
    # Ask if they want to search again
    again = input("🔄 Search another therapeutic area? (y/n): ").strip().lower()
    if again == 'y':
        run_interactive_search()

if __name__ == "__main__":
    run_interactive_search()