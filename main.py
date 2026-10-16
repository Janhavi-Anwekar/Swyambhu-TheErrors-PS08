
import json
import os
from datetime import datetime
from ai_explainer import explain_findings

# Create the reports folder if it doesn't exist
os.makedirs("reports", exist_ok=True)

# ----------------------------------
# 1. LOAD CONFIGURATION FILES
# ----------------------------------

with open("baseline.json", "r") as file:
    baseline = json.load(file)

with open("current.json", "r") as file:
    current = json.load(file)


# ----------------------------------
# 2. DEFINE SECURITY RULES
# ----------------------------------

security_rules = {
    "firewall_enabled": {
        "unsafe_value": False,
        "severity": 100,
        "impact": 90,
        "exposure": 80,
        "compliance": 90,
        "reason": "Firewall protection is disabled."
    },

    "ssh_password_login": {
        "unsafe_value": True,
        "severity": 85,
        "impact": 80,
        "exposure": 85,
        "compliance": 75,
        "reason": "SSH password login is enabled."
    },

    "logging_enabled": {
        "unsafe_value": False,
        "severity": 75,
        "impact": 65,
        "exposure": 40,
        "compliance": 80,
        "reason": "Security logging is disabled."
    },

    "security_updates": {
        "unsafe_value": False,
        "severity": 90,
        "impact": 85,
        "exposure": 70,
        "compliance": 85,
        "reason": "Security updates are disabled."
    }
}


# ----------------------------------
# 3. CALCULATE WEIGHTED RISK SCORE
# ----------------------------------

def calculate_risk(setting, actual_value):
    rule = security_rules.get(setting)

    if rule is None:
        return 0, "REVIEW REQUIRED", "No specific risk rule exists."

    if actual_value != rule["unsafe_value"]:
        return 0, "NO RULE-TRIGGERED RISK", "The predefined unsafe condition was not detected."

    score = (
        rule["severity"] * 0.40
        + rule["impact"] * 0.30
        + rule["exposure"] * 0.20
        + rule["compliance"] * 0.10
    )

    score = round(score)

    if score >= 80:
        level = "HIGH"
    elif score >= 50:
        level = "MEDIUM"
    else:
        level = "LOW"

    return score, level, rule["reason"]


# ----------------------------------
# 4. DETECT CONFIGURATION DRIFT
# ----------------------------------

print("\nCONFIGURATION DRIFT DETECTOR")
print("=" * 45)

drift_count = 0
findings = []

for setting in baseline:
    if setting not in current:
        drift_count += 1
        findings.append({
            "setting": setting,
            "expected": baseline[setting],
            "actual": "MISSING",
            "score": 0,
            "level": "REVIEW REQUIRED",
            "reason": "Setting is missing from the current configuration."
        })

    elif baseline[setting] != current[setting]:
        drift_count += 1

        score, level, reason = calculate_risk(
            setting, current[setting]
        )

        findings.append({
            "setting": setting,
            "expected": baseline[setting],
            "actual": current[setting],
            "score": score,
            "level": level,
            "reason": reason
        })


# Detect settings that are new
for setting in current:
    if setting not in baseline:
        drift_count += 1
        findings.append({
            "setting": setting,
            "expected": "NOT DEFINED",
            "actual": current[setting],
            "score": 0,
            "level": "REVIEW REQUIRED",
            "reason": "New setting requires security review."
        })


# ----------------------------------
# 5. DISPLAY FINDINGS
# ----------------------------------

for finding in findings:
    print(f"\nSetting: {finding['setting']}")
    print(f"Expected: {finding['expected']}")
    print(f"Current:  {finding['actual']}")
    print(f"Risk score: {finding['score']}/100")
    print(f"Risk level: {finding['level']}")
    print(f"Reason: {finding['reason']}")

print("\n" + "=" * 45)
print(f"Total drift findings: {drift_count}")

if drift_count == 0:
    print("No configuration differences detected.")
    # ----------------------------------
# 6. SAVE SCAN REPORT
# ----------------------------------

report = {
    "scan_time": datetime.now().astimezone().isoformat(
        timespec="seconds"
    ),
    "total_drift_findings": drift_count,
    "findings": findings
}

report_file = datetime.now().strftime(
    "reports/scan_report_%Y%m%d_%H%M%S.json"
)

with open(report_file, "w") as file:
    json.dump(report, file, indent=4)

print(f"\nReport saved successfully: {report_file}")

print("\nAI SECURITY EXPLANATION")
print("=" * 45)
print(explain_findings(findings))