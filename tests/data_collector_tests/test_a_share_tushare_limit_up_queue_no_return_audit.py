from __future__ import annotations

import json
import stat
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_tushare_limit_up_queue_no_return_audit as audit


def _base_keys_and_values(*, finite: bool = True) -> tuple[np.ndarray, np.ndarray]:
    sessions = pd.bdate_range("2019-01-02", "2023-12-29")[:1214]
    days = sessions.to_numpy(dtype="datetime64[D]").astype(np.int64)
    securities = 1_000_000 + np.arange(1, 61, dtype=np.int64)
    keys = (days[:, None] * 4_000_000 + securities[None, :]).reshape(-1)
    values = np.tile(np.r_[np.zeros(30), np.ones(30)], len(sessions)).astype(float)
    if not finite:
        values[:] = np.nan
    return keys, values


def _semantic_receipt() -> dict:
    return {
        "status": (
            "complete_semantically_verified_2019_2023_candidate_snapshot_"
            "pending_ordered_no_return_audit"
        )
    }


def _source_verification() -> dict:
    return {
        "dataset_sha256": "a" * 64,
        "session_count": 1214,
        "session_order_sha256": audit.EXPECTED_SESSION_ORDER_SHA256,
        "factor_rows": 72_840,
    }


def _base_receipt(keys: np.ndarray) -> dict:
    return {
        "manifest_path": str(audit.C102_MANIFEST),
        "manifest_sha256": audit.C102_MANIFEST_SHA256,
        "dataset_sha256": audit.C102_DATASET_SHA256,
        "selected_partition_years": list(audit.DEVELOPMENT_YEARS),
        "selected_partitions": [],
        "rows": len(keys),
        "sessions": 1214,
        "stock_day_key_order_sha256": "b" * 64,
        "parquet_columns_read_before_coverage": ["stock_day_key"],
        "comparator_values_read_before_coverage": False,
        "partition_year_2024_or_2025_read": False,
    }


def _candidate_receipt(values: np.ndarray) -> dict:
    return {
        "source_factor_rows_read": len(values),
        "coverage_base_rows_matched": int(np.isfinite(values).sum()),
        "candidate_value_sha256": audit._value_digest(values),
        "candidate_rows_embedded_in_audit": False,
    }


def _set_output_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    receipt = tmp_path / "semantic_receipt.json"
    receipt.write_text("{}\n", encoding="utf-8")
    receipt.chmod(0o600)
    monkeypatch.setattr(audit.VERIFIER, "RECEIPT", receipt)
    monkeypatch.setattr(audit, "AUDIT_PATH", tmp_path / "no_return_audit.json")
    monkeypatch.setattr(audit, "LOCK_PATH", tmp_path / "no_return_audit.lock")


def test_protocol_order_and_real_plan_remain_zero_value() -> None:
    assert audit._protocol_valid() is True
    definitions = audit._comparator_definitions()
    assert len(definitions) == 134
    assert (
        audit.C110._order_digest(definitions) == audit.EXPECTED_COMPARATOR_ORDER_SHA256
    )
    plan = audit.build_plan()
    assert plan["ready"] is False
    assert plan["parquet_candidate_values_read"] is False
    assert plan["parquet_comparator_values_read"] is False
    assert plan["daily_price_or_forward_return_values_read"] is False
    assert plan["partition_year_2024_or_2025_values_read"] is False
    assert plan["credential_loaded"] is False
    assert plan["provider_request_issued"] is False


def test_plan_never_calls_parquet_value_readers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("plan must not read Parquet values")

    monkeypatch.setattr(audit.pd, "read_parquet", forbidden)
    monkeypatch.setattr(audit.pa_dataset, "dataset", forbidden)
    plan = audit.build_plan()
    assert plan["ready"] is False
    assert plan["allowed_partition_years"] == [2019, 2020, 2021, 2022, 2023]


