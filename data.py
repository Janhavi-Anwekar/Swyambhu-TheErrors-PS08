"""Mock data. Replace with a database / API / uploaded files in a real deployment."""
import copy
from datetime import datetime, timedelta

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
