#!/usr/bin/env python3
"""Build Campaign121's frozen terminal-level first-attainment snapshot."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign110_features.py"
)
TEMPLATE_SHA256 = "319b1b350caee4fceb11fe7893f99c9c659abaca29bdbf043474a11790287319"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _file_sha256(TEMPLATE_PATH) != TEMPLATE_SHA256:
    raise RuntimeError("frozen Campaign110 feature-builder template changed")


FACTOR_NAME = "intraday_terminal_close_direction_first_attainment_240m"
FACTOR_SHORT_NAME = "terminal_close_direction_first_attainment"
FACTOR_FORMULA = (
    "zero on exact neutral terminal displacement; otherwise "
    "(240-first directional attainment index of close_240)/239"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "open", "close")
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign121_feature_library_v1"
)
PROTOCOL_SHA256 = "9ca39c1b9daac5f8cec11523ee1992b71c105a6c71547e4805d7301be93f0399"
MECHANISM_AUDIT_SHA256 = (
    "a3703f5a9f152f3c5d300637737f72d9ac564985c6f91978f965ec1414f376fc"
)
NUMERIC_POLICY_SHA256 = (
    "deeea64d88987f3c99c87228a7be9d78e57c8bae45d08e4d85d5f709c1bffb73"
)
NUMERIC_COMPARATOR_COUNT = 138
NUMERIC_COMPARATOR_ORDER_SHA256 = (
    "e917d9f832bda02f87c0a7e02a26127629146318de826684e8dfd6432fc20a3b"
)
COMPLETE_DEFINITION_COUNT = 147
COMPLETE_DEFINITION_ORDER_SHA256 = (
    "3f3756a4128011d9cd718e97d23ee3b1c78022433b269c75bd715f304a055bf0"
)
POSITION_SPAN = 239


_source = TEMPLATE_PATH.read_text(encoding="utf-8")
for _old, _new in (
    (
        "intraday_open_reference_directional_occupancy_240m",
        FACTOR_NAME,
    ),
    ("open_reference_directional_occupancy", FACTOR_SHORT_NAME),
    ("open_reference_occupancy", "terminal_first_attainment"),
    ("Campaign110", "Campaign121"),
    ("campaign110", "campaign121"),
    ("campaign_110", "campaign_121"),
    (
        "75999c8aad35d7197b233c578990bb95c0a8d87ca25821cdd2859ef56f210f56",
        PROTOCOL_SHA256,
    ),
    (
        "09927e6834169b4c0d94146870d00c49076364533ebfed0e801f7edf6177f7fb",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "e526abc1a3c6f8c0d0cbbf74538efe4ee184d5b0ac812e60ee177d83d2fb33c6",
        NUMERIC_POLICY_SHA256,
    ),
    ("NUMERIC_COMPARATOR_COUNT = 133", "NUMERIC_COMPARATOR_COUNT = 138"),
    (
        "b6fbcaffbc83699155d4291ebaa6a1b0066e4801b82b634cf27dfa6cee89eefc",
        NUMERIC_COMPARATOR_ORDER_SHA256,
    ),
    ("COMPLETE_DEFINITION_COUNT = 139", "COMPLETE_DEFINITION_COUNT = 147"),
    (
        "eb505226fcf171151c5a4ead04c08369136be1af88d64c1710f4ab34d83d83e0",
        COMPLETE_DEFINITION_ORDER_SHA256,
    ),
    (
        "a_share_three_day_walkforward_campaign109_features as c109",
        "a_share_three_day_walkforward_campaign120_features as c120",
    ),
    ("c109.", "c120."),
    ("FIXED_DENOMINATOR = 240", "FIXED_DENOMINATOR = 239"),
    ("20260808.json", "20260814.json"),
):
    if _old not in _source:
        raise RuntimeError(f"Campaign121 feature transformation token absent: {_old!r}")
    _source = _source.replace(_old, _new)


_implementation: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign121_features_implementation",
}
exec(compile(_source, str(TEMPLATE_PATH), "exec"), _implementation)
_base_generated: dict[str, Any] = _implementation["_base_generated"]

Campaign121FeatureError = _implementation["Campaign121FeatureError"]

from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign120_features as c120,
)
from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign121_formula as formula,
)


DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_121_no_return_preregistration_20260814.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_121_no_return_implementation_freeze_v2_20260814.json"
)
FEATURE_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign121_features.py"
)
FORMULA_PATH = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign121_formula.py"
)
FORMULA_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign121_formula.py"
)
AUDIT_RUNNER_PATH = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign121_no_return_audit.py"
)
AUDIT_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign121_no_return_audit.py"
)


def _order_digest(items: Iterable[dict[str, str]]) -> str:
    return _base_generated["_json_digest"](
        [[item["name"], item["score_direction"]] for item in items]
    )


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = [dict(item) for item in c120.reconstruct_comparisons()]
    items.append({"name": c120.FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != NUMERIC_COMPARATOR_COUNT
        or _order_digest(items) != NUMERIC_COMPARATOR_ORDER_SHA256
        or items[-1] != {"name": c120.FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign121FeatureError("Campaign121 numeric comparison order changed")
    return items


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = [dict(item) for item in c120.reconstruct_complete_definitions()]
    items.append({"name": FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != COMPLETE_DEFINITION_COUNT
        or _order_digest(items) != COMPLETE_DEFINITION_ORDER_SHA256
        or items[-1] != {"name": FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign121FeatureError("Campaign121 complete definition order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    target = path.expanduser().resolve()
    try:
        spec = formula.load_protocol(target)
    except formula.Campaign121FormulaError as exc:
        raise Campaign121FeatureError(str(exc)) from exc
    report = _base_generated["bindings"].validate_record(
        target, data_root=_implementation["DEFAULT_DATA_ROOT"]
    )
    if report.get("all_bindings_passed") is not True:
        raise Campaign121FeatureError("Campaign121 protocol binding failed")
    inputs = spec.get("authoritative_inputs") or {}
    policy = inputs.get("numeric_policy_v113") or {}
    snapshot = spec.get("source_snapshot_contract") or {}
    comparisons = spec.get("comparison_contract") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    gates = list(spec.get("ordered_no_return_gates") or [])
    if not (
        policy.get("sha256") == NUMERIC_POLICY_SHA256
        and policy.get("complete_definition_count") == 146
        and policy.get("complete_definition_order_sha256")
        == c120.COMPLETE_DEFINITION_ORDER_SHA256
        and policy.get("numeric_comparator_count") == NUMERIC_COMPARATOR_COUNT
        and policy.get("numeric_comparator_order_sha256")
        == NUMERIC_COMPARATOR_ORDER_SHA256
        and (inputs.get("mechanism_overlap_audit") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and snapshot.get("data_root") == str(_implementation["DEFAULT_DATA_ROOT"])
        and snapshot.get("joint_clean_manifest_sha256")
        == _implementation["CLEAN_MANIFEST_SHA256"]
        and snapshot.get("joint_clean_dataset_sha256")
        == _implementation["CLEAN_DATASET_SHA256"]
        and snapshot.get("expected_partitions")
        == _implementation["EXPECTED_PARTITIONS"]
        and snapshot.get("expected_rows") == _implementation["EXPECTED_ROWS"]
        and snapshot.get("output_run_id") == OUTPUT_RUN_ID
        and comparisons.get("numeric_comparator_count") == NUMERIC_COMPARATOR_COUNT
        and comparisons.get("numeric_comparator_order_sha256")
        == NUMERIC_COMPARATOR_ORDER_SHA256
        and comparisons.get("candidate_appended_complete_definition_count")
        == COMPLETE_DEFINITION_COUNT
        and comparisons.get("candidate_appended_complete_definition_order_sha256")
        == COMPLETE_DEFINITION_ORDER_SHA256
        and [item.get("gate") for item in gates] == [1, 2, 3]
        and finite.get("trial_count") == 1
        and finite.get("factor") == FACTOR_NAME
        and finite.get("direction") == "higher"
        and len(reconstruct_comparisons()) == NUMERIC_COMPARATOR_COUNT
        and len(reconstruct_complete_definitions()) == COMPLETE_DEFINITION_COUNT
    ):
        raise Campaign121FeatureError("Campaign121 protocol semantics changed")
    return spec


def compute_terminal_close_direction_first_attainment(
    opens: np.ndarray, closes: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, int]]:
    try:
        return formula.compute_terminal_close_direction_first_attainment(opens, closes)
    except formula.Campaign121FormulaError as exc:
        raise Campaign121FeatureError(str(exc)) from exc


def extract_terminal_close_direction_first_attainment(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign121FeatureError(
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
        "valid_terminal_first_attainment_sessions": 0,
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
        raise Campaign121FeatureError(f"raw minute identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    distinct = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].nunique()
    if (
        counts.empty
        or not counts.eq(_implementation["SOURCE_BAR_COUNT"]).all()
        or not distinct.eq(_implementation["SOURCE_BAR_COUNT"]).all()
        or not work["minute_code"].isin(_implementation["SOURCE_MINUTE_CODE_SET"]).all()
    ):
        raise Campaign121FeatureError(f"raw minute grid changed for {symbol}")
    selected = work.loc[
        work["minute_code"].isin(_implementation["CONTINUOUS_MINUTE_CODE_SET"]),
        ["trade_date", "minute_code", "open", "close"],
    ].copy()
    selected["minute_code"] = pd.Categorical(
        selected["minute_code"],
        categories=_implementation["CONTINUOUS_MINUTE_CODES"],
        ordered=True,
    )
    selected = selected.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(counts.index).normalize()
    if len(selected) != len(dates) * _implementation["SELECTED_BAR_COUNT"]:
        raise Campaign121FeatureError(f"continuous minute grid changed for {symbol}")
    opens = selected["open"].to_numpy(dtype=np.float64).reshape(len(dates), 240)
    closes = selected["close"].to_numpy(dtype=np.float64).reshape(len(dates), 240)
    values, eligible, tau, formula_quality = (
        compute_terminal_close_direction_first_attainment(opens, closes)
    )
    return pd.DataFrame({"trade_date": dates, FACTOR_SHORT_NAME: values}), {
        "source_rows": int(len(work)),
        "source_sessions": int(len(dates)),
        "valid_terminal_first_attainment_sessions": int(eligible.sum()),
        "invalid_anchor_or_close_sessions": formula_quality[
            "invalid_anchor_or_close_rows"
        ],
        "invalid_fixed_denominator_sessions": 0,
        "nonzero_reference_state_bars": int((tau > 0).sum()),
        "equal_reference_bars": formula_quality["neutral_terminal_rows"],
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
        raise Campaign121FeatureError("Campaign121 output columns changed")
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"].astype(bool)
    scaled = values[eligible] * POSITION_SPAN
    if (
        values[eligible].isna().any()
        or ((values[eligible] < 0.0) | (values[eligible] > 1.0)).any()
        or not np.allclose(scaled, np.rint(scaled), rtol=0.0, atol=1e-12)
        or values[~eligible].notna().any()
    ):
        raise Campaign121FeatureError("Campaign121 value semantics changed")
    return int(len(frame)), int(eligible.sum())


def validate_implementation_freeze() -> dict[str, Any]:
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign121FeatureError("Campaign121 implementation freeze v2 is absent")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    frozen = record.get("frozen_implementation") or {}
    parent = record.get("supersedes_without_rewriting") or {}
    verification = record.get("synthetic_verification") or {}
    boundary = record.get("research_boundary") or {}
    expected = {
        "formula": (FORMULA_PATH, formula._sha256(FORMULA_PATH)),
        "feature_builder": (Path(__file__).resolve(), _file_sha256(Path(__file__))),
        "coverage_audit": (AUDIT_RUNNER_PATH, _file_sha256(AUDIT_RUNNER_PATH)),
        "formula_test": (FORMULA_TEST_PATH, _file_sha256(FORMULA_TEST_PATH)),
        "feature_test": (FEATURE_TEST_PATH, _file_sha256(FEATURE_TEST_PATH)),
        "coverage_audit_test": (
            AUDIT_TEST_PATH,
            _file_sha256(AUDIT_TEST_PATH),
        ),
    }
    observed_ok = all(
        (frozen.get(name) or {}).get("path")
        == str(path.resolve().relative_to(REPO_ROOT.resolve()))
        and (frozen.get(name) or {}).get("sha256") == digest
        for name, (path, digest) in expected.items()
    )
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign121_no_return_implementation_freeze"
        and record.get("status")
        == "formula_builder_coverage_audit_and_tests_frozen_before_source_values_v2"
        and parent.get("path")
        == "docs/a_share_three_day_walkforward_campaign_121_no_return_implementation_freeze_20260814.json"
        and parent.get("sha256")
        == "de142a6b47f9fba49947a077bd141e3a5b8a108b1ad8b5ccf42ec103af66ca8f"
        and (record.get("authoritative_inputs") or {})
        .get("preregistration", {})
        .get("sha256")
        == PROTOCOL_SHA256
        and observed_ok
        and (record.get("frozen_semantics") or {}).get("numeric_comparator_count")
        == NUMERIC_COMPARATOR_COUNT
        and (record.get("frozen_semantics") or {}).get(
            "numeric_comparator_order_sha256"
        )
        == NUMERIC_COMPARATOR_ORDER_SHA256
        and (record.get("frozen_semantics") or {}).get(
            "complete_definition_order_sha256"
        )
        == COMPLETE_DEFINITION_ORDER_SHA256
        and verification.get("pytest") == "14 passed"
        and verification.get("black") == "passed"
        and verification.get("ruff") == "passed"
        and boundary.get("source_rows_read_before_freeze") is False
        and boundary.get("candidate_values_computed_or_read_before_freeze") is False
        and boundary.get("comparator_values_read_before_freeze") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign121FeatureError("Campaign121 implementation freeze v2 changed")
    return record


for _name, _value in {
    "FACTOR_NAME": FACTOR_NAME,
    "FACTOR_SHORT_NAME": FACTOR_SHORT_NAME,
    "FACTOR_FORMULA": FACTOR_FORMULA,
    "RAW_COLUMNS": RAW_COLUMNS,
    "OUTPUT_RUN_ID": OUTPUT_RUN_ID,
    "DEFAULT_PROTOCOL": DEFAULT_PROTOCOL,
    "DEFAULT_IMPLEMENTATION_FREEZE": DEFAULT_IMPLEMENTATION_FREEZE,
    "FEATURE_TEST_PATH": FEATURE_TEST_PATH,
    "FORMULA_PATH": FORMULA_PATH,
    "FORMULA_TEST_PATH": FORMULA_TEST_PATH,
    "AUDIT_RUNNER_PATH": AUDIT_RUNNER_PATH,
    "AUDIT_TEST_PATH": AUDIT_TEST_PATH,
    "PROTOCOL_SHA256": PROTOCOL_SHA256,
    "MECHANISM_AUDIT_SHA256": MECHANISM_AUDIT_SHA256,
    "NUMERIC_POLICY_SHA256": NUMERIC_POLICY_SHA256,
    "NUMERIC_COMPARATOR_COUNT": NUMERIC_COMPARATOR_COUNT,
    "NUMERIC_COMPARATOR_ORDER_SHA256": NUMERIC_COMPARATOR_ORDER_SHA256,
    "COMPLETE_DEFINITION_COUNT": COMPLETE_DEFINITION_COUNT,
    "COMPLETE_DEFINITION_ORDER_SHA256": COMPLETE_DEFINITION_ORDER_SHA256,
    "FIXED_DENOMINATOR": POSITION_SPAN,
    "POSITION_SPAN": POSITION_SPAN,
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
    "compute_terminal_close_direction_first_attainment": compute_terminal_close_direction_first_attainment,
    "extract_terminal_close_direction_first_attainment": extract_terminal_close_direction_first_attainment,
    "validate_value_semantics": validate_value_semantics,
    "_validate_implementation_freeze": validate_implementation_freeze,
}.items():
    _implementation[_name] = _value
    _base_generated[_name] = _value


DEFAULT_DATA_ROOT = _implementation["DEFAULT_DATA_ROOT"]
OUTPUT_COLUMNS = _implementation["OUTPUT_COLUMNS"]
EXPECTED_ROWS = _implementation["EXPECTED_ROWS"]
EXPECTED_PARTITIONS = _implementation["EXPECTED_PARTITIONS"]
CLEAN_MANIFEST_SHA256 = _implementation["CLEAN_MANIFEST_SHA256"]
CLEAN_DATASET_SHA256 = _implementation["CLEAN_DATASET_SHA256"]
SOURCE_BAR_COUNT = _implementation["SOURCE_BAR_COUNT"]
SELECTED_BAR_COUNT = _implementation["SELECTED_BAR_COUNT"]
CONTINUOUS_MINUTE_CODES = _implementation["CONTINUOUS_MINUTE_CODES"]
CONTINUOUS_MINUTE_CODE_SET = _implementation["CONTINUOUS_MINUTE_CODE_SET"]
SOURCE_MINUTE_CODE_SET = _implementation["SOURCE_MINUTE_CODE_SET"]
IDENTITY_COLUMNS = _implementation["IDENTITY_COLUMNS"]
bindings = _implementation["bindings"]
source = _implementation["source"]
attach_terminal_first_attainment_values = _implementation[
    "attach_terminal_first_attainment_values"
]
finalize_feature_frame = _implementation["finalize_feature_frame"]
empty_output_frame = _implementation["empty_output_frame"]
output_root = _implementation["output_root"]
build_snapshot = _implementation["build_snapshot"]
verify_snapshot_files = _implementation["verify_snapshot_files"]
_validate_implementation_freeze = validate_implementation_freeze
_sha256 = _implementation["_sha256"]
status = _implementation["status"]
