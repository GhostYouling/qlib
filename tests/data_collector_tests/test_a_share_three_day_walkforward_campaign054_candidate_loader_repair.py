"""Subprocess-isolated tests for Campaign054 candidate-loader repair."""

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


def test_campaign054_local_loader_reads_exact_bound_candidate_frame() -> None:
    result = _run_python(
        """
import json
from scripts import a_share_three_day_walkforward_campaign054_features_v7 as repair
path = repair.runner.output_root(repair.runner.DEFAULT_DATA_ROOT) / 'snapshot_manifest.json'
manifest = json.loads(path.read_text(encoding='utf-8'))
frame = repair.load_candidate_frame(path, manifest)
factor = repair.runner.FACTOR_NAME
eligible = frame[factor + '_eligible']
print(json.dumps({
    'rows': len(frame),
    'eligible': int(eligible.sum()),
    'minimum': float(frame.loc[eligible, factor].min()),
    'maximum': float(frame.loc[eligible, factor].max()),
    'duplicate_keys': int(frame.duplicated(['trade_date', 'symbol']).sum()),
}, sort_keys=True))
"""
    )
    assert json.loads(result.stdout) == {
        "duplicate_keys": 0,
        "eligible": 7675743,
        "maximum": 1.0,
        "minimum": -1.0,
        "rows": 7724498,
    }


def test_campaign054_local_loader_rejects_manifest_identity_before_values() -> None:
    result = _run_python(
        """
import json
from scripts import a_share_three_day_walkforward_campaign054_features_v7 as repair
path = repair.runner.output_root(repair.runner.DEFAULT_DATA_ROOT) / 'snapshot_manifest.json'
manifest = json.loads(path.read_text(encoding='utf-8'))
manifest['rows'] = manifest['rows'] - 1
try:
    repair.load_candidate_frame(path, manifest)
except repair.runner.Campaign054FeatureError as exc:
    print(json.dumps({'blocked': True, 'message': str(exc)}, sort_keys=True))
else:
    raise AssertionError('mutated manifest passed')
"""
    )
    payload = json.loads(result.stdout)
    assert payload["blocked"] is True
    assert "manifest identity changed" in payload["message"]


def test_campaign054_candidate_loader_repair_bindings_pass() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/a_share_three_day_preregistration_binding_validator.py",
            "--data-root",
            "/Volumes/DIsk/qlib-a-share-tushare-1m",
            "docs/a_share_three_day_walkforward_campaign_054_no_return_audit_candidate_loader_failure_repair_20260803.json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["all_bindings_passed"] is True
    assert payload["reports"][0]["binding_count"] == 3
