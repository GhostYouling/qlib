import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_official_exchange_enforcement_adapter_formula_freeze_20260809.json"
)
RESULT_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_113_adapter_formula_result_20260809.json"
)
LEDGER_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_113/research_attempt_ledger_v2.json"
)
POLICY_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v76_20260809.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_adapter_and_synthetic_test_hashes_are_frozen() -> None:
    freeze = load_json(FREEZE_PATH)
    implementation = freeze["pure_adapter_freeze"]["implementation"]
    synthetic_tests = freeze["pure_adapter_freeze"]["synthetic_tests"]
    assert sha256(REPO_ROOT / implementation["path"]) == implementation["sha256"]
    assert sha256(REPO_ROOT / synthetic_tests["path"]) == synthetic_tests["sha256"]
    assert freeze["pure_adapter_freeze"]["transport_implementation_present"] is False
    assert (
        freeze["page_metadata_mapping"][
            "programmatic_exchange_list_or_api_request_authorized"
        ]
        is False
    )


def test_exactly_one_formula_is_complete_before_values() -> None:
    freeze = load_json(FREEZE_PATH)
    factor = freeze["single_factor_definition"]
    assert factor["name"] == (
        "official_exchange_enforcement_recovery_session_age_60sessions"
    )
    assert factor["score_direction"] == "higher"
    assert factor["raw_value_range"] == {
        "minimum_inclusive": 0,
        "maximum_inclusive": 59,
    }
    assert factor["historical_candidate_values_materialized"] is False
    assert factor["numeric_comparator_appended_now"] is False
    assert (
        freeze["reserved_numeric_comparison_gate"]["comparison_values_loaded"] is False
    )


def test_result_ledger_and_v76_accounting_are_consistent() -> None:
    result = load_json(RESULT_PATH)
    ledger = load_json(LEDGER_PATH)
    policy = load_json(POLICY_PATH)
    assert result["adapter_and_formula_freeze"]["sha256"] == sha256(FREEZE_PATH)
    assert result["attempt_ledger"]["sha256"] == sha256(LEDGER_PATH)
    assert ledger["attempt_count"] == len(ledger["entries"]) == 9
    assert ledger["infrastructure_failure_count"] == 7
    assert ledger["complete_factor_attempt_count"] == 1
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
    assert policy["version"] == 76
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 141
    )
    assert (
        policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"]
        == 134
    )
    assert policy["authoritative_inputs"]["campaign113_attempt_ledger"][
        "sha256"
    ] == sha256(LEDGER_PATH)


def test_research_boundary_and_candidate49_ledgers_remain_closed() -> None:
    result = load_json(RESULT_PATH)
    assert result["research_boundary"]["programmatic_source_requests_issued"] is False
    assert (
        result["research_boundary"][
            "programmatic_source_rows_read_persisted_or_counted"
        ]
        is False
    )
    assert result["research_boundary"]["historical_daily_price_fields_read"] == []
    assert result["research_boundary"]["historical_forward_returns_read"] is False
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
