#!/usr/bin/env python3
"""Build Campaign110's frozen opening-reference directional-occupancy snapshot."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign109_features.py"
BASE_RUNNER_SHA256 = "c95ef89be6d0b0ab238ac8c1e570af6f759df7a5a44fbc2a4607cf25cddd75fa"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _file_sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign109 feature builder changed")


FACTOR_NAME = "intraday_open_reference_directional_occupancy_240m"
FACTOR_FORMULA = (
    "mean(sign(log(close_i/open_09_31))) over exactly 240 selected closes, "
    "with exact equality contributing zero"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "open", "close")
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign110_feature_library_v1"
)
PROTOCOL_SHA256 = "75999c8aad35d7197b233c578990bb95c0a8d87ca25821cdd2859ef56f210f56"
MECHANISM_AUDIT_SHA256 = (
    "09927e6834169b4c0d94146870d00c49076364533ebfed0e801f7edf6177f7fb"
)
NUMERIC_POLICY_SHA256 = (
    "e526abc1a3c6f8c0d0cbbf74538efe4ee184d5b0ac812e60ee177d83d2fb33c6"
)
NUMERIC_COMPARATOR_COUNT = 133
NUMERIC_COMPARATOR_ORDER_SHA256 = (
    "b6fbcaffbc83699155d4291ebaa6a1b0066e4801b82b634cf27dfa6cee89eefc"
)
COMPLETE_DEFINITION_COUNT = 139
COMPLETE_DEFINITION_ORDER_SHA256 = (
    "eb505226fcf171151c5a4ead04c08369136be1af88d64c1710f4ab34d83d83e0"
)
FIXED_DENOMINATOR = 240
GENERATED_DOCSTRING = """Build Campaign110's opening-reference occupancy snapshot without returns.

