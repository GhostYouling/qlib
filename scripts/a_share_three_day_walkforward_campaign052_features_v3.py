#!/usr/bin/env python3
"""Fingerprint-bound Campaign052 no-return runner after snapshot publication."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign052_features_v2 as frozen
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign052_features_v2 as frozen


runner = frozen.runner
EXPECTED_V2_ENTRYPOINT_SHA256 = (
    "0d1113e04f4656b0d90a7595a7edc2c1049d97a32136760d922f6c10d52dc810"
)
EXPECTED_SNAPSHOT_MANIFEST_SHA256 = (
    "04547981bed8a78438d7988296f1b3887a7d67b6604df555b207fac0b85a26c4"
)
EXPECTED_SNAPSHOT_DATASET_SHA256 = (
    "f9a6f08060c60c2183c587d6008ffa20f76735bdef46a989f02dff6ecba1a30e"
)
EXPECTED_SNAPSHOT_BINDING_SHA256 = (
    "8903320a59e651bee9f188a29ee9765cb206e7a26c8e7cd98baa9fef478d6d4d"
)

if runner._sha256(runner.Path(frozen.__file__).resolve()) != EXPECTED_V2_ENTRYPOINT_SHA256:
    raise runner.Campaign052FeatureError("Campaign052 frozen v2 entrypoint changed")
if (
    runner._sha256(runner.DEFAULT_SNAPSHOT_BINDING)
    != EXPECTED_SNAPSHOT_BINDING_SHA256
):
    raise runner.Campaign052FeatureError("Campaign052 snapshot binding changed")

runner.SNAPSHOT_MANIFEST_SHA256 = EXPECTED_SNAPSHOT_MANIFEST_SHA256
runner.SNAPSHOT_DATASET_SHA256 = EXPECTED_SNAPSHOT_DATASET_SHA256
runner.SNAPSHOT_PUBLICATION_BINDING_SHA256 = EXPECTED_SNAPSHOT_BINDING_SHA256
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(runner.main())
