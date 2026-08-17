#!/usr/bin/env python3
"""Fingerprint-bound Campaign055 feature implementation entrypoint."""

from __future__ import annotations

from pathlib import Path

try:
    import scripts.a_share_three_day_walkforward_campaign055_features as runner
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign055_features as runner


EXPECTED_RUNNER_SHA256 = (
    "d695e5acd9645f4706e238c95db2ea69df397004416ea4dd9f895385be603714"
)
EXPECTED_IMPLEMENTATION_FREEZE_SHA256 = (
    "ef050cb578ff06775ee43e3119488ad5fbfc39a86d3931abfec642b3d4d01f4a"
)

if runner._sha256(Path(runner.__file__).resolve()) != EXPECTED_RUNNER_SHA256:
    raise runner.Campaign055FeatureError(
        "Campaign055 frozen feature runner changed"
    )
runner._require_file(
    runner.DEFAULT_IMPLEMENTATION_FREEZE,
    EXPECTED_IMPLEMENTATION_FREEZE_SHA256,
    "Campaign055 implementation freeze",
)
runner.IMPLEMENTATION_FREEZE_SHA256 = EXPECTED_IMPLEMENTATION_FREEZE_SHA256
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(runner.main())
