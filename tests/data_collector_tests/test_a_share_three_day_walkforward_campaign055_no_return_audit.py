"""Subprocess-isolated pre-return tests for Campaign055 audit wiring."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = "/Volumes/DIsk/qlib-a-share-tushare-1m"


def _run_python(source: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", source],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_campaign055_audit_status_binds_only_authoritative_v2_snapshot() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/a_share_three_day_walkforward_campaign055_features_v7.py",
            "status",
            "--data-root",
            DATA_ROOT,
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["snapshot_exists"] is True
    assert payload["snapshot_sha256_bound"] is True
    assert payload["snapshot_observed_sha256"] == (
        "f78d62adf2772d64e718e7fdc4138c40325f6c02d17073dd5db0d1271216009e"
    )
    assert payload["snapshot_manifest_path"].endswith(
        "campaign055_feature_library_v2/snapshot_manifest.json"
    )
    assert payload["audit_count"] == 0
    assert payload["daily_price_fields_read_by_status"] is False
    assert payload["forward_return_fields_read_by_status"] is False


def test_campaign055_audit_reconstructs_exact_78_comparison_order() -> None:
    result = _run_python(
        """
import json
from scripts import a_share_three_day_walkforward_campaign055_features_v7 as audit
protocol = audit.runner.load_protocol()
items = protocol['ordered_no_return_gates']['uniqueness_after_coverage_only']['comparison_factors']
print(json.dumps({
    'count': len(items),
    'digest': audit.runner._comparison_order_digest(items),
    'first': items[0],
    'last': items[-1],
}, sort_keys=True))
"""
    )
    payload = json.loads(result.stdout)
    assert payload == {
        "count": 78,
        "digest": "2a9d3188624bd7dd2556de5754f1ce401b0b04c2b47ca8cf15dae46a56253de6",
        "first": {
            "name": "late_return_30m",
            "score_direction": "higher",
        },
        "last": {
            "name": "intraday_volume_weighted_transaction_price_bowley_skew_240m",
            "score_direction": "higher",
        },
    }


def test_campaign055_local_loader_reads_exact_bound_candidate_frame() -> None:
    result = _run_python(
        """
import json
from scripts import a_share_three_day_walkforward_campaign055_features_v7 as audit
path = audit.runner.output_root(audit.runner.DEFAULT_DATA_ROOT) / 'snapshot_manifest.json'
manifest = json.loads(path.read_text(encoding='utf-8'))
frame = audit.load_candidate_frame(path, manifest)
factor = audit.runner.FACTOR_NAME
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
        "eligible": 7664125,
        "maximum": 0.9999587450126793,
        "minimum": 0.0,
        "rows": 7724498,
    }


def test_campaign055_local_loader_rejects_manifest_identity_before_values() -> None:
    result = _run_python(
        """
import json
from scripts import a_share_three_day_walkforward_campaign055_features_v7 as audit
path = audit.runner.output_root(audit.runner.DEFAULT_DATA_ROOT) / 'snapshot_manifest.json'
manifest = json.loads(path.read_text(encoding='utf-8'))
manifest['rows'] = manifest['rows'] - 1
try:
    audit.load_candidate_frame(path, manifest)
except audit.runner.Campaign055FeatureError as exc:
    print(json.dumps({'blocked': True, 'message': str(exc)}, sort_keys=True))
else:
    raise AssertionError('mutated manifest passed')
"""
    )
    payload = json.loads(result.stdout)
    assert payload["blocked"] is True
    assert "manifest identity changed" in payload["message"]


def test_campaign055_audit_fails_before_values_on_wrong_data_root() -> None:
    result = _run_python(
        """
import json
from pathlib import Path
from scripts import a_share_three_day_walkforward_campaign055_features_v7 as audit
try:
    audit.run_no_return_audit(
        data_root=Path('/tmp/campaign055-audit-missing-root'),
        experiment_root=Path('/tmp/campaign055-audit-missing-experiment'),
        workers=1,
    )
except audit.runner.Campaign055FeatureError as exc:
    print(json.dumps({'blocked': True, 'message': str(exc)}, sort_keys=True))
else:
    raise AssertionError('audit unexpectedly crossed the missing snapshot gate')
"""
    )
    payload = json.loads(result.stdout)
    assert payload["blocked"] is True
    assert "authoritative v2 snapshot manifest changed" in payload["message"]


def test_campaign055_snapshot_publication_bindings_pass() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/a_share_three_day_preregistration_binding_validator.py",
            "--data-root",
            DATA_ROOT,
            "docs/a_share_three_day_walkforward_campaign_055_snapshot_publication_binding_20260804.json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["all_bindings_passed"] is True
    assert payload["reports"][0]["binding_count"] == 10
