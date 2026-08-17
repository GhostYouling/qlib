"""Pre-value tests for Campaign056 ordered no-return audit wiring."""

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


def test_campaign056_audit_static_bindings_and_exact_comparison_order() -> None:
    result = _run_python(
        """
import json
from scripts import a_share_three_day_walkforward_campaign056_no_return_audit as audit
print(json.dumps(audit.verify_static_bindings(), sort_keys=True))
"""
    )
    payload = json.loads(result.stdout)
    assert payload["comparison_count"] == 79
    assert payload["comparison_order_sha256"] == (
        "669a996cc0b8d2582f8a1c0cd2f7d9a8503fdcfe7fb5f1b79033ac7832bb4e67"
    )
    assert payload["comparison_first"] == {
        "name": "late_return_30m",
        "score_direction": "higher",
    }
    assert payload["comparison_last"] == {
        "name": "intraday_price_update_clock_entropy_10b_238m",
        "score_direction": "higher",
    }


def test_campaign056_status_reads_no_partition_values_or_returns() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/a_share_three_day_walkforward_campaign056_no_return_audit.py",
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
    assert payload["audit_count"] == 0
    assert payload["daily_price_fields_read_by_status"] is False
    assert payload["forward_return_fields_read_by_status"] is False


def test_campaign056_loader_rejects_identity_before_partition_values() -> None:
    result = _run_python(
        """
import json
from scripts import a_share_three_day_walkforward_campaign056_no_return_audit as audit
manifest = json.loads(audit.SNAPSHOT_MANIFEST_PATH.read_text(encoding='utf-8'))
manifest['rows'] -= 1
try:
    audit.load_candidate_frame(audit.SNAPSHOT_MANIFEST_PATH, manifest)
except audit.Campaign056NoReturnAuditError as exc:
    print(json.dumps({'blocked': True, 'message': str(exc)}, sort_keys=True))
else:
    raise AssertionError('mutated manifest passed')
"""
    )
    payload = json.loads(result.stdout)
    assert payload["blocked"] is True
    assert "manifest identity changed" in payload["message"]


def test_campaign056_audit_rejects_wrong_data_root_before_values() -> None:
    result = _run_python(
        """
import json
from pathlib import Path
from scripts import a_share_three_day_walkforward_campaign056_no_return_audit as audit
try:
    audit.run_no_return_audit(
        data_root=Path('/tmp/campaign056-wrong-root'),
        experiment_root=Path('/tmp/campaign056-wrong-experiment'),
        workers=1,
    )
except audit.Campaign056NoReturnAuditError as exc:
    print(json.dumps({'blocked': True, 'message': str(exc)}, sort_keys=True))
else:
    raise AssertionError('wrong data root passed')
"""
    )
    payload = json.loads(result.stdout)
    assert payload == {"blocked": True, "message": "Campaign056 data root changed"}


def test_campaign056_snapshot_publication_bindings_pass() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/a_share_three_day_preregistration_binding_validator.py",
            "--data-root",
            DATA_ROOT,
            "docs/a_share_three_day_walkforward_campaign_056_feature_snapshot_binding_20260804.json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["all_bindings_passed"] is True
    assert payload["reports"][0]["binding_count"] == 4
