"""
eCourt Scraper Package
Automated case details scraping by CNR number with neural captcha solving.
"""

from .scraper import ECourtScraper
from .captcha import CaptchaSolver
from .parser import parse_case_html
from .models import (
    ECourtCaseResult,
    CaseDetails,
    CaseStatus,
    Party,
    Act,
    ProcessRecord,
    IAStatus,
    HearingHistory,
)

__all__ = [
    "ECourtScraper",
    "CaptchaSolver",
    "parse_case_html",
    "ECourtCaseResult",
    "CaseDetails",
    "CaseStatus",
    "Party",
    "Act",
    "ProcessRecord",
    "IAStatus",
    "HearingHistory",
]
