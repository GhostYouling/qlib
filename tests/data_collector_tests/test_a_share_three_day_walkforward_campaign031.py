import argparse
import json
from pathlib import Path

import pytest

import scripts.a_share_three_day_preregistration_binding_validator as bindings
import scripts.a_share_three_day_walkforward_campaign031 as campaign
import scripts.a_share_three_day_walkforward_campaign031_features as features


REPO_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_SHA256 = (
    "288438e77d9da91300472cb57651efd79c565fb3d761609f30f8fcd74cea1ab0"
)


def test_campaign031_preregistration_and_catalog_are_frozen() -> None:
    path = campaign.engine_namespace["DEFAULT_CAMPAIGN"]
    result = bindings.validate_record(
        path, data_root=features.DEFAULT_DATA_ROOT
    )
    assert result["all_bindings_passed"] is True
    spec, observed_sha256 = campaign.load_campaign(path)
    assert observed_sha256 == CAMPAIGN_SHA256
    assert campaign.build_trial_catalog(spec) == [
        {
            "trial_id": (
                "wf031_single__"
                "intraday_market_dispersion_decoupling_238m"
            ),
            "parent_trial_id": None,
            "kind": "single_factor",
            "feature_set": [features.FACTOR_NAME],
            "weights": [1.0],
            "complexity": 1,
        }
    ]


def test_campaign031_development_and_stress_boundaries_are_closed() -> None:
    spec, _ = campaign.load_campaign(
        campaign.engine_namespace["DEFAULT_CAMPAIGN"]
    )
    assert spec["evidence_classification"]["development_2019_2023"].startswith(
        "historically exposed"
    )
    assert spec["search_space"]["expected_trial_count"] == 1
    assert spec["search_space"]["weight_fitting"] is False
    assert spec["search_space"]["threshold_search"] is False
    assert spec["search_space"]["year_subset_search"] is False
    assert spec["search_space"]["filter_search"] is False
    assert spec["candidate49_boundary"]["historical_return_read_allowed"] is False
    assert spec["research_output_boundary"]["current_scoring_allowed"] is False
    assert (
        spec["research_output_boundary"][
            "campaign030_rescue_or_reweight_allowed"
        ]
        is False
    )


def test_campaign031_status_is_terminal_with_closed_stress() -> None:
    result = campaign.status(
        argparse.Namespace(
            campaign=str(campaign.engine_namespace["DEFAULT_CAMPAIGN"]),
            output_root=str(campaign.engine_namespace["DEFAULT_OUTPUT_ROOT"]),
        )
    )
    assert result["campaign_sha256"] == CAMPAIGN_SHA256
    assert result["expected_trial_count"] == 1
    assert result["ledger_entry_count"] == 1
    assert result["selected_survivor_count"] == 0
    assert result["stress_intent_exists"] is False
    assert result["stress_record_exists"] is True
    assert result["stress_status"] == "not_opened_zero_development_survivors"
    assert result["candidate49_historical_return_read"] is False
    assert result["current_scoring_selection_sizing_or_orders_allowed"] is False


def test_campaign031_terminal_record_preserves_gate_failures_and_boundaries() -> None:
    root = (
        REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_031"
        / "walkforward"
    )
    record_path = (
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_031_research_record.json"
    )
    ledger = json.loads((root / "trial_ledger.json").read_text())
    survivors = json.loads((root / "development_survivors.json").read_text())
    stress = json.loads(
        (root / "exposed_stress_consumption_record.json").read_text()
    )
    record = json.loads(record_path.read_text())
    assert len(ledger["entries"]) == 1
    decision = survivors["trial_decisions"][0]
    assert decision["development_survivor_gate_passed"] is False
    assert decision["positive_mean_rank_ic_fold_count"] == 3
    assert decision["positive_normalized_return_fold_count"] == 2
    assert decision["positive_pilot_return_fold_count"] == 1
    assert decision["median_validation_mean_rank_ic"] == pytest.approx(
        0.03351151836586693
    )
    assert decision["development_aggregate_20bp_return"] == pytest.approx(
        -0.12827843361699542
    )
    assert decision["validation_quality_rejection_reasons"] == [
        "insufficient_positive_pilot_return_folds",
        "median_validation_pilot_return",
        "worst_validation_normalized_drawdown",
        "nonpositive_development_aggregate_20bp_return",
    ]
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    assert record["decision"]["factor_terminal"] is True
    assert (
        record["infrastructure_and_semantic_record"][
            "survivor_complexity_reporting_anomaly"
        ]["canonical_trial_catalog_complexity"]
        == 1
    )
    assert bindings.validate_record(
        record_path,
        data_root=features.DEFAULT_DATA_ROOT,
    )["all_bindings_passed"] is True


def test_unified_report_contains_campaign031_terminal_result() -> None:
    report = (
        REPO_ROOT
        / "data/experiments/short_horizon/three_day_research_report.md"
    ).read_text()
    assert "## 历史滚动 Campaign031 权威追加" in report
    assert "最大绝对中位日秩相关为 0.690903" in report
    assert "20bp 纸面收益为 +6.513813%/-0.223049%/-4.284055%/-12.827843%" in report
