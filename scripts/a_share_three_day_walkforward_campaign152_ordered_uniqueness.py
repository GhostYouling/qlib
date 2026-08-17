#!/usr/bin/env python3
"""Run Campaign152's frozen all-142 ordered no-return uniqueness audit."""

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

from scripts import (
    a_share_three_day_walkforward_campaign146_features as c146,
)  # noqa: E402
from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign146_no_return_audit as c146_frozen,
)
from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign146_ordered_uniqueness as base,
)
from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign146_snapshot_verify_recovery as c146_recovery,
)
from scripts import (
    a_share_three_day_walkforward_campaign152_features as candidate,
)  # noqa: E402
from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign152_no_return_audit as coverage,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_152_ordered_numeric_uniqueness_protocol_20260815.json"
)
PROTOCOL_SHA256 = "8f6c0b1e12d6d88566f8a2eed972f1e198829886dab4c6acc6fba93f499b5fca"
COVERAGE_PATH = coverage.OUTPUT_PATH
COVERAGE_SHA256 = "235289d3151eee543282c502fe40ac3d4986663fc00a777f4b3dcbb11c01f01b"
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_152_ordered_uniqueness_implementation_freeze_v2_20260815.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign152_ordered_uniqueness.py"
)
OUTPUT_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_152/uniqueness/campaign152_ordered_uniqueness_audit.json"
)
CANDIDATE_MANIFEST_PATH = (
    candidate.output_root(candidate.DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
)
CANDIDATE_MANIFEST_SHA256 = (
    "36bab509de3b8a012033b4591a5efa942e57b01178f099cd48cbb699267ca267"
)
CANDIDATE_DATASET_SHA256 = (
    "9ea1ebe6aad4867ce76d4fbc52fe46c80f5a3fca3096aa6e74a5e9c8292f4931"
)
EXPECTED_COMPARISON_COUNT = 142
EXPECTED_COMPARISON_ORDER_SHA256 = candidate.NUMERIC_COMPARATOR_ORDER_SHA256
EXPECTED_QUALITY_LISTING_CANDIDATE_ROWS = 1_330_171
MINIMUM_PAIRWISE_NAMES = 50
MINIMUM_PAIRWISE_SESSIONS = 100
MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION = 0.8
CANDIDATE49_SIGNAL_LEDGER = coverage.CANDIDATE49_SIGNAL_LEDGER
CANDIDATE49_SIGNAL_LEDGER_SHA256 = coverage.CANDIDATE49_SIGNAL_LEDGER_SHA256
CANDIDATE49_EXECUTION_LEDGER = coverage.CANDIDATE49_EXECUTION_LEDGER
CANDIDATE49_EXECUTION_LEDGER_SHA256 = coverage.CANDIDATE49_EXECUTION_LEDGER_SHA256


class Campaign152OrderedUniquenessError(RuntimeError):
    """Fail closed when an all-142 comparison invariant changes."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_file(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or file_sha256(path) != expected:
        raise Campaign152OrderedUniquenessError(f"Campaign152 {label} changed")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Campaign152OrderedUniquenessError(f"expected JSON object: {path}")
    return value


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def comparison_definitions() -> list[dict[str, str]]:
    items = [dict(item) for item in candidate.reconstruct_comparisons()]
    first = [dict(item) for item in base.comparison_definitions()]
    if not (
        len(items) == EXPECTED_COMPARISON_COUNT
        and items[:141] == first
        and items[-1] == {"name": c146.FACTOR_NAME, "score_direction": "higher"}
        and candidate._order_digest(items) == EXPECTED_COMPARISON_ORDER_SHA256
    ):
        raise Campaign152OrderedUniquenessError("comparison order changed")
    return items


def load_protocol() -> dict[str, Any]:
    require_file(PROTOCOL_PATH, PROTOCOL_SHA256, "uniqueness protocol")
    spec = load_json(PROTOCOL_PATH)
    order = spec.get("comparison_order") or {}
    alignment = spec.get("candidate_alignment") or {}
    gate = spec.get("exact_gate") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign152_ordered_numeric_uniqueness_protocol"
        and spec.get("status")
        == "all_142_ordered_comparators_frozen_after_coverage_pass_before_any_comparator_value"
        and order.get("count")
        == len(comparison_definitions())
        == EXPECTED_COMPARISON_COUNT
        and order.get("order_sha256") == EXPECTED_COMPARISON_ORDER_SHA256
        and order.get("first_140_design_order_sha256")
        == base.design.FEATURE_ORDER_SHA256
        and order.get("comparator_141")
        == "intraday_return_amount_cumulative_path_signed_area_238p from the verified Campaign136 snapshot"
        and order.get("comparator_142")
        == "intraday_return_amount_cross_spectral_phase_lead_59f from the recovery-verified Campaign146 snapshot"
        and order.get(
            "removal_reorder_subset_early_stop_or_candidate_specific_fill_allowed"
        )
        is False
        and alignment.get("quality_listing_candidate_rows_expected")
        == EXPECTED_QUALITY_LISTING_CANDIDATE_ROWS
        and alignment.get("candidate_value_range")
        == "finite and strictly positive with no upper bound"
        and alignment.get("candidate_missing_fill_allowed") is False
        and alignment.get("numeric140_design_is_a_superset_of_candidate_keys") is True
        and alignment.get(
            "campaign136_and_campaign146_comparators_use_exact_key_intersection_without_fill"
        )
        is True
        and gate.get("minimum_pairwise_names_per_session") == MINIMUM_PAIRWISE_NAMES
        and gate.get("minimum_pairwise_sessions_per_comparison")
        == MINIMUM_PAIRWISE_SESSIONS
        and gate.get("maximum_allowed_absolute_median_daily_rank_correlation")
        == MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION
        and gate.get("strict_inequality") is True
        and gate.get("all_142_must_pass") is True
        and gate.get("insufficient_overlap_fails_closed") is True
        and gate.get("all_results_recorded_without_early_stop") is True
        and boundary.get("comparator_values_read_before_protocol") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
    ):
        raise Campaign152OrderedUniquenessError("uniqueness protocol semantics changed")
    return spec


def validate_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE_PATH.is_file():
        raise Campaign152OrderedUniquenessError(
            "ordered uniqueness implementation freeze is absent"
        )
    record = load_json(IMPLEMENTATION_FREEZE_PATH)
    frozen = record.get("frozen_implementation") or {}
    tests = record.get("synthetic_verification") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign152_ordered_uniqueness_implementation_freeze"
        and record.get("status")
        == "all_142_source_loaders_alignment_and_gate_runner_frozen_before_comparator_values"
        and frozen.get("runner_sha256") == file_sha256(Path(__file__).resolve())
        and frozen.get("test_sha256") == file_sha256(TEST_PATH)
        and frozen.get("protocol_sha256") == PROTOCOL_SHA256
        and frozen.get("coverage_sha256") == COVERAGE_SHA256
        and frozen.get("design_manifest_sha256") == base.DESIGN_MANIFEST_SHA256
        and frozen.get("design_dataset_sha256") == base.DESIGN_DATASET_SHA256
        and frozen.get("campaign136_manifest_sha256") == base.C136_MANIFEST_SHA256
        and frozen.get("campaign136_dataset_sha256") == base.C136_DATASET_SHA256
        and frozen.get("campaign146_manifest_sha256")
        == c146_recovery.SNAPSHOT_MANIFEST_SHA256
        and frozen.get("campaign146_dataset_sha256")
        == c146_recovery.SNAPSHOT_DATASET_SHA256
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
        raise Campaign152OrderedUniquenessError(
            "ordered uniqueness implementation freeze changed"
        )
    return record


def validate_static_bindings() -> dict[str, Any]:
    load_protocol()
    candidate._validate_implementation_freeze()
    design_manifest = base.validate_design_manifest_metadata()
    c136_manifest = base.validate_c136_manifest_metadata()
    freeze = validate_implementation_freeze()
    for path, expected, label in (
        (COVERAGE_PATH, COVERAGE_SHA256, "coverage result"),
        (CANDIDATE_MANIFEST_PATH, CANDIDATE_MANIFEST_SHA256, "candidate manifest"),
        (
            c146_recovery.SNAPSHOT_MANIFEST,
            c146_recovery.SNAPSHOT_MANIFEST_SHA256,
            "Campaign146 comparator manifest",
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
        == "coverage_passed_ready_to_freeze_all_142_ordered_comparator_audit"
        and gate.get("gate_passed_before_comparator_values") is True
        and gate.get("candidate_eligible_rows")
        == EXPECTED_QUALITY_LISTING_CANDIDATE_ROWS
        and result.get("comparator_values_read") is False
        and result.get("numeric_comparator_count_read") == 0
        and result.get("historical_forward_return_fields_read") is False
    ):
        raise Campaign152OrderedUniquenessError("coverage authority changed")
    return {
        "implementation_freeze_sha256": file_sha256(IMPLEMENTATION_FREEZE_PATH),
        "coverage_sha256": COVERAGE_SHA256,
        "candidate_manifest_sha256": CANDIDATE_MANIFEST_SHA256,
        "candidate_dataset_sha256": CANDIDATE_DATASET_SHA256,
        "design_manifest_sha256": base.DESIGN_MANIFEST_SHA256,
        "design_dataset_sha256": base.DESIGN_DATASET_SHA256,
        "design_partition_count": len(design_manifest["files"]),
        "campaign136_manifest_sha256": base.C136_MANIFEST_SHA256,
        "campaign136_dataset_sha256": base.C136_DATASET_SHA256,
        "campaign136_partition_count": len(c136_manifest["partitions"]),
        "campaign146_manifest_sha256": c146_recovery.SNAPSHOT_MANIFEST_SHA256,
        "campaign146_dataset_sha256": c146_recovery.SNAPSHOT_DATASET_SHA256,
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
        "kind": "a_share_three_day_walkforward_campaign152_ordered_uniqueness_plan",
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
        raise Campaign152OrderedUniquenessError("candidate panel columns changed")
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
    if not np.isfinite(finite).all() or (finite <= 0.0).any():
        raise Campaign152OrderedUniquenessError("eligible candidate panel is invalid")
    return quality


def candidate_arrays() -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    load_candidate = coverage._generated["_load_candidate_frame"]
    load_keys = coverage._generated["_quality_listing_eligible_keys"]
    frame = load_candidate(candidate.EXPECTED_ROWS)
    eligible_keys = load_keys()
    quality = eligible_candidate_panel(frame, eligible_keys)
    del frame, eligible_keys
    gc.collect()
    if len(quality) != EXPECTED_QUALITY_LISTING_CANDIDATE_ROWS:
        raise Campaign152OrderedUniquenessError("candidate quality panel changed")
    keys = base.design.compact_stock_day_keys(quality["trade_date"], quality["symbol"])
    values = quality[candidate.FACTOR_NAME].to_numpy(dtype=np.float64)
    order = np.argsort(keys, kind="stable")
    keys = keys[order]
    values = values[order]
    if len(np.unique(keys)) != len(keys):
        raise Campaign152OrderedUniquenessError("candidate keys are not unique")
    return keys, values, {"quality_listing_candidate_rows": len(keys)}


def source_snapshot_comparison(
    *,
    frame: pd.DataFrame,
    factor: str,
    definition: dict[str, str],
    candidate_keys: np.ndarray,
    candidate_values: np.ndarray,
    valid_minimum: float,
    valid_maximum: float | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    eligible_column = f"{factor}_eligible"
    required = {"trade_date", "symbol", factor, eligible_column}
    if not required.issubset(frame.columns):
        raise Campaign152OrderedUniquenessError(f"comparator columns changed: {factor}")
    eligible = frame[eligible_column].astype("boolean").fillna(False).astype(bool)
    values = pd.to_numeric(frame[factor], errors="coerce")
    selected = frame.loc[eligible & values.notna(), ["trade_date", "symbol"]].copy()
    selected[factor] = values.loc[eligible & values.notna()].to_numpy()
    source_values = selected[factor].to_numpy(dtype=np.float64)
    if (
        not np.isfinite(source_values).all()
        or (source_values < valid_minimum).any()
        or (valid_maximum is not None and (source_values > valid_maximum).any())
    ):
        raise Campaign152OrderedUniquenessError(f"comparator values changed: {factor}")
    source_keys = base.design.compact_stock_day_keys(
        selected["trade_date"], selected["symbol"]
    )
    order = np.argsort(source_keys, kind="stable")
    source_keys = source_keys[order]
    source_values = source_values[order]
    if len(np.unique(source_keys)) != len(source_keys):
        raise Campaign152OrderedUniquenessError(f"comparator keys duplicate: {factor}")
    positions = np.searchsorted(source_keys, candidate_keys)
    matched = positions < len(source_keys)
    matched[matched] &= source_keys[positions[matched]] == candidate_keys[matched]
    aligned = np.full(len(candidate_keys), np.nan, dtype=np.float64)
    aligned[matched] = source_values[positions[matched]]
    daily_rows = base.base.daily_rank_rows(candidate_keys, candidate_values, aligned)
    result = base.base.comparison_result(
        definition=definition,
        daily_rows=daily_rows,
    )
    return result, {
        "eligible_source_rows": int(eligible.sum()),
        "matched_candidate_rows": int(matched.sum()),
        "unmatched_candidate_rows": int((~matched).sum()),
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
            raise Campaign152OrderedUniquenessError(
                "ordered uniqueness output already exists"
            ) from exc
    finally:
        temporary.unlink(missing_ok=True)


def run_ordered_uniqueness(*, confirm: bool) -> Path:
    if not confirm:
        raise Campaign152OrderedUniquenessError(
            "ordered uniqueness requires --confirm-run"
        )
    plan = build_plan()
    if plan["ready"] is not True:
        raise Campaign152OrderedUniquenessError("ordered uniqueness plan is not ready")
    definitions = comparison_definitions()
    expected_order = [item["name"] for item in definitions]
    candidate_verification = candidate.verify_snapshot_files(
        CANDIDATE_MANIFEST_PATH, workers=8
    )
    keys, values, candidate_receipt = candidate_arrays()
    design_manifest = base.validate_design_manifest_metadata()
    comparisons, design_receipt = base.audit_numeric140(
        candidate_keys=keys,
        candidate_values=values,
        definitions=definitions[:140],
        manifest=design_manifest,
    )
    c136_frame = base.c136_coverage.load_candidate_frame()
    c136_result, c136_receipt = source_snapshot_comparison(
        frame=c136_frame,
        factor=base.c136_formula.FACTOR_NAME,
        definition=definitions[140],
        candidate_keys=keys,
        candidate_values=values,
        valid_minimum=0.0,
        valid_maximum=None,
    )
    comparisons.append(c136_result)
    del c136_frame
    gc.collect()
    load_c146 = c146_frozen._generated["_load_candidate_frame"]
    c146_frame = load_c146(c146_recovery.EXPECTED_ELIGIBLE_ROWS)
    c146_result, c146_receipt = source_snapshot_comparison(
        frame=c146_frame,
        factor=c146.FACTOR_NAME,
        definition=definitions[141],
        candidate_keys=keys,
        candidate_values=values,
        valid_minimum=-1.0,
        valid_maximum=1.0,
    )
    comparisons.append(c146_result)
    del c146_frame, keys, values
    gc.collect()
    summary = summarize_comparisons(comparisons, expected_order)
    passed = summary["all_required_numeric_comparisons_passed"] is True
    result = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign152_ordered_numeric_uniqueness_audit",
        "status": (
            "all_142_uniqueness_gates_passed_ready_to_freeze_one_development_trial"
            if passed
            else "one_or_more_of_142_uniqueness_gates_failed_terminal_before_returns"
        ),
        "recorded_at": datetime.now(UTC).isoformat(),
        "factor": candidate.FACTOR_NAME,
        "direction": "higher",
        "comparison_order_sha256": EXPECTED_COMPARISON_ORDER_SHA256,
        "static_bindings": plan["static_bindings"],
        "candidate_snapshot_verification": candidate_verification,
        "candidate_receipt": candidate_receipt,
        "design_receipt": design_receipt,
        "campaign136_receipt": c136_receipt,
        "campaign146_receipt": c146_receipt,
        "exact_gate": {
            "minimum_pairwise_names_per_session": MINIMUM_PAIRWISE_NAMES,
            "minimum_pairwise_sessions_per_comparison": MINIMUM_PAIRWISE_SESSIONS,
            "maximum_allowed_absolute_median_daily_rank_correlation": MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION,
            "strict_inequality": True,
            "all_142_must_pass": True,
            "insufficient_overlap_fails_closed": True,
        },
        "comparisons": comparisons,
        "summary": summary,
        "all_142_results_recorded_without_early_stop": len(comparisons)
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
            "freeze exactly one Campaign152 2019-2023 walk-forward development trial before any daily price or return read"
            if passed
            else "terminalize Campaign152 without daily price or return reads and continue with a genuinely new Campaign153 prevalue scout"
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
    except Campaign152OrderedUniquenessError as exc:
        print(
            json.dumps(
                {
                    "ready": False,
                    "error_code": "campaign152_ordered_uniqueness_contract_failure",
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
