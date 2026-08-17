import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCOUTING_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_130_concept_scouting_20260814.json"
)
FRONTIER_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_130_mechanism_source_frontier_audit_20260814.json"
)
LEDGER_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_130/research_attempt_ledger_v1.json"
)
RESULT_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_130_terminal_result_20260814.json"
)
POLICY_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v148_20260814.json"
)
FAILURE_PATHS = [
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_130_unmatched_glob_search_failure_20260814.json",
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_130_masked_jq_expression_failure_20260814.json",
]
REPORT_PATH = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_130_terminal_report.md"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_finite_catalog_rejects_every_concept_before_values() -> None:
    scouting = load_json(SCOUTING_PATH)
    catalog = scouting["finite_prevalue_concept_catalog"]
    assert len(catalog) == 6
    assert all(item["prevalue_decision"].startswith("rejected_") for item in catalog)
    assert scouting["selection"]["selected_candidate_count"] == 0
    assert (
        scouting["decision"][
            "create_campaign130_formula_feature_or_model_implementation"
        ]
        is False
    )
    boundary = scouting["research_boundary"]
    assert boundary["campaign130_source_rows_read"] is False
    assert boundary["campaign130_candidate_values_computed_or_read"] is False
    assert boundary["historical_forward_returns_read"] is False


def test_frontier_result_and_v148_preserve_151_140_orders() -> None:
    frontier = load_json(FRONTIER_PATH)
    assert frontier["concept_scouting"]["sha256"] == sha256(SCOUTING_PATH)
    assert (
        frontier["terminal_decision"]["campaign130_complete_factor_definition_created"]
        is False
    )
    assert (
        frontier["terminal_decision"]["campaign130_development_or_stress_trial_run"]
        is False
    )

    result = load_json(RESULT_PATH)
    assert result["scientific_result"]["selected_candidate_count"] == 0
    assert result["effective_accounting"]["campaign130_attempt_count"] == 3

    policy = load_json(POLICY_PATH)
    complete = policy["complete_historical_feature_library"]
    numeric = policy["numerical_comparator_eligibility"]
    assert (
        complete["factor_definition_count"],
        numeric["eligible_numeric_comparator_count"],
    ) == (151, 140)
    assert (
        complete["order_sha256"]
        == "91c2da3018330edbaddbb60b86370dcd9732425590f0565c70790b990002e0b5"
    )
    assert (
        numeric["eligible_numeric_comparator_order_sha256"]
        == "c71bfe27486c9567afd3aca21e4b04053658c23ac651e7f4df7fd014b0c31efd"
    )
    assert policy["future_campaign_boundary"]["next_campaign"] == 131


def test_append_only_ledger_hash_chain_and_failures() -> None:
    ledger = load_json(LEDGER_PATH)
    previous = ledger["chain_genesis"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        material = (
            "campaign130|"
            + entry["attempt_id"]
            + "|"
            + previous
            + "|"
            + entry["phase"]
            + "|"
            + entry["status"]
        )
        assert hashlib.sha256(material.encode()).hexdigest() == entry["entry_sha256"]
        previous = entry["entry_sha256"]
    assert ledger["chain_tip_sha256"] == previous
    for entry, path in zip(ledger["entries"][1:], FAILURE_PATHS, strict=True):
        assert entry["failure_record"]["sha256"] == sha256(path)
    assert ledger["attempt_count"] == 3
    assert ledger["infrastructure_failure_count"] == 2
    assert ledger["cumulative_historical_research_attempt_count"] == 1060
    assert ledger["cumulative_return_reading_development_trial_count"] == 307


def test_candidate49_and_current_use_boundaries_remain_closed() -> None:
    result = load_json(RESULT_PATH)
    assert result["candidate49"]["signal_entry_count"] == 0
    assert result["candidate49"]["execution_entry_count"] == 0
    boundary = result["research_boundary"]
    assert boundary["candidate49_historical_backfill_performed"] is False
    assert boundary["second_prospective_candidate_created"] is False
    assert (
        boundary["current_scoring_selection_sizing_positions_or_orders_performed"]
        is False
    )
    assert boundary["stress_2024_2025_opened"] is False
    report = REPORT_PATH.read_text(encoding="utf-8")
    assert "Campaign131" in report
    assert "不构成投资建议" in report
