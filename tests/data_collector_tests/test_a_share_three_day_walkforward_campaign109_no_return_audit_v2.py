from scripts import a_share_three_day_walkforward_campaign109_features_v2 as feature
from scripts import a_share_three_day_walkforward_campaign109_no_return_audit_v2 as audit


def test_recovery_audit_uses_patched_candidate_identity() -> None:
    assert audit.candidate is feature.base
    assert audit.candidate.DEFAULT_IMPLEMENTATION_FREEZE == (
        feature.DEFAULT_IMPLEMENTATION_FREEZE
    )
    assert (
        audit.candidate._generated[
            "extract_intrabar_body_magnitude_serial_persistence"
        ]
        is feature.extract_body_magnitude_serial_persistence
    )


def test_recovery_audit_preserves_ordered_library_contract() -> None:
    assert audit.FACTOR_NAME == feature.FACTOR_NAME
    assert audit.EXPECTED_COMPARISON_COUNT == 132
    assert feature.NUMERIC_COMPARATOR_ORDER_SHA256 == (
        "7ed69afd1408e84dcc856583344166ffc9bcbb0add1aed63163b1d12a1be9a25"
    )
