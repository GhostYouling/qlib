import hashlib
from pathlib import Path

import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign075_no_return_audit_v3 as repair


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2020-01-02"]),
            "symbol": ["SZ000001"],
            "provider": ["tushare"],
            "factor": [0.25],
            "factor_eligible": [True],
        }
    )


def test_generic_partition_adapter_ignores_only_stored_frame_hash(tmp_path: Path) -> None:
    root = tmp_path / "partitions"
    path = root / "sz000001" / "2020.parquet"
    path.parent.mkdir(parents=True)
    frame = _frame()
    frame.to_parquet(path, index=False)
    item = {
        "path": str(path),
        "output_byte_sha256": _sha256(path),
        "output_frame_sha256": "runtime-sensitive-and-not-recomputed",
        "rows": 1,
    }
    assert repair._verify_partition(
        item,
        partition_root=root,
        output_columns=tuple(frame.columns),
        validate_values=lambda value: (len(value), int(value["factor_eligible"].sum())),
    ) == (1, 1)


def test_generic_partition_adapter_rejects_byte_tamper(tmp_path: Path) -> None:
    root = tmp_path / "partitions"
    path = root / "sz000001" / "2020.parquet"
    path.parent.mkdir(parents=True)
    frame = _frame()
    frame.to_parquet(path, index=False)
    item = {
        "path": str(path),
        "output_byte_sha256": "0" * 64,
        "output_frame_sha256": "irrelevant-after-byte-failure",
        "rows": 1,
    }
    with pytest.raises(repair.Campaign075NoReturnAuditV3Error):
        repair._verify_partition(
            item,
            partition_root=root,
            output_columns=tuple(frame.columns),
            validate_values=lambda value: (1, 1),
        )


def test_generic_partition_adapter_rejects_schema_change(tmp_path: Path) -> None:
    root = tmp_path / "partitions"
    path = root / "sz000001" / "2020.parquet"
    path.parent.mkdir(parents=True)
    frame = _frame()
    frame.to_parquet(path, index=False)
    item = {
        "path": str(path),
        "output_byte_sha256": _sha256(path),
        "output_frame_sha256": "not-recomputed",
        "rows": 1,
    }
    with pytest.raises(repair.Campaign075NoReturnAuditV3Error):
        repair._verify_partition(
            item,
            partition_root=root,
            output_columns=("wrong",),
            validate_values=lambda value: (1, 1),
        )


def test_repair_scope_is_exactly_campaign068_through_campaign074() -> None:
    spec = repair.load_repair_protocol()
    assert [item["campaign"] for item in spec["finite_compatibility_snapshot_list"]] == [
        68,
        69,
        70,
        71,
        72,
        73,
        74,
    ]
    assert spec["retry_semantics"]["partial_statistics_reused"] is False
    assert spec["retry_semantics"][
        "full_audit_restarts_from_candidate_snapshot_and_coverage"
    ] is True
