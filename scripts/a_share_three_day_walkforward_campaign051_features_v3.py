#!/usr/bin/env python3
"""Snapshot-publication-bound Campaign051 no-return audit entrypoint."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign051_features_v2 as built
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign051_features_v2 as built


runner = built.runner
EXPECTED_BUILD_ENTRYPOINT_SHA256 = (
    "ee05356df8f6cac5c4f26c5d65c8ab2ca813f3789d4415518f7435c9ccdbc930"
)
EXPECTED_SNAPSHOT_PUBLICATION_BINDING_SHA256 = (
    "f24916ca77a05ba7c988777b5d85656afae004d0034f1c44c060ad4bfbf81526"
)
EXPECTED_SNAPSHOT_MANIFEST_SHA256 = (
    "13a2b7862cb2118dd8e42bcd94653973de603d840bd09f0762be219b840f032e"
)
EXPECTED_SNAPSHOT_DATASET_SHA256 = (
    "2930b47c228f3e033f8130d9960e55668e688e02ba020a02d02ffa60987cabbd"
)

if (
    runner._sha256(runner.Path(built.__file__).resolve())
    != EXPECTED_BUILD_ENTRYPOINT_SHA256
):
    raise runner.Campaign051FeatureError("Campaign051 frozen v2 entrypoint changed")
if (
    runner._sha256(runner.DEFAULT_SNAPSHOT_BINDING)
    != EXPECTED_SNAPSHOT_PUBLICATION_BINDING_SHA256
):
    raise runner.Campaign051FeatureError(
        "Campaign051 snapshot publication binding changed"
    )

runner.SNAPSHOT_MANIFEST_SHA256 = EXPECTED_SNAPSHOT_MANIFEST_SHA256
runner.SNAPSHOT_DATASET_SHA256 = EXPECTED_SNAPSHOT_DATASET_SHA256
runner.SNAPSHOT_PUBLICATION_BINDING_SHA256 = (
    EXPECTED_SNAPSHOT_PUBLICATION_BINDING_SHA256
)
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(runner.main())
