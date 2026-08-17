from scripts import a_share_three_day_walkforward_campaign110_no_return_audit_v2 as audit


def test_audit_uses_frozen_verify_only_manifest_adapter() -> None:
    assert (
        audit.candidate._base_generated["_validate_manifest"]
        is audit.verifier.validate_manifest
    )


def test_audit_preserves_coverage_first_all_133_contract() -> None:
    assert audit.EXPECTED_COMPARISON_COUNT == 133
    protocol = audit.load_protocol()
    gates = protocol["ordered_no_return_gates"]
    assert list(gates) == [
        "coverage_and_capacity_before_comparison_values",
        "uniqueness_after_coverage_only",
    ]
    assert (
        gates["uniqueness_after_coverage_only"][
            "all_numeric_comparators_must_pass"
        ]
        is True
    )
    assert gates["uniqueness_after_coverage_only"]["comparison_factors"][-1][
        "name"
    ] == audit.c109.FACTOR_NAME
