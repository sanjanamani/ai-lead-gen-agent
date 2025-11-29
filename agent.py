"""
Convexia CRM Agent v2 - Human-in-the-Loop
Production-ready with manual research layer for non-LLM-ish emails
"""

import json
from typing import List, Dict, Optional
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import pandas as pd

from config.settings import config
from config.claude_client import claude
from config.prompts import (
    COMPANY_SYNTHESIS_SYSTEM,
    COMPANY_SYNTHESIS_USER_TEMPLATE,
    EMAIL_GENERATION_SYSTEM,
    EMAIL_GENERATION_USER_TEMPLATE,
    enhance_search_query
)
from tools.web_search import search_companies, find_decision_makers
from tools.clinical_trials import search_clinical_trials
from human_layer import ResearchLayer, EmailReviewLayer

console = Console()


class ConvexiaCRMAgent:
    """
    v2 Agent with human research layer
    
    Workflow:
    1. AI: Find companies with failed trials
    2. AI: Find decision makers
    3. HUMAN: Research each lead manually
    4. AI: Generate email using human research
    5. HUMAN: Review and edit email
    6. Export approved emails
    """
    
    def __init__(self, auto_research: bool = True, auto_approve: bool = False, batch_review: bool = True):
        self.research_layer = ResearchLayer(config.OUTPUT_DIR)
        self.review_layer = EmailReviewLayer()
        self.auto_research = auto_research
        self.auto_approve = auto_approve
        self.batch_review = batch_review
        
        # Big pharma exclusion list
        self.big_pharma = [
            'pfizer', 'novartis', 'roche', 'sanofi', 'gsk', 'glaxosmithkline',
            'astrazeneca', 'merck', 'lilly', 'eli lilly', 'bms', 'bristol myers',
            'johnson & johnson', 'j&j', 'bayer', 'boehringer', 'takeda', 'abbvie',
            'vertex', 'regeneron', 'biomarin', 'gilead', 'amgen', 'biogen',
            'moderna', 'incyte', 'alnylam', 'novo nordisk', 'alexion', 'seagen'
        ]
    
    def _is_big_pharma(self, company_name: str) -> bool:
        """Check if company is big pharma"""
        company_lower = company_name.lower()
        return any(bp in company_lower for bp in self.big_pharma)
    
    def run(self, query: str, max_leads: int = 5):
        """
        Run full pipeline with human checkpoints
        """
        console.print(f"\n[bold cyan]🚀 Starting Convexia CRM Pipeline[/bold cyan]")
        console.print(f"Query: {query}")
        console.print(f"Target: {max_leads} high-quality leads\n")
        
        # Phase 1: Discovery (AI)
        console.print("[bold]Phase 1: Discovery[/bold]")
        companies = self._discover_companies(query, max_leads)
        
        if not companies:
            console.print("[red]No companies found. Try a different query.[/red]")
            return
        
        console.print(f"[green]✓ Found {len(companies)} companies[/green]\n")
        
        # Phase 2: Enrichment (AI)
        console.print("[bold]Phase 2: Finding Decision Makers[/bold]")
        leads = self._enrich_with_contacts(companies)
        console.print(f"[green]✓ Found {len(leads)} contacts[/green]\n")
        
        # Phase 3: Research (HUMAN)
        console.print("[bold]Phase 3: Manual Research[/bold]")
        console.print("[yellow]This is where you add the human intelligence![/yellow]\n")
        researched_leads = self._conduct_research(leads)
        
        if not researched_leads:
            console.print("[yellow]No leads researched. Exiting.[/yellow]")
            return
        
        # Phase 4: Email Generation (AI + HUMAN)
        console.print(f"\n[bold]Phase 4: Email Generation & Review[/bold]")
        approved_emails = self._generate_and_review_emails(researched_leads)
        
        if not approved_emails:
            console.print("[yellow]No emails approved. Exiting.[/yellow]")
            return
        
        # Phase 5: Export
        self._export_results(approved_emails, query)
        
        console.print(f"\n[bold green]✅ Complete! Generated {len(approved_emails)} approved emails[/bold green]")
    
    def _discover_companies(self, query: str, max_companies: int) -> List[Dict]:
        """
        Use web search + clinical trials to find relevant companies
        """
        all_companies = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Search for biotech companies with failed trials
            for i in range(min(2, config.MAX_SEARCHES_PER_QUERY)):
                task = progress.add_task(f"Searching biotech companies (angle {i+1})...", total=None)
                
                search_query = enhance_search_query(query, i)
                
                # Web search
                search_results = search_companies(search_query)
                
                # Clinical trials
                trials_data = search_clinical_trials(query)
                
                # Synthesize with Claude
                companies = self._synthesize_companies(
                    query, search_results, trials_data, max_companies
                )
                
                all_companies.extend(companies)
                progress.remove_task(task)
            
            # Also search for biotech VC firms
            task = progress.add_task("Searching biotech VC firms...", total=None)
            vc_firms = self._discover_vc_firms()
            all_companies.extend(vc_firms)
            progress.remove_task(task)
        
        # Deduplicate and rank
        unique_companies = self._deduplicate_companies(all_companies)
        return sorted(unique_companies, key=lambda x: x.get('fit_score', 0), reverse=True)[:max_companies]
    
    def _discover_vc_firms(self) -> List[Dict]:
        """
        Search for biotech-focused VC firms
        """
        vc_query = "biotech venture capital firms portfolio companies"
        search_results = search_companies(vc_query)
        
        # Use Claude to extract VC firms
        user_prompt = f"""From these search results, extract biotech-focused VC firms.

SEARCH RESULTS:
{json.dumps(search_results, indent=2)}

Return a JSON array of VC firms with this structure:

[
  {{
    "company_name": "VC firm name",
    "company_type": "vc_firm",
    "company_size": "unknown",
    "overview": "Description of their biotech investment focus",
    "location": "City, State",
    "website": "https://...",
    "therapeutic_areas": [],
    "failed_trials": [],
    "portfolio_companies": ["Company A", "Company B", "Company C"],
    "why_relevant_to_convexia": "VC firm with biotech portfolio companies that may need drug rescue services",
    "fit_score": 80,
    "data_sources": ["web search"]
  }}
]

Include well-known biotech VCs like:
- Flagship Pioneering
- Atlas Venture
- Third Rock Ventures
- Polaris Partners
- Arch Venture Partners
- Versant Ventures
- OrbiMed
- RA Capital
- Foresite Capital
- Sofinnova Partners

Return ONLY the JSON array."""
        
        try:
            vc_firms = claude.chat_json(
                system_prompt=COMPANY_SYNTHESIS_SYSTEM,
                user_prompt=user_prompt
            )
            
            if isinstance(vc_firms, list):
                console.print(f"[dim]Found {len(vc_firms)} VC firms[/dim]")
                return vc_firms
            return []
        except Exception as e:
            console.print(f"[yellow]Warning: Error finding VC firms: {e}[/yellow]")
            return []
    
    def _synthesize_companies(
        self,
        query: str,
        search_results: List[Dict],
        trials_data: List[Dict],
        max_companies: int
    ) -> List[Dict]:
        """
        Use Claude to extract structured company data
        """
        user_prompt = COMPANY_SYNTHESIS_USER_TEMPLATE.format(
            search_results=json.dumps(search_results, indent=2),
            trials_data=json.dumps(trials_data, indent=2),
            max_companies=max_companies
        )
        
        try:
            companies = claude.chat_json(
                system_prompt=COMPANY_SYNTHESIS_SYSTEM,
                user_prompt=user_prompt
            )
            
            if isinstance(companies, list):
                result = companies
            elif isinstance(companies, dict) and 'companies' in companies:
                result = companies['companies']
            else:
                console.print("[yellow]Warning: Unexpected response format[/yellow]")
                return []
            
            # Filter out big pharma companies
            filtered = []
            for company in result:
                company_name = company.get('company_name', '')
                company_size = company.get('company_size', 'unknown')
                
                if self._is_big_pharma(company_name):
                    console.print(f"[dim]Filtered out big pharma: {company_name}[/dim]")
                    continue
                
                if company_size == 'large':
                    console.print(f"[dim]Filtered out large company: {company_name}[/dim]")
                    continue
                
                filtered.append(company)
            
            return filtered
            
        except Exception as e:
            console.print(f"[red]Error synthesizing companies: {e}[/red]")
            return []
    
    def _enrich_with_contacts(self, companies: List[Dict]) -> List[Dict]:
        """
        Find decision makers for each company
        """
        leads = []
        
        for company in companies:
            company_type = company.get('company_type', 'biotech')
            company_name = company['company_name']
            
            # For VC firms, search for partners/principals
            if company_type == 'vc_firm':
                decision_makers = find_decision_makers(
                    company_name,
                    title_filter="partner OR principal OR managing director",
                    max_results=3
                )
            else:
                # For biotech companies, search for C-suite/BD
                decision_makers = find_decision_makers(
                    company_name,
                    max_results=3
                )
            
            for dm in decision_makers:
                leads.append({
                    'company': company,
                    'contact': dm
                })
        
        return leads
    
    def _conduct_research(self, leads: List[Dict]) -> List[Dict]:
        """
        Research session for each lead (auto or manual based on settings)
        """
        researched = []
        
        for idx, lead in enumerate(leads):
            console.print(f"\n[cyan]Lead {idx+1}/{len(leads)}[/cyan]")
            
            company = lead['company']
            contact = lead['contact']
            
            # Check if already researched
            if self.research_layer.has_research(
                company['company_name'],
                contact['name']
            ):
                console.print("[dim]Already researched - loading notes...[/dim]")
                research = self.research_layer.get_research(
                    company['company_name'],
                    contact['name']
                )
            else:
                # Conduct research (auto or manual based on settings)
                research = self.research_layer.conduct_research(
                    company_name=company['company_name'],
                    contact_name=contact['name'],
                    contact_linkedin=contact.get('linkedin', ''),
                    company_data=company,
                    auto_research=self.auto_research  # Use the setting
                )
            
            if research:
                lead['research'] = research
                researched.append(lead)
        
        return researched
    
    def _generate_and_review_emails(self, leads: List[Dict]) -> List[Dict]:
        """
        Generate emails with Claude, then human review
        Supports both batch and sequential review modes
        """
        if self.batch_review:
            return self._generate_and_review_emails_batch(leads)
        else:
            return self._generate_and_review_emails_sequential(leads)
    
    def _generate_and_review_emails_batch(self, leads: List[Dict]) -> List[Dict]:
        """
        Batch mode: Generate all emails first, then review all at once
        """
        console.print("\n[cyan]Generating all emails first...[/cyan]")
        
        all_emails = []
        for idx, lead in enumerate(leads):
            console.print(f"[dim]Generating email {idx+1}/{len(leads)}...[/dim]")
            
            company = lead['company']
            contact = lead['contact']
            research = lead.get('research', {})
            
            # Generate email
            email_data = self._generate_email(company, contact, research)
            
            if email_data:
                all_emails.append({
                    'company_name': company['company_name'],
                    'contact_name': contact['name'],
                    'subject': email_data['subject'],
                    'body': email_data['body'],
                    'reasoning': email_data.get('reasoning', ''),
                    'company': company,
                    'contact': contact,
                    'research': research
                })
        
        if not all_emails:
            console.print("[red]No emails generated[/red]")
            return []
        
        console.print(f"\n[green]✓ Generated {len(all_emails)} emails![/green]")
        
        # Batch review
        approved_emails_data = self.review_layer.review_emails_batch(all_emails)
        
        # Convert to final format
        approved = []
        for email in approved_emails_data:
            approved.append({
                'company_name': email['company_name'],
                'company_overview': email['company'].get('overview', ''),
                'contact_name': email['contact_name'],
                'contact_role': email['contact'].get('role', ''),
                'contact_linkedin': email['contact'].get('linkedin', ''),
                'contact_email': email['contact'].get('email', ''),
                'subject': email['subject'],
                'body': email['body'],
                'research_notes': json.dumps(email.get('research', {}))
            })
        
        return approved
    
    def _generate_and_review_emails_sequential(self, leads: List[Dict]) -> List[Dict]:
        """
        Sequential mode: Generate and review each email one-by-one
        """
        approved = []
        
        for idx, lead in enumerate(leads):
            console.print(f"\n[cyan]Email {idx+1}/{len(leads)}[/cyan]")
            
            company = lead['company']
            contact = lead['contact']
            research = lead.get('research', {})
            
            max_attempts = 3
            for attempt in range(max_attempts):
                # Generate email
                email_data = self._generate_email(company, contact, research)
                
                if not email_data:
                    console.print("[red]Failed to generate email[/red]")
                    break
                
                # Human review
                review_result = self.review_layer.review_email(
                    company_name=company['company_name'],
                    contact_name=contact['name'],
                    subject=email_data['subject'],
                    body=email_data['body'],
                    reasoning=email_data.get('reasoning', '')
                )
                
                if review_result['status'] == 'approved':
                    # Final checklist
                    if self.review_layer.final_checklist(
                        review_result['subject'],
                        review_result['body']
                    ):
                        approved.append({
                            'company_name': company['company_name'],
                            'company_overview': company.get('overview', ''),
                            'contact_name': contact['name'],
                            'contact_role': contact.get('role', ''),
                            'contact_linkedin': contact.get('linkedin', ''),
                            'contact_email': contact.get('email', ''),
                            'subject': review_result['subject'],
                            'body': review_result['body'],
                            'research_notes': json.dumps(research)
                        })
                        break
                
                elif review_result['status'] == 'edited':
                    # Use edited version
                    approved.append({
                        'company_name': company['company_name'],
                        'company_overview': company.get('overview', ''),
                        'contact_name': contact['name'],
                        'contact_role': contact.get('role', ''),
                        'contact_linkedin': contact.get('linkedin', ''),
                        'contact_email': contact.get('email', ''),
                        'subject': review_result['subject'],
                        'body': review_result['body'],
                        'research_notes': json.dumps(research)
                    })
                    break
                
                elif review_result['status'] == 'regenerate':
                    if attempt < max_attempts - 1:
                        console.print("[yellow]Regenerating...[/yellow]")
                        continue
                    else:
                        console.print("[yellow]Max attempts reached, skipping[/yellow]")
                        break
                
                else:  # skipped
                    break
        
        return approved
    
    def _generate_email(
        self,
        company: Dict,
        contact: Dict,
        research: Dict
    ) -> Optional[Dict]:
        """
        Generate one email using Claude + research notes
        """
        # Build context from research (handles both auto and manual research)
        if research.get('auto_generated'):
            # Auto-research format
            recent_activity = "\n".join([
                f"Recent Activity: {research.get('recent_activity', 'N/A')}",
                f"News: {research.get('news_articles', [{}])[0].get('title', 'N/A') if research.get('news_articles') else 'N/A'}"
            ])
            research_notes = json.dumps({
                'current_focus': research.get('current_focus', 'N/A'),
                'pain_point': research.get('pain_point', 'N/A'),
                'best_angle': research.get('best_angle', 'N/A'),
                'manual_notes': research.get('manual_notes', '')
            }, indent=2)
        else:
            # Manual research format
            recent_activity = "\n".join([
                f"LinkedIn: {research.get('recent_linkedin_posts', 'N/A')}",
                f"Company News: {research.get('recent_news', 'N/A')}",
                f"Current Focus: {research.get('current_focus', 'N/A')}"
            ])
            research_notes = json.dumps(research, indent=2)
        
        user_prompt = EMAIL_GENERATION_USER_TEMPLATE.format(
            contact_name=contact['name'],
            contact_role=contact.get('role', ''),
            company_name=company['company_name'],
            company_context=company.get('overview', ''),
            recent_activity=recent_activity,
            research_notes=research_notes,
            why_relevant=company.get('why_relevant_to_convexia', '')
        )
        
        try:
            return claude.chat_json(
                system_prompt=EMAIL_GENERATION_SYSTEM,
                user_prompt=user_prompt,
                temperature=0.8  # Higher temp for more variety
            )
        except Exception as e:
            console.print(f"[red]Email generation error: {e}[/red]")
            return None
    
    def _export_results(self, emails: List[Dict], query: str):
        """
        Export approved emails to CSV
        """
        if not emails:
            return
        
        df = pd.DataFrame(emails)
        
        # Clean query for filename
        safe_query = "".join(c for c in query if c.isalnum() or c in (' ', '_')).strip()
        safe_query = safe_query.replace(' ', '_')[:30]
        
        output_file = config.OUTPUT_DIR / f"{safe_query}_approved_emails.csv"
        df.to_csv(output_file, index=False)
        
        console.print(f"\n[green]📁 Saved to: {output_file}[/green]")
    
    def _deduplicate_companies(self, companies: List[Dict]) -> List[Dict]:
        """Remove duplicate companies by name"""
        seen = set()
        unique = []
        
        for company in companies:
            name = company.get('company_name', '').lower().strip()
            if name and name not in seen:
                seen.add(name)
                unique.append(company)
        
        return unique
