from __future__ import annotations

import inspect
from types import SimpleNamespace

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign098_no_return_audit as audit


def test_protocol_materializes_exact_v43_orders() -> None:
    spec = audit.load_protocol()
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    assert gate["complete_definition_count"] == 129
    assert gate["numeric_comparator_count"] == 126
    assert len(gate["comparison_factors"]) == 126
    assert gate["comparison_factors"][-1] == {
        "name": "intraday_market_range_profile_synchronization_240m",
        "score_direction": "higher",
    }
    assert gate["all_126_numeric_comparators_must_pass"] is True


def test_semantic_only_factors_are_not_numeric_comparators() -> None:
    spec = audit.load_protocol()
    names = {
        item["name"]
        for item in spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
            "comparison_factors"
        ]
    }
    assert names.isdisjoint(audit.STRUCTURALLY_NONNUMERIC_FACTORS)


def test_snapshot_and_denominator_bindings_are_exact() -> None:
    assert audit._sha256(audit.SNAPSHOT_MANIFEST_PATH) == audit.SNAPSHOT_MANIFEST_SHA256
    assert audit._sha256(audit.SNAPSHOT_BINDING) == audit.SNAPSHOT_BINDING_SHA256
    assert (
        audit._sha256(audit.ELIGIBILITY_MANIFEST_PATH)
        == audit.ELIGIBILITY_MANIFEST_SHA256
    )
    assert (
        audit._sha256(audit.C97_COMPACT_MANIFEST_PATH)
        == audit.C97_COMPACT_MANIFEST_SHA256
    )


def test_candidate_range_is_added_without_changing_old_ranges() -> None:
    engine = SimpleNamespace(FACTOR_RANGES={"sentinel": (-7.0, 7.0)})
    audit._install_frozen_ranges(engine)
    assert engine.FACTOR_RANGES["sentinel"] == (-7.0, 7.0)
    assert engine.FACTOR_RANGES[audit.C97_FACTOR_NAME] == (-1.0, 1.0)
    assert engine.FACTOR_RANGES[audit.FACTOR_NAME] == (0.0, 1.0)


def test_comparator_loader_fails_before_coverage() -> None:
    with pytest.raises(
        audit.Campaign098NoReturnAuditError,
        match="before coverage pass",
    ):
        audit._load_comparisons_after_coverage(
            coverage={"gate_passed_before_comparison_values": False},
            candidate_keys=np.array([1], dtype=np.int64),
            candidate_values=np.array([0.5], dtype=np.float64),
            gate={},
            engine=SimpleNamespace(),
            comparison_engine=SimpleNamespace(),
            workers=1,
        )


def test_loader_appends_campaign097_only_after_first_125() -> None:
    source = inspect.getsource(audit._load_comparisons_after_coverage)
    assert "len(comparisons) != 125" in source
    assert "C97_COMPACT_MANIFEST_PATH" in source
    assert "all_126_sources_loaded_in_frozen_order" in source


def test_final_comparator_verifier_binds_the_frozen_manifest(monkeypatch) -> None:
    observed = []

    def fake_verify(path):
        observed.append(path)
        return {"status": "verified"}

    monkeypatch.setattr(audit.c97_compact, "verify_snapshot", fake_verify)
    assert audit._verify_campaign097_compact_snapshot() == {"status": "verified"}
    assert observed == [audit.C97_COMPACT_MANIFEST_PATH]


def test_run_requires_explicit_confirmation_before_static_or_value_reads() -> None:
    with pytest.raises(audit.Campaign098NoReturnAuditError, match="--confirm-run"):
        audit._run_no_return_audit(
            data_root=audit.DEFAULT_DATA_ROOT,
            experiment_root=audit.DEFAULT_EXPERIMENT_ROOT,
            workers=1,
            confirm_run=False,
        )


def test_status_is_no_value_and_no_return() -> None:
    result = audit.status()
    assert result["coverage_or_capacity_metrics_computed_by_status"] is False
    assert result["comparator_values_read_by_status"] is False
    assert (
        result["historical_daily_price_or_forward_return_values_read_by_status"]
        is False
    )
    assert result["provider_request_issued_by_status"] is False
