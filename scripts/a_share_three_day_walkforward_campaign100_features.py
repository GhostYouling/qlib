#!/usr/bin/env python3
"""Build Campaign100's frozen unchanged-close range-absorption snapshot."""

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

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign093_features as c93
from scripts import a_share_three_day_walkforward_campaign099_features as c99


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_100_no_return_preregistration.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_100_feature_implementation_freeze_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign100_features.py"
)

PROTOCOL_SHA256 = "0bd9dbe069895b8e7c82accbf9834fa6b90adbbd7673c5e42b914107903ddb15"
MECHANISM_AUDIT_SHA256 = (
    "be5d99cf55a37edb0458a96d1ac4d2cbf08323901cf7d1e33a9a2c0587d8ab76"
)
CURRENT_STATE_SHA256 = (
    "bf9ab5ff6481713742360675247bb9d3cb25865b1882887cfce72c7df9435092"
)
NUMERIC_POLICY_SHA256 = (
    "90df8d97e248f1293bb76dfdfdba2d16dfd0791aeb02a43067b98a9d5995851c"
)
C99_SNAPSHOT_MANIFEST = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign099_compact_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign099_compact_feature_library_v1/snapshot_manifest.json"
)
C99_SNAPSHOT_MANIFEST_SHA256 = (
    "a973f7d71a871e56294f50a0c39267006f9b859f1b9490599c89c51cbab5fe90"
)
C99_SNAPSHOT_DATASET_SHA256 = (
    "1ac5ddd9c59401a48876df69e409ba86b6fd71923c5be61936efb30a56c3de9b"
)

