from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import a_share_three_day_walkforward_campaign087_no_return_audit as audit


def test_protocol_reconstructs_complete_frozen_orders() -> None:
    spec = audit.load_protocol()
    comparisons = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ]
    complete = audit.definitions.reconstruct_complete_definitions()
    assert len(comparisons) == audit.EXPECTED_COMPARISON_COUNT == 116
    assert len(complete) == audit.EXPECTED_COMPLETE_DEFINITION_COUNT == 118
    assert comparisons[-1] == {
        "name": audit.c86_audit.FACTOR_NAME,
        "score_direction": "higher",
    }
    assert audit.STRUCTURALLY_NONNUMERIC_FACTOR not in {
        item["name"] for item in comparisons
    }
    assert audit.PREVALUE_TERMINAL_NONNUMERIC_FACTOR not in {
        item["name"] for item in comparisons
    }


def test_snapshot_binding_and_manifest_headers_are_frozen_without_value_scan() -> None:
    report = audit.definitions.bindings.validate_record(
        audit.SNAPSHOT_BINDING, data_root=audit.DEFAULT_DATA_ROOT
    )
    manifest = json.loads(audit.SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert report["all_bindings_passed"] is True
    assert audit._sha256(audit.SNAPSHOT_BINDING) == audit.SNAPSHOT_BINDING_SHA256
    assert audit._sha256(audit.SNAPSHOT_MANIFEST_PATH) == audit.SNAPSHOT_MANIFEST_SHA256
    assert manifest["dataset_sha256"] == audit.SNAPSHOT_DATASET_SHA256
    assert manifest["factor_eligible_rows"][audit.FACTOR_NAME] == 1_328_449
    assert manifest["comparison_values_read"] is False
    assert manifest["historical_forward_returns_read"] is False


def test_candidate_range_install_is_exact_and_conflict_fails_closed() -> None:
    engine = SimpleNamespace(FACTOR_RANGES={})
    audit._install_frozen_ranges(engine)
    assert engine.FACTOR_RANGES[audit.FACTOR_NAME] == (0.0, 1.0)
    conflicting = SimpleNamespace(FACTOR_RANGES={audit.FACTOR_NAME: (-1.0, 1.0)})
    with pytest.raises(audit.Campaign087NoReturnAuditError):
        audit._install_frozen_ranges(conflicting)


def test_run_requires_explicit_confirmation_before_any_audit_action(tmp_path: Path) -> None:
    with pytest.raises(audit.Campaign087NoReturnAuditError):
        audit._run_no_return_audit(
            data_root=audit.DEFAULT_DATA_ROOT,
            experiment_root=tmp_path,
            workers=1,
            confirm_run=False,
        )
    assert list(tmp_path.iterdir()) == []


def test_status_is_precoverage_and_no_audit_exists() -> None:
    status = audit.status()
    assert status["candidate_snapshot_exists"] is True
    assert status["audit_count"] == 0
    assert status["coverage_or_capacity_metrics_computed"] is False
    assert status["comparison_values_read"] is False
    assert status["historical_daily_price_or_forward_return_values_read"] is False
    assert status["provider_request_issued"] is False
