"""
Main Convexia CRM Agent - Production-ready implementation
Orchestrates the full pipeline from query to structured company data
"""

import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import pandas as pd

from config.settings import config
from config.models import Company, DecisionMaker, EmailOutreach, ClinicalTrialsData
from config.llm_client import LLMClient
from config.utils import (
    logger,
    save_json,
    deduplicate_companies,
    timestamp_now
)
from config.prompts import (
    SYSTEM_PLANNER_PROMPT,
    SYSTEM_SYNTHESIS_PROMPT,
    COMPANY_SYNTHESIS_USER_PROMPT_TEMPLATE,
    EMAIL_GENERATION_SYSTEM_PROMPT,
    EMAIL_GENERATION_USER_PROMPT_TEMPLATE
)
from tools.web_search import SearchClient, find_decision_makers_for_company
from tools.clinical_trials import fetch_clinical_trials_for_query


class ConvexiaCRMAgent:
    """
    Production-ready Convexia CRM Agent
    
    Pipeline:
    1. Plan: Use LLM to break down query into research plan
    2. Search: Web search + Clinical trials data gathering
    3. Synthesize: LLM converts raw data into structured company profiles
    4. Enrich: Add decision makers from LinkedIn
    5. Score: Validate and score each company for Convexia fit
    6. Save: Persist to JSON files
    7. (Optional) Generate personalized outreach emails
    """
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        search_client: Optional[SearchClient] = None,
        max_companies: Optional[int] = None,
        output_dir: Optional[Path] = None,
    ):
        self.llm = llm_client or LLMClient()
        self.search = search_client or SearchClient()
        self.max_companies = max_companies or config.max_companies
        self.output_dir = output_dir or config.output_dir
        
        logger.info(f"Initialized ConvexiaCRMAgent (max_companies={self.max_companies})")
    
    # ========================================
    # Main Pipeline
    # ========================================
    
    def run_query(self, query: str) -> List[Company]:
        """
        Execute full pipeline for a query
        
        Args:
            query: Natural language query about target companies
        
        Returns:
            List of Company objects with full profiles
        """
        run_id = str(uuid.uuid4())[:8]
        logger.info(f"[{run_id}] Starting pipeline for query: '{query}'")
        
        try:
            # Step 1: Planning
            plan = self._plan(query, run_id)
            
            # Step 2: Data gathering
            search_results = self._web_search(query, run_id)
            trials_data = self._clinical_trials_search(query, run_id)
            
            # Step 3: Synthesis
            companies = self._synthesize_companies(
                query, search_results, trials_data, run_id
            )
            
            if not companies:
                logger.warning(f"[{run_id}] No companies synthesized from data")
                return []
            
            # Step 4: Enrichment
            companies = self._enrich_with_decision_makers(companies, run_id)
            
            # Step 5: Validation & Scoring
            companies = self._validate_companies(companies, run_id)
            
            # Step 6: Save
            self._save_companies(companies, run_id)
            
            logger.info(
                f"[{run_id}] Pipeline complete. Generated {len(companies)} companies."
            )
            return companies
            
        except Exception as e:
            logger.error(f"[{run_id}] Pipeline failed: {e}", exc_info=True)
            return []
    
    def run_query_with_outputs(
        self,
        query: str,
        generate_emails: bool = False
    ) -> Tuple[List[Company], pd.DataFrame, pd.DataFrame, Optional[pd.DataFrame]]:
        """
        Run pipeline and return structured outputs
        
        Returns:
            companies, companies_df, decision_makers_df, emails_df
        """
        companies = self.run_query(query)
        
        emails = None
        if generate_emails and companies:
            emails = self.generate_emails(companies)
        
        companies_df, dms_df, emails_df = self._to_dataframes(companies, emails)
        
        return companies, companies_df, dms_df, emails_df
    
    # ========================================
    # Step 1: Planning
    # ========================================
    
    def _plan(self, query: str, run_id: str) -> Dict[str, Any]:
        """Generate research plan using LLM"""
        logger.info(f"[{run_id}] Generating research plan...")
        
        try:
            user_prompt = f"User query: {query}\n\nGenerate a research plan as JSON."
            plan = self.llm.chat_json(
                system_prompt=SYSTEM_PLANNER_PROMPT,
                user_prompt=user_prompt
            )
            logger.debug(f"[{run_id}] Plan: {json.dumps(plan, indent=2)}")
            return plan
        except Exception as e:
            logger.warning(f"[{run_id}] Planning failed: {e}")
            return {
                "high_level_goal": "Identify biotech companies matching query",
                "steps": ["Search", "Analyze", "Synthesize"]
            }
    
    # ========================================
    # Step 2: Data Gathering
    # ========================================
    
    def _web_search(self, query: str, run_id: str) -> List[Dict[str, Any]]:
        """Execute web search for companies"""
        logger.info(f"[{run_id}] Searching web...")
        
        try:
            results = self.search.search_companies(
                query,
                num_results=self.max_companies * 3
            )
            
            # Convert to dict format
            results_dicts = [
                {
                    "title": r.title,
                    "url": r.url,
                    "snippet": r.snippet,
                    "source": r.source
                }
                for r in results
            ]
            
            logger.info(f"[{run_id}] Web search returned {len(results_dicts)} results")
            return results_dicts
            
        except Exception as e:
            logger.error(f"[{run_id}] Web search failed: {e}")
            return []
    
    def _clinical_trials_search(self, query: str, run_id: str) -> List[Dict[str, Any]]:
        """Fetch clinical trials data"""
        logger.info(f"[{run_id}] Fetching clinical trials...")
        
        try:
            trials = fetch_clinical_trials_for_query(
                query,
                max_records=self.max_companies * 10
            )
            logger.info(f"[{run_id}] Found {len(trials)} clinical trials")
            return trials
            
        except Exception as e:
            logger.error(f"[{run_id}] Clinical trials fetch failed: {e}")
            return []
    
    # ========================================
    # Step 3: Synthesis
    # ========================================
    
    def _synthesize_companies(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        trials_data: List[Dict[str, Any]],
        run_id: str
    ) -> List[Company]:
        """Use LLM to synthesize structured company data"""
        logger.info(f"[{run_id}] Synthesizing companies with LLM...")
        
        # Prepare context
        context = {
            "user_query": query,
            "web_search_results": search_results[:30],  # Limit to avoid token issues
            "clinical_trials_data": trials_data[:50],
            "max_companies": self.max_companies
        }
        
        # Generate prompt
        user_prompt = COMPANY_SYNTHESIS_USER_PROMPT_TEMPLATE.format(
            query=query,
            context=json.dumps(context, indent=2, ensure_ascii=False),
            max_companies=self.max_companies
        )
        
        try:
            # Get LLM response
            raw_response = self.llm.chat(
                system_prompt=SYSTEM_SYNTHESIS_PROMPT,
                user_prompt=user_prompt,
                json_mode=True
            )
            
            # Parse JSON
            companies_data = json.loads(raw_response) if isinstance(raw_response, str) else raw_response
            
            if not isinstance(companies_data, list):
                logger.warning(f"[{run_id}] LLM returned non-list, wrapping")
                companies_data = [companies_data]
            
            # Validate and create Company objects
            companies = []
            for company_dict in companies_data[:self.max_companies]:
                try:
                    company = Company(**company_dict)
                    companies.append(company)
                except Exception as e:
                    logger.warning(f"[{run_id}] Failed to create Company object: {e}")
                    continue
            
            logger.info(f"[{run_id}] Synthesized {len(companies)} valid companies")
            return companies
            
        except Exception as e:
            logger.error(f"[{run_id}] Synthesis failed: {e}")
            return []
    
    # ========================================
    # Step 4: Enrichment
    # ========================================
    
    def _enrich_with_decision_makers(
        self,
        companies: List[Company],
        run_id: str
    ) -> List[Company]:
        """Add decision makers via LinkedIn search"""
        logger.info(f"[{run_id}] Enriching with decision makers...")
        
        for idx, company in enumerate(companies, 1):
            logger.info(
                f"[{run_id}] [{idx}/{len(companies)}] "
                f"Finding decision makers for {company.company_name}"
            )
            
            try:
                dms_data = find_decision_makers_for_company(
                    company_name=company.company_name,
                    website=company.website,
                    max_people=config.max_decision_makers_per_company
                )
                
                # Convert to DecisionMaker objects
                for dm_dict in dms_data:
                    try:
                        dm = DecisionMaker(**dm_dict)
                        company.decision_makers.append(dm)
                    except Exception as e:
                        logger.warning(f"Invalid decision maker data: {e}")
                        continue
                
                logger.info(
                    f"[{run_id}] Found {len(company.decision_makers)} "
                    f"decision makers for {company.company_name}"
                )
                
            except Exception as e:
                logger.warning(f"[{run_id}] DM search failed for {company.company_name}: {e}")
                continue
        
        return companies
    
    # ========================================
    # Step 5: Validation
    # ========================================
    
    def _validate_companies(
        self,
        companies: List[Company],
        run_id: str
    ) -> List[Company]:
        """Validate and filter companies"""
        logger.info(f"[{run_id}] Validating companies...")
        
        valid_companies = []
        for company in companies:
            # Basic validation
            if not company.company_name:
                logger.warning(f"[{run_id}] Skipping company with no name")
                continue
            
            # Check if we have meaningful data
            has_trials = (
                len(company.clinical_trials.phase_2_failed) > 0 or
                len(company.clinical_trials.phase_3_failed) > 0
            )
            has_assets = len(company.drug_assets) > 0
            has_overview = bool(company.overview)
            
            if not (has_trials or has_assets or has_overview):
                logger.warning(
                    f"[{run_id}] Skipping {company.company_name} - insufficient data"
                )
                continue
            
            valid_companies.append(company)
        
        logger.info(f"[{run_id}] Validated {len(valid_companies)}/{len(companies)} companies")
        return valid_companies
    
    # ========================================
    # Step 6: Save
    # ========================================
    
    def _save_companies(self, companies: List[Company], run_id: str):
        """Save companies to JSON files"""
        logger.info(f"[{run_id}] Saving companies...")
        
        for company in companies:
            # Create safe filename
            safe_name = "".join(
                c for c in company.company_name if c.isalnum() or c in ("-", "_")
            ).strip() or "unknown"
            filename = f"{safe_name}_{run_id}"
            
            # Save as JSON
            save_json(
                company.dict(),
                filename=filename,
                directory=self.output_dir
            )
    
    # ========================================
    # Email Generation
    # ========================================
    
    def generate_emails(
        self,
        companies: List[Company],
        from_name: str = "Ayaan",
        from_title: str = "Co-founder",
        from_company: str = "Convexia Bio"
    ) -> List[EmailOutreach]:
        """Generate personalized outreach emails for all decision makers"""
        logger.info("Generating personalized emails...")
        
        emails = []
        for company in companies:
            for dm in company.decision_makers:
                try:
                    email = self._generate_single_email(
                        company, dm, from_name, from_title, from_company
                    )
                    if email:
                        emails.append(email)
                except Exception as e:
                    logger.warning(f"Email generation failed for {dm.name}: {e}")
                    continue
        
        logger.info(f"Generated {len(emails)} emails")
        return emails
    
    def _generate_single_email(
        self,
        company: Company,
        dm: DecisionMaker,
        from_name: str,
        from_title: str,
        from_company: str
    ) -> Optional[EmailOutreach]:
        """Generate a single personalized email"""
        
        user_prompt = EMAIL_GENERATION_USER_PROMPT_TEMPLATE.format(
            from_name=from_name,
            from_title=from_title,
            contact_name=dm.name,
            contact_role=dm.role or "there",
            contact_linkedin=dm.linkedin_url or "N/A",
            company_name=company.company_name,
            company_overview=company.overview or "N/A",
            therapeutic_areas=", ".join(company.therapeutic_areas) or "N/A",
            reason_for_fit=company.reason_for_fit_score or "N/A"
        )
        
        try:
            email_data = self.llm.chat_json(
                system_prompt=EMAIL_GENERATION_SYSTEM_PROMPT,
                user_prompt=user_prompt
            )
            
            return EmailOutreach(
                company_name=company.company_name,
                company_overview=company.overview,
                contact_name=dm.name,
                contact_role=dm.role,
                contact_linkedin=dm.linkedin_url,
                contact_email=dm.email,
                subject=email_data.get("subject", "Exploring opportunities together"),
                body=email_data.get("body", "")
            )
        except Exception as e:
            logger.error(f"Email generation failed: {e}")
            return None
    
    # ========================================
    # Utilities
    # ========================================
    
    def _to_dataframes(
        self,
        companies: List[Company],
        emails: Optional[List[EmailOutreach]] = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Optional[pd.DataFrame]]:
        """Convert to pandas DataFrames for analysis"""
        
        # Companies DataFrame
        company_rows = []
        for c in companies:
            company_rows.append({
                "company_name": c.company_name,
                "location": c.location,
                "website": c.website,
                "therapeutic_areas": ", ".join(c.therapeutic_areas),
                "fit_score": c.fit_score_for_convexia,
                "reason_for_fit": c.reason_for_fit_score,
                "num_decision_makers": len(c.decision_makers),
                "num_phase2_failed": len(c.clinical_trials.phase_2_failed),
                "num_phase3_failed": len(c.clinical_trials.phase_3_failed),
                "num_drug_assets": len(c.drug_assets),
            })
        
        # Decision Makers DataFrame
        dm_rows = []
        for c in companies:
            for dm in c.decision_makers:
                dm_rows.append({
                    "company_name": c.company_name,
                    "name": dm.name,
                    "role": dm.role,
                    "linkedin_url": dm.linkedin_url,
                    "email": dm.email,
                    "source": dm.source
                })
        
        # Emails DataFrame
        emails_df = None
        if emails:
            emails_df = pd.DataFrame([e.dict() for e in emails])
        
        return (
            pd.DataFrame(company_rows),
            pd.DataFrame(dm_rows),
            emails_df
        )


# Convenience function for backwards compatibility
def run_convexia_agent(query: str, max_companies: int = 5) -> List[Dict[str, Any]]:
    """Simple function to run the agent and return company dicts"""
    agent = ConvexiaCRMAgent(max_companies=max_companies)
    companies = agent.run_query(query)
    return [c.dict() for c in companies]
