"""
Configuration constants for the eCourts Scraper.
"""

BASE_URL = "https://services.ecourts.gov.in"
HOME_PATH = "/ecourtindia_v6/?p=home/index"
SEARCH_AJAX_PATH = "/ecourtindia_v6/?p=cnr_status/searchByCNR/"

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://services.ecourts.gov.in/",
}

DEFAULT_TIMEOUT = 25  # seconds
DEFAULT_MAX_RETRIES = 10
