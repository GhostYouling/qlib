#!/usr/bin/env python3
"""Implementation-freeze-bound Campaign049 feature entrypoint."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign049_features as runner
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign049_features as runner


EXPECTED_RUNNER_SHA256 = (
    "981378510744bb53bb5353d1bf99ca9850b4f10c49bd8500d38d29994bdeff83"
)
EXPECTED_IMPLEMENTATION_FREEZE_SHA256 = (
    "3f3cb1ff92d3c3d7a50ff285122ba2f77531b89f35a97eb226b078e63810181b"
)

if runner._sha256(runner.Path(runner.__file__).resolve()) != EXPECTED_RUNNER_SHA256:
    raise runner.Campaign049FeatureError("Campaign049 frozen feature runner changed")

runner.IMPLEMENTATION_FREEZE_SHA256 = EXPECTED_IMPLEMENTATION_FREEZE_SHA256


def campaign049_output_root(data_root: runner.Path) -> runner.Path:
    return (
        data_root.expanduser().resolve()
        / "derived/a_share/rich/tushare/minute_walkforward_campaign049_feature_library"
        / runner.OUTPUT_RUN_ID
    )


runner.output_root = campaign049_output_root
runner._generated["output_root"] = campaign049_output_root
runner._engine_globals["output_root"] = campaign049_output_root
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(runner.main())
