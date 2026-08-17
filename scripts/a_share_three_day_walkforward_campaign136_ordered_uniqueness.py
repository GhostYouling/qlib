#!/usr/bin/env python3
"""Run Campaign136's frozen all-140 ordered no-return uniqueness audit."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import a_share_three_day_walkforward_campaign132_design as design
from scripts import a_share_three_day_walkforward_campaign136_coverage_audit as coverage
from scripts import a_share_three_day_walkforward_campaign136_features as candidate
from scripts import a_share_three_day_walkforward_campaign136_formula as formula


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_136_ordered_numeric_uniqueness_protocol_20260814.json"
)
PROTOCOL_SHA256 = "c412e7b63229f7a21c5ead00650bf1f55117f0a8eb6143f4609df6103096a740"
COVERAGE_PATH = coverage.OUTPUT_PATH
COVERAGE_SHA256 = "f79402a136db11d0186c93cf5347174d1427879a0823f6be071c87e476ad66ac"
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_136_ordered_uniqueness_implementation_freeze_20260814.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign136_ordered_uniqueness.py"
)
OUTPUT_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_136/uniqueness/campaign136_ordered_uniqueness_audit.json"
)
DESIGN_MANIFEST_PATH = (
    Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
    / "derived/a_share/rich/tushare/minute_walkforward_campaign132_design_matrix"
    / "tushare_stk_mins_1m_2019_2025_ea0cbb8f_walkforward_campaign132_numeric140_design_v1"
    / "snapshot_manifest.json"
)
DESIGN_MANIFEST_SHA256 = (
    "043c17fea89f3b0956d643a7c6e3f4d73a11403b967213d2d57539a6a8316a49"
)
DESIGN_DATASET_SHA256 = (
    "12ce3a64b5e13581392ded9890e2064db4ccca3945da3eb8ad7752c95366a9fc"
)
CANDIDATE49_SIGNAL_LEDGER = coverage.CANDIDATE49_SIGNAL_LEDGER
CANDIDATE49_SIGNAL_LEDGER_SHA256 = coverage.CANDIDATE49_SIGNAL_LEDGER_SHA256
CANDIDATE49_EXECUTION_LEDGER = coverage.CANDIDATE49_EXECUTION_LEDGER
CANDIDATE49_EXECUTION_LEDGER_SHA256 = coverage.CANDIDATE49_EXECUTION_LEDGER_SHA256

EXPECTED_COMPARISON_COUNT = 140
EXPECTED_COMPARISON_ORDER_SHA256 = coverage.NUMERIC_COMPARATOR_ORDER_SHA256
EXPECTED_QUALITY_LISTING_CANDIDATE_ROWS = 1331759
MINIMUM_PAIRWISE_NAMES = 50
MINIMUM_PAIRWISE_SESSIONS = 100
MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION = 0.8


class Campaign136OrderedUniquenessError(RuntimeError):
    """Fail closed when an all-140 comparison invariant changes."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_file(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or file_sha256(path) != expected:
        raise Campaign136OrderedUniquenessError(f"Campaign136 {label} changed")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Campaign136OrderedUniquenessError(f"expected JSON object: {path}")
    return value


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def comparison_definitions() -> list[dict[str, str]]:
    try:
        items = [dict(item) for item in design.current_feature_order()]
    except design.Campaign132DesignError as exc:
        raise Campaign136OrderedUniquenessError(str(exc)) from exc
    if (
        len(items) != EXPECTED_COMPARISON_COUNT
        or design.json_digest(
            [[item["name"], item["score_direction"]] for item in items]
        )
        != EXPECTED_COMPARISON_ORDER_SHA256
    ):
        raise Campaign136OrderedUniquenessError("comparison order changed")
    return items


