#!/usr/bin/env python3
"""Fingerprint-bound Campaign054 audit with isolated candidate loader."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign054_features_v7 as repaired
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign054_features_v7 as repaired


audited = repaired.audited
runner = repaired.runner
REPAIR_IMPLEMENTATION_FREEZE = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_054_candidate_loader_repair_implementation_freeze_20260803.json"
)
EXPECTED_REPAIRED_ENTRYPOINT_SHA256 = (
    "329436a275023554223efb692de895da9615241b0b3cc9bc0181ede8b36936e3"
)
EXPECTED_REPAIR_IMPLEMENTATION_FREEZE_SHA256 = (
    "c156b70ff11b11dc53b4556bad6a0f4b3f5997744166ec714b694c3bc1de3c3b"
)

if (
    runner._sha256(runner.Path(repaired.__file__).resolve())
    != EXPECTED_REPAIRED_ENTRYPOINT_SHA256
):
    raise runner.Campaign054FeatureError(
        "Campaign054 frozen v7 candidate loader changed"
    )
runner._require_file(
    REPAIR_IMPLEMENTATION_FREEZE,
    EXPECTED_REPAIR_IMPLEMENTATION_FREEZE_SHA256,
    "Campaign054 candidate-loader repair implementation freeze",
)
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(audited.main())
