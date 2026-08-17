import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
LEDGER_V1_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_130/research_attempt_ledger_v1.json"
)
LEDGER_V2_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_130/research_attempt_ledger_v2.json"
)
RESULT_V2_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_130_terminal_result_v2_20260814.json"
)
POLICY_V149_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v149_20260814.json"
)
FAILURE_PATHS = [
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_130_unified_report_patch_context_failure_20260814.json",
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_130_three_day_report_patch_context_failure_20260814.json",
]
REPORT_PATHS = [
    REPO_ROOT / "data/experiments/short_horizon/current_research_report.md",
    REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_130_terminal_report.md",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_v2_extends_v1_and_preserves_hash_chain() -> None:
    v1 = load_json(LEDGER_V1_PATH)
    v2 = load_json(LEDGER_V2_PATH)
    base = v2["base_ledger"]
    assert base["path"].endswith("research_attempt_ledger_v1.json")
    assert base["sha256"] == sha256(LEDGER_V1_PATH)
    assert base["entry_count"] == len(v1["entries"]) == 3
    assert base["chain_tip_sha256"] == v1["chain_tip_sha256"]
    assert base["preserved"] is True

    previous = base["chain_tip_sha256"]
    for entry, failure_path in zip(v2["appended_entries"], FAILURE_PATHS, strict=True):
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
        assert entry["failure_record"]["sha256"] == sha256(failure_path)
        assert entry["scientific_result_changed"] is False
        previous = entry["entry_sha256"]
    assert v2["chain_tip_sha256"] == previous


def test_v2_result_policy_and_accounting_are_consistent() -> None:
    ledger = load_json(LEDGER_V2_PATH)
    result = load_json(RESULT_V2_PATH)
    policy = load_json(POLICY_V149_PATH)

    expected = {
        "campaign130_attempt_count": 5,
        "campaign130_ledger_entry_count": 5,
        "campaign130_infrastructure_failure_count": 4,
        "campaign130_prevalue_scientific_attempt_count": 1,
        "cumulative_historical_research_attempt_count": 1062,
        "cumulative_return_reading_development_trial_count": 307,
    }
    for key, value in expected.items():
        assert result["effective_accounting"][key] == value
        assert policy["effective_accounting"][key] == value

    assert ledger["attempt_count"] == 5
    assert ledger["infrastructure_failure_count"] == 4
    assert result["authoritative_inputs"]["attempt_ledger_v2"]["sha256"] == sha256(
        LEDGER_V2_PATH
    )
    assert policy["authoritative_inputs"]["campaign130_terminal_result_v2"][
        "sha256"
    ] == sha256(RESULT_V2_PATH)
    assert result["scientific_result"]["selected_candidate_count"] == 0
    assert result["scientific_result"]["changed_from_v1"] is False


def test_v149_preserves_library_and_next_campaign_boundary() -> None:
    policy = load_json(POLICY_V149_PATH)
    complete = policy["complete_historical_feature_library"]
    numeric = policy["numerical_comparator_eligibility"]
    assert policy["version"] == 149
    assert (
        complete["factor_definition_count"],
        numeric["eligible_numeric_comparator_count"],
    ) == (
        151,
        140,
    )
    assert (
        complete["order_sha256"]
        == "91c2da3018330edbaddbb60b86370dcd9732425590f0565c70790b990002e0b5"
    )
    assert (
        numeric["eligible_numeric_comparator_order_sha256"]
        == "c71bfe27486c9567afd3aca21e4b04053658c23ac651e7f4df7fd014b0c31efd"
    )
    assert policy["future_campaign_boundary"]["next_campaign"] == 131
    assert policy["research_boundary"]["stress_2024_2025_opened"] is False


def test_reports_candidate49_and_current_use_boundaries_are_consistent() -> None:
    result = load_json(RESULT_V2_PATH)
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

    for report_path in REPORT_PATHS:
        report = report_path.read_text(encoding="utf-8")
        assert "Campaign130" in report
        assert "Campaign131" in report
