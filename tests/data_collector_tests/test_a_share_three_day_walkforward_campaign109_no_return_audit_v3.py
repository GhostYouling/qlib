from scripts import a_share_three_day_walkforward_campaign109_no_return_audit_v3 as audit


def test_audit_uses_frozen_verify_only_manifest_adapter() -> None:
    assert (
        audit.candidate._generated["_validate_manifest"]
        is audit.verifier.validate_manifest
    )
    assert audit.SNAPSHOT_BINDING_SHA256 == (
        "eb5df1a26abdcb4252a4299ef16c7aef856032ee271b43407dd3379393cb9a64"
    )


def test_audit_preserves_coverage_first_comparator_contract() -> None:
    assert audit.EXPECTED_COMPARISON_COUNT == 132
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
