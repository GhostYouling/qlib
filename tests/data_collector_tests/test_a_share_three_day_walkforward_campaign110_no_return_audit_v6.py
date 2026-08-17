from scripts import a_share_three_day_walkforward_campaign110_no_return_audit_v6 as audit


def test_exact_frozen_c109_verifier_alias_is_active() -> None:
    assert (
        audit.expected_namespace.c109_verifier
        is audit.source_namespace.c109_verifier
    )


def test_loader_binding_and_recovery_root_remain_unchanged() -> None:
    assert (
        audit.base.run_globals["_load_comparisons_after_coverage"]
        is audit.base.original._load_comparisons_after_coverage
    )
    assert audit.base.RECOVERY_OUTPUT_ROOT.name == "no_return_recovery_v1"
