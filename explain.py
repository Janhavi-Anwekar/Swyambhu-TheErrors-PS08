"""AI explanation layer. The AI only EXPLAINS findings that rules already found.

The AI call is the backend's ai_explainer.explain_findings() (local Ollama model). If Ollama is
not running, the model is missing, or the reply is unusable, the pre-written offline text is
used instead, so the demo never breaks.
"""
import json
import re
import urllib.request

from ai_explainer import MODEL_NAME, OLLAMA_URL, explain_findings

PORT_NAMES = {22: "SSH", 23: "Telnet", 80: "HTTP", 443: "HTTPS", 3306: "MySQL",
              5432: "PostgreSQL", 6379: "Redis", 8080: "alternate HTTP", 27017: "MongoDB"}

# explain_findings() returns one of these messages (instead of raising) when the AI fails.
AI_FAILED = ("AI explanation is temporarily unavailable", "Unexpected response from Ollama",
             "AI returned an empty explanation", "No configuration differences")

OFFLINE = {
    "firewall_enabled": (
        "The firewall is the first line of defence. With it switched off, every service listening on the server can be reached from the network, including ones never meant to be public.",
        "Exposed services can be scanned and attacked directly, which can lead to unauthorised access or data loss.",
        "Re-enable the firewall (for example `sudo ufw enable`) and confirm that only the approved ports are allowed."),
    "ssh_password_login": (
        "Password login lets anyone who guesses or steals a password sign in over SSH. Automated password guessing against SSH never stops on the internet. The baseline allows key-based login only.",
        "Brute-force and credential-stuffing attacks become possible against remote access.",
        "Set `PasswordAuthentication no` in /etc/ssh/sshd_config and restart sshd. Make sure SSH keys work for every admin first to avoid a lock-out."),
    "ssh_root_login": (
        "Direct root login hands attackers a well-known, all-powerful account to target.",
        "A single successful guess gives full control of the server.",
        "Set `PermitRootLogin no` in /etc/ssh/sshd_config, restart sshd, and use a normal admin account with sudo."),
    "password_min_length": (
        "A shorter minimum password length makes passwords easier to guess or crack.",
        "Weak passwords raise the chance of account takeover.",
        "Restore the approved minimum length in the password policy (for example PAM `minlen`)."),
    "auto_updates": (
        "Automatic updates install security patches without delay. Without them the server can stay exposed to known flaws.",
        "Known vulnerabilities may stay unpatched for weeks.",
        "Re-enable automatic security updates (for example `unattended-upgrades` on Debian/Ubuntu) and confirm they run."),
    "log_level": (
        "A more verbose log level fills disks faster and may record sensitive data. Low risk, but it differs from the approved setup.",
        "Possible disk pressure and sensitive data ending up in logs.",
        "Set the log level back to the baseline value unless debugging is still in progress."),
    "telnet_enabled": (
        "Telnet sends everything, including passwords, in plain text.",
        "Anyone on the network path can read credentials.",
        "Disable and remove the telnet service and use SSH instead."),
    "logging_enabled": (
        "Security logging records who did what on the server. Without it, attacks and mistakes leave no trace.",
        "Incidents become hard to detect and investigate, and audit requirements may not be met.",
        "Turn security logging back on and confirm that log files are being written."),
}
# the same advice applies to the matching names used elsewhere in the project
OFFLINE["security_updates"] = OFFLINE["auto_updates"]
OFFLINE["permitrootlogin"] = OFFLINE["ssh_root_login"]
OFFLINE["passwordauthentication"] = OFFLINE["ssh_password_login"]


def offline_explanation(f: dict) -> dict:
    why, impact, fix = OFFLINE.get(f["setting"], (
        f'"{f["setting"]}" differs from the approved baseline and should be reviewed.',
        "The effect depends on what this setting controls.",
        f"Restore `{f['setting']}` to the baseline value if the change was not intentional."))
    if f["setting"] == "open_ports" and isinstance(f["actual"], list) and isinstance(f["expected"], list):
        extra = [p for p in f["actual"] if p not in f["expected"]]
        names = ", ".join(f"{p} ({PORT_NAMES[p]})" if p in PORT_NAMES else str(p) for p in extra)
        why = ("Every open port is another service reachable from the network. Ports that were "
               "not approved in the baseline widen the attack surface.")
        impact = (f"Newly exposed: {names}. These may allow remote access or data theft."
                  if extra else "The set of exposed ports changed.")
        fix = (f"Close port(s) {', '.join(map(str, extra))} in the firewall (for example "
               f"`sudo ufw deny {extra[0]}`) and check whether the service behind it should be "
               "running at all." if extra else
               "Compare the open ports with the baseline and close any that are not approved.")
    if f["type"] == "removed":
        why = "This setting is missing from the current config. " + why
    if f["type"] == "added":
        why = "This setting is not in the approved baseline. " + why
    return {"why_it_matters": why, "impact": impact, "suggested_fix": fix,
            "source": "Offline text (demo)", "ai_text": ""}


def ollama_ready() -> bool:
    """True if Ollama is running and has the model the backend uses. Takes at most ~1.5 seconds."""
    try:
        base = OLLAMA_URL.split("/api/")[0]
        with urllib.request.urlopen(base + "/api/tags", timeout=1.5) as r:
            names = [m.get("name", "") for m in json.load(r).get("models", [])]
        return any(n.startswith(MODEL_NAME) for n in names)
    except Exception:
        return False


def explain(f: dict, use_ai: bool = True) -> dict:
    """f = one finding already detected and rated by code. Always returns the offline text; when the
    local AI answers, its text is added as "ai_text"."""
    out = offline_explanation(f)
    if not use_ai:
        return out
    finding = {"setting": f["setting"],
               "expected": "NOT DEFINED" if f["type"] == "added" else f["expected"],
               "actual": "MISSING" if f["type"] == "removed" else f["actual"],
               "level": f["risk"].upper(), "reason": f.get("reason", "")}
    if f.get("score") is not None:
        finding["score"] = f["score"]
    text = explain_findings([finding])                       # backend call (Ollama)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    if not text or text.startswith(AI_FAILED):
        out["source"] = "Offline text (AI unavailable)"
        return out
    out["ai_text"] = text
    out["source"] = f"AI-generated ({MODEL_NAME} via Ollama)"
    return out
