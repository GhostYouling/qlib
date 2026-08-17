from scripts import a_share_three_day_walkforward_campaign110_no_return_audit_v4 as audit


def test_runtime_description_records_all_133() -> None:
    assert audit.original.main.__globals__["__doc__"] == audit.RUNTIME_DOCSTRING
    assert "all-133" in audit.RUNTIME_DOCSTRING


def test_protocol_and_comparator_count_unchanged() -> None:
    assert audit.EXPECTED_COMPARISON_COUNT == 133
    factors = audit.load_protocol()["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(factors) == 133
    assert factors[-1]["name"] == audit.c109.FACTOR_NAME
