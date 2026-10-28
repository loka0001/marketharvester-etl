import time
import random
import logging
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger("marketharvester.client")

DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


class HarvestError(Exception):
    """Base exception for harvester client errors."""
    pass


class HarvestRateLimitError(HarvestError):
    """Raised when server returns 429 Too Many Requests."""
    pass


class HarvestHTTPError(HarvestError):
    """Raised on non-transient HTTP errors (e.g. 404, 403)."""
    def __init__(self, status_code: int, message: str):
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code


class ResilientClient:
    """
    Robust HTTP client featuring automated retry with exponential backoff and jitter,
    polite rate limiting, User-Agent rotation, and custom error handling.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_backoff: float = 1.0,
        rate_limit_delay: float = 0.5,
        timeout: float = 10.0,
        session: Optional[requests.Session] = None,
    ):
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout
        self.session = session or requests.Session()
        self.last_request_time = 0.0

    def _apply_rate_limit(self):
        """Enforces minimum pause between sequential outbound requests."""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed + random.uniform(0.05, 0.15)
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def get_html(self, url: str, headers: Optional[Dict[str, str]] = None) -> str:
        """
        Fetches an HTML document with exponential backoff retries.
        """
        request_headers = {
            "User-Agent": random.choice(DEFAULT_USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if headers:
            request_headers.update(headers)

        attempt = 0
        while attempt <= self.max_retries:
            attempt += 1
            self._apply_rate_limit()

            try:
                response = self.session.get(url, headers=request_headers, timeout=self.timeout)
                
                # Check for rate limiting
                if response.status_code == 429:
                    if attempt > self.max_retries:
                        raise HarvestRateLimitError(f"Rate limited (429) at {url} after {attempt} attempts")
                    retry_after = float(response.headers.get("Retry-After", self.base_backoff * (2 ** (attempt - 1))))
                    time.sleep(retry_after + random.uniform(0.2, 0.8))
                    continue

                # Check for server errors (5xx)
                if 500 <= response.status_code < 600:
                    if attempt > self.max_retries:
                        raise HarvestHTTPError(response.status_code, f"Server error on {url}")
                    backoff = self.base_backoff * (2 ** (attempt - 1)) + random.uniform(0.1, 0.5)
                    time.sleep(backoff)
                    continue

                # Check for client error
                if 400 <= response.status_code < 500:
                    raise HarvestHTTPError(response.status_code, f"Client error on {url}")

                response.encoding = response.apparent_encoding or "utf-8"
                return response.text

            except requests.RequestException as exc:
                if attempt > self.max_retries:
                    raise HarvestError(f"Connection failure fetching {url}: {exc}") from exc
                backoff = self.base_backoff * (2 ** (attempt - 1)) + random.uniform(0.1, 0.5)
                time.sleep(backoff)

        raise HarvestError(f"Failed to fetch {url} after {self.max_retries} attempts.")
