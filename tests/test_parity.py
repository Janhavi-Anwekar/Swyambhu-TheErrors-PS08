"""Checks that the dashboard shows exactly what the backend finds. Run from the repo root: python -m pytest"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import analyze                        # noqa: E402  (dashboard logic)
from data import get_servers                    # noqa: E402
from ssh_drift import compare_ssh_configs       # noqa: E402  (backend)

ROOT = Path(__file__).resolve().parent.parent


def test_dashboard_has_no_demo_servers_by_default():
    assert all(s["id"].startswith("sample-") for s in get_servers())


def test_ssh_dashboard_matches_backend():
    backend, _, _ = compare_ssh_configs(str(ROOT / "baseline_sshd_config"), str(ROOT / "current_sshd_config"))
    expected = {(f["setting"], str(f["expected"]), str(f["actual"])) for f in backend}
    server = next(s for s in get_servers() if s["id"] == "sample-ssh")
    shown = {(f["setting"],
              "NOT IN BASELINE" if f["type"] == "added" else str(f["expected"]),
              "MISSING" if f["type"] == "removed" else str(f["actual"]))
             for f in analyze(server)["findings"]}
    assert shown == expected


def test_json_scores_match_backend_main_py():
    server = next(s for s in get_servers() if s["id"] == "sample-json")
    got = {f["setting"]: (f["score"], f["risk"]) for f in analyze(server)["findings"]}
    assert got["firewall_enabled"] == (92, "High")        # main.py prints 92 / HIGH
    assert got["ssh_password_login"] == (82, "High")      # main.py prints 82 / HIGH
