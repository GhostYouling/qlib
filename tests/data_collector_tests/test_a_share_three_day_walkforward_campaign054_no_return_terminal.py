"""Terminal no-return evidence tests for Campaign054."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_054/no_return/20260803T153026Z_campaign054_no_return_audit.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign054_terminal_audit_passes_all_no_return_gates() -> None:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    factor = "intraday_volume_weighted_transaction_price_bowley_skew_240m"
    coverage = audit["coverage_and_capacity"][factor]
    uniqueness = audit["uniqueness"][factor]
    assert _sha256(AUDIT) == (
        "866006cbe319afeca3b055bef2a1754b954e4511b953a3e8a2337d3aa575ee87"
    )
    assert audit["status"] == (
        "completed_with_one_admissible_factor_pending_walkforward_preregistration"
    )
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["median_coverage"] == 0.9983855777993815
    assert coverage["p05_coverage"] == 0.992613184425025
    assert uniqueness["comparison_factor_count"] == 77
    assert uniqueness["comparison_order_matches_preregistration"] is True
    assert uniqueness["all_required_comparisons_passed"] is True
    assert uniqueness["maximum_observed_absolute_median_daily_rank_correlation"] == (
        0.2673548831122923
    )
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False
    assert audit["candidate49_historical_return_read"] is False


def test_campaign054_terminal_entrypoint_binds_existing_audit() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/a_share_three_day_walkforward_campaign054_features_v9.py",
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
    assert payload["audit_count"] == 1
    assert payload["no_return_audit_sha256_bound"] is True
    assert payload["latest_audit_observed_sha256"] == (
        "866006cbe319afeca3b055bef2a1754b954e4511b953a3e8a2337d3aa575ee87"
    )


def test_campaign054_no_return_freeze_bindings_pass() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/a_share_three_day_preregistration_binding_validator.py",
            "--data-root",
            "/Volumes/DIsk/qlib-a-share-tushare-1m",
            "docs/a_share_three_day_walkforward_campaign_054_no_return_audit_freeze_20260803.json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["all_bindings_passed"] is True
    assert payload["reports"][0]["binding_count"] == 7
