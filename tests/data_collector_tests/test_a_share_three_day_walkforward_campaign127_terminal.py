import hashlib
import json
import stat
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = REPO_ROOT / "docs"
CAMPAIGN_DIR = (
    REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_127"
)

SCOUTING_PATH = (
    DOCS / "a_share_three_day_walkforward_campaign_127_concept_scouting_20260814.json"
)
FORMULA_FREEZE_PATH = (
    DOCS
    / "a_share_three_day_walkforward_campaign_127_convertible_issue_adapter_formula_freeze_20260814.json"
)
WORKFLOW_FREEZE_PATH = (
    DOCS
    / "a_share_three_day_walkforward_campaign_127_convertible_issue_acceptance_workflow_freeze_20260814.json"
)
TERMINAL_PATH = (
    DOCS
    / "a_share_three_day_walkforward_campaign_127_convertible_issue_source_acceptance_terminal_20260814.json"
)
POLICY_PATH = (
    DOCS
    / "a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v135_20260814.json"
)
LEDGER_V2_PATH = CAMPAIGN_DIR / "research_attempt_ledger_v2.json"
LEDGER_V3_PATH = CAMPAIGN_DIR / "research_attempt_ledger_v3.json"
LEDGER_V4_PATH = CAMPAIGN_DIR / "research_attempt_ledger_v4.json"

ADAPTER_PATH = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign127_convertible_issue.py"
)
ADAPTER_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign127_convertible_issue.py"
)
WORKFLOW_PATH = (
    REPO_ROOT
    / "scripts/a_share_three_day_walkforward_campaign127_convertible_issue_acceptance.py"
)
WORKFLOW_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign127_convertible_issue_acceptance.py"
)

