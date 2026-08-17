#!/usr/bin/env python3
"""Build Campaign074's terminal-bar amount-share snapshot without returns.

The builder reads only ``datetime,symbol,provider,amount`` from the frozen
one-minute source and the joint-clean stock-day identity.  It never reads a
daily price, forward return, comparator value, or Candidate49 outcome.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from scripts import a_share_three_day_walkforward_campaign073_features as c73
from scripts import a_share_three_day_preregistration_binding_validator as bindings


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_074_no_return_preregistration_v3.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_074_feature_implementation_freeze_20260806.json"
)
DEFAULT_CALENDAR = c73.DEFAULT_CALENDAR
RAW_MANIFEST_RELATIVE = c73.RAW_MANIFEST_RELATIVE
CLEAN_MANIFEST_RELATIVE = c73.CLEAN_MANIFEST_RELATIVE

FACTOR_NAME = "intraday_terminal_bar_amount_share_240m"
FACTOR_FORMULA = (
    "amount at exact 15:00 divided by the positive sum of nonnegative finite "
    "amount over exact 09:31-11:30 and 13:01-15:00 bars"
)
PROTOCOL_SHA256 = "d327fef56cc6561c76f0620e2bcba25e1e07d1e70c681e7ff858eeb396d4c055"
MECHANISM_AUDIT_SHA256 = "ad656846ffecad1e59adf50a08c8ee85a2cd8547b8cc7205dd32423c6c21d291"
NUMERIC_POLICY_SHA256 = "1af4a2432e0186a47a8a69ddefdda25756810cf47b11ff0688d0cbd832438c03"
RAW_MANIFEST_SHA256 = c73.RAW_MANIFEST_SHA256
CLEAN_MANIFEST_SHA256 = c73.CLEAN_MANIFEST_SHA256
CLEAN_DATASET_SHA256 = c73.CLEAN_DATASET_SHA256
CALENDAR_SHA256 = c73.CALENDAR_SHA256
EXPECTED_PARTITIONS = c73.EXPECTED_PARTITIONS
EXPECTED_ROWS = c73.EXPECTED_ROWS
FULL_DEFINITION_COUNT = 105
FULL_DEFINITION_ORDER_SHA256 = (
    "bdc79e8c91fd43cd088437a47bdd805e0e4181fca2f4a6ff6714e0a033d34b61"
)
COMPARISON_COUNT = 104
COMPARISON_ORDER_SHA256 = (
    "0d36cb313d4ded22343120b3f93c1f066aa3818415cb6ea186f354217eeacd6b"
)
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign074_feature_library_v1"
)

RAW_COLUMNS = ("datetime", "symbol", "provider", "amount")
IDENTITY_COLUMNS = c73.IDENTITY_COLUMNS
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
CONTINUOUS_MINUTE_CODES = c73.CONTINUOUS_MINUTE_CODES
SOURCE_MINUTE_CODES = c73.SOURCE_MINUTE_CODES
CONTINUOUS_MINUTE_CODE_SET = c73.CONTINUOUS_MINUTE_CODE_SET
SOURCE_MINUTE_CODE_SET = c73.SOURCE_MINUTE_CODE_SET
SELECTED_BAR_COUNT = c73.SELECTED_BAR_COUNT
SOURCE_BAR_COUNT = c73.SOURCE_BAR_COUNT
C73_FACTOR = c73.FACTOR_NAME
C73_RECORD_SHA256 = "dc97df498f35cecbd8b5bb276e949849def5047dff12043f6e2ea6b76770b490"
C73_BINDING_SHA256 = "0bf34d781cff79f9f8e8262173a78699232cfa5271bd12b2fb897a9173698ae7"
C73_MANIFEST_SHA256 = "6b281be298be7df908300db6735e3ed3efc7d7c13b44c2ae679bf5a2073940e4"
C73_DATASET_SHA256 = "2cea2e0502be1c5cc70f93260a96175abac5f36af50482847c35746a80252a5f"


class Campaign074FeatureError(RuntimeError):
    """Fail-closed Campaign074 feature error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _comparison_order_digest(items: Iterable[dict[str, Any]]) -> str:
    return _json_digest(
        [[str(item["name"]), str(item["score_direction"])] for item in items]
    )


