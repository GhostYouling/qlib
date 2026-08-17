#!/usr/bin/env python3
"""Run Campaign146's frozen all-141 ordered no-return uniqueness audit."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import a_share_three_day_walkforward_campaign132_design as design
from scripts import (
    a_share_three_day_walkforward_campaign136_coverage_audit as c136_coverage,
)
from scripts import a_share_three_day_walkforward_campaign136_features as c136_candidate
from scripts import a_share_three_day_walkforward_campaign136_formula as c136_formula
from scripts import a_share_three_day_walkforward_campaign136_ordered_uniqueness as base
from scripts import a_share_three_day_walkforward_campaign146_features as candidate
from scripts import (
    a_share_three_day_walkforward_campaign146_no_return_audit as frozen_coverage,
)
from scripts import (
    a_share_three_day_walkforward_campaign146_no_return_audit_recovery as coverage,
)
from scripts import (
    a_share_three_day_walkforward_campaign146_snapshot_verify_recovery as recovery,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_146_ordered_numeric_uniqueness_protocol_20260814.json"
)
PROTOCOL_SHA256 = "ec070598c943232adb33643980710120c83030517c186a72bd1d7a0f3ec9fd81"
COVERAGE_PATH = coverage.OUTPUT_PATH
COVERAGE_SHA256 = "74c74d7cfb9e13d145251f8d266a5f44a62b78c6a45f8581132be7aeed68b83e"
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_146_ordered_uniqueness_implementation_freeze_20260814.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign146_ordered_uniqueness.py"
)
OUTPUT_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_146/uniqueness/campaign146_ordered_uniqueness_audit.json"
)
DESIGN_MANIFEST_PATH = base.DESIGN_MANIFEST_PATH
DESIGN_MANIFEST_SHA256 = base.DESIGN_MANIFEST_SHA256
DESIGN_DATASET_SHA256 = base.DESIGN_DATASET_SHA256
C136_MANIFEST_PATH = c136_candidate.DEFAULT_OUTPUT_ROOT / c136_candidate.MANIFEST_NAME
C136_MANIFEST_SHA256 = c136_coverage.SNAPSHOT_MANIFEST_SHA256
C136_DATASET_SHA256 = c136_coverage.SNAPSHOT_DATASET_SHA256
CANDIDATE49_SIGNAL_LEDGER = frozen_coverage.CANDIDATE49_SIGNAL_LEDGER
CANDIDATE49_SIGNAL_LEDGER_SHA256 = frozen_coverage.CANDIDATE49_SIGNAL_LEDGER_SHA256
CANDIDATE49_EXECUTION_LEDGER = frozen_coverage.CANDIDATE49_EXECUTION_LEDGER
CANDIDATE49_EXECUTION_LEDGER_SHA256 = (
    frozen_coverage.CANDIDATE49_EXECUTION_LEDGER_SHA256
)

EXPECTED_COMPARISON_COUNT = 141
EXPECTED_COMPARISON_ORDER_SHA256 = candidate.NUMERIC_COMPARATOR_ORDER_SHA256
EXPECTED_QUALITY_LISTING_CANDIDATE_ROWS = 1_320_628
MINIMUM_PAIRWISE_NAMES = 50
MINIMUM_PAIRWISE_SESSIONS = 100
MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION = 0.8


class Campaign146OrderedUniquenessError(RuntimeError):
    """Fail closed when an all-141 comparison invariant changes."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_file(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or file_sha256(path) != expected:
        raise Campaign146OrderedUniquenessError(f"Campaign146 {label} changed")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Campaign146OrderedUniquenessError(f"expected JSON object: {path}")
    return value


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def comparison_definitions() -> list[dict[str, str]]:
    items = [dict(item) for item in candidate.reconstruct_comparisons()]
    first = [dict(item) for item in design.current_feature_order()]
    if not (
        len(items) == EXPECTED_COMPARISON_COUNT
        and items[:140] == first
        and items[-1] == {"name": c136_formula.FACTOR_NAME, "score_direction": "higher"}
        and candidate._order_digest(items) == EXPECTED_COMPARISON_ORDER_SHA256
    ):
        raise Campaign146OrderedUniquenessError("comparison order changed")
    return items


