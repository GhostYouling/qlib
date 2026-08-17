#!/usr/bin/env python3
"""Snapshot-bound Campaign048 ordered no-return audit entrypoint."""

from __future__ import annotations

import json

import scripts.a_share_three_day_walkforward_campaign048_features as runner


EXPECTED_RUNNER_SHA256 = "2b7a19cda2d4d6371182e121ca3e265f5b124e2d7b5fe9d3940e4686a09b0cfa"
EXPECTED_IMPLEMENTATION_FREEZE_SHA256 = "5c746c68fb9c46e2555e6764bf502e17d44f459673dd2348d0736e24895b32c6"
EXPECTED_SNAPSHOT_MANIFEST_SHA256 = "49e5f7f83e8a5a4d34deb494602c8582da9dc645a0f7e5c8aef6ef824a3bc017"
EXPECTED_SNAPSHOT_DATASET_SHA256 = "d294401092beb8e8cd0b84c1991e3ba5a158318cdab4b63c4920120fafe9db1b"
EXPECTED_SNAPSHOT_BINDING_SHA256 = "e09fa6fde19013a52925244d20961dc035b97ffb238e55e710df2384c4f65b4a"
CLARIFICATION = runner.REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_inherited_protocol_evidence_clarification_20260801.json"
EXPECTED_CLARIFICATION_SHA256 = "5afc9b1dc28693fcd0952739afd1a481da7085a125928990a58ddbee8a64b3ed"

if runner._sha256(runner.Path(runner.__file__).resolve()) != EXPECTED_RUNNER_SHA256:
    raise runner.Campaign048FeatureError("Campaign048 frozen feature runner changed")
if runner._sha256(CLARIFICATION) != EXPECTED_CLARIFICATION_SHA256:
    raise runner.Campaign048FeatureError("Campaign048 inherited metadata clarification changed")
clarification = json.loads(CLARIFICATION.read_text(encoding="utf-8"))
if not (
    clarification.get("status") == "additive_metadata_clarification_snapshot_bytes_and_values_unchanged"
    and clarification.get("decision", {}).get("canonical_campaign048_bindings_valid") is True
    and clarification.get("effect", {}).get("comparison_values_read_before_clarification") is False
):
    raise runner.Campaign048FeatureError("Campaign048 metadata clarification semantics changed")

runner.IMPLEMENTATION_FREEZE_SHA256 = EXPECTED_IMPLEMENTATION_FREEZE_SHA256
runner.SNAPSHOT_MANIFEST_SHA256 = EXPECTED_SNAPSHOT_MANIFEST_SHA256
runner.SNAPSHOT_DATASET_SHA256 = EXPECTED_SNAPSHOT_DATASET_SHA256
runner.SNAPSHOT_PUBLICATION_BINDING_SHA256 = EXPECTED_SNAPSHOT_BINDING_SHA256


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
