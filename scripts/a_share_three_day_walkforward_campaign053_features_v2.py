#!/usr/bin/env python3
"""Fingerprint-bound Campaign053 feature builder after implementation freeze."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign053_features as runner
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign053_features as runner


EXPECTED_BASE_ENTRYPOINT_SHA256 = "4007eae34134d11bc057b3cd251050a18b36f0d79dac0ab5ecf5f5fcfb2407e3"
EXPECTED_IMPLEMENTATION_FREEZE_SHA256 = "98e6423515998a989458b51fd3896153a157cef27e53b489c0d818a2254c37be"

if runner._sha256(runner.Path(runner.__file__).resolve()) != EXPECTED_BASE_ENTRYPOINT_SHA256:
    raise runner.Campaign053FeatureError("Campaign053 base entrypoint changed")
if runner._sha256(runner.DEFAULT_IMPLEMENTATION_FREEZE) != EXPECTED_IMPLEMENTATION_FREEZE_SHA256:
    raise runner.Campaign053FeatureError("Campaign053 implementation freeze changed")

runner.IMPLEMENTATION_FREEZE_SHA256 = EXPECTED_IMPLEMENTATION_FREEZE_SHA256
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(runner.main())