def load_protocol() -> dict[str, Any]:
    require_file(PROTOCOL_PATH, PROTOCOL_SHA256, "uniqueness protocol")
    spec = load_json(PROTOCOL_PATH)
    order = spec.get("comparison_order") or {}
    gate = spec.get("exact_gate") or {}
    boundary = spec.get("research_boundary") or {}
    definitions = comparison_definitions()
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign136_ordered_numeric_uniqueness_protocol"
        and spec.get("status")
        == "all_140_ordered_comparators_frozen_after_coverage_pass_before_any_comparator_value"
        and order.get("count") == len(definitions) == EXPECTED_COMPARISON_COUNT
        and order.get("order_sha256") == EXPECTED_COMPARISON_ORDER_SHA256
        and order.get("comparison_value_semantics")
        == "Precomputed frozen direction-normalized cross-sectional average-tie percentile ranks; each paired session is reranked with average ties before Spearman calculation."
        and order.get(
            "removal_reorder_subset_early_stop_or_candidate_specific_fill_allowed"
        )
        is False
        and gate.get("minimum_pairwise_names_per_session") == MINIMUM_PAIRWISE_NAMES
        and gate.get("minimum_pairwise_sessions_per_comparison")
        == MINIMUM_PAIRWISE_SESSIONS
        and gate.get("maximum_allowed_absolute_median_daily_rank_correlation")
        == MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION
        and gate.get("strict_inequality") is True
        and gate.get("all_140_must_pass") is True
        and gate.get("insufficient_overlap_fails_closed") is True
        and gate.get(
            "constant_candidate_or_comparator_session_is_not_a_qualifying_session"
        )
        is True
        and boundary.get("comparator_values_read_before_protocol") is False
        and boundary.get("numeric140_design_partition_values_read_before_protocol")
        is False
        and boundary.get("historical_daily_ohlcv_fields_read") == []
        and boundary.get("historical_forward_returns_read") is False
    ):
        raise Campaign136OrderedUniquenessError("uniqueness protocol semantics changed")
    return spec


def validate_design_manifest_metadata() -> dict[str, Any]:
    require_file(DESIGN_MANIFEST_PATH, DESIGN_MANIFEST_SHA256, "design manifest")
    manifest = load_json(DESIGN_MANIFEST_PATH)
    definitions = comparison_definitions()
    names = [item["name"] for item in definitions]
    files = list(manifest.get("files") or [])
    expected_columns = [
        "stock_day_key",
        *names,
        design.FINITE_COUNT_NAME,
        design.ELIGIBLE_NAME,
    ]
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign132_numeric140_design_snapshot"
        and manifest.get("status")
        == "immutable_design_ready_for_structural_audit_before_training_returns"
        and manifest.get("feature_count") == EXPECTED_COMPARISON_COUNT
        and manifest.get("feature_names") == names
        and manifest.get("feature_order_sha256") == EXPECTED_COMPARISON_ORDER_SHA256
        and manifest.get("rows") == EXPECTED_QUALITY_LISTING_CANDIDATE_ROWS
        and manifest.get("partitions") == len(files) == 7
        and manifest.get("dataset_sha256") == DESIGN_DATASET_SHA256
        and [int(item["year"]) for item in files] == list(range(2019, 2026))
        and manifest.get("component_values_read") is True
        and manifest.get("historical_daily_price_fields_read") == []
        and manifest.get("historical_forward_return_fields_read") is False
        and manifest.get("model_fitting_performed") is False
        and manifest.get("stress_2024_2025_return_fields_read") is False
        and manifest.get("provider_request_issued") is False
    ):
        raise Campaign136OrderedUniquenessError("numeric140 design metadata changed")
    for item in files:
        path = (DESIGN_MANIFEST_PATH.parent / str(item["path"])).resolve()
        if not path.is_file() or len(str(item.get("sha256") or "")) != 64:
            raise Campaign136OrderedUniquenessError(
                "numeric140 design partition metadata changed"
            )
        if pq.read_schema(path).names != expected_columns:
            raise Campaign136OrderedUniquenessError(
                "numeric140 design partition schema changed"
            )
    return manifest


