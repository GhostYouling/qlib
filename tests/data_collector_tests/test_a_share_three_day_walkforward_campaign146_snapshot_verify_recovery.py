from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from scripts import (
    a_share_three_day_walkforward_campaign146_snapshot_verify_recovery as recovery,
)


def test_campaign146_recovery_protocol_and_manifest_header_are_bound() -> None:
    protocol = recovery.load_recovery_protocol()
    manifest = recovery.load_and_validate_manifest_metadata()
    assert protocol["status"] == "frozen_before_recovery_partition_reads"
    assert manifest["factor_ranges"] == {recovery.c146.FACTOR_NAME: [-1.0, 1.0]}
    assert manifest["positive_frequency_count_per_half"] == 59
    assert manifest["positive_half_spectral_denominators_required"] is True
    assert manifest["signed_return_and_amount_magnitudes_used"] is True


def test_campaign146_recovery_path_containment_is_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "snapshot" / "partitions"
    root.mkdir(parents=True)
    valid = root / "sh600000" / "2019.parquet"
    item = {
        "path": str(valid),
        "relative_path": "partitions/sh600000/2019.parquet",
    }
    assert recovery.resolve_partition_path(item, partition_root=root) == valid
    item["path"] = str(tmp_path / "escaped.parquet")
    with pytest.raises(recovery.Campaign146SnapshotRecoveryError):
        recovery.resolve_partition_path(item, partition_root=root)


def test_campaign146_recovery_effective_semantics_accept_negative_value() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2025-01-02"), pd.Timestamp("2025-01-03")],
            "symbol": ["SZ000001", "SZ000001"],
            "provider": ["tushare", "tushare"],
            recovery.c146.FACTOR_NAME: [-0.25, None],
            f"{recovery.c146.FACTOR_NAME}_eligible": [True, False],
        },
        columns=recovery.c146.OUTPUT_COLUMNS,
    )
    assert recovery.c146.validate_value_semantics(frame) == (2, 1)


def test_campaign146_recovery_digest_matches_frozen_canonical_json() -> None:
    value = [["partitions/sh600000/2019.parquet", "byte", "frame", 244]]
    expected = hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    assert recovery.json_digest(value) == expected


def test_campaign146_recovery_confirmation_and_worker_bounds_fail_closed() -> None:
    with pytest.raises(recovery.Campaign146SnapshotRecoveryError):
        recovery.verify(workers=4, confirm_snapshot_verification=False)
    with pytest.raises(recovery.Campaign146SnapshotRecoveryError):
        recovery.verify(workers=0, confirm_snapshot_verification=True)
