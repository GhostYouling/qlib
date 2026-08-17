from scripts import a_share_three_day_walkforward_campaign110_no_return_audit_v8 as audit


def test_campaign109_loader_export_is_exact_existing_generated_function() -> None:
    assert (
        audit.c109_audit._load_comparisons_after_coverage
        is audit.c109_audit._generated["_load_comparisons_after_coverage"]
    )


def test_campaign110_runtime_still_uses_append_one_loader() -> None:
    recovery = audit.base.base.base
    assert (
        recovery.run_globals["_load_comparisons_after_coverage"]
        is recovery.original._load_comparisons_after_coverage
    )
    assert recovery.EXPECTED_COMPARISON_COUNT == 133