def validate_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE_PATH.is_file():
        raise Campaign136OrderedUniquenessError(
            "ordered uniqueness implementation freeze is absent"
        )
    record = load_json(IMPLEMENTATION_FREEZE_PATH)
    frozen = record.get("frozen_implementation") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign136_ordered_uniqueness_implementation_freeze"
        and record.get("status")
        == "all_140_design_loader_and_gate_runner_frozen_before_comparator_values"
        and frozen.get("runner_sha256") == file_sha256(Path(__file__).resolve())
        and frozen.get("test_sha256") == file_sha256(TEST_PATH)
        and frozen.get("protocol_sha256") == PROTOCOL_SHA256
        and frozen.get("coverage_sha256") == COVERAGE_SHA256
        and frozen.get("design_manifest_sha256") == DESIGN_MANIFEST_SHA256
        and frozen.get("design_dataset_sha256") == DESIGN_DATASET_SHA256
        and frozen.get("comparison_count") == EXPECTED_COMPARISON_COUNT
        and frozen.get("comparison_order_sha256") == EXPECTED_COMPARISON_ORDER_SHA256
        and frozen.get("candidate_quality_listing_rows")
        == EXPECTED_QUALITY_LISTING_CANDIDATE_ROWS
        and frozen.get("minimum_pairwise_names") == MINIMUM_PAIRWISE_NAMES
        and frozen.get("minimum_pairwise_sessions") == MINIMUM_PAIRWISE_SESSIONS
        and frozen.get("strict_maximum_absolute_median_correlation")
        == MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION
        and frozen.get("output_path") == relative(OUTPUT_PATH)
        and boundary.get("comparator_values_read_before_freeze") is False
        and boundary.get("historical_daily_ohlcv_fields_read") == []
        and boundary.get("historical_forward_returns_read") is False
    ):
        raise Campaign136OrderedUniquenessError(
            "ordered uniqueness implementation freeze changed"
        )
    return record


def validate_static_bindings() -> dict[str, Any]:
    load_protocol()
    candidate.validate_implementation_freeze()
    coverage.validate_coverage_freeze()
    design_manifest = validate_design_manifest_metadata()
    freeze = validate_implementation_freeze()
    for path, expected, label in (
        (COVERAGE_PATH, COVERAGE_SHA256, "coverage result"),
        (
            candidate.DEFAULT_OUTPUT_ROOT / candidate.MANIFEST_NAME,
            coverage.SNAPSHOT_MANIFEST_SHA256,
            "candidate manifest",
        ),
        (
            CANDIDATE49_SIGNAL_LEDGER,
            CANDIDATE49_SIGNAL_LEDGER_SHA256,
            "Candidate49 signal ledger",
        ),
        (
            CANDIDATE49_EXECUTION_LEDGER,
            CANDIDATE49_EXECUTION_LEDGER_SHA256,
            "Candidate49 execution ledger",
        ),
    ):
        require_file(path, expected, label)
    coverage_result = load_json(COVERAGE_PATH)
    gate = coverage_result.get("coverage_and_variation") or {}
    if not (
        coverage_result.get("status")
        == "coverage_passed_ready_to_freeze_all_140_ordered_comparator_audit"
        and gate.get("gate_passed_before_comparator_values") is True
        and gate.get("quality_listing_eligible_rows")
        == EXPECTED_QUALITY_LISTING_CANDIDATE_ROWS
        and gate.get("candidate_eligible_rows")
        == EXPECTED_QUALITY_LISTING_CANDIDATE_ROWS
        and coverage_result.get("comparator_values_read") is False
        and coverage_result.get("numeric_comparator_count_read") == 0
        and coverage_result.get("historical_daily_ohlcv_fields_read") == []
        and coverage_result.get("historical_forward_return_fields_read") is False
    ):
        raise Campaign136OrderedUniquenessError("coverage authority changed")
    return {
        "implementation_freeze_sha256": file_sha256(IMPLEMENTATION_FREEZE_PATH),
        "coverage_sha256": COVERAGE_SHA256,
        "candidate_manifest_sha256": coverage.SNAPSHOT_MANIFEST_SHA256,
        "candidate_dataset_sha256": coverage.SNAPSHOT_DATASET_SHA256,
        "design_manifest_sha256": DESIGN_MANIFEST_SHA256,
        "design_dataset_sha256": DESIGN_DATASET_SHA256,
        "design_partition_count": len(design_manifest["files"]),
        "candidate49_signal_ledger_sha256": CANDIDATE49_SIGNAL_LEDGER_SHA256,
        "candidate49_execution_ledger_sha256": CANDIDATE49_EXECUTION_LEDGER_SHA256,
        "comparator_values_read": False,
        "historical_daily_ohlcv_fields_read": [],
        "historical_forward_returns_read": False,
        "provider_request_issued": False,
        "freeze_status": freeze["status"],
    }


