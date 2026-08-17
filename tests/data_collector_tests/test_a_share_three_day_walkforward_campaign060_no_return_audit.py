from __future__ import annotations

import json

from scripts import a_share_three_day_walkforward_campaign060_no_return_audit as audit


def test_static_bindings_are_snapshot_bound() -> None:
    result = audit.verify_static_bindings()
    assert result["snapshot_manifest_sha256"] == audit.SNAPSHOT_MANIFEST_SHA256
    assert result["snapshot_dataset_sha256"] == audit.SNAPSHOT_DATASET_SHA256
    assert result["calendar_sha256"] == audit.candidate.CALENDAR_SHA256


def test_protocol_reconstructs_exact_91_factor_order() -> None:
    spec = audit._load_protocol()
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert len(comparisons) == 91
    assert comparisons[0] == {"name": "late_return_30m", "score_direction": "higher"}
    assert comparisons[-1] == {
        "name": "intraday_market_directional_sign_agreement_238m",
        "score_direction": "higher",
    }


def test_status_is_pre_audit_and_no_return() -> None:
    result = audit.status(audit.DEFAULT_DATA_ROOT, audit.DEFAULT_EXPERIMENT_ROOT)
    assert result["audit_count"] == 0
    assert result["comparison_count"] == 91
    assert result["daily_price_fields_read_by_status"] is False
    assert result["forward_return_fields_read_by_status"] is False
    assert result["provider_request_issued_by_status"] is False


def test_campaign059_terminal_snapshot_identity_is_frozen() -> None:
    manifest = json.loads(audit.C59_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert audit._local_sha256(audit.C59_SNAPSHOT_PATH) == audit.C59_SNAPSHOT_SHA256
    assert manifest["dataset_sha256"] == audit.C59_DATASET_SHA256
    assert manifest["factor_names"] == [audit.C59_FACTOR]


def test_audit_identities_have_no_sentinels() -> None:
    audit._require_finalized_identities()
    assert audit.EXPECTED_ELIGIBLE_ROWS == 5_878_602
