#!/usr/bin/env python3
"""Empty-joint-base-repaired Campaign050 feature entrypoint."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign050_features_v2 as frozen
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign050_features_v2 as frozen


runner = frozen.runner
REPAIR_AUTHORIZATION = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_050_feature_build_infrastructure_repair_20260801.json"
)
EXPECTED_FROZEN_ENTRYPOINT_SHA256 = (
    "f450a953e44f4a9fd325d1aea7dc113dbd84fa9079761079ac6a1fa9a3292b97"
)
EXPECTED_REPAIR_AUTHORIZATION_SHA256 = (
    "4e514d9283ffd2e3878aa0b9d7bf0625ca45f3b13b8f08ab006f934667ea5443"
)

if (
    runner._sha256(runner.Path(frozen.__file__).resolve())
    != EXPECTED_FROZEN_ENTRYPOINT_SHA256
):
    raise runner.Campaign050FeatureError("Campaign050 frozen v2 entrypoint changed")
if runner._sha256(REPAIR_AUTHORIZATION) != EXPECTED_REPAIR_AUTHORIZATION_SHA256:
    raise runner.Campaign050FeatureError(
        "Campaign050 empty-joint-base repair authorization changed"
    )

_frozen_compute_partition_frame = runner.compute_partition_frame


def compute_partition_frame(
    raw: runner.pd.DataFrame,
    base_frame: runner.pd.DataFrame,
    benchmark: object,
    *,
    symbol: str,
) -> tuple[runner.pd.DataFrame, dict[str, int]]:
    """Return canonically empty output for an intentionally empty joint base."""

    if tuple(raw.columns) != runner.RAW_COLUMNS:
        raise runner.Campaign050FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != runner.BASE_COLUMNS:
        raise runner.Campaign050FeatureError(
            f"unexpected joint-base columns for {symbol}: {tuple(base_frame.columns)}"
        )
    base_work = base_frame.copy()
    base_work["trade_date"] = runner.pd.to_datetime(
        base_work["trade_date"], errors="coerce"
    ).dt.normalize()
    if base_work.empty:
        return runner.empty_output_frame(), {"base_rows": 0}
    return _frozen_compute_partition_frame(
        raw, base_frame, benchmark, symbol=symbol
    )


runner.compute_partition_frame = compute_partition_frame
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(runner.main())
