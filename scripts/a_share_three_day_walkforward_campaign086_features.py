#!/usr/bin/env python3
"""Build Campaign086's frozen intrabar close-location persistence snapshot."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from scripts import a_share_three_day_compact_comparator_cache as cache_v1
from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign083_features as c83
from scripts import a_share_three_day_walkforward_campaign085_features as c85

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_086_no_return_preregistration.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_086_feature_implementation_freeze_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign086_features.py"
)

PROTOCOL_SHA256 = "033cd34013770b5b19ccb8579100c7ab920946de22b3936bc34a0898f4d2acb3"
MECHANISM_AUDIT_SHA256 = (
    "874faeadca0fb0ba4b6e94fbaf9ad61c380914f8dc4a0f076417d76fb283f116"
)
CURRENT_STATE_SHA256 = (
    "99487c88232df6e0fedbd6207c20a6f25bab8bb6e8f66842f2599bbeba2c3024"
)
NUMERIC_POLICY_SHA256 = (
    "47d582150f3cca9c00f919e397600b388d65505e1f97d62017a693520d2828e1"
)
CACHE_PUBLICATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_compact_comparator_cache_v4_publication_binding_20260806.json"
)
CACHE_PUBLICATION_BINDING_SHA256 = (
    "244f70b88be0396f7473c6664835cbb3cdad9135b6692b77c74018b1d53c925b"
)
CACHE_MANIFEST_PATH = (
    DEFAULT_DATA_ROOT
    / "derived/a_share/rich/tushare/compact_comparator_cache/"
    "campaign067_terminal_numeric98_v4/snapshot_manifest.json"
)
CACHE_MANIFEST_SHA256 = (
    "3d81068f07ac61fe4cd04bd1a893e58759c06d88213263135fec5244e309b57b"
)
CACHE_DATASET_SHA256 = (
    "4a56dac48c14b667b6ee431519266f27bb8ff7cc25c51d8dce3bbc7aebe0376f"
)
C85_SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_085_feature_snapshot_binding_20260806.json"
)
C85_SNAPSHOT_BINDING_SHA256 = (
    "ce70c107d654b1d6151fde87bd5f177ee458cb2db825080cf1c6206df249ba4f"
)
C85_SNAPSHOT_MANIFEST = c85.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
C85_SNAPSHOT_MANIFEST_SHA256 = (
    "fb8ea4bdb2b2f783a8c1d4e020f1dcdfca1697c779c732e50233fe7b040b4d28"
)
C85_SNAPSHOT_DATASET_SHA256 = (
    "368f7cb96c15186cd511ccd4120e89b577141aa9687df8b39f9dd17320db8fb9"
)

FACTOR_NAME = "intraday_intrabar_close_location_serial_persistence_238p"
FACTOR_FORMULA = (
    "for positive-range selected bars x=(log(close)-log(low))/"
    "(log(high)-log(low)); pool within-half adjacent pairs; require at least "
    "120 pairs and positive population variances; return (1+population_rho)/2"
)
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_walkforward_"
    "campaign086_feature_library_v1"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low", "close")
IDENTITY_COLUMNS = c83.IDENTITY_COLUMNS
CONTINUOUS_MINUTE_CODES = c83.CONTINUOUS_MINUTE_CODES
CONTINUOUS_MINUTE_CODE_SET = c83.CONTINUOUS_MINUTE_CODE_SET
SOURCE_MINUTE_CODE_SET = c83.SOURCE_MINUTE_CODE_SET
SOURCE_BAR_COUNT = c83.SOURCE_BAR_COUNT
SELECTED_BAR_COUNT = c83.SELECTED_BAR_COUNT
HALF_SESSION_BAR_COUNT = 120
WITHIN_HALF_OPPORTUNITY_COUNT = 119
POOLED_OPPORTUNITY_COUNT = 238
MINIMUM_INFORMATIVE_PAIR_COUNT = 120
ENDPOINT_TOLERANCE = 1e-12
OUTPUT_COLUMNS = ("stock_day_key", FACTOR_NAME, f"{FACTOR_NAME}_eligible")
EXPECTED_ROWS = 1_331_759
EXPECTED_PARTITIONS = 7
EXPECTED_SESSIONS = 1_632
EXPECTED_RAW_PARTITIONS = 33_015
EXPECTED_JOINT_CLEAN_ROWS = 7_724_498
FULL_DEFINITION_COUNT = 117
FULL_DEFINITION_ORDER_SHA256 = (
    "462cd7b3aa1d7cd909e35b050025cf21094954b1f76925833f46f65c4d1317f8"
)
COMPARISON_COUNT = 115
COMPARISON_ORDER_SHA256 = (
    "f22759b26333f8e1fdb5a8ca942afa96aca88b544311e608fd9ffbd5105c80ab"
)


class Campaign086FeatureError(RuntimeError):
    """Fail-closed Campaign086 feature error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _comparison_order_digest(items: Iterable[dict[str, Any]]) -> str:
    return _json_digest(
        [[str(item["name"]), str(item["score_direction"])] for item in items]
    )


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign086FeatureError(f"Campaign086 {label} changed: {path}")


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = c85.reconstruct_comparisons()
    items.append({"name": c85.FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != COMPARISON_COUNT
        or _comparison_order_digest(items) != COMPARISON_ORDER_SHA256
        or items[-1] != {"name": c85.FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign086FeatureError("Campaign086 numeric comparison order changed")
    return items


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = c85.reconstruct_complete_definitions()
    items.append({"name": c85.FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != FULL_DEFINITION_COUNT
        or _comparison_order_digest(items) != FULL_DEFINITION_ORDER_SHA256
    ):
        raise Campaign086FeatureError("Campaign086 complete definition order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    _require(path, PROTOCOL_SHA256, "protocol")
    _require(
        CACHE_PUBLICATION_BINDING,
        CACHE_PUBLICATION_BINDING_SHA256,
        "compact-cache publication binding",
    )
    _require(CACHE_MANIFEST_PATH, CACHE_MANIFEST_SHA256, "compact-cache manifest")
    _require(C85_SNAPSHOT_BINDING, C85_SNAPSHOT_BINDING_SHA256, "Campaign085 binding")
    _require(C85_SNAPSHOT_MANIFEST, C85_SNAPSHOT_MANIFEST_SHA256, "Campaign085 manifest")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign086FeatureError("Campaign086 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    chain = spec.get("source_chain") or {}
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    unique = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    previous = json.loads(C85_SNAPSHOT_MANIFEST.read_text(encoding="utf-8"))
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign086_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign086_minute_source_candidate_comparison_daily_price_or_return_values"
        and (chain.get("mechanism_overlap_audit_v2") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and (chain.get("authoritative_iteration_state") or {}).get("sha256")
        == CURRENT_STATE_SHA256
        and (chain.get("numeric_comparator_policy_v24") or {}).get("sha256")
        == NUMERIC_POLICY_SHA256
        and (chain.get("compact_comparator_cache_v4_manifest") or {}).get(
            "dataset_sha256"
        )
        == CACHE_DATASET_SHA256
        and (chain.get("campaign085_terminal_numeric_comparator") or {}).get(
            "dataset_sha256"
        )
        == C85_SNAPSHOT_DATASET_SHA256
        and previous.get("dataset_sha256") == C85_SNAPSHOT_DATASET_SHA256
        and previous.get("factor_names") == [c85.FACTOR_NAME]
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and tuple(candidate.get("minute_source_projection") or ()) == RAW_COLUMNS
        and tuple(candidate.get("stock_day_identity_projection") or ())
        == IDENTITY_COLUMNS
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("half_session_bar_count") == HALF_SESSION_BAR_COUNT
        and candidate.get("within_half_opportunity_count")
        == WITHIN_HALF_OPPORTUNITY_COUNT
        and candidate.get("pooled_opportunity_count") == POOLED_OPPORTUNITY_COUNT
        and candidate.get("minimum_informative_pair_count")
        == MINIMUM_INFORMATIVE_PAIR_COUNT
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
        and unique.get("all_115_numeric_comparators_must_pass") is True
        and len(reconstruct_comparisons()) == COMPARISON_COUNT
        and len(reconstruct_complete_definitions()) == FULL_DEFINITION_COUNT
        and finite.get("trial_id")
        == "wf086_intraday_intrabar_close_location_serial_persistence_238p_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1]
        and finite.get("expected_trial_count") == 1
        and boundary.get("comparison_values_read_before_coverage_pass") is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign086FeatureError("Campaign086 protocol semantics changed")
    return spec


def compute_serial_persistence(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return mapped persistence, eligibility, and retained-pair counts by session."""

    high = np.asarray(highs, dtype=np.float64)
    low = np.asarray(lows, dtype=np.float64)
    close = np.asarray(closes, dtype=np.float64)
    expected_shape = (len(high), SELECTED_BAR_COUNT) if high.ndim == 2 else None
    if (
        expected_shape is None
        or high.shape != expected_shape
        or low.shape != expected_shape
        or close.shape != expected_shape
    ):
        raise Campaign086FeatureError("serial persistence requires aligned n-by-240 arrays")
    source_valid = (
        np.isfinite(high).all(axis=1)
        & np.isfinite(low).all(axis=1)
        & np.isfinite(close).all(axis=1)
        & (high > 0.0).all(axis=1)
        & (low > 0.0).all(axis=1)
        & (close > 0.0).all(axis=1)
        & (low <= close).all(axis=1)
        & (close <= high).all(axis=1)
    )
    positive_range = high > low
    state = np.full(high.shape, np.nan, dtype=np.float64)
    computable = positive_range & source_valid[:, None]
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        log_high = np.log(high)
        log_low = np.log(low)
        log_close = np.log(close)
        state[computable] = (
            (log_close - log_low)[computable]
            / (log_high - log_low)[computable]
        )
    state_valid = np.isfinite(state) & (state >= 0.0) & (state <= 1.0)
    lag = np.concatenate((state[:, :119], state[:, 120:239]), axis=1)
    lead = np.concatenate((state[:, 1:120], state[:, 121:240]), axis=1)
    pair_valid = np.concatenate(
        (
            state_valid[:, :119] & state_valid[:, 1:120],
            state_valid[:, 120:239] & state_valid[:, 121:240],
        ),
        axis=1,
    )
    pair_count = pair_valid.sum(axis=1).astype(np.int64)
    count = pair_count.astype(np.float64)
    first_pair = np.argmax(pair_valid, axis=1)
    row_index = np.arange(len(high))
    anchor_lag = lag[row_index, first_pair]
    anchor_lead = lead[row_index, first_pair]
    anchor_lag = np.where(pair_count > 0, anchor_lag, 0.0)
    anchor_lead = np.where(pair_count > 0, anchor_lead, 0.0)
    offset_lag = np.where(pair_valid, lag - anchor_lag[:, None], 0.0)
    offset_lead = np.where(pair_valid, lead - anchor_lead[:, None], 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        mean_offset_lag = offset_lag.sum(axis=1) / count
        mean_offset_lead = offset_lead.sum(axis=1) / count
        centered_lag = np.where(
            pair_valid, offset_lag - mean_offset_lag[:, None], 0.0
        )
        centered_lead = np.where(
            pair_valid, offset_lead - mean_offset_lead[:, None], 0.0
        )
        var_lag = (centered_lag * centered_lag).sum(axis=1) / count
        var_lead = (centered_lead * centered_lead).sum(axis=1) / count
        covariance = (centered_lag * centered_lead).sum(axis=1) / count
        rho = covariance / np.sqrt(var_lag * var_lead)
    eligible_base = (
        source_valid
        & (pair_count >= MINIMUM_INFORMATIVE_PAIR_COUNT)
        & (var_lag > 0.0)
        & (var_lead > 0.0)
        & np.isfinite(rho)
    )
    rho[np.abs(rho - 1.0) <= ENDPOINT_TOLERANCE] = 1.0
    rho[np.abs(rho + 1.0) <= ENDPOINT_TOLERANCE] = -1.0
    rho_valid = eligible_base & (rho >= -1.0) & (rho <= 1.0)
    result = np.full(len(high), np.nan, dtype=np.float64)
    result[rho_valid] = (1.0 + rho[rho_valid]) / 2.0
    eligible = rho_valid & np.isfinite(result) & (result >= 0.0) & (result <= 1.0)
    result[~eligible] = np.nan
    return result, eligible, pair_count


def extract_serial_persistence(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign086FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    empty = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            FACTOR_NAME: pd.Series(dtype="float64"),
        }
    )
    if raw.empty:
        return empty, {
            "source_rows": 0,
            "source_sessions": 0,
            "valid_serial_persistence_sessions": 0,
            "invalid_selected_source_sessions": 0,
            "insufficient_pair_sessions": 0,
            "zero_range_selected_bars": 0,
            "retained_informative_pairs": 0,
        }
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    for name in ("high", "low", "close"):
        work[name] = pd.to_numeric(work[name], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign086FeatureError(f"raw minute identity changed for {symbol}")
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
        or not work["minute_code"].isin(SOURCE_MINUTE_CODE_SET).all()
    ):
        raise Campaign086FeatureError(f"raw minute grid changed for {symbol}")
    continuous = work.loc[
        work["minute_code"].isin(CONTINUOUS_MINUTE_CODE_SET),
        ["trade_date", "minute_code", "high", "low", "close"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"], categories=CONTINUOUS_MINUTE_CODES, ordered=True
    )
    continuous = continuous.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(counts.index).normalize()
    if len(continuous) != len(dates) * SELECTED_BAR_COUNT:
        raise Campaign086FeatureError(f"continuous minute grid changed for {symbol}")
    arrays = {
        name: continuous[name]
        .to_numpy(dtype=np.float64)
        .reshape(len(dates), SELECTED_BAR_COUNT)
        for name in ("high", "low", "close")
    }
    values, eligible, pairs = compute_serial_persistence(
        arrays["high"], arrays["low"], arrays["close"]
    )
    selected_source_valid = (
        np.isfinite(arrays["high"]).all(axis=1)
        & np.isfinite(arrays["low"]).all(axis=1)
        & np.isfinite(arrays["close"]).all(axis=1)
        & (arrays["high"] > 0.0).all(axis=1)
        & (arrays["low"] > 0.0).all(axis=1)
        & (arrays["close"] > 0.0).all(axis=1)
        & (arrays["low"] <= arrays["close"]).all(axis=1)
        & (arrays["close"] <= arrays["high"]).all(axis=1)
    )
    return pd.DataFrame({"trade_date": dates, FACTOR_NAME: values}), {
        "source_rows": len(work),
        "source_sessions": len(dates),
        "valid_serial_persistence_sessions": int(eligible.sum()),
        "invalid_selected_source_sessions": int((~selected_source_valid).sum()),
        "insufficient_pair_sessions": int(
            (selected_source_valid & (pairs < MINIMUM_INFORMATIVE_PAIR_COUNT)).sum()
        ),
        "zero_range_selected_bars": int(
            ((arrays["high"] == arrays["low"]) & selected_source_valid[:, None]).sum()
        ),
        "retained_informative_pairs": int(pairs.sum()),
    }


def attach_values(
    identity: pd.DataFrame, values: pd.DataFrame, *, symbol: str
) -> pd.DataFrame:
    if tuple(identity.columns) != IDENTITY_COLUMNS:
        raise Campaign086FeatureError(f"identity projection changed for {symbol}")
    base = identity.copy()
    base["trade_date"] = pd.to_datetime(
        base["trade_date"], errors="coerce"
    ).dt.normalize()
    base["symbol"] = base["symbol"].astype(str).str.upper()
    base["provider"] = base["provider"].astype(str).str.lower()
    if (
        base.empty
        or base["trade_date"].isna().any()
        or base.duplicated(["trade_date", "symbol"]).any()
        or set(base["symbol"].unique()) != {symbol.upper()}
        or set(base["provider"].unique()) != {"tushare"}
        or values.empty
        or values.duplicated(["trade_date"]).any()
    ):
        raise Campaign086FeatureError(f"joint-clean/value identity changed for {symbol}")
    out = base.merge(values, on="trade_date", how="left", validate="one_to_one")
    if out[FACTOR_NAME].isna().all() and not values[FACTOR_NAME].isna().all():
        raise Campaign086FeatureError(f"Campaign086 dates failed to attach for {symbol}")
    if not out["trade_date"].isin(values["trade_date"]).all():
        raise Campaign086FeatureError(f"accepted session absent from raw source for {symbol}")
    return out


def compact_stock_day_keys(
    trade_dates: pd.Series, symbols: pd.Series
) -> np.ndarray:
    dates = pd.to_datetime(trade_dates, errors="coerce").dt.normalize()
    text = symbols.astype("string").str.upper()
    suffix = text.str.slice(7, 9)
    exchange = suffix.map({"SH": 1, "SZ": 2, "BJ": 3})
    codes = pd.to_numeric(text.str.slice(0, 6), errors="coerce")
    if (
        dates.isna().any()
        or exchange.isna().any()
        or codes.isna().any()
        or not text.str.fullmatch(r"[0-9]{6}\.(SH|SZ|BJ)").all()
    ):
        raise Campaign086FeatureError("Campaign086 stock-day identity cannot compact")
    day_number = dates.to_numpy(dtype="datetime64[D]").astype(np.int64, copy=False)
    security = exchange.to_numpy(dtype=np.int64) * 1_000_000 + codes.to_numpy(
        dtype=np.int64
    )
    return day_number * 4_000_000 + security


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived/a_share/rich/tushare/minute_walkforward_campaign086_feature_library"
        / OUTPUT_RUN_ID
    )


def _load_implementation_freeze() -> dict[str, Any]:
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign086FeatureError("Campaign086 implementation freeze is absent")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign086_feature_implementation_freeze"
        and record.get("status")
        == "frozen_before_campaign086_minute_source_rows_or_candidate_values"
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
        raise Campaign086FeatureError("Campaign086 implementation freeze changed")
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
        raise Campaign086FeatureError(f"raw partition changed: {raw_path}")
    raw = pd.read_parquet(raw_path, columns=list(RAW_COLUMNS))
    values, quality = extract_serial_persistence(raw, symbol=symbol)
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
        raise Campaign086FeatureError("Campaign086 build requires --confirm-build")
    data_root = data_root.expanduser().resolve()
    if data_root != DEFAULT_DATA_ROOT.resolve():
        raise Campaign086FeatureError("Campaign086 data root changed")
    load_protocol()
    freeze = _load_implementation_freeze()
    raw_manifest, clean_manifest, _c74_freeze, _calendar = c83.c74._require_inputs(
        data_root
    )
    raw_by_key = c83.c74._raw_file_map(raw_manifest)
    clean_files = list(clean_manifest.get("files") or [])
    if not (
        len(clean_files) == EXPECTED_RAW_PARTITIONS
        and clean_manifest.get("rows") == EXPECTED_JOINT_CLEAN_ROWS
    ):
        raise Campaign086FeatureError("Campaign086 joint-clean source changed")
    eligible_keys = cache_v1.eligible_keys()
    root = output_root(data_root)
    if root.exists():
        raise Campaign086FeatureError("Campaign086 output already exists")
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
        "valid_serial_persistence_sessions": 0,
        "invalid_selected_source_sessions": 0,
        "insufficient_pair_sessions": 0,
        "zero_range_selected_bars": 0,
        "retained_informative_pairs": 0,
    }
    try:
        for year in sorted(by_year):
            jobs: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
            for index, item in by_year[year]:
                raw_item = raw_by_key.get(
                    (str(item["symbol"]).upper(), int(item["year"]))
                )
                if raw_item is None:
                    raise Campaign086FeatureError("Campaign086 raw partition missing")
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
                raise Campaign086FeatureError("Campaign086 candidate keys duplicated")
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
            eligible = np.isfinite(values) & (values >= 0.0) & (values <= 1.0)
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
                f"Campaign086 built year={year} eligible_rows={eligible_count}",
                flush=True,
            )
        if not (
            len(records) == EXPECTED_PARTITIONS
            and sum(int(item["rows"]) for item in records) == EXPECTED_ROWS
            and len(np.unique(eligible_keys // 4_000_000)) == EXPECTED_SESSIONS
        ):
            raise Campaign086FeatureError("Campaign086 aggregate keys changed")
        manifest: dict[str, Any] = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign086_feature_snapshot",
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
                "raw_manifest_sha256": c83.RAW_MANIFEST_SHA256,
                "joint_clean_manifest_sha256": c83.CLEAN_MANIFEST_SHA256,
                "joint_clean_dataset_sha256": c83.CLEAN_DATASET_SHA256,
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
            "factor_ranges": {FACTOR_NAME: [0.0, 1.0]},
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
    manifest_path = manifest_path.expanduser().resolve()
    expected = output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
    if manifest_path != expected.resolve() or not manifest_path.is_file():
        raise Campaign086FeatureError("Campaign086 manifest path changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign086_feature_snapshot"
        and manifest.get("status") == "complete_no_return_candidate_snapshot"
        and (manifest.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (manifest.get("feature_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == {FACTOR_NAME: "higher"}
        and manifest.get("rows") == EXPECTED_ROWS
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and manifest.get("calendar_sessions") == EXPECTED_SESSIONS
        and manifest.get("comparison_values_read") is False
        and manifest.get("historical_daily_price_fields_read") == []
        and manifest.get("historical_forward_returns_read") is False
        and manifest.get("provider_request_issued") is False
        and manifest.get("dataset_sha256") == _json_digest(_dataset_material(manifest))
    ):
        raise Campaign086FeatureError("Campaign086 manifest semantics changed")
    rows = 0
    eligible_count = 0
    all_keys: list[np.ndarray] = []
    for record in manifest.get("files") or []:
        path = manifest_path.parent / str(record["path"])
        if _sha256(path) != record.get("sha256"):
            raise Campaign086FeatureError("Campaign086 partition bytes changed")
        frame = pd.read_parquet(path, columns=list(OUTPUT_COLUMNS))
        if c85._frame_sha256(frame) != record.get("frame_sha256"):
            raise Campaign086FeatureError("Campaign086 partition frame changed")
        values = frame[FACTOR_NAME].to_numpy(dtype=np.float64)
        flags = frame[f"{FACTOR_NAME}_eligible"].astype(bool).to_numpy()
        finite = np.isfinite(values)
        if not (
            np.array_equal(flags, finite)
            and ((values[finite] >= 0.0) & (values[finite] <= 1.0)).all()
            and int(flags.sum()) == int(record["eligible_rows"])
            and cache_v1.canonical_column_sha256(values)
            == record.get("factor_canonical_value_sha256")
        ):
            raise Campaign086FeatureError("Campaign086 partition values changed")
        rows += len(frame)
        eligible_count += int(flags.sum())
        all_keys.append(frame["stock_day_key"].to_numpy(dtype=np.int64))
    keys = np.concatenate(all_keys)
    if not (
        rows == EXPECTED_ROWS
        and eligible_count
        == (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
        and len(np.unique(keys)) == EXPECTED_ROWS
        and np.all(keys[1:] > keys[:-1])
        and hashlib.sha256(keys.astype("<i8", copy=False).tobytes()).hexdigest()
        == (manifest.get("eligible_universe") or {}).get("keys_sha256")
    ):
        raise Campaign086FeatureError("Campaign086 aggregate verification changed")
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
    manifest_path = output_root(data_root.expanduser().resolve()) / "snapshot_manifest.json"
    return {
        "status": "snapshot_present" if manifest_path.is_file() else "snapshot_absent_pre_build",
        "manifest_path": str(manifest_path),
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
        path = build_snapshot(
            data_root=args.data_root,
            workers=args.workers,
            confirm_build=args.confirm_build,
        )
        print(path)
        return 0
    manifest = args.manifest or (
        output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
    )
    print(json.dumps(verify_snapshot_files(manifest), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
