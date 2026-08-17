#!/usr/bin/env python3
"""Repair-implementation-freeze-bound Campaign050 feature entrypoint."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign050_features_v3 as repaired
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign050_features_v3 as repaired


runner = repaired.runner
REPAIR_IMPLEMENTATION_FREEZE = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_050_feature_build_repair_implementation_freeze_20260801.json"
)
EXPECTED_REPAIRED_ENTRYPOINT_SHA256 = (
    "21f08c6d4e11e7209e17bd4a642fcad400a6f876c1b022656f0ab617a400d41e"
)
EXPECTED_REPAIR_IMPLEMENTATION_FREEZE_SHA256 = (
    "4d5807ce08063afda59554c10c19a05bcc262df39b8e83fb6c5878ed4314dde6"
)

if (
    runner._sha256(runner.Path(repaired.__file__).resolve())
    != EXPECTED_REPAIRED_ENTRYPOINT_SHA256
):
    raise runner.Campaign050FeatureError("Campaign050 repaired v3 entrypoint changed")
if (
    runner._sha256(REPAIR_IMPLEMENTATION_FREEZE)
    != EXPECTED_REPAIR_IMPLEMENTATION_FREEZE_SHA256
):
    raise runner.Campaign050FeatureError(
        "Campaign050 repair implementation freeze changed"
    )


if __name__ == "__main__":
    raise SystemExit(runner.main())
