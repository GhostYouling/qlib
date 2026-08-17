import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
LEDGER_V2_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_130/research_attempt_ledger_v2.json"
)
LEDGER_V3_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_130/research_attempt_ledger_v3.json"
)
RESULT_V3_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_130_terminal_result_v3_20260814.json"
)
POLICY_V150_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v150_20260814.json"
)
FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_130_validation_test_path_failure_20260814.json"
)
REPORT_PATHS = [
    REPO_ROOT / "data/experiments/short_horizon/current_research_report.md",
    REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_130_terminal_report.md",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_v3_appends_validation_path_failure_without_scientific_change() -> None:
    v2 = load_json(LEDGER_V2_PATH)
    v3 = load_json(LEDGER_V3_PATH)
    base = v3["base_ledger"]
    assert base["sha256"] == sha256(LEDGER_V2_PATH)
    assert base["entry_count"] == 5
    assert base["chain_tip_sha256"] == v2["chain_tip_sha256"]

    entry = v3["appended_entries"][0]
    assert entry["previous_entry_sha256"] == base["chain_tip_sha256"]
    material = "|".join(
        [
            "campaign130",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        ]
    )
    assert hashlib.sha256(material.encode()).hexdigest() == entry["entry_sha256"]
    assert v3["chain_tip_sha256"] == entry["entry_sha256"]
    assert entry["failure_record"]["sha256"] == sha256(FAILURE_PATH)
    assert entry["scientific_result_changed"] is False
    assert entry["failed_exit_code_treated_as_success"] is False


def test_v3_result_v150_and_reports_bind_final_accounting() -> None:
    ledger = load_json(LEDGER_V3_PATH)
    result = load_json(RESULT_V3_PATH)
    policy = load_json(POLICY_V150_PATH)
    expected = {
        "campaign130_attempt_count": 6,
        "campaign130_ledger_entry_count": 6,
        "campaign130_infrastructure_failure_count": 5,
        "campaign130_prevalue_scientific_attempt_count": 1,
        "cumulative_historical_research_attempt_count": 1063,
        "cumulative_return_reading_development_trial_count": 307,
    }
    for key, value in expected.items():
        assert result["effective_accounting"][key] == value
        assert policy["effective_accounting"][key] == value

    assert ledger["attempt_count"] == 6
    assert result["authoritative_inputs"]["campaign130_attempt_ledger_v3"][
        "sha256"
    ] == sha256(LEDGER_V3_PATH)
    assert policy["authoritative_inputs"]["campaign130_terminal_result_v3"][
        "sha256"
    ] == sha256(RESULT_V3_PATH)
    assert policy["version"] == 150
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 151
    )
    assert (
        policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"]
        == 140
    )
    assert policy["future_campaign_boundary"]["next_campaign"] == 131
    assert result["candidate49"]["signal_entry_count"] == 0
    assert result["candidate49"]["execution_entry_count"] == 0
    assert result["research_boundary"]["stress_2024_2025_opened"] is False

    for report_path in REPORT_PATHS:
        report = report_path.read_text(encoding="utf-8")
        assert "Campaign130" in report
        assert "Campaign131" in report
