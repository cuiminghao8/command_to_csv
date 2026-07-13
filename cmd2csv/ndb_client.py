from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class NdbDevice:
    hostname: str
    mgmt_ip: str
    vendor: str
    os: str
    model: Optional[str] = None
    site: Optional[str] = None
    role: Optional[str] = None
    port: Optional[int] = None


class NdbClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        timeout: float = 10.0,
        verify: bool | str = True,
        max_retries: int = 3,
        backoff: float = 1.5,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.verify = verify
        self.max_retries = max_retries
        self.backoff = backoff

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }

    def _get_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.get(
                    url,
                    headers=self._headers(),
                    params=params,
                    timeout=self.timeout,
                    verify=self.verify,
                )
                resp.raise_for_status()
                return resp.json()
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exc = exc
                if attempt == self.max_retries:
                    break
                delay = self.backoff ** attempt
                logger.warning(
                    "NDB GET %s failed (attempt %d/%d): %s; retrying in %.1fs",
                    url, attempt, self.max_retries, exc, delay,
                )
                time.sleep(delay)
            except requests.HTTPError as exc:
                raise RuntimeError(f"NDB returned HTTP error for {url}: {exc}") from exc
        raise RuntimeError(f"NDB request failed after {self.max_retries} retries: {last_exc}")

    def fetch_devices_by_names(self, hostnames: Iterable[str]) -> List[NdbDevice]:
        """Fetch device inventory from NDB and filter to ``hostnames``.

        The exact response schema is NDB-specific; adapt ``_parse_device`` if yours
        differs. Hostnames that are not found are logged as warnings instead of
        silently dropped.
        """
        wanted = list(hostnames)
        wanted_set = set(wanted)
        if not wanted_set:
            return []

        params = {"hostname": ",".join(wanted)}
        data = self._get_json("/devices", params=params)
        raw = data.get("devices")
        if not isinstance(raw, list):
            raise RuntimeError(
                f"Unexpected NDB response shape; expected 'devices' list, got {type(raw).__name__}"
            )

        devices: List[NdbDevice] = []
        seen: set[str] = set()
        for d in raw:
            try:
                dev = self._parse_device(d)
            except KeyError as exc:
                logger.warning("Skipping NDB device with missing field %s: %r", exc, d)
                continue
            if dev.hostname in wanted_set:
                devices.append(dev)
                seen.add(dev.hostname)

        missing = sorted(wanted_set - seen)
        if missing:
            logger.warning("NDB did not return devices for: %s", ", ".join(missing))
        return devices

    @staticmethod
    def _parse_device(d: Dict[str, Any]) -> NdbDevice:
        return NdbDevice(
            hostname=d["hostname"],
            mgmt_ip=d["mgmt_ip"],
            vendor=d["vendor"],
            os=d["os"],
            model=d.get("model"),
            site=d.get("site"),
            role=d.get("role"),
            port=d.get("port"),
        )
