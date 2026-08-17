#!/usr/bin/env python3
"""Build Campaign109's frozen intrabar body-magnitude persistence snapshot."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign105_features.py"
BASE_RUNNER_SHA256 = "cf151f6f8af55bc219f9ed06512eb138d833352316a958b4a9b1dac05079e4ba"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _file_sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign105 feature builder changed")


FACTOR_NAME = "intraday_intrabar_body_magnitude_serial_persistence_238p"
FACTOR_FORMULA = (
    "population Pearson correlation between adjacent abs(log(close/open)) "
    "values over 119 morning plus 119 afternoon within-half pairs"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "open", "close")
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign109_feature_library_v1"
)
PROTOCOL_SHA256 = "e05004a5f6b93f2e5275d39f4e7855d73070038bbe5d25254cebb09d1a236015"
MECHANISM_AUDIT_SHA256 = (
    "cce214f9cc67bc4245c14adc981ec077ed14e7f406db594fdb9c8428d92479cf"
)
NUMERIC_POLICY_SHA256 = (
    "36ec8d963d733e5d6b44df7a3654b8e40444468e470b44b11cc19f6989a527b8"
)
NUMERIC_COMPARATOR_COUNT = 132
NUMERIC_COMPARATOR_ORDER_SHA256 = (
    "7ed69afd1408e84dcc856583344166ffc9bcbb0add1aed63163b1d12a1be9a25"
)
COMPLETE_DEFINITION_COUNT = 138
COMPLETE_DEFINITION_ORDER_SHA256 = (
    "6b0deb2e6d3f610e9fb18cc31636b92ac8a6f644a08b3e461c3f301966738b68"
)
PAIR_COUNT = 238
ENDPOINT_TOLERANCE = 1e-12


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign105", "Campaign109"),
    ("campaign105", "campaign109"),
    ("campaign_105", "campaign_109"),
    ("intraday_active_trading_bar_share_240m", FACTOR_NAME),
    ("active_trading_bar_share", "intrabar_body_magnitude_serial_persistence"),
    ("extract_active_trading_bar_share", "extract_body_magnitude_serial_persistence"),
    ("attach_activity_values", "attach_body_persistence_values"),
    ("valid_activity_sessions", "valid_body_persistence_sessions"),
    ("invalid_numeric_sessions", "invalid_open_close_sessions"),
    ("one_sided_zero_sessions", "degenerate_body_variance_sessions"),
    ("active_bars", "nonzero_body_bars"),
    ("joint_zero_bars", "zero_body_bars"),
    ("activity_rule", "body_persistence_rule"),
    ("minimum_active_bar_count", "fixed_pair_count"),
    ("positive_total_activity_required", "positive_body_variance_required"),
    ("activity_magnitude_used", "absolute_body_magnitude_used"),
    (
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "volume", "amount")',
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "open", "close")',
    ),
):
    _source = _source.replace(_old, _new)
_source = _source.replace("{FACTOR_NAME: [0.0, 1.0]}", "{FACTOR_NAME: [-1.0, 1.0]}")
_source = _source.replace(
    "values.ge(0.0) & values.le(1.0)",
    "values.ge(-1.0) & values.le(1.0)",
)
_source = _source.replace('"fixed_pair_count": 0', '"fixed_pair_count": 238')
_source = _source.replace(
    '"positive_body_variance_required": False',
    '"positive_body_variance_required": True',
)
_source = _source.replace(
    '"absolute_body_magnitude_used": False',
    '"absolute_body_magnitude_used": True',
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign109_features_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)

Campaign109FeatureError = _generated["Campaign109FeatureError"]

from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign108_features_v2 as c108,
)


DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_109_no_return_preregistration_20260808.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_109_no_return_implementation_freeze_20260808.json"
)
FEATURE_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign109_features.py"
)
AUDIT_RUNNER_PATH = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign109_no_return_audit.py"
)
AUDIT_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign109_no_return_audit.py"
)


def _order_digest(items: Iterable[dict[str, str]]) -> str:
    return _generated["_json_digest"](
        [[item["name"], item["score_direction"]] for item in items]
    )


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = [dict(item) for item in c108.reconstruct_comparisons()]
    if (
        len(items) != NUMERIC_COMPARATOR_COUNT
        or _order_digest(items) != NUMERIC_COMPARATOR_ORDER_SHA256
    ):
        raise Campaign109FeatureError("Campaign109 numeric comparison order changed")
    return items


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = [dict(item) for item in c108.reconstruct_complete_definitions()]
    items.append({"name": c108.FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != COMPLETE_DEFINITION_COUNT
        or _order_digest(items) != COMPLETE_DEFINITION_ORDER_SHA256
        or items[-1] != {"name": c108.FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign109FeatureError("Campaign109 complete definition order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    target = path.expanduser().resolve()
    _generated["_require"](target, PROTOCOL_SHA256, "protocol")
    report = _generated["bindings"].validate_record(
        target, data_root=_generated["DEFAULT_DATA_ROOT"]
    )
    if report.get("all_bindings_passed") is not True:
        raise Campaign109FeatureError("Campaign109 protocol binding failed")
    spec = json.loads(target.read_text(encoding="utf-8"))
    inputs = spec.get("authoritative_inputs") or {}
    policy = inputs.get("numeric_policy_v69") or {}
    candidate = spec.get("candidate") or {}
    grid = candidate.get("source_grid") or {}
    semantics = candidate.get("body_and_correlation_semantics") or {}
    snapshot = spec.get("source_snapshot_contract") or {}
    comparisons = spec.get("comparison_contract") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    gates = list(spec.get("ordered_no_return_gates") or [])
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign109_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign109_minute_source_candidate_comparator_daily_price_or_return_values"
        and policy.get("sha256") == NUMERIC_POLICY_SHA256
        and policy.get("complete_definition_count") == COMPLETE_DEFINITION_COUNT
        and policy.get("complete_definition_order_sha256")
        == COMPLETE_DEFINITION_ORDER_SHA256
        and policy.get("numeric_comparator_count") == NUMERIC_COMPARATOR_COUNT
        and policy.get("numeric_comparator_order_sha256")
        == NUMERIC_COMPARATOR_ORDER_SHA256
        and (inputs.get("mechanism_support_audit") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and tuple(candidate.get("source_projection") or ()) == RAW_COLUMNS
        and candidate.get("valid_range") == [-1.0, 1.0]
        and grid.get("accepted_rows_required") == _generated["SOURCE_BAR_COUNT"]
        and grid.get("selected_rows_for_formula") == _generated["SELECTED_BAR_COUNT"]
        and grid.get("selected_adjacent_pairs") == PAIR_COUNT
        and grid.get("morning_pairs") == 119
        and grid.get("afternoon_pairs") == 119
        and grid.get("standalone_09_30_preserved_but_not_loaded_for_formula")
        is True
        and grid.get("lunch_transition_excluded") is True
        and semantics.get(
            "all_selected_open_and_close_values_finite_and_strictly_positive"
        )
        is True
        and semantics.get("body_magnitude") == "abs(log(close/open))"
        and semantics.get("exact_zero_bodies_retained_in_fixed_support") is True
        and semantics.get("population_pearson_correlation") is True
        and semantics.get(
            "positive_population_variance_required_in_both_fixed_vectors"
        )
        is True
        and semantics.get("pair_drop_or_zero_bridge_allowed") is False
        and snapshot.get("data_root") == str(_generated["DEFAULT_DATA_ROOT"])
        and snapshot.get("joint_clean_manifest_sha256")
        == _generated["CLEAN_MANIFEST_SHA256"]
        and snapshot.get("joint_clean_dataset_sha256")
        == _generated["CLEAN_DATASET_SHA256"]
        and snapshot.get("expected_partitions") == _generated["EXPECTED_PARTITIONS"]
        and snapshot.get("expected_rows") == _generated["EXPECTED_ROWS"]
        and snapshot.get("output_run_id") == OUTPUT_RUN_ID
        and comparisons.get("numeric_comparator_count") == NUMERIC_COMPARATOR_COUNT
        and comparisons.get("numeric_comparator_order_sha256")
        == NUMERIC_COMPARATOR_ORDER_SHA256
        and comparisons.get(
            "complete_v69_semantic_definition_count_reviewed_before_values"
        )
        == COMPLETE_DEFINITION_COUNT
        and [item.get("gate") for item in gates] == [1, 2, 3]
        and finite.get("trial_count") == 1
        and finite.get("factor") == FACTOR_NAME
        and finite.get("direction") == "higher"
        and boundary.get("campaign109_source_rows_read_before_freeze") is False
        and boundary.get("campaign109_candidate_values_computed_or_read_before_freeze")
        is False
        and boundary.get("campaign109_comparison_values_read_before_freeze") is False
        and boundary.get("historical_daily_price_fields_read_before_freeze") == []
        and boundary.get("historical_forward_returns_read_before_freeze") is False
        and boundary.get("provider_request_issued") is False
        and len(reconstruct_comparisons()) == NUMERIC_COMPARATOR_COUNT
        and len(reconstruct_complete_definitions()) == COMPLETE_DEFINITION_COUNT
    ):
        raise Campaign109FeatureError("Campaign109 protocol semantics changed")
    return spec


def compute_body_magnitude_serial_persistence(
    opens: np.ndarray, closes: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    open_ = np.asarray(opens, dtype=np.float64)
    close = np.asarray(closes, dtype=np.float64)
    if open_.ndim != 2 or open_.shape[1] != _generated["SELECTED_BAR_COUNT"]:
        raise Campaign109FeatureError("Campaign109 requires an n-by-240 open array")
    if close.shape != open_.shape:
        raise Campaign109FeatureError("Campaign109 open/close shapes changed")
    source_valid = (
        np.isfinite(open_).all(axis=1)
        & np.isfinite(close).all(axis=1)
        & (open_ > 0.0).all(axis=1)
        & (close > 0.0).all(axis=1)
    )
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        bodies = np.abs(np.log(close / open_))
    lag = np.concatenate((bodies[:, :119], bodies[:, 120:239]), axis=1)
    lead = np.concatenate((bodies[:, 1:120], bodies[:, 121:240]), axis=1)
    lag_centered = lag - lag.mean(axis=1, keepdims=True)
    lead_centered = lead - lead.mean(axis=1, keepdims=True)
    lag_variance = np.mean(lag_centered * lag_centered, axis=1)
    lead_variance = np.mean(lead_centered * lead_centered, axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        raw_score = np.mean(lag_centered * lead_centered, axis=1) / np.sqrt(
            lag_variance * lead_variance
        )
    support = (
        source_valid
        & np.isfinite(bodies).all(axis=1)
        & np.isfinite(lag_variance)
        & np.isfinite(lead_variance)
        & (lag_variance > 0.0)
        & (lead_variance > 0.0)
        & np.isfinite(raw_score)
    )
    result = np.full(len(open_), np.nan, dtype=np.float64)
    values = raw_score[support].copy()
    values[np.abs(values - 1.0) <= ENDPOINT_TOLERANCE] = 1.0
    values[np.abs(values + 1.0) <= ENDPOINT_TOLERANCE] = -1.0
    valid_score = np.isfinite(values) & (values >= -1.0) & (values <= 1.0)
    positions = np.flatnonzero(support)
    result[positions[valid_score]] = values[valid_score]
    eligible = np.isfinite(result) & (result >= -1.0) & (result <= 1.0)
    result[~eligible] = np.nan
    return result, eligible, bodies, lag_variance, lead_variance


def extract_body_magnitude_serial_persistence(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign109FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    empty = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "intrabar_body_magnitude_serial_persistence": pd.Series(dtype="float64"),
        }
    )
    quality = {
        "source_rows": 0,
        "source_sessions": 0,
        "valid_body_persistence_sessions": 0,
        "invalid_open_close_sessions": 0,
        "degenerate_body_variance_sessions": 0,
        "nonzero_body_bars": 0,
        "zero_body_bars": 0,
    }
    if raw.empty:
        return empty, quality
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    for column in ("open", "close"):
        work[column] = pd.to_numeric(work[column], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign109FeatureError(f"raw minute identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    distinct = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].nunique()
    if (
        counts.empty
        or not counts.eq(_generated["SOURCE_BAR_COUNT"]).all()
        or not distinct.eq(_generated["SOURCE_BAR_COUNT"]).all()
        or not work["minute_code"].isin(_generated["SOURCE_MINUTE_CODE_SET"]).all()
    ):
        raise Campaign109FeatureError(f"raw minute grid changed for {symbol}")
    selected = work.loc[
        work["minute_code"].isin(_generated["CONTINUOUS_MINUTE_CODE_SET"]),
        ["trade_date", "minute_code", "open", "close"],
    ].copy()
    selected["minute_code"] = pd.Categorical(
        selected["minute_code"],
        categories=_generated["CONTINUOUS_MINUTE_CODES"],
        ordered=True,
    )
    selected = selected.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(counts.index).normalize()
    if len(selected) != len(dates) * _generated["SELECTED_BAR_COUNT"]:
        raise Campaign109FeatureError(f"continuous minute grid changed for {symbol}")
    open_ = selected["open"].to_numpy(dtype=np.float64).reshape(len(dates), 240)
    close = selected["close"].to_numpy(dtype=np.float64).reshape(len(dates), 240)
    values, eligible, bodies, lag_variance, lead_variance = (
        compute_body_magnitude_serial_persistence(open_, close)
    )
    source_valid = (
        np.isfinite(open_).all(axis=1)
        & np.isfinite(close).all(axis=1)
        & (open_ > 0.0).all(axis=1)
        & (close > 0.0).all(axis=1)
    )
    degenerate = source_valid & (
        ~np.isfinite(lag_variance)
        | ~np.isfinite(lead_variance)
        | (lag_variance <= 0.0)
        | (lead_variance <= 0.0)
    )
    return pd.DataFrame(
        {
            "trade_date": dates,
            "intrabar_body_magnitude_serial_persistence": values,
        }
    ), {
        "source_rows": int(len(work)),
        "source_sessions": int(len(dates)),
        "valid_body_persistence_sessions": int(eligible.sum()),
        "invalid_open_close_sessions": int((~source_valid).sum()),
        "degenerate_body_variance_sessions": int(degenerate.sum()),
        "nonzero_body_bars": int(((bodies > 0.0) & source_valid[:, None]).sum()),
        "zero_body_bars": int(((bodies == 0.0) & source_valid[:, None]).sum()),
    }


def validate_value_semantics(frame: pd.DataFrame) -> tuple[int, int]:
    expected = (
        "trade_date",
        "symbol",
        "provider",
        FACTOR_NAME,
        f"{FACTOR_NAME}_eligible",
    )
    if tuple(frame.columns) != expected:
        raise Campaign109FeatureError("Campaign109 output columns changed")
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"].astype(bool)
    if (
        values[eligible].isna().any()
        or ((values[eligible] < -1.0) | (values[eligible] > 1.0)).any()
        or values[~eligible].notna().any()
    ):
        raise Campaign109FeatureError("Campaign109 value semantics changed")
    return int(len(frame)), int(eligible.sum())


for _name, _value in {
    "FACTOR_NAME": FACTOR_NAME,
    "FACTOR_FORMULA": FACTOR_FORMULA,
    "RAW_COLUMNS": RAW_COLUMNS,
    "OUTPUT_RUN_ID": OUTPUT_RUN_ID,
    "DEFAULT_PROTOCOL": DEFAULT_PROTOCOL,
    "DEFAULT_IMPLEMENTATION_FREEZE": DEFAULT_IMPLEMENTATION_FREEZE,
    "FEATURE_TEST_PATH": FEATURE_TEST_PATH,
    "AUDIT_RUNNER_PATH": AUDIT_RUNNER_PATH,
    "AUDIT_TEST_PATH": AUDIT_TEST_PATH,
    "PROTOCOL_SHA256": PROTOCOL_SHA256,
    "MECHANISM_AUDIT_SHA256": MECHANISM_AUDIT_SHA256,
    "NUMERIC_POLICY_SHA256": NUMERIC_POLICY_SHA256,
    "NUMERIC_COMPARATOR_COUNT": NUMERIC_COMPARATOR_COUNT,
    "NUMERIC_COMPARATOR_ORDER_SHA256": NUMERIC_COMPARATOR_ORDER_SHA256,
    "COMPLETE_DEFINITION_COUNT": COMPLETE_DEFINITION_COUNT,
    "COMPLETE_DEFINITION_ORDER_SHA256": COMPLETE_DEFINITION_ORDER_SHA256,
    "OUTPUT_COLUMNS": (
        "trade_date",
        "symbol",
        "provider",
        FACTOR_NAME,
        f"{FACTOR_NAME}_eligible",
    ),
    "load_protocol": load_protocol,
    "reconstruct_comparisons": reconstruct_comparisons,
    "reconstruct_complete_definitions": reconstruct_complete_definitions,
    "compute_body_magnitude_serial_persistence": compute_body_magnitude_serial_persistence,
    "extract_body_magnitude_serial_persistence": extract_body_magnitude_serial_persistence,
    "validate_value_semantics": validate_value_semantics,
}.items():
    _generated[_name] = _value


DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
OUTPUT_COLUMNS = _generated["OUTPUT_COLUMNS"]
EXPECTED_ROWS = _generated["EXPECTED_ROWS"]
EXPECTED_PARTITIONS = _generated["EXPECTED_PARTITIONS"]
CLEAN_MANIFEST_SHA256 = _generated["CLEAN_MANIFEST_SHA256"]
CLEAN_DATASET_SHA256 = _generated["CLEAN_DATASET_SHA256"]
SOURCE_BAR_COUNT = _generated["SOURCE_BAR_COUNT"]
SELECTED_BAR_COUNT = _generated["SELECTED_BAR_COUNT"]
CONTINUOUS_MINUTE_CODES = _generated["CONTINUOUS_MINUTE_CODES"]
CONTINUOUS_MINUTE_CODE_SET = _generated["CONTINUOUS_MINUTE_CODE_SET"]
SOURCE_MINUTE_CODE_SET = _generated["SOURCE_MINUTE_CODE_SET"]
IDENTITY_COLUMNS = _generated["IDENTITY_COLUMNS"]
bindings = _generated["bindings"]
source = _generated["source"]
attach_body_persistence_values = _generated["attach_body_persistence_values"]
finalize_feature_frame = _generated["finalize_feature_frame"]
empty_output_frame = _generated["empty_output_frame"]
output_root = _generated["output_root"]
build_snapshot = _generated["build_snapshot"]
verify_snapshot_files = _generated["verify_snapshot_files"]
_validate_implementation_freeze = _generated["_validate_implementation_freeze"]
_sha256 = _generated["_sha256"]
status = _generated["status"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
