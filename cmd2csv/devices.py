from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .ndb_client import NdbDevice

logger = logging.getLogger(__name__)


@dataclass
class ClassifiedDevice:
    hostname: str
    mgmt_ip: str
    vendor: str
    os: str
    model: Optional[str]
    site: Optional[str]
    role: Optional[str]
    pyats_os: str
    ntc_platform: str
    port: Optional[int] = None


OS_MAP: Dict[Tuple[str, str], Dict[str, str]] = {
    ("cisco", "iosxe"): {"pyats_os": "iosxe", "ntc_platform": "cisco_ios"},
    ("cisco", "ios"): {"pyats_os": "ios", "ntc_platform": "cisco_ios"},
    ("cisco", "nxos"): {"pyats_os": "nxos", "ntc_platform": "cisco_nxos"},
    ("cisco", "iosxr"): {"pyats_os": "iosxr", "ntc_platform": "cisco_xr"},
    ("cisco", "asa"): {"pyats_os": "asa", "ntc_platform": "cisco_asa"},
    ("arista", "eos"): {"pyats_os": "eos", "ntc_platform": "arista_eos"},
    ("juniper", "junos"): {"pyats_os": "junos", "ntc_platform": "juniper_junos"},
    ("hp", "comware"): {"pyats_os": "comware", "ntc_platform": "hp_comware"},
    ("huawei", "vrp"): {"pyats_os": "vrp", "ntc_platform": "huawei_vrp"},
}

ROLE_TO_PYATS_TYPE = {
    "switch": "switch",
    "router": "router",
    "firewall": "firewall",
    "load-balancer": "load-balancer",
    "loadbalancer": "load-balancer",
    "access-point": "access-point",
    "wlc": "wlc",
}


def register_os_mapping(vendor: str, os_name: str, pyats_os: str, ntc_platform: str) -> None:
    """Extend ``OS_MAP`` at runtime (e.g., from a config file)."""
    OS_MAP[(vendor.lower(), os_name.lower())] = {
        "pyats_os": pyats_os,
        "ntc_platform": ntc_platform,
    }


def classify_device(d: NdbDevice) -> ClassifiedDevice:
    key = (d.vendor.lower(), d.os.lower())
    info = OS_MAP.get(key)
    if not info:
        raise ValueError(
            f"Unknown device type vendor={d.vendor!r} os={d.os!r}; "
            f"register it via register_os_mapping() or update OS_MAP."
        )
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
        port=d.port,
    )


def _pyats_type(role: Optional[str]) -> str:
    if not role:
        return "router"
    return ROLE_TO_PYATS_TYPE.get(role.lower().strip(), "router")


def build_testbed_from_devices(
    devices: List[ClassifiedDevice],
    username: str,
    password: str,
    *,
    enable_password: Optional[str] = None,
    default_port: int = 22,
):
    """Build a pyATS testbed in memory from classified devices."""
    from genie.testbed import load as load_testbed

    if not devices:
        raise ValueError("No devices to build testbed from")

    credentials: Dict[str, Any] = {
        "default": {"username": username, "password": password},
    }
    if enable_password:
        credentials["enable"] = {"password": enable_password}

    tb: Dict[str, Any] = {
        "testbed": {"name": "from_ndb", "credentials": credentials},
        "devices": {},
    }

    for d in devices:
        cli: Dict[str, Any] = {
            "protocol": "ssh",
            "ip": d.mgmt_ip,
            "port": d.port or default_port,
        }
        tb["devices"][d.hostname] = {
            "os": d.pyats_os,
            "type": _pyats_type(d.role),
            "connections": {
                "defaults": {"class": "unicon.Unicon"},
                "cli": cli,
            },
            "custom": {
                "site": d.site or "",
                "role": d.role or "",
                "vendor": d.vendor,
                "model": d.model or "",
                "ntc_platform": d.ntc_platform,
            },
        }

    logger.debug("Built testbed with %d devices", len(devices))
    return load_testbed(tb)
