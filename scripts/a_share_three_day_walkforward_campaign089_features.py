#!/usr/bin/env python3
"""Build Campaign089's frozen directional amount-timing-spread snapshot."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from scripts import a_share_three_day_compact_comparator_cache as cache_v1
from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign085_features as c85
from scripts import a_share_three_day_walkforward_campaign086_features as c86
from scripts import a_share_three_day_walkforward_campaign088_features as c88

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = c88.DEFAULT_DATA_ROOT
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_089_no_return_preregistration.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_089_feature_implementation_freeze_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign089_features.py"
)

PROTOCOL_SHA256 = "444e6aecdd82ad8f9ca909063bb42a5bf6453b826067f637e2bc54977d14e1be"
MECHANISM_AUDIT_SHA256 = (
    "837621b6ee61f659e7b82f589758cea43b98143bb3e1f0aa2fbae3b6b3fd74a9"
)
CURRENT_STATE_SHA256 = (
    "985f80fb46c1abdc4dc29f49e3525d292ca5632d67e7448d3f7ff00996ac4a37"
)
NUMERIC_POLICY_SHA256 = (
    "5a8f14e6740fa6fabb72b0ef455d173502cfa4c0e1542f808852665afbb2fc35"
)
C88_SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_088_feature_snapshot_binding_20260807.json"
)
C88_SNAPSHOT_BINDING_SHA256 = (
    "15a17b1db513901a3a56ac3e39768971a78e9319937c8ac18eb980d362a33064"
)
C88_SNAPSHOT_MANIFEST = c88.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
C88_SNAPSHOT_MANIFEST_SHA256 = (
    "fd244df87c30d273f53e376561d03956c91f326237ae78cb16dc57906a136d41"
)
C88_SNAPSHOT_DATASET_SHA256 = (
    "022e0bed5b6dc3ea50e069c44aa4e834aeaa6ec65444e87d75287cbeedf3d756"
)

FACTOR_NAME = "intraday_directional_amount_timing_spread_238m"
FACTOR_FORMULA = (
    "on exactly 238 within-half adjacent log-close returns with destination "
    "amount A_k and u_k=k/237, return the separately normalized positive-return "
    "amount clock center minus the negative-return amount clock center"
)
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_walkforward_"
    "campaign089_feature_library_v1"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "close", "amount")
IDENTITY_COLUMNS = c86.IDENTITY_COLUMNS
SELECTED_BAR_COUNT = c86.SELECTED_BAR_COUNT
SOURCE_BAR_COUNT = c86.SOURCE_BAR_COUNT
RETURN_COUNT = 238
CLOCK_DENOMINATOR = 237
ENDPOINT_TOLERANCE = 1e-12
OUTPUT_COLUMNS = ("stock_day_key", FACTOR_NAME, f"{FACTOR_NAME}_eligible")
EXPECTED_ROWS = c86.EXPECTED_ROWS
EXPECTED_PARTITIONS = c86.EXPECTED_PARTITIONS
EXPECTED_SESSIONS = c86.EXPECTED_SESSIONS
EXPECTED_RAW_PARTITIONS = c86.EXPECTED_RAW_PARTITIONS
EXPECTED_JOINT_CLEAN_ROWS = c86.EXPECTED_JOINT_CLEAN_ROWS
FULL_DEFINITION_COUNT = 120
FULL_DEFINITION_ORDER_SHA256 = (
    "9f0d70e832e7a1e5a62a312d79441621eda5822ff3de9155edc108409dcdb276"
)
COMPARISON_COUNT = 118
COMPARISON_ORDER_SHA256 = (
    "a83d4485182d4dc6a2173af4c3158a3290939740c5465991a69521fdc65607c2"
)


class Campaign089FeatureError(RuntimeError):
    """Fail-closed Campaign089 feature error."""


def _sha256(path: Path) -> str:
    return c86._sha256(path)


def _json_digest(value: Any) -> str:
    return c86._json_digest(value)


def _comparison_order_digest(items: list[dict[str, str]]) -> str:
    return c86._comparison_order_digest(items)


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign089FeatureError(f"Campaign089 {label} changed: {path}")


def _freeze_v28_order(
    items: list[dict[str, str]], *, expected_count: int, expected_digest: str
) -> tuple[tuple[str, str], ...]:
    frozen = tuple((str(item["name"]), str(item["score_direction"])) for item in items)
    materialized = [
        {"name": name, "score_direction": direction} for name, direction in frozen
    ]
    if (
        len(materialized) != expected_count
        or _comparison_order_digest(materialized) != expected_digest
        or materialized[-1] != {"name": c88.FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign089FeatureError("Campaign089 v28 frozen order changed")
    return frozen


_FROZEN_V28_COMPARISONS = _freeze_v28_order(
    [
        *c88.reconstruct_comparisons(),
        {"name": c88.FACTOR_NAME, "score_direction": "higher"},
    ],
    expected_count=COMPARISON_COUNT,
    expected_digest=COMPARISON_ORDER_SHA256,
)
_FROZEN_V28_DEFINITIONS = _freeze_v28_order(
    [
        *c88.reconstruct_complete_definitions(),
        {"name": c88.FACTOR_NAME, "score_direction": "higher"},
    ],
    expected_count=FULL_DEFINITION_COUNT,
    expected_digest=FULL_DEFINITION_ORDER_SHA256,
)


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = [
        {"name": name, "score_direction": direction}
        for name, direction in _FROZEN_V28_COMPARISONS
    ]
    if (
        len(items) != COMPARISON_COUNT
        or _comparison_order_digest(items) != COMPARISON_ORDER_SHA256
        or items[-1] != {"name": c88.FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign089FeatureError("Campaign089 comparison order changed")
    return items


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = [
        {"name": name, "score_direction": direction}
        for name, direction in _FROZEN_V28_DEFINITIONS
    ]
    if (
        len(items) != FULL_DEFINITION_COUNT
        or _comparison_order_digest(items) != FULL_DEFINITION_ORDER_SHA256
        or items[-1] != {"name": c88.FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign089FeatureError("Campaign089 definition order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    _require(path, PROTOCOL_SHA256, "protocol")
    _require(C88_SNAPSHOT_BINDING, C88_SNAPSHOT_BINDING_SHA256, "Campaign088 binding")
    _require(
        C88_SNAPSHOT_MANIFEST,
        C88_SNAPSHOT_MANIFEST_SHA256,
        "Campaign088 manifest",
    )
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign089FeatureError("Campaign089 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    chain = spec.get("source_chain") or {}
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    unique = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    previous = json.loads(C88_SNAPSHOT_MANIFEST.read_text(encoding="utf-8"))
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign089_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign089_minute_source_candidate_comparison_daily_price_or_return_values"
        and (chain.get("mechanism_overlap_audit") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and (chain.get("authoritative_iteration_state") or {}).get("sha256")
        == CURRENT_STATE_SHA256
        and (chain.get("numeric_comparator_policy_v28") or {}).get("sha256")
        == NUMERIC_POLICY_SHA256
        and (chain.get("campaign088_terminal_numeric_comparator") or {}).get(
            "dataset_sha256"
        )
        == C88_SNAPSHOT_DATASET_SHA256
        and previous.get("dataset_sha256") == C88_SNAPSHOT_DATASET_SHA256
        and previous.get("factor_names") == [c88.FACTOR_NAME]
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and tuple(candidate.get("minute_source_projection") or ()) == RAW_COLUMNS
        and tuple(candidate.get("stock_day_identity_projection") or ())
        == IDENTITY_COLUMNS
        and candidate.get("selected_close_count") == SELECTED_BAR_COUNT
        and candidate.get("total_return_count") == RETURN_COUNT
        and candidate.get("destination_amount_count") == RETURN_COUNT
        and candidate.get("clock_coordinate_denominator") == CLOCK_DENOMINATOR
        and candidate.get("endpoint_canonicalization_tolerance") == ENDPOINT_TOLERANCE
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and unique.get("complete_definition_count") == FULL_DEFINITION_COUNT
        and unique.get("complete_definition_order_sha256")
        == FULL_DEFINITION_ORDER_SHA256
        and unique.get("numeric_comparator_count") == COMPARISON_COUNT
        and unique.get("numeric_comparator_order_sha256") == COMPARISON_ORDER_SHA256
        and unique.get("all_118_numeric_comparators_must_pass") is True
        and len(reconstruct_comparisons()) == COMPARISON_COUNT
        and len(reconstruct_complete_definitions()) == FULL_DEFINITION_COUNT
        and finite.get("trial_id")
        == "wf089_intraday_directional_amount_timing_spread_238m_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1]
        and finite.get("expected_trial_count") == 1
        and boundary.get("comparison_values_read_before_coverage_pass") is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign089FeatureError("Campaign089 protocol semantics changed")
    return spec


def compute_directional_amount_timing_spread(
    closes: np.ndarray, destination_amounts: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return score, eligibility, U, D, T_up, and T_down."""

    close = np.asarray(closes, dtype=np.float64)
    amount = np.asarray(destination_amounts, dtype=np.float64)
    if close.ndim != 2 or close.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign089FeatureError("Campaign089 requires an n-by-240 close array")
    if amount.ndim != 2 or amount.shape != (len(close), RETURN_COUNT):
        raise Campaign089FeatureError("Campaign089 requires an n-by-238 amount array")
    source_valid = (
        np.isfinite(close).all(axis=1)
        & (close > 0.0).all(axis=1)
        & np.isfinite(amount).all(axis=1)
        & (amount >= 0.0).all(axis=1)
    )
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        logged = np.log(close)
        returns = np.concatenate(
            (np.diff(logged[:, :120], axis=1), np.diff(logged[:, 120:], axis=1)),
            axis=1,
        )
    clock = np.arange(RETURN_COUNT, dtype=np.float64) / float(CLOCK_DENOMINATOR)
    up_amount = np.where(returns > 0.0, amount, 0.0)
    down_amount = np.where(returns < 0.0, amount, 0.0)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        up_mass = np.sum(up_amount, axis=1, dtype=np.float64)
        down_mass = np.sum(down_amount, axis=1, dtype=np.float64)
        up_center = np.sum(up_amount * clock, axis=1, dtype=np.float64) / up_mass
        down_center = np.sum(down_amount * clock, axis=1, dtype=np.float64) / down_mass
        score = up_center - down_center
    support = (
        source_valid
        & np.isfinite(returns).all(axis=1)
        & np.isfinite(up_mass)
        & (up_mass > 0.0)
        & np.isfinite(down_mass)
        & (down_mass > 0.0)
        & np.isfinite(up_center)
        & np.isfinite(down_center)
    )
    result = np.full(len(close), np.nan, dtype=np.float64)
    candidate = score[support].copy()
    candidate[np.abs(candidate) <= ENDPOINT_TOLERANCE] = 0.0
    candidate[np.abs(candidate - 1.0) <= ENDPOINT_TOLERANCE] = 1.0
    candidate[np.abs(candidate + 1.0) <= ENDPOINT_TOLERANCE] = -1.0
    valid_score = np.isfinite(candidate) & (candidate >= -1.0) & (candidate <= 1.0)
    positions = np.flatnonzero(support)
    result[positions[valid_score]] = candidate[valid_score]
    eligible = np.isfinite(result) & (result >= -1.0) & (result <= 1.0)
    result[~eligible] = np.nan
    return result, eligible, up_mass, down_mass, up_center, down_center


