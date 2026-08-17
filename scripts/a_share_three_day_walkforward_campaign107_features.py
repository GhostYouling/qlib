#!/usr/bin/env python3
"""Build Campaign107's frozen exact close-level diversity snapshot.

Only ``datetime,symbol,provider,close`` is projected from the immutable minute
source.  No comparator, daily-price, forward-return, Candidate49, or provider
value is read by the feature builder.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign105_features.py"
)
BASE_RUNNER_SHA256 = "cf151f6f8af55bc219f9ed06512eb138d833352316a958b4a9b1dac05079e4ba"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _file_sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign105 feature builder changed")


FACTOR_NAME = "intraday_exact_close_level_diversity_240m"
FACTOR_FORMULA = (
    "on exactly 240 bars at 09:31-11:30 and 13:01-15:00, require finite "
    "strictly positive close; for exact close-level counts n_j return "
    "1-sum_j n_j*(n_j-1)/57360, with no rounding, tolerance, tick inference, "
    "binning, normalization, threshold, or clock-order use after grid validation"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "close")
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign107_feature_library_v1"
)
BASE_PROTOCOL_SHA256 = (
    "9c5665f0c10b73706b67e66a8acd503e2a1c191ef9e7f4f41f1b68ca29dc9a3e"
)
PROTOCOL_SHA256 = "7d03d2c983cabdb6d63b22ff61b96a2b90ca76ec6518ea45a5d5465431570794"
MECHANISM_AUDIT_SHA256 = (
    "f6a043e7819fc47e259b14e37cee5db9690aaf4e55bc56ebec07c1e4ce0d6206"
)
NUMERIC_POLICY_SHA256 = (
    "76033dc9623bdb85993232ee12518ebb80331d662a3fa5861bfedcc0cf8dc086"
)
NUMERIC_COMPARATOR_COUNT = 132
NUMERIC_COMPARATOR_ORDER_SHA256 = (
    "7ed69afd1408e84dcc856583344166ffc9bcbb0add1aed63163b1d12a1be9a25"
)
COMPLETE_DEFINITION_COUNT = 136
COMPLETE_DEFINITION_ORDER_SHA256 = (
    "2099f016f5979a820b480a83aa28877504ea5238362feed551bb7cf583cbf7d0"
)
UNORDERED_PAIR_COUNT = 28_680
ORDERED_PAIR_COUNT = 57_360


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign105", "Campaign107"),
    ("campaign105", "campaign107"),
    ("campaign_105", "campaign_107"),
    ("intraday_active_trading_bar_share_240m", FACTOR_NAME),
    ("active_trading_bar_share", "exact_close_level_diversity"),
    ("extract_active_trading_bar_share", "extract_exact_close_level_diversity"),
    ("attach_activity_values", "attach_exact_level_values"),
    ("valid_activity_sessions", "valid_exact_level_sessions"),
    ("one_sided_zero_sessions", "invalid_exact_level_sessions"),
    ("active_bars", "exact_close_distinct_levels"),
    ("joint_zero_bars", "exact_close_repeated_unordered_pairs"),
    (
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "volume", "amount")',
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "close")',
    ),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign107_features_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)

Campaign107FeatureError = _generated["Campaign107FeatureError"]

from scripts import (
    a_share_three_day_walkforward_campaign106_features as c106,
)  # noqa: E402


DEFAULT_BASE_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_107_no_return_preregistration_20260808.json"
)
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_107_no_return_preregistration_binding_correction_v2_20260808.json"
)


def _order_digest(items: Iterable[dict[str, str]]) -> str:
    payload = [[item["name"], item["score_direction"]] for item in items]
    return _generated["_json_digest"](payload)


def reconstruct_comparisons() -> list[dict[str, str]]:
    """Rebuild the exact v66 numeric order without reading factor values."""

    items = [dict(item) for item in c106.reconstruct_comparisons()]
    if (
        len(items) != NUMERIC_COMPARATOR_COUNT
        or _order_digest(items) != NUMERIC_COMPARATOR_ORDER_SHA256
        or items[-1]
        != {
            "name": "intraday_active_trading_bar_share_240m",
            "score_direction": "higher",
        }
    ):
        raise Campaign107FeatureError("Campaign107 numeric comparison order changed")
    return items


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    """Rebuild all 136 v66 definitions, including Campaign106 semantic-only."""

    items = [dict(item) for item in c106.reconstruct_complete_definitions()]
    items.append({"name": c106.FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != COMPLETE_DEFINITION_COUNT
        or _order_digest(items) != COMPLETE_DEFINITION_ORDER_SHA256
        or items[-1] != {"name": c106.FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign107FeatureError("Campaign107 complete definition order changed")
    return items


def _binding_pairs(record: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        record["base_preregistration"],
        record["preserved_failure"],
        record["exact_binding_correction"],
        *record["current_authority_rebinding"].values(),
        *record["unchanged_prevalue_support_bindings"].values(),
    ]


def load_protocol(path: Path | None = None) -> dict[str, Any]:
    """Load base+overlay and fail closed before any Campaign107 value read."""

    target = DEFAULT_PROTOCOL if path is None else path.expanduser().resolve()
    _generated["_require"](target, PROTOCOL_SHA256, "effective protocol overlay")
    overlay = json.loads(target.read_text(encoding="utf-8"))
    for binding in _binding_pairs(overlay):
        bound = REPO_ROOT / str(binding["path"])
        expected = str(binding.get("sha256") or binding.get("effective_sha256") or "")
        _generated["_require"](bound, expected, "effective protocol binding")
    _generated["_require"](DEFAULT_BASE_PROTOCOL, BASE_PROTOCOL_SHA256, "base protocol")
    base = json.loads(DEFAULT_BASE_PROTOCOL.read_text(encoding="utf-8"))

    candidate = base.get("candidate") or {}
    grid = candidate.get("source_grid") or {}
    exact = candidate.get("exact_level_semantics") or {}
    snapshot = base.get("source_snapshot_contract") or {}
    comparisons = base.get("comparison_contract") or {}
    finite = base.get("finite_development_catalog_if_admitted") or {}
    boundary = base.get("research_boundary") or {}
    correction = overlay.get("exact_binding_correction") or {}
    policy = (overlay.get("current_authority_rebinding") or {}).get(
        "future_numeric_policy_v66"
    ) or {}
    effective = overlay.get("effective_protocol_semantics") or {}
    gates = effective.get("uniqueness_gate") or {}
    coverage = effective.get("coverage_gate") or {}
    if not (
        base.get("kind")
        == "a_share_three_day_walkforward_campaign107_no_return_preregistration"
        and overlay.get("kind")
        == "a_share_three_day_walkforward_campaign107_no_return_preregistration_binding_correction"
        and overlay.get("status")
        == "effective_prevalue_protocol_overlay_all_bindings_corrected"
        and overlay.get("effective_protocol_requires_base_plus_this_overlay") is True
        and correction.get("only_base_literal_corrected") is True
        and correction.get("effective_sha256")
        == "2c8c85ba1155289d03c3ebc1175a4a2504bf8022b849087840777ee41586e2a0"
        and policy.get("sha256") == NUMERIC_POLICY_SHA256
        and policy.get("complete_definition_count") == COMPLETE_DEFINITION_COUNT
        and policy.get("complete_definition_order_sha256")
        == COMPLETE_DEFINITION_ORDER_SHA256
        and policy.get("numeric_comparator_count") == NUMERIC_COMPARATOR_COUNT
        and policy.get("numeric_comparator_order_sha256")
        == NUMERIC_COMPARATOR_ORDER_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and tuple(candidate.get("source_projection") or ()) == RAW_COLUMNS
        and grid.get("accepted_rows_required") == _generated["SOURCE_BAR_COUNT"]
        and grid.get("selected_rows") == _generated["SELECTED_BAR_COUNT"]
        and grid.get("standalone_09_30_preserved_but_not_loaded_for_formula") is True
        and exact.get("finite_strictly_positive_close_required") is True
        and exact.get("exact_numeric_equality_only") is True
        and exact.get("rounding_tick_inference_tolerance_or_binning_used") is False
        and exact.get("clock_order_used_after_exact_grid_validation") is False
        and exact.get("unordered_distinct_clock_pair_count") == UNORDERED_PAIR_COUNT
        and exact.get("ordered_distinct_clock_pair_count") == ORDERED_PAIR_COUNT
        and exact.get("positive_return_range_variance_or_update_count_required")
        is False
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
        and coverage
        == {
            "median_minimum": 0.95,
            "p05_minimum": 0.9,
            "p05_eligible_names_minimum": 50,
            "non_overlapping_three_session_cohorts_minimum": 200,
            "observed_years_minimum": 5,
        }
        and gates.get("numeric_comparator_count") == NUMERIC_COMPARATOR_COUNT
        and gates.get("minimum_pairwise_names_per_session") == 50
        and gates.get("minimum_pairwise_sessions_per_comparison") == 100
        and gates.get("strict_maximum_absolute_median_daily_spearman") == 0.8
        and gates.get("all_comparators_must_pass") is True
        and gates.get("missing_comparator_values_preserved_until_pairwise_overlap")
        is True
        and finite.get("trial_count") == 1
        and finite.get("trial_id")
        == "wf107_intraday_exact_close_level_diversity_240m_single_higher"
        and finite.get("factor") == FACTOR_NAME
        and finite.get("direction") == "higher"
        and boundary.get("campaign107_source_rows_read_before_freeze") is False
        and boundary.get("campaign107_candidate_values_computed_or_read_before_freeze")
        is False
        and boundary.get("campaign107_comparison_values_read_before_freeze") is False
        and boundary.get("historical_daily_price_fields_read_before_freeze") == []
        and boundary.get("historical_forward_returns_read_before_freeze") is False
        and boundary.get("provider_request_issued") is False
        and len(reconstruct_comparisons()) == NUMERIC_COMPARATOR_COUNT
        and len(reconstruct_complete_definitions()) == COMPLETE_DEFINITION_COUNT
    ):
        raise Campaign107FeatureError(
            "Campaign107 effective protocol semantics changed"
        )
    return {"base": base, "overlay": overlay}


def _repeated_unordered_pairs(sorted_close: np.ndarray) -> np.ndarray:
    """Count exact equal-value unordered pairs independently in each row."""

    if (
        sorted_close.ndim != 2
        or sorted_close.shape[1] != _generated["SELECTED_BAR_COUNT"]
    ):
        raise Campaign107FeatureError("Campaign107 close matrix shape changed")
    rows, width = sorted_close.shape
    flat = sorted_close.reshape(-1)
    boundaries = np.empty(flat.size, dtype=bool)
    boundaries[0] = True
    boundaries[1:] = flat[1:] != flat[:-1]
    boundaries[::width] = True
    starts = np.flatnonzero(boundaries)
    lengths = np.diff(np.append(starts, flat.size)).astype(np.int64, copy=False)
    group_rows = starts // width
    pair_weights = lengths * (lengths - 1) // 2
    return np.bincount(group_rows, weights=pair_weights, minlength=rows).astype(
        np.int64, copy=False
    )


def extract_exact_close_level_diversity(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Validate the exact grid and compute collision-complement diversity."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign107FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    empty = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "exact_close_level_diversity": pd.Series(dtype="float64"),
        }
    )
    quality = {
        "source_rows": 0,
        "source_sessions": 0,
        "valid_exact_level_sessions": 0,
        "invalid_numeric_sessions": 0,
        "invalid_exact_level_sessions": 0,
        "exact_close_distinct_levels": 0,
        "exact_close_repeated_unordered_pairs": 0,
    }
    if raw.empty:
        return empty, quality
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["close"] = pd.to_numeric(work["close"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign107FeatureError(f"raw minute identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    distinct_minutes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].nunique()
    if (
        counts.empty
        or not counts.eq(_generated["SOURCE_BAR_COUNT"]).all()
        or not distinct_minutes.eq(_generated["SOURCE_BAR_COUNT"]).all()
        or not work["minute_code"].isin(_generated["SOURCE_MINUTE_CODE_SET"]).all()
    ):
        raise Campaign107FeatureError(f"raw minute grid changed for {symbol}")
    selected = work.loc[
        work["minute_code"].isin(_generated["CONTINUOUS_MINUTE_CODE_SET"]),
        ["trade_date", "minute_code", "close"],
    ].copy()
    selected["minute_code"] = pd.Categorical(
        selected["minute_code"],
        categories=_generated["CONTINUOUS_MINUTE_CODES"],
        ordered=True,
    )
    selected = selected.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(counts.index).normalize()
    width = _generated["SELECTED_BAR_COUNT"]
    if len(selected) != len(dates) * width:
        raise Campaign107FeatureError(f"continuous minute grid changed for {symbol}")
    close = selected["close"].to_numpy(dtype=np.float64).reshape(len(dates), width)
    numeric_valid = np.isfinite(close).all(axis=1) & (close > 0.0).all(axis=1)
    scores = np.full(len(dates), np.nan, dtype=np.float64)
    repeated_pairs = np.zeros(len(dates), dtype=np.int64)
    distinct_levels = np.zeros(len(dates), dtype=np.int64)
    if numeric_valid.any():
        valid_close = np.sort(close[numeric_valid], axis=1)
        repeated = _repeated_unordered_pairs(valid_close)
        repeated_pairs[numeric_valid] = repeated
        distinct_levels[numeric_valid] = 1 + np.count_nonzero(
            valid_close[:, 1:] != valid_close[:, :-1], axis=1
        )
        scores[numeric_valid] = 1.0 - repeated.astype(np.float64) / UNORDERED_PAIR_COUNT
    eligible = np.isfinite(scores) & (scores >= 0.0) & (scores <= 1.0)
    scaled = scores[eligible] * UNORDERED_PAIR_COUNT
    if not np.allclose(scaled, np.rint(scaled), rtol=0.0, atol=1e-9):
        raise Campaign107FeatureError("Campaign107 discrete factor semantics changed")
    scores[~eligible] = np.nan
    return pd.DataFrame({"trade_date": dates, "exact_close_level_diversity": scores}), {
        "source_rows": int(len(work)),
        "source_sessions": int(len(dates)),
        "valid_exact_level_sessions": int(eligible.sum()),
        "invalid_numeric_sessions": int((~numeric_valid).sum()),
        "invalid_exact_level_sessions": int((~numeric_valid).sum()),
        "exact_close_distinct_levels": int(distinct_levels[eligible].sum()),
        "exact_close_repeated_unordered_pairs": int(repeated_pairs[eligible].sum()),
    }


def validate_value_semantics(frame: pd.DataFrame) -> tuple[int, int]:
    if tuple(frame.columns) != tuple(_generated["OUTPUT_COLUMNS"]):
        raise Campaign107FeatureError("Campaign107 output columns changed")
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"].astype(bool)
    scaled = values[eligible] * UNORDERED_PAIR_COUNT
    if (
        values[eligible].isna().any()
        or ((values[eligible] < 0.0) | (values[eligible] > 1.0)).any()
        or not np.allclose(scaled, np.rint(scaled), rtol=0.0, atol=1e-9)
        or values[~eligible].notna().any()
    ):
        raise Campaign107FeatureError("Campaign107 value semantics changed")
    return int(len(frame)), int(eligible.sum())


for _name, _value in {
    "FACTOR_NAME": FACTOR_NAME,
    "FACTOR_FORMULA": FACTOR_FORMULA,
    "RAW_COLUMNS": RAW_COLUMNS,
    "OUTPUT_RUN_ID": OUTPUT_RUN_ID,
    "DEFAULT_PROTOCOL": DEFAULT_PROTOCOL,
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
    "extract_exact_close_level_diversity": extract_exact_close_level_diversity,
    "validate_value_semantics": validate_value_semantics,
}.items():
    _generated[_name] = _value


DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
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
empty_output_frame = _generated["empty_output_frame"]
_validate_implementation_freeze = _generated["_validate_implementation_freeze"]
_sha256 = _generated["_sha256"]
status = _generated["status"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
