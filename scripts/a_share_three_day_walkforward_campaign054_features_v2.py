#!/usr/bin/env python3
"""Fingerprint-bound Campaign054 feature builder after implementation freeze."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign054_features as runner
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign054_features as runner


EXPECTED_BASE_ENTRYPOINT_SHA256 = (
    "4530bd70360d40e8ee72950f1936041482401a5e07240ac42050836d60d6ad27"
)
EXPECTED_IMPLEMENTATION_FREEZE_SHA256 = (
    "965bb952c21b53bf0c72b28ade7e1a39a30d9f009687b601d33f3a95860d6288"
)

if (
    runner._sha256(runner.Path(runner.__file__).resolve())
    != EXPECTED_BASE_ENTRYPOINT_SHA256
):
    raise runner.Campaign054FeatureError("Campaign054 base entrypoint changed")
if (
    runner._sha256(runner.DEFAULT_IMPLEMENTATION_FREEZE)
    != EXPECTED_IMPLEMENTATION_FREEZE_SHA256
):
    raise runner.Campaign054FeatureError(
        "Campaign054 implementation freeze changed"
    )

runner.IMPLEMENTATION_FREEZE_SHA256 = EXPECTED_IMPLEMENTATION_FREEZE_SHA256
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(runner.main())
