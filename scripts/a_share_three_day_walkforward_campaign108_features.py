#!/usr/bin/env python3
"""Build Campaign108's frozen continuous-session endpoint reversal snapshot."""

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


FACTOR_NAME = "intraday_continuous_session_net_return_reversal_240m"
FACTOR_FORMULA = (
    "after exact 241-row grid validation, require finite strictly positive "
    "close at 09:31 and 15:00 and return -tanh(log(close_15_00/close_09_31)); "
    "09:30 and all intermediate values are excluded from the formula"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "close")
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign108_feature_library_v1"
)
PROTOCOL_SHA256 = "d196415b08996bb8ff68959abe2e6325f7c4dcfe4119494a96e86a66ec8a4339"
MECHANISM_AUDIT_SHA256 = (
    "3349c97387b51669a453b10d56c0da642715127af8916d6573034662a82fce34"
)
NUMERIC_POLICY_SHA256 = (
    "4740555b0647540e99396682705a1e77745c53badc9a4bbb671e1607550b9435"
)
NUMERIC_COMPARATOR_COUNT = 132
NUMERIC_COMPARATOR_ORDER_SHA256 = (
    "7ed69afd1408e84dcc856583344166ffc9bcbb0add1aed63163b1d12a1be9a25"
)
COMPLETE_DEFINITION_COUNT = 137
COMPLETE_DEFINITION_ORDER_SHA256 = (
    "26233fd1fe697b08268910286fb077fbda894e8e572af020959b1997e4285baa"
)
FIRST_ENDPOINT_CODE = 9 * 60 + 31
LAST_ENDPOINT_CODE = 15 * 60


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign105", "Campaign108"),
    ("campaign105", "campaign108"),
    ("campaign_105", "campaign_108"),
    ("intraday_active_trading_bar_share_240m", FACTOR_NAME),
    ("active_trading_bar_share", "continuous_session_net_return_reversal"),
    (
        "extract_active_trading_bar_share",
        "extract_continuous_session_net_return_reversal",
    ),
    ("attach_activity_values", "attach_endpoint_values"),
    ("valid_activity_sessions", "valid_endpoint_sessions"),
    ("one_sided_zero_sessions", "invalid_endpoint_sessions"),
    ("active_bars", "positive_reversal_scores"),
    ("joint_zero_bars", "zero_endpoint_returns"),
    (
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "volume", "amount")',
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "close")',
    ),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign108_features_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)

Campaign108FeatureError = _generated["Campaign108FeatureError"]

from scripts import (
    a_share_three_day_walkforward_campaign107_features as c107,
)  # noqa: E402


DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_108_no_return_preregistration_20260808.json"
)


