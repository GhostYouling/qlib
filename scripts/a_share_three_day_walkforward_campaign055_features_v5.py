#!/usr/bin/env python3
"""Authorized Campaign055 v2 snapshot protocol-evidence repair."""

from __future__ import annotations

import re
from pathlib import Path

try:
    import scripts.a_share_three_day_walkforward_campaign055_features_v4 as frozen
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign055_features_v4 as frozen


runner = frozen.runner
REPAIR_AUTHORIZATION = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_055_snapshot_v1_protocol_evidence_failure_repair_20260804.json"
)
FAILED_V1_SNAPSHOT = (
    runner.DEFAULT_DATA_ROOT
    / "derived/a_share/rich/tushare/minute_walkforward_campaign055_feature_library"
    / runner.OUTPUT_RUN_ID
    / "snapshot_manifest.json"
)
REPAIRED_OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign055_feature_library_v2"
)
EXPECTED_FROZEN_V4_SHA256 = (
    "0ed81a3883cd00bf072972c431f49a6d17fc3e9a8ff5028afeffb85c9aaa60af"
)
EXPECTED_REPAIR_AUTHORIZATION_SHA256 = (
    "d6c3172a082fb2bb607431fd82dbba30a513851b1bc04259269dff3b19131c49"
)
EXPECTED_FAILED_V1_SNAPSHOT_SHA256 = (
    "6cbdfafb216c3064271c8eba301ce85dfa2ed27d14afb4073e96aff62be445b6"
)

if runner._sha256(Path(frozen.__file__).resolve()) != EXPECTED_FROZEN_V4_SHA256:
    raise runner.Campaign055FeatureError(
        "Campaign055 frozen v4 snapshot entrypoint changed"
    )
runner._require_file(
    REPAIR_AUTHORIZATION,
    EXPECTED_REPAIR_AUTHORIZATION_SHA256,
    "Campaign055 v1 protocol-evidence repair authorization",
)
runner._require_file(
    FAILED_V1_SNAPSHOT,
    EXPECTED_FAILED_V1_SNAPSHOT_SHA256,
    "Campaign055 failed v1 snapshot",
)


def output_root(data_root: Path) -> Path:
    return (
        data_root.expanduser().resolve()
        / "derived/a_share/rich/tushare/minute_walkforward_campaign055_feature_library"
        / REPAIRED_OUTPUT_RUN_ID
    )


def clean_protocol_evidence(evidence: dict[str, object]) -> dict[str, object]:
    """Keep Candidate49 and current Campaign055 evidence only."""

    return {
        key: value
        for key, value in evidence.items()
        if not re.match(r"^campaign\d{3}_", key)
        or key.startswith("campaign055_")
    }


_base_validate_snapshot_manifest = runner._validate_snapshot_manifest


def validate_snapshot_manifest(
    manifest: dict[str, object], *, require_fingerprint_constants: bool
) -> None:
    _base_validate_snapshot_manifest(
        manifest,
        require_fingerprint_constants=require_fingerprint_constants,
    )
    evidence = dict(manifest.get("protocol_evidence") or {})
    if not require_fingerprint_constants:
        evidence = clean_protocol_evidence(evidence)
        manifest["protocol_evidence"] = evidence
    stale = [
        key
        for key in evidence
        if re.match(r"^campaign\d{3}_", key)
        and not key.startswith("campaign055_")
    ]
    if stale:
        raise runner.Campaign055FeatureError(
            "Campaign055 snapshot retained stale numbered-campaign evidence"
        )


runner.OUTPUT_RUN_ID = REPAIRED_OUTPUT_RUN_ID
runner.output_root = output_root
runner._validate_snapshot_manifest = validate_snapshot_manifest
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(runner.main())
