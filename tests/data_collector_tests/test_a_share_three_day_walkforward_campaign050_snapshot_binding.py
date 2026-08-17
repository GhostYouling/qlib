from __future__ import annotations

import json
import subprocess
import sys


def test_campaign050_snapshot_bound_entrypoint_is_no_return_only() -> None:
    source = """
import json
from pathlib import Path
import scripts.a_share_three_day_walkforward_campaign050_features_v5 as entry

runner = entry.runner
status = runner.status(
    runner.DEFAULT_DATA_ROOT,
    runner.DEFAULT_EXPERIMENT_ROOT,
)
print(json.dumps({
    "snapshot_exists": status["snapshot_exists"],
    "snapshot_sha256_bound": status["snapshot_sha256_bound"],
    "snapshot_observed_sha256": status["snapshot_observed_sha256"],
    "expected_snapshot_sha256": entry.EXPECTED_SNAPSHOT_MANIFEST_SHA256,
    "audit_count": status["audit_count"],
    "daily_prices": status["daily_price_fields_read_by_status"],
    "forward_returns": status["forward_return_fields_read_by_status"],
    "prospective_candidate50": status["candidate50_prospective_activation_created"],
}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", source],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)
    assert result == {
        "snapshot_exists": True,
        "snapshot_sha256_bound": True,
        "snapshot_observed_sha256": "8e95728fd9e1ba3d3ab820dbf5d92812bd18f9076ee901ee80cd76cf989300ef",
        "expected_snapshot_sha256": "8e95728fd9e1ba3d3ab820dbf5d92812bd18f9076ee901ee80cd76cf989300ef",
        "audit_count": 1,
        "daily_prices": False,
        "forward_returns": False,
        "prospective_candidate50": False,
    }
