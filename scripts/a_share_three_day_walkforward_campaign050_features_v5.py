#!/usr/bin/env python3
"""Snapshot-publication-bound Campaign050 no-return audit entrypoint."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign050_features_v4 as built
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign050_features_v4 as built


runner = built.runner
EXPECTED_BUILD_ENTRYPOINT_SHA256 = (
    "f06f14ef38b33eeacce83d10b4aaa44c2d15889707d3a16959620f7afea2788d"
)
EXPECTED_SNAPSHOT_PUBLICATION_BINDING_SHA256 = (
    "f6e1ea181f52a0137ba0f2d03718e9f393cc98a2ecb322dd7c4d89c5f4d651d6"
)
EXPECTED_SNAPSHOT_MANIFEST_SHA256 = (
    "8e95728fd9e1ba3d3ab820dbf5d92812bd18f9076ee901ee80cd76cf989300ef"
)
EXPECTED_SNAPSHOT_DATASET_SHA256 = (
    "d758c059ff6fb602106c240c369d5d3db60eb245ec7cccf23d5a32b9f69dec8a"
)

if (
    runner._sha256(runner.Path(built.__file__).resolve())
    != EXPECTED_BUILD_ENTRYPOINT_SHA256
):
    raise runner.Campaign050FeatureError("Campaign050 frozen v4 entrypoint changed")
if (
    runner._sha256(runner.DEFAULT_SNAPSHOT_BINDING)
    != EXPECTED_SNAPSHOT_PUBLICATION_BINDING_SHA256
):
    raise runner.Campaign050FeatureError(
        "Campaign050 snapshot publication binding changed"
    )

runner.SNAPSHOT_MANIFEST_SHA256 = EXPECTED_SNAPSHOT_MANIFEST_SHA256
runner.SNAPSHOT_DATASET_SHA256 = EXPECTED_SNAPSHOT_DATASET_SHA256
runner.SNAPSHOT_PUBLICATION_BINDING_SHA256 = (
    EXPECTED_SNAPSHOT_PUBLICATION_BINDING_SHA256
)
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(runner.main())
