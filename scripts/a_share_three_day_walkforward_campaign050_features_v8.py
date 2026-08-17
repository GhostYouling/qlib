#!/usr/bin/env python3
"""Audit-repair-implementation-freeze-bound Campaign050 entrypoint."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign050_features_v7 as repaired
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign050_features_v7 as repaired


runner = repaired.runner
REPAIR_IMPLEMENTATION_FREEZE = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_050_no_return_audit_repair_implementation_freeze_20260801.json"
)
EXPECTED_REPAIR_ENTRYPOINT_SHA256 = (
    "7665c101e803e7bc28855b1d9c72702405ecc142cd2e92dd3df09e20fac528c7"
)
EXPECTED_REPAIR_IMPLEMENTATION_FREEZE_SHA256 = (
    "06a301cf51c0b939a62251016c60466be6f129834ec0f2306dafdbaddb2f8f96"
)

if (
    runner._sha256(runner.Path(repaired.__file__).resolve())
    != EXPECTED_REPAIR_ENTRYPOINT_SHA256
):
    raise runner.Campaign050FeatureError("Campaign050 repaired v7 entrypoint changed")
if (
    runner._sha256(REPAIR_IMPLEMENTATION_FREEZE)
    != EXPECTED_REPAIR_IMPLEMENTATION_FREEZE_SHA256
):
    raise runner.Campaign050FeatureError(
        "Campaign050 audit repair implementation freeze changed"
    )


if __name__ == "__main__":
    raise SystemExit(runner.main())
