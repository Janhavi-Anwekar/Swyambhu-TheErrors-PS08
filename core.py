"""Core logic (no UI): file parsing, drift detection, risk rules, scoring, reports."""
import csv
import hashlib
import io
import json
import re
from datetime import datetime

# ---------------------------------------------------------------- rules & labels
SETTING_LABELS = {
    "firewall_enabled": "Firewall", "ssh_password_login": "SSH password login",
    "ssh_root_login": "SSH root login", "open_ports": "Open ports",
    "password_min_length": "Minimum password length", "auto_updates": "Automatic updates",
    "log_level": "Log level", "telnet_enabled": "Telnet service",
    "permit_empty_passwords": "Empty passwords allowed", "x11_forwarding": "X11 forwarding",
    "max_auth_tries": "Max authentication attempts", "ssh_port": "SSH port",
}
# Risk is decided by RULES, never by AI. Unknown settings default to Medium.
RISK_RULES = {
    "firewall_enabled": "High", "ssh_password_login": "High", "ssh_root_login": "High",
    "open_ports": "High", "telnet_enabled": "High", "permit_empty_passwords": "High",
    "password_min_length": "Medium", "auto_updates": "Medium", "max_auth_tries": "Medium",
    "log_level": "Low", "x11_forwarding": "Low", "ssh_port": "Low",
}
RISK_ORDER = {"High": 0, "Medium": 1, "Low": 2, "None": 3}
PENALTY = {"High": 15, "Medium": 7, "Low": 2}
DOT = {"High": "#FF3B30", "Medium": "#FF9F0A", "Low": "#34C759", "None": "#34C759"}
TYPE_LABEL = {"modified": "Modified", "added": "Added", "removed": "Removed", "same": "Unchanged"}

# Used ONLY when the user does not upload a baseline.
STANDARD_BASELINE = {
        # Network security
    "firewall_enabled": True,
    "open_ports": [22, 443],
    "telnet_enabled": False,

    # SSH authentication
    "ssh_password_login": False,
    "ssh_root_login": False,
    "permit_empty_passwords": False,
    "max_auth_tries": 4,
    "password_min_length": 12,
    "pubkey_authentication": True,
    "strict_modes": True,
    "ignore_rhosts": True,

    # SSH connection and forwarding
    "x11_forwarding": False,
    "allow_tcp_forwarding": False,
    "client_alive_interval": 300,
    "client_alive_count_max": 3,
    "compression": False,

    # System maintenance
    "auto_updates": True,

    # Logging
    "log_level": "info",

    # SSH server configuration
    "port": 22,
    "protocol": 2,
}


def label(key: str) -> str:
    return SETTING_LABELS.get(key) or key.replace("_", " ").capitalize()


# ---------------------------------------------------------------- file parsing
class ConfigError(ValueError):
    """A problem with an uploaded file, worded for the end user."""


MAX_BYTES = 2_000_000
BOOL = {"yes": True, "no": False, "true": True, "false": False, "on": True, "off": False}
# sshd keyword (lower-case) -> normalised setting name used by the rules above
SSH_ALIASES = {
    "passwordauthentication": "ssh_password_login", "permitrootlogin": "ssh_root_login",
    "permitemptypasswords": "permit_empty_passwords", "x11forwarding": "x11_forwarding",
    "maxauthtries": "max_auth_tries", "loglevel": "log_level", "port": "ssh_port",
}
SSH_MULTI = {"hostkey", "listenaddress", "acceptenv", "subsystem", "allowusers", "allowgroups",
             "denyusers", "denygroups", "include"}
SSH_KNOWN = set(SSH_ALIASES) | SSH_MULTI | {
    "protocol", "syslogfacility", "logingracetime", "strictmodes", "pubkeyauthentication",
    "authorizedkeysfile", "usepam", "challengeresponseauthentication", "kbdinteractiveauthentication",
    "printmotd", "printlastlog", "clientaliveinterval", "clientalivecountmax", "usedns",
    "allowtcpforwarding", "gatewayports", "permittunnel", "maxsessions", "maxstartups", "banner",
    "ciphers", "macs", "kexalgorithms", "ignorerhosts", "hostbasedauthentication",
    "permituserenvironment", "compression", "tcpkeepalive", "authenticationmethods",
    "permittty", "chrootdirectory", "forcecommand", "allowagentforwarding"}


def _snake(name: str) -> str:
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s).lower()


def _coerce(v: str):
    low = v.lower()
    if low in BOOL:
        return BOOL[low]
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    return v


