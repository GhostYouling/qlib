#!/usr/bin/env python3
"""Build Campaign146's frozen return-amount cross-spectral phase snapshot."""

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


FACTOR_NAME = "intraday_return_amount_cross_spectral_phase_lead_59f"
FACTOR_SHORT_NAME = "return_amount_cross_spectral_phase_lead"
FACTOR_FORMULA = (
    "equal mean of two fixed-half power-weighted signed cross-spectral phase "
    "lead scores using all 59 positive frequencies of demeaned signed log-close "
    "returns and destination log1p transaction amount"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "close", "amount")
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign146_feature_library_v1"
)
PROTOCOL_SHA256 = "7ad8c1bd0ab56521609bf02fcd2f4effa9fb49753ee5703fb3bf3d55c1527e47"
MECHANISM_AUDIT_SHA256 = (
    "0e9c9db630b3efa4b7a08a59e992d26c9502b61fe8c2ebdc95ad232572883d5c"
)
NUMERIC_POLICY_SHA256 = (
    "b9835d1d3ab888f50060707e22fdb5784bd8a433b1c16aba6473162b96be288b"
)
NUMERIC_COMPARATOR_COUNT = 141
NUMERIC_COMPARATOR_ORDER_SHA256 = (
    "ec1aebcb939ad516c58037a36a4aaadd4ad8b2abbd3c884705895c58da85a2ee"
)
PRIOR_COMPLETE_DEFINITION_COUNT = 154
PRIOR_COMPLETE_DEFINITION_ORDER_SHA256 = (
    "dcea4c75bb9194ea2e522d803409e4005cf0185fe87c84f6f9810dbe51de2f75"
)
COMPLETE_DEFINITION_COUNT = 155
COMPLETE_DEFINITION_ORDER_SHA256 = (
    "2e4114edb26fa3aaebd145ef07fe4e2ac9c5d9dc4586cf70ff61c20e39b954ba"
)


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign105", "Campaign146"),
    ("campaign105", "campaign146"),
    ("campaign_105", "campaign_146"),
    ("activity-clock occupancy", "return-amount cross-spectral phase lead"),
    (
        "``datetime,symbol,provider,volume,amount``",
        "``datetime,symbol,provider,close,amount``",
    ),
    ("intraday_active_trading_bar_share_240m", FACTOR_NAME),
    ("active_trading_bar_share", FACTOR_SHORT_NAME),
    (
        "extract_active_trading_bar_share",
        "extract_return_amount_cross_spectral_phase_lead",
    ),
    ("attach_activity_values", "attach_phase_values"),
    ("valid_activity_sessions", "valid_phase_sessions"),
    ("invalid_numeric_sessions", "invalid_close_or_amount_sessions"),
    ("one_sided_zero_sessions", "nonpositive_spectral_denominator_halves"),
    ("active_bars", "positive_frequency_observations"),
    ("joint_zero_bars", "zero_destination_amount_observations"),
    ("activity_rule", "phase_rule"),
    ("minimum_active_bar_count", "positive_frequency_count_per_half"),
    (
        "positive_total_activity_required",
        "positive_half_spectral_denominators_required",
    ),
    (
        "activity_magnitude_used",
        "signed_return_and_amount_magnitudes_used",
    ),
    (
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "volume", "amount")',
        'RAW_COLUMNS = ("datetime", "symbol", "provider", "close", "amount")',
    ),
    ("{FACTOR_NAME: [0.0, 1.0]}", "{FACTOR_NAME: [-1.0, 1.0]}"),
):
    _source = _source.replace(_old, _new)
_source = _source.replace(
    '"positive_frequency_count_per_half": 0',
    '"positive_frequency_count_per_half": 59',
)
_source = _source.replace(
    '"positive_half_spectral_denominators_required": False',
    '"positive_half_spectral_denominators_required": True',
)
_source = _source.replace(
    '"signed_return_and_amount_magnitudes_used": False',
    '"signed_return_and_amount_magnitudes_used": True',
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign146_features_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)

Campaign146FeatureError = _generated["Campaign146FeatureError"]

from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign145_features as c145,
)
from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign146_formula as formula,
)


DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_146_no_return_preregistration_20260814.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_146_no_return_implementation_freeze_20260814.json"
)
FEATURE_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign146_features.py"
)
FORMULA_PATH = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign146_formula.py"
)
FORMULA_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign146_formula.py"
)
AUDIT_RUNNER_PATH = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign146_no_return_audit.py"
)
AUDIT_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign146_no_return_audit.py"
)


