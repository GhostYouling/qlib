#!/usr/bin/env python3
"""Fingerprint-bound Campaign054 development execution entrypoint."""

from __future__ import annotations

from pathlib import Path

try:
    import scripts.a_share_three_day_walkforward_campaign054 as runner
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign054 as runner


DEVELOPMENT_IMPLEMENTATION_FREEZE = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_054_development_implementation_freeze_20260803.json"
)
EXPECTED_BASE_ENTRYPOINT_SHA256 = (
    "1a8ac0d9e562ef5e749b7570e197b0ded22142f26a592c87517d7e6140da836c"
)
EXPECTED_PREREGISTRATION_SHA256 = (
    "4841579f32e889de783a9a665df346c45b6c7955b32d5315d443efc5de174330"
)
EXPECTED_DEVELOPMENT_IMPLEMENTATION_FREEZE_SHA256 = (
    "a34176f0e663ba8f7a7e1ce1ca2507f4895f248ca608c1f49268755ac459c9f9"
)

if runner._sha256(Path(runner.__file__).resolve()) != EXPECTED_BASE_ENTRYPOINT_SHA256:
    raise runner.Campaign054Error("Campaign054 base development entrypoint changed")
if (
    runner._sha256(runner.DEFAULT_PREREGISTRATION)
    != EXPECTED_PREREGISTRATION_SHA256
):
    raise runner.Campaign054Error("Campaign054 development preregistration changed")
if (
    runner._sha256(DEVELOPMENT_IMPLEMENTATION_FREEZE)
    != EXPECTED_DEVELOPMENT_IMPLEMENTATION_FREEZE_SHA256
):
    raise runner.Campaign054Error(
        "Campaign054 development implementation freeze changed"
    )


if __name__ == "__main__":
    raise SystemExit(runner.main())
