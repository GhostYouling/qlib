"""Pre-return tests for the single frozen Campaign062 walk-forward trial."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import scripts.a_share_three_day_walkforward_campaign062 as campaign


REPO_ROOT = Path(__file__).resolve().parents[2]
PREREGISTRATION_SHA256 = (
    "6542def5305cd4c3d88a077105bfeeaf5530186adf75530b768d3f4e522be1de"
)
AUDIT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_062/no_return/"
    "20260804T210409Z_campaign062_no_return_audit.json"
)


def test_campaign062_preregistration_loads_exact_single_trial() -> None:
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


def test_campaign062_inherits_exact_three_folds_and_survivor_gates() -> None:
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


def test_campaign062_no_return_audit_is_admissible_and_return_closed() -> None:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    factor = campaign.ADMITTED_FACTOR
    coverage = audit["coverage_and_capacity"][factor]
    uniqueness = audit["uniqueness"][factor]
    assert hashlib.sha256(AUDIT.read_bytes()).hexdigest() == (
        "c783f58c5432068b1c5ca724be01d83bb234f17df21fcda64f9e7818b12bd4ea"
    )
    assert audit["status"] == (
        "completed_with_one_admissible_factor_pending_walkforward_preregistration"
    )
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["median_coverage"] == 0.9994517542211769
    assert coverage["p05_coverage"] == 0.9956886515772271
    assert coverage["potential_non_overlapping_three_session_cohorts"] == 540
    assert uniqueness["comparison_values_loaded_after_coverage_pass"] is True
    assert uniqueness["comparison_factor_count"] == 93
    assert uniqueness["comparison_order_matches_preregistration"] is True
    assert uniqueness["all_required_comparisons_passed"] is True
    assert uniqueness["maximum_observed_absolute_median_daily_rank_correlation"] == (
        0.7691435839145652
    )
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False
    assert audit["candidate49_historical_return_read"] is False
    assert audit["provider_request_issued"] is False


def test_campaign062_stress_is_closed_before_development_survivor_freeze() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/a_share_three_day_walkforward_campaign062.py",
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


def test_campaign062_development_preregistration_bindings_pass() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/a_share_three_day_preregistration_binding_validator.py",
            "--data-root",
            "/Volumes/DIsk/qlib-a-share-tushare-1m",
            "docs/a_share_three_day_walkforward_campaign_062_preregistration.json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["all_bindings_passed"] is True
    assert payload["reports"][0]["binding_count"] == 21
