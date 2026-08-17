"""Subprocess-isolated pre-comparison tests for Campaign054 audit wiring."""

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


def test_campaign054_audit_status_binds_only_repaired_snapshot() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/a_share_three_day_walkforward_campaign054_features_v5.py",
            "status",
            "--data-root",
            "/Volumes/DIsk/qlib-a-share-tushare-1m",
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
        "e61ec157d2119575bc53444d0c8e3c808a4c1113ace8ffa7ed2866bb5e431904"
    )
    assert payload["snapshot_manifest_path"].endswith(
        "campaign054_feature_library_v2/snapshot_manifest.json"
    )
    assert payload["audit_count"] == 0


def test_campaign054_audit_reconstructs_exact_77_comparison_order() -> None:
    result = _run_python(
        """
import json
from scripts import a_share_three_day_walkforward_campaign054_features_v5 as audit
protocol = audit.runner.load_protocol()
items = protocol['ordered_no_return_gates']['uniqueness_after_coverage_only']['comparison_factors']
print(json.dumps({
    'count': len(items),
    'digest': audit.runner._comparison_order_digest(items),
    'last': items[-1],
}, sort_keys=True))
"""
    )
    payload = json.loads(result.stdout)
    assert payload == {
        "count": 77,
        "digest": "f6ec66bf87ae76240e1ad890699cb2a82856f32a327a2f9be52d3d1f0b753de2",
        "last": {
            "name": "intraday_amount_price_discovery_alignment_js_238p",
            "score_direction": "higher",
        },
    }


def test_campaign054_audit_fails_before_values_on_wrong_data_root() -> None:
    result = _run_python(
        """
import json
from pathlib import Path
from scripts import a_share_three_day_walkforward_campaign054_features_v5 as audit
try:
    audit.run_no_return_audit(
        data_root=Path('/tmp/campaign054-audit-missing-root'),
        experiment_root=Path('/tmp/campaign054-audit-missing-experiment'),
        workers=1,
    )
except audit.runner.Campaign054FeatureError as exc:
    print(json.dumps({'blocked': True, 'message': str(exc)}, sort_keys=True))
else:
    raise AssertionError('audit unexpectedly crossed the missing snapshot gate')
"""
    )
    payload = json.loads(result.stdout)
    assert payload["blocked"] is True
    assert "repaired snapshot manifest changed" in payload["message"]


def test_campaign054_snapshot_publication_bindings_pass() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/a_share_three_day_preregistration_binding_validator.py",
            "--data-root",
            "/Volumes/DIsk/qlib-a-share-tushare-1m",
            "docs/a_share_three_day_walkforward_campaign_054_snapshot_publication_binding_20260803.json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["all_bindings_passed"] is True
    assert payload["reports"][0]["binding_count"] == 6
