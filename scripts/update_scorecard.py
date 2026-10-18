import os
import sys
import csv

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("scripts"))

from scripts.md_to_pdf import md_to_pdf
from scripts.update_reports_with_pictures_and_rules import TEST_CASES_DATA

base_dir = r"F:\ashik test data\MANUAL_TEST_3"
md_path = os.path.join(base_dir, "MANUAL_TEST_RESULTS.md")
pdf_path = os.path.join(base_dir, "MANUAL_TEST_RESULTS.pdf")
csv_path = os.path.join(base_dir, "MANUAL_TEST_RESULTS.csv")

lines = [
    "# LandGuard — Manual Test Results Scorecard (MANUAL_TEST_3)",
    "",
    "This scorecard is designed for human testers, competition judges, and QA officers to record empirical test execution results, explicitly tracking each **test picture (sample image)** and **rules broken**.",
    "",
    "---",
    "",
    "## Tester Information",
    "- **Tester Name / Role:** ________________________________________",
    "- **Test Execution Date:** ________________________________________",
    "- **LandGuard Application Version:** LandGuard v2.4 (Statutory Evidence Release)",
    "- **Test Environment URL:** `http://localhost:8000`",
    "",
    "---",
    "",
    "## Test Execution Scorecard Table",
    "",
    "| Test ID | Test Picture / File | Category / Rule Broken | Expected Status | Actual Status | Expected Rules Triggered | Actual Rules | Pass / Fail | Notes |",
    "|:---|:---|:---|:---|:---|:---|:---|:---|:---|",
]

csv_rows = [
    [
        "test_id", "test_picture", "category_rule_broken", "expected_status",
        "actual_status", "expected_rules", "actual_rules", "pass_fail",
        "tester_initials", "execution_date", "tester_notes"
    ]
]

for tc in TEST_CASES_DATA:
    rules_fmt = "<br/>".join(tc["rules_broken"])
    lines.append(
        f"| **{tc['id']}** | `{tc['picture']}` | {tc['rule_category']} | **`{tc['status']}`** | | {rules_fmt} | | [ ] P  [ ] F | |"
    )
    csv_rows.append([
        tc["id"], tc["picture"], tc["rule_category"], tc["status"],
        "", "; ".join(tc["rules_broken"]), "", "", "", "", ""
    ])

lines.extend([
    "",
    "---",
    "",
    "## Summary Evaluation",
    "- **Total Tests Conducted:** ______ / 25",
    "- **Total Passed:** ______",
    "- **Total Failed:** ______",
    "- **Pass Rate:** ______%",
    "- **Final Recommendation:** `[ ] CERTIFIED COMPLIANT WITH LANDTECH P3  [ ] REMEDIATION REQUIRED`",
    "- **Judge / Tester Signature:** ________________________________________",
])

with open(md_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
md_to_pdf(md_path, pdf_path, title="Manual Test Scorecard")

with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerows(csv_rows)

print("Updated MANUAL_TEST_RESULTS.md, .pdf, and .csv")
