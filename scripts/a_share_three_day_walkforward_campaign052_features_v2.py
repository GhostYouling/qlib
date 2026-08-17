#!/usr/bin/env python3
"""Fingerprint-bound Campaign052 feature runner after implementation freeze."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign052_features as runner
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign052_features as runner


EXPECTED_BASE_RUNNER_SHA256 = (
    "8a8a389f5b6f8d3cacd3d10ad6d0f2bd44eae4bf8b2e680fb22987f1944c3875"
)
EXPECTED_IMPLEMENTATION_FREEZE_SHA256 = (
    "e599183d5d43f74c48fa601a5acc049606c219fb773800f15ba590f4c265c0b4"
)

if runner._sha256(runner.Path(runner.__file__).resolve()) != EXPECTED_BASE_RUNNER_SHA256:
    raise runner.Campaign052FeatureError("Campaign052 frozen base runner changed")
if (
    runner._sha256(runner.DEFAULT_IMPLEMENTATION_FREEZE)
    != EXPECTED_IMPLEMENTATION_FREEZE_SHA256
):
    raise runner.Campaign052FeatureError(
        "Campaign052 implementation-freeze record changed"
    )

runner.IMPLEMENTATION_FREEZE_SHA256 = EXPECTED_IMPLEMENTATION_FREEZE_SHA256
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(runner.main())