def build_plan() -> dict[str, Any]:
    static = validate_static_bindings()
    blockers = ["uniqueness_output_already_exists"] if OUTPUT_PATH.exists() else []
    return {
        "kind": "a_share_three_day_walkforward_campaign136_ordered_uniqueness_plan",
        "ready": not blockers,
        "blockers": blockers,
        "output_path": str(OUTPUT_PATH),
        "comparison_count": EXPECTED_COMPARISON_COUNT,
        "comparison_order_sha256": EXPECTED_COMPARISON_ORDER_SHA256,
        "static_bindings": static,
        "candidate_values_read": False,
        "comparator_values_read": False,
        "historical_daily_ohlcv_fields_read": [],
        "historical_forward_returns_read": False,
        "provider_request_issued": False,
    }


def eligible_candidate_panel(
    frame: pd.DataFrame, eligible_keys: pd.DataFrame
) -> pd.DataFrame:
    required = {
        "trade_date",
        "symbol",
        formula.FACTOR_NAME,
        f"{formula.FACTOR_NAME}_eligible",
    }
    if not required.issubset(frame.columns):
        raise Campaign136OrderedUniquenessError("candidate panel columns changed")
    eligible = (
        frame[f"{formula.FACTOR_NAME}_eligible"]
        .astype("boolean")
        .fillna(False)
        .astype(bool)
    )
    values = pd.to_numeric(frame[formula.FACTOR_NAME], errors="coerce")
    selected = frame.loc[
        eligible & values.notna(),
        ["trade_date", "symbol"],
    ].copy()
    selected[formula.FACTOR_NAME] = values.loc[eligible & values.notna()].to_numpy()
    quality = eligible_keys[["trade_date", "symbol"]].merge(
        selected,
        on=["trade_date", "symbol"],
        how="inner",
        validate="one_to_one",
    )
    finite = quality[formula.FACTOR_NAME].to_numpy(dtype=np.float64)
    if not np.isfinite(finite).all() or (finite < 0.0).any():
        raise Campaign136OrderedUniquenessError("eligible candidate panel is invalid")
    return quality


def candidate_arrays() -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    frame = coverage.load_candidate_frame()
    eligible_keys = coverage.quality_listing_eligible_keys()
    quality = eligible_candidate_panel(frame, eligible_keys)
    del frame, eligible_keys
    gc.collect()
    if len(quality) != EXPECTED_QUALITY_LISTING_CANDIDATE_ROWS:
        raise Campaign136OrderedUniquenessError("candidate quality panel changed")
    keys = design.compact_stock_day_keys(quality["trade_date"], quality["symbol"])
    values = quality[formula.FACTOR_NAME].to_numpy(dtype=np.float64)
    order = np.argsort(keys, kind="stable")
    keys = keys[order]
    values = values[order]
    if len(np.unique(keys)) != len(keys):
        raise Campaign136OrderedUniquenessError("candidate keys are not unique")
    del quality
    gc.collect()
    return keys, values, {"quality_listing_candidate_rows": len(keys)}


