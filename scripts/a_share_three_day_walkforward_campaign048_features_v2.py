#!/usr/bin/env python3
"""Implementation-freeze-bound Campaign048 feature build entrypoint."""

from __future__ import annotations

import scripts.a_share_three_day_walkforward_campaign048_features as runner


EXPECTED_RUNNER_SHA256 = "2b7a19cda2d4d6371182e121ca3e265f5b124e2d7b5fe9d3940e4686a09b0cfa"
EXPECTED_IMPLEMENTATION_FREEZE_SHA256 = "5c746c68fb9c46e2555e6764bf502e17d44f459673dd2348d0736e24895b32c6"

if runner._sha256(runner.Path(runner.__file__).resolve()) != EXPECTED_RUNNER_SHA256:
    raise runner.Campaign048FeatureError("Campaign048 frozen feature runner changed")

runner.IMPLEMENTATION_FREEZE_SHA256 = EXPECTED_IMPLEMENTATION_FREEZE_SHA256


def campaign048_output_root(data_root: runner.Path) -> runner.Path:
    return (
        data_root.expanduser().resolve()
        / "derived/a_share/rich/tushare/minute_walkforward_campaign048_feature_library"
        / runner.OUTPUT_RUN_ID
    )


runner.output_root = campaign048_output_root
runner._generated["output_root"] = campaign048_output_root
runner._engine_globals["output_root"] = campaign048_output_root
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(runner.main())
