"""
Ultra-fast eCourts Scraper Engine.
Features:
- Pre-warmed singleton neural captcha solver (~30ms OCR)
- In-memory cached dynamic security headers (skips re-fetching components.js)
- Connection pooling with HTTP Keep-Alive
- High-speed regex extraction of tokens & captcha URLs (<1ms vs 50ms DOM parsing)
- Ultra-low latency retry loop
"""

import re
import time
import urllib.parse
from typing import Dict, Any, Optional, Tuple, List
import requests
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup

from .config import (
    BASE_URL,
    HOME_PATH,
    SEARCH_AJAX_PATH,
    DEFAULT_HEADERS,
    DEFAULT_TIMEOUT,
    DEFAULT_MAX_RETRIES,
)
from .captcha import get_shared_solver, CaptchaSolver
from .parser import parse_case_html
from .models import ECourtCaseResult, CaseDetails, CaseStatus, Party, Act, ProcessRecord, IAStatus, HearingHistory


class ECourtScraper:
    """
    High-performance automated scraper for eCourts India Services.
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        solver: Optional[CaptchaSolver] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        
        # HTTP Connection Pooling with Keep-Alive
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=2)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update(DEFAULT_HEADERS)

        # Use pre-warmed singleton OCR solver (~30ms)
        self.solver = solver or get_shared_solver()

        # State tracked across requests for this session
        self.hidden_inputs: Dict[str, Dict[str, str]] = {}
        self.app_token: str = ""
        self.custom_headers: Dict[str, str] = {}
        self.captcha_src: str = ""
        self.components_js_url: str = ""

    def get_dynamic_headers(self, raw_html: str = "") -> Dict[str, str]:
        """
        Retrieves security delimiter headers for the current session.
        Headers are bound to the current session cookies.
        """
        if self.custom_headers:
            return self.custom_headers

        # Find components.js script tag
        comp_match = re.search(r'<script[^>]*src=["\']([^"\']*components\.js[^"\']*)["\']', raw_html)
        if comp_match:
            src = comp_match.group(1)
            self.components_js_url = urllib.parse.urljoin(self.base_url, src)
        else:
            self.components_js_url = f"{self.base_url}/ecourtindia_v6/js/components.js"

        try:
            resp = self.session.get(self.components_js_url, timeout=self.timeout)
            js_text = resp.text

            delimeter_match = re.search(r'delimeter\s*=\s*["\']([^"\']+)["\']', js_text)
            delimeter = delimeter_match.group(1) if delimeter_match else "bzmvnbgf456"

            headers_block = re.search(r'headers\s*:\s*\{([^}]+)\}', js_text)
            custom_headers: Dict[str, str] = {"delimeter": delimeter}

            if headers_block:
                pairs = re.findall(
                    r'["\']([^"\']+)["\']\s*:\s*([^,\r\n}]+)',
                    headers_block.group(1),
                )
                for k, v in pairs:
                    v = v.strip()
                    custom_headers[k] = delimeter if "delimeter" in v else v.strip('"\'')

            self.custom_headers = custom_headers
            return custom_headers

        except Exception:
            fallback = {"delimeter": "bzmvnbgf456", "Suiyrty45": "bzmvnbgf456"}
            self.custom_headers = fallback
            return fallback

    def initialize_session(self, initial_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Initializes portal session with ultra-fast regex extraction (<1ms).
        """
        self.custom_headers = {}
        target_url = initial_url or f"{self.base_url}{HOME_PATH}"
        resp = self.session.get(target_url, timeout=self.timeout)
        if resp.status_code != 200:
            raise ConnectionError(f"Failed to access eCourts portal: HTTP {resp.status_code}")

        html = resp.text

        # 1. Fast regex extraction of app_token (<0.1ms vs 50ms BeautifulSoup)
        token_match = re.search(r'id=["\']app_token["\'][^>]*value=["\']([a-f0-9]+)["\']', html)
        if not token_match:
            token_match = re.search(r'name=["\']app_token["\'][^>]*value=["\']([a-f0-9]+)["\']', html)
        self.app_token = token_match.group(1) if token_match else ""

        # 2. Fast regex extraction of captcha image src
        captcha_match = re.search(r'id=["\']captcha_image["\'][^>]*src=["\']([^"\']+)["\']', html)
        if not captcha_match:
            captcha_match = re.search(r'src=["\']([^"\']*securimage_show\.php[^"\']*)["\']', html)
        
        if not captcha_match:
            raise ValueError("Captcha image element not found in eCourts DOM.")

        raw_src = captcha_match.group(1)
        self.captcha_src = urllib.parse.urljoin(f"{self.base_url}/ecourtindia_v6/", raw_src)

        # 3. Get session-specific security headers
        self.get_dynamic_headers(raw_html=html)

        return {
            "url": resp.url,
            "status_code": resp.status_code,
            "app_token": self.app_token,
            "custom_headers": self.custom_headers,
            "captcha_url": self.captcha_src,
        }

    def fetch_captcha_bytes(self, captcha_url: str) -> bytes:
        """Downloads captcha image bytes with cache-busting headers."""
        headers = self.session.headers.copy()
        headers["Referer"] = f"{self.base_url}{HOME_PATH}&app_token={self.app_token}"
        headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        headers["Pragma"] = "no-cache"
        resp = self.session.get(captcha_url, headers=headers, timeout=self.timeout)
        if resp.status_code != 200:
            raise ConnectionError(f"Failed to download captcha image: HTTP {resp.status_code}")
        return resp.content

    def update_captcha_from_html(self, div_captcha_html: str) -> Optional[str]:
        """Fast regex extraction of refreshed captcha URL."""
        match = re.search(r'src=["\']([^"\']*securimage_show\.php[^"\']*)["\']', div_captcha_html)
        if match:
            self.captcha_src = urllib.parse.urljoin(f"{self.base_url}/ecourtindia_v6/", match.group(1))
            return self.captcha_src
        return None

    def refresh_captcha(self) -> str:
        """
        Actively forces the eCourts server to generate a new captcha code and token.
        Uses eCourts casestatus/getCaptcha API with fallback to cache-buster parameter.
        """
        import random
        try:
            ajax_headers = {
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": self.base_url,
                "Referer": f"{self.base_url}{HOME_PATH}&app_token={self.app_token}",
            }
            ajax_headers.update(self.custom_headers)
            resp = self.session.post(
                f"{self.base_url}/ecourtindia_v6/?p=casestatus/getCaptcha",
                headers=ajax_headers,
                data={"ajax_req": "true", "app_token": self.app_token},
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                d = resp.json()
                if d.get("app_token"):
                    self.app_token = d["app_token"]
                if d.get("div_captcha"):
                    new_src = self.update_captcha_from_html(d["div_captcha"])
                    if new_src:
                        return new_src
        except Exception:
            pass

        rnd = f"{random.random():.16f}"
        self.captcha_src = f"{self.base_url}/ecourtindia_v6/vendor/securimage/securimage_show.php?{rnd}"
        return self.captcha_src

    def search_case(
        self,
        cino: str,
        max_retries: int = DEFAULT_MAX_RETRIES,
        initial_url: Optional[str] = None,
        verbose: bool = True,
        progress_callback: Optional[Any] = None,
    ) -> ECourtCaseResult:
        """
        Executes ultra-fast case search:
          1. Connects to portal, extracts app_token and headers via fast regex.
          2. Decodes captcha with pre-warmed neural model in ~30ms.
          3. Submits query via persistent pooled HTTP connection.
          4. Returns structured case details.
        """
        cino = cino.strip().upper()
        if len(cino) != 16 or not cino.isalnum():
            raise ValueError(f"Invalid CNR Number: '{cino}'. Must be exactly 16 alphanumeric characters.")

        if progress_callback:
            progress_callback("session_init", "Connecting to eCourts India Gateway...")
        elif verbose:
            print(f"[eCourts] Initializing session on {self.base_url}...")

        self.initialize_session(initial_url)

        if progress_callback:
            progress_callback("tokens_extracted", "Session established with active security tokens.")
        elif verbose:
            print(f"[eCourts] Initial DOM app_token: {self.app_token}")
            print(f"[eCourts] Security headers: {self.custom_headers}")

        search_endpoint = f"{self.base_url}{SEARCH_AJAX_PATH}"

        last_bytes_hash: Optional[int] = None

        for attempt in range(1, max_retries + 1):
            if progress_callback:
                progress_callback("captcha_fetch", f"Decoding captcha (Attempt {attempt})...")
            elif verbose:
                print(f"[eCourts] Attempt {attempt}/{max_retries}: Fetching captcha...")

            # 1. Download captcha over pooled connection
            captcha_bytes = self.fetch_captcha_bytes(self.captcha_src)
            curr_hash = hash(captcha_bytes)

            # Prevent duplicate/stale captcha submission
            if curr_hash == last_bytes_hash:
                if verbose:
                    print(f"[eCourts] Duplicate captcha detected on attempt {attempt}. Forcing server refresh...")
                self.refresh_captcha()
                captcha_bytes = self.fetch_captcha_bytes(self.captcha_src)
                curr_hash = hash(captcha_bytes)

            last_bytes_hash = curr_hash

            # 2. Fast neural OCR decode (~30ms)
            captcha_code = self.solver.solve(captcha_bytes)

            if progress_callback:
                progress_callback("captcha_solved", f"Captcha solved: '{captcha_code}'. Querying database...")
            elif verbose:
                print(f"[eCourts] Decoded captcha: '{captcha_code}'")

            # 3. Headers and payload
            ajax_headers = {
                "User-Agent": self.session.headers["User-Agent"],
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "en-US,en;q=0.9",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": self.base_url,
                "Referer": f"{self.base_url}{HOME_PATH}&app_token={self.app_token}",
            }
            ajax_headers.update(self.custom_headers)

            post_data = {
                "cino": cino,
                "fcaptcha_code": captcha_code,
                "ajax_req": "true",
                "app_token": self.app_token,
            }

            resp = self.session.post(
                search_endpoint,
                headers=ajax_headers,
                data=post_data,
                timeout=self.timeout,
            )

            try:
                data = resp.json()
            except Exception as exc:
                raise ValueError(f"Invalid response from server: {resp.text[:300]}") from exc

            # Refresh token
            if data.get("app_token"):
                self.app_token = data["app_token"]

            status = data.get("status")

            # Success
            if status == 1 and "casetype_list" in data:
                raw_html = data["casetype_list"]
                if "Record not found" in raw_html or "does not exist" in raw_html.lower():
                    raise LookupError(f"Case with CNR '{cino}' does not exist.")

                if progress_callback:
                    progress_callback("parsing_results", "Case found! Compiling report...")
                elif verbose:
                    print(f"[eCourts] Case found! Parsed HTML response ({len(raw_html)} chars).")

                parsed_dict = parse_case_html(raw_html)

                return ECourtCaseResult(
                    cnr=cino,
                    court_name=parsed_dict["court_name"],
                    case_details=CaseDetails(**parsed_dict["case_details"]),
                    case_status=CaseStatus(**parsed_dict["case_status"]),
                    petitioners=[Party(**p) for p in parsed_dict["petitioners"]],
                    respondents=[Party(**r) for r in parsed_dict["respondents"]],
                    acts=[Act(**a) for a in parsed_dict["acts"]],
                    processes=[ProcessRecord(**pr) for pr in parsed_dict["processes"]],
                    ia_status=[IAStatus(**ia) for ia in parsed_dict["ia_status"]],
                    case_history=[HearingHistory(**h) for h in parsed_dict["case_history"]],
                    raw_html=raw_html,
                    metadata={
                        "attempts": attempt,
                        "last_app_token": self.app_token,
                    },
                )

            # Not found check
            errormsg = data.get("errormsg", "")
            if "does not exist" in errormsg or "Record not found" in errormsg:
                raise LookupError(f"eCourts returned: Case with CNR '{cino}' does not exist.")

            # Invalid session or token rejection recovery
            if "Invalid Request" in errormsg or "Oops" in errormsg:
                if verbose:
                    print(f"[eCourts] Security token expired or rejected. Re-initializing session...")
                self.initialize_session()
                continue

            # Immediate refresh on captcha mismatch
            if data.get("div_captcha"):
                self.update_captcha_from_html(data["div_captcha"])
            else:
                self.refresh_captcha()

            time.sleep(0.05)  # ultra-low latency pause between retries

        raise TimeoutError(f"Failed to solve captcha after {max_retries} attempts.")