FACTOR_NAME = "intraday_unchanged_close_range_absorption_share_238p"
FACTOR_FORMULA = (
    "for each of 238 fixed within-half destination bars set "
    "h_j=log(high_j/low_j) and z_j=1[close_j equals close_j-1 exactly]; "
    "return sum(h_j*z_j)/sum(h_j)"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low", "close")
IDENTITY_COLUMNS = ("trade_date", "symbol", "provider")
OUTPUT_COLUMNS = (
    "stock_day_key",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
SELECTED_BAR_COUNT = 240
PAIR_COUNT = 238
ENDPOINT_TOLERANCE = 1e-12
FULL_DEFINITION_COUNT = 131
FULL_DEFINITION_ORDER_SHA256 = (
    "065077dfa5df9331906141f938204efedb3274e252d3b94c8fa1e9beebb5fc2e"
)
COMPARISON_COUNT = 128
COMPARISON_ORDER_SHA256 = (
    "12ebf65ee86e23e606875a9a78165f0410bfdb320bdc99d159097ec669583756"
)
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign100_feature_library_v1"
)

_engine = c93._generated
EXPECTED_RAW_PARTITIONS = int(_engine["EXPECTED_RAW_PARTITIONS"])
EXPECTED_JOINT_CLEAN_ROWS = int(_engine["EXPECTED_JOINT_CLEAN_ROWS"])
EXPECTED_ROWS = int(_engine["EXPECTED_ROWS"])
EXPECTED_SESSIONS = int(_engine["EXPECTED_SESSIONS"])
EXPECTED_PARTITIONS = int(_engine["EXPECTED_PARTITIONS"])


class Campaign100FeatureError(RuntimeError):
    """Fail closed when a frozen Campaign100 invariant changes."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(path: Path, expected_sha256: str, label: str) -> None:
    resolved = path.expanduser().resolve()
    if not resolved.is_file() or _sha256(resolved) != expected_sha256:
        raise Campaign100FeatureError(f"{label} changed: {resolved}")


def _order_digest(items: Iterable[dict[str, str]]) -> str:
    return c99._order_digest(items)


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = [dict(item) for item in c99.reconstruct_complete_definitions()]
    items.append({"name": c99.FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != FULL_DEFINITION_COUNT
        or _order_digest(items) != FULL_DEFINITION_ORDER_SHA256
        or items[-1]
        != {"name": c99.FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign100FeatureError("Campaign100 complete definition order changed")
    return items


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = [dict(item) for item in c99.reconstruct_comparisons()]
    items.append({"name": c99.FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != COMPARISON_COUNT
        or _order_digest(items) != COMPARISON_ORDER_SHA256
        or items[-1]
        != {"name": c99.FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign100FeatureError("Campaign100 numeric comparator order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    _require(path, PROTOCOL_SHA256, "Campaign100 protocol")
    _require(
        C99_SNAPSHOT_MANIFEST,
        C99_SNAPSHOT_MANIFEST_SHA256,
        "Campaign099 compact snapshot",
    )
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign100FeatureError("Campaign100 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    chain = spec.get("source_chain") or {}
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    support = gates.get("support_predicate_before_source_rows") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    previous = json.loads(C99_SNAPSHOT_MANIFEST.read_text(encoding="utf-8"))
    previous_chain = chain.get("campaign099_terminal_numeric_comparator") or {}
    previous_snapshot = previous_chain.get("snapshot_manifest") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign100_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign100_minute_source_candidate_comparator_daily_price_or_return_values"
        and (chain.get("mechanism_overlap_and_support_predicate_audit") or {}).get(
            "sha256"
        )
        == MECHANISM_AUDIT_SHA256
        and (chain.get("authoritative_iteration_state") or {}).get("sha256")
        == CURRENT_STATE_SHA256
        and (chain.get("numeric_comparator_policy_v52") or {}).get("sha256")
        == NUMERIC_POLICY_SHA256
        and previous_snapshot.get("sha256") == C99_SNAPSHOT_MANIFEST_SHA256
        and previous_snapshot.get("dataset_sha256") == C99_SNAPSHOT_DATASET_SHA256
        and previous.get("dataset_sha256") == C99_SNAPSHOT_DATASET_SHA256
        and previous.get("factor_eligible_rows", {}).get(c99.FACTOR_NAME)
        == 1_328_449
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and tuple(candidate.get("minute_source_projection") or ()) == RAW_COLUMNS
        and tuple(candidate.get("stock_day_identity_projection") or ())
        == IDENTITY_COLUMNS
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("within_half_transition_count") == PAIR_COUNT
        and candidate.get("endpoint_tolerance") == ENDPOINT_TOLERANCE
        and candidate.get("valid_range")
        == {
            "lower": 0,
            "lower_inclusive": True,
            "upper": 1,
            "upper_inclusive": True,
        }
        and candidate.get("exact_support_predicate_gate_passed_before_source_rows")
        is True
        and support.get("required") is True
        and support.get("known_terminal_coverage_failure_inventory_reviewed") is True
        and support.get(
            "candidate_identical_to_or_provably_narrower_than_known_failure"
        )
        is False
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and uniqueness.get("complete_definition_count") == FULL_DEFINITION_COUNT
        and uniqueness.get("complete_definition_order_sha256")
        == FULL_DEFINITION_ORDER_SHA256
        and uniqueness.get("numeric_comparator_count") == COMPARISON_COUNT
        and uniqueness.get("numeric_comparator_order_sha256")
        == COMPARISON_ORDER_SHA256
        and uniqueness.get("all_128_numeric_comparators_must_pass") is True
        and uniqueness.get("candidate_specific_comparator_drop_allowed") is False
        and uniqueness.get("insufficient_pairwise_overlap_fails_closed") is True
        and len(reconstruct_complete_definitions()) == FULL_DEFINITION_COUNT
        and len(reconstruct_comparisons()) == COMPARISON_COUNT
        and finite.get("trial_id")
        == "wf100_intraday_unchanged_close_range_absorption_share_238p_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("expected_trial_count") == 1
        and finite.get("purge_local_signal_sessions_before_each_partition_boundary")
        == 3
        and finite.get("t_plus_1_and_t_plus_3_must_remain_inside_partition")
        is True
        and boundary.get("candidate_source_rows_read_before_freeze") is False
        and boundary.get("candidate_values_read_before_freeze") is False
        and boundary.get("comparison_values_read_before_coverage_pass") is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign100FeatureError("Campaign100 protocol semantics changed")
    return spec


def compute_unchanged_close_range_absorption_share(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    """Return score, eligibility, absorbed/total mass, equality and ranges."""

    high = np.asarray(highs, dtype=np.float64)
    low = np.asarray(lows, dtype=np.float64)
    close = np.asarray(closes, dtype=np.float64)
    if high.ndim != 2 or high.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign100FeatureError("Campaign100 requires an n-by-240 high array")
    if low.shape != high.shape or close.shape != high.shape:
        raise Campaign100FeatureError("Campaign100 requires matching n-by-240 HLC arrays")
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
    previous_closes = np.concatenate((close[:, :119], close[:, 120:239]), axis=1)
    destination_closes = np.concatenate((close[:, 1:120], close[:, 121:240]), axis=1)
    destination_highs = np.concatenate((high[:, 1:120], high[:, 121:240]), axis=1)
    destination_lows = np.concatenate((low[:, 1:120], low[:, 121:240]), axis=1)
    unchanged = destination_closes == previous_closes
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        destination_ranges = np.log(destination_highs / destination_lows)
        total_range_mass = np.sum(destination_ranges, axis=1, dtype=np.float64)
        absorbed_range_mass = np.sum(
            np.where(unchanged, destination_ranges, 0.0),
            axis=1,
            dtype=np.float64,
        )
        raw_score = absorbed_range_mass / total_range_mass
    support = (
        source_valid
        & np.isfinite(destination_ranges).all(axis=1)
        & (destination_ranges >= 0.0).all(axis=1)
        & np.isfinite(total_range_mass)
        & (total_range_mass > 0.0)
        & np.isfinite(absorbed_range_mass)
        & (absorbed_range_mass >= 0.0)
        & (absorbed_range_mass <= total_range_mass)
        & np.isfinite(raw_score)
    )
    result = np.full(len(high), np.nan, dtype=np.float64)
    candidate = raw_score[support].copy()
    candidate[np.abs(candidate) <= ENDPOINT_TOLERANCE] = 0.0
    candidate[np.abs(candidate - 1.0) <= ENDPOINT_TOLERANCE] = 1.0
    valid_score = np.isfinite(candidate) & (candidate >= 0.0) & (candidate <= 1.0)
    positions = np.flatnonzero(support)
    result[positions[valid_score]] = candidate[valid_score]
    eligible = np.isfinite(result) & (result >= 0.0) & (result <= 1.0)
    result[~eligible] = np.nan
    return (
        result,
        eligible,
        absorbed_range_mass,
        total_range_mass,
        unchanged,
        destination_ranges,
    )


def extract_unchanged_close_range_absorption_share(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign100FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    empty = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            FACTOR_NAME: pd.Series(dtype="float64"),
        }
    )
    quality = {
        "source_rows": 0,
        "source_sessions": 0,
        "valid_range_absorption_sessions": 0,
        "invalid_selected_source_sessions": 0,
        "nonpositive_destination_range_mass_sessions": 0,
        "invalid_ordered_hlc_sessions": 0,
        "unchanged_close_pairs": 0,
        "changed_close_pairs": 0,
        "zero_destination_range_pairs": 0,
        "unchanged_positive_range_pairs": 0,
        "endpoint_canonicalized_sessions": 0,
    }
    if raw.empty:
        return empty, quality
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    for column in ("high", "low", "close"):
        work[column] = pd.to_numeric(work[column], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign100FeatureError(f"raw minute identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    distinct = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].nunique()
    c86 = _engine["c86"]
    if (
        counts.empty
        or not counts.eq(_engine["SOURCE_BAR_COUNT"]).all()
        or not distinct.eq(_engine["SOURCE_BAR_COUNT"]).all()
        or not work["minute_code"].isin(c86.SOURCE_MINUTE_CODE_SET).all()
    ):
        raise Campaign100FeatureError(f"raw minute grid changed for {symbol}")
    continuous = work.loc[
        work["minute_code"].isin(c86.CONTINUOUS_MINUTE_CODE_SET),
        ["trade_date", "minute_code", "high", "low", "close"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"],
        categories=c86.CONTINUOUS_MINUTE_CODES,
        ordered=True,
    )
    continuous = continuous.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(counts.index).normalize()
    if len(continuous) != len(dates) * SELECTED_BAR_COUNT:
        raise Campaign100FeatureError(f"continuous minute grid changed for {symbol}")
    arrays = {
        column: continuous[column]
        .to_numpy(dtype=np.float64)
        .reshape(len(dates), SELECTED_BAR_COUNT)
        for column in ("high", "low", "close")
    }
    (
        values,
        eligible,
        absorbed_mass,
        total_mass,
        unchanged,
        destination_ranges,
    ) = compute_unchanged_close_range_absorption_share(
        arrays["high"], arrays["low"], arrays["close"]
    )
    finite_positive = np.logical_and.reduce(
        [
            np.isfinite(array).all(axis=1) & (array > 0.0).all(axis=1)
            for array in arrays.values()
        ]
    )
    ordered = (
        finite_positive
        & (arrays["low"] <= arrays["close"]).all(axis=1)
        & (arrays["close"] <= arrays["high"]).all(axis=1)
    )
    return pd.DataFrame({"trade_date": dates, FACTOR_NAME: values}), {
        "source_rows": len(work),
        "source_sessions": len(dates),
        "valid_range_absorption_sessions": int(eligible.sum()),
        "invalid_selected_source_sessions": int((~finite_positive).sum()),
        "nonpositive_destination_range_mass_sessions": int(
            (ordered & (~np.isfinite(total_mass) | (total_mass <= 0.0))).sum()
        ),
        "invalid_ordered_hlc_sessions": int((finite_positive & ~ordered).sum()),
        "unchanged_close_pairs": int((unchanged & ordered[:, None]).sum()),
        "changed_close_pairs": int((~unchanged & ordered[:, None]).sum()),
        "zero_destination_range_pairs": int(
            ((destination_ranges == 0.0) & ordered[:, None]).sum()
        ),
        "unchanged_positive_range_pairs": int(
            (unchanged & (destination_ranges > 0.0) & ordered[:, None]).sum()
        ),
        "endpoint_canonicalized_sessions": int(
            (eligible & ((values == 0.0) | (values == 1.0))).sum()
        ),
    }


def _attach_values(
    identity: pd.DataFrame, values: pd.DataFrame, *, symbol: str
) -> pd.DataFrame:
    if tuple(identity.columns) != IDENTITY_COLUMNS:
        raise Campaign100FeatureError(f"identity projection changed for {symbol}")
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
        raise Campaign100FeatureError(
            f"joint-clean/value identity changed for {symbol}"
        )
    out = base.merge(values, on="trade_date", how="left", validate="one_to_one")
    if out[FACTOR_NAME].isna().all() and not values[FACTOR_NAME].isna().all():
        raise Campaign100FeatureError(f"Campaign100 dates failed to attach for {symbol}")
    if not out["trade_date"].isin(values["trade_date"]).all():
        raise Campaign100FeatureError(f"accepted session absent from source for {symbol}")
    return out


def _load_attached(
    index: int, clean_item: dict[str, Any], raw_item: dict[str, Any]
) -> tuple[int, pd.DataFrame, dict[str, int]]:
    symbol = str(clean_item["symbol"]).upper()
    identity = pd.read_parquet(clean_item["path"], columns=list(IDENTITY_COLUMNS))
    raw_path = Path(str(raw_item["path"])).expanduser().resolve()
    if not raw_path.is_file() or pq.ParquetFile(raw_path).metadata.num_rows != int(
        raw_item["rows"]
    ):
        raise Campaign100FeatureError(f"raw partition changed: {raw_path}")
    raw = pd.read_parquet(raw_path, columns=list(RAW_COLUMNS))
    values, quality = extract_unchanged_close_range_absorption_share(
        raw, symbol=symbol
    )
    attached = _attach_values(identity, values, symbol=symbol)
    attached["_partition_index"] = index
    return index, attached, quality


def _load_implementation_freeze() -> dict[str, Any]:
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign100FeatureError("Campaign100 implementation freeze is absent")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign100_feature_implementation_freeze"
        and record.get("status")
        == "frozen_before_campaign100_minute_source_rows_or_candidate_values"
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
        raise Campaign100FeatureError("Campaign100 implementation freeze changed")
    return record


def output_root(data_root: Path) -> Path:
    return (
        data_root.expanduser().resolve()
        / "derived/a_share/rich/tushare/minute_walkforward_campaign100_feature_library"
        / OUTPUT_RUN_ID
    )


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


def _json_digest(value: Any) -> str:
    return _engine["_json_digest"](value)


def build_snapshot(
    *, data_root: Path, workers: int = 8, confirm_build: bool = False
) -> Path:
    if not confirm_build:
        raise Campaign100FeatureError("Campaign100 build requires --confirm-build")
    data_root = data_root.expanduser().resolve()
    if data_root != DEFAULT_DATA_ROOT.resolve():
        raise Campaign100FeatureError("Campaign100 data root changed")
    load_protocol()
    freeze = _load_implementation_freeze()
    c86 = _engine["c86"]
    raw_manifest, clean_manifest, _c74_freeze, _calendar = (
        c86.c83.c74._require_inputs(data_root)
    )
    raw_by_key = c86.c83.c74._raw_file_map(raw_manifest)
    clean_files = list(clean_manifest.get("files") or [])
    if not (
        len(clean_files) == EXPECTED_RAW_PARTITIONS
        and clean_manifest.get("rows") == EXPECTED_JOINT_CLEAN_ROWS
    ):
        raise Campaign100FeatureError("Campaign100 joint-clean source changed")
    cache_v1 = _engine["cache_v1"]
    eligible_keys = cache_v1.eligible_keys()
    root = output_root(data_root)
    if root.exists():
        raise Campaign100FeatureError("Campaign100 output already exists")
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
        "valid_range_absorption_sessions": 0,
        "invalid_selected_source_sessions": 0,
        "nonpositive_destination_range_mass_sessions": 0,
        "invalid_ordered_hlc_sessions": 0,
        "unchanged_close_pairs": 0,
        "changed_close_pairs": 0,
        "zero_destination_range_pairs": 0,
        "unchanged_positive_range_pairs": 0,
        "endpoint_canonicalized_sessions": 0,
    }
    c85 = _engine["c85"]
    compact_stock_day_keys = _engine["compact_stock_day_keys"]
    try:
        for year in sorted(by_year):
            jobs: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
            for index, item in by_year[year]:
                raw_item = raw_by_key.get(
                    (str(item["symbol"]).upper(), int(item["year"]))
                )
                if raw_item is None:
                    raise Campaign100FeatureError("Campaign100 raw partition missing")
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
                raise Campaign100FeatureError("Campaign100 candidate keys duplicated")
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
                f"Campaign100 built year={year} eligible_rows={eligible_count}",
                flush=True,
            )
        if not (
            len(records) == EXPECTED_PARTITIONS
            and sum(int(item["rows"]) for item in records) == EXPECTED_ROWS
            and len(np.unique(eligible_keys // 4_000_000)) == EXPECTED_SESSIONS
        ):
            raise Campaign100FeatureError("Campaign100 aggregate keys changed")
        manifest: dict[str, Any] = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign100_feature_snapshot",
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
    _load_implementation_freeze()
    path = manifest_path.expanduser().resolve()
    expected = output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
    if path != expected.resolve() or not path.is_file():
        raise Campaign100FeatureError("Campaign100 manifest path changed")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign100_feature_snapshot"
        and manifest.get("status") == "complete_no_return_candidate_snapshot"
        and (manifest.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (manifest.get("implementation_freeze") or {}).get("sha256")
        == _sha256(DEFAULT_IMPLEMENTATION_FREEZE)
        and (manifest.get("feature_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == {FACTOR_NAME: "higher"}
        and manifest.get("factor_ranges") == {FACTOR_NAME: [0.0, 1.0]}
        and manifest.get("rows") == EXPECTED_ROWS
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and manifest.get("calendar_sessions") == EXPECTED_SESSIONS
        and manifest.get("comparison_values_read") is False
        and manifest.get("historical_daily_price_fields_read") == []
        and manifest.get("historical_forward_returns_read") is False
        and manifest.get("candidate49_historical_return_read") is False
        and manifest.get("candidate49_ledgers_changed") is False
        and manifest.get("provider_request_issued") is False
        and manifest.get("dataset_sha256") == _json_digest(_dataset_material(manifest))
    ):
        raise Campaign100FeatureError("Campaign100 manifest semantics changed")
    rows = 0
    eligible_count = 0
    all_keys: list[np.ndarray] = []
    cache_v1 = _engine["cache_v1"]
    c85 = _engine["c85"]
    for record in manifest.get("files") or []:
        partition = path.parent / str(record["path"])
        if _sha256(partition) != record.get("sha256"):
            raise Campaign100FeatureError("Campaign100 partition bytes changed")
        frame = pd.read_parquet(partition, columns=list(OUTPUT_COLUMNS))
        if c85._frame_sha256(frame) != record.get("frame_sha256"):
            raise Campaign100FeatureError("Campaign100 partition frame changed")
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
            raise Campaign100FeatureError("Campaign100 partition values changed")
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
        raise Campaign100FeatureError("Campaign100 aggregate identity changed")
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
    subparsers = parser.add_subparsers(dest="command", required=True)
    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    build_parser.add_argument("--workers", type=int, default=8)
    build_parser.add_argument("--confirm-build", action="store_true")
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--manifest", type=Path)
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
