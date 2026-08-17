import hashlib
from pathlib import Path

import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign075_no_return_audit_v2 as repair


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _frame() -> pd.DataFrame:
    factor = repair.c68.v1.FACTOR_NAME
    return pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2020-01-02", "2020-01-03"]),
            "symbol": ["SZ000001", "SZ000001"],
            "provider": ["tushare", "tushare"],
            factor: [-0.25, None],
            f"{factor}_eligible": [True, False],
        }
    ).loc[:, repair.c68.v1.OUTPUT_COLUMNS]


def test_partition_byte_schema_and_value_checks_ignore_only_frame_hash(tmp_path: Path) -> None:
    root = tmp_path / "partitions"
    path = root / "sz000001" / "2020.parquet"
    path.parent.mkdir(parents=True)
    _frame().to_parquet(path, index=False)
    item = {
        "path": str(path),
        "output_byte_sha256": _sha256(path),
        "output_frame_sha256": "deliberately-runtime-incompatible",
        "rows": 2,
    }
    assert repair._verify_partition(item, partition_root=root) == (2, 1)


def test_partition_byte_change_still_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "partitions"
    path = root / "sz000001" / "2020.parquet"
    path.parent.mkdir(parents=True)
    _frame().to_parquet(path, index=False)
    item = {
        "path": str(path),
        "output_byte_sha256": "0" * 64,
        "output_frame_sha256": "ignored-only-after-byte-match",
        "rows": 2,
    }
    with pytest.raises(repair.Campaign075NoReturnAuditV2Error):
        repair._verify_partition(item, partition_root=root)


def test_partition_value_semantics_still_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "partitions"
    path = root / "sz000001" / "2020.parquet"
    path.parent.mkdir(parents=True)
    frame = _frame()
    frame.loc[0, repair.c68.v1.FACTOR_NAME] = 2.0
    frame.to_parquet(path, index=False)
    item = {
        "path": str(path),
        "output_byte_sha256": _sha256(path),
        "output_frame_sha256": "ignored-only-after-byte-match",
        "rows": 2,
    }
    with pytest.raises(repair.c68.Campaign068FeatureV2Error):
        repair._verify_partition(item, partition_root=root)


def test_repair_protocol_preserves_all_research_gates() -> None:
    spec = repair.load_repair_protocol()
    assert spec["sole_repair"]["partial_statistics_may_be_reused"] is False
    assert spec["sole_repair"]["full_campaign075_audit_must_restart_from_coverage"] is True
    assert all(spec["unchanged_research_semantics"].values())
