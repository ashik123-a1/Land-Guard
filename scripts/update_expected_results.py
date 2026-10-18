import os
import sys

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("scripts"))

from scripts.md_to_pdf import md_to_pdf
from scripts.update_reports_with_pictures_and_rules import TEST_CASES_DATA

base_dir = r"F:\ashik test data\MANUAL_TEST_3"
md_path = os.path.join(base_dir, "EXPECTED_RESULTS_REFERENCE.md")
pdf_path = os.path.join(base_dir, "EXPECTED_RESULTS_REFERENCE.pdf")

lines = [
    "# LandGuard — Expected Results Reference & Ground Truth Benchmark",
    "",
    "This document provides authoritative, ground-truth reference findings for each of the 25 manual test cases in **MANUAL_TEST_3**, explicitly identifying the **test picture (sample image)**, **test cause (cuz)**, and **specific rules broken**.",
    "",
    "---",
    "",
    "## Authoritative Ground Truth Reference Table",
    "",
    "| Test ID | Test Picture / File | Document Type | Test Cause / Rationale | Rules Broken / Violations | Expected Status | Risk Level |",
    "|:---|:---|:---|:---|:---|:---|:---|",
]

for tc in TEST_CASES_DATA:
    rules_fmt = "<br/>".join(tc["rules_broken"])
    lines.append(
        f"| **{tc['id']}** | `{tc['picture']}` | {tc['doc_type']} | {tc['cause']} | {rules_fmt} | **`{tc['status']}`** | {tc['risk']} |"
    )

content = "\n".join(lines)
with open(md_path, "w", encoding="utf-8") as f:
    f.write(content)
md_to_pdf(md_path, pdf_path, title="Expected Results Reference")
print("Updated EXPECTED_RESULTS_REFERENCE.md and .pdf")
