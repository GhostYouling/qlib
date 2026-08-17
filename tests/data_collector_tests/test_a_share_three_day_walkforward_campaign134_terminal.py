from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign133_finalize as chain


ROOT = Path(__file__).resolve().parents[2]
RUN_ROOT = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_134/walkforward_v1"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_134_terminal_result_20260814.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v161_20260814.json"
)
STATE = (
    ROOT / "docs/a_share_three_day_iteration_status_20260814_campaign134_terminal.json"
)


def _load(path: Path) -> dict:
    return chain.load_json(path)


def _resolve(path: str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


def test_campaign134_ledger_chain_and_zero_validation_return_semantics() -> None:
    ledger = _load(RUN_ROOT / "trial_ledger.json")
    assert chain.validate_chain(ledger) == ledger["chain_tip_sha256"]
    assert ledger["entry_count"] == 9
    assert ledger["prevalue_concept_attempt_count"] == 6
    assert ledger["infrastructure_failure_attempt_count"] == 2
    trial = ledger["entries"][-1]
    assert trial["status"] == "development_rejected"
    assert (
        trial["terminal_before_validation_return_reason"] == "fold_1_uniqueness_failed"
    )
    assert len(trial["validation_metrics"]) == 0
    assert len(trial["folds"]) == 1


def test_campaign134_bound_graph_and_prefit_evidence_are_immutable() -> None:
    terminal = _load(TERMINAL)
    for binding in terminal["authoritative_inputs"].values():
        path = _resolve(binding["path"])
        assert chain.file_sha256(path) == binding["sha256"]
    graph = _load(
        _resolve(terminal["authoritative_inputs"]["fold1_training_graph"]["path"])
    )
    prefit = _load(
        _resolve(terminal["authoritative_inputs"]["fold1_prefit_uniqueness"]["path"])
    )
    assert graph["graph"]["component_count"] == 124
    assert graph["graph"]["edge_count"] == 19
    assert graph["historical_forward_return_fields_used_for_fit"] is False
    assert prefit["validation_forward_return_fields_read_before_record"] is False
    assert prefit["uniqueness"]["all_required_comparisons_passed"] is False
    assert (
        prefit["uniqueness"]["maximum_observed_absolute_median_daily_rank_correlation"]
        == 0.8180313718344464
    )


def test_campaign134_policy_state_and_candidate49_boundaries() -> None:
    policy = _load(POLICY)
    state = _load(STATE)
    terminal = _load(TERMINAL)
    assert policy["version"] == 161
    assert policy["effective_accounting"]["campaign134_attempt_count"] == 9
    assert (
        policy["research_boundary"]["historical_2021_2023_validation_returns_read"]
        is False
    )
    assert state["campaign134"]["development_survivor_count"] == 0
    assert state["campaign134"]["2024_2025_lockbox_opened"] is False
    assert (
        state["campaign134"]["append_only_ledger"]["chain_tip_sha256"]
        == _load(RUN_ROOT / "trial_ledger.json")["chain_tip_sha256"]
    )
    assert terminal["candidate49"]["ledgers_changed"] is False
    assert (
        chain.file_sha256(
            ROOT
            / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
        )
        == terminal["candidate49"]["signal_ledger_sha256"]
    )
    assert (
        chain.file_sha256(
            ROOT
            / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
        )
        == terminal["candidate49"]["execution_ledger_sha256"]
    )
