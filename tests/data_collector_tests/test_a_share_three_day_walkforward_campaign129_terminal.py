import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCOUTING_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_129_concept_scouting_20260814.json"
)
FRONTIER_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_129_mechanism_source_frontier_audit_20260814.json"
)
POLICY_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v147_20260814.json"
)
BASE_LEDGER_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_129/research_attempt_ledger_v3.json"
)
LEDGER_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_129/research_attempt_ledger_v4.json"
)
TERMINAL_RESULT_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_129_terminal_result_v4_20260814.json"
)
FAILURE_PATHS = [
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_129_credential_presence_shell_quote_failure_20260814.json",
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_129_definition_listing_python_quote_failure_20260814.json",
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_129_unified_report_append_patch_context_failure_20260814.json",
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_129_terminal_test_black_check_failure_20260814.json",
]
TIMESTAMP_FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_129_terminal_metadata_future_timestamp_failure_20260814.json"
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
            "create_campaign129_formula_feature_or_model_implementation"
        ]
        is False
    )
    boundary = scouting["research_boundary"]
    assert boundary["programmatic_provider_request_issued"] is False
    assert boundary["campaign129_candidate_values_computed_or_read"] is False
    assert boundary["historical_forward_returns_read"] is False
    assert boundary["inherited_current_listing_survivorship_limitation_remains"]


def test_frontier_result_and_v147_preserve_151_140_orders() -> None:
    frontier = load_json(FRONTIER_PATH)
    assert frontier["concept_scouting"]["sha256"] == sha256(SCOUTING_PATH)
    terminal = frontier["terminal_decision"]
    assert terminal["campaign129_complete_factor_definition_created"] is False
    assert terminal["campaign129_development_or_stress_trial_run"] is False

    result = load_json(TERMINAL_RESULT_PATH)
    assert result["scientific_result"]["selected_candidate_count"] == 0
    assert result["effective_accounting"]["campaign129_attempt_count"] == 6

    policy = load_json(POLICY_PATH)
    complete = policy["complete_historical_feature_library"]
    numeric = policy["numerical_comparator_eligibility"]
    assert (
        complete["factor_definition_count"],
        numeric["eligible_numeric_comparator_count"],
    ) == (151, 140)
    assert complete["order_sha256"] == (
        "91c2da3018330edbaddbb60b86370dcd9732425590f0565c70790b990002e0b5"
    )
    assert numeric["eligible_numeric_comparator_order_sha256"] == (
        "c71bfe27486c9567afd3aca21e4b04053658c23ac651e7f4df7fd014b0c31efd"
    )
    assert (
        policy["campaign129_terminal_classification"]["selected_candidate_count"] == 0
    )


def test_ledger_hash_chain_bindings_and_accounting() -> None:
    base = load_json(BASE_LEDGER_PATH)
    previous = base["chain_genesis"]
    for entry in base["entries"]:
        assert entry["previous_entry_sha256"] == previous
        material = (
            "campaign129|"
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
    assert base["chain_tip_sha256"] == previous
    for entry, path in zip(base["entries"][1:], FAILURE_PATHS, strict=True):
        assert entry["failure_record"]["sha256"] == sha256(path)

    ledger = load_json(LEDGER_PATH)
    assert ledger["base_ledger"]["sha256"] == sha256(BASE_LEDGER_PATH)
    assert ledger["base_ledger"]["chain_tip_sha256"] == previous
    for entry in ledger["appended_entries"]:
        assert entry["previous_entry_sha256"] == previous
        material = (
            "campaign129|"
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
    assert ledger["attempt_count"] == ledger["ledger_entry_count"] == 6
    assert ledger["infrastructure_failure_count"] == 5
    assert ledger["prevalue_scientific_attempt_count"] == 1
    assert ledger["complete_factor_attempt_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 1057
    assert ledger["cumulative_return_reading_development_trial_count"] == 307
    assert ledger["appended_entries"][0]["failure_record"]["sha256"] == sha256(
        TIMESTAMP_FAILURE_PATH
    )


def test_candidate49_remains_only_empty_prospective_ledger() -> None:
    signal = (
        REPO_ROOT
        / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    )
    execution = (
        REPO_ROOT
        / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert sha256(signal) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert sha256(execution) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert load_json(signal)["entries"] == []
    assert load_json(execution)["entries"] == []


def test_unified_reports_record_campaign129_without_trading_output() -> None:
    for relative in [
        "data/experiments/short_horizon/current_research_report.md",
        "data/experiments/short_horizon/three_day_research_report.md",
    ]:
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        section = text.split("## Campaign129 值前零候选终止", maxsplit=1)[1]
        assert "选中 0 个候选" in section
        assert "累计历史尝试 `1057`" in section
        assert "Campaign130" in section
        assert "选股" not in section
        assert "订单" not in section
