#!/usr/bin/env python3
"""Build Campaign262's frozen cumulative amount-schedule snapshot."""

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
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign261_features.py"
)
BASE_BUILDER_SHA256 = "b21e325d84b1153b4b3f5ad314e19434a8056b2e2f955e751500a6424f3108c2"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _file_sha256(BASE_BUILDER) != BASE_BUILDER_SHA256:
    raise RuntimeError("frozen Campaign261 feature builder changed")


FACTOR_NAME = "intraday_amount_schedule_uniformity_240m"
FACTOR_SHORT_NAME = "amount_schedule_uniformity"
FACTOR_FORMULA = (
    "one minus normalized cumulative-L1 distance of the exact 240-bar "
    "amount-share clock distribution from the fixed uniform schedule"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "amount")
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign262_feature_library_v1"
)
PROTOCOL_SHA256 = "cf4ea3e0c39f31207e175891321b3eb5cc8a49391cb3022d87cd98e80cc282d0"
MECHANISM_AUDIT_SHA256 = (
    "13f5f04c050be5e5d9c26c8f42e0b3a36bfe6d4508b6bb0d8389146d8e9cf6f6"
)
NUMERIC_POLICY_SHA256 = (
    "fb2a95214db33763c6b14fe132c0c29eafad9a15ee4ea8fdafb58de3e2eb9fed"
)
NUMERIC_COMPARATOR_COUNT = 142
NUMERIC_COMPARATOR_ORDER_SHA256 = (
    "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf"
)
PRIOR_COMPLETE_DEFINITION_COUNT = 160
PRIOR_COMPLETE_DEFINITION_ORDER_SHA256 = (
    "2c431b3c9f9e772f7fdccab2625d671f8a836809710e78af8cb43d6d4e66cc0c"
)
COMPLETE_DEFINITION_COUNT = 161
COMPLETE_DEFINITION_ORDER_SHA256 = (
    "e387d2865b8957a933c522c2cd9ae890612ab45993307f97693ec73fa5288144"
)


_source = BASE_BUILDER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign261", "Campaign262"),
    ("campaign261", "campaign262"),
    ("campaign_261", "campaign_262"),
    (
        "normalized Lorenz-Gini amount inequality",
        "cumulative amount-schedule uniformity",
    ),
    (
        "normalized-Lorenz-Gini-amount-inequality",
        "cumulative-amount-schedule-uniformity",
    ),
    ("intraday_amount_lorenz_gini_240m", FACTOR_NAME),
    ("amount_lorenz_gini", FACTOR_SHORT_NAME),
    ("extract_amount_lorenz_gini", "extract_amount_schedule_uniformity"),
    ("compute_amount_lorenz_gini", "compute_amount_schedule_uniformity"),
    ("attach_gini_values", "attach_schedule_values"),
    ("valid_gini_sessions", "valid_schedule_sessions"),
):
    _source = _source.replace(_old, _new)

_namespace: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign262_features_generated",
}
exec(compile(_source, str(BASE_BUILDER), "exec"), _namespace)  # noqa: S102

_engine: dict[str, Any] = _namespace["_engine"]
Campaign262FeatureError = _namespace["Campaign262FeatureError"]

from scripts import (
    a_share_three_day_walkforward_campaign261_features as c261,
)  # noqa: E402
from scripts import (
    a_share_three_day_walkforward_campaign262_formula as formula,
)  # noqa: E402


DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_262_no_return_preregistration_20260816.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_262_implementation_freeze_v3_20260816.json"
)
FEATURE_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign262_features.py"
)
FORMULA_PATH = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign262_formula.py"
)
FORMULA_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign262_formula.py"
)


def _order_digest(items: Iterable[dict[str, str]]) -> str:
    return _engine["_json_digest"](
        [[item["name"], item["score_direction"]] for item in items]
    )


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = [dict(item) for item in c261.reconstruct_comparisons()]
    if (
        len(items) != NUMERIC_COMPARATOR_COUNT
        or _order_digest(items) != NUMERIC_COMPARATOR_ORDER_SHA256
    ):
        raise Campaign262FeatureError("Campaign262 numeric comparison order changed")
    return items


