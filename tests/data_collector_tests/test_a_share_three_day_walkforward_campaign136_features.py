from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from scripts import a_share_three_day_walkforward_campaign136_features as features
from scripts import a_share_three_day_walkforward_campaign136_formula as formula


def _calendar() -> pd.DatetimeIndex:
    return pd.date_range("2018-12-28", "2019-01-08", freq="B")


def _raw() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2018-12-31", "2019-01-01", "2019-01-02", "2019-01-04"]
            ),
            "symbol": ["SH600000"] * 4,
            "factor": [1.0, 1.0, 1.1, 1.2],
            "price_basis": [formula.PRICE_BASIS] * 4,
            "daily_source": [formula.DAILY_SOURCE] * 4,
        },
        columns=features.SOURCE_COLUMNS,
    )


def test_frozen_protocol_formula_and_source_contract_bindings() -> None:
    spec = features.validate_protocol()
    assert hashlib.sha256(formula.PROTOCOL_PATH.read_bytes()).hexdigest() == (
        features.PROTOCOL_SHA256
    )
    snapshot = spec["source_snapshot_contract"]
    assert snapshot["source_file_count"] == 5451
    assert snapshot["output_signal_start"] == "2019-01-01"
    assert snapshot["output_signal_end"] == "2025-12-31"
    assert snapshot["source_rows_after_output_signal_end_allowed"] is False


def test_source_bound_implementation_freeze_is_live() -> None:
    record = features.validate_implementation_freeze()
    frozen = record["frozen_implementation"]
    assert frozen["feature_builder_sha256"] == features.file_sha256(
        Path(features.__file__).resolve()
    )
    assert frozen["source_projection"] == list(features.SOURCE_COLUMNS)


def test_build_symbol_frame_requires_calendar_adjacent_predecessor() -> None:
    output, quality = features.build_symbol_frame(
        _raw(), symbol="SH600000", calendar=_calendar()
    )
    assert output["trade_date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2019-01-01",
        "2019-01-02",
        "2019-01-04",
    ]
    assert output[f"{formula.FACTOR_NAME}_eligible"].tolist() == [True, True, False]
    assert output[formula.FACTOR_NAME].iloc[:2].tolist() == pytest.approx(
        [0.0, np.log(1.1)]
    )
    assert np.isnan(output[formula.FACTOR_NAME].iloc[2])
    assert quality["exact_zero_score_pairs"] == 1
    assert quality["nonadjacent_or_missing_predecessor_pairs"] == 1


def test_source_identity_mismatch_and_invalid_factor_are_ineligible() -> None:
    raw = _raw()
    raw.loc[1, "price_basis"] = "future_qfq"
    raw.loc[2, "factor"] = 0.0
    output, quality = features.build_symbol_frame(
        raw, symbol="SH600000", calendar=_calendar()
    )
    assert output[f"{formula.FACTOR_NAME}_eligible"].tolist() == [False, False, False]
    assert output[formula.FACTOR_NAME].isna().all()
    assert quality["invalid_factor_pairs"] == 2
    assert quality["invalid_source_identity_pairs"] == 1


def test_first_source_row_without_predecessor_is_ineligible() -> None:
    raw = pd.DataFrame(
        {
            "date": pd.to_datetime(["2019-01-02"]),
            "symbol": ["SH600000"],
            "factor": [1.0],
            "price_basis": [formula.PRICE_BASIS],
            "daily_source": [formula.DAILY_SOURCE],
        },
        columns=features.SOURCE_COLUMNS,
    )
    output, quality = features.build_symbol_frame(
        raw, symbol="SH600000", calendar=_calendar()
    )
    assert output[f"{formula.FACTOR_NAME}_eligible"].tolist() == [False]
    assert output[formula.FACTOR_NAME].isna().all()
    assert quality["invalid_factor_pairs"] == 1


def test_duplicate_date_symbol_and_projection_changes_fail_closed() -> None:
    duplicate = pd.concat([_raw(), _raw().iloc[[1]]], ignore_index=True)
    with pytest.raises(features.Campaign136FeatureError, match="invalid dates"):
        features.build_symbol_frame(duplicate, symbol="SH600000", calendar=_calendar())
    with pytest.raises(features.Campaign136FeatureError, match="projection"):
        features.build_symbol_frame(
            _raw().drop(columns="daily_source"),
            symbol="SH600000",
            calendar=_calendar(),
        )


def test_source_identity_digest_is_ordered_and_byte_sensitive(tmp_path: Path) -> None:
    first = tmp_path / "sh600000.parquet"
    second = tmp_path / "sz000001.parquet"
    table = pa.Table.from_pydict({"factor": [1.0]})
    pq.write_table(table, second)
    pq.write_table(table, first)
    identity = features.source_identity(tmp_path)
    items = [
        [path.name, path.stat().st_size, features.file_sha256(path)]
        for path in [first, second]
    ]
    assert identity["file_count"] == 2
    assert identity["file_identity_order_sha256"] == features.canonical_sha256(items)
    original = identity["file_identity_order_sha256"]
    pq.write_table(pa.Table.from_pydict({"factor": [2.0]}), first)
    assert features.source_identity(tmp_path)["file_identity_order_sha256"] != original


def test_snapshot_verifier_checks_hash_schema_and_aggregate(tmp_path: Path) -> None:
    output = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2019-01-02"]),
            "symbol": ["SH600000"],
            "provider": [formula.DAILY_SOURCE],
            formula.FACTOR_NAME: [0.0],
            f"{formula.FACTOR_NAME}_eligible": [True],
        },
        columns=features.OUTPUT_COLUMNS,
    )
    partition = tmp_path / "sh600000.parquet"
    pq.write_table(pa.Table.from_pandas(output, preserve_index=False), partition)
    entry = {
        "path": partition.name,
        "size_bytes": partition.stat().st_size,
        "sha256": features.file_sha256(partition),
        "rows": 1,
        "eligible_rows": 1,
    }
    manifest = {
        "kind": "a_share_three_day_walkforward_campaign136_snapshot",
        "status": "published_and_verified",
        "protocol_sha256": features.PROTOCOL_SHA256,
        "formula_sha256": features.FORMULA_SHA256,
        "implementation_freeze_sha256": features.file_sha256(
            features.IMPLEMENTATION_FREEZE
        ),
        "source_projection": list(features.SOURCE_COLUMNS),
        "output_columns": list(features.OUTPUT_COLUMNS),
        "output_signal_start": "2019-01-01",
        "output_signal_end": "2025-12-31",
        "partitions": [entry],
        "partition_count": 1,
        "rows": 1,
        "eligible_rows": 1,
        "dataset_sha256": features._dataset_digest([entry]),
    }
    (tmp_path / features.MANIFEST_NAME).write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    verified = features.verify_snapshot(tmp_path, verify_source=False)
    assert verified["verified"] is True
    assert verified["rows"] == verified["eligible_rows"] == 1
    partition.write_bytes(partition.read_bytes() + b"changed")
    with pytest.raises(features.Campaign136FeatureError, match="partition changed"):
        features.verify_snapshot(tmp_path, verify_source=False)
