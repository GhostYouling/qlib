import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign121_features as c121

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = REPO_ROOT / "docs"
SCOUTING_PATH = (
    DOCS / "a_share_three_day_walkforward_campaign_128_concept_scouting_20260814.json"
)
AUDIT_PATH = (
    DOCS
    / "a_share_three_day_walkforward_campaign_128_mechanism_overlap_audit_20260814.json"
)
PROTOCOL_PATH = (
    DOCS
    / "a_share_three_day_walkforward_campaign_128_no_return_preregistration_20260814.json"
)
FORMULA_FREEZE_PATH = (
    DOCS
    / "a_share_three_day_walkforward_campaign_128_formula_implementation_freeze_20260814.json"
)
STATUS_PATH = (
    DOCS / "a_share_three_day_iteration_status_20260814_campaign128_formula_frozen.json"
)
POLICY_PATH = (
    DOCS
    / "a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v137_20260814.json"
)
LEDGER_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_128/research_attempt_ledger_v2.json"
)
FORMULA_PATH = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign128_formula.py"
)
FORMULA_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign128_formula.py"
)
OUTPUT_ROOT = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign128_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign128_feature_library_v1"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def order_digest(items: list[dict[str, str]]) -> str:
    payload = json.dumps(
        [[item["name"], item["score_direction"]] for item in items],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def test_finite_catalog_selects_exactly_one_before_values() -> None:
    scouting = load_json(SCOUTING_PATH)
    catalog = scouting["finite_prevalue_concept_catalog"]
    assert len(catalog) == 6
    assert [item["decision"].startswith("selected_") for item in catalog].count(
        True
    ) == 1
    selected = scouting["selected_candidate"]
    assert selected["selected_candidate_count"] == 1
    assert selected["name"] == ("intraday_transaction_price_dispersion_resolution_2h")
    assert selected["score_direction"] == "higher"
    boundary = scouting["research_boundary"]
    assert boundary["minute_source_rows_read"] is False
    assert boundary["candidate_or_comparison_values_read"] is False


def test_semantic_audit_and_protocol_freeze_one_formula() -> None:
    audit = load_json(AUDIT_PATH)
    assert audit["authoritative_inputs"]["concept_scouting"]["sha256"] == sha256(
        SCOUTING_PATH
    )
    decision = audit["semantic_decision"]
    assert decision["complete_definition_count_reviewed"] == 150
    assert decision["selected_candidate_count"] == 1
    assert decision["numeric_distinctness_established"] is False

    protocol = load_json(PROTOCOL_PATH)
    assert protocol["authoritative_inputs"]["mechanism_overlap_audit"][
        "sha256"
    ] == sha256(AUDIT_PATH)
    candidate = protocol["candidate"]
    assert candidate["source_projection"] == [
        "datetime",
        "symbol",
        "provider",
        "volume",
        "amount",
    ]
    assert candidate["exact_formula"]["score"] == "(D_m-D_a)/(D_m+D_a)"
    assert candidate["search_space"]["candidate_count"] == 1
    assert protocol["comparison_contract"]["numeric_comparator_count"] == 139


def test_complete_definition_and_comparator_orders_reconstruct() -> None:
    definitions = c121.reconstruct_complete_definitions() + [
        {
            "name": "official_pure_security_rename_recency_60s",
            "score_direction": "higher",
        },
        {
            "name": "ipo_retail_ballot_scarcity_20to79s",
            "score_direction": "higher",
        },
        {
            "name": "convertible_issue_online_demand_180d",
            "score_direction": "higher",
        },
    ]
    assert len(definitions) == 150
    assert order_digest(definitions) == (
        "c3713559f968c7f79b070398742ef625733e9c178d4e0c0010805fa12c5d5142"
    )
    definitions.append(
        {
            "name": "intraday_transaction_price_dispersion_resolution_2h",
            "score_direction": "higher",
        }
    )
    assert len(definitions) == 151
    assert order_digest(definitions) == (
        "91c2da3018330edbaddbb60b86370dcd9732425590f0565c70790b990002e0b5"
    )

    comparators = c121.reconstruct_comparisons() + [
        {"name": c121.FACTOR_NAME, "score_direction": "higher"}
    ]
    assert len(comparators) == 139
    assert order_digest(comparators) == (
        "9c4de054ca1b83eced67eece256b024ebec3a6e1925de17a4cedfa7d36265161"
    )


def test_formula_freeze_binds_tested_bytes() -> None:
    freeze = load_json(FORMULA_FREEZE_PATH)
    frozen = freeze["frozen_formula"]
    assert frozen["implementation"]["sha256"] == sha256(FORMULA_PATH)
    assert frozen["synthetic_tests"]["sha256"] == sha256(FORMULA_TEST_PATH)
    assert freeze["verification"]["synthetic_pytest"].startswith("8 passed")
    assert freeze["research_boundary"]["minute_source_rows_read"] is False


def test_append_only_ledger_chain_and_accounting() -> None:
    ledger = load_json(LEDGER_PATH)
    previous = ledger["chain_genesis"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        material = (
            "campaign128|"
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
    assert ledger["attempt_count"] == ledger["ledger_entry_count"] == 4
    assert ledger["infrastructure_failure_count"] == 2
    assert ledger["prevalue_scientific_attempt_count"] == 2
    assert ledger["complete_factor_attempt_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 1037
    assert ledger["cumulative_return_reading_development_trial_count"] == 306


def test_v137_keeps_candidate_non_numeric_before_snapshot() -> None:
    policy = load_json(POLICY_PATH)
    complete = policy["complete_historical_feature_library"]
    numeric = policy["numerical_comparator_eligibility"]
    gate = policy["campaign128_gate_state"]
    assert complete["factor_definition_count"] == 151
    assert complete["order_sha256"] == (
        "91c2da3018330edbaddbb60b86370dcd9732425590f0565c70790b990002e0b5"
    )
    assert numeric["eligible_numeric_comparator_count"] == 139
    assert numeric["campaign128_definition_eligible_now"] is False
    assert gate["source_bound_builder_implementation_allowed"] is True
    assert gate["historical_snapshot_build_allowed_now"] is False
    assert not OUTPUT_ROOT.exists()


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


def test_active_status_binds_latest_policy_ledger_reports_and_closed_gates() -> None:
    status = load_json(STATUS_PATH)
    assert status["status"] == (
        "campaign128_formula_frozen_v137_source_bound_builder_implementation_next"
    )
    assert status["authoritative_boundaries"]["numeric_policy"]["sha256"] == sha256(
        POLICY_PATH
    )
    assert status["campaign128_authoritative_artifacts"]["research_attempt_ledger"][
        "sha256"
    ] == sha256(LEDGER_PATH)
    for item in status["reports"].values():
        assert item["sha256"] == sha256(REPO_ROOT / item["path"])
    assert status["validation"]["prevalue_test"]["sha256"] == sha256(Path(__file__))
    assert (
        status["effective_accounting"]["cumulative_historical_research_attempt_count"]
        == 1037
    )
    assert status["frozen_candidate"]["source_bound_builder_frozen"] is False
    assert (
        status["research_boundary"]["campaign128_historical_minute_source_rows_read"]
        is False
    )
    assert status["candidate49_daily_20260814"]["candidate49_plan_executed"] is False
