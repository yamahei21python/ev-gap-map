"""HTTP client with retry and rate limit handling"""

import time
import random
import logging
from typing import Optional
from dataclasses import dataclass, field

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import HEADERS, REQUEST_TIMEOUT, MAX_RETRIES, REQUEST_DELAY


logger = logging.getLogger(__name__)


@dataclass
class HTTPClient:
    """HTTP client with built-in retry and rate limiting"""

    delay: float = REQUEST_DELAY
    timeout: int = REQUEST_TIMEOUT
    max_retries: int = MAX_RETRIES
    session: requests.Session = field(default_factory=requests.Session, init=False)

    def __post_init__(self):
        """Setup session with retry strategy"""
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update(HEADERS)

    def get(
        self,
        url: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        retry_count: int = 0,
    ) -> Optional[str]:
        """
        GET request with retry and rate limit handling

        Args:
            url: Target URL
            params: Query parameters
            headers: Additional headers
            retry_count: Current retry attempt

        Returns:
            Response text or None on failure
        """
        # Rate limiting delay
        jitter = random.uniform(0.5, 1.5)
        time.sleep(self.delay * jitter)

        request_headers = dict(HEADERS)
        if headers:
            request_headers.update(headers)

        try:
            response = self.session.get(
                url,
                params=params,
                headers=request_headers,
                timeout=self.timeout,
            )

            # Check for rate limit (202 or short response)
            if response.status_code == 202 or len(response.text) < 100:
                backoff = min(60, self.delay * (2 ** (retry_count + 1)))
                logger.warning(
                    f"Rate limited (status={response.status_code}, len={len(response.text)}). "
                    f"Backing off {backoff:.0f}s (attempt {retry_count + 1}/{self.max_retries})"
                )
                if retry_count < self.max_retries:
                    time.sleep(backoff)
                    return self.get(url, params, headers, retry_count + 1)
                return None

            response.raise_for_status()
            return response.text

        except requests.RequestException as e:
            logger.warning(
                f"Request failed (attempt {retry_count + 1}/{self.max_retries}): {url} - {e}"
            )
            if retry_count < self.max_retries:
                backoff = min(60, self.delay * (2 ** (retry_count + 1)))
                time.sleep(backoff)
                return self.get(url, params, headers, retry_count + 1)
            else:
                logger.error(f"All retries failed: {url}")
                return None

    def post(
        self,
        url: str,
        data: Optional[dict] = None,
        json: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> Optional[dict]:
        """
        POST request

        Returns:
            JSON response or None on failure
        """
        request_headers = dict(HEADERS)
        if headers:
            request_headers.update(headers)

        try:
            response = self.session.post(
                url,
                data=data,
                json=json,
                headers=request_headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"POST failed: {url} - {e}")
            return None

    def close(self):
        """Close session"""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
