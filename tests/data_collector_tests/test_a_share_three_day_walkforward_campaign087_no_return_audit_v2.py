from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign087_no_return_audit as v1
from scripts import a_share_three_day_walkforward_campaign087_no_return_audit_v2 as v2


class _ComparisonEngine:
    def _aligned_comparison_result(self, **kwargs: object) -> dict[str, object]:
        values = np.asarray(kwargs["comparison_values"], dtype=np.float64)
        return {
            "comparison_factor": kwargs["comparison"],
            "comparison_values": values.tolist(),
            "gate_passed": True,
        }


def test_v2_repair_inputs_and_failed_v1_are_immutable() -> None:
    assert v2._sha256(v2.REPAIR_PROTOCOL) == v2.REPAIR_PROTOCOL_SHA256
    assert v2._sha256(Path(v1.__file__).resolve()) == v2.V1_RUNNER_SHA256
    assert v2._sha256(v1.AUDIT_IMPLEMENTATION_FREEZE) == v2.V1_FREEZE_SHA256
    assert v2._sha256(v1.AUDIT_ACTIVATION_BINDING) == v2.V1_ACTIVATION_SHA256
    assert v2._sha256(v2.C85_MANIFEST_PATH) == v2.C85_MANIFEST_SHA256
    assert v2._sha256(v2.C86_MANIFEST_PATH) == v2.C86_MANIFEST_SHA256


def test_compact_loader_aligns_synthetic_stock_day_keys_without_old_engine(
    tmp_path: Path,
) -> None:
    factor = "synthetic_factor"
    keys_by_year = {
        2019: [10],
        2020: [],
        2021: [20],
        2022: [],
        2023: [30],
        2024: [],
        2025: [],
    }
    records = []
    for year in range(2019, 2026):
        frame = pd.DataFrame(
            {
                "stock_day_key": pd.Series(keys_by_year[year], dtype="int64"),
                factor: pd.Series(
                    [float(key) / 10.0 for key in keys_by_year[year]],
                    dtype="float64",
                ),
            }
        )
        relative = Path("partitions") / f"{year}.parquet"
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(destination, index=False)
        records.append({"year": year, "path": str(relative)})
    manifest = tmp_path / "snapshot.json"
    manifest.write_text(json.dumps({"files": records}), encoding="utf-8")
    expected_sha = v2._sha256(manifest)
    original_rows = v1.EXPECTED_ROWS
    v1.EXPECTED_ROWS = 3
    try:
        result, receipt = v2._compact_snapshot_comparison(
            manifest_path=manifest,
            expected_manifest_sha256=expected_sha,
            factor=factor,
            candidate_keys=np.array([10, 30], dtype=np.int64),
            candidate_values=np.array([0.1, 0.3], dtype=np.float64),
            gate={},
            comparison_engine=_ComparisonEngine(),
            verifier=lambda: {"status": "synthetic_verified"},
        )
    finally:
        v1.EXPECTED_ROWS = original_rows
    assert result["comparison_factor"] == factor
    assert result["comparison_values"] == [1.0, 3.0]
    assert receipt["loader"] == "frozen_seven_partition_stock_day_key_direct_alignment"


def test_compact_loader_fails_closed_on_missing_candidate_key(tmp_path: Path) -> None:
    factor = "synthetic_factor"
    records = []
    for year in range(2019, 2026):
        relative = Path("partitions") / f"{year}.parquet"
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            {
                "stock_day_key": pd.Series([year], dtype="int64")
                if year == 2019
                else pd.Series(dtype="int64"),
                factor: pd.Series([1.0], dtype="float64")
                if year == 2019
                else pd.Series(dtype="float64"),
            }
        ).to_parquet(destination, index=False)
        records.append({"year": year, "path": str(relative)})
    manifest = tmp_path / "snapshot.json"
    manifest.write_text(json.dumps({"files": records}), encoding="utf-8")
    original_rows = v1.EXPECTED_ROWS
    v1.EXPECTED_ROWS = 1
    try:
        with pytest.raises(v2.Campaign087NoReturnAuditV2Error):
            v2._compact_snapshot_comparison(
                manifest_path=manifest,
                expected_manifest_sha256=v2._sha256(manifest),
                factor=factor,
                candidate_keys=np.array([9999], dtype=np.int64),
                candidate_values=np.array([0.5], dtype=np.float64),
                gate={},
                comparison_engine=_ComparisonEngine(),
                verifier=lambda: {"status": "synthetic_verified"},
            )
    finally:
        v1.EXPECTED_ROWS = original_rows


def test_v2_run_requires_confirmation_before_any_research_action(tmp_path: Path) -> None:
    with pytest.raises(v2.Campaign087NoReturnAuditV2Error):
        v2._run_no_return_audit(
            data_root=v2.DEFAULT_DATA_ROOT,
            experiment_root=tmp_path,
            workers=1,
            confirm_run=False,
        )
    assert list(tmp_path.iterdir()) == []


def test_status_remains_precoverage_before_v2_activation() -> None:
    status = v2.status()
    assert status["audit_count"] == 0
    assert status["coverage_or_capacity_metrics_computed_by_status"] is False
    assert status["comparison_values_read_by_status"] is False
    assert status["historical_daily_price_or_forward_return_values_read_by_status"] is False
