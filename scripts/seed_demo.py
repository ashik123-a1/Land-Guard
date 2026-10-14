"""Idempotent Demo Verification & Seeding Script
Validates the demo scenarios manifest, verifies image paths, checks registry presence,
and runs live verification to confirm expected outcomes.
"""

import os
import sys
import json

sys.path.insert(0, os.path.abspath("."))

from src.landguard_web.service import LandGuardVerificationService


def run_demo_seeding():
    print("==================================================================")
    print("   LandGuard AI — Idempotent Demo Verification & Seeding Engine   ")
    print("==================================================================")

    manifest_path = os.path.join("data", "fixtures", "demo_manifest.json")
    if not os.path.exists(manifest_path):
        print(f"[ERROR] Manifest not found: {manifest_path}")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    scenarios = manifest.get("scenarios", [])
    print(f"Loaded {len(scenarios)} demonstration scenarios from fixture manifest.")

    service = LandGuardVerificationService()
    print(f"Indexed {len(service.parcels_by_plot)} cadastral parcels in service memory.")
    print(f"XGBoost Model Status: {'ONLINE' if service.xgb_model is not None else 'FALLBACK'}\n")

    passed_count = 0

    for s in scenarios:
        demo_id = s["demo_id"]
        title = s["title"]
        img_path = s["image_path"]
        expected = s["expected_behavior"]

        img_ok = os.path.exists(img_path)
        print(f"[{demo_id}] {title}")
        print(f"  - Image: {img_path} ({'FOUND' if img_ok else 'MISSING'})")

        # Run verification
        result = service.verify_transaction(
            confirmed_fields=s["preset_fields"],
            image_path=img_path if img_ok else None,
        )

        status_match = result["overall_status"] == expected["status"]
        rule_codes = [r["rule_code"] for r in result["rules_triggered"]]

        rule_match = True
        if "expected_rule" in expected:
            rule_match = expected["expected_rule"] in rule_codes

        ml_match = True
        if "min_ml_risk" in expected and result["ml_risk_score"] is not None:
            ml_match = result["ml_risk_score"] >= expected["min_ml_risk"]

        if status_match and rule_match and ml_match:
            print(f"  - Verification Outcome: PASS (Status: {result['overall_status']}, Rules: {rule_codes}, ML Risk: {result['ml_risk_score']})")
            passed_count += 1
        else:
            print(f"  - Verification Outcome: MISMATCH! (Got: {result['overall_status']}, Expected: {expected['status']})")

        print("")

    print("------------------------------------------------------------------")
    print(f"Demo Seeding & Verification Summary: {passed_count}/{len(scenarios)} Scenarios Verified.")
    print("==================================================================")
    return passed_count == len(scenarios)


if __name__ == "__main__":
    success = run_demo_seeding()
    sys.exit(0 if success else 1)