def _order_digest(items: Iterable[dict[str, str]]) -> str:
    return _generated["_json_digest"](
        [[item["name"], item["score_direction"]] for item in items]
    )


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = [dict(item) for item in c107.reconstruct_comparisons()]
    if (
        len(items) != NUMERIC_COMPARATOR_COUNT
        or _order_digest(items) != NUMERIC_COMPARATOR_ORDER_SHA256
    ):
        raise Campaign108FeatureError("Campaign108 numeric comparison order changed")
    return items


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = [dict(item) for item in c107.reconstruct_complete_definitions()]
    items.append({"name": c107.FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != COMPLETE_DEFINITION_COUNT
        or _order_digest(items) != COMPLETE_DEFINITION_ORDER_SHA256
        or items[-1] != {"name": c107.FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign108FeatureError("Campaign108 complete definition order changed")
    return items


def load_protocol(path: Path | None = None) -> dict[str, Any]:
    target = DEFAULT_PROTOCOL if path is None else path.expanduser().resolve()
    _generated["_require"](target, PROTOCOL_SHA256, "protocol")
    report = _generated["bindings"].validate_record(
        target, data_root=_generated["DEFAULT_DATA_ROOT"]
    )
    if report.get("all_bindings_passed") is not True:
        raise Campaign108FeatureError("Campaign108 protocol binding failed")
    spec = json.loads(target.read_text(encoding="utf-8"))
    inputs = spec.get("authoritative_inputs") or {}
    policy = inputs.get("numeric_policy_v67") or {}
    candidate = spec.get("candidate") or {}
    grid = candidate.get("source_grid") or {}
    endpoint = candidate.get("endpoint_semantics") or {}
    snapshot = spec.get("source_snapshot_contract") or {}
    comparisons = spec.get("comparison_contract") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    gates = list(spec.get("ordered_no_return_gates") or [])
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign108_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign108_minute_source_candidate_comparator_daily_price_or_return_values"
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
        and candidate.get("formula") == "-tanh(log(close_15_00 / close_09_31))"
        and tuple(candidate.get("source_projection") or ()) == RAW_COLUMNS
        and grid.get("accepted_rows_required") == _generated["SOURCE_BAR_COUNT"]
        and grid.get("selected_rows_for_formula") == 2
        and grid.get("standalone_09_30_preserved_but_not_loaded_for_formula") is True
        and grid.get("first_endpoint") == "09:31"
        and grid.get("last_endpoint") == "15:00"
        and grid.get("full_continuous_grid_validated_before_endpoint_selection") is True
        and endpoint.get("finite_strictly_positive_selected_closes_required") is True
        and endpoint.get("intermediate_close_values_used_after_grid_validation")
        is False
        and endpoint.get("strictly_monotone_in_negative_net_return") is True
        and candidate.get("valid_range") == [-1.0, 1.0]
        and snapshot.get("data_root") == str(_generated["DEFAULT_DATA_ROOT"])
        and snapshot.get("joint_clean_manifest_sha256")
        == _generated["CLEAN_MANIFEST_SHA256"]
        and snapshot.get("joint_clean_dataset_sha256")
        == _generated["CLEAN_DATASET_SHA256"]
        and snapshot.get("expected_partitions") == _generated["EXPECTED_PARTITIONS"]
        and snapshot.get("expected_rows") == _generated["EXPECTED_ROWS"]
        and snapshot.get("output_run_id") == OUTPUT_RUN_ID
        and comparisons.get(
            "complete_v67_semantic_definition_count_reviewed_before_values"
        )
        == COMPLETE_DEFINITION_COUNT
        and comparisons.get("numeric_comparator_count") == NUMERIC_COMPARATOR_COUNT
        and comparisons.get("numeric_comparator_order_sha256")
        == NUMERIC_COMPARATOR_ORDER_SHA256
        and [item.get("gate") for item in gates] == [1, 2, 3]
        and finite.get("trial_count") == 1
        and finite.get("trial_id")
        == "wf108_intraday_continuous_session_net_return_reversal_240m_single_higher"
        and finite.get("factor") == FACTOR_NAME
        and finite.get("direction") == "higher"
        and boundary.get("campaign108_source_rows_read_before_freeze") is False
        and boundary.get("campaign108_candidate_values_computed_or_read_before_freeze")
        is False
        and boundary.get("campaign108_comparison_values_read_before_freeze") is False
        and boundary.get("historical_daily_price_fields_read_before_freeze") == []
        and boundary.get("historical_forward_returns_read_before_freeze") is False
        and boundary.get("provider_request_issued") is False
        and len(reconstruct_comparisons()) == NUMERIC_COMPARATOR_COUNT
        and len(reconstruct_complete_definitions()) == COMPLETE_DEFINITION_COUNT
    ):
        raise Campaign108FeatureError("Campaign108 protocol semantics changed")
    return spec


def extract_continuous_session_net_return_reversal(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign108FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    empty = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "continuous_session_net_return_reversal": pd.Series(dtype="float64"),
        }
    )
    quality = {
        "source_rows": 0,
        "source_sessions": 0,
        "valid_endpoint_sessions": 0,
        "invalid_numeric_sessions": 0,
        "invalid_endpoint_sessions": 0,
        "positive_reversal_scores": 0,
        "zero_endpoint_returns": 0,
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
        raise Campaign108FeatureError(f"raw minute identity changed for {symbol}")
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
        raise Campaign108FeatureError(f"raw minute grid changed for {symbol}")
    endpoints = work.loc[
        work["minute_code"].isin([FIRST_ENDPOINT_CODE, LAST_ENDPOINT_CODE]),
        ["trade_date", "minute_code", "close"],
    ].copy()
    endpoints["minute_code"] = pd.Categorical(
        endpoints["minute_code"],
        categories=[FIRST_ENDPOINT_CODE, LAST_ENDPOINT_CODE],
        ordered=True,
    )
    endpoints = endpoints.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(counts.index).normalize()
    if len(endpoints) != len(dates) * 2:
        raise Campaign108FeatureError(f"endpoint minute grid changed for {symbol}")
    close = endpoints["close"].to_numpy(dtype=np.float64).reshape(len(dates), 2)
    valid = np.isfinite(close).all(axis=1) & (close > 0.0).all(axis=1)
    scores = np.full(len(dates), np.nan, dtype=np.float64)
    scores[valid] = -np.tanh(np.log(close[valid, 1] / close[valid, 0]))
    eligible = np.isfinite(scores) & (scores >= -1.0) & (scores <= 1.0)
    scores[~eligible] = np.nan
    return pd.DataFrame(
        {"trade_date": dates, "continuous_session_net_return_reversal": scores}
    ), {
        "source_rows": int(len(work)),
        "source_sessions": int(len(dates)),
        "valid_endpoint_sessions": int(eligible.sum()),
        "invalid_numeric_sessions": int((~valid).sum()),
        "invalid_endpoint_sessions": int((~valid).sum()),
        "positive_reversal_scores": int((scores[eligible] > 0.0).sum()),
        "zero_endpoint_returns": int((scores[eligible] == 0.0).sum()),
    }


def validate_value_semantics(frame: pd.DataFrame) -> tuple[int, int]:
    if tuple(frame.columns) != tuple(_generated["OUTPUT_COLUMNS"]):
        raise Campaign108FeatureError("Campaign108 output columns changed")
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"].astype(bool)
    if (
        values[eligible].isna().any()
        or ((values[eligible] < -1.0) | (values[eligible] > 1.0)).any()
        or values[~eligible].notna().any()
    ):
        raise Campaign108FeatureError("Campaign108 value semantics changed")
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
    "extract_continuous_session_net_return_reversal": extract_continuous_session_net_return_reversal,
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
