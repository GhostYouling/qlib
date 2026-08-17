#!/usr/bin/env python3
"""Build Campaign152's frozen session-total-amount feature snapshot."""

# ruff: noqa: E402

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


FACTOR_NAME = "intraday_session_total_amount_magnitude_240m"
FACTOR_SHORT_NAME = "session_total_amount_magnitude"
FACTOR_FORMULA = (
    "natural log1p of the strictly positive sum of exact finite nonnegative raw "
    "CNY amount over 09:31-11:30 and 13:01-15:00"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "amount")
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign152_feature_library_v1"
)
PROTOCOL_SHA256 = "026344726b68729336ce68a4b039c91c5faeecec6586929a804f9fb3eb465250"
MECHANISM_AUDIT_SHA256 = (
    "e51c0c03cd1f43b9cb383e6459491088b459ae36ffe4d6a61e7bfcbdae804fab"
)
NUMERIC_POLICY_SHA256 = (
    "b904387571a5f63636b329050c1ad26d54b21cf4dc9a7dbc79dd548eadcd9ce8"
)
NUMERIC_COMPARATOR_COUNT = 142
NUMERIC_COMPARATOR_ORDER_SHA256 = (
    "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf"
)
PRIOR_COMPLETE_DEFINITION_COUNT = 156
PRIOR_COMPLETE_DEFINITION_ORDER_SHA256 = (
    "928e7eff198f44fa3112d7e8ff94571c1ad18b85a1ee50a38f3896baf555847c"
)
COMPLETE_DEFINITION_COUNT = 157
COMPLETE_DEFINITION_ORDER_SHA256 = (
    "c39bb6ca969b5f469a9377a5b5ca743405cec9d8511297ed6a1c44188ef40b82"
)


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign105", "Campaign152"),
    ("campaign105", "campaign152"),
    ("campaign_105", "campaign_152"),
    ("activity-clock occupancy", "session total amount magnitude"),
    (
        "``datetime,symbol,provider,volume,amount``",
        "``datetime,symbol,provider,amount``",
    ),
    ("intraday_active_trading_bar_share_240m", FACTOR_NAME),
    ("active_trading_bar_share", FACTOR_SHORT_NAME),
    ("extract_active_trading_bar_share", "extract_session_total_amount_magnitude"),
    ("attach_activity_values", "attach_amount_values"),
    ("valid_activity_sessions", "valid_amount_sessions"),
    ("one_sided_zero_sessions", "nonpositive_total_amount_sessions"),
    ("active_bars", "positive_amount_bars"),
    ("joint_zero_bars", "zero_amount_bars"),
    ("activity_rule", "amount_rule"),
    ("minimum_active_bar_count", "minimum_positive_amount_bar_count"),
    ("positive_total_activity_required", "positive_total_amount_required"),
    ("activity_magnitude_used", "raw_amount_magnitude_used"),
    (
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "volume", "amount")',
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "amount")',
    ),
    ("{FACTOR_NAME: [0.0, 1.0]}", "{FACTOR_NAME: [0.0, None]}"),
):
    _source = _source.replace(_old, _new)
_source = _source.replace(
    '"minimum_positive_amount_bar_count": 0',
    '"minimum_positive_amount_bar_count": 1',
)
_source = _source.replace(
    'get("minimum_positive_amount_bar_count") == 0',
    'get("minimum_positive_amount_bar_count") == 1',
)
_source = _source.replace(
    '"positive_total_amount_required": False',
    '"positive_total_amount_required": True',
)
_source = _source.replace(
    'get("positive_total_amount_required") is False',
    'get("positive_total_amount_required") is True',
)
_source = _source.replace(
    '"raw_amount_magnitude_used": False',
    '"raw_amount_magnitude_used": True',
)
_source = _source.replace(
    'get("raw_amount_magnitude_used") is False',
    'get("raw_amount_magnitude_used") is True',
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign152_features_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)

Campaign152FeatureError = _generated["Campaign152FeatureError"]

