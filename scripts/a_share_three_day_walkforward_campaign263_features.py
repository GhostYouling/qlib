#!/usr/bin/env python3
"""Build Campaign263's frozen amount-profile spectral-entropy snapshot."""

# ruff: noqa: E402

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_BUILDER = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign262_features.py"
)
BASE_BUILDER_SHA256 = "b7499a518042a998e269be953084ad939915f4b87a21e0f53ce6fcb17a25e8a7"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _file_sha256(BASE_BUILDER) != BASE_BUILDER_SHA256:
    raise RuntimeError("frozen Campaign262 feature builder changed")


FACTOR_NAME = "intraday_amount_profile_spectral_entropy_60f"
FACTOR_SHORT_NAME = "amount_profile_spectral_entropy"
FACTOR_FORMULA = (
    "normalized Shannon entropy of pooled all-frequency power from the two "
    "independently normalized 120-bar amount profiles"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "amount")
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign263_feature_library_v1"
)
PROTOCOL_SHA256 = "07c5875034f3e26e6a98f01e3329b3cf1d3d287d119c9358e32e5a2e76b5b924"
MECHANISM_AUDIT_SHA256 = (
    "f43dbea09fbf3a8cbc553bfd04edf313209ea029c62e14f5e2c46ca31f851b87"
)
NUMERIC_POLICY_SHA256 = (
    "3b303b088e87ee96a45379f11870fd9349a6d70e188e5448d71df9ce0a89cfe6"
)
NUMERIC_COMPARATOR_COUNT = 142
NUMERIC_COMPARATOR_ORDER_SHA256 = (
    "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf"
)
PRIOR_COMPLETE_DEFINITION_COUNT = 161
PRIOR_COMPLETE_DEFINITION_ORDER_SHA256 = (
    "e387d2865b8957a933c522c2cd9ae890612ab45993307f97693ec73fa5288144"
)
COMPLETE_DEFINITION_COUNT = 162
COMPLETE_DEFINITION_ORDER_SHA256 = (
    "974f2c1f16a85eb43a0bd1e8db768dbe120cd8826c1754d5f220bf9f1d4a3ea0"
)


_source = BASE_BUILDER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign262", "Campaign263"),
    ("campaign262", "campaign263"),
    ("campaign_262", "campaign_263"),
    ("20260816", "20260816"),
    ("intraday_amount_schedule_uniformity_240m", FACTOR_NAME),
    ("amount_schedule_uniformity", FACTOR_SHORT_NAME),
    ("extract_amount_schedule_uniformity", "extract_amount_profile_spectral_entropy"),
    ("compute_amount_schedule_uniformity", "compute_amount_profile_spectral_entropy"),
    ("attach_schedule_values", "attach_spectral_values"),
    ("valid_schedule_sessions", "valid_spectral_sessions"),
    ("nonpositive_total_amount_sessions", "nonpositive_half_total_sessions"),
    ("nonpositive_total_amount_rows", "nonpositive_half_total_rows"),
    ("cumulative amount-schedule uniformity", "amount-profile spectral entropy"),
    ("cumulative-amount-schedule-uniformity", "amount-profile-spectral-entropy"),
    (
        "tushare_stk_mins_1m_2019_2025_ea0cbb8f_walkforward_campaign262_feature_library_v1",
        OUTPUT_RUN_ID,
    ),
):
    _source = _source.replace(_old, _new)

_namespace: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign263_features_generated",
}
exec(compile(_source, str(BASE_BUILDER), "exec"), _namespace)  # noqa: S102

_engine: dict[str, Any] = _namespace["_engine"]
Campaign263FeatureError = _namespace["Campaign263FeatureError"]

from scripts import a_share_three_day_walkforward_campaign262_features as c262
from scripts import a_share_three_day_walkforward_campaign263_formula as formula


DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_263_no_return_preregistration_20260816.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_263_implementation_freeze_v4_20260816.json"
)
FEATURE_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign263_features.py"
)
FORMULA_PATH = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign263_formula.py"
FORMULA_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign263_formula.py"
)


def _order_digest(items: Iterable[dict[str, str]]) -> str:
    return _engine["_json_digest"](
        [[item["name"], item["score_direction"]] for item in items]
    )


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = [dict(item) for item in c262.reconstruct_comparisons()]
    if (
        len(items) != NUMERIC_COMPARATOR_COUNT
        or _order_digest(items) != NUMERIC_COMPARATOR_ORDER_SHA256
    ):
        raise Campaign263FeatureError("Campaign263 numeric comparison order changed")
    return items