def daily_rank_rows(
    keys: np.ndarray,
    candidate_values: np.ndarray,
    comparison_values: np.ndarray,
    *,
    minimum_names: int = MINIMUM_PAIRWISE_NAMES,
) -> list[list[Any]]:
    compact = np.asarray(keys, dtype=np.int64)
    candidate_values = np.asarray(candidate_values, dtype=np.float64)
    comparison_values = np.asarray(comparison_values, dtype=np.float64)
    if not (
        compact.ndim == candidate_values.ndim == comparison_values.ndim == 1
        and len(compact) == len(candidate_values) == len(comparison_values)
        and np.all(compact[1:] >= compact[:-1])
    ):
        raise Campaign136OrderedUniquenessError("daily rank-correlation arrays changed")
    days = compact // 4_000_000
    boundaries = np.flatnonzero(np.r_[True, days[1:] != days[:-1], True])
    rows: list[list[Any]] = []
    for start, stop in zip(boundaries[:-1], boundaries[1:]):
        candidate_slice = candidate_values[start:stop]
        comparison_slice = comparison_values[start:stop]
        finite = np.isfinite(candidate_slice) & np.isfinite(comparison_slice)
        pairwise = int(finite.sum())
        if pairwise < minimum_names:
            continue
        candidate_pair = candidate_slice[finite]
        comparison_pair = comparison_slice[finite]
        if np.unique(candidate_pair).size < 2 or np.unique(comparison_pair).size < 2:
            continue
        candidate_rank = pd.Series(candidate_pair).rank(method="average", pct=True)
        comparison_rank = pd.Series(comparison_pair).rank(method="average", pct=True)
        correlation = float(candidate_rank.corr(comparison_rank, method="pearson"))
        if math.isfinite(correlation):
            rows.append([int(days[start]), pairwise, correlation])
    return rows


