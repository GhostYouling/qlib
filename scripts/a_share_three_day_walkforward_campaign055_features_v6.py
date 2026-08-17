#!/usr/bin/env python3
"""Fingerprint-bound Campaign055 v2 snapshot-build entrypoint."""

from __future__ import annotations

from pathlib import Path

try:
    import scripts.a_share_three_day_walkforward_campaign055_features_v5 as repaired
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign055_features_v5 as repaired


runner = repaired.runner
REPAIR_IMPLEMENTATION_FREEZE = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_055_snapshot_repair_implementation_freeze_20260804.json"
)
EXPECTED_REPAIRED_V5_SHA256 = (
    "32241f9ccadcd2f8867c0d9fe1b8bb0c21a9cc742c252eb6b81ff9c630627a79"
)
EXPECTED_REPAIR_IMPLEMENTATION_FREEZE_SHA256 = (
    "5ea65079404c0fb547ffcdb5c1a4f1b5b497864454c1a609b34569d170fe3457"
)

if runner._sha256(Path(repaired.__file__).resolve()) != EXPECTED_REPAIRED_V5_SHA256:
    raise runner.Campaign055FeatureError(
        "Campaign055 frozen v5 snapshot repair changed"
    )
runner._require_file(
    REPAIR_IMPLEMENTATION_FREEZE,
    EXPECTED_REPAIR_IMPLEMENTATION_FREEZE_SHA256,
    "Campaign055 snapshot repair implementation freeze",
)
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(runner.main())
