"""Terminal and isolation evidence for rejected Campaign040."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign040_features as feature


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_040/"
    "no_return/20260731T051832Z_campaign040_no_return_audit.json"
)
RESEARCH_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_040_research_record.json"
)
SIGNAL_LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_terminal_audit_rejects_exactly_one_of_61_after_coverage():
    record = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    factor = feature.FACTOR_NAME
    coverage = record["coverage_and_capacity"][factor]
    uniqueness = record["uniqueness"][factor]

    assert _sha256(AUDIT_PATH) == feature.NO_RETURN_AUDIT_SHA256
    assert coverage["gate_passed_before_comparison_values"] is True
    assert uniqueness["comparison_values_loaded_after_coverage_pass"] is True
    assert uniqueness["comparison_factor_count"] == 61
    assert uniqueness["comparison_order_matches_preregistration"] is True
    assert sum(item["gate_passed"] for item in uniqueness["comparisons"]) == 60
    assert uniqueness["all_required_comparisons_passed"] is False
    assert record["admissible_factor_count"] == 0


def test_failed_comparison_is_frozen_range_participation_entropy():
    record = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    comparisons = record["uniqueness"][feature.FACTOR_NAME]["comparisons"]
    failed = [item for item in comparisons if not item["gate_passed"]]

    assert failed == [
        {
            "absolute_median_daily_rank_correlation": 0.8843376129920713,
            "comparison_factor": (
                "intraday_intrabar_range_participation_entropy_240m"
            ),
            "daily_correlation_frame_sha256": (
                "8c37806ae30b77a8a360fa80371e3ea3bc716a05cd3476d314e1bdf8257ce1b3"
            ),
            "daily_rank_correlation_p05": 0.7837451854908563,
            "daily_rank_correlation_p95": 0.9472981852546142,
            "gate_passed": False,
            "median_daily_rank_correlation": 0.8843376129920713,
            "minimum_pairwise_names_observed": 52,
            "pairwise_sessions": 1623,
            "score_direction": "higher",
        }
    ]


def test_research_record_bindings_and_no_return_boundary_hold():
    validation = bindings.validate_record(
        RESEARCH_RECORD,
        data_root=feature.DEFAULT_DATA_ROOT,
    )
    record = json.loads(RESEARCH_RECORD.read_text(encoding="utf-8"))

    assert validation["all_bindings_passed"] is True
    assert validation["passed_binding_count"] == 12
    assert record["trial_accounting"]["development_trial_count"] == 0
    assert record["trial_accounting"]["development_return_fields_read"] is False
    assert record["trial_accounting"]["stress_2024_2025_opened"] is False
    assert record["trial_accounting"]["stress_return_fields_read"] is False
    assert (
        record["no_return_admission"]["audit"][
            "historical_forward_return_fields_read"
        ]
        is False
    )


def test_no_campaign040_development_artifacts_or_candidate49_changes_exist():
    assert not (
        REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_040/"
        "walkforward"
    ).exists()
    assert not (
        REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign040.py"
    ).exists()
    assert not (
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_040_preregistration.json"
    ).exists()
    assert (
        _sha256(SIGNAL_LEDGER)
        == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert (
        _sha256(EXECUTION_LEDGER)
        == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
