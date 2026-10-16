"""Core logic (no UI): drift detection, risk rules, scoring, reports."""
import csv
import io
import json
from datetime import datetime

# ---------------------------------------------------------------- rules & labels
SETTING_LABELS = {
    "firewall_enabled": "Firewall", "ssh_password_login": "SSH password login",
    "ssh_root_login": "SSH root login", "open_ports": "Open ports",
    "password_min_length": "Minimum password length", "auto_updates": "Automatic updates",
    "log_level": "Log level", "telnet_enabled": "Telnet service",
}
# Risk is decided by RULES, never by AI. Unknown settings default to Medium.
RISK_RULES = {
    "firewall_enabled": "High", "ssh_password_login": "High", "ssh_root_login": "High",
    "open_ports": "High", "telnet_enabled": "High",
    "password_min_length": "Medium", "auto_updates": "Medium", "log_level": "Low",
}
RISK_ORDER = {"High": 0, "Medium": 1, "Low": 2, "None": 3}
PENALTY = {"High": 15, "Medium": 7, "Low": 2}
DOT = {"High": "#F04438", "Medium": "#F79009", "Low": "#12B76A", "None": "#12B76A"}
TYPE_LABEL = {"modified": "Modified", "added": "Added", "removed": "Removed", "same": "Unchanged"}


def label(key: str) -> str:
    return SETTING_LABELS.get(key) or key.replace("_", " ").capitalize()


# ---------------------------------------------------------------- comparison
def _norm(v):
    if isinstance(v, list):
        try:
            v = sorted(v)
        except TypeError:
            v = sorted(v, key=str)
    return json.dumps(v, sort_keys=True)


def find_drifts(baseline: dict, current: dict) -> list[dict]:
    """Compare baseline vs current -> list of {setting, type, expected, actual}."""
    out = []
    for k, exp in baseline.items():
        if k not in current:
            out.append({"setting": k, "type": "removed", "expected": exp, "actual": None})
        elif _norm(exp) != _norm(current[k]):
            out.append({"setting": k, "type": "modified", "expected": exp, "actual": current[k]})
    for k, act in current.items():
        if k not in baseline:
            out.append({"setting": k, "type": "added", "expected": None, "actual": act})
    return out


def rate_risk(f: dict) -> str:
    return RISK_RULES.get(f["setting"], "Medium")


def overall_risk(findings: list[dict]) -> str:
    if not findings:
        return "None"
    return min((f["risk"] for f in findings), key=lambda r: RISK_ORDER[r])


def posture_score(findings: list[dict]) -> int:
    """100 - 15 per High - 7 per Medium - 2 per Low, floored at 0."""
    return max(0, 100 - sum(PENALTY[f["risk"]] for f in findings))


def analyze(server: dict) -> dict:
    findings = []
    for d in find_drifts(server["baseline"], server["current"]):
        d["id"] = f"{server['id']}::{d['setting']}"
        d["server_id"] = server["id"]
        d["risk"] = rate_risk(d)
        findings.append(d)
    findings.sort(key=lambda f: RISK_ORDER[f["risk"]])
    return {**server, "findings": findings, "highest": overall_risk(findings),
            "score": posture_score(findings)}


def totals(analyzed: list[dict]) -> dict:
    allf = [f for s in analyzed for f in s["findings"]]
    c = {"High": 0, "Medium": 0, "Low": 0}
    for f in allf:
        c[f["risk"]] += 1
    affected = sum(1 for s in analyzed if s["findings"])
    posture = round(sum(s["score"] for s in analyzed) / len(analyzed)) if analyzed else 100
    return {"all": allf, "c": c, "affected": affected, "healthy": len(analyzed) - affected,
            "total": len(allf), "posture": posture}


def history_points(history: list[dict], analyzed: list[dict]) -> list[dict]:
    t = totals(analyzed)
    return history + [{"id": "now", "time": datetime.now(), "servers": len(analyzed),
                       "drifts": t["total"], "high": t["c"]["High"]}]


# ---------------------------------------------------------------- reports
def plain(v, present: bool = True) -> str:
    if not present:
        return "not set"
    if isinstance(v, bool):
        return "ON" if v else "OFF"
    if isinstance(v, list):
        return "[" + ", ".join(str(x) for x in v) + "]"
    if isinstance(v, dict):
        return json.dumps(v)
    return str(v)


def f_expected(f):  # printable expected / actual of a finding
    return plain(f["expected"], f["type"] != "added")


def f_actual(f):
    return plain(f["actual"], f["type"] != "removed")


def summary(f: dict) -> str:
    return f"{label(f['setting'])}: {f_expected(f)} → {f_actual(f)}"


def report_data(analyzed: list[dict], decisions: dict) -> dict:
    t = totals(analyzed)
    return {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "summary": {"servers": len(analyzed), "drifts": t["total"], "high": t["c"]["High"],
                    "medium": t["c"]["Medium"], "low": t["c"]["Low"], "postureScore": t["posture"]},
        "servers": [{
            "id": s["id"], "name": s["name"], "environment": s["environment"], "os": s["os"],
            "status": s["status"], "lastScan": s["last_scan"].isoformat(timespec="seconds"),
            "riskLevel": s["highest"], "score": s["score"],
            "findings": [{"setting": f["setting"], "change": f["type"], "expected": f["expected"],
                          "actual": f["actual"], "risk": f["risk"],
                          "decision": decisions.get(f["id"], {"status": "Pending"})}
                         for f in s["findings"]],
        } for s in analyzed],
    }


def report_csv(analyzed: list[dict], decisions: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_ALL)
    w.writerow(["server", "environment", "setting", "change", "expected", "actual", "risk",
                "status", "decided_by", "decided_at", "note"])
    for s in analyzed:
        for f in s["findings"]:
            d = decisions.get(f["id"], {})
            w.writerow([s["name"], s["environment"], f["setting"], f["type"], f_expected(f),
                        f_actual(f), f["risk"], d.get("status", "Pending"), d.get("by", ""),
                        d.get("at", ""), d.get("note", "")])
    return buf.getvalue()
