from scripts import a_share_three_day_walkforward_campaign110_no_return_audit_v5 as audit


def test_recovery_binds_exact_frozen_133_loader_into_run_globals() -> None:
    assert (
        audit.run_globals["_load_comparisons_after_coverage"]
        is audit.original._load_comparisons_after_coverage
    )
    assert audit.EXPECTED_COMPARISON_COUNT == 133


def test_recovery_protocol_fixes_only_loader_binding_and_output_root() -> None:
    record = audit.load_recovery_protocol()
    exact = record["exact_recovery"]
    assert exact["last_comparator"] == audit.c109.FACTOR_NAME
    assert exact["all_other_protocol_and_activation_semantics_unchanged"] is True
    assert exact["new_output_root"] == str(audit.RECOVERY_OUTPUT_ROOT)


def test_recovery_status_reads_no_values() -> None:
    report = audit.status()
    assert report["runtime_loader_is_frozen_133_loader"] is True
    assert report["coverage_or_comparator_values_read_by_status"] is False
    assert report["historical_daily_price_or_forward_return_values_read_by_status"] is False
