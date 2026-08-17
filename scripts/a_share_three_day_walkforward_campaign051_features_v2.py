#!/usr/bin/env python3
"""Implementation-freeze-bound Campaign051 feature entrypoint."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign051_features as runner
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign051_features as runner


EXPECTED_RUNNER_SHA256 = (
    "091642ad8e678b6d9e99bc227045ca89d63f7b6b7317ab239e4a55401507a6f2"
)
EXPECTED_IMPLEMENTATION_FREEZE_SHA256 = (
    "7721ecac1ea54a12f4ed1f16a71be962205c983cf4a7462602c68c8131a6b688"
)

if runner._sha256(runner.Path(runner.__file__).resolve()) != EXPECTED_RUNNER_SHA256:
    raise runner.Campaign051FeatureError("Campaign051 frozen feature runner changed")

runner.IMPLEMENTATION_FREEZE_SHA256 = EXPECTED_IMPLEMENTATION_FREEZE_SHA256
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(runner.main())
