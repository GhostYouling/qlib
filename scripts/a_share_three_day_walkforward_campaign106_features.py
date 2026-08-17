#!/usr/bin/env python3
"""Build Campaign106's frozen 240-bar nonzero-range occupancy snapshot.

Only ``datetime,symbol,provider,high,low`` is projected from the immutable
minute source.  The builder does not read comparator values, daily prices,
forward returns, Candidate49 history, or any provider endpoint.
"""

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


FACTOR_NAME = "intraday_nonzero_range_bar_share_240m"
FACTOR_FORMULA = (
    "on exactly 240 bars at 09:31-11:30 and 13:01-15:00, require finite "
    "strictly positive high and low with low<=high; count bars with high>low "
    "and divide by 240; high==low is a valid non-varying bar"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign106_feature_library_v1"
)
PROTOCOL_SHA256 = "933b1f0bea9d092e67ba688d6270983e75e9002f2948f5e01f363d50cc4f2670"
MECHANISM_AUDIT_SHA256 = (
    "185ef069986578db40ff99dc87fb4fe9b7e8676b918d86357a02d1f7e7305e09"
)
NUMERIC_POLICY_SHA256 = (
    "2ec29422ce2938c22307095879acfd60397f03c0c70355d68466fd4179ec4ce8"
)
NUMERIC_COMPARATOR_COUNT = 132
NUMERIC_COMPARATOR_ORDER_SHA256 = (
    "7ed69afd1408e84dcc856583344166ffc9bcbb0add1aed63163b1d12a1be9a25"
)
COMPLETE_DEFINITION_COUNT = 135
COMPLETE_DEFINITION_ORDER_SHA256 = (
    "f77f069f07f05bca7b3d478d0e411945a27f6ecf9e8437c02f73900975eb89b3"
)


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign105", "Campaign106"),
    ("campaign105", "campaign106"),
    ("campaign_105", "campaign_106"),
    ("intraday_active_trading_bar_share_240m", FACTOR_NAME),
    ("active_trading_bar_share", "nonzero_range_bar_share"),
    ("valid_activity_sessions", "valid_range_occupancy_sessions"),
    ("one_sided_zero_sessions", "invalid_ordered_range_sessions"),
    ("active_bars", "nonzero_range_bars"),
    ("joint_zero_bars", "zero_range_bars"),
    ("activity_rule", "range_occupancy_rule"),
    ("minimum_active_bar_count", "minimum_nonzero_range_bar_count"),
    ("positive_total_activity_required", "positive_total_range_required"),
    ("activity_magnitude_used", "range_magnitude_used"),
    (
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "volume", "amount")',
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")',
    ),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign106_features_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)

Campaign106FeatureError = _generated["Campaign106FeatureError"]

from scripts import a_share_three_day_walkforward_campaign100_features as inventory  # noqa: E402
from scripts import a_share_three_day_walkforward_campaign101_features as c101  # noqa: E402
from scripts import a_share_three_day_walkforward_campaign103 as c103_record  # noqa: E402
from scripts import a_share_three_day_walkforward_campaign105_features as c105  # noqa: E402


def _order_digest(items: Iterable[dict[str, str]]) -> str:
    payload = [[item["name"], item["score_direction"]] for item in items]
    return _generated["_json_digest"](payload)