def load_protocol() -> dict[str, Any]:
    require_file(PROTOCOL_PATH, PROTOCOL_SHA256, "uniqueness protocol")
    spec = load_json(PROTOCOL_PATH)
    order = spec.get("comparison_order") or {}
    alignment = spec.get("candidate_alignment") or {}
    gate = spec.get("exact_gate") or {}
    boundary = spec.get("research_boundary") or {}
    definitions = comparison_definitions()
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign146_ordered_numeric_uniqueness_protocol"
        and spec.get("status")
        == "all_141_ordered_comparators_frozen_after_coverage_pass_before_any_comparator_value"
        and order.get("count") == len(definitions) == EXPECTED_COMPARISON_COUNT
        and order.get("order_sha256") == EXPECTED_COMPARISON_ORDER_SHA256
        and order.get("first_140_design_order_sha256") == design.FEATURE_ORDER_SHA256
        and order.get("last_factor") == c136_formula.FACTOR_NAME
        and order.get("last_factor_direction") == "higher"
        and order.get(
            "removal_reorder_subset_early_stop_or_candidate_specific_fill_allowed"
        )
        is False
        and alignment.get("quality_listing_candidate_rows_expected")
        == EXPECTED_QUALITY_LISTING_CANDIDATE_ROWS
        and alignment.get("candidate_value_range_inclusive") == [-1.0, 1.0]
        and alignment.get("candidate_missing_fill_allowed") is False
        and alignment.get("numeric140_design_is_a_superset_of_candidate_keys") is True
        and alignment.get("campaign136_snapshot_must_cover_every_candidate_key") is True
        and gate.get("minimum_pairwise_names_per_session") == MINIMUM_PAIRWISE_NAMES
        and gate.get("minimum_pairwise_sessions_per_comparison")
        == MINIMUM_PAIRWISE_SESSIONS
        and gate.get("maximum_allowed_absolute_median_daily_rank_correlation")
        == MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION
        and gate.get("strict_inequality") is True
        and gate.get("all_141_must_pass") is True
        and gate.get("insufficient_overlap_fails_closed") is True
        and boundary.get("comparator_values_read_before_protocol") is False
        and boundary.get("numeric140_design_partition_values_read_before_protocol")
        is False
        and boundary.get("campaign136_snapshot_partition_values_read_before_protocol")
        is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
    ):
        raise Campaign146OrderedUniquenessError("uniqueness protocol semantics changed")
    return spec


def validate_design_manifest_metadata() -> dict[str, Any]:
    try:
        manifest = base.validate_design_manifest_metadata()
    except base.Campaign136OrderedUniquenessError as exc:
        raise Campaign146OrderedUniquenessError(str(exc)) from exc
    return manifest


def validate_c136_manifest_metadata() -> dict[str, Any]:
    require_file(C136_MANIFEST_PATH, C136_MANIFEST_SHA256, "Campaign136 manifest")
    manifest = load_json(C136_MANIFEST_PATH)
    files = list(manifest.get("partitions") or [])
    if not (
        manifest.get("kind") == "a_share_three_day_walkforward_campaign136_snapshot"
        and manifest.get("status") == "published_and_verified"
        and manifest.get("source_projection") == list(c136_candidate.SOURCE_COLUMNS)
        and manifest.get("output_columns") == list(c136_candidate.OUTPUT_COLUMNS)
        and manifest.get("dataset_sha256") == C136_DATASET_SHA256
        and manifest.get("rows") == c136_coverage.SNAPSHOT_ROWS
        and manifest.get("eligible_rows") == c136_coverage.SNAPSHOT_ELIGIBLE_ROWS
        and manifest.get("partition_count") == len(files) > 0
        and manifest.get("historical_daily_ohlcv_fields_read") == []
        and manifest.get("historical_forward_returns_read") is False
        and manifest.get("provider_request_issued") is False
    ):
        raise Campaign146OrderedUniquenessError("Campaign136 manifest changed")
    return manifest


