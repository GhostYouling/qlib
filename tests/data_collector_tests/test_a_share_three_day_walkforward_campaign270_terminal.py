from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PREREGISTRATION = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_270_facility_flood_source_contract_preregistration_20260824.json"
)
LEDGER_V1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_270/research_attempt_ledger_v1.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_270/research_attempt_ledger_v2.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_270_terminal_source_contract_result_20260824.json"
)
REPORT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_270_terminal_source_contract_report.md"
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
            "campaign270",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def test_preregistration_is_frozen_before_inventory_and_has_six_conjunctive_gates() -> (
    None
):
    assert _sha256(PREREGISTRATION) == (
        "f5f7c24ffca6aa9e5c4853ff199439721b1a6faf5be056fb4e0ea88d340c3053"
    )
    preregistration = _load(PREREGISTRATION)
    _assert_bindings(preregistration["authoritative_inputs"])
    route = preregistration["locked_route"]
    assert route["predecessor_concept_id"] == "c269_01"
    for key in (
        "formula",
        "direction",
        "threshold",
        "spatial_radius",
        "event_window",
        "source_fields",
    ):
        assert route[key] is None
    gates = preregistration["finite_contract_gate_catalog"]
    assert [gate["gate_id"] for gate in gates] == [
        "c270_g01",
        "c270_g02",
        "c270_g03",
        "c270_g04",
        "c270_g05",
        "c270_g06",
    ]
    decision = preregistration["decision_rule"]
    assert decision["terminalize_if_any_gate_fails"] is True
    assert decision["partial_contract_not_admissible"] is True
    assert decision["provider_or_web_access_allowed_by_campaign270"] is False


def test_terminal_result_rejects_all_contract_gates_before_factor_definition() -> None:
    assert _sha256(RESULT) == (
        "b78f742a51823dff5829c0dd7b78ec3348b86c87e975ebfe84283632b2219307"
    )
    result = _load(RESULT)
    _assert_bindings(result["authoritative_inputs"])
    assert result["status"] == (
        "terminal_source_contract_rejected_before_formula_direction_source_rows_or_values"
    )
    gates = result["contract_gate_results"]
    assert len(gates) == 6
    assert all(gate["passed"] is False for gate in gates)
    assert result["decision"]["source_contract_admitted"] is False
    assert result["decision"]["terminalize_c269_01"] is True
    assert result["decision"]["sibling_hazard_or_parameter_rescue_allowed"] is False
    route = result["locked_route"]
    assert route["concept_is_factor"] is False
    assert route["formula"] is None
    assert route["direction"] is None
    assert route["source_fields"] is None


def test_repository_inventory_has_no_accepted_facility_hazard_channel() -> None:
    result = _load(RESULT)
    inventory = result["bounded_repository_inventory"]
    assert inventory["accepted_local_facility_hazard_source_contract_present"] is False
    assert inventory["accepted_local_unconsumed_raw_channel_present"] is False
    counts = inventory["script_implementation_match_counts"]
    assert all(value == 0 for value in counts.values())
    prior = inventory["prior_source_gate_evidence"]
    assert all(value is False for value in prior.values())


def test_append_only_attempt_chain_and_accounting_are_exact() -> None:
    assert _sha256(LEDGER_V1) == (
        "d5d4a76274df2e443321ee0f6c7ab92e964ba379f4c826252658b714b006bb34"
    )
    assert _sha256(LEDGER) == (
        "1e310a1dfa9e64387fbbc5688d536762fee99daf40b14c595496789fd907967f"
    )
    ledgers = [_load(LEDGER_V1), _load(LEDGER)]
    entries = [entry for ledger in ledgers for entry in ledger["entries"]]
    previous = ledgers[0]["authoritative_predecessor"]["chain_tip_sha256"]
    assert len(entries) == ledgers[-1]["effective_entry_count"] == 12
    for ordinal, entry in enumerate(entries, 1):
        assert entry["ordinal"] == ordinal
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        assert entry["candidate_or_comparator_value_read"] is False
        assert entry["return_reading_development_trial"] is False
        previous = entry["entry_sha256"]
    ledger = ledgers[-1]
    assert previous == ledger["chain_tip_sha256"]
    assert sum(not entry["scientific_attempt"] for entry in entries) == 6
    assert sum(entry["scientific_attempt"] for entry in entries) == 6
    assert sum(entry["result_consumed"] for entry in entries) == 6
    assert ledger["effective_complete_factor_attempt_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 2732
    assert ledger["cumulative_return_reading_development_trial_count"] == 315


def test_no_value_provider_stress_or_current_use_boundary_is_closed() -> None:
    for artifact in (
        _load(PREREGISTRATION),
        _load(LEDGER_V1),
        _load(LEDGER),
        _load(RESULT),
    ):
        boundary = artifact["research_boundary"]
        for key, value in boundary.items():
            if key == "repository_metadata_and_prior_terminal_history_read":
                assert value is True
            else:
                assert value is False
    result = _load(RESULT)
    scientific = result["scientific_result"]
    assert scientific["development_trial_count"] == 0
    assert scientific["stress_trial_count_2024_2025"] == 0
    assert scientific["predictive_claim_created"] is False


def test_library_campaign265_and_candidate49_are_unchanged() -> None:
    result = _load(RESULT)
    library = result["library_state"]
    assert library["changed_by_campaign270"] is False
    assert library["complete_factor_definition_count"] == 162
    assert library["eligible_numeric_comparator_count"] == 143
    assert result["campaign265"]["changed_by_campaign270"] is False
    assert result["campaign265"]["v420_policy_present"] is False
    assert result["candidate49"]["same_session_retry_allowed"] is False
    assert result["candidate49"]["campaign270_plan_or_run_executed"] is False
    assert _sha256(SIGNAL) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha256(EXECUTION) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert _load(SIGNAL)["entries"] == []
    assert _load(EXECUTION)["entries"] == []


def test_reports_publish_one_terminal_section_without_a_trading_claim() -> None:
    assert _sha256(REPORT) == (
        "9f5262aab1e29d207a7fc3f8a71e7da26f20d23372b764b84164537190df4f7f"
    )
    report = REPORT.read_text(encoding="utf-8")
    assert "六项门槛全部失败" in report
    assert "预测价值没有被测试" in report
    assert "不授权当前评分、选股、仓位或订单" in report
    for path in UNIFIED_REPORTS:
        text = path.read_text(encoding="utf-8")
        title = "## Campaign270：设施—洪涝来源合同值前终止"
        assert text.count(title) == 1
        section = text.split(title, maxsplit=1)[1]
        assert "六项门全部失败" in section
        assert "预测价值未测试" in section
        assert "Candidate49 当日失败继续封口且账本 0/0" in section
        assert "不构成投资建议" in section