def _resolve_repo_path(raw: Any) -> Path:
    path = Path(str(raw or "")).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign074FeatureError(f"Campaign074 {label} changed: {path}")


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = c73.reconstruct_comparisons()
    items.append({"name": C73_FACTOR, "score_direction": "higher"})
    if (
        len(items) != COMPARISON_COUNT
        or _comparison_order_digest(items) != COMPARISON_ORDER_SHA256
        or items[-1] != {"name": C73_FACTOR, "score_direction": "higher"}
    ):
        raise Campaign074FeatureError("Campaign074 numeric comparison order changed")
    return items


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = c73.reconstruct_complete_definitions()
    items.append({"name": C73_FACTOR, "score_direction": "higher"})
    if (
        len(items) != FULL_DEFINITION_COUNT
        or _comparison_order_digest(items) != FULL_DEFINITION_ORDER_SHA256
    ):
        raise Campaign074FeatureError("Campaign074 complete definition order changed")
    return items


def _validate_comparator_sources(spec: dict[str, Any]) -> None:
    c73._validate_comparator_sources(spec)
    chain = spec.get("source_chain") or {}
    c73_link = chain.get("campaign073_terminal_comparator") or {}
    required = (
        (
            c73_link.get("research_record_path"),
            C73_RECORD_SHA256,
            "Campaign073 record",
        ),
        (
            c73_link.get("snapshot_binding_path"),
            C73_BINDING_SHA256,
            "Campaign073 snapshot binding",
        ),
        (
            c73_link.get("snapshot_manifest_path"),
            C73_MANIFEST_SHA256,
            "Campaign073 snapshot manifest",
        ),
    )
    for raw, expected, label in required:
        _require(_resolve_repo_path(raw), expected, label)
    manifest = json.loads(
        _resolve_repo_path(c73_link.get("snapshot_manifest_path")).read_text(
            encoding="utf-8"
        )
    )
    if not (
        c73_link.get("factor") == C73_FACTOR
        and c73_link.get("score_direction") == "higher"
        and c73_link.get("dataset_sha256") == C73_DATASET_SHA256
        and manifest.get("dataset_sha256") == C73_DATASET_SHA256
        and manifest.get("factor_names") == [C73_FACTOR]
    ):
        raise Campaign074FeatureError("Campaign073 comparator semantics changed")


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    _require(path, PROTOCOL_SHA256, "protocol")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign074FeatureError("Campaign074 protocol binding failed")
    overlay = json.loads(path.read_text(encoding="utf-8"))
    overlay_boundary = overlay.get("research_boundary") or {}
    invariants = overlay.get("frozen_invariants") or {}
    if not (
        overlay.get("kind")
        == "a_share_three_day_walkforward_campaign074_no_return_preregistration_repair_overlay"
        and overlay.get("status")
        == "frozen_effective_protocol_before_campaign074_minute_source_candidate_comparison_daily_price_or_return_values"
        and invariants.get("candidate") == FACTOR_NAME
        and invariants.get("direction") == "higher"
        and invariants.get("formula_changed_from_v1") is False
        and invariants.get("complete_definition_count") == FULL_DEFINITION_COUNT
        and invariants.get("complete_definition_order_sha256")
        == FULL_DEFINITION_ORDER_SHA256
        and invariants.get("numeric_comparator_count") == COMPARISON_COUNT
        and invariants.get("numeric_comparator_order_sha256")
        == COMPARISON_ORDER_SHA256
        and invariants.get("coverage_thresholds_changed_from_v1") is False
        and invariants.get("uniqueness_thresholds_changed_from_v1") is False
        and overlay_boundary.get("candidate_source_rows_read_before_this_overlay")
        is False
        and overlay_boundary.get("candidate_values_read_before_this_overlay") is False
        and overlay_boundary.get("comparison_values_read_before_this_overlay")
        is False
        and overlay_boundary.get("historical_forward_returns_read") is False
        and overlay_boundary.get("provider_request_issued") is False
    ):
        raise Campaign074FeatureError("Campaign074 protocol overlay changed")
    base_link = overlay.get("effective_protocol_base") or {}
    base_path = _resolve_repo_path(base_link.get("path"))
    base_sha = str(base_link.get("sha256") or "")
    _require(base_path, base_sha, "effective protocol base")
    base_report = bindings.validate_record(base_path, data_root=DEFAULT_DATA_ROOT)
    if base_report.get("all_bindings_passed") is not True:
        raise Campaign074FeatureError("Campaign074 protocol-base binding failed")
    spec = json.loads(base_path.read_text(encoding="utf-8"))
    patch = overlay.get("campaign072_comparator_source_patch") or {}
    c72_source = (spec.get("source_chain") or {}).get(
        "campaign072_terminal_comparator"
    ) or {}
    c72_source.update(
        {
            "research_record_path": patch.get("research_record_path"),
            "research_record_sha256": patch.get("research_record_sha256"),
            "snapshot_binding_path": patch.get("snapshot_binding_path"),
            "snapshot_binding_sha256": patch.get("snapshot_binding_sha256"),
        }
    )
    spec["source_chain"]["campaign072_terminal_comparator"] = c72_source
    _validate_comparator_sources(spec)
    chain = spec.get("source_chain") or {}
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    unique = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign074_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign074_minute_source_candidate_comparison_daily_price_or_return_values"
        and (chain.get("numeric_comparison_policy") or {}).get("sha256")
        == NUMERIC_POLICY_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and tuple(candidate.get("minute_source_projection") or ()) == RAW_COLUMNS
        and tuple(candidate.get("stock_day_identity_projection") or ())
        == IDENTITY_COLUMNS
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("terminal_anchor")
        == "Exactly the standard one-minute source amount at 15:00; no dedicated closing-auction feed semantics are claimed."
        and candidate.get("valid_range")
        == {
            "lower": 0.0,
            "lower_inclusive": True,
            "upper": 1.0,
            "upper_inclusive": True,
        }
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and unique.get("complete_definition_count") == FULL_DEFINITION_COUNT
        and unique.get("complete_definition_order_sha256")
        == FULL_DEFINITION_ORDER_SHA256
        and unique.get("numeric_comparator_count") == COMPARISON_COUNT
        and unique.get("numeric_comparator_order_sha256")
        == COMPARISON_ORDER_SHA256
        and unique.get("all_104_numeric_comparators_must_pass") is True
        and len(reconstruct_comparisons()) == COMPARISON_COUNT
        and len(reconstruct_complete_definitions()) == FULL_DEFINITION_COUNT
        and finite.get("trial_id")
        == "wf074_intraday_terminal_bar_amount_share_240m_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("complexity") == 1
        and finite.get("expected_trial_count") == 1
        and boundary.get("minute_or_stock_day_source_rows_read_before_this_freeze")
        is False
        and boundary.get("candidate_or_comparison_values_read_before_this_freeze")
        is False
        and boundary.get("historical_forward_return_fields_read") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign074FeatureError("Campaign074 protocol semantics changed")
    return spec


