from __future__ import annotations
from typing import Dict, Any, List
from dataclasses import dataclass
from genie.testbed import load as load_testbed

from .ndb_client import NdbDevice


@dataclass
class ClassifiedDevice:
    hostname: str
    mgmt_ip: str
    vendor: str
    os: str
    model: str | None
    site: str | None
    role: str | None
    pyats_os: str
    ntc_platform: str


OS_MAP: Dict[tuple[str, str], Dict[str, str]] = {
    ("cisco", "iosxe"): {
        "pyats_os": "iosxe",
        "ntc_platform": "cisco_ios",
    },
    ("cisco", "ios"): {
        "pyats_os": "ios",
        "ntc_platform": "cisco_ios",
    },
    ("cisco", "nxos"): {
        "pyats_os": "nxos",
        "ntc_platform": "cisco_nxos",
    },
    ("arista", "eos"): {
        "pyats_os": "eos",
        "ntc_platform": "arista_eos",
    },
    # 按需补充
}


def classify_device(d: NdbDevice) -> ClassifiedDevice:
    key = (d.vendor.lower(), d.os.lower())
    info = OS_MAP.get(key)
    if not info:
        raise ValueError(f"Unknown device type: vendor={d.vendor}, os={d.os}")

    return ClassifiedDevice(
        hostname=d.hostname,
        mgmt_ip=d.mgmt_ip,
        vendor=d.vendor,
        os=d.os,
        model=d.model,
        site=d.site,
        role=d.role,
        pyats_os=info["pyats_os"],
        ntc_platform=info["ntc_platform"],
    )


def build_testbed_from_devices(devices: List[ClassifiedDevice], username: str, password: str):
    """
    动态构造 pyATS testbed（内存）
    """
    tb: Dict[str, Any] = {
        "testbed": {
            "name": "from_ndb",
            "credentials": {
                "default": {
                    "username": username,
                    "password": password,
                }
            },
        },
        "devices": {},
    }

    for d in devices:
        tb["devices"][d.hostname] = {
            "os": d.pyats_os,
            "type": "router",
            "connections": {
                "defaults": {
                    "class": "unicon.Unicon",
                },
                "cli": {
                    "protocol": "ssh",
                    "ip": d.mgmt_ip,
                },
            },
            "custom": {
                "site": d.site or "",
                "role": d.role or "",
                "vendor": d.vendor,
                "model": d.model or "",
                "ntc_platform": d.ntc_platform,
            },
        }

    return load_testbed(tb)
