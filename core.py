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
    # settings that appear in the backend's baseline.json
    "logging_enabled": "Security logging", "security_updates": "Security updates",
    # sshd_config directives (ssh_parser.py lower-cases every directive name)
    "permitrootlogin": "SSH root login", "passwordauthentication": "SSH password login",
    "pubkeyauthentication": "SSH key login", "permitemptypasswords": "Empty passwords allowed",
    "maxauthtries": "Max login attempts", "logingracetime": "Login grace time",
    "x11forwarding": "X11 forwarding", "allowagentforwarding": "Agent forwarding",
    "allowtcpforwarding": "TCP forwarding", "gatewayports": "Gateway ports",
    "permittunnel": "Tunnel devices", "permituserrc": "User rc files",
    "clientaliveinterval": "Idle check interval", "clientalivecountmax": "Idle check count",
    "ignorerhosts": "Ignore .rhosts", "hostbasedauthentication": "Host-based login",
    "loglevel": "SSH log level", "kbdinteractiveauthentication": "Keyboard-interactive login",
    "challengeresponseauthentication": "Challenge-response login",
}
# Risk is decided by RULES, never by AI. Unknown settings default to Medium.
RISK_RULES = {
    "firewall_enabled": "High", "ssh_password_login": "High", "ssh_root_login": "High",
    "open_ports": "High", "telnet_enabled": "High",
    "password_min_length": "Medium", "auto_updates": "Medium", "log_level": "Low",
    "logging_enabled": "Medium", "security_updates": "High",
    # sshd_config directives
    "permitrootlogin": "High", "passwordauthentication": "High", "permitemptypasswords": "High",
    "hostbasedauthentication": "Medium", "allowagentforwarding": "Medium", "allowtcpforwarding": "Medium",
    "gatewayports": "Medium", "permittunnel": "Medium", "ignorerhosts": "Medium", "maxauthtries": "Medium",
    "kbdinteractiveauthentication": "Medium", "challengeresponseauthentication": "Medium",
    "x11forwarding": "Low", "permituserrc": "Low", "logingracetime": "Low", "clientaliveinterval": "Low",
    "clientalivecountmax": "Low", "loglevel": "Low", "pubkeyauthentication": "Low", "usepam": "Low",
    "printmotd": "Low", "printlastlog": "Low", "tcpkeepalive": "Low", "compression": "Low",
    "syslogfacility": "Low", "addressfamily": "Low", "port": "Low", "listenaddress": "Low",
}

# Mirror of security_rules / calculate_risk() in the backend's main.py. main.py is a script that
# runs on import, so the frontend cannot import it. If the backend weights change, change them here too.
BACKEND_RULES = {
    "firewall_enabled":   dict(unsafe=False, severity=100, impact=90, exposure=80, compliance=90,
                               reason="Firewall protection is disabled."),
    "ssh_password_login": dict(unsafe=True, severity=85, impact=80, exposure=85, compliance=75,
                               reason="SSH password login is enabled."),
    "logging_enabled":    dict(unsafe=False, severity=75, impact=65, exposure=40, compliance=80,
                               reason="Security logging is disabled."),
    "security_updates":   dict(unsafe=False, severity=90, impact=85, exposure=70, compliance=85,
                               reason="Security updates are disabled."),
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


def backend_score(setting: str, actual):
    """Same maths as the backend: weighted 0-100 score and level for a rule-covered setting."""
    rule = BACKEND_RULES[setting]
    if actual != rule["unsafe"]:
        return 0, "LOW", "The predefined unsafe condition was not detected."
    score = round(rule["severity"] * 0.40 + rule["impact"] * 0.30
                  + rule["exposure"] * 0.20 + rule["compliance"] * 0.10)
    return score, "HIGH" if score >= 80 else "MEDIUM" if score >= 50 else "LOW", rule["reason"]


def rate(f: dict):
    """-> (risk, score, reason). Backend rules first; otherwise the frontend rule table (score None)."""
    if f["type"] == "modified" and f["setting"] in BACKEND_RULES:
        score, level, reason = backend_score(f["setting"], f["actual"])
        return level.title(), score, reason
    reason = {"added": "New setting requires security review.",
              "removed": "Setting is missing from the current configuration."}.get(
                  f["type"], "Setting differs from the approved baseline.")
    return RISK_RULES.get(f["setting"], "Medium"), None, reason


def rate_risk(f: dict) -> str:
    return rate(f)[0]


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
        d["risk"], d["score"], d["reason"] = rate(d)
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
                          "riskScore": f.get("score"), "reason": f.get("reason"),
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
