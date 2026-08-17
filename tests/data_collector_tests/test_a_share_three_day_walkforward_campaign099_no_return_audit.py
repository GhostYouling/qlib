from __future__ import annotations

import inspect
import json
from types import SimpleNamespace

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign099_no_return_audit as audit


def test_campaign099_no_return_protocol_binds_130_definitions_and_127_comparators() -> (
    None
):
    spec = audit.load_protocol()
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert len(audit.definitions.reconstruct_complete_definitions()) == 130
    assert len(comparisons) == 127
    assert comparisons[-1] == {
        "name": audit.C98_FACTOR_NAME,
        "score_direction": "higher",
    }


def test_comparison_loader_fails_before_coverage_pass() -> None:
    with pytest.raises(audit.Campaign099NoReturnAuditError):
        audit._load_comparisons_after_coverage(
            coverage={"gate_passed_before_comparison_values": False},
            candidate_keys=np.array([1], dtype=np.int64),
            candidate_values=np.array([0.0]),
            gate={},
            engine=SimpleNamespace(),
            comparison_engine=SimpleNamespace(),
            workers=1,
        )


def test_campaign099_range_is_installed_without_weakening_prior_ranges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = SimpleNamespace(FACTOR_RANGES={"prior": (0.0, 1.0)})
    monkeypatch.setattr(audit.c98_audit, "_install_frozen_ranges", lambda value: None)
    audit._install_frozen_ranges(engine)
    assert engine.FACTOR_RANGES["prior"] == (0.0, 1.0)
    assert engine.FACTOR_RANGES[audit.FACTOR_NAME] == (-1.0, 1.0)


def test_alignment_retains_absent_denominator_identity_as_nan() -> None:
    keys, values, years, stats = audit.align_candidate_year_with_missing(
        eligible_keys=np.array([10, 30], dtype=np.int64),
        candidate_keys=np.array([20, 10], dtype=np.int64),
        candidate_values=np.array([-0.5, 0.25]),
        year=2019,
    )
    assert keys.tolist() == [10, 30]
    assert values[0] == 0.25
    assert np.isnan(values[1])
    assert years.tolist() == [2019, 2019]
    assert stats["matched_candidate_keys"] == 1
    assert stats["missing_candidate_keys_retained_as_nan"] == 1


def test_alignment_rejects_duplicate_keys_and_out_of_range_values() -> None:
    with pytest.raises(audit.Campaign099NoReturnAuditError):
        audit.align_candidate_year_with_missing(
            eligible_keys=np.array([10], dtype=np.int64),
            candidate_keys=np.array([10, 10], dtype=np.int64),
            candidate_values=np.array([0.1, 0.2]),
            year=2019,
        )
    with pytest.raises(audit.Campaign099NoReturnAuditError):
        audit.align_candidate_year_with_missing(
            eligible_keys=np.array([10], dtype=np.int64),
            candidate_keys=np.array([10], dtype=np.int64),
            candidate_values=np.array([1.01]),
            year=2019,
        )


def test_status_does_not_read_coverage_comparators_or_returns(tmp_path) -> None:
    payload = audit.status(tmp_path)
    assert payload["audit_count"] == 0
    assert payload["coverage_or_capacity_metrics_computed_by_status"] is False
    assert payload["comparator_values_read_by_status"] is False
    assert (
        payload["historical_daily_price_or_forward_return_values_read_by_status"]
        is False
    )
    assert payload["provider_request_issued_by_status"] is False


def test_audit_uses_available_atomic_json_writer(tmp_path) -> None:
    path = tmp_path / "payload.json"
    payload = {"status": "writer_test"}
    audit.definitions.c97.base.foundation.atomic_write_json(payload, path)
    assert json.loads(path.read_text(encoding="utf-8")) == payload
    source = inspect.getsource(audit._run_no_return_audit)
    assert "definitions.c97.base.foundation.atomic_write_json" in source
    assert "definitions.c90" not in source