INTENT_PATH = (
    REPO_ROOT
    / "data/metadata/rich_data/runs/campaign127_convertible_issue_acceptance_intent_v1.json"
)
FAILURE_PATH = (
    REPO_ROOT
    / "data/metadata/rich_data/runs/campaign127_convertible_issue_acceptance_failure_v1.json"
)
ACCEPTED_SNAPSHOT_PATH = (
    REPO_ROOT
    / "data/raw/a_share/rich/tushare/cb_issue/snapshots/campaign127_2018_2025_v1.json"
)
ACCEPTED_MANIFEST_PATH = (
    REPO_ROOT
    / "data/metadata/rich_data/runs/campaign127_convertible_issue_acceptance_v1.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_entry(entry: dict, previous: str) -> str:
    assert entry["previous_entry_sha256"] == previous
    material = (
        "campaign127|"
        + entry["attempt_id"]
        + "|"
        + previous
        + "|"
        + entry["phase"]
        + "|"
        + entry["status"]
    )
    assert hashlib.sha256(material.encode()).hexdigest() == entry["entry_sha256"]
    return entry["entry_sha256"]


def test_finite_catalog_formula_and_library_freeze() -> None:
    scouting = load_json(SCOUTING_PATH)
    catalog = scouting["finite_prevalue_concept_catalog"]
    assert len(catalog) == 6
    assert [item["decision"].startswith("selected_") for item in catalog].count(
        True
    ) == 1
    selected = scouting["selected_candidate"]
    assert selected["name"] == "convertible_issue_online_demand_180d"
    assert selected["selected_candidate_count"] == 1
    assert selected["score_direction"] == "higher"
    assert selected["maximum_event_age_calendar_days"] == 180

    freeze = load_json(FORMULA_FREEZE_PATH)
    definition = freeze["single_factor_definition"]
    assert definition["name"] == selected["name"]
    assert "log1p(onl_pch_excess)" in definition["formula"]
    library = freeze["complete_library_semantic_review"]
    assert library["complete_definition_count_after_append"] == 150
    assert library["complete_definition_order_sha256_after_append"] == (
        "c3713559f968c7f79b070398742ef625733e9c178d4e0c0010805fa12c5d5142"
    )
    assert library["eligible_numeric_comparator_count_reserved_without_values"] == 139


def test_frozen_implementations_and_workflow_bytes() -> None:
    assert sha256(ADAPTER_PATH) == (
        "1edcd09dcb9b6ede6a574f8a55218b2cba993b992a94eabce1ab90d207d27c2b"
    )
    assert sha256(ADAPTER_TEST_PATH) == (
        "58d25ac17b386e499e794e7dd6b44faed062af284633879f71abcb849dc23bb9"
    )
    assert sha256(WORKFLOW_PATH) == (
        "3b3536dd13920c72f28c8dba08f5abf4dccf016003b68ab80702e612ac8d9d44"
    )
    assert sha256(WORKFLOW_TEST_PATH) == (
        "2acb138ecb1fea8169e8eb1ab49b81f3f68cb4a013350de8638501b03250d890"
    )
    workflow_freeze = load_json(WORKFLOW_FREEZE_PATH)
    assert workflow_freeze["frozen_request_schedule"]["maximum_provider_calls"] == 9


def test_one_shot_terminal_semantics_and_private_records() -> None:
    terminal = load_json(TERMINAL_PATH)
    plan = terminal["plan_evidence"]
    run = terminal["run_evidence"]
    assert plan["exit_code"] == 0
    assert plan["ready"] is True
    assert plan["all_29_checks_passed"] is True
    assert run["exit_code"] == 2
    assert run["provider_calls_issued"] == 9
    assert run["retry_performed"] is False
    assert run["failure_code"] == ("source_schema_or_canonicalization_contract_failure")

    assert sha256(INTENT_PATH) == (
        "c1bbad697b44feb3eb6344a7bb029b3314ff33a85653daaa1e4fc525b43035dd"
    )
    assert sha256(FAILURE_PATH) == (
        "ed835f03abce21e65604efc75edaf0ee178d5005bdc391f36856f00dbcab347b"
    )
    assert stat.S_IMODE(INTENT_PATH.stat().st_mode) == 0o600
    assert stat.S_IMODE(FAILURE_PATH.stat().st_mode) == 0o600
    failure = load_json(FAILURE_PATH)
    assert failure["raw_provider_rows_or_counts_persisted"] is False
    assert failure["candidate_comparator_price_or_return_values_read"] is False
    assert not ACCEPTED_SNAPSHOT_PATH.exists()
    assert not ACCEPTED_MANIFEST_PATH.exists()


def test_append_only_ledger_chain_and_final_accounting() -> None:
    ledger_v2 = load_json(LEDGER_V2_PATH)
    previous = ledger_v2["chain_genesis"]
    for entry in ledger_v2["entries"]:
        previous = validate_entry(entry, previous)
    assert previous == ledger_v2["chain_tip_sha256"]

    ledger_v3 = load_json(LEDGER_V3_PATH)
    assert ledger_v3["supersedes_without_rewriting"]["sha256"] == sha256(LEDGER_V2_PATH)
    for entry in ledger_v3["appended_entries"]:
        previous = validate_entry(entry, previous)
    assert previous == ledger_v3["chain_tip_sha256"]

    ledger_v4 = load_json(LEDGER_V4_PATH)
    assert ledger_v4["supersedes_without_rewriting"]["sha256"] == sha256(LEDGER_V3_PATH)
    for entry in ledger_v4["appended_entries"]:
        previous = validate_entry(entry, previous)
    assert previous == ledger_v4["chain_tip_sha256"]
    assert ledger_v4["attempt_count"] == ledger_v4["ledger_entry_count"] == 8
    assert ledger_v4["infrastructure_failure_count"] == 4
    assert ledger_v4["prevalue_scientific_attempt_count"] == 4
    assert ledger_v4["source_acceptance_attempt_count"] == 1
    assert ledger_v4["return_reading_complete_development_trial_count"] == 0
    assert ledger_v4["cumulative_historical_research_attempt_count"] == 1033
    assert ledger_v4["cumulative_return_reading_development_trial_count"] == 306


def test_policy_and_candidate49_preserve_terminal_boundaries() -> None:
    policy = load_json(POLICY_PATH)
    complete = policy["complete_historical_feature_library"]
    numeric = policy["numerical_comparator_eligibility"]
    assert complete["factor_definition_count"] == 150
    assert complete["order_sha256"] == (
        "c3713559f968c7f79b070398742ef625733e9c178d4e0c0010805fa12c5d5142"
    )
    assert numeric["eligible_numeric_comparator_count"] == 139
    assert numeric["eligible_numeric_comparator_order_sha256"] == (
        "9c4de054ca1b83eced67eece256b024ebec3a6e1925de17a4cedfa7d36265161"
    )
    assert policy["future_campaign_boundary"]["next_campaign"] == 128
    assert policy["campaign127_terminal_classification"]["terminal"] is True

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
