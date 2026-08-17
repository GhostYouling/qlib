"""Terminal and isolation evidence for rejected Campaign041."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign041_features as feature


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_041/"
    "no_return/20260731T072630Z_campaign041_no_return_audit.json"
)
RESEARCH_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_041_research_record.json"
)
SIGNAL_LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
UNIFIED_REPORT = (
    REPO_ROOT
    / "data/experiments/short_horizon/three_day_research_report.md"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_terminal_audit_rejects_two_of_62_after_coverage():
    record = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    factor = feature.FACTOR_NAME
    coverage = record["coverage_and_capacity"][factor]
    uniqueness = record["uniqueness"][factor]

    assert _sha256(AUDIT_PATH) == feature.NO_RETURN_AUDIT_SHA256
    assert coverage["gate_passed_before_comparison_values"] is True
    assert uniqueness["comparison_values_loaded_after_coverage_pass"] is True
    assert uniqueness["comparison_factor_count"] == 62
    assert uniqueness["comparison_order_matches_preregistration"] is True
    assert sum(item["gate_passed"] for item in uniqueness["comparisons"]) == 60
    assert uniqueness["all_required_comparisons_passed"] is False
    assert record["admissible_factor_count"] == 0


def test_failed_comparisons_are_frozen_overlap_and_range_entropy():
    record = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    comparisons = record["uniqueness"][feature.FACTOR_NAME]["comparisons"]
    failed = [item for item in comparisons if not item["gate_passed"]]

    assert failed == [
        {
            "absolute_median_daily_rank_correlation": 0.836224378645272,
            "comparison_factor": (
                "intraday_adjacent_range_overlap_continuity_238p"
            ),
            "daily_correlation_frame_sha256": (
                "a7319c3cfbd1ad2ca15101a62a87559247790691e1edac61a934830bb6c2487f"
            ),
            "daily_rank_correlation_p05": 0.6747901985827572,
            "daily_rank_correlation_p95": 0.9030827860995972,
            "gate_passed": False,
            "median_daily_rank_correlation": 0.836224378645272,
            "minimum_pairwise_names_observed": 52,
            "pairwise_sessions": 1623,
            "score_direction": "higher",
        },
        {
            "absolute_median_daily_rank_correlation": 0.8017225564350808,
            "comparison_factor": (
                "intraday_intrabar_range_participation_entropy_240m"
            ),
            "daily_correlation_frame_sha256": (
                "ee6d7425d9d5200d16b82c3227b9c6dda84685612e443968ab7a92041305017c"
            ),
            "daily_rank_correlation_p05": 0.651528370950728,
            "daily_rank_correlation_p95": 0.8673400438197966,
            "gate_passed": False,
            "median_daily_rank_correlation": 0.8017225564350808,
            "minimum_pairwise_names_observed": 52,
            "pairwise_sessions": 1623,
            "score_direction": "higher",
        },
    ]


def test_research_record_bindings_and_no_return_boundary_hold():
    validation = bindings.validate_record(
        RESEARCH_RECORD,
        data_root=feature.DEFAULT_DATA_ROOT,
    )
    record = json.loads(RESEARCH_RECORD.read_text(encoding="utf-8"))

    assert validation["all_bindings_passed"] is True
    assert validation["passed_binding_count"] == 16
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


def test_no_campaign041_development_artifacts_or_candidate49_changes_exist():
    assert not (
        REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_041/"
        "walkforward"
    ).exists()
    assert not (
        REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign041.py"
    ).exists()
    assert not (
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_041_preregistration.json"
    ).exists()
    assert (
        _sha256(SIGNAL_LEDGER)
        == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert (
        _sha256(EXECUTION_LEDGER)
        == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )


def test_unified_report_contains_campaign041_terminal_result():
    report = UNIFIED_REPORT.read_text(encoding="utf-8")

    assert "## 历史滚动 Campaign041 权威追加" in report
    assert "`intraday_microgap_absorption_share_238p`" in report
    assert "+0.836224" in report
    assert "+0.801723" in report
    assert "没有读取任何历史 forward return" in report
