"""Focused tests for the Campaign053 Campaign051-verifier repair."""

from __future__ import annotations

import subprocess
import sys
import textwrap


def test_campaign053_repair_replaces_only_campaign051_verifier() -> None:
    code = """
import scripts.a_share_three_day_walkforward_campaign053_features_v4 as repair
sources = repair.runner.previous._extra_comparison_sources()
assert sources[-1][0] == "campaign051"
assert sources[-1][5].verify_snapshot_files is repair.verify_campaign051_snapshot_files
assert repair.runner.previous.previous.verify_snapshot_files is repair.verify_campaign051_snapshot_files
assert repair.C51_OUTPUT_COLUMNS == (
    "trade_date",
    "symbol",
    "provider",
    "intraday_close_range_occupancy_entropy_10b",
    "intraday_close_range_occupancy_entropy_10b_eligible",
)
assert repair.runner.COMPARISON_COUNT == 76
assert repair.runner.COMPARISON_ORDER_SHA256 == "e0740ee631eabfd281b5819379829feaabcd18910ab76a94623d3098d1e0b62e"
"""
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_campaign053_repair_verifies_exact_campaign051_schema() -> None:
    code = r"""
import hashlib
import json
import tempfile
from pathlib import Path

import pandas as pd
import scripts.a_share_three_day_walkforward_campaign053_features_v4 as repair

def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

with tempfile.TemporaryDirectory() as temp:
    factor = repair.C51_FACTOR_NAME
    root = Path(temp) / "snapshot"
    partition = root / "partitions" / "SZ000001" / "2021.parquet"
    partition.parent.mkdir(parents=True)
    frame = pd.DataFrame({
        "trade_date": pd.to_datetime(["2021-01-04", "2021-01-05"]),
        "symbol": ["SZ000001", "SZ000001"],
        "provider": ["tushare", "tushare"],
        factor: [0.25, 0.75],
        f"{factor}_eligible": [True, True],
    }).loc[:, repair.C51_OUTPUT_COLUMNS]
    frame.to_parquet(partition, index=False)
    _, foundation, _, _, _, _ = repair.runner.campaign044._context()
    manifest = {
        "kind": repair.EXPECTED_C51_KIND,
        "dataset_sha256": "synthetic-dataset",
        "files": [{
            "path": str(partition.resolve()),
            "rows": len(frame),
            "output_byte_sha256": sha256(partition),
            "output_frame_sha256": foundation.frame_digest(frame),
        }],
    }
    manifest_path = root / "snapshot_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    repair.EXPECTED_C51_SNAPSHOT_PATH = manifest_path.resolve()
    repair.EXPECTED_C51_MANIFEST_SHA256 = sha256(manifest_path)
    repair.EXPECTED_C51_DATASET_SHA256 = "synthetic-dataset"
    repair.EXPECTED_C51_PARTITIONS = 1
    repair.EXPECTED_C51_ROWS = 2
    result = repair.verify_campaign051_snapshot_files(manifest, manifest_path, workers=1)
    assert result["verified_partitions"] == 1
    assert result["verified_rows"] == 2
    assert result["all_partition_byte_and_frame_hashes_valid"] is True
    assert result["isolated_exact_campaign051_output_columns"] == list(repair.C51_OUTPUT_COLUMNS)
"""
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