def reconstruct_prior_complete_definitions() -> list[dict[str, str]]:
    items = [dict(item) for item in c262.reconstruct_complete_definitions()]
    if (
        len(items) != PRIOR_COMPLETE_DEFINITION_COUNT
        or _order_digest(items) != PRIOR_COMPLETE_DEFINITION_ORDER_SHA256
    ):
        raise Campaign263FeatureError("Campaign263 prior definition order changed")
    return items


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = reconstruct_prior_complete_definitions()
    items.append({"name": FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != COMPLETE_DEFINITION_COUNT
        or _order_digest(items) != COMPLETE_DEFINITION_ORDER_SHA256
    ):
        raise Campaign263FeatureError("Campaign263 complete definition order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    target = path.expanduser().resolve()
    if target != DEFAULT_PROTOCOL.resolve():
        raise Campaign263FeatureError("Campaign263 protocol path changed")
    try:
        spec = formula.load_protocol(target)
    except formula.Campaign263FormulaError as exc:
        raise Campaign263FeatureError(str(exc)) from exc
    for binding in (spec.get("authoritative_inputs") or {}).values():
        bound = Path(str(binding.get("path", "")))
        if not bound.is_absolute():
            bound = REPO_ROOT / bound
        if not bound.is_file() or _file_sha256(bound) != binding.get("sha256"):
            raise Campaign263FeatureError(
                f"Campaign263 authoritative input changed: {bound}"
            )
    source = spec.get("source_snapshot_contract") or {}
    comparison = spec.get("comparison_contract") or {}
    candidate = spec.get("candidate") or {}
    gates = list(spec.get("ordered_no_return_gates") or [])
    if not (
        source.get("data_root") == str(_engine["DEFAULT_DATA_ROOT"])
        and source.get("raw_manifest_sha256") == _engine["RAW_MANIFEST_SHA256"]
        and source.get("joint_clean_manifest_sha256")
        == _engine["CLEAN_MANIFEST_SHA256"]
        and source.get("joint_clean_dataset_sha256")
        == _engine["CLEAN_DATASET_SHA256"]
        and source.get("expected_partitions") == _engine["EXPECTED_PARTITIONS"]
        and source.get("expected_rows") == _engine["EXPECTED_ROWS"]
        and source.get("output_run_id") == OUTPUT_RUN_ID
        and candidate.get("source_projection") == list(RAW_COLUMNS)
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
        raise Campaign263FeatureError("Campaign263 protocol bindings changed")
    return spec


def extract_amount_profile_spectral_entropy(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign263FeatureError(
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
        "valid_spectral_sessions": 0,
        "invalid_numeric_sessions": 0,
        "nonpositive_total_amount_sessions": 0,
        "nonpositive_half_total_sessions": 0,
        "zero_non_dc_power_sessions": 0,
        "bound_violation_sessions": 0,
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
        raise Campaign263FeatureError(f"raw minute identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    distinct = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].nunique()
    if (
        counts.empty
        or not counts.eq(_engine["SOURCE_BAR_COUNT"]).all()
        or not distinct.eq(_engine["SOURCE_BAR_COUNT"]).all()
        or not work["minute_code"].isin(_engine["SOURCE_MINUTE_CODE_SET"]).all()
    ):
        raise Campaign263FeatureError(f"raw minute grid changed for {symbol}")
    selected = work.loc[
        work["minute_code"].isin(_engine["CONTINUOUS_MINUTE_CODE_SET"]),
        ["trade_date", "minute_code", "amount"],
    ].copy()
    selected["minute_code"] = pd.Categorical(
        selected["minute_code"],
        categories=_engine["CONTINUOUS_MINUTE_CODES"],
        ordered=True,
    )
    selected = selected.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(counts.index).normalize()
    if len(selected) != len(dates) * formula.PROFILE_POSITIONS:
        raise Campaign263FeatureError(f"continuous minute grid changed for {symbol}")
    amount = (
        selected["amount"]
        .to_numpy(dtype=np.float64)
        .reshape(len(dates), formula.PROFILE_POSITIONS)
    )
    scores, eligible, formula_quality = (
        formula.compute_amount_profile_spectral_entropy(amount)
    )
    return pd.DataFrame({"trade_date": dates, FACTOR_SHORT_NAME: scores}), {
        "source_rows": int(len(work)),
        "source_sessions": int(len(dates)),
        "valid_spectral_sessions": int(eligible.sum()),
        "invalid_numeric_sessions": int(
            formula_quality["nonfinite_amount_rows"]
            + formula_quality["negative_amount_rows"]
        ),
        "nonpositive_half_total_sessions": int(
            formula_quality["nonpositive_half_total_rows"]
        ),
        "nonpositive_total_amount_sessions": int(
            formula_quality["nonpositive_half_total_rows"]
        ),
        "zero_non_dc_power_sessions": int(
            formula_quality["zero_non_dc_power_rows"]
        ),
        "bound_violation_sessions": int(formula_quality["bound_violation_rows"]),
        "positive_amount_bars": int((amount[eligible] > 0.0).sum()),
        "zero_amount_bars": int((amount[eligible] == 0.0).sum()),
    }


def finalize_feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = (*_engine["IDENTITY_COLUMNS"], FACTOR_SHORT_NAME)
    if not set(required).issubset(frame.columns):
        raise Campaign263FeatureError("Campaign263 attached frame columns changed")
    work = frame.copy()
    values = pd.to_numeric(work[FACTOR_SHORT_NAME], errors="coerce")
    eligible = np.isfinite(values) & (values >= 0.0) & (values <= 1.0)
    work[FACTOR_NAME] = values.where(eligible)
    work[f"{FACTOR_NAME}_eligible"] = eligible.astype(bool)
    return work


def validate_value_semantics(frame: pd.DataFrame) -> tuple[int, int]:
    if tuple(frame.columns) != _engine["OUTPUT_COLUMNS"]:
        raise Campaign263FeatureError("Campaign263 output columns changed")
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"].astype(bool)
    valid = np.isfinite(values) & (values >= 0.0) & (values <= 1.0)
    if not eligible.equals(valid.astype(bool)) or values[~eligible].notna().any():
        raise Campaign263FeatureError("Campaign263 value semantics changed")
    return int(len(frame)), int(eligible.sum())


def _validate_implementation_freeze() -> dict[str, Any]:
    target = DEFAULT_IMPLEMENTATION_FREEZE.resolve()
    if not target.is_file():
        raise Campaign263FeatureError("Campaign263 implementation freeze missing")
    record = json.loads(target.read_text(encoding="utf-8"))
    code = record.get("code") or {}
    tests = record.get("tests") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign263_implementation_freeze"
        and record.get("status")
        == "partition_index_passthrough_repair_frozen_before_same_formula_recovery"
        and record.get("protocol_sha256") == PROTOCOL_SHA256
        and code.get("formula_sha256") == _file_sha256(FORMULA_PATH)
        and code.get("feature_builder_sha256") == _file_sha256(Path(__file__))
        and tests.get("formula_test_sha256") == _file_sha256(FORMULA_TEST_PATH)
        and tests.get("feature_test_sha256") == _file_sha256(FEATURE_TEST_PATH)
        and tests.get("exit_code") == 0
        and tests.get("passed") >= 18
        and record.get("complete_definition_count") == COMPLETE_DEFINITION_COUNT
        and record.get("complete_definition_order_sha256")
        == COMPLETE_DEFINITION_ORDER_SHA256
        and record.get("numeric_comparator_count") == NUMERIC_COMPARATOR_COUNT
        and record.get("numeric_comparator_order_sha256")
        == NUMERIC_COMPARATOR_ORDER_SHA256
        and boundary.get("historical_source_rows_read") is True
        and boundary.get("candidate_or_comparator_values_read") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign263FeatureError("Campaign263 implementation freeze changed")
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
    "extract_amount_profile_spectral_entropy": extract_amount_profile_spectral_entropy,
    "finalize_feature_frame": finalize_feature_frame,
    "validate_value_semantics": validate_value_semantics,
    "_validate_implementation_freeze": _validate_implementation_freeze,
}.items():
    _engine[_name] = _value


DEFAULT_DATA_ROOT = _engine["DEFAULT_DATA_ROOT"]
OUTPUT_COLUMNS = _engine["OUTPUT_COLUMNS"]
EXPECTED_ROWS = _engine["EXPECTED_ROWS"]
EXPECTED_PARTITIONS = _engine["EXPECTED_PARTITIONS"]
CLEAN_MANIFEST_SHA256 = _engine["CLEAN_MANIFEST_SHA256"]
CLEAN_DATASET_SHA256 = _engine["CLEAN_DATASET_SHA256"]
RAW_MANIFEST_SHA256 = _engine["RAW_MANIFEST_SHA256"]
SOURCE_BAR_COUNT = _engine["SOURCE_BAR_COUNT"]
CONTINUOUS_MINUTE_CODES = _engine["CONTINUOUS_MINUTE_CODES"]
CONTINUOUS_MINUTE_CODE_SET = _engine["CONTINUOUS_MINUTE_CODE_SET"]
SOURCE_MINUTE_CODE_SET = _engine["SOURCE_MINUTE_CODE_SET"]
IDENTITY_COLUMNS = _engine["IDENTITY_COLUMNS"]
attach_spectral_values = _engine["attach_amount_values"]
empty_output_frame = _engine["empty_output_frame"]
output_root = _engine["output_root"]
build_snapshot = _engine["build_snapshot"]
verify_snapshot_files = _engine["verify_snapshot_files"]
status = _engine["status"]
main = _engine["main"]


if __name__ == "__main__":
    raise SystemExit(main())
