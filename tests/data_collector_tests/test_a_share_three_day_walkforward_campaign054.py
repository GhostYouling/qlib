"""Pre-return tests for the single frozen Campaign054 walk-forward trial."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import scripts.a_share_three_day_walkforward_campaign054 as campaign


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_campaign054_preregistration_loads_exact_single_trial() -> None:
    spec, observed_sha = campaign.load_campaign(campaign.DEFAULT_PREREGISTRATION)
    catalog = campaign.build_trial_catalog(spec)
    assert observed_sha == (
        "4841579f32e889de783a9a665df346c45b6c7955b32d5315d443efc5de174330"
    )
    assert len(catalog) == 1
    assert catalog[0]["trial_id"] == campaign.FROZEN_TRIAL_ID
    assert catalog[0]["kind"] == "single_factor"
    assert catalog[0]["feature_set"] == [campaign.ADMITTED_FACTOR]
    assert catalog[0]["weights"] == [1.0]
    assert catalog[0]["complexity"] == 1


def test_campaign054_inherits_exact_three_folds_and_survivor_gates() -> None:
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
    assert spec["split_protocol"]["purge_signal_sessions_each_boundary"] == 3
    assert spec["split_protocol"]["label_containment_required"] is True
    assert spec["split_protocol"]["topk"] == 3
    survivor = spec["survivor_rule"]
    assert survivor["positive_ic_fold_count_gte"] == 2
    assert survivor["positive_pilot_return_fold_count_gte"] == 2
    assert survivor["development_aggregate_20bp_return_gt"] == 0.0
    assert survivor["worst_normalized_drawdown_gte"] == -0.25


def test_campaign054_stress_is_closed_before_development_survivor_freeze() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/a_share_three_day_walkforward_campaign054.py",
            "status",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    status = json.loads(result.stdout)
    assert status["expected_trial_count"] == 1
    assert status["ledger_entry_count"] == 0
    assert status["stress_intent_exists"] is False
    assert status["stress_record_exists"] is False
    assert status["candidate49_historical_return_read"] is False
    assert status["current_scoring_selection_sizing_or_orders_allowed"] is False


def test_campaign054_preregistration_bindings_pass() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/a_share_three_day_preregistration_binding_validator.py",
            "--data-root",
            "/Volumes/DIsk/qlib-a-share-tushare-1m",
            "docs/a_share_three_day_walkforward_campaign_054_preregistration.json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["all_bindings_passed"] is True
    assert payload["reports"][0]["binding_count"] == 19
