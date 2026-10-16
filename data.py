"""Server data: the 6 mock servers (demo fleet) plus real files read with the backend's parser.

Replace with a database / API in a real deployment.
"""
import copy
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from ssh_parser import parse_ssh_config   # backend: reads an sshd_config file -> dict of settings

ROOT = Path(__file__).parent

BASE = {
    "firewall_enabled": True, "ssh_password_login": False, "ssh_root_login": False,
    "open_ports": [22, 443], "password_min_length": 12, "auto_updates": True,
    "log_level": "info", "telnet_enabled": False,
}


def cfg(changes=None, remove=()):
    """Copy of BASE with some values changed and some keys removed."""
    c = copy.deepcopy(BASE)
    c.update(changes or {})
    for k in remove:
        c.pop(k, None)
    return c


def _ago(minutes):
    return datetime.now() - timedelta(minutes=minutes)


def get_mock_servers() -> list[dict]:
    return [
        dict(id="web-prod-01", name="web-prod-01", environment="prod", os="Ubuntu 22.04 LTS",
             location="Mumbai (ap-south-1)", status="online", last_scan=_ago(12),
             baseline=cfg({}, ["telnet_enabled"]),
             current=cfg({"firewall_enabled": False, "ssh_password_login": True,
                          "open_ports": [22, 443, 3306], "telnet_enabled": True})),
        dict(id="db-prod-01", name="db-prod-01", environment="prod", os="Ubuntu 22.04 LTS",
             location="Mumbai (ap-south-1)", status="online", last_scan=_ago(12),
             baseline=cfg({"open_ports": [22, 5432]}),
             current=cfg({"open_ports": [22, 5432], "password_min_length": 8,
                          "auto_updates": False, "ssh_root_login": True})),
        dict(id="api-staging-01", name="api-staging-01", environment="staging", os="Debian 12",
             location="Singapore (ap-southeast-1)", status="online", last_scan=_ago(35),
             baseline=cfg(), current=cfg({"log_level": "debug", "open_ports": [22, 443, 8080]})),
        dict(id="app-dev-01", name="app-dev-01", environment="dev", os="Ubuntu 20.04 LTS",
             location="Pune (on-prem)", status="online", last_scan=_ago(35),
             baseline=cfg({"log_level": "debug"}), current=cfg({"log_level": "debug"})),
        dict(id="cache-prod-01", name="cache-prod-01", environment="prod", os="RHEL 9",
             location="Frankfurt (eu-central-1)", status="offline", last_scan=_ago(190),
             baseline=cfg({"open_ports": [22, 6379]}),
             current=cfg({"open_ports": [22, 6379]}, ["auto_updates", "log_level"])),
        dict(id="batch-dev-02", name="batch-dev-02", environment="dev", os="Amazon Linux 2023",
             location="N. Virginia (us-east-1)", status="unknown", last_scan=_ago(1500),
             baseline=cfg({}, ["telnet_enabled"]),
             current=cfg({"password_min_length": 6, "telnet_enabled": True})),
    ]


def get_mock_history() -> list[dict]:
    now = datetime.now()
    rows = [(5, 6, 2), (4, 8, 3), (3, 11, 5), (2, 15, 8), (1, 14, 7)]
    return [dict(id=f"scan-{d}", time=now - timedelta(days=d), servers=6, drifts=n, high=h)
            for d, n, h in rows]


# ---------------------------------------------------------------- real files (backend sample data)
def _server(sid: str, name: str, location: str, baseline: dict, current: dict) -> dict:
    return dict(id=sid, name=name, environment="dev", os="Not specified", location=location,
                status="online", last_scan=datetime.now(), baseline=baseline, current=current)


def get_backend_servers() -> list[dict]:
    """Servers built from the backend's own files. A missing or broken file is skipped, not fatal."""
    out = []
    try:
        base = json.loads((ROOT / "baseline.json").read_text(encoding="utf-8"))
        cur = json.loads((ROOT / "current.json").read_text(encoding="utf-8"))
        out.append(_server("sample-json", "sample-json-config", "baseline.json / current.json", base, cur))
    except Exception:
        pass
    try:
        base, _ = parse_ssh_config(str(ROOT / "baseline_sshd_config"))
        cur, _ = parse_ssh_config(str(ROOT / "current_sshd_config"))
        out.append(_server("sample-ssh", "sample-ssh-config", "baseline_sshd_config / current_sshd_config",
                           base, cur))
    except Exception:
        pass
    return out


def parse_uploaded(raw: bytes) -> dict:
    """An uploaded file -> flat dict of settings. JSON objects as-is; anything else goes through
    the backend's sshd_config parser. Raises ValueError with a message the user can act on."""
    text = raw.decode("utf-8-sig", errors="replace")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        if text.lstrip().startswith(("{", "[")):
            raise ValueError("One of the files looks like JSON but is not valid. "
                             "Check for missing commas or quotes and try again.")
        data = None
    if data is not None:
        if not isinstance(data, dict):
            raise ValueError('JSON files must contain an object of settings, e.g. {"firewall_enabled": true}.')
        return data
    with tempfile.NamedTemporaryFile("w", suffix=".conf", delete=False, encoding="utf-8") as tmp:
        tmp.write(text)
        path = tmp.name
    try:
        settings, _warnings = parse_ssh_config(path)
    finally:
        os.remove(path)
    if not settings:
        raise ValueError("No settings found. Upload a JSON object or an sshd_config style file.")
    return settings
