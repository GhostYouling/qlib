from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign263_features as features


ROOT = Path(__file__).resolve().parents[2]
SCOUTING = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_265_convertible_premium_concept_scouting_20260824.json"
)
AUDIT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_265_convertible_premium_mechanism_audit_20260824.json"
)
CONTRACT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_265_convertible_premium_source_contract_20260824.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_265/research_attempt_ledger_v1.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_265_prevalue_contract_result_20260824.json"
)
REPORT = (
    ROOT / "docs/a_share_three_day_walkforward_campaign_265_prevalue_contract_report.md"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v416_20260824.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260824_campaign265_prevalue_contract.json"
)
SIGNAL = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION = (
    ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
UNIFIED_REPORTS = (
    ROOT / "data/experiments/short_horizon/current_research_report.md",
    ROOT / "data/experiments/short_horizon/three_day_research_report.md",
)


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve(path: str) -> Path:
    target = Path(path)
    return target if target.is_absolute() else ROOT / target


def _assert_bindings(bindings: dict) -> None:
    for binding in bindings.values():
        target = _resolve(binding["path"])
        assert target.is_file()
        assert _sha256(target) == binding["sha256"]


def _entry_hash(entry: dict) -> str:
    payload = "|".join(
        (
            "campaign265",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def test_prevalue_artifact_hashes_and_reference_graph_are_exact() -> None:
    expected = {
        SCOUTING: "b6c41973c4d13063804adffacc59d938fdea8a1ee6c9fab2b45b711865386837",
        AUDIT: "d31c5260f9ba3f28718b44f2a60b772c7a9472ad4c898bcbe4907aff67d48d93",
        CONTRACT: "efe7884d3ea0fd7f974e0d3347432e68e9e01ceefe0e6ebdca7fdd3e6349301c",
        LEDGER: "f4be9e7abfe336d5b5eb9c799ebb3acbb54d50a9f1dc73f3677a8743096be8fe",
        RESULT: "0f2e3014c56d1d1ef92506166a2c2a9f38c25cf8078bc801cd5b15937d3cd0c8",
        REPORT: "5f3d56bb2da41184e472d41dca74ce3343ec82487c928d6075d8cc853fb81c62",
        POLICY: "1c864ecafbe4d338b5480a34ed9d7f539e51f3afa7f51b261697d166726fe616",
    }
    for path, digest in expected.items():
        assert _sha256(path) == digest
    for artifact in (
        _load(SCOUTING),
        _load(AUDIT),
        _load(CONTRACT),
        _load(RESULT),
        _load(POLICY),
    ):
        _assert_bindings(artifact["authoritative_inputs"])


def test_finite_catalog_selects_only_the_preserved_cross_asset_deferral() -> None:
    scouting = _load(SCOUTING)
    catalog = scouting["finite_prevalue_catalog"]
    assert [item["route_id"] for item in catalog] == [
        "c265_01",
        "c265_02",
        "c265_03",
        "c265_04",
        "c265_05",
        "c265_06",
    ]
    assert (
        catalog[0]["decision"] == "selected_for_zero_row_mechanism_and_source_contract"
    )
    assert all(item["decision"].startswith("rejected_") for item in catalog[1:])
    selection = scouting["selection"]
    assert selection["selected_candidate_count"] == 1
    assert selection["complete_definition_created"] is False
    assert selection["numeric_comparator_eligibility_created"] is False
    assert selection["source_acceptance_authorized_now"] is False
    audit = _load(AUDIT)["audit_decision"]
    assert audit["pass"] is True
    assert audit["may_freeze_zero_row_source_contract"] is True
    assert audit["may_request_provider_rows_now"] is False


def test_source_formula_clock_denominator_and_gates_are_frozen() -> None:
    contract = _load(CONTRACT)
    source = contract["official_source_contract"]
    assert source["minimum_points_required"] == 2000
    assert source["five_thousand_points_required"] is False
    assert source["cb_basic"]["exact_fields"] == [
        "ts_code",
        "cb_type",
        "stk_code",
        "list_date",
        "delist_date",
        "exchange",
    ]
    assert source["cb_daily"]["exact_fields"] == [
        "ts_code",
        "trade_date",
        "amount",
        "cb_over_rate",
    ]
    factor = contract["single_factor_definition"]
    assert factor["name"] == "convertible_bond_equity_parity_premium_compression_3s"
    assert factor["score_direction"] == "higher"
    assert factor["per_bond_formula"] == (
        "cb_over_rate(t_minus_3) - cb_over_rate(t), in percentage points"
    )
    assert "Arithmetic median" in factor["issuer_aggregation"]
    assert factor["no_active_or_no_eligible_bond_semantics"].startswith("missing")
    gates = contract["source_denominator_and_no_return_gates"]
    assert gates["coverage_gates"] == {
        "median_daily_coverage_minimum": 0.95,
        "p05_daily_coverage_minimum": 0.9,
        "p05_eligible_equity_count_minimum": 50,
        "nonconstant_cross_sectional_sessions_minimum": 200,
        "non_overlapping_three_signal_session_cohorts_minimum": 200,
        "observed_calendar_years_minimum": 5,
    }
    uniqueness = gates["ordered_numeric_uniqueness"]
    assert uniqueness["comparator_count"] == 143
    assert uniqueness["strict_absolute_maximum"] == 0.8
    assert uniqueness["minimum_pair_names_per_session"] == 50
    assert uniqueness["minimum_pair_sessions_per_comparator"] == 100
    assert (
        gates["daily_price_or_forward_return_values_may_open_before_all_gates_pass"]
        is False
    )


def test_complete_definition_and_comparator_orders_remain_unchanged() -> None:
    policy = _load(POLICY)
    definitions = features.reconstruct_complete_definitions()
    comparators = features.reconstruct_comparisons()
    comparators.append({"name": features.FACTOR_NAME, "score_direction": "higher"})
    library = policy["complete_historical_feature_library"]
    numeric = policy["numerical_comparator_eligibility"]
    assert len(definitions) == library["factor_definition_count"] == 162
    assert features._order_digest(definitions) == library["order_sha256"]
    assert len(comparators) == numeric["eligible_numeric_comparator_count"] == 143
    assert features._order_digest(comparators) == numeric["order_sha256"]
    assert library["campaign265_definition_appended"] is False
    assert numeric["campaign265_numeric_comparator_appended"] is False


def test_append_only_chain_and_accounting_include_prewrite_failure() -> None:
    ledger = _load(LEDGER)
    previous = ledger["authoritative_predecessor"]["chain_tip_sha256"]
    for ordinal, entry in enumerate(ledger["entries"], 1):
        assert entry["ordinal"] == ordinal
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        previous = entry["entry_sha256"]
    assert len(ledger["entries"]) == ledger["effective_entry_count"] == 7
    assert ledger["effective_prevalue_scientific_attempt_count"] == 6
    assert ledger["effective_infrastructure_failure_attempt_count"] == 1
    assert ledger["effective_complete_factor_attempt_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 2611
    assert ledger["cumulative_return_reading_development_trial_count"] == 315
    assert (
        previous
        == ledger["chain_tip_sha256"]
        == ("5461f13897fa8caf2384083e20008722a58471104656d2cfb4819320409dbce4")
    )


def test_candidate49_values_and_future_stages_remain_closed() -> None:
    policy = _load(POLICY)
    assert _sha256(SIGNAL) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha256(EXECUTION) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert _load(SIGNAL)["entries"] == []
    assert _load(EXECUTION)["entries"] == []
    boundary = policy["campaign265_next_stage_boundary"]
    assert boundary["provider_request_allowed_by_v416"] is False
    assert boundary["credential_load_allowed_by_v416"] is False
    assert boundary["comparator_values_open_before_all_coverage_gates"] is False
    assert (
        boundary["development_returns_open_before_all_143_ordered_uniqueness_gates"]
        is False
    )
    assert boundary["stress_2024_2025_open_without_development_survivor"] is False


def test_unified_reports_and_latest_state_preserve_prevalue_semantics() -> None:
    policy = _load(POLICY)
    heading = "## Campaign265：可转债平价溢价压缩值前合同冻结（2026-08-24）"
    expected = (
        policy["mutable_unified_reports"]["current"]["sha256_at_publication"],
        policy["mutable_unified_reports"]["three_day"]["sha256_at_publication"],
    )
    for path, digest in zip(UNIFIED_REPORTS, expected, strict=True):
        text = path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        assert "2,611" in text
        assert "5,000 积分" in text
        assert _sha256(path) == digest
    state = _load(STATE)
    _assert_bindings({"policy": state["authoritative_policy"]})
    _assert_bindings(state["campaign265_prevalue_stage"]["artifacts"])
    validation = state["campaign265_prevalue_stage"]["validation"]
    target = _resolve(validation["path"])
    assert target.is_file()
    assert _sha256(target) == validation["sha256"]
    assert state["goal"]["status"] == "active"
    assert state["goal"]["current_campaign"] == 265
    assert state["next_action"].startswith("Continue Campaign265")
