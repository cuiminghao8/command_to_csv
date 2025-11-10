from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict
import requests


@dataclass
class NdbDevice:
    hostname: str
    mgmt_ip: str
    vendor: str
    os: str
    model: str | None = None
    site: str | None = None
    role: str | None = None


class NdbClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }

    def fetch_devices_by_names(self, hostnames: list[str]) -> list[NdbDevice]:
        """
        根据实际 NDB API 修改。
        目标是返回 NdbDevice 列表。
        """
        # 示例：假设 /devices?hostname=R1,R2
        params = {"hostname": ",".join(hostnames)}
        resp = requests.get(
            f"{self.base_url}/devices",
            headers=self._headers(),
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        devices: list[NdbDevice] = []
        for d in data["devices"]:
            hostname = d["hostname"]
            if hostname not in hostnames:
                continue
            devices.append(
                NdbDevice(
                    hostname=hostname,
                    mgmt_ip=d["mgmt_ip"],
                    vendor=d["vendor"],
                    os=d["os"],          # iosxe / nxos / eos / ...
                    model=d.get("model"),
                    site=d.get("site"),
                    role=d.get("role"),
                )
            )
        return devices