def _order_digest(items: Iterable[dict[str, str]]) -> str:
    return _generated["_json_digest"](
        [[item["name"], item["score_direction"]] for item in items]
    )


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = [dict(item) for item in c145.reconstruct_comparisons()]
    if (
        len(items) != NUMERIC_COMPARATOR_COUNT
        or _order_digest(items) != NUMERIC_COMPARATOR_ORDER_SHA256
    ):
        raise Campaign146FeatureError("Campaign146 numeric comparison order changed")
    return items


def reconstruct_prior_complete_definitions() -> list[dict[str, str]]:
    items = [dict(item) for item in c145.reconstruct_complete_definitions()]
    if (
        len(items) != PRIOR_COMPLETE_DEFINITION_COUNT
        or _order_digest(items) != PRIOR_COMPLETE_DEFINITION_ORDER_SHA256
    ):
        raise Campaign146FeatureError("Campaign146 prior definition order changed")
    return items


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = reconstruct_prior_complete_definitions()
    items.append({"name": FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != COMPLETE_DEFINITION_COUNT
        or _order_digest(items) != COMPLETE_DEFINITION_ORDER_SHA256
    ):
        raise Campaign146FeatureError("Campaign146 complete definition order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    target = path.expanduser().resolve()
    if target != DEFAULT_PROTOCOL.resolve():
        raise Campaign146FeatureError("Campaign146 protocol path changed")
    try:
        spec = formula.load_protocol(target)
    except formula.Campaign146FormulaError as exc:
        raise Campaign146FeatureError(str(exc)) from exc
    inputs = spec.get("authoritative_inputs") or {}
    policy = inputs.get("numeric_policy_v194") or {}
    snapshot = spec.get("source_snapshot_contract") or {}
    comparisons = spec.get("comparison_contract") or {}
    gates = list(spec.get("ordered_no_return_gates") or [])
    if not (
        policy.get("sha256") == NUMERIC_POLICY_SHA256
        and policy.get("complete_definition_count") == PRIOR_COMPLETE_DEFINITION_COUNT
        and policy.get("complete_definition_order_sha256")
        == PRIOR_COMPLETE_DEFINITION_ORDER_SHA256
        and policy.get("numeric_comparator_count") == NUMERIC_COMPARATOR_COUNT
        and policy.get("numeric_comparator_order_sha256")
        == NUMERIC_COMPARATOR_ORDER_SHA256
        and (inputs.get("mechanism_overlap_audit") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and snapshot.get("data_root") == str(_generated["DEFAULT_DATA_ROOT"])
        and snapshot.get("raw_manifest_sha256") == _generated["RAW_MANIFEST_SHA256"]
        and snapshot.get("joint_clean_manifest_sha256")
        == _generated["CLEAN_MANIFEST_SHA256"]
        and snapshot.get("joint_clean_dataset_sha256")
        == _generated["CLEAN_DATASET_SHA256"]
        and snapshot.get("expected_partitions") == _generated["EXPECTED_PARTITIONS"]
        and snapshot.get("expected_rows") == _generated["EXPECTED_ROWS"]
        and snapshot.get("output_run_id") == OUTPUT_RUN_ID
        and snapshot.get("provider_request_allowed") is False
        and snapshot.get("credential_required") is False
        and comparisons.get("candidate_appended_complete_definition_count")
        == COMPLETE_DEFINITION_COUNT
        and comparisons.get("candidate_appended_complete_definition_order_sha256")
        == COMPLETE_DEFINITION_ORDER_SHA256
        and comparisons.get("numeric_comparator_count") == NUMERIC_COMPARATOR_COUNT
        and comparisons.get("numeric_comparator_order_sha256")
        == NUMERIC_COMPARATOR_ORDER_SHA256
        and [item.get("gate") for item in gates] == [1, 2, 3]
        and len(reconstruct_complete_definitions()) == COMPLETE_DEFINITION_COUNT
        and len(reconstruct_comparisons()) == NUMERIC_COMPARATOR_COUNT
    ):
        raise Campaign146FeatureError("Campaign146 protocol bindings changed")
    return spec


def extract_return_amount_cross_spectral_phase_lead(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign146FeatureError(
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
        "valid_phase_sessions": 0,
        "invalid_close_or_amount_sessions": 0,
        "nonpositive_spectral_denominator_halves": 0,
        "positive_frequency_observations": 0,
        "zero_destination_amount_observations": 0,
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
        raise Campaign146FeatureError(f"raw minute identity changed for {symbol}")
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
        raise Campaign146FeatureError(f"raw minute grid changed for {symbol}")
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
        raise Campaign146FeatureError(f"continuous minute grid changed for {symbol}")
    close = selected["close"].to_numpy(dtype=np.float64).reshape(len(dates), 240)
    amount = selected["amount"].to_numpy(dtype=np.float64).reshape(len(dates), 240)
    values, eligible, _half_phases, formula_quality = (
        formula.compute_return_amount_cross_spectral_phase_lead(close, amount)
    )
    source_valid = (
        np.isfinite(close).all(axis=1)
        & (close > 0.0).all(axis=1)
        & np.isfinite(amount).all(axis=1)
        & (amount >= 0.0).all(axis=1)
    )
    destination_amount = np.concatenate((amount[:, 1:120], amount[:, 121:240]), axis=1)
    denominator_failures = (
        formula_quality["morning_nonpositive_spectral_denominator_rows"]
        + formula_quality["afternoon_nonpositive_spectral_denominator_rows"]
    )
    return pd.DataFrame({"trade_date": dates, FACTOR_SHORT_NAME: values}), {
        "source_rows": int(len(work)),
        "source_sessions": int(len(dates)),
        "valid_phase_sessions": int(eligible.sum()),
        "invalid_close_or_amount_sessions": int((~source_valid).sum()),
        "nonpositive_spectral_denominator_halves": int(denominator_failures),
        "positive_frequency_observations": int(
            eligible.sum() * formula.POSITIVE_FREQUENCY_COUNT * 2
        ),
        "zero_destination_amount_observations": int(
            ((destination_amount == 0.0) & source_valid[:, None]).sum()
        ),
    }


def finalize_feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = (*_generated["IDENTITY_COLUMNS"], FACTOR_SHORT_NAME)
    if not set(required).issubset(frame.columns):
        raise Campaign146FeatureError("Campaign146 input columns changed")
    work = frame.copy()
    values = pd.to_numeric(work[FACTOR_SHORT_NAME], errors="coerce")
    eligible = np.isfinite(values) & values.ge(-1.0) & values.le(1.0)
    work[FACTOR_NAME] = values.where(eligible)
    work[f"{FACTOR_NAME}_eligible"] = eligible
    work["provider"] = "tushare"
    return work


def validate_value_semantics(frame: pd.DataFrame) -> tuple[int, int]:
    expected = (
        "trade_date",
        "symbol",
        "provider",
        FACTOR_NAME,
        f"{FACTOR_NAME}_eligible",
    )
    if tuple(frame.columns) != expected:
        raise Campaign146FeatureError("Campaign146 output columns changed")
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"].astype(bool)
    if (
        values[eligible].isna().any()
        or ((values[eligible] < -1.0) | (values[eligible] > 1.0)).any()
        or values[~eligible].notna().any()
    ):
        raise Campaign146FeatureError("Campaign146 value semantics changed")
    return int(len(frame)), int(eligible.sum())


def _validate_implementation_freeze() -> dict[str, Any]:
    path = DEFAULT_IMPLEMENTATION_FREEZE.resolve()
    if not path.is_file():
        raise Campaign146FeatureError("Campaign146 implementation freeze is absent")
    record = json.loads(path.read_text(encoding="utf-8"))
    frozen = record.get("frozen_implementation") or {}
    tests = record.get("synthetic_verification") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign146_no_return_implementation_freeze"
        and record.get("status")
        == "snapshot_builder_audit_runner_and_synthetic_semantics_frozen_before_historical_source_values"
        and (record.get("authoritative_inputs") or {})
        .get("no_return_preregistration", {})
        .get("sha256")
        == PROTOCOL_SHA256
        and frozen.get("pure_formula_sha256") == _file_sha256(FORMULA_PATH)
        and frozen.get("snapshot_builder_sha256")
        == _file_sha256(Path(__file__).resolve())
        and frozen.get("ordered_audit_runner_sha256") == _file_sha256(AUDIT_RUNNER_PATH)
        and tests.get("formula_test_sha256") == _file_sha256(FORMULA_TEST_PATH)
        and tests.get("feature_test_sha256") == _file_sha256(FEATURE_TEST_PATH)
        and tests.get("audit_test_sha256") == _file_sha256(AUDIT_TEST_PATH)
        and tests.get("exit_code") == 0
        and tests.get("passed") >= 12
        and boundary.get("campaign146_historical_source_rows_read") is False
        and boundary.get("campaign146_candidate_values_computed_or_read") is False
        and boundary.get("campaign146_comparator_values_read") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign146FeatureError("Campaign146 implementation freeze changed")
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
    "extract_return_amount_cross_spectral_phase_lead": extract_return_amount_cross_spectral_phase_lead,
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
attach_phase_values = _generated["attach_phase_values"]
empty_output_frame = _generated["empty_output_frame"]
output_root = _generated["output_root"]
build_snapshot = _generated["build_snapshot"]
verify_snapshot_files = _generated["verify_snapshot_files"]
status = _generated["status"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
