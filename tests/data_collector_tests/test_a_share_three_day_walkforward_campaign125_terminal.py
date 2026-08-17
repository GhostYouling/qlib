import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCOUTING_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_125_concept_scouting_20260814.json"
)
FRONTIER_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_125_mechanism_source_frontier_audit_20260814.json"
)
POLICY_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v129_20260814.json"
)
LEDGER_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_125/research_attempt_ledger_v1.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_finite_catalog_rejects_every_concept_before_values() -> None:
    scouting = load_json(SCOUTING_PATH)
    catalog = scouting["finite_prevalue_concept_catalog"]
    assert len(catalog) == 6
    assert all(item["decision"].startswith("rejected_before") for item in catalog)
    decision = scouting["prevalue_decision"]
    assert decision["selected_candidate_count"] == 0
    assert decision["campaign125_candidate_formula_frozen"] is False
    assert decision["campaign125_source_or_candidate_values_may_be_read"] is False
    boundary = scouting["research_boundary"]
    assert boundary["programmatic_provider_request_issued"] is False
    assert boundary["campaign125_candidate_values_computed_or_read"] is False
    assert boundary["historical_forward_returns_read"] is False


def test_frontier_and_v129_preserve_149_139_orders() -> None:
    frontier = load_json(FRONTIER_PATH)
    assert frontier["concept_scouting"]["sha256"] == sha256(SCOUTING_PATH)
    assert (
        frontier["terminal_decision"]["campaign125_complete_factor_definition_created"]
        is False
    )
    assert (
        frontier["terminal_decision"]["campaign125_development_or_stress_trial_run"]
        is False
    )

    policy = load_json(POLICY_PATH)
    complete = policy["complete_historical_feature_library"]
    numeric = policy["numerical_comparator_eligibility"]
    assert (
        complete["factor_definition_count"],
        numeric["eligible_numeric_comparator_count"],
    ) == (149, 139)
    assert (
        complete["order_sha256"]
        == "be9c6085af2202e8fa5b4c6d89608b712b27740b16b5e78d7d88ca0c4d9bc5e3"
    )
    assert (
        numeric["eligible_numeric_comparator_order_sha256"]
        == "9c4de054ca1b83eced67eece256b024ebec3a6e1925de17a4cedfa7d36265161"
    )
    assert (
        policy["campaign125_terminal_classification"]["selected_candidate_count"] == 0
    )


def test_ledger_hash_chain_and_accounting() -> None:
    ledger = load_json(LEDGER_PATH)
    previous = ledger["chain_genesis"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        material = (
            "campaign125|"
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
    assert ledger["attempt_count"] == ledger["ledger_entry_count"] == 2
    assert ledger["infrastructure_failure_count"] == 1
    assert ledger["prevalue_scientific_attempt_count"] == 1
    assert ledger["complete_factor_attempt_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 1022
    assert ledger["cumulative_return_reading_development_trial_count"] == 306


def test_candidate49_remains_only_empty_prospective_ledger() -> None:
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
