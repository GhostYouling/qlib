#!/usr/bin/env python3
"""Authorized Campaign055 implementation-freeze semantic-path repair."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import scripts.a_share_three_day_walkforward_campaign055_features_v2 as failed
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign055_features_v2 as failed


runner = failed.runner
FAILURE_RECORD = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_055_implementation_freeze_semantic_path_failure_20260804.json"
)
EXPECTED_FAILED_WRAPPER_SHA256 = (
    "3c07d8d294846f8e3508d69e010baa8a8ea07997281ce96194dad19141be97e1"
)
EXPECTED_FAILURE_RECORD_SHA256 = (
    "820497ae38b2d9404b3c52c546aab9e98a06bc59ce508e0661aa57629e7974b2"
)

if runner._sha256(Path(failed.__file__).resolve()) != EXPECTED_FAILED_WRAPPER_SHA256:
    raise runner.Campaign055FeatureError(
        "Campaign055 failed v2 wrapper changed"
    )
runner._require_file(
    FAILURE_RECORD,
    EXPECTED_FAILURE_RECORD_SHA256,
    "Campaign055 semantic-path failure authorization",
)


def load_implementation_freeze() -> dict[str, Any]:
    """Validate the immutable freeze's truthful nested pre-value evidence."""

    runner._require_file(
        runner.DEFAULT_IMPLEMENTATION_FREEZE,
        failed.EXPECTED_IMPLEMENTATION_FREEZE_SHA256,
        "Campaign055 implementation freeze",
    )
    record = json.loads(
        runner.DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8")
    )
    feature_runner = record.get("feature_runner") or {}
    protocol = record.get("no_return_protocol") or {}
    evidence = record.get("pre_freeze_execution_evidence") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign055_feature_implementation_freeze"
        and record.get("status") == "frozen_before_campaign055_candidate_values"
        and Path(str(feature_runner.get("path"))).resolve()
        == Path(runner.__file__).resolve()
        and feature_runner.get("sha256")
        == runner._sha256(Path(runner.__file__).resolve())
        and protocol.get("sha256") == runner.PROTOCOL_SHA256
        and evidence.get("candidate_values_read_before_freeze") is False
        and evidence.get("comparison_values_read_before_freeze") is False
        and evidence.get(
            "historical_daily_price_or_forward_returns_read_before_freeze"
        )
        is False
        and evidence.get("provider_request_issued_before_freeze") is False
        and evidence.get("external_campaign055_snapshot_manifest_present") is False
        and evidence.get("campaign055_experiment_artifact_count") == 0
    ):
        raise runner.Campaign055FeatureError(
            "Campaign055 repaired implementation freeze semantics changed"
        )
    return record


runner._load_implementation_freeze = load_implementation_freeze
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(runner.main())
