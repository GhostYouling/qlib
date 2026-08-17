#!/usr/bin/env python3
"""Build Campaign116's frozen local minute factor snapshot without returns."""

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


FACTOR_NAME = "intraday_amount_conditioned_directional_persistence_spread_236p"
FACTOR_SHORT_NAME = "amount_conditioned_directional_persistence_spread"
FACTOR_FORMULA = (
    "0.5 times the difference between mean directional-persistence state in "
    "strictly-above-daily-median endpoint-amount pairs and ordinary-amount "
    "pairs over 118 morning plus 118 afternoon adjacent-return pairs"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "close", "amount")
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign116_feature_library_v1"
)
PROTOCOL_SHA256 = "d47d4f1b8d6d7742c17eb82712a85a1dbe8dbb6e8f44e0ff9190e36ef7115c2c"
MECHANISM_AUDIT_SHA256 = (
    "fbebbb18226c36d45f97ae896e1a53e274c2cddccdbe5ed3cf50ef9b48009843"
)
NUMERIC_POLICY_SHA256 = (
    "18ab42ee095db886b77e72601d01161ee851cfcf94ccab5efeb715d1cb043787"
)
NUMERIC_COMPARATOR_COUNT = 134
NUMERIC_COMPARATOR_ORDER_SHA256 = (
    "31d788db467f558a0ac538315343090f1b3ad4cb27a26136a49ebaa88b2fdbf2"
)
PRIOR_COMPLETE_DEFINITION_COUNT = 141
PRIOR_COMPLETE_DEFINITION_ORDER_SHA256 = (
    "ccab6e3d9d81b0a02d4ff178fdd442b26a1e68e3655e1c6f5b2fcb28cd4a4559"
)
COMPLETE_DEFINITION_COUNT = 142
COMPLETE_DEFINITION_ORDER_SHA256 = (
    "ed61b10f3acb939c10ae5759f33aafde377cc921dd99c642300603b50a4851c5"
)


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign105", "Campaign116"),
    ("campaign105", "campaign116"),
    ("campaign_105", "campaign_116"),
    ("activity-clock occupancy", "amount-conditioned directional persistence"),
    (
        "``datetime,symbol,provider,volume,amount``",
        "``datetime,symbol,provider,close,amount``",
    ),
    ("It never reads a price,", "It never reads a daily price,"),
    ("intraday_active_trading_bar_share_240m", FACTOR_NAME),
    ("active_trading_bar_share", FACTOR_SHORT_NAME),
    ("attach_activity_values", "attach_persistence_values"),
    ("valid_activity_sessions", "valid_persistence_sessions"),
    ("invalid_numeric_sessions", "invalid_close_or_amount_sessions"),
    ("one_sided_zero_sessions", "insufficient_group_support_sessions"),
    ("active_bars", "informative_high_pairs"),
    ("joint_zero_bars", "informative_ordinary_pairs"),
    ("activity_rule", "persistence_rule"),
    ("minimum_active_bar_count", "minimum_group_support"),
    ("activity_magnitude_used", "endpoint_amount_used"),
    (
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "volume", "amount")',
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "close", "amount")',
    ),
):
    _source = _source.replace(_old, _new)
_source = _source.replace("{FACTOR_NAME: [0.0, 1.0]}", "{FACTOR_NAME: [-1.0, 1.0]}")
_source = _source.replace(
    "values.ge(0.0) & values.le(1.0)",
    "values.ge(-1.0) & values.le(1.0)",
)
_source = _source.replace('"minimum_group_support": 0', '"minimum_group_support": 30')
_source = _source.replace(
    '"positive_total_activity_required": False',
    '"positive_total_activity_required": True',
)
_source = _source.replace(
    '"endpoint_amount_used": False',
    '"endpoint_amount_used": True',
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign116_features_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)

Campaign116FeatureError = _generated["Campaign116FeatureError"]

from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign110_features as c110,
)
from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign116_formula as formula,
)


DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_116_no_return_preregistration_20260812.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_116_no_return_implementation_freeze_v2_20260812.json"
)
FEATURE_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign116_features.py"
)
FORMULA_PATH = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign116_formula.py"
FORMULA_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign116_formula.py"
)