def daily_rows_sha256(rows: list[list[Any]]) -> str:
    payload = json.dumps(
        rows,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def comparison_result(
    *,
    definition: dict[str, str],
    daily_rows: list[list[Any]],
) -> dict[str, Any]:
    correlations = np.asarray([row[2] for row in daily_rows], dtype=np.float64)
    sessions = len(daily_rows)
    median = float(np.median(correlations)) if sessions else math.nan
    passed = bool(
        sessions >= MINIMUM_PAIRWISE_SESSIONS
        and math.isfinite(median)
        and abs(median) < MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION
    )
    return {
        "comparison_factor": definition["name"],
        "source_score_direction": definition["score_direction"],
        "comparison_value_semantics": "frozen direction-normalized average-tie percentile rank",
        "pairwise_sessions": sessions,
        "minimum_pairwise_names_observed": (
            min(int(row[1]) for row in daily_rows) if daily_rows else 0
        ),
        "median_daily_rank_correlation": (median if math.isfinite(median) else None),
        "absolute_median_daily_rank_correlation": (
            abs(median) if math.isfinite(median) else None
        ),
        "daily_rank_correlation_p05": (
            float(np.quantile(correlations, 0.05)) if sessions else None
        ),
        "daily_rank_correlation_p95": (
            float(np.quantile(correlations, 0.95)) if sessions else None
        ),
        "daily_correlation_frame_sha256": (
            daily_rows_sha256(daily_rows) if sessions else None
        ),
        "gate_passed": passed,
    }


def summarize_comparisons(
    results: list[dict[str, Any]], expected_order: list[str]
) -> dict[str, Any]:
    observed = [str(item.get("comparison_factor")) for item in results]
    correlations = [
        float(item["absolute_median_daily_rank_correlation"])
        for item in results
        if item.get("absolute_median_daily_rank_correlation") is not None
    ]
    all_passed = bool(
        len(results) == EXPECTED_COMPARISON_COUNT
        and observed == expected_order
        and len(correlations) == EXPECTED_COMPARISON_COUNT
        and all(item.get("gate_passed") is True for item in results)
        and all(value < MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION for value in correlations)
    )
    return {
        "comparison_factor_count": len(results),
        "comparison_order_matches_preregistration": observed == expected_order,
        "all_required_numeric_comparisons_passed": all_passed,
        "maximum_observed_absolute_median_daily_rank_correlation": (
            max(correlations) if correlations else None
        ),
    }


def resolve_design_partition(record: dict[str, Any]) -> Path:
    return (DESIGN_MANIFEST_PATH.parent / str(record["path"])).resolve()


def audit_design_partitions(
    *,
    candidate_keys: np.ndarray,
    candidate_values: np.ndarray,
    definitions: list[dict[str, str]],
    manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    names = [item["name"] for item in definitions]
    accumulated: dict[str, list[list[Any]]] = {name: [] for name in names}
    seen = np.zeros(len(candidate_keys), dtype=bool)
    receipts: list[dict[str, Any]] = []
    for record in manifest["files"]:
        path = resolve_design_partition(record)
        require_file(path, str(record["sha256"]), f"design partition {record['year']}")
        frame = pd.read_parquet(path, columns=["stock_day_key", *names])
        keys = frame["stock_day_key"].to_numpy(dtype=np.int64)
        if len(keys) != int(record["rows"]) or len(np.unique(keys)) != len(keys):
            raise Campaign136OrderedUniquenessError(
                f"design key rows changed for {record['year']}"
            )
        order = np.argsort(keys, kind="stable")
        keys = keys[order]
        positions = np.searchsorted(candidate_keys, keys)
        if (
            np.any(positions >= len(candidate_keys))
            or not np.array_equal(candidate_keys[positions], keys)
            or seen[positions].any()
        ):
            raise Campaign136OrderedUniquenessError(
                f"design keys changed for {record['year']}"
            )
        seen[positions] = True
        values = candidate_values[positions]
        for definition in definitions:
            name = definition["name"]
            comparison = pd.to_numeric(frame[name], errors="coerce").to_numpy(
                dtype=np.float64
            )[order]
            finite = comparison[np.isfinite(comparison)]
            if finite.size and ((finite <= 0.0).any() or (finite > 1.0).any()):
                raise Campaign136OrderedUniquenessError(
                    f"directional rank range changed for {name}"
                )
            accumulated[name].extend(daily_rank_rows(keys, values, comparison))
        receipts.append(
            {
                "year": int(record["year"]),
                "path": str(path),
                "sha256": str(record["sha256"]),
                "rows": len(frame),
            }
        )
        del frame, keys, values
        gc.collect()
    if not seen.all():
        raise Campaign136OrderedUniquenessError(
            "numeric140 design does not cover every candidate quality key"
        )
    results = [
        comparison_result(
            definition=definition,
            daily_rows=accumulated[definition["name"]],
        )
        for definition in definitions
    ]
    return results, {"partitions": receipts, "candidate_keys_covered": int(seen.sum())}


def atomic_exclusive_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise Campaign136OrderedUniquenessError(
                "ordered uniqueness output already exists"
            ) from exc
    finally:
        temporary.unlink(missing_ok=True)


def run_ordered_uniqueness(*, confirm: bool) -> Path:
    if not confirm:
        raise Campaign136OrderedUniquenessError(
            "ordered uniqueness requires --confirm-run"
        )
    plan = build_plan()
    if plan["ready"] is not True:
        raise Campaign136OrderedUniquenessError("ordered uniqueness plan is not ready")
    definitions = comparison_definitions()
    expected_order = [item["name"] for item in definitions]
    candidate_verification = candidate.verify_snapshot(verify_source=True)
    try:
        design_verification = design.verify_snapshot(DESIGN_MANIFEST_PATH, workers=1)
    except design.Campaign132DesignError as exc:
        raise Campaign136OrderedUniquenessError(str(exc)) from exc
    if not (
        design_verification.get("manifest_sha256") == DESIGN_MANIFEST_SHA256
        and design_verification.get("dataset_sha256") == DESIGN_DATASET_SHA256
        and design_verification.get("rows") == EXPECTED_QUALITY_LISTING_CANDIDATE_ROWS
        and design_verification.get("feature_count") == EXPECTED_COMPARISON_COUNT
        and design_verification.get(
            "historical_daily_price_or_forward_return_values_read"
        )
        is False
    ):
        raise Campaign136OrderedUniquenessError(
            "numeric140 design verification changed"
        )
    keys, values, candidate_receipt = candidate_arrays()
    manifest = validate_design_manifest_metadata()
    comparisons, design_receipt = audit_design_partitions(
        candidate_keys=keys,
        candidate_values=values,
        definitions=definitions,
        manifest=manifest,
    )
    summary = summarize_comparisons(comparisons, expected_order)
    passed = summary["all_required_numeric_comparisons_passed"] is True
    result = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign136_ordered_numeric_uniqueness_audit",
        "status": (
            "all_140_uniqueness_gates_passed_ready_to_freeze_one_development_trial"
            if passed
            else "one_or_more_of_140_uniqueness_gates_failed_terminal_before_returns"
        ),
        "recorded_at": datetime.now(UTC).isoformat(),
        "factor": formula.FACTOR_NAME,
        "direction": formula.SCORE_DIRECTION,
        "comparison_order_sha256": EXPECTED_COMPARISON_ORDER_SHA256,
        "static_bindings": plan["static_bindings"],
        "candidate_snapshot_verification": candidate_verification,
        "numeric140_design_verification": design_verification,
        "candidate_receipt": candidate_receipt,
        "design_receipt": design_receipt,
        "exact_gate": {
            "minimum_pairwise_names_per_session": MINIMUM_PAIRWISE_NAMES,
            "minimum_pairwise_sessions_per_comparison": MINIMUM_PAIRWISE_SESSIONS,
            "maximum_allowed_absolute_median_daily_rank_correlation": MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION,
            "strict_inequality": True,
            "all_140_must_pass": True,
            "insufficient_overlap_fails_closed": True,
        },
        "comparisons": comparisons,
        "summary": summary,
        "all_140_results_recorded_without_early_stop": len(comparisons)
        == EXPECTED_COMPARISON_COUNT,
        "historical_daily_ohlcv_fields_read": [],
        "historical_forward_return_fields_read": False,
        "stress_2024_2025_return_values_opened": False,
        "provider_request_issued": False,
        "credential_loaded": False,
        "candidate49_historical_backfill_performed": False,
        "candidate49_ledgers_changed": False,
        "second_prospective_candidate_created": False,
        "current_scoring_selection_sizing_positions_or_orders_performed": False,
        "investment_advice": False,
        "next_action": (
            "freeze exactly one Campaign136 2019-2023 walk-forward development trial before any OHLCV or return read"
            if passed
            else "terminalize Campaign136 without OHLCV or return reads and start a genuinely new Campaign137 prevalue scout"
        ),
    }
    atomic_exclusive_json(OUTPUT_PATH, result)
    return OUTPUT_PATH


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    sub = value.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    run = sub.add_parser("run")
    run.add_argument("--confirm-run", action="store_true")
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "plan":
            value = build_plan()
            print(json.dumps(value, ensure_ascii=False, sort_keys=True))
            return 0 if value["ready"] else 2
        path = run_ordered_uniqueness(confirm=args.confirm_run)
        print(json.dumps({"uniqueness_audit_path": str(path)}, sort_keys=True))
        return 0
    except Campaign136OrderedUniquenessError as exc:
        print(
            json.dumps(
                {
                    "ready": False,
                    "error_code": "campaign136_ordered_uniqueness_contract_failure",
                    "error": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
