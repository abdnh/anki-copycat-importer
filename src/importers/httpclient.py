from typing import Any

import requests

from ..consts import USER_AGENT
from .errors import CopycatImporterError


class HttpClient:
    timeout = 60

    def __init__(self) -> None:
        super().__init__()
        self.session = requests.Session()

    def request(self, method: str, url: str, **kwrags: Any) -> requests.Response:
        headers = {"User-Agent": USER_AGENT}
        headers.update(kwrags.pop("headers", {}))
        try:
            res = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                headers=headers,
                **kwrags,
            )
            res.raise_for_status()
            return res
        except requests.HTTPError as exc:
            raise CopycatImporterError(f"Request to {url} failed: {str(exc)}") from exc
