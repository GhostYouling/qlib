#!/usr/bin/env python3
"""Exact Candidate49 EINTR repair for Campaign051 no-return audit."""

from __future__ import annotations

import errno
from pathlib import Path
from typing import Any, Iterable

import numpy as np

try:
    import scripts.a_share_three_day_walkforward_campaign051_features_v5 as failed
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign051_features_v5 as failed


runner = failed.runner
REPAIR_AUTHORIZATION = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_051_no_return_audit_candidate49_eintr_failure_repair_20260803.json"
)
EXPECTED_FAILED_ENTRYPOINT_SHA256 = (
    "0bbea654a68354ab8df3f919037d4deb452b9fe64615467bb2b0076f6a166023"
)
EXPECTED_REPAIR_AUTHORIZATION_SHA256 = (
    "f85f187014638ae23260bd0fb8dc342641b6029d25d5e4c5840d271b72885fae"
)
EXPECTED_C49_KIND = (
    "a_share_tushare_intraday_cumulative_vwap_crossing_rate_snapshot"
)
EXPECTED_C49_FACTOR = "intraday_cumulative_vwap_crossing_rate_240m"
EXPECTED_C49_MANIFEST_SHA256 = (
    "f3dd3417bd6adcaa06d8927865ea3f464ebc02df302b8f488e43450f7c620196"
)
EXPECTED_C49_DATASET_SHA256 = (
    "67bda6df74747a0f39fe6eb252aada84ea7850fff2c05bdae4951aa41fcc7037"
)
EXPECTED_C49_PARTITIONS = 33_015
EXPECTED_C49_ROWS = 7_724_498

if runner._sha256(Path(failed.__file__).resolve()) != EXPECTED_FAILED_ENTRYPOINT_SHA256:
    raise runner.Campaign051FeatureError("Campaign051 frozen v5 entrypoint changed")
if runner._sha256(REPAIR_AUTHORIZATION) != EXPECTED_REPAIR_AUTHORIZATION_SHA256:
    raise runner.Campaign051FeatureError(
        "Campaign051 Candidate49 EINTR repair authorization changed"
    )

_, _, engine, _, candidate49, _ = runner.campaign044._context()
if not (
    candidate49.FACTOR_NAME == EXPECTED_C49_FACTOR
    and candidate49.CANDIDATE_MANIFEST_SHA256 == EXPECTED_C49_MANIFEST_SHA256
    and candidate49.CANDIDATE_DATASET_SHA256 == EXPECTED_C49_DATASET_SHA256
):
    raise runner.Campaign051FeatureError("frozen Candidate49 identity changed")

ORIGINAL_EXPLICIT_LOADER = engine._load_filtered_comparison_values_explicit


def _is_exact_candidate49_request(
    manifest: dict[str, Any], factors: Iterable[str]
) -> bool:
    factor_tuple = tuple(str(value) for value in factors)
    return bool(
        factor_tuple == (EXPECTED_C49_FACTOR,)
        and manifest.get("kind") == EXPECTED_C49_KIND
        and manifest.get("dataset_sha256") == EXPECTED_C49_DATASET_SHA256
        and manifest.get("factor_name") == EXPECTED_C49_FACTOR
        and manifest.get("partitions") == EXPECTED_C49_PARTITIONS
        and manifest.get("rows") == EXPECTED_C49_ROWS
        and len(list(manifest.get("files") or [])) == EXPECTED_C49_PARTITIONS
    )


def load_filtered_comparison_values_with_candidate49_eintr_retry(
    manifest: dict[str, Any],
    factors: Iterable[str],
    candidate_keys: np.ndarray,
) -> dict[str, np.ndarray]:
    """Retry one exact Candidate49 load after a transient POSIX EINTR."""

    factor_tuple = tuple(str(value) for value in factors)
    try:
        return ORIGINAL_EXPLICIT_LOADER(manifest, factor_tuple, candidate_keys)
    except InterruptedError as exc:
        if exc.errno != errno.EINTR or not _is_exact_candidate49_request(
            manifest, factor_tuple
        ):
            raise
    return ORIGINAL_EXPLICIT_LOADER(manifest, factor_tuple, candidate_keys)


engine._load_filtered_comparison_values_explicit = (
    load_filtered_comparison_values_with_candidate49_eintr_retry
)


if __name__ == "__main__":
    raise SystemExit(runner.main())