def extract_terminal_amount_shares(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Validate exact source grids and return one terminal amount share/session."""
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign074FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    empty = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "terminal_amount_share": pd.Series(dtype="float64"),
        }
    )
    empty_quality = {
        "source_rows": 0,
        "source_sessions": 0,
        "valid_terminal_share_sessions": 0,
        "invalid_amount_grid_sessions": 0,
        "nonpositive_total_amount_sessions": 0,
    }
    if raw.empty:
        return empty, empty_quality
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["amount"] = pd.to_numeric(work["amount"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign074FeatureError(f"raw minute identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    distinct_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].nunique()
    if (
        counts.empty
        or not counts.eq(SOURCE_BAR_COUNT).all()
        or not distinct_codes.eq(SOURCE_BAR_COUNT).all()
        or not work["minute_code"].isin(SOURCE_MINUTE_CODE_SET).all()
    ):
        raise Campaign074FeatureError(f"raw minute grid changed for {symbol}")
    continuous = work.loc[
        work["minute_code"].isin(CONTINUOUS_MINUTE_CODE_SET),
        ["trade_date", "minute_code", "amount"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"], categories=CONTINUOUS_MINUTE_CODES, ordered=True
    )
    continuous = continuous.sort_values(
        ["trade_date", "minute_code"], kind="stable"
    )
    dates = pd.DatetimeIndex(counts.index).normalize()
    if len(continuous) != len(dates) * SELECTED_BAR_COUNT:
        raise Campaign074FeatureError(f"continuous minute grid changed for {symbol}")
    matrix = continuous["amount"].to_numpy(dtype=np.float64).reshape(
        len(dates), SELECTED_BAR_COUNT
    )
    amount_valid = np.isfinite(matrix).all(axis=1) & (matrix >= 0.0).all(axis=1)
    totals = matrix.sum(axis=1, dtype=np.float64)
    total_valid = amount_valid & np.isfinite(totals) & (totals > 0.0)
    shares = np.full(len(dates), np.nan, dtype=np.float64)
    shares[total_valid] = matrix[total_valid, -1] / totals[total_valid]
    range_valid = np.isfinite(shares) & (shares >= 0.0) & (shares <= 1.0)
    shares[~range_valid] = np.nan
    return (
        pd.DataFrame({"trade_date": dates, "terminal_amount_share": shares}),
        {
            "source_rows": int(len(work)),
            "source_sessions": int(len(dates)),
            "valid_terminal_share_sessions": int(range_valid.sum()),
            "invalid_amount_grid_sessions": int((~amount_valid).sum()),
            "nonpositive_total_amount_sessions": int(
                (amount_valid & ~total_valid).sum()
            ),
        },
    )


def attach_terminal_amount_shares(
    identity: pd.DataFrame,
    shares: pd.DataFrame,
    *,
    symbol: str,
) -> pd.DataFrame:
    if tuple(identity.columns) != IDENTITY_COLUMNS:
        raise Campaign074FeatureError(f"identity projection changed for {symbol}")
    base = identity.copy()
    base["trade_date"] = pd.to_datetime(
        base["trade_date"], errors="coerce"
    ).dt.normalize()
    base["symbol"] = base["symbol"].astype(str).str.upper()
    base["provider"] = base["provider"].astype(str).str.lower()
    if base.empty:
        base["terminal_amount_share"] = pd.Series(dtype="float64")
        return base
    if (
        base["trade_date"].isna().any()
        or base.duplicated(["trade_date", "symbol"]).any()
        or set(base["symbol"].unique()) != {symbol.upper()}
        or set(base["provider"].unique()) != {"tushare"}
    ):
        raise Campaign074FeatureError(f"joint-clean identity changed for {symbol}")
    source = shares.copy()
    if source.empty or source.duplicated(["trade_date"]).any():
        raise Campaign074FeatureError(f"terminal amount identity changed for {symbol}")
    out = base.merge(source, on="trade_date", how="left", validate="one_to_one")
    raw_dates = set(source["trade_date"].tolist())
    if any(date not in raw_dates for date in out["trade_date"]):
        raise Campaign074FeatureError(
            f"accepted session absent from raw source for {symbol}"
        )
    return out


def finalize_feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = (*IDENTITY_COLUMNS, "terminal_amount_share")
    if not set(required).issubset(frame.columns):
        raise Campaign074FeatureError("terminal amount-share input columns changed")
    work = frame.copy()
    values = pd.to_numeric(work["terminal_amount_share"], errors="coerce")
    eligible = np.isfinite(values) & values.ge(0.0) & values.le(1.0)
    work[FACTOR_NAME] = values.where(eligible)
    work[f"{FACTOR_NAME}_eligible"] = eligible
    work["provider"] = "tushare"
    return work


def empty_output_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="object"),
            "provider": pd.Series(dtype="object"),
            FACTOR_NAME: pd.Series(dtype="float64"),
            f"{FACTOR_NAME}_eligible": pd.Series(dtype="bool"),
        }
    ).loc[:, OUTPUT_COLUMNS]


def validate_value_semantics(frame: pd.DataFrame) -> tuple[int, int]:
    if tuple(frame.columns) != OUTPUT_COLUMNS:
        raise Campaign074FeatureError("Campaign074 output columns changed")
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"].astype(bool)
    if (
        values[eligible].isna().any()
        or ((values[eligible] < 0.0) | (values[eligible] > 1.0)).any()
        or values[~eligible].notna().any()
    ):
        raise Campaign074FeatureError("Campaign074 value semantics changed")
    return int(len(frame)), int(eligible.sum())


def _frame_sha256(frame: pd.DataFrame) -> str:
    sink = pa.BufferOutputStream()
    table = pa.Table.from_pandas(frame, preserve_index=False)
    with pa.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    return hashlib.sha256(sink.getvalue().to_pybytes()).hexdigest()


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived/a_share/rich/tushare/minute_walkforward_campaign074_feature_library"
        / OUTPUT_RUN_ID
    )


_atomic_parquet = c73._atomic_parquet
_atomic_json = c73._atomic_json


def _validate_implementation_freeze() -> dict[str, Any]:
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign074FeatureError("Campaign074 implementation freeze is absent")
    freeze = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    runner = freeze.get("feature_runner") or {}
    tests = freeze.get("tests") or {}
    test_path = REPO_ROOT / str(tests.get("path") or "")
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign074_feature_implementation_freeze"
        and freeze.get("status") == "frozen_before_campaign074_minute_source_values"
        and runner.get("path")
        == "scripts/a_share_three_day_walkforward_campaign074_features.py"
        and runner.get("sha256") == _sha256(Path(__file__).resolve())
        and test_path.is_file()
        and tests.get("sha256") == _sha256(test_path)
        and (freeze.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (freeze.get("mechanism_overlap_audit") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and (freeze.get("research_boundary") or {}).get(
            "candidate_source_rows_read_before_freeze"
        )
        is False
    ):
        raise Campaign074FeatureError("Campaign074 implementation freeze changed")
    return freeze


def _require_inputs(
    data_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], pd.DatetimeIndex]:
    load_protocol()
    freeze = _validate_implementation_freeze()
    raw_path = data_root / RAW_MANIFEST_RELATIVE
    clean_path = data_root / CLEAN_MANIFEST_RELATIVE
    for path, expected, label in (
        (raw_path, RAW_MANIFEST_SHA256, "raw minute manifest"),
        (clean_path, CLEAN_MANIFEST_SHA256, "joint-clean manifest"),
        (DEFAULT_CALENDAR, CALENDAR_SHA256, "calendar"),
    ):
        _require(path, expected, label)
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    clean = json.loads(clean_path.read_text(encoding="utf-8"))
    if not (
        len(raw.get("files") or []) == EXPECTED_PARTITIONS
        and len(clean.get("files") or []) == EXPECTED_PARTITIONS
        and clean.get("dataset_sha256") == CLEAN_DATASET_SHA256
        and clean.get("rows") == EXPECTED_ROWS
        and clean.get("partitions") == EXPECTED_PARTITIONS
    ):
        raise Campaign074FeatureError("Campaign074 source aggregate semantics changed")
    calendar = pd.DatetimeIndex(
        pd.to_datetime(
            [
                line.strip()
                for line in DEFAULT_CALENDAR.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ],
            errors="raise",
        )
    ).normalize()
    return raw, clean, freeze, calendar


def _raw_file_map(raw: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    result: dict[tuple[str, int], dict[str, Any]] = {}
    for item in raw.get("files") or []:
        key = (str(item["symbol"]).upper(), int(item["year"]))
        if key in result:
            raise Campaign074FeatureError(f"duplicate raw partition identity: {key}")
        result[key] = item
    if len(result) != EXPECTED_PARTITIONS:
        raise Campaign074FeatureError("raw partition identity count changed")
    return result


def _load_attached_partition(
    index: int,
    clean_item: dict[str, Any],
    raw_item: dict[str, Any],
) -> tuple[int, pd.DataFrame, dict[str, int]]:
    symbol = str(clean_item["symbol"]).upper()
    identity = pd.read_parquet(clean_item["path"], columns=list(IDENTITY_COLUMNS))
    raw_path = Path(str(raw_item["path"])).expanduser().resolve()
    if not raw_path.is_file():
        raise Campaign074FeatureError(f"raw partition absent: {raw_path}")
    if pq.ParquetFile(raw_path).metadata.num_rows != int(raw_item["rows"]):
        raise Campaign074FeatureError(f"raw partition row count changed: {raw_path}")
    raw = pd.read_parquet(raw_path, columns=list(RAW_COLUMNS))
    shares, quality = extract_terminal_amount_shares(raw, symbol=symbol)
    attached = attach_terminal_amount_shares(identity, shares, symbol=symbol)
    attached["_partition_index"] = index
    return index, attached, quality


def build_snapshot(*, data_root: Path, workers: int = 4) -> Path:
    data_root = data_root.expanduser().resolve()
    raw, clean, freeze, _calendar = _require_inputs(data_root)
    del _calendar
    raw_by_key = _raw_file_map(raw)
    files = list(clean.get("files") or [])
    by_year: dict[int, list[tuple[int, dict[str, Any]]]] = {}
    for index, item in enumerate(files):
        by_year.setdefault(int(item["year"]), []).append((index, item))
    root = output_root(data_root)
    manifest_path = root / "snapshot_manifest.json"
    if manifest_path.exists():
        raise Campaign074FeatureError(
            "Campaign074 snapshot already exists; verify it instead of rebuilding"
        )
    records: list[dict[str, Any] | None] = [None] * len(files)
    totals = {
        "eligible": 0,
        "missing": 0,
        "source_rows": 0,
        "source_sessions": 0,
        "invalid_amount_grid_sessions": 0,
        "nonpositive_total_amount_sessions": 0,
    }
    for year in sorted(by_year):
        jobs: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
        for index, item in by_year[year]:
            key = (str(item["symbol"]).upper(), int(item["year"]))
            raw_item = raw_by_key.get(key)
            if raw_item is None:
                raise Campaign074FeatureError(f"raw partition missing for {key}")
            jobs.append((index, item, raw_item))
        pieces: list[pd.DataFrame] = []
        quality_by_index: dict[int, dict[str, int]] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = [
                pool.submit(_load_attached_partition, index, item, raw_item)
                for index, item, raw_item in jobs
            ]
            for future in concurrent.futures.as_completed(futures):
                index, attached, quality = future.result()
                pieces.append(attached)
                quality_by_index[index] = quality
                totals["source_rows"] += quality["source_rows"]
                totals["source_sessions"] += quality["source_sessions"]
                totals["invalid_amount_grid_sessions"] += quality[
                    "invalid_amount_grid_sessions"
                ]
                totals["nonpositive_total_amount_sessions"] += quality[
                    "nonpositive_total_amount_sessions"
                ]
        if not pieces:
            raise Campaign074FeatureError(f"Campaign074 year {year} has no partitions")
        year_frame = finalize_feature_frame(pd.concat(pieces, ignore_index=True))
        grouped = {
            int(index): group
            for index, group in year_frame.groupby("_partition_index", sort=False)
        }
        for index, item in by_year[year]:
            group = grouped.get(index)
            if group is None:
                out = empty_output_frame()
            else:
                out = (
                    group.loc[:, OUTPUT_COLUMNS]
                    .sort_values("trade_date", kind="stable")
                    .reset_index(drop=True)
                )
            validate_value_semantics(out)
            relative = (
                Path("partitions")
                / str(item["symbol"]).lower()
                / f"{int(item['year'])}.parquet"
            )
            path = root / relative
            _atomic_parquet(out, path)
            eligible = int(out[f"{FACTOR_NAME}_eligible"].sum())
            missing = int(len(out) - eligible)
            totals["eligible"] += eligible
            totals["missing"] += missing
            raw_item = raw_by_key[(str(item["symbol"]).upper(), int(item["year"]))]
            records[index] = {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign074_feature_partition",
                "status": "complete_pending_aggregate_publication",
                "path": str(path.resolve()),
                "relative_path": str(relative),
                "symbol": str(item["symbol"]),
                "code": str(item["code"]),
                "year": int(item["year"]),
                "rows": int(len(out)),
                "output_byte_sha256": _sha256(path),
                "output_frame_sha256": _frame_sha256(out),
                "joint_clean_path": str(item["path"]),
                "joint_clean_byte_sha256": str(item["output_byte_sha256"]),
                "raw_source_path": str(raw_item["path"]),
                "raw_source_manifest_byte_sha256": str(raw_item["byte_sha256"]),
                "raw_source_rows": int(raw_item["rows"]),
                "source_fields_read": list(RAW_COLUMNS),
                "factor_eligible_rows": {FACTOR_NAME: eligible},
                "quality": {
                    "base_rows": int(len(out)),
                    f"{FACTOR_NAME}__eligible_rows": eligible,
                    f"{FACTOR_NAME}__missing_rows": missing,
                    **quality_by_index[index],
                },
                "protocol_sha256": PROTOCOL_SHA256,
                "implementation_freeze_sha256": _sha256(
                    DEFAULT_IMPLEMENTATION_FREEZE
                ),
                "daily_price_fields_read": [],
                "forward_return_fields_read": False,
                "comparison_factor_values_read": False,
                "provider_request_issued": False,
            }
        print(
            f"Campaign074 built year={year} partitions={len(by_year[year])} "
            f"eligible_rows={totals['eligible']}",
            flush=True,
        )
    completed = [item for item in records if item is not None]
    if (
        len(completed) != EXPECTED_PARTITIONS
        or sum(int(item["rows"]) for item in completed) != EXPECTED_ROWS
    ):
        raise Campaign074FeatureError("Campaign074 publication totals changed")
    digest_rows = [
        [
            item["relative_path"],
            item["output_byte_sha256"],
            item["output_frame_sha256"],
            item["rows"],
        ]
        for item in completed
    ]
    manifest = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign074_feature_snapshot",
        "status": "feature_library_complete_pending_ordered_no_return_gates",
        "output_run_id": OUTPUT_RUN_ID,
        "dataset_sha256": _json_digest(digest_rows),
        "partitions": EXPECTED_PARTITIONS,
        "rows": EXPECTED_ROWS,
        "files": completed,
        "factor_names": [FACTOR_NAME],
        "factor_directions": {FACTOR_NAME: "higher"},
        "factor_ranges": {FACTOR_NAME: [0.0, 1.0]},
        "factor_upper_endpoint_exclusive": {FACTOR_NAME: False},
        "factor_formulas": {FACTOR_NAME: FACTOR_FORMULA},
        "factor_eligible_rows": {FACTOR_NAME: totals["eligible"]},
        "quality": {
            "base_rows": EXPECTED_ROWS,
            f"{FACTOR_NAME}__eligible_rows": totals["eligible"],
            f"{FACTOR_NAME}__missing_rows": totals["missing"],
            "raw_source_rows_read": totals["source_rows"],
            "raw_source_sessions": totals["source_sessions"],
            "invalid_amount_grid_sessions": totals["invalid_amount_grid_sessions"],
            "nonpositive_total_amount_sessions": totals[
                "nonpositive_total_amount_sessions"
            ],
        },
        "source_fields_read": list(RAW_COLUMNS),
        "joint_clean_identity_fields_read": list(IDENTITY_COLUMNS),
        "source_selected_bar_count": SELECTED_BAR_COUNT,
        "source_minute_grid": "09:30 plus 09:31-11:30 and 13:01-15:00; factor excludes 09:30 and selects the latter exact 240 amount bars",
        "terminal_amount_anchor": "standard one-minute source amount at exact 15:00",
        "dedicated_closing_auction_feed_claimed": False,
        "normalization_rule": "15:00 amount divided by exact 240-bar selected amount total",
        "raw_manifest_sha256": RAW_MANIFEST_SHA256,
        "joint_clean_manifest_sha256": CLEAN_MANIFEST_SHA256,
        "joint_clean_dataset_sha256": CLEAN_DATASET_SHA256,
        "protocol_sha256": PROTOCOL_SHA256,
        "mechanism_overlap_audit_sha256": MECHANISM_AUDIT_SHA256,
        "implementation_freeze_sha256": _sha256(DEFAULT_IMPLEMENTATION_FREEZE),
        "implementation_freeze_status": freeze.get("status"),
        "daily_price_fields_read": [],
        "forward_return_fields_read": False,
        "comparison_factor_values_read": False,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
        "training_or_model_fitting_performed": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
        "prospective_candidate_activation_created": False,
        "provider_request_issued": False,
    }
    _atomic_json(manifest, manifest_path)
    return manifest_path


def _validate_manifest(manifest: dict[str, Any]) -> None:
    quality = manifest.get("quality") or {}
    files = list(manifest.get("files") or [])
    eligible = (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign074_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and len(files) == EXPECTED_PARTITIONS
        and manifest.get("rows") == EXPECTED_ROWS
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == {FACTOR_NAME: "higher"}
        and manifest.get("factor_ranges") == {FACTOR_NAME: [0.0, 1.0]}
        and manifest.get("factor_upper_endpoint_exclusive")
        == {FACTOR_NAME: False}
        and manifest.get("factor_formulas") == {FACTOR_NAME: FACTOR_FORMULA}
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("joint_clean_identity_fields_read")
        == list(IDENTITY_COLUMNS)
        and manifest.get("source_selected_bar_count") == SELECTED_BAR_COUNT
        and manifest.get("terminal_amount_anchor")
        == "standard one-minute source amount at exact 15:00"
        and manifest.get("dedicated_closing_auction_feed_claimed") is False
        and manifest.get("protocol_sha256") == PROTOCOL_SHA256
        and manifest.get("mechanism_overlap_audit_sha256")
        == MECHANISM_AUDIT_SHA256
        and quality.get("base_rows") == EXPECTED_ROWS
        and quality.get(f"{FACTOR_NAME}__eligible_rows") == eligible
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("candidate49_historical_return_read") is False
        and manifest.get("candidate49_ledgers_changed") is False
        and manifest.get("training_or_model_fitting_performed") is False
        and manifest.get("current_scoring_selection_sizing_or_orders_performed")
        is False
        and manifest.get("prospective_candidate_activation_created") is False
        and manifest.get("provider_request_issued") is False
    ):
        raise Campaign074FeatureError("Campaign074 manifest semantics changed")


def verify_snapshot_files(
    manifest_path: Path, *, workers: int = 4
) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    expected = (output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json").resolve()
    if manifest_path != expected:
        raise Campaign074FeatureError("Campaign074 manifest path changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_manifest(manifest)
    partition_root = (manifest_path.parent / "partitions").resolve()

    def verify(item: dict[str, Any]) -> tuple[int, int]:
        path = Path(str(item["path"])).expanduser().resolve()
        path.relative_to(partition_root)
        if _sha256(path) != item["output_byte_sha256"]:
            raise Campaign074FeatureError(f"partition byte hash changed: {path}")
        frame = pd.read_parquet(path)
        if (
            len(frame) != item["rows"]
            or _frame_sha256(frame) != item["output_frame_sha256"]
        ):
            raise Campaign074FeatureError(f"partition frame changed: {path}")
        return validate_value_semantics(frame)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        verified = list(pool.map(verify, manifest["files"]))
    digest_rows = [
        [
            item["relative_path"],
            item["output_byte_sha256"],
            item["output_frame_sha256"],
            item["rows"],
        ]
        for item in manifest["files"]
    ]
    if not (
        _json_digest(digest_rows) == manifest["dataset_sha256"]
        and len(verified) == EXPECTED_PARTITIONS
        and sum(value[0] for value in verified) == EXPECTED_ROWS
        and sum(value[1] for value in verified)
        == (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    ):
        raise Campaign074FeatureError("Campaign074 aggregate identity changed")
    return {
        "status": "verified",
        "partitions": len(verified),
        "rows": sum(value[0] for value in verified),
        "eligible_rows": sum(value[1] for value in verified),
        "dataset_sha256": manifest["dataset_sha256"],
        "comparison_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def status(data_root: Path) -> dict[str, Any]:
    load_protocol()
    path = output_root(data_root.expanduser().resolve()) / "snapshot_manifest.json"
    return {
        "status": "snapshot_present" if path.is_file() else "snapshot_absent_pre_build",
        "snapshot_manifest": str(path),
        "source_fields_read_by_status": [],
        "candidate_or_comparison_values_read_by_status": False,
        "historical_daily_price_or_forward_return_values_read_by_status": False,
        "provider_request_issued_by_status": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    build.add_argument("--workers", type=int, default=4)
    inspect = subparsers.add_parser("status")
    inspect.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.command == "build":
        payload = {
            "snapshot_manifest": str(
                build_snapshot(data_root=args.data_root, workers=args.workers)
            )
        }
    elif args.command == "verify":
        payload = verify_snapshot_files(args.manifest, workers=args.workers)
    else:
        payload = status(args.data_root)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
