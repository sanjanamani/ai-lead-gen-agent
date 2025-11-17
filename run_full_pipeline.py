"""
Full Convexia CRM Pipeline - Maximum Companies + Emails
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from agent import ConvexiaCRMAgent
from config.utils import deduplicate_companies, logger
from config.settings import config
import pandas as pd

def run_full_pipeline():
    print("\n" + "="*80)
    print("🚀 CONVEXIA CRM - FULL PIPELINE")
    print("="*80 + "\n")
    
    # Initialize agent with higher max_companies
    agent = ConvexiaCRMAgent(max_companies=10)
    
    # Multiple targeted queries for better coverage
    queries = [
        "small to mid-size US oncology biotech companies with failed phase 2 trials",
        "US oncology biotechs with terminated phase 2 trials 2020-2024",
        "immuno-oncology biotech companies with suspended clinical trials",
        "small biotech companies failed phase 3 cancer trials",
        "oncology biotech terminated checkpoint inhibitor trials",
        "US biotech companies discontinued oncology programs",
    ]
    
    all_companies = []
    
    for i, query in enumerate(queries, 1):
        print(f"\n📋 Query {i}/{len(queries)}: {query[:60]}...")
        try:
            companies = agent.run_query(query)
            print(f"   ✅ Found {len(companies)} companies")
            all_companies.extend([c.dict() for c in companies])
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue
    
    # Deduplicate
    print(f"\n🔄 Deduplicating...")
    unique_companies = deduplicate_companies(all_companies)
    print(f"   Total: {len(all_companies)} → {len(unique_companies)} unique companies")
    
    if not unique_companies:
        print("\n❌ No companies found. Check your API keys and queries.")
        return
    
    # Convert back to Company objects for email generation
    from config.models import Company
    company_objects = []
    for c in unique_companies:
        try:
            company_objects.append(Company(**c))
        except Exception as e:
            logger.warning(f"Could not create Company object: {e}")
    
    # Sort by fit score (highest first)
    company_objects.sort(key=lambda x: x.fit_score_for_convexia, reverse=True)
    
    # Generate emails
    print(f"\n✉️  Generating personalized emails...")
    emails = agent.generate_emails(
        company_objects,
        from_name="Ayaan",
        from_title="Co-founder",
        from_company="Convexia Bio"
    )
    print(f"   ✅ Generated {len(emails)} emails")
    
    # Create DataFrames
    companies_df, dms_df, emails_df = agent._to_dataframes(company_objects, emails)
    
    # Sort companies by fit score
    if not companies_df.empty:
        companies_df = companies_df.sort_values('fit_score', ascending=False)
    
    # Display results
    print("\n" + "="*80)
    print("📊 RESULTS SUMMARY")
    print("="*80)
    
    print(f"\n🏢 Companies Found: {len(companies_df)}")
    if not companies_df.empty:
        print("\nTop Companies by Fit Score:")
        print(companies_df[['company_name', 'fit_score', 'therapeutic_areas', 'num_decision_makers']].to_string())
    
    print(f"\n👥 Decision Makers Found: {len(dms_df)}")
    if not dms_df.empty and len(dms_df) > 0:
        print("\nSample Decision Makers:")
        print(dms_df[['company_name', 'name', 'role']].head(10).to_string())
    
    print(f"\n✉️  Emails Generated: {len(emails_df) if emails_df is not None else 0}")
    
    # Show sample emails
    if emails_df is not None and not emails_df.empty:
        print("\n" + "="*80)
        print("📧 SAMPLE PERSONALIZED EMAILS")
        print("="*80)
        
        for idx, row in emails_df.head(3).iterrows():
            print(f"\n{'─'*80}")
            print(f"To: {row['contact_name']} ({row['contact_role']})")
            print(f"Company: {row['company_name']}")
            print(f"Subject: {row['subject']}")
            print(f"{'─'*80}")
            print(row['body'])
            print()
    
    # Export to CSV
    output_dir = config.output_dir
    
    companies_csv = output_dir / "all_companies.csv"
    dms_csv = output_dir / "all_decision_makers.csv"
    emails_csv = output_dir / "all_emails.csv"
    
    companies_df.to_csv(companies_csv, index=False)
    dms_df.to_csv(dms_csv, index=False)
    if emails_df is not None:
        emails_df.to_csv(emails_csv, index=False)
    
    print("\n" + "="*80)
    print("💾 EXPORTED FILES")
    print("="*80)
    print(f"\n✅ Companies: {companies_csv}")
    print(f"✅ Decision Makers: {dms_csv}")
    print(f"✅ Emails: {emails_csv}")
    
    # Also save full JSON
    import json
    full_data = {
        "companies": [c.dict() for c in company_objects],
        "total_companies": len(company_objects),
        "total_decision_makers": len(dms_df),
        "total_emails": len(emails_df) if emails_df is not None else 0
    }
    
    full_json = output_dir / "full_pipeline_results.json"
    with open(full_json, 'w') as f:
        json.dump(full_data, f, indent=2, default=str)
    print(f"✅ Full JSON: {full_json}")
    
    print("\n" + "="*80)
    print("🎉 PIPELINE COMPLETE!")
    print("="*80 + "\n")
    
    return company_objects, emails

if __name__ == "__main__":
    run_full_pipeline()