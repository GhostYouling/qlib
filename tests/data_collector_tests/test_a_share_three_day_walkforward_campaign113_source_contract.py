import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_official_exchange_enforcement_source_contract_20260809.json"
)
RESULT_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_113_source_contract_freeze_result_20260809.json"
)
LEDGER_PATH = (
    REPO_ROOT
    / "data"
    / "experiments"
    / "short_horizon"
    / "historical_walkforward"
    / "campaign_113"
    / "research_attempt_ledger_v1.json"
)
POLICY_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v75_20260809.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_source_contract_is_zero_row_and_pre_formula() -> None:
    contract = load_json(CONTRACT_PATH)
    assert contract["status"].startswith("frozen_zero_programmatic_rows")
    assert contract["mechanism_independence"]["source_state"] == (
        "formal_exchange_enforcement_action"
    )
    assert contract["mechanism_independence"]["factor_formula"] is None
    assert contract["mechanism_independence"]["score_direction"] is None
    boundary = contract["research_boundary"]
    assert boundary["programmatic_source_requests_issued"] is False
    assert boundary["source_rows_persisted_or_counted"] is False
    assert boundary["historical_daily_price_fields_read"] == []
    assert boundary["historical_forward_returns_read"] is False


def test_source_contract_freezes_two_exchange_point_in_time_semantics() -> None:
    contract = load_json(CONTRACT_PATH)
    assert set(contract["official_source_pages"]) == {"sse", "szse"}
    point_in_time = contract["point_in_time_contract"]
    assert point_in_time["same_day_availability_allowed"] is False
    assert point_in_time["holding_period_trading_sessions"] == 3
    canonical = contract["canonicalization_contract"]
    assert canonical["normalized_event_key"] == [
        "exchange",
        "instrument",
        "action_date",
        "action_family",
        "document_href_sha256",
    ]
    assert canonical["provider_value"] == "official_exchange"
    capacity = contract["source_acceptance_and_capacity_contract"]
    assert capacity["historical_scope_after_all_pre_row_gates"][
        "both_exchanges_required"
    ]
    assert capacity["factor_level_capacity_rule_reserved_before_formula"][
        "minimum_complete_cohorts"
    ] == 200


def test_campaign113_result_and_ledger_preserve_append_only_accounting() -> None:
    result = load_json(RESULT_PATH)
    ledger = load_json(LEDGER_PATH)
    assert result["scientific_result"]["complete_factor_definition_count"] == 0
    assert result["scientific_result"]["campaign113_terminal"] is False
    assert result["accounting"]["campaign113_attempt_count"] == 6
    assert result["accounting"]["cumulative_historical_research_attempt_count"] == 833
    assert ledger["append_only"] is True
    assert ledger["attempt_count"] == len(ledger["entries"]) == 6
    assert ledger["infrastructure_failure_count"] == 5
    assert ledger["chain_tip_sha256"] == ledger["entries"][-1]["entry_sha256"]
    previous = ledger["chain_genesis"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        material = (
            "campaign113|"
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


def test_v75_preserves_numeric_library_and_binds_campaign113_records() -> None:
    policy = load_json(POLICY_PATH)
    assert policy["version"] == 75
    assert policy["complete_historical_feature_library"]["factor_definition_count"] == 140
    assert policy["complete_historical_feature_library"][
        "campaign113_definition_appended"
    ] is False
    assert policy["numerical_comparator_eligibility"][
        "eligible_numeric_comparator_count"
    ] == 134
    assert policy["authoritative_inputs"]["campaign113_source_contract"][
        "sha256"
    ] == sha256(CONTRACT_PATH)
    assert policy["authoritative_inputs"][
        "campaign113_source_contract_freeze_result"
    ]["sha256"] == sha256(RESULT_PATH)
    assert policy["authoritative_inputs"]["campaign113_attempt_ledger"][
        "sha256"
    ] == sha256(LEDGER_PATH)


def test_candidate49_ledgers_remain_empty_and_immutable() -> None:
    signal_path = (
        REPO_ROOT
        / "data"
        / "experiments"
        / "short_horizon"
        / "candidate49_future_signal_ledger.json"
    )
    execution_path = (
        REPO_ROOT
        / "data"
        / "experiments"
        / "short_horizon"
        / "candidate49_future_execution_ledger.json"
    )
    assert sha256(signal_path) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert sha256(execution_path) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert load_json(signal_path)["entries"] == []
    assert load_json(execution_path)["entries"] == []
