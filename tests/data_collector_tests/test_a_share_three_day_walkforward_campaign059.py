"""Pre-return tests for the single frozen Campaign059 walk-forward trial."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import scripts.a_share_three_day_walkforward_campaign059 as campaign


REPO_ROOT = Path(__file__).resolve().parents[2]
PREREGISTRATION_SHA256 = (
    "5b266c9729d20ebbf392dee25e50905feec390703077d992bbd2cb1218862ed5"
)
AUDIT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_059/"
    "20260804T141411Z_campaign059_no_return_audit.json"
)


def test_campaign059_preregistration_loads_exact_single_trial() -> None:
    spec, observed_sha = campaign.load_campaign(campaign.DEFAULT_PREREGISTRATION)
    catalog = campaign.build_trial_catalog(spec)
    assert observed_sha == PREREGISTRATION_SHA256
    assert catalog == [
        {
            "trial_id": campaign.FROZEN_TRIAL_ID,
            "parent_trial_id": None,
            "kind": "single_factor",
            "feature_set": [campaign.ADMITTED_FACTOR],
            "weights": [1.0],
            "complexity": 1,
        }
    ]


def test_campaign059_inherits_exact_three_folds_and_survivor_gates() -> None:
    spec, _ = campaign.load_campaign(campaign.DEFAULT_PREREGISTRATION)
    assert spec["walkforward_folds"] == [
        {
            "fold": 1,
            "training": {"start": "2019-01-01", "end": "2020-12-31"},
            "validation": {"start": "2021-01-01", "end": "2021-12-31"},
        },
        {
            "fold": 2,
            "training": {"start": "2019-01-01", "end": "2021-12-31"},
            "validation": {"start": "2022-01-01", "end": "2022-12-31"},
        },
        {
            "fold": 3,
            "training": {"start": "2019-01-01", "end": "2022-12-31"},
            "validation": {"start": "2023-01-01", "end": "2023-12-31"},
        },
    ]
    split = spec["split_protocol"]
    assert split["purge_signal_sessions_each_boundary"] == 3
    assert split["label_containment_required"] is True
    assert split["topk"] == 3
    survivor = spec["survivor_rule"]
    assert survivor["positive_ic_fold_count_gte"] == 2
    assert survivor["positive_pilot_return_fold_count_gte"] == 2
    assert survivor["development_aggregate_20bp_return_gt"] == 0.0
    assert survivor["worst_normalized_drawdown_gte"] == -0.25


def test_campaign059_no_return_audit_is_admissible_and_return_closed() -> None:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    factor = campaign.ADMITTED_FACTOR
    coverage = audit["coverage_and_capacity"][factor]
    uniqueness = audit["uniqueness"][factor]
    assert hashlib.sha256(AUDIT.read_bytes()).hexdigest() == (
        "633a85a1fe808947bb2a1ef3837f53ecfb85716fcc6ef91a4a06cff9e059ae0e"
    )
    assert audit["status"] == (
        "completed_with_one_admissible_factor_pending_walkforward_preregistration"
    )
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["median_coverage"] == 0.9930020520847165
    assert coverage["p05_coverage"] == 0.9806793901047609
    assert uniqueness["comparison_values_loaded_after_coverage_pass"] is True
    assert uniqueness["comparison_factor_count"] == 90
    assert uniqueness["comparison_order_matches_preregistration"] is True
    assert uniqueness["all_required_comparisons_passed"] is True
    assert uniqueness["maximum_observed_absolute_median_daily_rank_correlation"] == (
        0.7148903759224717
    )
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False
    assert audit["candidate49_historical_return_read"] is False
    assert audit["provider_request_issued_by_campaign059_audit"] is False


def test_campaign059_stress_is_closed_before_development_survivor_freeze() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/a_share_three_day_walkforward_campaign059.py",
            "status",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    status = json.loads(result.stdout)
    assert status["campaign_sha256"] == PREREGISTRATION_SHA256
    assert status["expected_trial_count"] == 1
    assert status["ledger_entry_count"] == 0
    assert status["stress_intent_exists"] is False
    assert status["stress_record_exists"] is False
    assert status["candidate49_historical_return_read"] is False
    assert status["current_scoring_selection_sizing_or_orders_allowed"] is False


def test_campaign059_development_preregistration_bindings_pass() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/a_share_three_day_preregistration_binding_validator.py",
            "--data-root",
            "/Volumes/DIsk/qlib-a-share-tushare-1m",
            "docs/a_share_three_day_walkforward_campaign_059_preregistration.json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["all_bindings_passed"] is True
    assert payload["reports"][0]["binding_count"] == 22
