"""Base HTTP Client with robust retry logic, pagination handling, and security safeguards."""
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlsplit, parse_qsl, urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class APIError(RuntimeError):
    """HTTP failure without response body, credentials or query parameters."""
    def __init__(self,path,status_code):
        self.status_code=status_code
        super().__init__(f'GET {path} failed with HTTP {status_code}')


class BaseClient:
    """Robust, authenticated HTTP client for REST APIs (CVAT, GitHub)."""

    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        auth_prefix: str = "Bearer",
        org: Optional[str] = None,
        timeout: tuple = (10, 60),
        max_pages: int = 10000,
    ):
        self.base_url = base_url.rstrip("/") + "/"
        base=urlsplit(self.base_url)
        if base.scheme not in ('http','https') or not base.hostname or base.username or base.password or base.query or base.fragment:
            raise ValueError('API base URL must be HTTP(S), without embedded credentials, query or fragment')
        if type(max_pages) is not int or max_pages<1: raise ValueError('max_pages must be positive')
        self.max_pages=max_pages
        self.org = org
        self.timeout = timeout
        self.session = requests.Session()

        if token:
            self.session.headers.update({"Authorization": f"{auth_prefix} {token}".strip()})

        self.session.headers.setdefault("Accept", "application/json")
        if self.org:
            self.session.headers["X-Organization"] = self.org

        # Configure connection pooling & exponential backoff retry
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _safe_url(self,path):
        if not isinstance(path,str) or not path.strip(): raise ValueError('API path must be a nonempty string')
        url = urljoin(self.base_url, path)
        split_url = urlsplit(url)
        split_base = urlsplit(self.base_url)
        if (split_url.scheme != split_base.scheme or split_url.netloc != split_base.netloc
            or split_url.username or split_url.password or split_url.fragment):
            raise ValueError('Unsafe API URL: pagination and requests must retain the configured origin')
        return url

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        """Execute GET without redirects, origin changes or HTTPS downgrade."""
        url=self._safe_url(path)

        req_params = dict(params or {})
        if self.org is not None and "org" not in req_params and 'org' not in dict(parse_qsl(urlsplit(url).query,keep_blank_values=True)):
            req_params["org"] = self.org

        response = self.session.get(
            url,
            params=req_params,
            timeout=self.timeout,
            allow_redirects=False,
        )
        if response.status_code != 200:
            response.close()
            raise APIError(urlsplit(url).path,response.status_code)
        return response

    def close(self):
        self.session.close()

    def listing(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        is_github: bool = False,
    ) -> List[Dict[str, Any]]:
        """Traverse paginated API responses safely without duplicate loops."""
        rows: List[Dict[str, Any]] = []
        seen = set()

        curr_path: Optional[str] = path
        curr_params = params

        while curr_path:
            if len(seen)>=self.max_pages: raise ValueError('API pagination exceeded max_pages')
            url=self._safe_url(curr_path)
            prepared=requests.Request('GET',url,params=curr_params).prepare().url
            parts=urlsplit(prepared)
            identity=(parts.scheme,parts.netloc,parts.path,urlencode(sorted(parse_qsl(parts.query,keep_blank_values=True))))
            if identity in seen:
                raise ValueError("Infinite pagination loop detected")
            seen.add(identity)

            response = self.get(curr_path, curr_params)
            payload = response.json()

            if is_github:
                if not isinstance(payload, list):
                    raise ValueError("Expected GitHub API list response")
                batch=payload
                curr_path = response.links.get("next", {}).get("url")
            else:
                if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
                    raise ValueError("Expected CVAT paginated 'results' dictionary")
                batch=payload['results']
                curr_path = payload.get("next")

            if any(not isinstance(row,dict) for row in batch): raise ValueError('API list items must be objects')
            rows.extend(batch)
            if curr_path is not None:
                if not isinstance(curr_path,str) or not curr_path.strip(): raise ValueError('Invalid pagination next URL')
                # CVAT usually returns absolute URLs; accept query-only and
                # resource-relative URLs as well as the legacy api/... form.
                reference=self.base_url if curr_path.startswith('api/') else prepared
                curr_path=self._safe_url(urljoin(reference,curr_path))

            curr_params = None  # Next URL already includes required parameters

        return rows
