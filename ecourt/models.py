"""
Data models representing structured eCourts case information.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CaseDetails(BaseModel):
    case_type: Optional[str] = None
    filing_number: Optional[str] = None
    filing_date: Optional[str] = None
    registration_number: Optional[str] = None
    registration_date: Optional[str] = None
    cnr_number: Optional[str] = None
    e_filing_number: Optional[str] = None
    e_filing_date: Optional[str] = None


class CaseStatus(BaseModel):
    first_hearing_date: Optional[str] = None
    next_hearing_date: Optional[str] = None
    case_stage: Optional[str] = None
    court_number_and_judge: Optional[str] = None


class Party(BaseModel):
    name: str
    advocate: Optional[str] = None


class Act(BaseModel):
    under_act: str
    under_section: str


class ProcessRecord(BaseModel):
    process_id: str
    process_title: str
    process_date: str


class IAStatus(BaseModel):
    ia_number: str
    party_name: str
    filing_date: str
    next_date: str
    purpose: Optional[str] = None
    status: str


class HearingHistory(BaseModel):
    judge: str
    business_on_date: str
    hearing_date: str
    purpose_of_hearing: str


class ECourtCaseResult(BaseModel):
    cnr: str
    court_name: str
    case_details: CaseDetails
    case_status: CaseStatus
    petitioners: List[Party] = Field(default_factory=list)
    respondents: List[Party] = Field(default_factory=list)
    acts: List[Act] = Field(default_factory=list)
    processes: List[ProcessRecord] = Field(default_factory=list)
    ia_status: List[IAStatus] = Field(default_factory=list)
    case_history: List[HearingHistory] = Field(default_factory=list)
    raw_html: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
