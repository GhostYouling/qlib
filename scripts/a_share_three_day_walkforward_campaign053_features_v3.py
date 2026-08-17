#!/usr/bin/env python3
"""Fingerprint-bound Campaign053 no-return runner after snapshot publication."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign053_features_v2 as frozen
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign053_features_v2 as frozen


runner = frozen.runner
EXPECTED_V2_ENTRYPOINT_SHA256 = "10fd4c43d0af5274154bde1965196d7f55cbbe2b35d4deeb0cef9b9ecf49c24a"
EXPECTED_SNAPSHOT_MANIFEST_SHA256 = "e0f0e9176580e9e6216049d026ab360aea0904e5d1db57d61311fe6da7d3c402"
EXPECTED_SNAPSHOT_DATASET_SHA256 = "d56d8628608faf32c97fb374cb05d06bfa0182d87f2d0467f5a08bca8c3f0f87"
EXPECTED_SNAPSHOT_BINDING_SHA256 = "0bef2d554baad10c90a1be00e126ba92a76e7bc7625cbd88501d60d386a2350a"

if runner._sha256(runner.Path(frozen.__file__).resolve()) != EXPECTED_V2_ENTRYPOINT_SHA256:
    raise runner.Campaign053FeatureError("Campaign053 frozen v2 entrypoint changed")
if runner._sha256(runner.DEFAULT_SNAPSHOT_BINDING) != EXPECTED_SNAPSHOT_BINDING_SHA256:
    raise runner.Campaign053FeatureError("Campaign053 snapshot binding changed")

runner.SNAPSHOT_MANIFEST_SHA256 = EXPECTED_SNAPSHOT_MANIFEST_SHA256
runner.SNAPSHOT_DATASET_SHA256 = EXPECTED_SNAPSHOT_DATASET_SHA256
runner.SNAPSHOT_PUBLICATION_BINDING_SHA256 = EXPECTED_SNAPSHOT_BINDING_SHA256
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(runner.main())
