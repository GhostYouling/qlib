from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign146_features as c146
from scripts import a_share_three_day_walkforward_campaign151_formula as c151


ROOT = Path(__file__).resolve().parents[2]
SCOUTING = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_151_concept_scouting_20260815.json"
)
AUDIT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_151_mechanism_overlap_audit_20260815.json"
)
PROTOCOL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_151_no_return_preregistration_20260815.json"
)
FREEZE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_151_formula_implementation_freeze_20260815.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_151/research_attempt_ledger_v1.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v204_20260815.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260815_campaign151_formula_frozen.json"
)
REPORT = (
    ROOT / "docs/a_share_three_day_walkforward_campaign_151_formula_frozen_report.md"
)
SIGNAL_LEDGER = (
    ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER = (
    ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bound_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def test_campaign151_selects_one_candidate_before_values() -> None:
    scouting = _load(SCOUTING)
    catalog = scouting["finite_prevalue_concept_catalog"]
    assert len(catalog) == 6
    assert len({item["catalog_id"] for item in catalog}) == 6
    assert len({item["name"] for item in catalog}) == 6
    assert scouting["selection"]["selected_candidate_count"] == 1
    assert scouting["selection"]["selected_candidate"] == c151.FACTOR_NAME
    assert (
        sum(item["prevalue_decision"].startswith("selected_") for item in catalog) == 1
    )
    boundary = scouting["research_boundary"]
    assert boundary["source_rows_or_column_values_read"] is False
    assert boundary["campaign151_candidate_values_computed_or_read"] is False
    assert boundary["campaign151_comparator_values_read"] is False


def test_campaign151_mechanism_audit_passes_only_selected_factor() -> None:
    audit = _load(AUDIT)
    results = audit["proposal_gate_results"]
    assert len(results) == 6
    passed = [item for item in results if item["passed"]]
    assert [item["name"] for item in passed] == [c151.FACTOR_NAME]
    assert passed[0]["semantically_independent_from_terminal_library"] is True
    assert audit["semantic_decision"]["numeric_distinctness_established"] is False
    assert audit["semantic_decision"]["predictive_value_established"] is False


def test_campaign151_protocol_formula_and_policy_library_are_frozen() -> None:
    spec = c151.load_protocol()
    assert spec["candidate"]["name"] == c151.FACTOR_NAME
    definitions = c146.reconstruct_complete_definitions() + [
        {"name": c151.FACTOR_NAME, "score_direction": "higher"}
    ]
    comparisons = c146.reconstruct_comparisons() + [
        {"name": c146.FACTOR_NAME, "score_direction": "higher"}
    ]
    assert len(definitions) == 156
    assert c146._order_digest(definitions) == (
        "928e7eff198f44fa3112d7e8ff94571c1ad18b85a1ee50a38f3896baf555847c"
    )
    assert len(comparisons) == 142
    assert c146._order_digest(comparisons) == (
        "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf"
    )
    policy = _load(POLICY)
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 156
    )
    assert (
        policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"]
        == 142
    )
    assert policy["campaign151_active_classification"]["terminal"] is False


def test_campaign151_append_only_attempt_chain_and_accounting() -> None:
    ledger = _load(LEDGER)
    previous = "0" * 64
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign151",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        assert entry["entry_sha256"] == expected
        assert entry["candidate_comparator_price_or_return_value_read"] is False
        previous = expected
    assert len(ledger["entries"]) == 7
    assert ledger["effective_prevalue_concept_attempt_count"] == 6
    assert ledger["effective_infrastructure_failure_attempt_count"] == 1
    assert ledger["effective_complete_factor_attempt_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 1310
    assert ledger["cumulative_return_reading_development_trial_count"] == 314
    assert ledger["chain_tip_sha256"] == previous


def test_campaign151_publication_bindings_and_candidate49_boundary() -> None:
    for record in (_load(PROTOCOL), _load(FREEZE), _load(POLICY)):
        for binding in record.get("authoritative_inputs", {}).values():
            if not isinstance(binding, dict) or "path" not in binding:
                continue
            path = _bound_path(binding["path"])
            assert _sha(path) == binding["sha256"]
    state = _load(STATE)
    for binding in state["campaign151_authoritative_artifacts"].values():
        assert _sha(_bound_path(binding["path"])) == binding["sha256"]
    assert state["authoritative_boundaries"]["numeric_policy_v204"]["sha256"] == _sha(
        POLICY
    )
    assert state["frozen_candidate"]["historical_snapshot_built"] is False
    assert _sha(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert len(_load(SIGNAL_LEDGER)["entries"]) == 0
    assert len(_load(EXECUTION_LEDGER)["entries"]) == 0
    assert state["candidate49_daily_status"]["accepted_local_trade_session"] is False
    assert state["candidate49_daily_status"]["provider_request_issued"] is False


def test_campaign151_records_have_reached_wall_clock_timestamps() -> None:
    for path in (SCOUTING, AUDIT, PROTOCOL, FREEZE, LEDGER, POLICY, STATE):
        recorded_at = datetime.fromisoformat(_load(path)["recorded_at"])
        modified_at = datetime.fromtimestamp(
            path.stat().st_mtime, tz=recorded_at.tzinfo
        )
        assert recorded_at <= modified_at


def test_campaign151_reports_are_appended_once() -> None:
    heading = "## Campaign151 相对市场成交活跃度时钟因子公式冻结"
    assert c151.FACTOR_NAME in REPORT.read_text(encoding="utf-8")
    for path in (
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        assert path.read_text(encoding="utf-8").count(heading) == 1
