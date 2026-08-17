from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
LEDGER_V4 = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_106/research_attempt_ledger_v4.json"
LEDGER_V5 = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_106/research_attempt_ledger_v5.json"
TERMINAL = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_106_terminal_result_binding_v3_20260808.json"
POLICY = REPO_ROOT / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v66_20260808.json"
STATE = REPO_ROOT / "docs/a_share_three_day_iteration_status_20260808_campaign106_terminal_v3.json"
FAILURE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_106_accounting_correction_test_field_alias_failure_20260808.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_failed_test_and_790_count_nodes_are_preserved() -> None:
    failure = _load(FAILURE)
    failed_test = REPO_ROOT / failure["failed_test"]["path"]
    assert _sha256(failed_test) == failure["failed_test"]["sha256"]
    assert failure["failed_test"]["result"] == "8 passed, 1 failed"
    assert failure["scientific_or_accounting_value_mismatch_detected"] is False
    for binding in failure["preserved_published_nodes"].values():
        path = REPO_ROOT / binding["path"]
        assert _sha256(path) == binding["sha256"]


def test_ledger_v5_adds_exactly_one_valid_chain_node() -> None:
    prior = _load(LEDGER_V4)
    ledger = _load(LEDGER_V5)
    superseded = ledger["supersedes_without_rewriting"]
    assert _sha256(LEDGER_V4) == superseded["sha256"]
    assert superseded["entry_count"] == len(prior["entries"]) == 4
    assert len(ledger["appended_entries"]) == 1
    entry = ledger["appended_entries"][0]
    assert entry["previous_entry_sha256"] == prior["chain_tip_sha256"]
    payload = "|".join(
        [
            "campaign106",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        ]
    )
    assert entry["entry_sha256"] == hashlib.sha256(payload.encode("utf-8")).hexdigest()
    assert ledger["chain_tip_sha256"] == entry["entry_sha256"]
    assert ledger["attempt_count"] == ledger["ledger_entry_count"] == 5
    assert ledger["infrastructure_failure_count"] == 4
    assert ledger["prevalue_scientific_attempt_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 786 + 5 == 791


def test_alias_aware_accounting_is_numerically_identical() -> None:
    terminal = _load(TERMINAL)["accounting"]
    policy = _load(POLICY)["final_accounting"]
    state = _load(STATE)["campaign106_terminal"]
    common = {
        "campaign106_attempt_count": "attempt_count",
        "campaign106_ledger_entry_count": "ledger_entry_count",
        "campaign106_infrastructure_failure_count": "infrastructure_failure_count",
        "campaign106_complete_factor_attempt_count": "complete_factor_attempt_count",
        "campaign106_scientifically_decided_factor_attempt_count": "scientifically_decided_factor_attempt_count",
        "cumulative_historical_research_attempt_count": "cumulative_historical_research_attempt_count",
        "cumulative_return_reading_development_trial_count": "cumulative_return_reading_development_trial_count",
    }
    for key, state_key in common.items():
        assert terminal[key] == policy[key] == state[state_key]
    assert terminal["campaign106_return_reading_complete_development_trial_count"] == 0
    assert policy["campaign106_return_reading_development_trial_count"] == 0
    assert state["return_reading_development_trial_count"] == 0


def test_scientific_and_library_semantics_did_not_change() -> None:
    terminal = _load(TERMINAL)
    policy = _load(POLICY)
    state = _load(STATE)
    assert terminal["scientific_result_changed"] is False
    assert terminal["preserved_scientific_terminal_semantics"]["scientific_admissibility"] == "inconclusive_due_to_infrastructure"
    assert state["campaign106_terminal"]["scientific_result"] == "inconclusive_due_to_infrastructure"
    assert policy["complete_historical_feature_library"]["factor_definition_count"] == 136
    assert policy["complete_historical_feature_library"]["order_sha256"] == "2099f016f5979a820b480a83aa28877504ea5238362feed551bb7cf583cbf7d0"
    assert policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"] == 132
    assert policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_order_sha256"] == "7ed69afd1408e84dcc856583344166ffc9bcbb0add1aed63163b1d12a1be9a25"


def test_current_state_bindings_reports_and_safety_boundaries() -> None:
    state = _load(STATE)
    bindings = [
        state["campaign106_terminal"]["terminal_result"],
        state["campaign106_terminal"]["research_attempt_ledger"],
        state["campaign106_terminal"]["latest_failure"],
        state["effective_future_numeric_policy"],
        *state["reports"].values(),
    ]
    for binding in bindings:
        path = REPO_ROOT / binding["path"]
        assert _sha256(path) == binding["sha256"]
    assert state["provider_credential"]["repository_dotenv_mode"] == "0600"
    assert state["provider_credential"]["tushare_token_nonempty"] is True
    assert state["provider_credential"]["secret_printed_hashed_logged_or_persisted"] is False
    assert state["weekend_boundary"]["candidate49_plan_or_run_executed"] is False
    assert state["candidate49"]["signal_ledger_entry_count"] == 0
    assert state["candidate49"]["execution_ledger_entry_count"] == 0
    assert state["research_boundary"]["campaign107_values_read_before_effective_protocol"] is False
