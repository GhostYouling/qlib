#!/usr/bin/env python3
"""Fingerprint-bound Campaign054 v2 snapshot repair entrypoint."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign054_features_v3 as repaired
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign054_features_v3 as repaired


runner = repaired.runner
REPAIR_IMPLEMENTATION_FREEZE = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_054_snapshot_repair_implementation_freeze_20260803.json"
)
EXPECTED_REPAIRED_ENTRYPOINT_SHA256 = (
    "c608905ba9e315fe995be1b1e09cf67b9c652e01d1e88679e1bae3a80579c468"
)
EXPECTED_REPAIR_IMPLEMENTATION_FREEZE_SHA256 = (
    "c8e784a2c86b87ac256f0cc230835de4ed387555da3b40b5d78b20db8cd246d3"
)

if (
    runner._sha256(runner.Path(repaired.__file__).resolve())
    != EXPECTED_REPAIRED_ENTRYPOINT_SHA256
):
    raise runner.Campaign054FeatureError(
        "Campaign054 frozen v3 snapshot repair changed"
    )
runner._require_file(
    REPAIR_IMPLEMENTATION_FREEZE,
    EXPECTED_REPAIR_IMPLEMENTATION_FREEZE_SHA256,
    "Campaign054 snapshot-repair implementation freeze",
)
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(runner.main())
