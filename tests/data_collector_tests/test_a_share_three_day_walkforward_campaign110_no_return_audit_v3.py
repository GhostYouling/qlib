from scripts import a_share_three_day_walkforward_campaign110_no_return_audit_v3 as audit


def test_nested_require_helper_is_exact_existing_object() -> None:
    assert (
        audit.base.base._base_generated["_require"]
        is audit.helper_namespace["_require"]
    )


def test_campaign109_comparator_uses_frozen_verify_only_adapter() -> None:
    assert (
        audit.base.base.c109._generated["_validate_manifest"]
        is audit.c109_verifier.validate_manifest
    )


def test_all_133_coverage_first_contract_is_unchanged() -> None:
    assert audit.EXPECTED_COMPARISON_COUNT == 133
    gates = audit.load_protocol()["ordered_no_return_gates"]
    assert list(gates) == [
        "coverage_and_capacity_before_comparison_values",
        "uniqueness_after_coverage_only",
    ]
    assert len(gates["uniqueness_after_coverage_only"]["comparison_factors"]) == 133