def reconstruct_comparisons() -> list[dict[str, str]]:
    """Rebuild the exact v63 numeric order without reading factor values."""

    items = [dict(item) for item in c105.reconstruct_comparisons()]
    items.append({"name": c105.FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != NUMERIC_COMPARATOR_COUNT
        or _order_digest(items) != NUMERIC_COMPARATOR_ORDER_SHA256
        or items[-1] != {"name": c105.FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign106FeatureError("Campaign106 numeric comparison order changed")
    return items


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    """Rebuild all v63 semantic definitions, including terminated definitions."""

    items = [dict(item) for item in inventory.reconstruct_complete_definitions()]
    items.extend(
        [
            {"name": inventory.FACTOR_NAME, "score_direction": "higher"},
            {"name": c101.FACTOR_NAME, "score_direction": "higher"},
            {"name": c103_record.ADMITTED_FACTOR, "score_direction": "higher"},
            {"name": c105.FACTOR_NAME, "score_direction": "higher"},
        ]
    )
    if (
        len(items) != COMPLETE_DEFINITION_COUNT
        or _order_digest(items) != COMPLETE_DEFINITION_ORDER_SHA256
        or items[-1] != {"name": c105.FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign106FeatureError("Campaign106 complete definition order changed")
    return items


def load_protocol(path: Path | None = None) -> dict[str, Any]:
    """Validate the exact pre-value protocol without reading any value rows."""

    target = _generated["DEFAULT_PROTOCOL"] if path is None else path
    target = target.expanduser().resolve()
    _generated["_require"](target, PROTOCOL_SHA256, "protocol")
    report = _generated["bindings"].validate_record(
        target, data_root=_generated["DEFAULT_DATA_ROOT"]
    )
    if report.get("all_bindings_passed") is not True:
        raise Campaign106FeatureError("Campaign106 protocol binding failed")
    spec = json.loads(target.read_text(encoding="utf-8"))
    inputs = spec.get("authoritative_inputs") or {}
    policy = inputs.get("numeric_policy_v63") or {}
    candidate = spec.get("candidate") or {}
    grid = candidate.get("source_grid") or {}
    semantics = candidate.get("range_occupancy_semantics") or {}
    snapshot = spec.get("source_snapshot_contract") or {}
    comparisons = spec.get("comparison_contract") or {}
    boundary = spec.get("research_boundary") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    gates = list(spec.get("ordered_no_return_gates") or [])
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign106_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign106_minute_source_candidate_comparator_daily_price_or_return_values"
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
        and grid.get("accepted_rows_required") == _generated["SOURCE_BAR_COUNT"]
        and grid.get("selected_rows") == _generated["SELECTED_BAR_COUNT"]
        and grid.get("standalone_09_30_preserved_but_not_loaded_for_formula") is True
        and semantics.get("finite_strictly_positive_high_and_low_required") is True
        and semantics.get("low_not_above_high_required") is True
        and semantics.get("zero_range") == "valid non-varying bar"
        and semantics.get("positive_range") == "varying bar"
        and semantics.get("minimum_nonzero_range_bar_count") == 0
        and semantics.get("positive_total_range_required") is False
        and semantics.get("range_magnitude_used") is False
        and semantics.get("clock_order_used_after_exact_grid_validation") is False
        and snapshot.get("data_root") == str(_generated["DEFAULT_DATA_ROOT"])
        and snapshot.get("joint_clean_manifest_sha256")
        == _generated["CLEAN_MANIFEST_SHA256"]
        and snapshot.get("joint_clean_dataset_sha256")
        == _generated["CLEAN_DATASET_SHA256"]
        and snapshot.get("expected_partitions") == _generated["EXPECTED_PARTITIONS"]
        and snapshot.get("expected_rows") == _generated["EXPECTED_ROWS"]
        and snapshot.get("output_run_id") == OUTPUT_RUN_ID
        and comparisons.get("complete_v63_semantic_definition_count_reviewed_before_values")
        == COMPLETE_DEFINITION_COUNT
        and comparisons.get("numeric_comparator_count") == NUMERIC_COMPARATOR_COUNT
        and comparisons.get("numeric_comparator_order_sha256")
        == NUMERIC_COMPARATOR_ORDER_SHA256
        and len(reconstruct_comparisons()) == NUMERIC_COMPARATOR_COUNT
        and len(reconstruct_complete_definitions()) == COMPLETE_DEFINITION_COUNT
        and [item.get("gate") for item in gates] == [1, 2, 3]
        and finite.get("trial_count") == 1
        and finite.get("trial_id")
        == "wf106_intraday_nonzero_range_bar_share_240m_single_higher"
        and finite.get("factor") == FACTOR_NAME
        and finite.get("direction") == "higher"
        and boundary.get("campaign106_source_rows_read_before_freeze") is False
        and boundary.get("campaign106_candidate_values_computed_or_read_before_freeze")
        is False
        and boundary.get("campaign106_comparison_values_read_before_freeze") is False
        and boundary.get("historical_daily_price_fields_read_before_freeze") == []
        and boundary.get("historical_forward_returns_read_before_freeze") is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign106FeatureError("Campaign106 protocol semantics changed")
    return spec


def extract_nonzero_range_bar_share(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Validate exact grids and count high>low bars; range magnitude is unused."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign106FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    empty = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "nonzero_range_bar_share": pd.Series(dtype="float64"),
        }
    )
    quality = {
        "source_rows": 0,
        "source_sessions": 0,
        "valid_range_occupancy_sessions": 0,
        "invalid_numeric_sessions": 0,
        "invalid_ordered_range_sessions": 0,
        "nonzero_range_bars": 0,
        "zero_range_bars": 0,
    }
    if raw.empty:
        return empty, quality
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["high"] = pd.to_numeric(work["high"], errors="coerce")
    work["low"] = pd.to_numeric(work["low"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign106FeatureError(f"raw minute identity changed for {symbol}")
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
        raise Campaign106FeatureError(f"raw minute grid changed for {symbol}")
    selected = work.loc[
        work["minute_code"].isin(_generated["CONTINUOUS_MINUTE_CODE_SET"]),
        ["trade_date", "minute_code", "high", "low"],
    ].copy()
    selected["minute_code"] = pd.Categorical(
        selected["minute_code"],
        categories=_generated["CONTINUOUS_MINUTE_CODES"],
        ordered=True,
    )
    selected = selected.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(counts.index).normalize()
    selected_count = _generated["SELECTED_BAR_COUNT"]
    if len(selected) != len(dates) * selected_count:
        raise Campaign106FeatureError(f"continuous minute grid changed for {symbol}")
    highs = selected["high"].to_numpy(dtype=np.float64).reshape(
        len(dates), selected_count
    )
    lows = selected["low"].to_numpy(dtype=np.float64).reshape(
        len(dates), selected_count
    )
    numeric_valid = (
        np.isfinite(highs).all(axis=1)
        & np.isfinite(lows).all(axis=1)
        & (highs > 0.0).all(axis=1)
        & (lows > 0.0).all(axis=1)
    )
    ordered = (lows <= highs).all(axis=1)
    valid = numeric_valid & ordered
    varying = highs > lows
    nonvarying = highs == lows
    scores = np.full(len(dates), np.nan, dtype=np.float64)
    counts_varying = varying.sum(axis=1, dtype=np.int16)
    scores[valid] = counts_varying[valid].astype(np.float64) / selected_count
    eligible = np.isfinite(scores) & (scores >= 0.0) & (scores <= 1.0)
    scores[~eligible] = np.nan
    return pd.DataFrame(
        {"trade_date": dates, "nonzero_range_bar_share": scores}
    ), {
        "source_rows": int(len(work)),
        "source_sessions": int(len(dates)),
        "valid_range_occupancy_sessions": int(eligible.sum()),
        "invalid_numeric_sessions": int((~numeric_valid).sum()),
        "invalid_ordered_range_sessions": int((numeric_valid & ~ordered).sum()),
        "nonzero_range_bars": int(varying[valid].sum()),
        "zero_range_bars": int(nonvarying[valid].sum()),
    }


for _name, _value in {
    "FACTOR_NAME": FACTOR_NAME,
    "FACTOR_FORMULA": FACTOR_FORMULA,
    "RAW_COLUMNS": RAW_COLUMNS,
    "OUTPUT_RUN_ID": OUTPUT_RUN_ID,
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
    "extract_nonzero_range_bar_share": extract_nonzero_range_bar_share,
}.items():
    _generated[_name] = _value


# The inherited loader resolves this global name at call time.
_generated["extract_nonzero_range_bar_share"] = extract_nonzero_range_bar_share

DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
DEFAULT_PROTOCOL = _generated["DEFAULT_PROTOCOL"]
DEFAULT_IMPLEMENTATION_FREEZE = _generated["DEFAULT_IMPLEMENTATION_FREEZE"]
FEATURE_TEST_PATH = _generated["FEATURE_TEST_PATH"]
AUDIT_RUNNER_PATH = _generated["AUDIT_RUNNER_PATH"]
AUDIT_TEST_PATH = _generated["AUDIT_TEST_PATH"]
SOURCE_BAR_COUNT = _generated["SOURCE_BAR_COUNT"]
SELECTED_BAR_COUNT = _generated["SELECTED_BAR_COUNT"]
CONTINUOUS_MINUTE_CODES = _generated["CONTINUOUS_MINUTE_CODES"]
CONTINUOUS_MINUTE_CODE_SET = _generated["CONTINUOUS_MINUTE_CODE_SET"]
SOURCE_MINUTE_CODE_SET = _generated["SOURCE_MINUTE_CODE_SET"]
IDENTITY_COLUMNS = _generated["IDENTITY_COLUMNS"]
OUTPUT_COLUMNS = _generated["OUTPUT_COLUMNS"]
EXPECTED_ROWS = _generated["EXPECTED_ROWS"]
EXPECTED_PARTITIONS = _generated["EXPECTED_PARTITIONS"]
CLEAN_MANIFEST_SHA256 = _generated["CLEAN_MANIFEST_SHA256"]
CLEAN_DATASET_SHA256 = _generated["CLEAN_DATASET_SHA256"]
bindings = _generated["bindings"]
source = _generated["source"]
output_root = _generated["output_root"]
build_snapshot = _generated["build_snapshot"]
verify_snapshot_files = _generated["verify_snapshot_files"]
validate_value_semantics = _generated["validate_value_semantics"]
empty_output_frame = _generated["empty_output_frame"]
_validate_implementation_freeze = _generated["_validate_implementation_freeze"]
_sha256 = _generated["_sha256"]
status = _generated["status"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
