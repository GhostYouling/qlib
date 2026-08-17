from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from scripts import a_share_three_day_walkforward_campaign088_no_return_audit as audit


def test_protocol_freezes_all_117_numeric_comparisons() -> None:
    spec = audit.load_protocol()
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    comparisons = gate["comparison_factors"]
    assert len(comparisons) == 117
    assert comparisons[-1] == {
        "name": audit.C87_FACTOR_NAME,
        "score_direction": "higher",
    }
    assert gate["all_117_numeric_comparators_must_pass"] is True


def test_candidate_snapshot_verifies_without_comparator_or_return_read() -> None:
    result = audit.verify_candidate_snapshot()
    assert result["status"] == "verified"
    assert result["eligible_rows"] == 1_328_065
    assert result["comparison_values_read"] is False
    assert result["historical_daily_price_or_forward_return_values_read"] is False


def test_synthetic_coverage_passes_without_comparison_values() -> None:
    spec = audit.load_protocol()
    keys = np.array(
        [
            (
                (np.datetime64(f"{year}-01-01", "D") + np.timedelta64(day, "D")).astype(
                    np.int64
                )
                * 4_000_000
            )
            + 1_600_000
            + name
            for year in range(2019, 2026)
            for day in range(100)
            for name in range(60)
        ],
        dtype=np.int64,
    )
    order = np.argsort(keys)
    keys = keys[order]
    values = np.linspace(0.0, 1.0, len(keys), dtype=np.float64)[order]
    years = np.repeat(np.arange(2019, 2026), 100 * 60)[order]
    coverage, finite_keys, finite_values = audit.coverage_and_capacity(
        keys, values, years, spec
    )
    assert coverage["median_coverage"] == 1.0
    assert coverage["p05_coverage"] == 1.0
    assert coverage["gate_passed_before_comparison_values"] is True
    assert np.array_equal(finite_keys, keys)
    assert np.array_equal(finite_values, values)


def test_run_requires_confirmation_before_any_research_action(tmp_path: Path) -> None:
    with pytest.raises(audit.Campaign088NoReturnAuditError):
        audit._run_no_return_audit(
            data_root=audit.DEFAULT_DATA_ROOT,
            experiment_root=tmp_path,
            workers=1,
            confirm_run=False,
        )
    assert list(tmp_path.iterdir()) == []


def test_comparison_loader_appends_campaign087_as_number_117(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frozen = audit.definitions.reconstruct_comparisons()

    def fake_first_116(
        **_kwargs: object,
    ) -> tuple[list[dict[str, object]], dict[str, object]]:
        return (
            [{"comparison_factor": item["name"]} for item in frozen[:116]],
            {"all_116_sources_loaded_in_frozen_order": True},
        )

    def fake_c87(**_kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        return {"comparison_factor": audit.C87_FACTOR_NAME}, {"status": "synthetic"}

    monkeypatch.setattr(
        audit.c87_audit, "_load_comparisons_after_coverage", fake_first_116
    )
    monkeypatch.setattr(audit.c87_audit, "_compact_snapshot_comparison", fake_c87)
    comparisons, receipts = audit._load_comparisons_after_coverage(
        coverage={},
        candidate_keys=np.array([1], dtype=np.int64),
        candidate_values=np.array([0.5], dtype=np.float64),
        gate={},
        engine=object(),
        comparison_engine=object(),
        workers=1,
    )
    assert [item["comparison_factor"] for item in comparisons] == [
        item["name"] for item in frozen
    ]
    assert receipts["all_117_sources_loaded_in_frozen_order"] is True


def test_status_is_read_only_before_activation() -> None:
    result = audit.status()
    assert result["candidate_snapshot_exists"] is True
    assert result["audit_count"] == 0
    assert result["coverage_or_capacity_metrics_computed"] is False
    assert result["comparison_values_read"] is False
    assert result["historical_daily_price_or_forward_return_values_read"] is False
