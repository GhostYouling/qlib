from __future__ import annotations

import json
import subprocess
import sys


def _run_isolated(source: str) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, "-c", source],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_campaign050_audit_repair_installs_isolated_campaign049_verifier() -> None:
    result = _run_isolated(
        """
import json
import scripts.a_share_three_day_walkforward_campaign050_features_v7 as entry

runner = entry.runner
print(json.dumps({
    "repair_authorization": runner._sha256(entry.REPAIR_AUTHORIZATION),
    "campaign049_factor": entry.isolated_campaign049.FACTOR_NAME,
    "campaign049_output_columns": list(entry.isolated_campaign049.OUTPUT_COLUMNS),
    "installed_verifier_is_isolated": (
        runner._base.verify_snapshot_files
        is entry.isolated_campaign049.verify_snapshot_files
    ),
}))
"""
    )
    factor = "intraday_morning_afternoon_amount_profile_similarity_120b"
    assert result == {
        "repair_authorization": "97b21132e090aacaf5821833d35a50a4813dc0e67b5061359a978a936b94ea9f",
        "campaign049_factor": factor,
        "campaign049_output_columns": [
            "trade_date",
            "symbol",
            "provider",
            factor,
            f"{factor}_eligible",
        ],
        "installed_verifier_is_isolated": True,
    }


def test_campaign050_isolated_campaign049_verifier_accepts_all_frozen_files() -> None:
    result = _run_isolated(
        """
import json
import scripts.a_share_three_day_walkforward_campaign050_features_v7 as entry

runner = entry.runner
path = runner.C49_SNAPSHOT_PATH
manifest = json.loads(path.read_text(encoding="utf-8"))
result = runner._base.verify_snapshot_files(manifest, path, 4)
print(json.dumps(result, sort_keys=True))
"""
    )
    assert result == {
        "all_partition_byte_and_frame_hashes_valid": True,
        "verified_partitions": 33015,
        "verified_rows": 7724498,
    }