def _order_digest(items: Iterable[dict[str, str]]) -> str:
    return _generated["_json_digest"](
        [[item["name"], item["score_direction"]] for item in items]
    )


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = [dict(item) for item in c110.reconstruct_comparisons()]
    items.append({"name": c110.FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != NUMERIC_COMPARATOR_COUNT
        or _order_digest(items) != NUMERIC_COMPARATOR_ORDER_SHA256
    ):
        raise Campaign116FeatureError("Campaign116 numeric comparison order changed")
    return items


def reconstruct_prior_complete_definitions() -> list[dict[str, str]]:
    items = [dict(item) for item in c110.reconstruct_complete_definitions()]
    items.extend(
        [
            {"name": c110.FACTOR_NAME, "score_direction": "higher"},
            {
                "name": "official_exchange_enforcement_recovery_session_age_60sessions",
                "score_direction": "higher",
            },
        ]
    )
    if (
        len(items) != PRIOR_COMPLETE_DEFINITION_COUNT
        or _order_digest(items) != PRIOR_COMPLETE_DEFINITION_ORDER_SHA256
    ):
        raise Campaign116FeatureError("Campaign116 prior definition order changed")
    return items


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = reconstruct_prior_complete_definitions()
    items.append({"name": FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != COMPLETE_DEFINITION_COUNT
        or _order_digest(items) != COMPLETE_DEFINITION_ORDER_SHA256
    ):
        raise Campaign116FeatureError("Campaign116 complete definition order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    target = path.expanduser().resolve()
    if target != DEFAULT_PROTOCOL.resolve():
        raise Campaign116FeatureError("Campaign116 protocol path changed")
    try:
        spec = formula.load_protocol(target)
    except formula.Campaign116FormulaError as exc:
        raise Campaign116FeatureError(str(exc)) from exc
    inputs = spec.get("authoritative_inputs") or {}
    policy = inputs.get("numeric_policy_v98") or {}
    snapshot = spec.get("source_snapshot_contract") or {}
    comparisons = spec.get("comparison_contract") or {}
    gates = list(spec.get("ordered_no_return_gates") or [])
    if not (
        policy.get("complete_definition_count") == PRIOR_COMPLETE_DEFINITION_COUNT
        and policy.get("complete_definition_order_sha256")
        == PRIOR_COMPLETE_DEFINITION_ORDER_SHA256
        and policy.get("numeric_comparator_count") == NUMERIC_COMPARATOR_COUNT
        and policy.get("numeric_comparator_order_sha256")
        == NUMERIC_COMPARATOR_ORDER_SHA256
        and (inputs.get("mechanism_support_audit") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and snapshot.get("data_root") == str(_generated["DEFAULT_DATA_ROOT"])
        and snapshot.get("joint_clean_manifest_sha256")
        == _generated["CLEAN_MANIFEST_SHA256"]
        and snapshot.get("joint_clean_dataset_sha256")
        == _generated["CLEAN_DATASET_SHA256"]
        and snapshot.get("expected_partitions") == _generated["EXPECTED_PARTITIONS"]
        and snapshot.get("expected_rows") == _generated["EXPECTED_ROWS"]
        and snapshot.get("output_run_id") == OUTPUT_RUN_ID
        and snapshot.get("provider_request_allowed") is False
        and comparisons.get("numeric_comparator_count") == NUMERIC_COMPARATOR_COUNT
        and comparisons.get("numeric_comparator_order_sha256")
        == NUMERIC_COMPARATOR_ORDER_SHA256
        and [item.get("gate") for item in gates] == [1, 2, 3]
        and len(reconstruct_prior_complete_definitions())
        == PRIOR_COMPLETE_DEFINITION_COUNT
        and len(reconstruct_comparisons()) == NUMERIC_COMPARATOR_COUNT
    ):
        raise Campaign116FeatureError("Campaign116 protocol bindings changed")
    return spec


def extract_amount_conditioned_directional_persistence_spread(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign116FeatureError(
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
        "valid_persistence_sessions": 0,
        "invalid_close_or_amount_sessions": 0,
        "insufficient_group_support_sessions": 0,
        "informative_high_pairs": 0,
        "informative_ordinary_pairs": 0,
    }
    if raw.empty:
        return empty, quality
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
        raise Campaign116FeatureError(f"raw minute identity changed for {symbol}")
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
        raise Campaign116FeatureError(f"raw minute grid changed for {symbol}")
    selected = work.loc[
        work["minute_code"].isin(_generated["CONTINUOUS_MINUTE_CODE_SET"]),
        ["trade_date", "minute_code", "close", "amount"],
    ].copy()
    selected["minute_code"] = pd.Categorical(
        selected["minute_code"],
        categories=_generated["CONTINUOUS_MINUTE_CODES"],
        ordered=True,
    )
    selected = selected.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(counts.index).normalize()
    if len(selected) != len(dates) * formula.SELECTED_BAR_COUNT:
        raise Campaign116FeatureError(f"continuous minute grid changed for {symbol}")
    close = selected["close"].to_numpy(dtype=np.float64).reshape(len(dates), 240)
    amount = selected["amount"].to_numpy(dtype=np.float64).reshape(len(dates), 240)
    values, eligible, high_support, ordinary_support, *_ = (
        formula.compute_amount_conditioned_directional_persistence_spread(close, amount)
    )
    source_valid = (
        np.isfinite(close).all(axis=1)
        & (close > 0.0).all(axis=1)
        & np.isfinite(amount).all(axis=1)
        & (amount >= 0.0).all(axis=1)
        & (amount.sum(axis=1) > 0.0)
    )
    enough_support = (
        (high_support >= formula.MINIMUM_GROUP_SUPPORT)
        & (ordinary_support >= formula.MINIMUM_GROUP_SUPPORT)
    )
    return pd.DataFrame(
        {"trade_date": dates, FACTOR_SHORT_NAME: values}
    ), {
        "source_rows": int(len(work)),
        "source_sessions": int(len(dates)),
        "valid_persistence_sessions": int(eligible.sum()),
        "invalid_close_or_amount_sessions": int((~source_valid).sum()),
        "insufficient_group_support_sessions": int(
            (source_valid & ~enough_support).sum()
        ),
        "informative_high_pairs": int(high_support[source_valid].sum()),
        "informative_ordinary_pairs": int(ordinary_support[source_valid].sum()),
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
        raise Campaign116FeatureError("Campaign116 output columns changed")
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"].astype(bool)
    if (
        values[eligible].isna().any()
        or ((values[eligible] < -1.0) | (values[eligible] > 1.0)).any()
        or values[~eligible].notna().any()
    ):
        raise Campaign116FeatureError("Campaign116 value semantics changed")
    return int(len(frame)), int(eligible.sum())


def _validate_implementation_freeze() -> dict[str, Any]:
    path = DEFAULT_IMPLEMENTATION_FREEZE.resolve()
    if not path.is_file():
        raise Campaign116FeatureError("Campaign116 implementation freeze is absent")
    record = json.loads(path.read_text(encoding="utf-8"))
    frozen = record.get("frozen_implementation") or {}
    tests = record.get("synthetic_verification") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign116_no_return_implementation_freeze"
        and record.get("status")
        == "snapshot_builder_and_synthetic_semantics_frozen_before_historical_source_values"
        and (record.get("authoritative_inputs") or {})
        .get("no_return_preregistration", {})
        .get("sha256")
        == PROTOCOL_SHA256
        and frozen.get("pure_formula_sha256") == _file_sha256(FORMULA_PATH)
        and frozen.get("snapshot_builder_sha256")
        == _file_sha256(Path(__file__).resolve())
        and tests.get("formula_test_sha256") == _file_sha256(FORMULA_TEST_PATH)
        and tests.get("feature_test_sha256") == _file_sha256(FEATURE_TEST_PATH)
        and tests.get("exit_code") == 0
        and tests.get("passed") == 10
        and boundary.get("campaign116_historical_source_rows_read") is False
        and boundary.get("campaign116_candidate_values_computed_or_read") is False
        and boundary.get("campaign116_comparator_values_read") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign116FeatureError("Campaign116 implementation freeze changed")
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
    "extract_amount_conditioned_directional_persistence_spread": extract_amount_conditioned_directional_persistence_spread,
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
attach_persistence_values = _generated["attach_persistence_values"]
finalize_feature_frame = _generated["finalize_feature_frame"]
empty_output_frame = _generated["empty_output_frame"]
output_root = _generated["output_root"]
build_snapshot = _generated["build_snapshot"]
verify_snapshot_files = _generated["verify_snapshot_files"]
status = _generated["status"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