from scripts import (
    a_share_three_day_walkforward_campaign146_features as c146,
)  # noqa: E402
from scripts import (
    a_share_three_day_walkforward_campaign152_formula as formula,
)  # noqa: E402


DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_152_no_return_preregistration_20260815.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_152_implementation_freeze_20260815.json"
)
FEATURE_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign152_features.py"
)
FORMULA_PATH = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign152_formula.py"
)
FORMULA_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign152_formula.py"
)


def _order_digest(items: Iterable[dict[str, str]]) -> str:
    return _generated["_json_digest"](
        [[item["name"], item["score_direction"]] for item in items]
    )


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = [dict(item) for item in c146.reconstruct_comparisons()]
    items.append({"name": c146.FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != NUMERIC_COMPARATOR_COUNT
        or _order_digest(items) != NUMERIC_COMPARATOR_ORDER_SHA256
    ):
        raise Campaign152FeatureError("Campaign152 numeric comparison order changed")
    return items


def reconstruct_prior_complete_definitions() -> list[dict[str, str]]:
    items = [dict(item) for item in c146.reconstruct_complete_definitions()]
    items.append(
        {
            "name": "intraday_relative_amount_share_clock_center_240m",
            "score_direction": "higher",
        }
    )
    if (
        len(items) != PRIOR_COMPLETE_DEFINITION_COUNT
        or _order_digest(items) != PRIOR_COMPLETE_DEFINITION_ORDER_SHA256
    ):
        raise Campaign152FeatureError("Campaign152 prior definition order changed")
    return items


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = reconstruct_prior_complete_definitions()
    items.append({"name": FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != COMPLETE_DEFINITION_COUNT
        or _order_digest(items) != COMPLETE_DEFINITION_ORDER_SHA256
    ):
        raise Campaign152FeatureError("Campaign152 complete definition order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    target = path.expanduser().resolve()
    if target != DEFAULT_PROTOCOL.resolve():
        raise Campaign152FeatureError("Campaign152 protocol path changed")
    try:
        spec = formula.load_protocol(target)
    except formula.Campaign152FormulaError as exc:
        raise Campaign152FeatureError(str(exc)) from exc
    inputs = spec.get("authoritative_inputs") or {}
    for binding in inputs.values():
        bound = Path(str(binding.get("path", "")))
        if not bound.is_absolute():
            bound = REPO_ROOT / bound
        if not bound.is_file() or _file_sha256(bound) != binding.get("sha256"):
            raise Campaign152FeatureError(
                f"Campaign152 authoritative input changed: {bound}"
            )
    source = spec.get("source_snapshot_contract") or {}
    comparison = spec.get("comparison_contract") or {}
    candidate = spec.get("candidate") or {}
    exact = candidate.get("exact_formula") or {}
    gates = list(spec.get("ordered_no_return_gates") or [])
    if not (
        (inputs.get("numeric_policy_v208") or {}).get("sha256") == NUMERIC_POLICY_SHA256
        and (inputs.get("mechanism_overlap_audit") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and source.get("data_root") == str(_generated["DEFAULT_DATA_ROOT"])
        and source.get("raw_manifest_sha256") == _generated["RAW_MANIFEST_SHA256"]
        and source.get("joint_clean_manifest_sha256")
        == _generated["CLEAN_MANIFEST_SHA256"]
        and source.get("joint_clean_dataset_sha256")
        == _generated["CLEAN_DATASET_SHA256"]
        and source.get("expected_partitions") == _generated["EXPECTED_PARTITIONS"]
        and source.get("expected_rows") == _generated["EXPECTED_ROWS"]
        and source.get("output_run_id") == OUTPUT_RUN_ID
        and candidate.get("source_projection") == list(RAW_COLUMNS)
        and exact.get("score") == "log1p(S) using the natural logarithm."
        and comparison.get("candidate_appended_complete_definition_count")
        == COMPLETE_DEFINITION_COUNT
        and comparison.get("candidate_appended_complete_definition_order_sha256")
        == COMPLETE_DEFINITION_ORDER_SHA256
        and comparison.get("numeric_comparator_count") == NUMERIC_COMPARATOR_COUNT
        and comparison.get("numeric_comparator_order_sha256")
        == NUMERIC_COMPARATOR_ORDER_SHA256
        and [item.get("gate") for item in gates] == [1, 2, 3]
        and len(reconstruct_complete_definitions()) == COMPLETE_DEFINITION_COUNT
        and len(reconstruct_comparisons()) == NUMERIC_COMPARATOR_COUNT
    ):
        raise Campaign152FeatureError("Campaign152 protocol bindings changed")
    return spec


def extract_session_total_amount_magnitude(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign152FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    empty = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            FACTOR_SHORT_NAME: pd.Series(dtype="float64"),
        }
    )
    quality = {
        "source_rows": 0,
        "source_sessions": 0,
        "valid_amount_sessions": 0,
        "invalid_numeric_sessions": 0,
        "nonpositive_total_amount_sessions": 0,
        "positive_amount_bars": 0,
        "zero_amount_bars": 0,
    }
    if raw.empty:
        return empty, quality
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
        raise Campaign152FeatureError(f"raw minute identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    distinct = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].nunique()
    source_bar_count = _generated["SOURCE_BAR_COUNT"]
    source_codes = _generated["SOURCE_MINUTE_CODE_SET"]
    if (
        counts.empty
        or not counts.eq(source_bar_count).all()
        or not distinct.eq(source_bar_count).all()
        or not work["minute_code"].isin(source_codes).all()
    ):
        raise Campaign152FeatureError(f"raw minute grid changed for {symbol}")
    selected = work.loc[
        work["minute_code"].isin(_generated["CONTINUOUS_MINUTE_CODE_SET"]),
        ["trade_date", "minute_code", "amount"],
    ].copy()
    selected["minute_code"] = pd.Categorical(
        selected["minute_code"],
        categories=_generated["CONTINUOUS_MINUTE_CODES"],
        ordered=True,
    )
    selected = selected.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(counts.index).normalize()
    if len(selected) != len(dates) * formula.PROFILE_POSITIONS:
        raise Campaign152FeatureError(f"continuous minute grid changed for {symbol}")
    amount = (
        selected["amount"]
        .to_numpy(dtype=np.float64)
        .reshape(len(dates), formula.PROFILE_POSITIONS)
    )
    scores, eligible, formula_quality = formula.compute_session_total_amount_magnitude(
        amount
    )
    return pd.DataFrame({"trade_date": dates, FACTOR_SHORT_NAME: scores}), {
        "source_rows": int(len(work)),
        "source_sessions": int(len(dates)),
        "valid_amount_sessions": int(eligible.sum()),
        "invalid_numeric_sessions": int(
            formula_quality["nonfinite_amount_rows"]
            + formula_quality["negative_amount_rows"]
        ),
        "nonpositive_total_amount_sessions": int(
            formula_quality["nonpositive_total_amount_rows"]
        ),
        "positive_amount_bars": int((amount[eligible] > 0.0).sum()),
        "zero_amount_bars": int((amount[eligible] == 0.0).sum()),
    }


def finalize_feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = (*_generated["IDENTITY_COLUMNS"], FACTOR_SHORT_NAME)
    if not set(required).issubset(frame.columns):
        raise Campaign152FeatureError("Campaign152 attached frame columns changed")
    work = frame.copy()
    values = pd.to_numeric(work[FACTOR_SHORT_NAME], errors="coerce")
    eligible = np.isfinite(values) & (values > 0.0)
    work[FACTOR_NAME] = values.where(eligible)
    work[f"{FACTOR_NAME}_eligible"] = eligible.astype(bool)
    return work


def validate_value_semantics(frame: pd.DataFrame) -> tuple[int, int]:
    if tuple(frame.columns) != _generated["OUTPUT_COLUMNS"]:
        raise Campaign152FeatureError("Campaign152 output columns changed")
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"].astype(bool)
    valid = np.isfinite(values) & (values > 0.0)
    if not eligible.equals(valid.astype(bool)) or values[~eligible].notna().any():
        raise Campaign152FeatureError("Campaign152 value semantics changed")
    return int(len(frame)), int(eligible.sum())


def _validate_implementation_freeze() -> dict[str, Any]:
    target = DEFAULT_IMPLEMENTATION_FREEZE.resolve()
    if not target.is_file():
        raise Campaign152FeatureError("Campaign152 implementation freeze missing")
    record = json.loads(target.read_text(encoding="utf-8"))
    code = record.get("code") or {}
    tests = record.get("tests") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign152_implementation_freeze"
        and record.get("status")
        == "formula_builder_and_synthetic_tests_frozen_before_historical_values"
        and record.get("protocol_sha256") == PROTOCOL_SHA256
        and code.get("formula_sha256") == _file_sha256(FORMULA_PATH)
        and code.get("feature_builder_sha256") == _file_sha256(Path(__file__))
        and tests.get("formula_test_sha256") == _file_sha256(FORMULA_TEST_PATH)
        and tests.get("feature_test_sha256") == _file_sha256(FEATURE_TEST_PATH)
        and tests.get("exit_code") == 0
        and tests.get("passed") >= 10
        and record.get("complete_definition_count") == COMPLETE_DEFINITION_COUNT
        and record.get("complete_definition_order_sha256")
        == COMPLETE_DEFINITION_ORDER_SHA256
        and record.get("numeric_comparator_count") == NUMERIC_COMPARATOR_COUNT
        and record.get("numeric_comparator_order_sha256")
        == NUMERIC_COMPARATOR_ORDER_SHA256
        and boundary.get("historical_source_rows_read") is False
        and boundary.get("candidate_or_comparator_values_read") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign152FeatureError("Campaign152 implementation freeze changed")
    return record


for _name, _value in {
    "FACTOR_NAME": FACTOR_NAME,
    "FACTOR_FORMULA": FACTOR_FORMULA,
    "RAW_COLUMNS": RAW_COLUMNS,
    "OUTPUT_RUN_ID": OUTPUT_RUN_ID,
    "DEFAULT_PROTOCOL": DEFAULT_PROTOCOL,
    "DEFAULT_IMPLEMENTATION_FREEZE": DEFAULT_IMPLEMENTATION_FREEZE,
    "FEATURE_TEST_PATH": FEATURE_TEST_PATH,
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
    "extract_session_total_amount_magnitude": extract_session_total_amount_magnitude,
    "finalize_feature_frame": finalize_feature_frame,
    "validate_value_semantics": validate_value_semantics,
    "_validate_implementation_freeze": _validate_implementation_freeze,
}.items():
    _generated[_name] = _value


DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
OUTPUT_COLUMNS = _generated["OUTPUT_COLUMNS"]
EXPECTED_ROWS = _generated["EXPECTED_ROWS"]
EXPECTED_PARTITIONS = _generated["EXPECTED_PARTITIONS"]
CLEAN_MANIFEST_SHA256 = _generated["CLEAN_MANIFEST_SHA256"]
CLEAN_DATASET_SHA256 = _generated["CLEAN_DATASET_SHA256"]
RAW_MANIFEST_SHA256 = _generated["RAW_MANIFEST_SHA256"]
SOURCE_BAR_COUNT = _generated["SOURCE_BAR_COUNT"]
CONTINUOUS_MINUTE_CODES = _generated["CONTINUOUS_MINUTE_CODES"]
CONTINUOUS_MINUTE_CODE_SET = _generated["CONTINUOUS_MINUTE_CODE_SET"]
SOURCE_MINUTE_CODE_SET = _generated["SOURCE_MINUTE_CODE_SET"]
IDENTITY_COLUMNS = _generated["IDENTITY_COLUMNS"]
attach_amount_values = _generated["attach_amount_values"]
empty_output_frame = _generated["empty_output_frame"]
output_root = _generated["output_root"]
build_snapshot = _generated["build_snapshot"]
verify_snapshot_files = _generated["verify_snapshot_files"]
status = _generated["status"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
