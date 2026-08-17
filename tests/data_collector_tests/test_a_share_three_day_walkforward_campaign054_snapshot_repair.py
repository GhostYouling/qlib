"""Subprocess-isolated tests for the Campaign054 additive snapshot repair."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_python(source: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", source],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_campaign054_repair_is_separate_v2_output_and_preserves_v1() -> None:
    result = _run_python(
        """
import json
from scripts import a_share_three_day_walkforward_campaign054_features_v3 as repair
payload = {
    'output_run_id': repair.runner.OUTPUT_RUN_ID,
    'output_root': str(repair.runner.output_root(repair.runner.DEFAULT_DATA_ROOT)),
    'failed_v1_hash': repair.runner._sha256(repair.FAILED_V1_SNAPSHOT),
}
print(json.dumps(payload, sort_keys=True))
"""
    )
    payload = json.loads(result.stdout)
    assert payload["output_run_id"].endswith("campaign054_feature_library_v2")
    assert payload["output_root"].endswith("campaign054_feature_library_v2")
    assert payload["failed_v1_hash"] == (
        "dd893a54fe04e336bcff3730c96e1181e7c429ccb9b25a7a768c0d96a07d93ed"
    )


def test_campaign054_repair_uses_stable_difference_and_cleans_evidence() -> None:
    result = _run_python(
        """
import json
import numpy as np
from scripts import a_share_three_day_walkforward_campaign054_features_v3 as repair
log_prices = np.r_[np.zeros(60), np.ones(60), np.full(59, 2.0), np.full(61, 10.0)]
volumes = np.ones((1, 240))
amounts = np.exp(log_prices)[None, :]
values, eligible, quality = repair.compute_factor_values(volumes, amounts)
clean = repair.clean_protocol_evidence({
    'campaign006_no_return_preregistration_sha256': 'stale',
    'campaign053_no_return_preregistration_sha256': 'stale',
    'campaign054_no_return_preregistration_sha256': 'current',
    'candidate49_no_return_protocol_sha256': 'kept',
})
print(json.dumps({
    'value': float(values[repair.runner.FACTOR_NAME][0]),
    'eligible': bool(eligible[repair.runner.FACTOR_NAME][0]),
    'range_failures': quality[repair.runner.FACTOR_NAME + '__range_or_nonfinite_score_rows'],
    'clean': clean,
}, sort_keys=True))
"""
    )
    payload = json.loads(result.stdout)
    assert payload["value"] == 0.8
    assert payload["eligible"] is True
    assert payload["range_failures"] == 0
    assert payload["clean"] == {
        "campaign054_no_return_preregistration_sha256": "current",
        "candidate49_no_return_protocol_sha256": "kept",
    }


def test_campaign054_repair_authorization_bindings_pass() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/a_share_three_day_preregistration_binding_validator.py",
            "--data-root",
            "/Volumes/DIsk/qlib-a-share-tushare-1m",
            "docs/a_share_three_day_walkforward_campaign_054_snapshot_v1_prebinding_failure_repair_20260803.json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["all_bindings_passed"] is True
    assert payload["reports"][0]["binding_count"] == 4
