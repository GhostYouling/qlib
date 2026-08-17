#!/usr/bin/env python3
"""Fingerprint-bound Campaign055 snapshot-build entrypoint."""

from __future__ import annotations

from pathlib import Path

try:
    import scripts.a_share_three_day_walkforward_campaign055_features_v3 as repaired
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign055_features_v3 as repaired


runner = repaired.runner
REPAIR_FREEZE = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_055_implementation_freeze_repair_freeze_20260804.json"
)
EXPECTED_REPAIRED_ENTRYPOINT_SHA256 = (
    "fa9cc6449404da91dd39dd6ed340f83eb70be768a7808df5cd9bc4da1b0040fa"
)
EXPECTED_REPAIR_FREEZE_SHA256 = (
    "648aaf8a2734089fa0225ac4f5fe6f1967abf98ac6284e15c40dc06cc6904485"
)

if (
    runner._sha256(Path(repaired.__file__).resolve())
    != EXPECTED_REPAIRED_ENTRYPOINT_SHA256
):
    raise runner.Campaign055FeatureError(
        "Campaign055 repaired v3 entrypoint changed"
    )
runner._require_file(
    REPAIR_FREEZE,
    EXPECTED_REPAIR_FREEZE_SHA256,
    "Campaign055 implementation-freeze repair freeze",
)
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(runner.main())