def parse_ssh(text: str) -> dict:
    """Parse an sshd_config style file into normalised settings."""
    out: dict = {}
    ports: list = []
    known_seen = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z][A-Za-z0-9]*)(?:\s*=\s*|\s+)(.+)$", line)
        if not m:
            continue
        key, val = m.group(1), re.sub(r"\s+#.*$", "", m.group(2)).strip().strip('"')
        low = key.lower()
        if low == "match":          # conditional blocks follow; stop reading global settings
            break
        if low in SSH_KNOWN:
            known_seen += 1
        if low == "port":
            if val.isdigit():
                ports.append(int(val))
            continue
        name = SSH_ALIASES.get(low) or _snake(key)
        if low in SSH_MULTI:
            out.setdefault(name, []).append(val)
        elif name not in out:       # sshd: the first occurrence of a keyword wins
            out[name] = val.lower() if low == "loglevel" else _coerce(val)
    if not known_seen:
        raise ConfigError("This doesn't look like an SSH config (sshd_config). "
                          "Upload a JSON object of settings or an sshd_config file.")
    if ports:
        out["ssh_port"] = sorted(set(ports))
    return out


def parse_json(text: str, filename: str) -> dict:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ConfigError(f"{filename} is not valid JSON (line {e.lineno}, column {e.colno}: {e.msg}).")
    if not isinstance(data, dict) or not data:
        raise ConfigError(f'{filename} must contain a JSON object of settings, e.g. {{"firewall_enabled": true}}.')
    out = {}
    for k, v in data.items():
        norm = SSH_ALIASES.get(str(k).lower())     # allow sshd-style names inside JSON too
        if norm:
            k = norm
            if isinstance(v, str):
                v = _coerce(v)
        out[str(k)] = v
    return out


def parse_config(filename: str, data: bytes) -> tuple[dict, str]:
    """Detect JSON vs SSH and parse. Returns (settings, kind) with kind in {'json', 'ssh'}."""
    if len(data) > MAX_BYTES:
        raise ConfigError(f"{filename} is larger than 2 MB. Upload just the configuration file.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ConfigError(f"{filename} is not a text file. Upload a JSON or SSH config file.")
    if "\x00" in text:
        raise ConfigError(f"{filename} is not a text file. Upload a JSON or SSH config file.")
    stripped = text.lstrip()
    if not stripped:
        raise ConfigError(f"{filename} is empty.")
    if filename.lower().endswith(".json") or stripped[0] in "{[":
        return parse_json(text, filename), "json"
    return parse_ssh(text), "ssh"


def build_run(cur_name: str, cur_bytes: bytes, base_name: str | None = None,
              base_bytes: bytes | None = None) -> dict:
    """Parse the uploads and prepare one comparison.

    With a baseline file the two files are compared as they are.
    Without one, the current file is checked against STANDARD_BASELINE, limited to the
    settings the file actually contains (so an sshd_config is not blamed for having no firewall key).
    """
    cur, cur_kind = parse_config(cur_name, cur_bytes)
    if base_bytes is not None:
        base, base_kind = parse_config(base_name or "baseline", base_bytes)
        mode, base_label, not_covered, missing = "custom", base_name or "baseline", [], []
    else:
        shared = [k for k in STANDARD_BASELINE if k in cur]
        if not shared:
            raise ConfigError(f"None of the settings in {cur_name} are covered by the standard baseline. "
                              "Upload your own baseline file to compare against.")
        base = {k: STANDARD_BASELINE[k] for k in shared}
        not_covered = [k for k in cur if k not in base]
        cur = {k: cur[k] for k in shared}
        missing = [k for k in STANDARD_BASELINE if k not in base]
        mode, base_kind, base_label = "standard", "standard", "Standard baseline"
    digest = hashlib.sha1(cur_bytes + (base_bytes if base_bytes is not None else b"standard")).hexdigest()[:8]
    return dict(id=f"cfg-{digest}", name=cur_name, kind=cur_kind, base_kind=base_kind, mode=mode,
                base_label=base_label, baseline=base, current=cur, not_covered=not_covered,
                missing=missing, last_scan=datetime.now())


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


def analyze(run: dict) -> dict:
    findings = []
    for d in find_drifts(run["baseline"], run["current"]):
        d["id"] = f"{run['id']}::{d['setting']}"
        d["server_id"] = run["id"]
        d["risk"] = rate_risk(d)
        findings.append(d)
    findings.sort(key=lambda f: RISK_ORDER[f["risk"]])
    return {**run, "findings": findings, "highest": overall_risk(findings),
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
        "summary": {"comparisons": len(analyzed), "drifts": t["total"], "high": t["c"]["High"],
                    "medium": t["c"]["Medium"], "low": t["c"]["Low"], "postureScore": t["posture"]},
        "comparisons": [{
            "id": s["id"], "currentFile": s["name"], "fileType": s["kind"],
            "comparedAgainst": s["base_label"], "baselineMode": s["mode"],
            "scannedAt": s["last_scan"].isoformat(timespec="seconds"),
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
    w.writerow(["file", "compared_against", "setting", "change", "expected", "actual", "risk",
                "status", "decided_by", "decided_at", "note"])
    for s in analyzed:
        for f in s["findings"]:
            d = decisions.get(f["id"], {})
            w.writerow([s["name"], s["base_label"], f["setting"], f["type"], f_expected(f),
                        f_actual(f), f["risk"], d.get("status", "Pending"), d.get("by", ""),
                        d.get("at", ""), d.get("note", "")])
    return buf.getvalue()