def validate_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE_PATH.is_file():
        raise Campaign146OrderedUniquenessError(
            "ordered uniqueness implementation freeze is absent"
        )
    record = load_json(IMPLEMENTATION_FREEZE_PATH)
    frozen = record.get("frozen_implementation") or {}
    tests = record.get("synthetic_verification") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign146_ordered_uniqueness_implementation_freeze"
        and record.get("status")
        == "all_141_source_loaders_alignment_and_gate_runner_frozen_before_comparator_values"
        and frozen.get("runner_sha256") == file_sha256(Path(__file__).resolve())
        and frozen.get("test_sha256") == file_sha256(TEST_PATH)
        and frozen.get("protocol_sha256") == PROTOCOL_SHA256
        and frozen.get("coverage_sha256") == COVERAGE_SHA256
        and frozen.get("design_manifest_sha256") == DESIGN_MANIFEST_SHA256
        and frozen.get("design_dataset_sha256") == DESIGN_DATASET_SHA256
        and frozen.get("campaign136_manifest_sha256") == C136_MANIFEST_SHA256
        and frozen.get("campaign136_dataset_sha256") == C136_DATASET_SHA256
        and frozen.get("comparison_count") == EXPECTED_COMPARISON_COUNT
        and frozen.get("comparison_order_sha256") == EXPECTED_COMPARISON_ORDER_SHA256
        and frozen.get("candidate_quality_listing_rows")
        == EXPECTED_QUALITY_LISTING_CANDIDATE_ROWS
        and frozen.get("output_path") == relative(OUTPUT_PATH)
        and tests.get("exit_code") == 0
        and tests.get("passed") >= 6
        and boundary.get("comparator_values_read_before_freeze") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
    ):
        raise Campaign146OrderedUniquenessError(
            "ordered uniqueness implementation freeze changed"
        )
    return record


