import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONCEPT_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_131_concept_scouting_20260814.json"
)
FRONTIER_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_131_mechanism_source_frontier_audit_20260814.json"
)
LEDGER_V1_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_131/research_attempt_ledger_v1.json"
)
LEDGER_V2_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_131/research_attempt_ledger_v2.json"
)
LEDGER_V3_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_131/research_attempt_ledger_v3.json"
)
LEDGER_V4_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_131/research_attempt_ledger_v4.json"
)
LEDGER_V5_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_131/research_attempt_ledger_v5.json"
)
LEDGER_V6_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_131/research_attempt_ledger_v6.json"
)
LEDGER_V7_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_131/research_attempt_ledger_v7.json"
)
RESULT_V7_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_131_terminal_result_v7_20260814.json"
)
POLICY_V158_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v158_20260814.json"
)
SIGNAL_LEDGER_PATH = (
    REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
REPORT_PATHS = [
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_131_terminal_report.md",
    REPO_ROOT / "data/experiments/short_horizon/current_research_report.md",
    REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_campaign131_finite_catalog_terminalizes_before_values() -> None:
    concept = load_json(CONCEPT_PATH)
    frontier = load_json(FRONTIER_PATH)
    catalog = concept["finite_prevalue_concept_catalog"]
    assert len(catalog) == 6
    assert concept["selection"]["selected_candidate_count"] == 0
    assert all(
        item["formula_direction_parameters_or_filters_frozen"] is False
        for item in catalog
    )
    assert concept["recordkeeping"]["selected_only_reporting_used"] is False
    assert (
        frontier["mandatory_prevalue_gate"][
            "candidate_formula_direction_parameters_filters_subset_or_model_admitted"
        ]
        is False
    )
    assert (
        frontier["terminal_decision"][
            "campaign131_source_acceptance_coverage_uniqueness_or_return_audit_run"
        ]
        is False
    )
    assert frontier["research_boundary"]["campaign131_comparator_values_read"] is False
    assert frontier["research_boundary"]["stress_2024_2025_opened"] is False


def test_campaign131_append_only_ledger_chain_and_accounting() -> None:
    v1 = load_json(LEDGER_V1_PATH)
    v2 = load_json(LEDGER_V2_PATH)
    v3 = load_json(LEDGER_V3_PATH)
    v4 = load_json(LEDGER_V4_PATH)
    v5 = load_json(LEDGER_V5_PATH)
    v6 = load_json(LEDGER_V6_PATH)
    v7 = load_json(LEDGER_V7_PATH)
    previous = v1["genesis_previous_entry_sha256"]
    for entry in v1["entries"]:
        assert entry["previous_entry_sha256"] == previous
        material = "|".join(
            [
                "campaign131",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        assert hashlib.sha256(material.encode()).hexdigest() == entry["entry_sha256"]
        previous = entry["entry_sha256"]
    assert previous == v1["chain_tip_sha256"]

    base = v2["base_ledger"]
    assert base["sha256"] == sha256(LEDGER_V1_PATH)
    assert base["chain_tip_sha256"] == v1["chain_tip_sha256"]
    appended = v2["appended_entries"][0]
    material = "|".join(
        [
            "campaign131",
            appended["attempt_id"],
            appended["previous_entry_sha256"],
            appended["phase"],
            appended["status"],
        ]
    )
    assert hashlib.sha256(material.encode()).hexdigest() == appended["entry_sha256"]
    assert v2["chain_tip_sha256"] == appended["entry_sha256"]
    base = v3["base_ledger"]
    assert base["sha256"] == sha256(LEDGER_V2_PATH)
    assert base["chain_tip_sha256"] == v2["chain_tip_sha256"]
    appended = v3["appended_entries"][0]
    material = "|".join(
        [
            "campaign131",
            appended["attempt_id"],
            appended["previous_entry_sha256"],
            appended["phase"],
            appended["status"],
        ]
    )
    assert hashlib.sha256(material.encode()).hexdigest() == appended["entry_sha256"]
    assert v3["chain_tip_sha256"] == appended["entry_sha256"]
    base = v4["base_ledger"]
    assert base["sha256"] == sha256(LEDGER_V3_PATH)
    assert base["chain_tip_sha256"] == v3["chain_tip_sha256"]
    appended = v4["appended_entries"][0]
    material = "|".join(
        [
            "campaign131",
            appended["attempt_id"],
            appended["previous_entry_sha256"],
            appended["phase"],
            appended["status"],
        ]
    )
    assert hashlib.sha256(material.encode()).hexdigest() == appended["entry_sha256"]
    assert v4["chain_tip_sha256"] == appended["entry_sha256"]
    base = v5["base_ledger"]
    assert base["sha256"] == sha256(LEDGER_V4_PATH)
    assert base["chain_tip_sha256"] == v4["chain_tip_sha256"]
    appended = v5["appended_entries"][0]
    material = "|".join(
        [
            "campaign131",
            appended["attempt_id"],
            appended["previous_entry_sha256"],
            appended["phase"],
            appended["status"],
        ]
    )
    assert hashlib.sha256(material.encode()).hexdigest() == appended["entry_sha256"]
    assert v5["chain_tip_sha256"] == appended["entry_sha256"]
    base = v6["base_ledger"]
    assert base["sha256"] == sha256(LEDGER_V5_PATH)
    assert base["chain_tip_sha256"] == v5["chain_tip_sha256"]
    appended = v6["appended_entries"][0]
    material = "|".join(
        [
            "campaign131",
            appended["attempt_id"],
            appended["previous_entry_sha256"],
            appended["phase"],
            appended["status"],
        ]
    )
    assert hashlib.sha256(material.encode()).hexdigest() == appended["entry_sha256"]
    assert v6["chain_tip_sha256"] == appended["entry_sha256"]
    base = v7["base_ledger"]
    assert base["sha256"] == sha256(LEDGER_V6_PATH)
    assert base["chain_tip_sha256"] == v6["chain_tip_sha256"]
    appended = v7["appended_entries"][0]
    material = "|".join(
        [
            "campaign131",
            appended["attempt_id"],
            appended["previous_entry_sha256"],
            appended["phase"],
            appended["status"],
        ]
    )
    assert hashlib.sha256(material.encode()).hexdigest() == appended["entry_sha256"]
    assert v7["chain_tip_sha256"] == appended["entry_sha256"]
    assert v7["attempt_count"] == 8
    assert v7["infrastructure_failure_count"] == 7
    assert v7["prevalue_scientific_attempt_count"] == 1
    assert v7["cumulative_historical_research_attempt_count"] == 1072
    assert v7["cumulative_return_reading_development_trial_count"] == 307


def test_campaign131_terminal_result_and_v158_preserve_library() -> None:
    result = load_json(RESULT_V7_PATH)
    policy = load_json(POLICY_V158_PATH)
    assert result["authoritative_inputs"]["campaign131_attempt_ledger_v7"][
        "sha256"
    ] == sha256(LEDGER_V7_PATH)
    assert policy["authoritative_inputs"]["campaign131_terminal_result_v7"][
        "sha256"
    ] == sha256(RESULT_V7_PATH)
    assert result["scientific_result"]["selected_candidate_count"] == 0
    assert result["effective_accounting"]["campaign131_attempt_count"] == 8
    assert policy["version"] == 158
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 151
    )
    assert (
        policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"]
        == 140
    )
    assert policy["future_campaign_boundary"]["next_campaign"] == 132
    assert (
        policy["research_boundary"][
            "historical_daily_price_or_forward_return_values_read"
        ]
        is False
    )


def test_candidate49_and_reports_remain_semantically_unchanged() -> None:
    result = load_json(RESULT_V7_PATH)
    signal = load_json(SIGNAL_LEDGER_PATH)
    execution = load_json(EXECUTION_LEDGER_PATH)
    assert signal["entries"] == []
    assert execution["entries"] == []
    assert sha256(SIGNAL_LEDGER_PATH) == result["candidate49"]["signal_ledger_sha256"]
    assert (
        sha256(EXECUTION_LEDGER_PATH)
        == result["candidate49"]["execution_ledger_sha256"]
    )
    assert result["candidate49"]["historical_backfill_performed"] is False
    for path in REPORT_PATHS:
        report = path.read_text(encoding="utf-8")
        assert "Campaign131" in report
        assert "1072" in report
        assert "Campaign132" in report
