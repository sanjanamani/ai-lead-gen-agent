"""
Clinical Trials data fetcher using ClinicalTrials.gov API v2
Completely FREE - no API key required
"""

import requests
from typing import List, Dict, Any, Optional
from datetime import datetime

from config.settings import config
from config.models import ClinicalTrial
from config.utils import logger, retry_with_backoff, cached, normalize_phase, is_valid_nct_id


@retry_with_backoff(exceptions=(requests.RequestException,))
@cached(expire=86400)  # Cache for 24 hours
def fetch_clinical_trials_for_query(
    query: str,
    max_records: int = 50,
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Fetch clinical trials from ClinicalTrials.gov API v2
    
    Args:
        query: Search query string
        max_records: Maximum number of records to return
        filters: Additional filters (status, phase, etc.)
    
    Returns:
        List of trial dicts with structured data
    """
    
    # Build query parameters
    params = {
        "query.term": query,
        "pageSize": min(max_records, 1000),  # API max is 1000
        "format": "json",
    }
    
    # Add filters if provided
    if filters:
        if "status" in filters:
            params["filter.overallStatus"] = filters["status"]
        if "phase" in filters:
            params["filter.phase"] = filters["phase"]
    
    try:
        logger.info(f"Fetching clinical trials for query: {query[:50]}...")
        response = requests.get(
            config.ctgov_base_url,
            params=params,
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        
        studies = data.get("studies", [])
        logger.info(f"Retrieved {len(studies)} clinical trials")
        
        trials = []
        for study in studies:
            trial_data = _parse_study(study)
            if trial_data:
                trials.append(trial_data)
        
        return trials[:max_records]
        
    except requests.RequestException as e:
        logger.error(f"ClinicalTrials.gov API error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching clinical trials: {e}")
        return []


def _parse_study(study: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse a single study from ClinicalTrials.gov API v2
    
    Args:
        study: Raw study data from API
    
    Returns:
        Structured trial dict or None if invalid
    """
    try:
        protocol = study.get("protocolSection", {})
        identification = protocol.get("identificationModule", {})
        status = protocol.get("statusModule", {})
        conditions = protocol.get("conditionsModule", {})
        arms_interventions = protocol.get("armsInterventionsModule", {})
        sponsor = protocol.get("sponsorCollaboratorsModule", {})
        
        # Extract NCT ID
        nct_id = identification.get("nctId", "")
        if not is_valid_nct_id(nct_id):
            return None
        
        # Extract basic info
        title = identification.get("briefTitle", "")
        overall_status = status.get("overallStatus", "Unknown")
        
        # Extract phase
        design = protocol.get("designModule", {})
        phases = design.get("phases", [])
        phase = phases[0] if phases else "Unknown"
        phase = normalize_phase(phase)
        
        # Extract conditions/diseases
        condition_list = conditions.get("conditions", [])
        condition_str = ", ".join(condition_list) if condition_list else None
        
        # Extract interventions
        interventions = arms_interventions.get("interventions", [])
        intervention_names = []
        for intervention in interventions:
            name = intervention.get("name")
            if name:
                intervention_names.append(name)
        intervention_str = ", ".join(intervention_names) if intervention_names else None
        
        # Extract sponsor
        lead_sponsor = sponsor.get("leadSponsor", {})
        sponsor_name = lead_sponsor.get("name")
        
        # Extract why stopped (if applicable)
        why_stopped = status.get("whyStopped")
        
        # Extract completion date
        completion_date = None
        if "completionDateStruct" in status:
            date_struct = status["completionDateStruct"]
            completion_date = date_struct.get("date")
        
        return {
            "nct_id": nct_id,
            "title": title,
            "conditions": condition_str,
            "overall_status": overall_status,
            "phase": phase,
            "sponsor": sponsor_name,
            "why_stopped": why_stopped,
            "intervention_name": intervention_str,
            "completion_date": completion_date,
            "summary": identification.get("briefSummary", {}).get("text"),
        }
        
    except Exception as e:
        logger.warning(f"Error parsing study: {e}")
        return None


def fetch_failed_trials_for_company(
    company_name: str,
    phases: Optional[List[str]] = None,
    max_records: int = 50
) -> Dict[str, List[ClinicalTrial]]:
    """
    Fetch failed/terminated trials for a specific company
    
    Args:
        company_name: Name of the company/sponsor
        phases: List of phases to filter (e.g., ["Phase 2", "Phase 3"])
        max_records: Maximum number of records per phase
    
    Returns:
        Dict with phase_2_failed, phase_3_failed lists
    """
    if phases is None:
        phases = ["Phase 2", "Phase 3"]
    
    result = {
        "phase_2_failed": [],
        "phase_3_failed": [],
    }
    
    # Fetch terminated/suspended trials
    filters = {
        "status": "TERMINATED,SUSPENDED,WITHDRAWN"
    }
    
    # Search by company name
    trials = fetch_clinical_trials_for_query(
        query=company_name,
        max_records=max_records * 2,  # Fetch more since we'll filter
        filters=filters
    )
    
    # Categorize by phase
    for trial_data in trials:
        phase = trial_data.get("phase", "").lower()
        
        # Create ClinicalTrial model
        try:
            trial = ClinicalTrial(
                nct_id=trial_data["nct_id"],
                title=trial_data["title"],
                condition_or_disease=trial_data.get("conditions"),
                intervention_name=trial_data.get("intervention_name"),
                phase=trial_data.get("phase"),
                status=trial_data["overall_status"],
                sponsor=trial_data.get("sponsor"),
                why_stopped=trial_data.get("why_stopped"),
                completion_date=trial_data.get("completion_date")
            )
            
            # Categorize
            if "phase 2" in phase or "phase ii" in phase:
                result["phase_2_failed"].append(trial)
            elif "phase 3" in phase or "phase iii" in phase:
                result["phase_3_failed"].append(trial)
                
        except Exception as e:
            logger.warning(f"Could not create ClinicalTrial model: {e}")
            continue
    
    logger.info(
        f"Found {len(result['phase_2_failed'])} Phase 2 and "
        f"{len(result['phase_3_failed'])} Phase 3 failed trials for {company_name}"
    )
    
    return result


def search_trials_by_indication(
    indication: str,
    status: str = "TERMINATED,SUSPENDED,WITHDRAWN",
    phase: Optional[str] = None,
    max_records: int = 100
) -> List[Dict[str, Any]]:
    """
    Search for trials by disease/indication and status
    
    Args:
        indication: Disease or condition (e.g., "solid tumors", "NSCLC")
        status: Trial status (default: failed trials)
        phase: Specific phase filter (e.g., "PHASE2")
        max_records: Maximum results
    
    Returns:
        List of trial dicts
    """
    filters = {"status": status}
    if phase:
        filters["phase"] = phase
    
    return fetch_clinical_trials_for_query(
        query=indication,
        max_records=max_records,
        filters=filters
    )


# Testing
if __name__ == "__main__":
    # Test fetching trials
    trials = fetch_clinical_trials_for_query(
        query="oncology biotech phase 2 failed",
        max_records=10
    )
    
    print(f"Found {len(trials)} trials")
    for trial in trials[:3]:
        print(f"\n{trial['nct_id']}: {trial['title']}")
        print(f"  Status: {trial['overall_status']}")
        print(f"  Phase: {trial['phase']}")
        print(f"  Sponsor: {trial['sponsor']}")
