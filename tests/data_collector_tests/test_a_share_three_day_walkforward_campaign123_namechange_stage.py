import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign121_features as c121

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v121_20260814.json"
)
FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_123_namechange_adapter_formula_freeze_20260814.json"
)
LEDGER_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_123/research_attempt_ledger_v1.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_frozen_adapter_tests_and_source_contract_bindings_are_exact() -> None:
    freeze = load_json(FREEZE_PATH)
    for key in ("implementation", "synthetic_tests"):
        binding = freeze["pure_adapter_freeze"][key]
        assert sha256(REPO_ROOT / binding["path"]) == binding["sha256"]
    source = freeze["authoritative_inputs"]["source_contract"]
    assert sha256(REPO_ROOT / source["path"]) == source["sha256"]
    assert (
        freeze["pure_adapter_freeze"]["transport_or_cli_implementation_present"]
        is False
    )
    assert (
        freeze["single_factor_definition"]["historical_candidate_values_materialized"]
        is False
    )
    assert (
        freeze["single_factor_definition"]["prospective_candidate_registered"] is False
    )


def test_append_only_attempt_chain_and_accounting_are_consistent() -> None:
    ledger = load_json(LEDGER_PATH)
    assert (
        ledger["attempt_count"]
        == ledger["ledger_entry_count"]
        == len(ledger["entries"])
        == 7
    )
    assert ledger["infrastructure_failure_count"] == 5
    assert ledger["prevalue_scientific_attempt_count"] == 2
    assert ledger["complete_factor_attempt_count"] == 1
    previous = ledger["chain_genesis"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        material = (
            "campaign123|"
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
    assert ledger["cumulative_historical_research_attempt_count"] == 1006
    assert ledger["cumulative_return_reading_development_trial_count"] == 306


def test_v121_appends_only_the_logical_definition_not_a_numeric_comparator() -> None:
    policy = load_json(POLICY_PATH)
    prior_complete = c121.reconstruct_complete_definitions()
    complete = prior_complete + [
        {
            "name": "official_pure_security_rename_recency_60s",
            "score_direction": "higher",
        }
    ]
    prior_numeric = c121.reconstruct_comparisons() + [
        {"name": c121.FACTOR_NAME, "score_direction": "higher"}
    ]
    assert (
        len(complete)
        == policy["complete_historical_feature_library"]["factor_definition_count"]
        == 148
    )
    assert (
        c121._order_digest(complete)
        == policy["complete_historical_feature_library"]["order_sha256"]
    )
    assert (
        len(prior_numeric)
        == policy["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_count"
        ]
        == 139
    )
    assert (
        c121._order_digest(prior_numeric)
        == policy["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_order_sha256"
        ]
    )
    assert (
        policy["numerical_comparator_eligibility"][
            "campaign123_definition_eligible_now"
        ]
        is False
    )
    assert (
        policy["research_boundary"]["provider_rows_read_persisted_or_counted"] is False
    )


def test_candidate49_ledgers_remain_empty_and_byte_stable() -> None:
    signal = (
        REPO_ROOT
        / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    )
    execution = (
        REPO_ROOT
        / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert (
        sha256(signal)
        == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert (
        sha256(execution)
        == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert load_json(signal)["entries"] == []
    assert load_json(execution)["entries"] == []