def validate_static_bindings() -> dict[str, Any]:
    load_protocol()
    candidate._validate_implementation_freeze()
    design_manifest = validate_design_manifest_metadata()
    c136_manifest = validate_c136_manifest_metadata()
    freeze = validate_implementation_freeze()
    for path, expected, label in (
        (COVERAGE_PATH, COVERAGE_SHA256, "coverage result"),
        (
            recovery.SNAPSHOT_MANIFEST,
            recovery.SNAPSHOT_MANIFEST_SHA256,
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
    result = load_json(COVERAGE_PATH)
    gate = result.get("coverage_and_variation") or {}
    if not (
        result.get("status")
        == "coverage_passed_ready_to_freeze_all_141_ordered_comparator_audit"
        and gate.get("gate_passed_before_comparator_values") is True
        and gate.get("candidate_eligible_rows")
        == EXPECTED_QUALITY_LISTING_CANDIDATE_ROWS
        and result.get("comparator_values_read") is False
        and result.get("numeric_comparator_count_read") == 0
        and result.get("historical_forward_return_fields_read") is False
    ):
        raise Campaign146OrderedUniquenessError("coverage authority changed")
    return {
        "implementation_freeze_sha256": file_sha256(IMPLEMENTATION_FREEZE_PATH),
        "coverage_sha256": COVERAGE_SHA256,
        "candidate_manifest_sha256": recovery.SNAPSHOT_MANIFEST_SHA256,
        "candidate_dataset_sha256": recovery.SNAPSHOT_DATASET_SHA256,
        "design_manifest_sha256": DESIGN_MANIFEST_SHA256,
        "design_dataset_sha256": DESIGN_DATASET_SHA256,
        "design_partition_count": len(design_manifest["files"]),
        "campaign136_manifest_sha256": C136_MANIFEST_SHA256,
        "campaign136_dataset_sha256": C136_DATASET_SHA256,
        "campaign136_partition_count": len(c136_manifest["files"]),
        "candidate49_signal_ledger_sha256": CANDIDATE49_SIGNAL_LEDGER_SHA256,
        "candidate49_execution_ledger_sha256": CANDIDATE49_EXECUTION_LEDGER_SHA256,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
        "freeze_status": freeze["status"],
    }


def build_plan() -> dict[str, Any]:
    static = validate_static_bindings()
    blockers = ["uniqueness_output_already_exists"] if OUTPUT_PATH.exists() else []
    return {
        "kind": "a_share_three_day_walkforward_campaign146_ordered_uniqueness_plan",
        "ready": not blockers,
        "blockers": blockers,
        "output_path": str(OUTPUT_PATH),
        "comparison_count": EXPECTED_COMPARISON_COUNT,
        "comparison_order_sha256": EXPECTED_COMPARISON_ORDER_SHA256,
        "static_bindings": static,
        "candidate_values_read": False,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def eligible_candidate_panel(
    frame: pd.DataFrame, eligible_keys: pd.DataFrame
) -> pd.DataFrame:
    factor = candidate.FACTOR_NAME
    required = {"trade_date", "symbol", factor, f"{factor}_eligible"}
    if not required.issubset(frame.columns):
        raise Campaign146OrderedUniquenessError("candidate panel columns changed")
    declared = frame[f"{factor}_eligible"].astype("boolean").fillna(False).astype(bool)
    values = pd.to_numeric(frame[factor], errors="coerce")
    selected = frame.loc[declared & values.notna(), ["trade_date", "symbol"]].copy()
    selected[factor] = values.loc[declared & values.notna()].to_numpy()
    quality = eligible_keys[["trade_date", "symbol"]].merge(
        selected,
        on=["trade_date", "symbol"],
        how="inner",
        validate="one_to_one",
    )
    finite = quality[factor].to_numpy(dtype=np.float64)
    if not np.isfinite(finite).all() or (finite < -1.0).any() or (finite > 1.0).any():
        raise Campaign146OrderedUniquenessError("eligible candidate panel is invalid")
    return quality


def candidate_arrays() -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    load_candidate = frozen_coverage._generated["_load_candidate_frame"]
    load_keys = frozen_coverage._generated["_quality_listing_eligible_keys"]
    frame = load_candidate(recovery.EXPECTED_ELIGIBLE_ROWS)
    eligible_keys = load_keys()
    quality = eligible_candidate_panel(frame, eligible_keys)
    del frame, eligible_keys
    gc.collect()
    if len(quality) != EXPECTED_QUALITY_LISTING_CANDIDATE_ROWS:
        raise Campaign146OrderedUniquenessError("candidate quality panel changed")
    keys = design.compact_stock_day_keys(quality["trade_date"], quality["symbol"])
    values = quality[candidate.FACTOR_NAME].to_numpy(dtype=np.float64)
    order = np.argsort(keys, kind="stable")
    keys = keys[order]
    values = values[order]
    if len(np.unique(keys)) != len(keys):
        raise Campaign146OrderedUniquenessError("candidate keys are not unique")
    return keys, values, {"quality_listing_candidate_rows": len(keys)}


def subset_positions(*, source_keys: np.ndarray, target_keys: np.ndarray) -> np.ndarray:
    source = np.asarray(source_keys, dtype=np.int64)
    target = np.asarray(target_keys, dtype=np.int64)
    if (
        source.ndim != 1
        or target.ndim != 1
        or len(np.unique(source)) != len(source)
        or len(np.unique(target)) != len(target)
        or (len(source) > 1 and np.any(source[1:] < source[:-1]))
        or (len(target) > 1 and np.any(target[1:] < target[:-1]))
    ):
        raise Campaign146OrderedUniquenessError("subset key order changed")
    positions = np.searchsorted(source, target)
    if np.any(positions >= len(source)) or not np.array_equal(
        source[positions], target
    ):
        raise Campaign146OrderedUniquenessError("source does not cover target keys")
    return positions


def audit_numeric140(
    *,
    candidate_keys: np.ndarray,
    candidate_values: np.ndarray,
    definitions: list[dict[str, str]],
    manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    names = [item["name"] for item in definitions]
    accumulated: dict[str, list[list[Any]]] = {name: [] for name in names}
    candidate_days = candidate_keys // 4_000_000
    candidate_years = pd.DatetimeIndex(
        candidate_days.astype("datetime64[D]")
    ).year.to_numpy()
    seen = np.zeros(len(candidate_keys), dtype=bool)
    receipts: list[dict[str, Any]] = []
    for record in manifest["files"]:
        path = base.resolve_design_partition(record)
        require_file(path, str(record["sha256"]), f"design partition {record['year']}")
        frame = pd.read_parquet(path, columns=["stock_day_key", *names])
        source_keys = frame["stock_day_key"].to_numpy(dtype=np.int64)
        source_order = np.argsort(source_keys, kind="stable")
        source_keys = source_keys[source_order]
        target_indices = np.flatnonzero(candidate_years == int(record["year"]))
        target_keys = candidate_keys[target_indices]
        positions = subset_positions(source_keys=source_keys, target_keys=target_keys)
        seen[target_indices] = True
        target_values = candidate_values[target_indices]
        for definition in definitions:
            name = definition["name"]
            comparison = pd.to_numeric(frame[name], errors="coerce").to_numpy(
                dtype=np.float64
            )[source_order][positions]
            finite = comparison[np.isfinite(comparison)]
            if finite.size and ((finite <= 0.0).any() or (finite > 1.0).any()):
                raise Campaign146OrderedUniquenessError(
                    f"directional rank range changed for {name}"
                )
            accumulated[name].extend(
                base.daily_rank_rows(target_keys, target_values, comparison)
            )
        receipts.append(
            {
                "year": int(record["year"]),
                "path": str(path),
                "sha256": str(record["sha256"]),
                "source_rows": len(frame),
                "candidate_rows": len(target_keys),
            }
        )
        del frame, source_keys, positions, target_values
        gc.collect()
    if not seen.all():
        raise Campaign146OrderedUniquenessError(
            "numeric140 design does not cover every candidate key"
        )
    results = [
        base.comparison_result(
            definition=definition,
            daily_rows=accumulated[definition["name"]],
        )
        for definition in definitions
    ]
    return results, {"partitions": receipts, "candidate_keys_covered": int(seen.sum())}


def campaign136_comparison(
    *, candidate_keys: np.ndarray, candidate_values: np.ndarray
) -> tuple[dict[str, Any], dict[str, Any]]:
    frame = c136_coverage.load_candidate_frame()
    factor = c136_formula.FACTOR_NAME
    eligible = frame[f"{factor}_eligible"].astype("boolean").fillna(False).astype(bool)
    values = pd.to_numeric(frame[factor], errors="coerce")
    selected = frame.loc[eligible & values.notna(), ["trade_date", "symbol"]].copy()
    selected[factor] = values.loc[eligible & values.notna()].to_numpy()
    source_keys = design.compact_stock_day_keys(
        selected["trade_date"], selected["symbol"]
    )
    source_values = selected[factor].to_numpy(dtype=np.float64)
    aligned = design.align_values(
        source_keys=source_keys,
        source_values=source_values,
        target_keys=candidate_keys,
    )
    if not np.isfinite(aligned).all() or (aligned < 0.0).any():
        raise Campaign146OrderedUniquenessError(
            "Campaign136 comparator does not cover every candidate key"
        )
    definition = comparison_definitions()[-1]
    daily_rows = base.daily_rank_rows(candidate_keys, candidate_values, aligned)
    return base.comparison_result(definition=definition, daily_rows=daily_rows), {
        "source_snapshot_manifest_sha256": C136_MANIFEST_SHA256,
        "source_snapshot_dataset_sha256": C136_DATASET_SHA256,
        "eligible_source_rows": int(eligible.sum()),
        "aligned_candidate_rows": len(aligned),
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
            raise Campaign146OrderedUniquenessError(
                "ordered uniqueness output already exists"
            ) from exc
    finally:
        temporary.unlink(missing_ok=True)


def run_ordered_uniqueness(*, confirm: bool) -> Path:
    if not confirm:
        raise Campaign146OrderedUniquenessError(
            "ordered uniqueness requires --confirm-run"
        )
    plan = build_plan()
    if plan["ready"] is not True:
        raise Campaign146OrderedUniquenessError("ordered uniqueness plan is not ready")
    definitions = comparison_definitions()
    expected_order = [item["name"] for item in definitions]
    design_verification = design.verify_snapshot(DESIGN_MANIFEST_PATH, workers=1)
    c136_verification = c136_candidate.verify_snapshot(verify_source=True)
    keys, values, candidate_receipt = candidate_arrays()
    manifest = validate_design_manifest_metadata()
    comparisons, design_receipt = audit_numeric140(
        candidate_keys=keys,
        candidate_values=values,
        definitions=definitions[:140],
        manifest=manifest,
    )
    last, c136_receipt = campaign136_comparison(
        candidate_keys=keys, candidate_values=values
    )
    comparisons.append(last)
    summary = summarize_comparisons(comparisons, expected_order)
    passed = summary["all_required_numeric_comparisons_passed"] is True
    result = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign146_ordered_numeric_uniqueness_audit",
        "status": (
            "all_141_uniqueness_gates_passed_ready_to_freeze_one_development_trial"
            if passed
            else "one_or_more_of_141_uniqueness_gates_failed_terminal_before_returns"
        ),
        "recorded_at": datetime.now(UTC).isoformat(),
        "factor": candidate.FACTOR_NAME,
        "direction": "higher",
        "comparison_order_sha256": EXPECTED_COMPARISON_ORDER_SHA256,
        "static_bindings": plan["static_bindings"],
        "candidate_snapshot_recovery_verification_sha256": coverage.RECOVERY_RECEIPT_SHA256,
        "numeric140_design_verification": design_verification,
        "campaign136_snapshot_verification": c136_verification,
        "candidate_receipt": candidate_receipt,
        "design_receipt": design_receipt,
        "campaign136_receipt": c136_receipt,
        "exact_gate": {
            "minimum_pairwise_names_per_session": MINIMUM_PAIRWISE_NAMES,
            "minimum_pairwise_sessions_per_comparison": MINIMUM_PAIRWISE_SESSIONS,
            "maximum_allowed_absolute_median_daily_rank_correlation": MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION,
            "strict_inequality": True,
            "all_141_must_pass": True,
            "insufficient_overlap_fails_closed": True,
        },
        "comparisons": comparisons,
        "summary": summary,
        "all_141_results_recorded_without_early_stop": len(comparisons)
        == EXPECTED_COMPARISON_COUNT,
        "historical_daily_price_or_forward_return_values_read": False,
        "stress_2024_2025_return_values_opened": False,
        "provider_request_issued": False,
        "credential_loaded": False,
        "candidate49_historical_backfill_performed": False,
        "candidate49_ledgers_changed": False,
        "second_prospective_candidate_created": False,
        "current_scoring_selection_sizing_positions_or_orders_performed": False,
        "investment_advice": False,
        "next_action": (
            "freeze exactly one Campaign146 2019-2023 walk-forward development trial before any daily price or return read"
            if passed
            else "terminalize Campaign146 without daily price or return reads and continue with a genuinely new Campaign147 prevalue scout"
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
    except Campaign146OrderedUniquenessError as exc:
        print(
            json.dumps(
                {
                    "ready": False,
                    "error_code": "campaign146_ordered_uniqueness_contract_failure",
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
