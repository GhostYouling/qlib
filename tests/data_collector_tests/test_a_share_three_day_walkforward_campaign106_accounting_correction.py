from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
FAILURE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_106_postterminal_attempt_accounting_failure_20260808.json"
LEDGER = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_106/research_attempt_ledger_v4.json"
TERMINAL = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_106_terminal_result_binding_v2_20260808.json"
POLICY = REPO_ROOT / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v65_20260808.json"
STATE = REPO_ROOT / "docs/a_share_three_day_iteration_status_20260808_campaign106_terminal_v2.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_correction_preserves_and_binds_every_prior_node() -> None:
    failure = _load(FAILURE)
    for binding in failure["preserved_inputs"].values():
        path = REPO_ROOT / binding["path"]
        assert path.is_file()
        assert _sha256(path) == binding["sha256"]

    assert failure["failure"]["published"] == 787
    assert failure["failure"]["expected_before_this_discovery"] == 789
    assert failure["failure"]["corrected_cumulative_historical_research_attempt_count"] == 790
    assert failure["scientific_result_changed"] is False


def test_ledger_v4_is_an_exact_append_and_hash_chain_is_valid() -> None:
    ledger = _load(LEDGER)
    prior_path = REPO_ROOT / ledger["supersedes_without_rewriting"]["path"]
    prior = _load(prior_path)
    assert _sha256(prior_path) == ledger["supersedes_without_rewriting"]["sha256"]
    assert ledger["entries"][:3] == prior["entries"]
    assert len(ledger["entries"]) == ledger["attempt_count"] == 4

    previous = ledger["chain_genesis"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign106",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        assert entry["entry_sha256"] == expected
        previous = expected
    assert ledger["chain_tip_sha256"] == previous


def test_corrected_accounting_reconciles_with_campaign105_terminal() -> None:
    ledger = _load(LEDGER)
    failure = _load(FAILURE)
    previous_count = failure["preserved_inputs"]["campaign105_terminal_result"][
        "terminal_cumulative_historical_research_attempt_count"
    ]
    assert previous_count == 786
    assert ledger["attempt_count"] == 4
    assert ledger["infrastructure_failure_count"] == 3
    assert ledger["prevalue_scientific_attempt_count"] == 1
    assert ledger["complete_factor_attempt_count"] == 1
    assert ledger["scientifically_decided_factor_attempt_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == previous_count + ledger["attempt_count"] == 790
    assert ledger["cumulative_return_reading_development_trial_count"] == 300


def test_terminal_policy_and_state_share_one_effective_accounting() -> None:
    terminal = _load(TERMINAL)
    policy = _load(POLICY)
    state = _load(STATE)
    terminal_accounting = terminal["accounting_correction"]
    policy_accounting = policy["final_accounting"]
    state_accounting = state["campaign106_terminal"]

    keys = {
        "campaign106_attempt_count": "attempt_count",
        "campaign106_ledger_entry_count": "ledger_entry_count",
        "campaign106_infrastructure_failure_count": "infrastructure_failure_count",
        "campaign106_complete_factor_attempt_count": "complete_factor_attempt_count",
        "campaign106_scientifically_decided_factor_attempt_count": "scientifically_decided_factor_attempt_count",
        "campaign106_return_reading_complete_development_trial_count": "return_reading_development_trial_count",
        "cumulative_historical_research_attempt_count": "cumulative_historical_research_attempt_count",
        "cumulative_return_reading_development_trial_count": "cumulative_return_reading_development_trial_count",
    }
    for policy_key, state_key in keys.items():
        assert terminal_accounting[policy_key] == policy_accounting[policy_key] == state_accounting[state_key]

    assert state["campaign106_terminal"]["scientific_result"] == "inconclusive_due_to_infrastructure"
    assert policy["complete_historical_feature_library"]["factor_definition_count"] == 136
    assert policy["complete_historical_feature_library"]["order_sha256"] == "2099f016f5979a820b480a83aa28877504ea5238362feed551bb7cf583cbf7d0"
    assert policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"] == 132
    assert policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_order_sha256"] == "7ed69afd1408e84dcc856583344166ffc9bcbb0add1aed63163b1d12a1be9a25"


def test_state_bindings_and_reports_are_current() -> None:
    state = _load(STATE)
    bindings = [
        state["campaign106_terminal"]["terminal_result"],
        state["campaign106_terminal"]["research_attempt_ledger"],
        state["campaign106_terminal"]["accounting_failure_record"],
        state["effective_future_numeric_policy"],
        *state["reports"].values(),
    ]
    for binding in bindings:
        path = REPO_ROOT / binding["path"]
        assert path.is_file()
        assert _sha256(path) == binding["sha256"]

    assert state["provider_credential"]["repository_dotenv_mode"] == "0600"
    assert state["provider_credential"]["tushare_token_nonempty"] is True
    assert state["provider_credential"]["secret_printed_hashed_logged_or_persisted"] is False
    assert state["weekend_boundary"]["candidate49_plan_or_run_executed"] is False
    assert state["research_boundary"]["campaign107_values_read_before_effective_protocol"] is False
