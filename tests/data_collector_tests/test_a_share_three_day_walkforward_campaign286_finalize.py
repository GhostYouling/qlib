from __future__ import annotations

from scripts import a_share_three_day_walkforward_campaign286_finalize as finalizer


def test_safe_decision_rejects_constant_deep_trial_without_casting_nulls() -> None:
    validations = [
        finalizer.campaign.load_json(
            finalizer.OUTPUT_ROOT / f"fold_{fold}_validation_metrics.json"
        )["validation_metrics"]["wf286_lgb_deep_158f"]
        for fold in range(1, 4)
    ]

    decision = finalizer.safe_survivor_decision({"validation_metrics": validations})

    assert not decision["passed"]
    assert decision["undefined_metrics_are_explicit_gate_failures"]
    assert decision["median_validation_mean_rank_ic"] is None
    assert all(
        f"fold_{fold}_insufficient_association_cohorts" in decision["rejection_reasons"]
        for fold in range(1, 4)
    )


def test_persisted_evidence_rejects_all_three_trials() -> None:
    _, trials, diagnostics = finalizer.load_evidence()

    assert [record["trial_id"] for record in trials] == list(
        finalizer.campaign.TRIAL_ORDER
    )
    assert all(len(record["validation_metrics"]) == 3 for record in trials)
    assert all(not record["decision"]["passed"] for record in trials)
    assert all(
        diagnostics[str(fold)]["wf286_lgb_deep_158f"]["unique_score_count"] == 1
        for fold in range(1, 4)
    )


def test_final_ledger_accounts_for_every_attempt_and_return_read() -> None:
    _, trials, _ = finalizer.load_evidence()

    ledger = finalizer.build_ledger(trials)

    assert ledger["entry_count"] == 16
    assert ledger["prevalue_concept_attempt_count"] == 6
    assert ledger["infrastructure_failure_attempt_count"] == 7
    assert ledger["model_trial_attempt_count"] == 3
    assert ledger["total_model_fold_validation_return_reads"] == 9
    assert not ledger["candidate49_ledgers_changed"]
    for previous, current in zip(ledger["entries"], ledger["entries"][1:]):
        assert current["previous_entry_sha256"] == previous["entry_sha256"]


def test_all_frozen_development_artifacts_are_present() -> None:
    finalizer.validate_artifacts()