def reconstruct_prior_complete_definitions() -> list[dict[str, str]]:
    items = [dict(item) for item in c261.reconstruct_complete_definitions()]
    if (
        len(items) != PRIOR_COMPLETE_DEFINITION_COUNT
        or _order_digest(items) != PRIOR_COMPLETE_DEFINITION_ORDER_SHA256
    ):
        raise Campaign262FeatureError("Campaign262 prior definition order changed")
    return items


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = reconstruct_prior_complete_definitions()
    items.append({"name": FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != COMPLETE_DEFINITION_COUNT
        or _order_digest(items) != COMPLETE_DEFINITION_ORDER_SHA256
    ):
        raise Campaign262FeatureError("Campaign262 complete definition order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    target = path.expanduser().resolve()
    if target != DEFAULT_PROTOCOL.resolve():
        raise Campaign262FeatureError("Campaign262 protocol path changed")
    try:
        spec = formula.load_protocol(target)
    except formula.Campaign262FormulaError as exc:
        raise Campaign262FeatureError(str(exc)) from exc
    inputs = spec.get("authoritative_inputs") or {}
    for binding in inputs.values():
        bound = Path(str(binding.get("path", "")))
        if not bound.is_absolute():
            bound = REPO_ROOT / bound
        if not bound.is_file() or _file_sha256(bound) != binding.get("sha256"):
            raise Campaign262FeatureError(
                f"Campaign262 authoritative input changed: {bound}"
            )
    source = spec.get("source_snapshot_contract") or {}
    comparison = spec.get("comparison_contract") or {}
    candidate = spec.get("candidate") or {}
    exact = candidate.get("exact_formula") or {}
    gates = list(spec.get("ordered_no_return_gates") or [])
    if not (
        (inputs.get("numeric_policy_v404") or {}).get("sha256") == NUMERIC_POLICY_SHA256
        and (inputs.get("mechanism_overlap_audit") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and source.get("data_root") == str(_engine["DEFAULT_DATA_ROOT"])
        and source.get("raw_manifest_sha256") == _engine["RAW_MANIFEST_SHA256"]
        and source.get("joint_clean_manifest_sha256")
        == _engine["CLEAN_MANIFEST_SHA256"]
        and source.get("joint_clean_dataset_sha256") == _engine["CLEAN_DATASET_SHA256"]
        and source.get("expected_partitions") == _engine["EXPECTED_PARTITIONS"]
        and source.get("expected_rows") == _engine["EXPECTED_ROWS"]
        and source.get("output_run_id") == OUTPUT_RUN_ID
        and candidate.get("source_projection") == list(RAW_COLUMNS)
        and exact.get("distance") == "D=sum_{k=0}^{238} abs(F_k-U_k)."
        and exact.get("score") == "1-D/119.5."
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
        raise Campaign262FeatureError("Campaign262 protocol bindings changed")
    return spec


def extract_amount_schedule_uniformity(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign262FeatureError(
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
        "valid_schedule_sessions": 0,
        "invalid_numeric_sessions": 0,
        "nonpositive_total_amount_sessions": 0,
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
        raise Campaign262FeatureError(f"raw minute identity changed for {symbol}")
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
        raise Campaign262FeatureError(f"raw minute grid changed for {symbol}")
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
        raise Campaign262FeatureError(f"continuous minute grid changed for {symbol}")
    amount = (
        selected["amount"]
        .to_numpy(dtype=np.float64)
        .reshape(len(dates), formula.PROFILE_POSITIONS)
    )
    scores, eligible, formula_quality = formula.compute_amount_schedule_uniformity(
        amount
    )
    return pd.DataFrame({"trade_date": dates, FACTOR_SHORT_NAME: scores}), {
        "source_rows": int(len(work)),
        "source_sessions": int(len(dates)),
        "valid_schedule_sessions": int(eligible.sum()),
        "invalid_numeric_sessions": int(
            formula_quality["nonfinite_amount_rows"]
            + formula_quality["negative_amount_rows"]
        ),
        "nonpositive_total_amount_sessions": int(
            formula_quality["nonpositive_total_amount_rows"]
        ),
        "bound_violation_sessions": int(formula_quality["bound_violation_rows"]),
        "positive_amount_bars": int((amount[eligible] > 0.0).sum()),
        "zero_amount_bars": int((amount[eligible] == 0.0).sum()),
    }


def finalize_feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = (*_engine["IDENTITY_COLUMNS"], FACTOR_SHORT_NAME)
    if not set(required).issubset(frame.columns):
        raise Campaign262FeatureError("Campaign262 attached frame columns changed")
    work = frame.copy()
    values = pd.to_numeric(work[FACTOR_SHORT_NAME], errors="coerce")
    eligible = np.isfinite(values) & (values >= 0.0) & (values <= 1.0)
    work[FACTOR_NAME] = values.where(eligible)
    work[f"{FACTOR_NAME}_eligible"] = eligible.astype(bool)
    return work


def validate_value_semantics(frame: pd.DataFrame) -> tuple[int, int]:
    if tuple(frame.columns) != _engine["OUTPUT_COLUMNS"]:
        raise Campaign262FeatureError("Campaign262 output columns changed")
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"].astype(bool)
    valid = np.isfinite(values) & (values >= 0.0) & (values <= 1.0)
    if not eligible.equals(valid.astype(bool)) or values[~eligible].notna().any():
        raise Campaign262FeatureError("Campaign262 value semantics changed")
    return int(len(frame)), int(eligible.sum())


def _validate_implementation_freeze() -> dict[str, Any]:
    target = DEFAULT_IMPLEMENTATION_FREEZE.resolve()
    if not target.is_file():
        raise Campaign262FeatureError("Campaign262 implementation freeze missing")
    record = json.loads(target.read_text(encoding="utf-8"))
    code = record.get("code") or {}
    tests = record.get("tests") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign262_implementation_freeze"
        and record.get("status")
        == "formula_contract_frozen_before_values_and_diagnostic_recovery_frozen_after_failed_unpublished_build"
        and record.get("protocol_sha256") == PROTOCOL_SHA256
        and code.get("formula_sha256") == _file_sha256(FORMULA_PATH)
        and code.get("feature_builder_sha256") == _file_sha256(Path(__file__))
        and tests.get("formula_test_sha256") == _file_sha256(FORMULA_TEST_PATH)
        and tests.get("feature_test_sha256") == _file_sha256(FEATURE_TEST_PATH)
        and tests.get("exit_code") == 0
        and tests.get("passed") >= 14
        and record.get("complete_definition_count") == COMPLETE_DEFINITION_COUNT
        and record.get("complete_definition_order_sha256")
        == COMPLETE_DEFINITION_ORDER_SHA256
        and record.get("numeric_comparator_count") == NUMERIC_COMPARATOR_COUNT
        and record.get("numeric_comparator_order_sha256")
        == NUMERIC_COMPARATOR_ORDER_SHA256
        and boundary.get("historical_source_rows_read") is True
        and boundary.get(
            "historical_source_rows_read_before_protocol_and_formula_freeze"
        )
        is False
        and boundary.get("candidate_values_computed_in_failed_partial_build") is True
        and boundary.get("candidate_values_published_or_inspected") is False
        and boundary.get("comparator_values_read") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign262FeatureError("Campaign262 implementation freeze changed")
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
    "extract_amount_schedule_uniformity": extract_amount_schedule_uniformity,
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
attach_schedule_values = _engine["attach_amount_values"]
empty_output_frame = _engine["empty_output_frame"]
output_root = _engine["output_root"]
build_snapshot = _engine["build_snapshot"]
verify_snapshot_files = _engine["verify_snapshot_files"]
status = _engine["status"]
main = _engine["main"]


if __name__ == "__main__":
    raise SystemExit(main())