The builder reads only ``datetime,symbol,provider,open,close`` from the
immutable Tushare minute source and stock-day identity from the joint-clean
snapshot. It never reads a daily price, comparator value, forward return, or
Candidate49 outcome.
"""


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign109", "Campaign110"),
    ("campaign109", "campaign110"),
    ("campaign_109", "campaign_110"),
    (
        "intraday_intrabar_body_magnitude_serial_persistence_238p",
        FACTOR_NAME,
    ),
    (
        "intrabar_body_magnitude_serial_persistence",
        "open_reference_directional_occupancy",
    ),
    ("body_magnitude_serial_persistence", "open_reference_directional_occupancy"),
    ("body_persistence", "open_reference_occupancy"),
    ("valid_body_persistence_sessions", "valid_open_reference_occupancy_sessions"),
    ("invalid_open_close_sessions", "invalid_anchor_or_close_sessions"),
    ("degenerate_body_variance_sessions", "invalid_fixed_denominator_sessions"),
    ("nonzero_body_bars", "nonzero_reference_state_bars"),
    ("zero_body_bars", "equal_reference_bars"),
    ("body_persistence_rule", "open_reference_occupancy_rule"),
    ("fixed_pair_count", "fixed_denominator"),
    (
        "positive_body_variance_required",
        "fixed_anchor_and_close_support_required",
    ),
    ("absolute_body_magnitude_used", "exact_reference_ties_retained"),
    ("body_and_correlation_semantics", "reference_and_occupancy_semantics"),
):
    _source = _source.replace(_old, _new)
for _old, _new in (
    (
        "e05004a5f6b93f2e5275d39f4e7855d73070038bbe5d25254cebb09d1a236015",
        PROTOCOL_SHA256,
    ),
    (
        "cce214f9cc67bc4245c14adc981ec077ed14e7f406db594fdb9c8428d92479cf",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "36ec8d963d733e5d6b44df7a3654b8e40444468e470b44b11cc19f6989a527b8",
        NUMERIC_POLICY_SHA256,
    ),
):
    _source = _source.replace(_old, _new)
_source = _source.replace('"fixed_denominator": 238', '"fixed_denominator": 240')

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign110_features_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)

_base_generated: dict[str, Any] = _generated["_generated"]

Campaign110FeatureError = _generated["Campaign110FeatureError"]

from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign109_features as c109,
)


DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_110_no_return_preregistration_20260808.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_110_no_return_implementation_freeze_v2_20260808.json"
)
FEATURE_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign110_features.py"
)
AUDIT_RUNNER_PATH = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign110_no_return_audit.py"
)
AUDIT_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign110_no_return_audit.py"
)


def _order_digest(items: Iterable[dict[str, str]]) -> str:
    return _base_generated["_json_digest"](
        [[item["name"], item["score_direction"]] for item in items]
    )


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = [dict(item) for item in c109.reconstruct_comparisons()]
    items.append({"name": c109.FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != NUMERIC_COMPARATOR_COUNT
        or _order_digest(items) != NUMERIC_COMPARATOR_ORDER_SHA256
        or items[-1] != {"name": c109.FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign110FeatureError("Campaign110 numeric comparison order changed")
    return items


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = [dict(item) for item in c109.reconstruct_complete_definitions()]
    items.append({"name": c109.FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != COMPLETE_DEFINITION_COUNT
        or _order_digest(items) != COMPLETE_DEFINITION_ORDER_SHA256
        or items[-1] != {"name": c109.FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign110FeatureError("Campaign110 complete definition order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    target = path.expanduser().resolve()
    _base_generated["_require"](target, PROTOCOL_SHA256, "protocol")
    report = _base_generated["bindings"].validate_record(
        target, data_root=_generated["DEFAULT_DATA_ROOT"]
    )
    if report.get("all_bindings_passed") is not True:
        raise Campaign110FeatureError("Campaign110 protocol binding failed")
    spec = json.loads(target.read_text(encoding="utf-8"))
    inputs = spec.get("authoritative_inputs") or {}
    policy = inputs.get("numeric_policy_v70") or {}
    candidate = spec.get("candidate") or {}
    grid = candidate.get("source_grid") or {}
    semantics = candidate.get("reference_and_occupancy_semantics") or {}
    snapshot = spec.get("source_snapshot_contract") or {}
    comparisons = spec.get("comparison_contract") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    gates = list(spec.get("ordered_no_return_gates") or [])
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign110_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign110_minute_source_candidate_comparator_daily_price_or_return_values"
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
        and grid.get("standalone_09_30_preserved_but_not_loaded_for_formula")
        is True
        and grid.get("lunch_transition_excluded") is True
        and semantics.get(
            "reference_open_and_all_selected_closes_finite_and_strictly_positive"
        )
        is True
        and semantics.get("reference") == "raw open of the selected 09:31 bar"
        and semantics.get("state") == "sign(log(close_i/reference))"
        and semantics.get("exact_reference_ties_retained_as_zero") is True
        and semantics.get("fixed_denominator") == FIXED_DENOMINATOR
        and semantics.get("row_drop_or_zero_bridge_allowed") is False
        and semantics.get("non_09_31_open_values_used") is False
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
            "complete_v70_semantic_definition_count_reviewed_before_values"
        )
        == COMPLETE_DEFINITION_COUNT
        and [item.get("gate") for item in gates] == [1, 2, 3]
        and finite.get("trial_count") == 1
        and finite.get("factor") == FACTOR_NAME
        and finite.get("direction") == "higher"
        and boundary.get("campaign110_source_rows_read_before_freeze") is False
        and boundary.get("campaign110_candidate_values_computed_or_read_before_freeze")
        is False
        and boundary.get("campaign110_comparison_values_read_before_freeze") is False
        and boundary.get("historical_daily_price_fields_read_before_freeze") == []
        and boundary.get("historical_forward_returns_read_before_freeze") is False
        and boundary.get("provider_request_issued") is False
        and len(reconstruct_comparisons()) == NUMERIC_COMPARATOR_COUNT
        and len(reconstruct_complete_definitions()) == COMPLETE_DEFINITION_COUNT
    ):
        raise Campaign110FeatureError("Campaign110 protocol semantics changed")
    return spec


def compute_open_reference_directional_occupancy(
    opens: np.ndarray, closes: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    open_ = np.asarray(opens, dtype=np.float64)
    close = np.asarray(closes, dtype=np.float64)
    if open_.ndim != 2 or open_.shape[1] != _generated["SELECTED_BAR_COUNT"]:
        raise Campaign110FeatureError("Campaign110 requires an n-by-240 open array")
    if close.shape != open_.shape:
        raise Campaign110FeatureError("Campaign110 open/close shapes changed")
    reference = open_[:, 0]
    source_valid = (
        np.isfinite(reference)
        & (reference > 0.0)
        & np.isfinite(close).all(axis=1)
        & (close > 0.0).all(axis=1)
    )
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        states = np.sign(np.log(close / reference[:, None]))
        raw_score = states.mean(axis=1)
    support = source_valid & np.isfinite(states).all(axis=1) & np.isfinite(raw_score)
    result = np.full(len(open_), np.nan, dtype=np.float64)
    result[support] = raw_score[support]
    eligible = np.isfinite(result) & (result >= -1.0) & (result <= 1.0)
    result[~eligible] = np.nan
    return result, eligible, states, reference


def extract_open_reference_directional_occupancy(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign110FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    empty = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "open_reference_directional_occupancy": pd.Series(dtype="float64"),
        }
    )
    quality = {
        "source_rows": 0,
        "source_sessions": 0,
        "valid_open_reference_occupancy_sessions": 0,
        "invalid_anchor_or_close_sessions": 0,
        "invalid_fixed_denominator_sessions": 0,
        "nonzero_reference_state_bars": 0,
        "equal_reference_bars": 0,
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
        raise Campaign110FeatureError(f"raw minute identity changed for {symbol}")
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
        raise Campaign110FeatureError(f"raw minute grid changed for {symbol}")
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
        raise Campaign110FeatureError(f"continuous minute grid changed for {symbol}")
    open_ = selected["open"].to_numpy(dtype=np.float64).reshape(len(dates), 240)
    close = selected["close"].to_numpy(dtype=np.float64).reshape(len(dates), 240)
    values, eligible, states, reference = compute_open_reference_directional_occupancy(
        open_, close
    )
    source_valid = (
        np.isfinite(reference)
        & (reference > 0.0)
        & np.isfinite(close).all(axis=1)
        & (close > 0.0).all(axis=1)
    )
    return pd.DataFrame(
        {
            "trade_date": dates,
            "open_reference_directional_occupancy": values,
        }
    ), {
        "source_rows": int(len(work)),
        "source_sessions": int(len(dates)),
        "valid_open_reference_occupancy_sessions": int(eligible.sum()),
        "invalid_anchor_or_close_sessions": int((~source_valid).sum()),
        "invalid_fixed_denominator_sessions": 0,
        "nonzero_reference_state_bars": int(
            ((states != 0.0) & source_valid[:, None]).sum()
        ),
        "equal_reference_bars": int(
            ((states == 0.0) & source_valid[:, None]).sum()
        ),
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
        raise Campaign110FeatureError("Campaign110 output columns changed")
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"].astype(bool)
    scaled = values[eligible] * FIXED_DENOMINATOR
    if (
        values[eligible].isna().any()
        or ((values[eligible] < -1.0) | (values[eligible] > 1.0)).any()
        or not np.allclose(scaled, np.rint(scaled), rtol=0.0, atol=1e-12)
        or values[~eligible].notna().any()
    ):
        raise Campaign110FeatureError("Campaign110 value semantics changed")
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
    "FIXED_DENOMINATOR": FIXED_DENOMINATOR,
    "__doc__": GENERATED_DOCSTRING,
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
    "compute_open_reference_directional_occupancy": compute_open_reference_directional_occupancy,
    "extract_open_reference_directional_occupancy": extract_open_reference_directional_occupancy,
    "validate_value_semantics": validate_value_semantics,
}.items():
    _generated[_name] = _value
    _base_generated[_name] = _value


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
attach_open_reference_occupancy_values = _generated[
    "attach_open_reference_occupancy_values"
]
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
