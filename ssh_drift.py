
import json
import os
from datetime import datetime

from ssh_parser import parse_ssh_config
from ai_explainer import explain_findings


REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)


def compare_ssh_configs(baseline_path, current_path):
    baseline, baseline_warnings = parse_ssh_config(baseline_path)
    current, current_warnings = parse_ssh_config(current_path)

    findings = []

    # Check settings present in the approved baseline
    for setting, expected_value in baseline.items():
        if setting not in current:
            findings.append({
                "setting": setting,
                "expected": expected_value,
                "actual": "MISSING",
                "status": "MISSING_SETTING"
            })

        elif current[setting] != expected_value:
            findings.append({
                "setting": setting,
                "expected": expected_value,
                "actual": current[setting],
                "status": "CHANGED"
            })

    # Check settings present only in the current file
    for setting, actual_value in current.items():
        if setting not in baseline:
            findings.append({
                "setting": setting,
                "expected": "NOT IN BASELINE",
                "actual": actual_value,
                "status": "NEW_SETTING"
            })

    return findings, baseline_warnings, current_warnings


if __name__ == "__main__":
    findings, baseline_warnings, current_warnings = (
        compare_ssh_configs(
            "baseline_sshd_config",
            "current_sshd_config"
        )
    )

    print("SSH CONFIGURATION DRIFT REPORT")
    print("=" * 35)

    if not findings:
        print("No differences detected.")
    else:
        for finding in findings:
            print(f"\nSetting: {finding['setting']}")
            print(f"Expected: {finding['expected']}")
            print(f"Current: {finding['actual']}")
            print(f"Status: {finding['status']}")

    # Collect parser warnings
    if baseline_warnings or current_warnings:
        print("\nPARSER WARNINGS")
        for warning in baseline_warnings:
            print("Baseline:", warning)
        for warning in current_warnings:
            print("Current:", warning)

    # Generate AI explanation
    print("\nAI SECURITY EXPLANATION")
    print("=" * 35)

    ai_explanation = explain_findings(findings)
    print(ai_explanation)

    # Save the SSH scan report
    report = {
        "scan_type": "SSH configuration",
        "scan_time": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "total_drift_findings": len(findings),
        "findings": findings,
        "baseline_warnings": baseline_warnings,
        "current_warnings": current_warnings,
        "ai_explanation": ai_explanation
    }

    report_file = os.path.join(
        REPORTS_DIR,
        datetime.now().strftime(
            "ssh_scan_report_%Y%m%d_%H%M%S.json"
        )
    )

    with open(report_file, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    print(f"\nSSH report saved successfully: {report_file}")