def test_frozen_direct_plan_entry_runs_in_clean_subprocess() -> None:
    completed = subprocess.run(
        [sys.executable, str(Path(audit.__file__).resolve()), "plan"],
        cwd=audit.ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    assert completed.returncode == 2
    assert completed.stderr == ""
    payload = json.loads(completed.stdout)
    assert payload["ready"] is False
    assert payload["parquet_candidate_values_read"] is False
    assert payload["parquet_comparator_values_read"] is False
    assert payload["daily_price_or_forward_return_values_read"] is False
    assert payload["partition_year_2024_or_2025_values_read"] is False
    assert payload["credential_loaded"] is False
    assert payload["provider_request_issued"] is False


def test_partition_digest_adapter_accepts_either_exact_field_and_rejects_ambiguity() -> (
    None
):
    expected = "a" * 64
    assert audit._partition_digest({"sha256": expected}) == expected
    assert audit._partition_digest({"output_byte_sha256": expected}) == expected
    assert (
        audit._partition_digest({"sha256": expected, "output_byte_sha256": expected})
        == expected
    )
    for receipt in (
        {},
        {"sha256": "not-a-digest"},
        {"sha256": expected, "output_byte_sha256": "b" * 64},
    ):
        with pytest.raises(
            audit.OrderedNoReturnAuditError,
            match="partition digest receipt is ambiguous",
        ):
            audit._partition_digest(receipt)


def test_manifest_no_return_boundary_adapter_is_source_specific_and_fail_closed() -> (
    None
):
    source_131 = {"ordinal": 131}
    source_132 = {"ordinal": 132}
    assert (
        audit._manifest_no_return_boundary_valid(
            source_131,
            {"historical_forward_return_fields_read": False},
        )
        is True
    )
    assert (
        audit._manifest_no_return_boundary_valid(
            source_132,
            {"daily_price_fields_read": [], "forward_return_fields_read": False},
        )
        is True
    )
    assert audit._manifest_no_return_boundary_valid(source_131, {}) is False
    assert audit._manifest_no_return_boundary_valid(source_132, {}) is False
    assert (
        audit._manifest_no_return_boundary_valid(
            source_132,
            {"daily_price_fields_read": ["close"], "forward_return_fields_read": False},
        )
        is False
    )


def test_coverage_gate_is_exact_and_independent_of_comparators() -> None:
    keys, values = _base_keys_and_values(finite=True)
    passed = audit._coverage_and_capacity(keys, values)
    assert passed["calendar_sessions"] == 1214
    assert passed["median_coverage"] == 1.0
    assert passed["p05_coverage"] == 1.0
    assert passed["eligible_names_p05"] == 60.0
    assert passed["gate_passed_before_comparator_values"] is True

    failed = audit._coverage_and_capacity(keys, np.full(len(keys), np.nan))
    assert failed["gate_passed_before_comparator_values"] is False


def test_pairwise_average_tie_spearman_and_strict_gate() -> None:
    keys, candidate = _base_keys_and_values(finite=True)
    comparison = 1.0 - candidate
    rows = audit._daily_correlation_rows(keys, candidate, comparison)
    assert len(rows) == 1214
    result = audit._comparison_result(
        {"name": "synthetic_inverse", "score_direction": "higher"},
        rows,
        audit._value_digest(comparison),
    )
    assert result["median_daily_rank_correlation"] == pytest.approx(-1.0)
    assert result["gate_passed"] is False
    assert result["daily_correlation_rows_embedded"] is False


def test_coverage_failure_publishes_without_comparator_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_output_paths(tmp_path, monkeypatch)
    keys, values = _base_keys_and_values(finite=False)
    monkeypatch.setattr(audit, "build_plan", lambda: {"ready": True})
    monkeypatch.setattr(
        audit,
        "_source_receipt_and_verification",
        lambda: (_semantic_receipt(), _source_verification()),
    )
    monkeypatch.setattr(
        audit,
        "_load_base_keys",
        lambda **_kwargs: (keys, _base_receipt(keys)),
    )
    monkeypatch.setattr(
        audit,
        "_load_candidate_on_base",
        lambda _keys: (values, _candidate_receipt(values)),
    )

    def forbidden(**_kwargs: object) -> object:
        raise AssertionError("coverage rejection must not load comparator values")

    monkeypatch.setattr(audit, "_all_comparisons", forbidden)
    record = audit.run_audit(confirmed=True)
    assert record["status"] == (
        "completed_zero_admissible_factor_coverage_stop_before_comparator_values"
    )
    assert record["uniqueness"]["comparison_count"] == 0
    assert (
        record["uniqueness"]["comparison_source_verification"]["comparator_values_read"]
        is False
    )
    assert stat.S_IMODE(audit.AUDIT_PATH.stat().st_mode) == 0o600
    assert audit.inspect_audit()["valid"] is True


def test_coverage_pass_can_publish_all_134_aggregate_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_output_paths(tmp_path, monkeypatch)
    keys, values = _base_keys_and_values(finite=True)
    monkeypatch.setattr(audit, "build_plan", lambda: {"ready": True})
    monkeypatch.setattr(
        audit,
        "_source_receipt_and_verification",
        lambda: (_semantic_receipt(), _source_verification()),
    )
    monkeypatch.setattr(
        audit,
        "_load_base_keys",
        lambda **_kwargs: (keys, _base_receipt(keys)),
    )
    monkeypatch.setattr(
        audit,
        "_load_candidate_on_base",
        lambda _keys: (values, _candidate_receipt(values)),
    )
    synthetic = [
        {
            "comparison_factor": definition["name"],
            "source_score_direction": definition["score_direction"],
            "pairwise_sessions": 1214,
            "minimum_pairwise_names_observed": 60,
            "median_daily_rank_correlation": 0.0,
            "absolute_median_daily_rank_correlation": 0.0,
            "daily_rank_correlation_p05": 0.0,
            "daily_rank_correlation_p95": 0.0,
            "comparison_value_sha256": "c" * 64,
            "daily_correlation_frame_sha256": "d" * 64,
            "daily_correlation_rows_embedded": False,
            "gate_passed": True,
        }
        for definition in audit._comparator_definitions()
    ]
    monkeypatch.setattr(
        audit,
        "_all_comparisons",
        lambda **_kwargs: (
            synthetic,
            {
                "all_134_loaded_in_frozen_order": True,
                "partition_year_2024_or_2025_read": False,
            },
        ),
    )
    record = audit.run_audit(confirmed=True)
    assert record["status"] == (
        "completed_one_no_return_admissible_factor_pending_frozen_development_trial"
    )
    assert record["admissible_factor_count"] == 1
    assert record["uniqueness"]["comparison_count"] == 134
    assert record["candidate_or_comparator_row_values_embedded"] is False
    assert record["partition_year_2024_or_2025_values_read"] is False


def test_explicit_confirmation_and_absent_inspection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_output_paths(tmp_path, monkeypatch)
    with pytest.raises(
        audit.OrderedNoReturnAuditError,
        match="confirm-no-return-audit",
    ):
        audit.run_audit(confirmed=False)
    assert audit.inspect_audit() == {
        "valid": True,
        "status": "no_ordered_no_return_audit",
        "credential_loaded": False,
        "provider_request_issued": False,
    }


def test_inspection_rejects_semantically_tampered_private_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _set_output_paths(tmp_path, monkeypatch)
    audit.AUDIT_PATH.write_text(json.dumps({"kind": "wrong"}) + "\n", encoding="utf-8")
    audit.AUDIT_PATH.chmod(0o600)
    with pytest.raises(
        audit.OrderedNoReturnAuditError,
        match="semantics changed",
    ):
        audit.inspect_audit()
