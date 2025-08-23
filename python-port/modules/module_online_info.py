from __future__ import annotations
import threading
import json
from typing import Any, Dict

try:
    import requests
except Exception:  # pragma: no cover - optional dependency
    requests = None  # type: ignore

from .module_base import ModuleBase
from uks import UKS


class ModuleOnlineInfo(ModuleBase):
    """Query Wikipedia for information about words and add summaries to UKS."""

    def __init__(self, interval: float = 0.0):
        super().__init__()
        self.interval = interval
        self._queue: list[str] = []
        self._timer: threading.Timer | None = None
        self.uks: UKS | None = None

    def initialize(self, uks: UKS) -> None:  # type: ignore[override]
        self.uks = uks
        if self.interval:
            self._schedule()

    # worker scheduling
    def _schedule(self) -> None:
        if self.interval and self._timer is None:
            self._timer = threading.Timer(self.interval, self.fire)
            self._timer.daemon = True
            self._timer.start()

    def reset(self) -> None:
        if self._timer:
            self._timer.cancel()
            self._timer = None
        self._queue.clear()

    def add_query(self, term: str) -> None:
        self._queue.append(term)
        if not self.interval:
            self.fire()

    def fire(self) -> None:  # type: ignore[override]
        if not self._queue or self.uks is None:
            self._timer = None
            return
        term = self._queue.pop(0)
        summary = self._get_summary(term)
        if summary:
            self.uks.add_statement(term, "hasSummary", summary)
        self._timer = None
        if self.interval and self._queue:
            self._schedule()

    def _get_summary(self, term: str) -> str:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{term}"
        if requests is None:  # fallback using urllib
            from urllib.request import urlopen

            try:
                with urlopen(url, timeout=10) as resp:
                    data = json.load(resp)
                    return data.get("extract", "")
            except Exception:
                return ""
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data: Dict[str, Any] = resp.json()
            return data.get("extract", "")
        return ""
