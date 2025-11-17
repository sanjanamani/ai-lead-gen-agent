"""
Pydantic models for data validation and structure
Ensures data consistency and type safety throughout the pipeline
"""

from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, validator
import validators


class ClinicalTrial(BaseModel):
    """Model for clinical trial data"""
    nct_id: Optional[str] = Field(None, description="NCT identifier")
    title: str
    condition_or_disease: Optional[str] = None
    intervention_name: Optional[str] = None
    phase: Optional[str] = None
    status: str
    sponsor: Optional[str] = None
    why_stopped: Optional[str] = None
    completion_date: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "nct_id": "NCT12345678",
                "title": "Study of Drug X in Solid Tumors",
                "condition_or_disease": "Non-Small Cell Lung Cancer",
                "intervention_name": "Drug X",
                "phase": "Phase 2",
                "status": "Terminated",
                "sponsor": "Biotech Company Inc",
                "why_stopped": "Lack of efficacy",
                "completion_date": "2023-06-15"
            }
        }


class DormantAsset(BaseModel):
    """Model for dormant drug assets"""
    asset_name: str
    indication: Optional[str] = None
    status: Literal["dormant", "paused", "unknown"] = "unknown"
    notes: Optional[str] = None


class DrugAsset(BaseModel):
    """Model for drug asset information"""
    name: str
    modality: Literal[
        "small molecule",
        "biologic",
        "gene therapy",
        "cell therapy",
        "RNA therapy",
        "other",
        "unknown"
    ] = "unknown"
    indication: Optional[str] = None
    development_stage: Literal[
        "preclinical",
        "phase 1",
        "phase 2",
        "phase 3",
        "approved",
        "unknown"
    ] = "unknown"
    target: Optional[str] = None


class Investor(BaseModel):
    """Model for investor information"""
    name: str
    type: Literal["vc", "corporate", "family office", "angel", "strategic", "unknown"] = "unknown"
    notable_portfolio_companies: List[str] = Field(default_factory=list)
    investment_round: Optional[str] = None


class DecisionMaker(BaseModel):
    """Model for decision maker / contact information"""
    name: str
    role: Optional[str] = None
    linkedin_url: Optional[str] = None
    email: Optional[str] = None
    source: str = "unknown"
    
    @validator("linkedin_url")
    def validate_linkedin_url(cls, v):
        if v and not validators.url(v):
            raise ValueError(f"Invalid LinkedIn URL: {v}")
        return v
    
    @validator("email")
    def validate_email(cls, v):
        if v and not validators.email(v):
            raise ValueError(f"Invalid email: {v}")
        return v


class ClinicalTrialsData(BaseModel):
    """Container for clinical trials data"""
    phase_2_failed: List[ClinicalTrial] = Field(default_factory=list)
    phase_3_failed: List[ClinicalTrial] = Field(default_factory=list)
    dormant_assets: List[DormantAsset] = Field(default_factory=list)


class Company(BaseModel):
    """Complete company profile for CRM"""
    company_name: str = Field(..., min_length=1)
    overview: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    therapeutic_areas: List[str] = Field(default_factory=list)
    clinical_trials: ClinicalTrialsData = Field(default_factory=ClinicalTrialsData)
    drug_assets: List[DrugAsset] = Field(default_factory=list)
    decision_makers: List[DecisionMaker] = Field(default_factory=list)
    investors: List[Investor] = Field(default_factory=list)
    fit_score_for_convexia: int = Field(0, ge=0, le=100)
    reason_for_fit_score: Optional[str] = None
    data_sources_used: List[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    @validator("website")
    def validate_website(cls, v):
        if v and not validators.url(v):
            # Try to fix common issues
            if not v.startswith(("http://", "https://")):
                v = f"https://{v}"
            if not validators.url(v):
                raise ValueError(f"Invalid website URL: {v}")
        return v
    
    @validator("company_name")
    def normalize_company_name(cls, v):
        """Normalize company name for better deduplication"""
        # Remove common suffixes
        suffixes = [" Inc", " Inc.", " LLC", " Ltd", " Ltd.", " Corporation", " Corp", " Corp."]
        normalized = v.strip()
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)].strip()
        return normalized
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "Example Biotech",
                "overview": "Oncology-focused biotech developing novel therapeutics",
                "location": "Cambridge, MA, USA",
                "website": "https://examplebiotech.com",
                "therapeutic_areas": ["oncology", "immuno-oncology"],
                "fit_score_for_convexia": 85,
                "reason_for_fit_score": "Failed Phase 2 trial with compelling MOA"
            }
        }


class EmailOutreach(BaseModel):
    """Model for outreach email generation"""
    company_name: str
    company_overview: Optional[str] = None
    contact_name: str
    contact_role: Optional[str] = None
    contact_linkedin: Optional[str] = None
    contact_email: Optional[str] = None
    subject: str = Field(..., max_length=80)
    body: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "company_name": "Example Biotech",
                "contact_name": "Dr. Jane Smith",
                "contact_role": "CEO",
                "subject": "Exploring drug rescue opportunities together",
                "body": "Hi Dr. Smith,\n\nI came across Example Biotech..."
            }
        }


class SearchResult(BaseModel):
    """Model for web search results"""
    title: str
    url: str
    snippet: str
    source: str = "web"
    relevance_score: Optional[float] = None
    
    @validator("url")
    def validate_url(cls, v):
        if not validators.url(v):
            raise ValueError(f"Invalid URL: {v}")
        return v
