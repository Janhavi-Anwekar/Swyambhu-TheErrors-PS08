"""AI explanation layer. The AI only EXPLAINS findings that rules already found.

Uses the Anthropic API when ANTHROPIC_API_KEY is set; otherwise (or on any error) it falls
back to pre-written offline text so the demo never breaks. To use another provider
(OpenAI, Gemini...), change only _ask_llm().
"""
import json
import os
import re

MODEL = "claude-sonnet-5-5"
PORT_NAMES = {22: "SSH", 23: "Telnet", 80: "HTTP", 443: "HTTPS", 3306: "MySQL",
              5432: "PostgreSQL", 6379: "Redis", 8080: "alternate HTTP", 27017: "MongoDB"}

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
}


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
            "source": "Offline text (demo)"}


def _ask_llm(prompt: str) -> str:
    import anthropic
    r = anthropic.Anthropic().messages.create(
        model=MODEL, max_tokens=500, messages=[{"role": "user", "content": prompt}])
    return r.content[0].text


def explain(f: dict, use_ai: bool = True) -> dict:
    """f = one finding already detected and rated by code."""
    if not use_ai or not os.getenv("ANTHROPIC_API_KEY"):
        return offline_explanation(f)
    prompt = f"""A server's configuration drifted from its approved baseline.
Setting: {f['setting']}
Change type: {f['type']}
Expected: {f['expected']}
Actual: {f['actual']}
Risk level (set by rules): {f['risk']}

Reply with ONLY JSON with three keys:
"why_it_matters": 1-2 plain-language sentences on the danger
"impact": 1 sentence on what could happen
"suggested_fix": the safe step(s) to restore the expected value
Use only the facts above. Do not invent other problems."""
    try:
        text = re.sub(r"^```(?:json)?|```$", "", _ask_llm(prompt).strip(), flags=re.M).strip()
        d = json.loads(text)
        return {"why_it_matters": d["why_it_matters"], "impact": d["impact"],
                "suggested_fix": d["suggested_fix"], "source": "AI-generated"}
    except Exception as e:  # network, key, parse errors -> keep the demo alive
        out = offline_explanation(f)
        out["source"] = f"Offline text (AI error: {type(e).__name__})"
        return out
