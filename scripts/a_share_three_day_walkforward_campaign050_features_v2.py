#!/usr/bin/env python3
"""Implementation-freeze-bound Campaign050 feature entrypoint."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign050_features as runner
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign050_features as runner


EXPECTED_RUNNER_SHA256 = (
    "4364a92123432a867fa172d30b6cf5a6a27123d735d1b6150422dd94311f7294"
)
EXPECTED_IMPLEMENTATION_FREEZE_SHA256 = (
    "264c207abe3149d1b4083609a275da26e74d97fcc0bdc8dccde076a1fa847205"
)

if runner._sha256(runner.Path(runner.__file__).resolve()) != EXPECTED_RUNNER_SHA256:
    raise runner.Campaign050FeatureError("Campaign050 frozen feature runner changed")

runner.IMPLEMENTATION_FREEZE_SHA256 = EXPECTED_IMPLEMENTATION_FREEZE_SHA256
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(runner.main())
