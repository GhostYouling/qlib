#!/usr/bin/env python3
"""Exact-schema Campaign051 verifier repair for Campaign053 no-return audit."""

from __future__ import annotations

import concurrent.futures
from pathlib import Path
from typing import Any

import pandas as pd

try:
    import scripts.a_share_three_day_walkforward_campaign053_features_v3 as failed
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign053_features_v3 as failed


runner = failed.runner
REPAIR_AUTHORIZATION = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_053_no_return_audit_campaign051_verifier_failure_repair_20260803.json"
)
EXPECTED_FAILED_ENTRYPOINT_SHA256 = (
    "e561a78f3409df7746b30e381ac752d33edbf6d8d24831d8cfae99b98d7a1608"
)
EXPECTED_REPAIR_AUTHORIZATION_SHA256 = (
    "f70412a025886ef117eac7b9568a438c7edfdb3a4bf0ec5021f4017b300da20a"
)
EXPECTED_C51_SNAPSHOT_PATH = runner.previous.C51_SNAPSHOT_PATH.resolve()
EXPECTED_C51_MANIFEST_SHA256 = runner.previous.C51_SNAPSHOT_SHA256
EXPECTED_C51_DATASET_SHA256 = runner.previous.C51_DATASET_SHA256
EXPECTED_C51_KIND = "a_share_three_day_walkforward_campaign051_feature_snapshot"
EXPECTED_C51_PARTITIONS = 33015
EXPECTED_C51_ROWS = 7724498
C51_FACTOR_NAME = runner.previous.C51_FACTOR_NAME
C51_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C51_FACTOR_NAME,
    f"{C51_FACTOR_NAME}_eligible",
)


if runner._sha256(Path(failed.__file__).resolve()) != EXPECTED_FAILED_ENTRYPOINT_SHA256:
    raise runner.Campaign053FeatureError("Campaign053 frozen v3 entrypoint changed")
if runner._sha256(REPAIR_AUTHORIZATION) != EXPECTED_REPAIR_AUTHORIZATION_SHA256:
    raise runner.Campaign053FeatureError(
        "Campaign053 Campaign051-verifier repair authorization changed"
    )


def verify_campaign051_snapshot_files(
    manifest: dict[str, Any], manifest_path: Path, workers: int
) -> dict[str, Any]:
    """Verify Campaign051 bytes and frames without shared engine globals."""

    manifest_path = manifest_path.expanduser().resolve()
    if manifest_path != EXPECTED_C51_SNAPSHOT_PATH:
        raise runner.Campaign053FeatureError(
            "Campaign051 repair verifier received another snapshot"
        )
    if runner._sha256(manifest_path) != EXPECTED_C51_MANIFEST_SHA256:
        raise runner.Campaign053FeatureError("Campaign051 snapshot manifest changed")
    if not (
        manifest.get("kind") == EXPECTED_C51_KIND
        and manifest.get("dataset_sha256") == EXPECTED_C51_DATASET_SHA256
    ):
        raise runner.Campaign053FeatureError("Campaign051 snapshot identity changed")
    records = list(manifest.get("files") or [])
    if len(records) != EXPECTED_C51_PARTITIONS:
        raise runner.Campaign053FeatureError("Campaign051 partition count changed")
    if workers < 1:
        raise runner.Campaign053FeatureError("workers must be positive")
    root = (manifest_path.parent / "partitions").resolve()
    _, foundation, _, _, _, _ = runner.campaign044._context()

    def verify(record: dict[str, Any]) -> int:
        path = Path(str(record["path"])).expanduser().resolve()
        if path.parent.parent != root:
            raise runner.Campaign053FeatureError(
                f"Campaign051 snapshot partition escapes root: {path}"
            )
        if runner._sha256(path) != str(record["output_byte_sha256"]):
            raise runner.Campaign053FeatureError(
                f"Campaign051 snapshot partition bytes changed: {path}"
            )
        frame = pd.read_parquet(path, columns=list(C51_OUTPUT_COLUMNS))
        if (
            tuple(frame.columns) != C51_OUTPUT_COLUMNS
            or len(frame) != int(record["rows"])
            or foundation.frame_digest(frame) != str(record["output_frame_sha256"])
        ):
            raise runner.Campaign053FeatureError(
                f"Campaign051 snapshot partition frame changed: {path}"
            )
        return len(frame)

    counts: list[int] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for index, count in enumerate(pool.map(verify, records), start=1):
            counts.append(count)
            if index % 5000 == 0 or index == len(records):
                print(
                    f"verified Campaign051 repair partitions {index}/{len(records)}",
                    flush=True,
                )
    if len(counts) != EXPECTED_C51_PARTITIONS or sum(counts) != EXPECTED_C51_ROWS:
        raise runner.Campaign053FeatureError("Campaign051 snapshot aggregate changed")
    return {
        "verified_partitions": len(counts),
        "verified_rows": sum(counts),
        "all_partition_byte_and_frame_hashes_valid": True,
        "isolated_exact_campaign051_output_columns": list(C51_OUTPUT_COLUMNS),
    }


runner.previous.previous.verify_snapshot_files = verify_campaign051_snapshot_files


if __name__ == "__main__":
    raise SystemExit(runner.main())
