#!/usr/bin/env python3
"""Fingerprint-bound Campaign053 audit after Campaign051 verifier repair."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign053_features_v4 as repaired
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign053_features_v4 as repaired


runner = repaired.runner
REPAIR_IMPLEMENTATION_FREEZE = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_053_campaign051_verifier_repair_implementation_freeze_20260803.json"
)
EXPECTED_REPAIRED_ENTRYPOINT_SHA256 = (
    "7ce884725f3ac9bc8027b91380a8d549b609818c92961e21db3992cc8f1e124f"
)
EXPECTED_REPAIR_IMPLEMENTATION_FREEZE_SHA256 = (
    "2a86d8f6bd2791d823c661bebec16f21664ddfadee1b9a362eea5bcbc3dbec16"
)


if (
    runner._sha256(runner.Path(repaired.__file__).resolve())
    != EXPECTED_REPAIRED_ENTRYPOINT_SHA256
):
    raise runner.Campaign053FeatureError("Campaign053 frozen v4 verifier repair changed")
if (
    runner._sha256(REPAIR_IMPLEMENTATION_FREEZE)
    != EXPECTED_REPAIR_IMPLEMENTATION_FREEZE_SHA256
):
    raise runner.Campaign053FeatureError(
        "Campaign053 Campaign051-verifier implementation freeze changed"
    )
if (
    runner.previous.previous.verify_snapshot_files
    is not repaired.verify_campaign051_snapshot_files
):
    raise runner.Campaign053FeatureError(
        "Campaign053 Campaign051 isolated verifier repair is not installed"
    )


if __name__ == "__main__":
    raise SystemExit(runner.main())