def extract_directional_amount_timing_spread(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign089FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    empty = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            FACTOR_NAME: pd.Series(dtype="float64"),
        }
    )
    empty_quality = {
        "source_rows": 0,
        "source_sessions": 0,
        "valid_directional_timing_sessions": 0,
        "invalid_selected_source_sessions": 0,
        "nonpositive_up_mass_sessions": 0,
        "nonpositive_down_mass_sessions": 0,
        "zero_returns": 0,
        "zero_destination_amounts": 0,
    }
    if raw.empty:
        return empty, empty_quality
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["close"] = pd.to_numeric(work["close"], errors="coerce")
    work["amount"] = pd.to_numeric(work["amount"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign089FeatureError(f"raw minute identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    distinct = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].nunique()
    if (
        counts.empty
        or not counts.eq(SOURCE_BAR_COUNT).all()
        or not distinct.eq(SOURCE_BAR_COUNT).all()
        or not work["minute_code"].isin(c86.SOURCE_MINUTE_CODE_SET).all()
    ):
        raise Campaign089FeatureError(f"raw minute grid changed for {symbol}")
    continuous = work.loc[
        work["minute_code"].isin(c86.CONTINUOUS_MINUTE_CODE_SET),
        ["trade_date", "minute_code", "close", "amount"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"],
        categories=c86.CONTINUOUS_MINUTE_CODES,
        ordered=True,
    )
    continuous = continuous.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(counts.index).normalize()
    if len(continuous) != len(dates) * SELECTED_BAR_COUNT:
        raise Campaign089FeatureError(f"continuous minute grid changed for {symbol}")
    closes = (
        continuous["close"]
        .to_numpy(dtype=np.float64)
        .reshape(len(dates), SELECTED_BAR_COUNT)
    )
    selected_amounts = (
        continuous["amount"]
        .to_numpy(dtype=np.float64)
        .reshape(len(dates), SELECTED_BAR_COUNT)
    )
    destination_amounts = np.concatenate(
        (selected_amounts[:, 1:120], selected_amounts[:, 121:240]), axis=1
    )
    values, eligible, up_mass, down_mass, _up_center, _down_center = (
        compute_directional_amount_timing_spread(closes, destination_amounts)
    )
    source_valid = (
        np.isfinite(closes).all(axis=1)
        & (closes > 0.0).all(axis=1)
        & np.isfinite(destination_amounts).all(axis=1)
        & (destination_amounts >= 0.0).all(axis=1)
    )
    logged = np.full_like(closes, np.nan)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        logged[source_valid] = np.log(closes[source_valid])
    return_frame = np.concatenate(
        (np.diff(logged[:, :120], axis=1), np.diff(logged[:, 120:], axis=1)),
        axis=1,
    )
    return pd.DataFrame({"trade_date": dates, FACTOR_NAME: values}), {
        "source_rows": len(work),
        "source_sessions": len(dates),
        "valid_directional_timing_sessions": int(eligible.sum()),
        "invalid_selected_source_sessions": int((~source_valid).sum()),
        "nonpositive_up_mass_sessions": int(
            (source_valid & (~np.isfinite(up_mass) | (up_mass <= 0.0))).sum()
        ),
        "nonpositive_down_mass_sessions": int(
            (source_valid & (~np.isfinite(down_mass) | (down_mass <= 0.0))).sum()
        ),
        "zero_returns": int(((return_frame == 0.0) & source_valid[:, None]).sum()),
        "zero_destination_amounts": int(
            ((destination_amounts == 0.0) & source_valid[:, None]).sum()
        ),
    }


def attach_values(
    identity: pd.DataFrame, values: pd.DataFrame, *, symbol: str
) -> pd.DataFrame:
    if tuple(identity.columns) != IDENTITY_COLUMNS:
        raise Campaign089FeatureError(f"identity projection changed for {symbol}")
    base = identity.copy()
    base["trade_date"] = pd.to_datetime(
        base["trade_date"], errors="coerce"
    ).dt.normalize()
    base["symbol"] = base["symbol"].astype(str).str.upper()
    base["provider"] = base["provider"].astype(str).str.lower()
    if base.empty:
        base[FACTOR_NAME] = pd.Series(dtype="float64")
        return base
    if (
        base["trade_date"].isna().any()
        or base.duplicated(["trade_date", "symbol"]).any()
        or set(base["symbol"].unique()) != {symbol.upper()}
        or set(base["provider"].unique()) != {"tushare"}
        or values.empty
        or values.duplicated(["trade_date"]).any()
    ):
        raise Campaign089FeatureError(
            f"joint-clean/value identity changed for {symbol}"
        )
    out = base.merge(values, on="trade_date", how="left", validate="one_to_one")
    if out[FACTOR_NAME].isna().all() and not values[FACTOR_NAME].isna().all():
        raise Campaign089FeatureError(
            f"Campaign089 dates failed to attach for {symbol}"
        )
    if not out["trade_date"].isin(values["trade_date"]).all():
        raise Campaign089FeatureError(
            f"accepted session absent from source for {symbol}"
        )
    return out


def compact_stock_day_keys(trade_dates: pd.Series, symbols: pd.Series) -> np.ndarray:
    dates = pd.to_datetime(trade_dates, errors="coerce").dt.normalize()
    text = symbols.astype("string")
    exchange = text.str.slice(0, 2).map({"SH": 1, "SZ": 2, "BJ": 3})
    codes = pd.to_numeric(text.str.slice(2, 8), errors="coerce")
    if (
        dates.isna().any()
        or exchange.isna().any()
        or codes.isna().any()
        or not text.str.fullmatch(r"(SH|SZ|BJ)[0-9]{6}").all()
    ):
        raise Campaign089FeatureError("Campaign089 stock-day identity cannot compact")
    day_number = dates.to_numpy(dtype="datetime64[D]").astype(np.int64, copy=False)
    security = exchange.to_numpy(dtype=np.int64) * 1_000_000 + codes.to_numpy(
        dtype=np.int64
    )
    return day_number * 4_000_000 + security


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived/a_share/rich/tushare/minute_walkforward_campaign089_feature_library"
        / OUTPUT_RUN_ID
    )


def _load_implementation_freeze() -> dict[str, Any]:
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign089FeatureError("Campaign089 implementation freeze is absent")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign089_feature_implementation_freeze"
        and record.get("status")
        == "frozen_before_campaign089_minute_source_rows_or_candidate_values"
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (record.get("feature_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("candidate_source_rows_read_before_freeze") is False
        and record.get("candidate_values_computed_before_freeze") is False
        and record.get("comparison_values_read_before_freeze") is False
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and record.get("provider_request_issued_before_freeze") is False
    ):
        raise Campaign089FeatureError("Campaign089 implementation freeze changed")
    return record


def _load_attached(
    index: int, clean_item: dict[str, Any], raw_item: dict[str, Any]
) -> tuple[int, pd.DataFrame, dict[str, int]]:
    symbol = str(clean_item["symbol"]).upper()
    identity = pd.read_parquet(clean_item["path"], columns=list(IDENTITY_COLUMNS))
    raw_path = Path(str(raw_item["path"])).expanduser().resolve()
    if not raw_path.is_file() or pq.ParquetFile(raw_path).metadata.num_rows != int(
        raw_item["rows"]
    ):
        raise Campaign089FeatureError(f"raw partition changed: {raw_path}")
    raw = pd.read_parquet(raw_path, columns=list(RAW_COLUMNS))
    values, quality = extract_directional_amount_timing_spread(raw, symbol=symbol)
    attached = attach_values(identity, values, symbol=symbol)
    attached["_partition_index"] = index
    return index, attached, quality


def _dataset_material(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocol_sha256": manifest["protocol"]["sha256"],
        "implementation_freeze_sha256": manifest["implementation_freeze"]["sha256"],
        "raw_manifest_sha256": manifest["source"]["raw_manifest_sha256"],
        "joint_clean_manifest_sha256": manifest["source"][
            "joint_clean_manifest_sha256"
        ],
        "eligible_keys_sha256": manifest["eligible_universe"]["keys_sha256"],
        "factor_name": FACTOR_NAME,
        "factor_formula": FACTOR_FORMULA,
        "factor_eligible_rows": manifest["factor_eligible_rows"][FACTOR_NAME],
        "files": manifest["files"],
    }


def build_snapshot(
    *, data_root: Path, workers: int = 8, confirm_build: bool = False
) -> Path:
    if not confirm_build:
        raise Campaign089FeatureError("Campaign089 build requires --confirm-build")
    data_root = data_root.expanduser().resolve()
    if data_root != DEFAULT_DATA_ROOT.resolve():
        raise Campaign089FeatureError("Campaign089 data root changed")
    load_protocol()
    freeze = _load_implementation_freeze()
    raw_manifest, clean_manifest, _c74_freeze, _calendar = c86.c83.c74._require_inputs(
        data_root
    )
    raw_by_key = c86.c83.c74._raw_file_map(raw_manifest)
    clean_files = list(clean_manifest.get("files") or [])
    if not (
        len(clean_files) == EXPECTED_RAW_PARTITIONS
        and clean_manifest.get("rows") == EXPECTED_JOINT_CLEAN_ROWS
    ):
        raise Campaign089FeatureError("Campaign089 joint-clean source changed")
    eligible_keys = cache_v1.eligible_keys()
    root = output_root(data_root)
    if root.exists():
        raise Campaign089FeatureError("Campaign089 output already exists")
    root.parent.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(tempfile.mkdtemp(prefix=f".{root.name}.", dir=root.parent))
    by_year: dict[int, list[tuple[int, dict[str, Any]]]] = {}
    for index, item in enumerate(clean_files):
        by_year.setdefault(int(item["year"]), []).append((index, item))
    records: list[dict[str, Any]] = []
    total_eligible = 0
    totals = {
        "source_rows": 0,
        "source_sessions": 0,
        "valid_directional_timing_sessions": 0,
        "invalid_selected_source_sessions": 0,
        "nonpositive_up_mass_sessions": 0,
        "nonpositive_down_mass_sessions": 0,
        "zero_returns": 0,
        "zero_destination_amounts": 0,
    }
    try:
        for year in sorted(by_year):
            jobs: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
            for index, item in by_year[year]:
                raw_item = raw_by_key.get(
                    (str(item["symbol"]).upper(), int(item["year"]))
                )
                if raw_item is None:
                    raise Campaign089FeatureError("Campaign089 raw partition missing")
                jobs.append((index, item, raw_item))
            pieces: list[pd.DataFrame] = []
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max(1, workers)
            ) as pool:
                futures = [pool.submit(_load_attached, *job) for job in jobs]
                for future in concurrent.futures.as_completed(futures):
                    _index, attached, quality = future.result()
                    pieces.append(attached)
                    for key in totals:
                        totals[key] += int(quality[key])
            attached_year = pd.concat(pieces, ignore_index=True)
            candidate_keys = compact_stock_day_keys(
                attached_year["trade_date"], attached_year["symbol"]
            )
            candidate_values = pd.to_numeric(
                attached_year[FACTOR_NAME], errors="coerce"
            ).to_numpy(dtype=np.float64)
            order = np.argsort(candidate_keys, kind="stable")
            candidate_keys = candidate_keys[order]
            candidate_values = candidate_values[order]
            if len(np.unique(candidate_keys)) != len(candidate_keys):
                raise Campaign089FeatureError("Campaign089 candidate keys duplicated")
            days = eligible_keys // 4_000_000
            start_day = np.datetime64(f"{year}-01-01", "D").astype(np.int64)
            stop_day = np.datetime64(f"{year + 1}-01-01", "D").astype(np.int64)
            start = int(np.searchsorted(days, start_day, side="left"))
            stop = int(np.searchsorted(days, stop_day, side="left"))
            year_keys = eligible_keys[start:stop]
            positions = np.searchsorted(candidate_keys, year_keys)
            matched = positions < len(candidate_keys)
            matched[matched] &= candidate_keys[positions[matched]] == year_keys[matched]
            values = np.full(len(year_keys), np.nan, dtype=np.float64)
            values[matched] = candidate_values[positions[matched]]
            eligible = np.isfinite(values) & (values >= -1.0) & (values <= 1.0)
            values[~eligible] = np.nan
            out = pd.DataFrame(
                {
                    "stock_day_key": year_keys.astype(np.int64, copy=False),
                    FACTOR_NAME: values,
                    f"{FACTOR_NAME}_eligible": eligible,
                }
            ).loc[:, OUTPUT_COLUMNS]
            relative = Path("partitions") / f"{year}.parquet"
            destination = temporary_root / relative
            c85._atomic_parquet(out, destination)
            eligible_count = int(eligible.sum())
            records.append(
                {
                    "path": str(relative),
                    "year": year,
                    "rows": len(out),
                    "eligible_rows": eligible_count,
                    "sha256": _sha256(destination),
                    "frame_sha256": c85._frame_sha256(out),
                    "factor_canonical_value_sha256": cache_v1.canonical_column_sha256(
                        values
                    ),
                    "joint_clean_partitions_read": len(jobs),
                }
            )
            total_eligible += eligible_count
            print(
                f"Campaign089 built year={year} eligible_rows={eligible_count}",
                flush=True,
            )
        if not (
            len(records) == EXPECTED_PARTITIONS
            and sum(int(item["rows"]) for item in records) == EXPECTED_ROWS
            and len(np.unique(eligible_keys // 4_000_000)) == EXPECTED_SESSIONS
        ):
            raise Campaign089FeatureError("Campaign089 aggregate keys changed")
        manifest: dict[str, Any] = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign089_feature_snapshot",
            "status": "complete_no_return_candidate_snapshot",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "protocol": {
                "path": str(DEFAULT_PROTOCOL.resolve()),
                "sha256": PROTOCOL_SHA256,
            },
            "implementation_freeze": {
                "path": str(DEFAULT_IMPLEMENTATION_FREEZE.resolve()),
                "sha256": _sha256(DEFAULT_IMPLEMENTATION_FREEZE),
            },
            "feature_runner": {
                "path": str(Path(__file__).resolve()),
                "sha256": _sha256(Path(__file__).resolve()),
            },
            "source": {
                "raw_manifest_sha256": c86.c83.RAW_MANIFEST_SHA256,
                "joint_clean_manifest_sha256": c86.c83.CLEAN_MANIFEST_SHA256,
                "joint_clean_dataset_sha256": c86.c83.CLEAN_DATASET_SHA256,
                "raw_fields_read": list(RAW_COLUMNS),
                "joint_clean_identity_fields_read": list(IDENTITY_COLUMNS),
                "raw_partitions_read": len(clean_files),
                "joint_clean_rows": EXPECTED_JOINT_CLEAN_ROWS,
            },
            "eligible_universe": {
                "rows": EXPECTED_ROWS,
                "calendar_sessions": EXPECTED_SESSIONS,
                "keys_sha256": hashlib.sha256(
                    eligible_keys.astype("<i8", copy=False).tobytes()
                ).hexdigest(),
            },
            "factor_names": [FACTOR_NAME],
            "factor_directions": {FACTOR_NAME: "higher"},
            "factor_formulas": {FACTOR_NAME: FACTOR_FORMULA},
            "factor_ranges": {FACTOR_NAME: [-1.0, 1.0]},
            "rows": EXPECTED_ROWS,
            "partitions": EXPECTED_PARTITIONS,
            "calendar_sessions": EXPECTED_SESSIONS,
            "factor_eligible_rows": {FACTOR_NAME: total_eligible},
            "factor_missing_rows": {FACTOR_NAME: EXPECTED_ROWS - total_eligible},
            "quality": totals,
            "files": records,
            "comparison_values_read": False,
            "historical_daily_price_fields_read": [],
            "historical_forward_returns_read": False,
            "candidate49_historical_return_read": False,
            "candidate49_ledgers_changed": False,
            "provider_request_issued": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
            "implementation_freeze_status": freeze["status"],
        }
        manifest["dataset_sha256"] = _json_digest(_dataset_material(manifest))
        c85._atomic_json(manifest, temporary_root / "snapshot_manifest.json")
        os.replace(temporary_root, root)
        return root / "snapshot_manifest.json"
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise


def verify_snapshot_files(manifest_path: Path) -> dict[str, Any]:
    _load_implementation_freeze()
    path = manifest_path.expanduser().resolve()
    expected = output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
    if path != expected.resolve() or not path.is_file():
        raise Campaign089FeatureError("Campaign089 manifest path changed")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign089_feature_snapshot"
        and manifest.get("status") == "complete_no_return_candidate_snapshot"
        and (manifest.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (manifest.get("implementation_freeze") or {}).get("sha256")
        == _sha256(DEFAULT_IMPLEMENTATION_FREEZE)
        and (manifest.get("feature_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == {FACTOR_NAME: "higher"}
        and manifest.get("factor_ranges") == {FACTOR_NAME: [-1.0, 1.0]}
        and manifest.get("rows") == EXPECTED_ROWS
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and manifest.get("calendar_sessions") == EXPECTED_SESSIONS
        and manifest.get("comparison_values_read") is False
        and manifest.get("historical_daily_price_fields_read") == []
        and manifest.get("historical_forward_returns_read") is False
        and manifest.get("provider_request_issued") is False
        and manifest.get("dataset_sha256") == _json_digest(_dataset_material(manifest))
    ):
        raise Campaign089FeatureError("Campaign089 manifest semantics changed")
    rows = 0
    eligible_count = 0
    all_keys: list[np.ndarray] = []
    for record in manifest.get("files") or []:
        partition = path.parent / str(record["path"])
        if _sha256(partition) != record.get("sha256"):
            raise Campaign089FeatureError("Campaign089 partition bytes changed")
        frame = pd.read_parquet(partition, columns=list(OUTPUT_COLUMNS))
        if c85._frame_sha256(frame) != record.get("frame_sha256"):
            raise Campaign089FeatureError("Campaign089 partition frame changed")
        values = frame[FACTOR_NAME].to_numpy(dtype=np.float64)
        flags = frame[f"{FACTOR_NAME}_eligible"].astype(bool).to_numpy()
        finite = np.isfinite(values)
        if not (
            np.array_equal(flags, finite)
            and ((values[finite] >= -1.0) & (values[finite] <= 1.0)).all()
            and int(flags.sum()) == int(record["eligible_rows"])
            and cache_v1.canonical_column_sha256(values)
            == record.get("factor_canonical_value_sha256")
        ):
            raise Campaign089FeatureError("Campaign089 partition values changed")
        rows += len(frame)
        eligible_count += int(flags.sum())
        all_keys.append(frame["stock_day_key"].to_numpy(dtype=np.int64))
    keys = np.concatenate(all_keys)
    key_sha = hashlib.sha256(keys.astype("<i8", copy=False).tobytes()).hexdigest()
    if not (
        rows == EXPECTED_ROWS
        and eligible_count
        == (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
        and len(np.unique(keys)) == EXPECTED_ROWS
        and np.all(keys[1:] > keys[:-1])
        and key_sha == (manifest.get("eligible_universe") or {}).get("keys_sha256")
    ):
        raise Campaign089FeatureError("Campaign089 aggregate identity changed")
    return {
        "status": "verified",
        "dataset_sha256": manifest["dataset_sha256"],
        "partitions": len(manifest["files"]),
        "rows": rows,
        "eligible_rows": eligible_count,
        "comparison_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def status(data_root: Path = DEFAULT_DATA_ROOT) -> dict[str, Any]:
    load_protocol()
    path = output_root(data_root.expanduser().resolve()) / "snapshot_manifest.json"
    return {
        "status": "snapshot_present" if path.is_file() else "snapshot_absent_prebuild",
        "manifest_path": str(path),
        "source_rows_read_by_status": False,
        "candidate_values_computed_by_status": False,
        "comparison_values_read_by_status": False,
        "historical_daily_price_or_forward_return_values_read_by_status": False,
        "provider_request_issued_by_status": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    build.add_argument("--workers", type=int, default=8)
    build.add_argument("--confirm-build", action="store_true")
    inspect = sub.add_parser("status")
    inspect.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    verify = sub.add_parser("verify")
    verify.add_argument("--manifest", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "status":
        print(json.dumps(status(args.data_root), sort_keys=True))
        return 0
    if args.command == "build":
        print(
            build_snapshot(
                data_root=args.data_root,
                workers=args.workers,
                confirm_build=args.confirm_build,
            )
        )
        return 0
    manifest = args.manifest or (
        output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
    )
    print(json.dumps(verify_snapshot_files(manifest), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
