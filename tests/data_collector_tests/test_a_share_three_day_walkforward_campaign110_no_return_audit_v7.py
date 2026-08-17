from scripts import a_share_three_day_walkforward_campaign110_no_return_audit_v7 as audit


def test_exact_frozen_candidate_verifier_alias_is_active() -> None:
    assert audit.expected_namespace.verifier is audit.source_namespace.verifier


def test_prior_c109_alias_and_loader_binding_remain_active() -> None:
    assert hasattr(audit.source_namespace, "c109_verifier")
    recovery = audit.base.base
    assert (
        recovery.run_globals["_load_comparisons_after_coverage"]
        is recovery.original._load_comparisons_after_coverage
    )
