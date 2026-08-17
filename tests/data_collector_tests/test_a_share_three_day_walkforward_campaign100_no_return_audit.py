from __future__ import annotations

import inspect
from types import SimpleNamespace

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign100_no_return_audit as audit


def test_campaign100_protocol_binds_131_definitions_and_128_comparators() -> None:
    spec = audit.load_protocol()
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    assert len(audit.definitions.reconstruct_complete_definitions()) == 131
    assert len(comparisons) == 128
    assert comparisons[-1] == {
        "name": audit.C99_FACTOR_NAME,
        "score_direction": "higher",
    }


def test_comparison_loader_fails_before_coverage_pass() -> None:
    with pytest.raises(audit.Campaign100NoReturnAuditError):
        audit._load_comparisons_after_coverage(
            coverage={"gate_passed_before_comparison_values": False},
            candidate_keys=np.array([1], dtype=np.int64),
            candidate_values=np.array([0.0]),
            gate={},
            engine=SimpleNamespace(),
            comparison_engine=SimpleNamespace(),
            workers=1,
        )


def test_campaign100_range_is_installed_without_weakening_prior_ranges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = SimpleNamespace(FACTOR_RANGES={"prior": (0.0, 1.0)})
    monkeypatch.setattr(audit.c99_audit, "_install_frozen_ranges", lambda value: None)
    audit._install_frozen_ranges(engine)
    assert engine.FACTOR_RANGES["prior"] == (0.0, 1.0)
    assert engine.FACTOR_RANGES[audit.FACTOR_NAME] == (0.0, 1.0)


def test_campaign099_compact_verifier_uses_frozen_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[object] = []
    monkeypatch.setattr(
        audit.c99_compact,
        "verify_snapshot",
        lambda path: observed.append(path) or {"status": "verified"},
    )
    assert audit._verify_campaign099_compact_snapshot() == {"status": "verified"}
    assert observed == [audit.C99_COMPACT_MANIFEST_PATH]


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


def test_candidate_snapshot_verifier_binds_expected_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(audit, "_require", lambda *args: None)
    monkeypatch.setattr(
        audit.definitions,
        "verify_snapshot_files",
        lambda path: {
            "status": "verified",
            "dataset_sha256": audit.SNAPSHOT_DATASET_SHA256,
            "partitions": audit.EXPECTED_PARTITIONS,
            "rows": audit.EXPECTED_ROWS,
            "eligible_rows": audit.EXPECTED_ELIGIBLE_ROWS,
            "comparison_values_read": False,
            "historical_daily_price_or_forward_return_values_read": False,
            "provider_request_issued": False,
        },
    )
    assert audit.verify_candidate_snapshot()["eligible_rows"] == 1_328_142


def test_audit_uses_available_atomic_json_writer() -> None:
    source = inspect.getsource(audit._run_no_return_audit)
    assert 'definitions._engine["c85"]._atomic_json' in source
    assert "historical_forward_return" not in inspect.getsource(
        audit.load_candidate_arrays
    )
