from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign151_snapshot_verify as verify


def _zero_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2021-01-04", "2021-01-05"]),
            "symbol": ["SH600000", "SH600000"],
            "provider": ["tushare", "tushare"],
            verify.features.FACTOR_NAME: [float("nan"), float("nan")],
            f"{verify.features.FACTOR_NAME}_eligible": [False, False],
        }
    ).loc[:, verify.features.OUTPUT_COLUMNS]


def _item(frame: pd.DataFrame) -> dict:
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign151_feature_partition",
        "symbol": "SH600000",
        "year": 2021,
        "rows": len(frame),
        "eligible_rows": 0,
        "output_byte_sha256": "",
        "output_frame_sha256": verify.features.foundation.frame_digest(frame),
    }


def test_campaign151_verification_protocol_and_manifest_are_metadata_bound() -> None:
    protocol = verify.load_protocol()
    manifest = verify.load_manifest_metadata()
    assert protocol["terminal_decision"]["formula_or_gate_rescue_allowed"] is False
    assert manifest["partitions"] == 33_015
    assert manifest["rows"] == 7_724_498
    assert manifest["eligible_rows"] == 0
    assert manifest["quality"]["nonpositive_peer_clock_rows"] == 7_724_498


def test_campaign151_verification_path_containment_fails_closed(
    tmp_path: Path,
) -> None:
    root = tmp_path / "snapshot" / "partitions"
    valid = root / "2021" / "sh600000.parquet"
    valid.parent.mkdir(parents=True)
    valid.touch()
    assert verify._contained_path(str(valid), root=root, label="data") == valid
    with pytest.raises(verify.Campaign151SnapshotVerificationError, match="escapes"):
        verify._contained_path(
            str(tmp_path / "escaped.parquet"), root=root, label="data"
        )


def test_campaign151_zero_coverage_frame_semantics_pass() -> None:
    frame = _zero_frame()
    assert verify.validate_partition_frame(frame, _item(frame)) == (2, 0)


@pytest.mark.parametrize("mutation", ["eligible", "value", "duplicate", "provider"])
def test_campaign151_partition_semantic_mutations_fail_closed(mutation: str) -> None:
    frame = _zero_frame()
    if mutation == "eligible":
        frame.loc[0, f"{verify.features.FACTOR_NAME}_eligible"] = True
    elif mutation == "value":
        frame.loc[0, verify.features.FACTOR_NAME] = 0.5
    elif mutation == "duplicate":
        frame.loc[1, "trade_date"] = frame.loc[0, "trade_date"]
    else:
        frame.loc[0, "provider"] = "other"
    with pytest.raises(verify.Campaign151SnapshotVerificationError):
        verify.validate_partition_frame(frame, _item(frame))


def test_campaign151_partition_bytes_frame_and_sidecar_are_all_required(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "snapshot"
    path = root / "partitions/2021/sh600000.parquet"
    sidecar = root / ".metadata/partitions/2021/sh600000.json"
    path.parent.mkdir(parents=True)
    sidecar.parent.mkdir(parents=True)
    frame = _zero_frame()
    frame.to_parquet(path, index=False)
    item = _item(frame)
    item["path"] = str(path)
    item["sidecar_path"] = str(sidecar)
    item["output_byte_sha256"] = verify.file_sha256(path)
    sidecar.write_text(json.dumps(item), encoding="utf-8")
    monkeypatch.setattr(verify, "SNAPSHOT_ROOT", root)
    observed = verify.verify_partition(item)
    assert observed["rows"] == 2
    assert observed["eligible_rows"] == 0
    sidecar.write_text("{}", encoding="utf-8")
    with pytest.raises(verify.Campaign151SnapshotVerificationError, match="sidecar"):
        verify.verify_partition(item)


def test_campaign151_dataset_digest_matches_builder_payload() -> None:
    records = [
        {
            "symbol": "SH600000",
            "year": 2019,
            "output_byte_sha256": "a" * 64,
        },
        {
            "symbol": "SZ000001",
            "year": 2020,
            "output_byte_sha256": "b" * 64,
        },
    ]
    payload = (
        f"benchmark|{verify.BENCHMARK_BYTE_SHA256}\n"
        f"SH600000|2019|{'a' * 64}\n"
        f"SZ000001|2020|{'b' * 64}"
    ).encode()
    assert verify.dataset_digest(records) == hashlib.sha256(payload).hexdigest()


def test_campaign151_benchmark_position_tuples_compare_as_objects() -> None:
    expected = tuple(range(verify.features.PROFILE_POSITIONS))
    observed = pd.Series([expected, expected], dtype="object")
    assert verify.position_sets_are_exact(observed)
    changed = list(expected)
    changed[-1] = 238
    observed.iloc[-1] = tuple(changed)
    assert not verify.position_sets_are_exact(observed)


def test_campaign151_verification_confirmation_and_worker_bounds_fail_closed() -> None:
    with pytest.raises(verify.Campaign151SnapshotVerificationError, match="confirm"):
        verify.verify(workers=4, confirm_snapshot_verification=False)
    with pytest.raises(verify.Campaign151SnapshotVerificationError, match="workers"):
        verify.verify(workers=0, confirm_snapshot_verification=True)
