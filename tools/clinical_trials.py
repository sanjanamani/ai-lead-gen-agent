"""
ClinicalTrials.gov API client
"""

import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta


def search_clinical_trials(
    query: str,
    status: Optional[List[str]] = None,
    max_results: int = 20
) -> List[Dict]:
    """
    Search ClinicalTrials.gov for trials
    
    Args:
        query: Search query (condition, intervention, etc.)
        status: Trial statuses to filter (e.g., ["TERMINATED", "WITHDRAWN"])
        max_results: Max number of results
        
    Returns:
        List of trial data
    """
    if status is None:
        status = ["TERMINATED", "WITHDRAWN", "SUSPENDED"]
    
    # ClinicalTrials.gov API v2
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    
    params = {
        "query.cond": query,
        "filter.overallStatus": ",".join(status),
        "pageSize": max_results,
        "format": "json"
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        trials = []
        for study in data.get("studies", []):
            protocol = study.get("protocolSection", {})
            
            # Extract key info
            id_module = protocol.get("identificationModule", {})
            status_module = protocol.get("statusModule", {})
            sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
            design_module = protocol.get("designModule", {})
            conditions_module = protocol.get("conditionsModule", {})
            interventions_module = protocol.get("armsInterventionsModule", {})
            
            trial_data = {
                "nct_id": id_module.get("nctId", ""),
                "title": id_module.get("officialTitle", id_module.get("briefTitle", "")),
                "status": status_module.get("overallStatus", ""),
                "phase": design_module.get("phases", ["Unknown"])[0] if design_module.get("phases") else "Unknown",
                "conditions": conditions_module.get("conditions", []),
                "interventions": [
                    interv.get("name", "")
                    for interv in interventions_module.get("interventions", [])
                ],
                "sponsor": sponsor_module.get("leadSponsor", {}).get("name", ""),
                "why_stopped": status_module.get("whyStopped", ""),
                "start_date": status_module.get("startDateStruct", {}).get("date", ""),
                "completion_date": status_module.get("completionDateStruct", {}).get("date", ""),
            }
            
            trials.append(trial_data)
        
        return trials
    
    except Exception as e:
        print(f"ClinicalTrials.gov error: {e}")
        return []


def get_recent_failures(
    condition: str,
    days_back: int = 365,
    phases: Optional[List[str]] = None
) -> List[Dict]:
    """
    Get trials that failed/terminated recently
    
    Args:
        condition: Disease/condition
        days_back: How many days to look back
        phases: Phase filter (e.g., ["Phase 2", "Phase 3"])
        
    Returns:
        List of failed trials
    """
    if phases is None:
        phases = ["Phase 2", "Phase 3"]
    
    trials = search_clinical_trials(condition, max_results=50)
    
    # Filter by date and phase
    cutoff_date = datetime.now() - timedelta(days=days_back)
    recent_failures = []
    
    for trial in trials:
        # Check phase
        if trial["phase"] not in phases:
            continue
        
        # Check date
        comp_date_str = trial.get("completion_date", "")
        if comp_date_str:
            try:
                comp_date = datetime.strptime(comp_date_str, "%Y-%m-%d")
                if comp_date >= cutoff_date:
                    recent_failures.append(trial)
            except:
                # If date parsing fails, include it anyway
                recent_failures.append(trial)
    
    return recent_failures


def get_company_trials(company_name: str) -> List[Dict]:
    """
    Get all trials for a specific company
    
    Args:
        company_name: Sponsor company name
        
    Returns:
        List of trials
    """
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    
    params = {
        "query.lead": company_name,
        "pageSize": 50,
        "format": "json"
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        trials = []
        for study in data.get("studies", []):
            protocol = study.get("protocolSection", {})
            
            id_module = protocol.get("identificationModule", {})
            status_module = protocol.get("statusModule", {})
            design_module = protocol.get("designModule", {})
            
            trial_data = {
                "nct_id": id_module.get("nctId", ""),
                "title": id_module.get("briefTitle", ""),
                "status": status_module.get("overallStatus", ""),
                "phase": design_module.get("phases", ["Unknown"])[0] if design_module.get("phases") else "Unknown",
            }
            
            trials.append(trial_data)
        
        return trials
    
    except Exception as e:
        print(f"Error fetching company trials: {e}")
        return []
