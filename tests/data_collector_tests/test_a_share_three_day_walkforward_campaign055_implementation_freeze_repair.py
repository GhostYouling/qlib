"""Additive tests for Campaign055 implementation-freeze path repair."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign055_features.py"
FAILED = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign055_features_v2.py"
REPAIRED = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign055_features_v3.py"
FAILURE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_055_implementation_freeze_semantic_path_failure_20260804.json"
TEST_FAILURE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_055_repair_test_shared_module_mutation_failure_20260804.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign055_repair_preserves_frozen_base_and_failure_evidence() -> None:
    assert _sha256(BASE) == (
        "d695e5acd9645f4706e238c95db2ea69df397004416ea4dd9f895385be603714"
    )
    assert _sha256(FAILED) == (
        "3c07d8d294846f8e3508d69e010baa8a8ea07997281ce96194dad19141be97e1"
    )
    assert _sha256(REPAIRED) == (
        "fa9cc6449404da91dd39dd6ed340f83eb70be768a7808df5cd9bc4da1b0040fa"
    )
    assert _sha256(FAILURE) == (
        "820497ae38b2d9404b3c52c546aab9e98a06bc59ce508e0661aa57629e7974b2"
    )
    assert _sha256(TEST_FAILURE) == (
        "b4142dbdd6be797b5ed7bd456cb36cdf81f4557ef419f89ac7b50e42545d806c"
    )


def _run_child(source: str) -> dict:
    completed = subprocess.run(
        [sys.executable, "-c", source],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_campaign055_repaired_loader_reads_nested_pre_value_evidence() -> None:
    payload = _run_child(
        "import json; "
        "from scripts import a_share_three_day_walkforward_campaign055_features_v3 as r; "
        "f=r.load_implementation_freeze(); e=f['pre_freeze_execution_evidence']; "
        "print(json.dumps({'status':f['status'],'candidate':e['candidate_values_read_before_freeze'],"
        "'comparison':e['comparison_values_read_before_freeze'],'returns':e['historical_daily_price_or_forward_returns_read_before_freeze'],"
        "'provider':e['provider_request_issued_before_freeze'],'snapshot':e['external_campaign055_snapshot_manifest_present']}))"
    )
    assert payload == {
        "status": "frozen_before_campaign055_candidate_values",
        "candidate": False,
        "comparison": False,
        "returns": False,
        "provider": False,
        "snapshot": False,
    }


def test_campaign055_repair_status_remains_no_value_and_no_audit() -> None:
    status = _run_child(
        "import json; "
        "from scripts import a_share_three_day_walkforward_campaign055_features_v3 as r; "
        "print(json.dumps(r.runner.status(r.runner.DEFAULT_DATA_ROOT,r.runner.DEFAULT_EXPERIMENT_ROOT),sort_keys=True))"
    )
    assert status["implementation_freeze_sha256_bound"] is True
    assert status["snapshot_exists"] is False
    assert status["audit_count"] == 0
    assert status["daily_price_fields_read_by_status"] is False
    assert status["forward_return_fields_read_by_status"] is False
    assert status["candidate49_historical_return_read"] is False
