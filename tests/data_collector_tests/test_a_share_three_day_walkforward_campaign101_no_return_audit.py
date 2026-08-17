from __future__ import annotations

import inspect
from types import SimpleNamespace

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign101_no_return_audit as audit


def test_protocol_binds_132_definitions_and_129_numeric_comparators() -> None:
    spec = audit.load_protocol()
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert len(comparisons) == 129
    assert (
        audit.definitions._order_digest(comparisons)
        == audit.definitions.NUMERIC_ORDER_SHA256
    )
    assert comparisons[-1] == {
        "name": audit.C100_FACTOR_NAME,
        "score_direction": "higher",
    }


def test_comparison_loader_fails_before_coverage_pass() -> None:
    with pytest.raises(audit.Campaign101NoReturnAuditError):
        audit._load_comparisons_after_coverage(
            coverage={"gate_passed_before_comparison_values": False},
            candidate_keys=np.array([1], dtype=np.int64),
            candidate_values=np.array([0.5]),
            gate={},
            engine=SimpleNamespace(),
            comparison_engine=SimpleNamespace(),
            workers=1,
        )


def test_range_is_installed_without_weakening_prior_ranges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = SimpleNamespace(FACTOR_RANGES={"prior": (0.0, 1.0)})
    monkeypatch.setattr(audit.c100_audit, "_install_frozen_ranges", lambda value: None)
    audit._install_frozen_ranges(engine)
    assert engine.FACTOR_RANGES["prior"] == (0.0, 1.0)
    assert engine.FACTOR_RANGES[audit.FACTOR_NAME] == (0.0, 1.0)


def test_comparison_loader_appends_campaign100_only_after_first_128(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = [
        {"comparison_factor": f"factor_{index}", "gate_passed": True}
        for index in range(128)
    ]
    monkeypatch.setattr(
        audit.c100_audit,
        "_load_comparisons_after_coverage",
        lambda **kwargs: (
            list(first),
            {"all_128_sources_loaded_in_frozen_order": True},
        ),
    )
    monkeypatch.setattr(
        audit.compact_helper,
        "_compact_snapshot_comparison",
        lambda **kwargs: (
            {"comparison_factor": audit.C100_FACTOR_NAME, "gate_passed": True},
            {"status": "verified"},
        ),
    )
    comparisons, receipts = audit._load_comparisons_after_coverage(
        coverage={"gate_passed_before_comparison_values": True},
        candidate_keys=np.array([1], dtype=np.int64),
        candidate_values=np.array([0.5]),
        gate={},
        engine=SimpleNamespace(),
        comparison_engine=SimpleNamespace(),
        workers=1,
    )
    assert len(comparisons) == 129
    assert comparisons[-1]["comparison_factor"] == audit.C100_FACTOR_NAME
    assert receipts["all_129_sources_loaded_in_frozen_order"] is True
    assert "all_128_sources_loaded_in_frozen_order" not in receipts


def test_status_reads_no_coverage_comparators_or_returns(tmp_path) -> None:
    payload = audit.status(tmp_path)
    assert payload["audit_count"] == 0
    assert payload["coverage_or_capacity_metrics_computed_by_status"] is False
    assert payload["uniqueness_comparator_values_read_by_status"] is False
    assert (
        payload["historical_daily_price_or_forward_return_values_read_by_status"]
        is False
    )
    assert payload["provider_request_issued_by_status"] is False


def test_candidate_snapshot_verifier_binds_expected_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(audit, "_require", lambda *args: None)
    monkeypatch.setattr(
        audit.definitions,
        "verify_snapshot",
        lambda path: {
            "status": "verified",
            "dataset_sha256": audit.SNAPSHOT_DATASET_SHA256,
            "partitions": audit.EXPECTED_PARTITIONS,
            "rows": audit.EXPECTED_ROWS,
            "eligible_rows": audit.EXPECTED_ELIGIBLE_ROWS,
            "calendar_sessions": audit.EXPECTED_SESSIONS,
            "historical_daily_price_or_forward_return_values_read": False,
            "provider_request_issued": False,
        },
    )
    assert audit.verify_candidate_snapshot()["eligible_rows"] == 1_327_637


def test_candidate_loader_source_has_no_price_or_return_fields() -> None:
    source = inspect.getsource(audit.load_candidate_arrays)
    for prohibited_column in ('"open"', '"high"', '"low"', '"close"', '"label_t3"'):
        assert prohibited_column not in source
    assert "stock_day_key" in source
