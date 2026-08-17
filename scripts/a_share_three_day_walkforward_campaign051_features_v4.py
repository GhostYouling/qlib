#!/usr/bin/env python3
"""Exact-schema Campaign050 verifier repair for Campaign051 no-return audit."""

from __future__ import annotations

import concurrent.futures
import json
from pathlib import Path
from typing import Any

import pandas as pd

try:
    import scripts.a_share_three_day_walkforward_campaign051_features_v3 as failed
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign051_features_v3 as failed


runner = failed.runner
REPAIR_AUTHORIZATION = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_051_no_return_audit_campaign050_verifier_failure_repair_20260803.json"
)
EXPECTED_FAILED_ENTRYPOINT_SHA256 = (
    "178479da821a780773550d66f97193403dc4238601fb034d7cab24e02f24c0a9"
)
EXPECTED_REPAIR_AUTHORIZATION_SHA256 = (
    "da97b374f28c8538e515781765ab72923853832840d26d846e12834b2d532648"
)
EXPECTED_C50_ENTRYPOINT = (
    runner.REPO_ROOT
    / "scripts/a_share_three_day_walkforward_campaign050_features_v8.py"
)
EXPECTED_C50_ENTRYPOINT_SHA256 = (
    "79bba06d0d621d2a415271b8096548706ecd871cc380f233c8ea2f3f1596a5d9"
)
EXPECTED_C50_SNAPSHOT_PATH = runner.C50_SNAPSHOT_PATH.resolve()
EXPECTED_C50_MANIFEST_SHA256 = runner.C50_SNAPSHOT_SHA256
EXPECTED_C50_DATASET_SHA256 = runner.C50_DATASET_SHA256
EXPECTED_C50_KIND = "a_share_three_day_walkforward_campaign050_feature_snapshot"
EXPECTED_C50_PARTITIONS = 33015
EXPECTED_C50_ROWS = 7724498
C50_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    runner.C50_FACTOR_NAME,
    f"{runner.C50_FACTOR_NAME}_eligible",
)


if runner._sha256(Path(failed.__file__).resolve()) != EXPECTED_FAILED_ENTRYPOINT_SHA256:
    raise runner.Campaign051FeatureError("Campaign051 frozen v3 entrypoint changed")
if runner._sha256(REPAIR_AUTHORIZATION) != EXPECTED_REPAIR_AUTHORIZATION_SHA256:
    raise runner.Campaign051FeatureError(
        "Campaign051 Campaign050-verifier repair authorization changed"
    )
if runner._sha256(EXPECTED_C50_ENTRYPOINT) != EXPECTED_C50_ENTRYPOINT_SHA256:
    raise runner.Campaign051FeatureError("frozen Campaign050 entrypoint changed")


def verify_campaign050_snapshot_files(
    manifest: dict[str, Any], manifest_path: Path, workers: int
) -> dict[str, Any]:
    """Verify Campaign050 bytes and frames without shared engine globals."""

    manifest_path = manifest_path.expanduser().resolve()
    if manifest_path != EXPECTED_C50_SNAPSHOT_PATH:
        raise runner.Campaign051FeatureError(
            "Campaign050 repair verifier received another snapshot"
        )
    if runner._sha256(manifest_path) != EXPECTED_C50_MANIFEST_SHA256:
        raise runner.Campaign051FeatureError("Campaign050 snapshot manifest changed")
    if not (
        manifest.get("kind") == EXPECTED_C50_KIND
        and manifest.get("dataset_sha256") == EXPECTED_C50_DATASET_SHA256
    ):
        raise runner.Campaign051FeatureError("Campaign050 snapshot identity changed")
    records = list(manifest.get("files") or [])
    if len(records) != EXPECTED_C50_PARTITIONS:
        raise runner.Campaign051FeatureError("Campaign050 partition count changed")
    if workers < 1:
        raise runner.Campaign051FeatureError("workers must be positive")
    root = (manifest_path.parent / "partitions").resolve()
    _, foundation, _, _, _, _ = runner.campaign044._context()

    def verify(record: dict[str, Any]) -> int:
        path = Path(str(record["path"])).expanduser().resolve()
        if path.parent.parent != root:
            raise runner.Campaign051FeatureError(
                f"Campaign050 snapshot partition escapes root: {path}"
            )
        if runner._sha256(path) != str(record["output_byte_sha256"]):
            raise runner.Campaign051FeatureError(
                f"Campaign050 snapshot partition bytes changed: {path}"
            )
        frame = pd.read_parquet(path, columns=list(C50_OUTPUT_COLUMNS))
        if (
            tuple(frame.columns) != C50_OUTPUT_COLUMNS
            or len(frame) != int(record["rows"])
            or foundation.frame_digest(frame) != str(record["output_frame_sha256"])
        ):
            raise runner.Campaign051FeatureError(
                f"Campaign050 snapshot partition frame changed: {path}"
            )
        return len(frame)

    counts: list[int] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for index, count in enumerate(pool.map(verify, records), start=1):
            counts.append(count)
            if index % 5000 == 0 or index == len(records):
                print(
                    f"verified Campaign050 repair partitions {index}/{len(records)}",
                    flush=True,
                )
    if len(counts) != EXPECTED_C50_PARTITIONS or sum(counts) != EXPECTED_C50_ROWS:
        raise runner.Campaign051FeatureError("Campaign050 snapshot aggregate changed")
    return {
        "verified_partitions": len(counts),
        "verified_rows": sum(counts),
        "all_partition_byte_and_frame_hashes_valid": True,
        "isolated_exact_campaign050_output_columns": list(C50_OUTPUT_COLUMNS),
    }


runner.previous.verify_snapshot_files = verify_campaign050_snapshot_files


if __name__ == "__main__":
    raise SystemExit(runner.main())
