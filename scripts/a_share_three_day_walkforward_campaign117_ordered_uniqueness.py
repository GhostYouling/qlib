#!/usr/bin/env python3
"""Run Campaign117's frozen all-134 ordered uniqueness audit without returns."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign110_features as c110
from scripts import (
    a_share_three_day_walkforward_campaign110_no_return_audit as c110_v1,
)
from scripts import (
    a_share_three_day_walkforward_campaign110_no_return_audit_v8 as c110_v8,
)
from scripts import (
    a_share_three_day_walkforward_campaign110_snapshot_verifier as c110_verifier,
)
from scripts import a_share_three_day_walkforward_campaign117_features as candidate
from scripts import (
    a_share_three_day_walkforward_campaign117_no_return_audit as coverage,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_117_ordered_numeric_uniqueness_protocol_20260813.json"
)
PROTOCOL_SHA256 = "fa636becbf72cc67959df5cb3d39dd2fe56f7ff1fc0adb639758f9fce178b35a"
COVERAGE_PATH = coverage.OUTPUT_PATH
COVERAGE_SHA256 = "b794f59f8bbdfb308c91223043b9211fe8514e8755d98637b8c114a9ff1c93a1"
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_117_ordered_uniqueness_implementation_freeze_20260813.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign117_ordered_uniqueness.py"
)
OUTPUT_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_117/uniqueness/campaign117_ordered_uniqueness_audit.json"
)
C110_MANIFEST_PATH = c110.output_root(c110.DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
C110_MANIFEST_SHA256 = (
    "e3ae3c01e0a6eadd8dfce0362520e13bc4c047ff8357cdc7be2d1f9b31e93b72"
)
C110_DATASET_SHA256 = "9082b74891ea2e1c107309637941e42acdc9afeec0b44748e2242506c1a68c4b"
C110_BINDING_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_110_feature_snapshot_binding_20260808.json"
)
C110_BINDING_SHA256 = "35315e56abe2f48abd51177d6ff29b3f5dd6854202675af95fb26d71f493aefe"
CANDIDATE49_SIGNAL_LEDGER = (
    REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
CANDIDATE49_SIGNAL_LEDGER_SHA256 = (
    "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
)
CANDIDATE49_EXECUTION_LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
CANDIDATE49_EXECUTION_LEDGER_SHA256 = (
    "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
)
EXPECTED_COMPARISON_COUNT = 134
MINIMUM_PAIRWISE_NAMES = 50
MINIMUM_PAIRWISE_SESSIONS = 100
MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION = 0.8


class Campaign117OrderedUniquenessError(RuntimeError):
    """Fail closed when the frozen all-134 comparison boundary changes."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def load_protocol() -> dict[str, Any]:
    if not PROTOCOL_PATH.is_file() or _sha256(PROTOCOL_PATH) != PROTOCOL_SHA256:
        raise Campaign117OrderedUniquenessError("uniqueness protocol changed")
    spec = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    order = spec.get("comparison_order") or {}
    gate = spec.get("exact_gate") or {}
    boundary = spec.get("research_boundary") or {}
    definitions = candidate.reconstruct_comparisons()
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign117_ordered_numeric_uniqueness_protocol"
        and spec.get("status")
        == "all_134_ordered_comparators_frozen_after_coverage_pass_before_any_comparator_value"
        and order.get("count") == len(definitions) == EXPECTED_COMPARISON_COUNT
        and order.get("order_sha256") == candidate.NUMERIC_COMPARATOR_ORDER_SHA256
        and definitions[-1] == {"name": c110.FACTOR_NAME, "score_direction": "higher"}
        and gate.get("minimum_pairwise_names_per_session") == MINIMUM_PAIRWISE_NAMES
        and gate.get("minimum_pairwise_sessions_per_comparison")
        == MINIMUM_PAIRWISE_SESSIONS
        and gate.get("maximum_allowed_absolute_median_daily_rank_correlation")
        == MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION
        and gate.get("strict_inequality") is True
        and gate.get("all_134_must_pass") is True
        and gate.get("insufficient_overlap_fails_closed") is True
        and boundary.get("comparator_values_read_before_protocol") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
    ):
        raise Campaign117OrderedUniquenessError("uniqueness protocol semantics changed")
    return spec


def _validate_c110_loader_stack() -> None:
    modules = []
    current: Any = c110_v8
    while hasattr(current, "base"):
        modules.append(current)
        current = current.base
    for module in modules:
        for name in (
            "validate_recovery_adapter_freeze",
            "validate_recovery_implementation_freeze",
            "validate_audit_adapter_freeze",
        ):
            function = getattr(module, name, None)
            if function is not None:
                function()


def _validate_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE_PATH.is_file():
        raise Campaign117OrderedUniquenessError(
            "ordered uniqueness implementation freeze is absent"
        )
    record = json.loads(IMPLEMENTATION_FREEZE_PATH.read_text(encoding="utf-8"))
    frozen = record.get("frozen_implementation") or {}
    test = record.get("synthetic_verification") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign117_ordered_uniqueness_implementation_freeze"
        and record.get("status")
        == "all_134_loader_and_gate_runner_frozen_before_comparator_values"
        and frozen.get("runner_path") == _relative(Path(__file__))
        and frozen.get("runner_sha256") == _sha256(Path(__file__))
        and frozen.get("test_path") == _relative(TEST_PATH)
        and frozen.get("test_sha256") == _sha256(TEST_PATH)
        and frozen.get("protocol_sha256") == PROTOCOL_SHA256
        and frozen.get("coverage_sha256") == COVERAGE_SHA256
        and frozen.get("comparison_count") == EXPECTED_COMPARISON_COUNT
        and frozen.get("comparison_order_sha256")
        == candidate.NUMERIC_COMPARATOR_ORDER_SHA256
        and test.get("passed") == 3
        and test.get("exit_code") == 0
        and boundary.get("comparator_values_read_before_freeze") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
    ):
        raise Campaign117OrderedUniquenessError(
            "ordered uniqueness implementation freeze changed"
        )
    return record


def validate_static_bindings() -> dict[str, Any]:
    load_protocol()
    freeze = _validate_implementation_freeze()
    for path, expected, label in (
        (COVERAGE_PATH, COVERAGE_SHA256, "coverage result"),
        (
            candidate.output_root(candidate.DEFAULT_DATA_ROOT)
            / "snapshot_manifest.json",
            "114bb5dd2ac28d8e51e6a35c234cfe06f7d3810b4d7c46303e38af33d4566879",
            "candidate manifest",
        ),
        (C110_MANIFEST_PATH, C110_MANIFEST_SHA256, "comparator 134 manifest"),
        (C110_BINDING_PATH, C110_BINDING_SHA256, "comparator 134 binding"),
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
        if not path.is_file() or _sha256(path) != expected:
            raise Campaign117OrderedUniquenessError(f"{label} changed: {path}")
    coverage_result = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))
    if not (
        (coverage_result.get("coverage_and_variation") or {}).get(
            "gate_passed_before_comparator_values"
        )
        is True
        and coverage_result.get("comparator_values_read") is False
        and coverage_result.get("numeric_comparator_count_read") == 0
        and coverage_result.get("historical_forward_return_fields_read") is False
    ):
        raise Campaign117OrderedUniquenessError("coverage authority changed")
    _validate_c110_loader_stack()
    c110_verifier.validate_implementation_freeze()
    return {
        "implementation_freeze_sha256": _sha256(IMPLEMENTATION_FREEZE_PATH),
        "coverage_sha256": COVERAGE_SHA256,
        "candidate_manifest_sha256": "114bb5dd2ac28d8e51e6a35c234cfe06f7d3810b4d7c46303e38af33d4566879",
        "comparator_134_manifest_sha256": C110_MANIFEST_SHA256,
        "comparator_134_dataset_sha256": C110_DATASET_SHA256,
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
        "kind": "a_share_three_day_walkforward_campaign117_ordered_uniqueness_plan",
        "ready": not blockers,
        "blockers": blockers,
        "output_path": str(OUTPUT_PATH),
        "comparison_count": EXPECTED_COMPARISON_COUNT,
        "comparison_order_sha256": candidate.NUMERIC_COMPARATOR_ORDER_SHA256,
        "static_bindings": static,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
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


def _candidate_arrays() -> tuple[np.ndarray, np.ndarray, Any, dict[str, Any]]:
    activation = coverage._load_activation()
    expected_eligible = int(activation["candidate_snapshot"]["eligible_rows"])
    frame = coverage._load_candidate_frame(expected_eligible)
    eligible_keys = coverage._quality_listing_eligible_keys()
    quality = eligible_keys[["trade_date", "symbol"]].merge(
        frame[["trade_date", "symbol", candidate.FACTOR_NAME]],
        on=["trade_date", "symbol"],
        how="inner",
        validate="one_to_one",
    )
    del frame, eligible_keys
    gc.collect()
    if len(quality) != 1_330_171 or quality[candidate.FACTOR_NAME].isna().any():
        raise Campaign117OrderedUniquenessError("candidate quality panel changed")
    from scripts import (  # noqa: PLC0415
        a_share_three_day_walkforward_campaign105_no_return_audit as c105_audit,
    )

    context = (
        c105_audit.cache_v4.v1.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    )
    _prior, _foundation, engine, _, _, comparison_engine = context
    keys, values = engine._sorted_candidate_arrays(quality, candidate.FACTOR_NAME)
    del quality
    gc.collect()
    return (
        keys,
        values,
        comparison_engine,
        {"quality_listing_candidate_rows": len(keys)},
    )


def _load_final_comparator(
    *,
    candidate_keys: np.ndarray,
    candidate_values: np.ndarray,
    gate: dict[str, Any],
    comparison_engine: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    verification = c110_verifier.verify_snapshot_files(C110_MANIFEST_PATH, workers=4)
    if not (
        verification.get("manifest_sha256") == C110_MANIFEST_SHA256
        and verification.get("dataset_sha256") == C110_DATASET_SHA256
        and verification.get("rows") == candidate.EXPECTED_ROWS
    ):
        raise Campaign117OrderedUniquenessError("comparator 134 snapshot changed")
    manifest = json.loads(C110_MANIFEST_PATH.read_text(encoding="utf-8"))
    context = c110_v1.c107_audit._generated[
        "cache_v4"
    ].v1.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    engine = context[2]
    ranges = dict(getattr(engine, "FACTOR_RANGES", {}))
    ranges[c110.FACTOR_NAME] = (-1.0, 1.0)
    engine.FACTOR_RANGES = ranges
    frame = engine.load_factor_frame(C110_MANIFEST_PATH, manifest, c110.FACTOR_NAME)
    source_keys, source_values = c110_v1.adapter.sorted_raw_comparator_arrays(
        frame,
        factor=c110.FACTOR_NAME,
        value_range=(-1.0, 1.0),
        compact_key_fn=comparison_engine._compact_stock_day_keys,
    )
    del frame
    gc.collect()
    aligned = c110_v1.adapter.align_raw_comparator_values(
        source_keys=source_keys,
        source_values=source_values,
        target_keys=candidate_keys,
    )
    legal_nan_count = int(np.isnan(aligned).sum())
    result = comparison_engine._aligned_comparison_result(
        candidate_keys=candidate_keys,
        candidate_values=candidate_values,
        comparison_values=aligned,
        comparison=c110.FACTOR_NAME,
        direction="higher",
        gate=gate,
    )
    result["source_score_direction"] = "higher"
    result["comparison_value_semantics"] = "frozen Campaign110 raw factor value"
    result["aligned_legal_nan_count_before_pairwise_overlap"] = legal_nan_count
    return result, {
        "manifest_path": str(C110_MANIFEST_PATH),
        "manifest_sha256": C110_MANIFEST_SHA256,
        "dataset_sha256": C110_DATASET_SHA256,
        "binding_sha256": C110_BINDING_SHA256,
        "verification": verification,
        "legal_nan_preserved_count": legal_nan_count,
    }


def run_ordered_uniqueness(*, confirm: bool) -> Path:
    if not confirm:
        raise Campaign117OrderedUniquenessError(
            "ordered uniqueness requires --confirm-run"
        )
    plan = build_plan()
    if plan["ready"] is not True:
        raise Campaign117OrderedUniquenessError("ordered uniqueness plan is not ready")
    definitions = candidate.reconstruct_comparisons()
    expected_order = [item["name"] for item in definitions]
    gate = {
        "minimum_pairwise_names_per_session": MINIMUM_PAIRWISE_NAMES,
        "minimum_pairwise_sessions_per_comparison": MINIMUM_PAIRWISE_SESSIONS,
        "maximum_allowed_absolute_median_daily_rank_correlation": MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION,
        "all_numeric_comparators_must_pass": True,
        "insufficient_pairwise_overlap_fails_closed": True,
        "raw_comparator_nan_preserved_until_pairwise_overlap": True,
    }
    keys, values, comparison_engine, candidate_receipt = _candidate_arrays()
    first_results, receipts = c110_v1._load_comparisons_after_coverage(
        coverage={"gate_passed_before_comparison_values": True},
        candidate_keys=keys,
        candidate_values=values,
        gate=gate,
        comparison_engine=comparison_engine,
    )
    if [item["comparison_factor"] for item in first_results] != expected_order[:133]:
        raise Campaign117OrderedUniquenessError("first 133 comparator order changed")
    final_result, final_receipt = _load_final_comparator(
        candidate_keys=keys,
        candidate_values=values,
        gate=gate,
        comparison_engine=comparison_engine,
    )
    results = [*first_results, final_result]
    summary = summarize_comparisons(results, expected_order)
    admitted = summary["all_required_numeric_comparisons_passed"] is True
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign117_ordered_uniqueness_audit",
        "status": (
            "all_134_uniqueness_gates_passed_ready_to_freeze_one_development_trial"
            if admitted
            else "uniqueness_failed_terminal_before_historical_daily_prices_or_returns"
        ),
        "recorded_at": datetime.now(UTC).isoformat(),
        "factor": candidate.FACTOR_NAME,
        "direction": "higher",
        "static_bindings": plan["static_bindings"],
        "candidate_receipt": candidate_receipt,
        "comparison_summary": summary,
        "comparisons": results,
        "comparison_source_verification": {
            "first_133": receipts,
            "comparator_134": final_receipt,
            "all_134_sources_loaded_in_frozen_order": True,
        },
        "admissible_factor_names": [candidate.FACTOR_NAME] if admitted else [],
        "admissible_factor_count": 1 if admitted else 0,
        "failed_factor_names": [] if admitted else [candidate.FACTOR_NAME],
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "development_trial_count": 0,
        "stress_2024_2025_opened": False,
        "provider_request_issued": False,
        "candidate49_historical_backfill_performed": False,
        "candidate49_ledgers_changed": False,
        "current_scoring_selection_sizing_positions_or_orders_performed": False,
        "investment_advice": False,
        "next_action": (
            "freeze exactly one 2019-2023 development activation before daily prices or returns"
            if admitted
            else "terminalize Campaign117 and begin only a genuinely new campaign"
        ),
    }
    coverage._atomic_exclusive_json(OUTPUT_PATH, record)
    return OUTPUT_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "run"))
    parser.add_argument("--confirm-run", action="store_true")
    args = parser.parse_args()
    if args.command == "plan":
        value = build_plan()
        print(json.dumps(value, sort_keys=True))
        return 0 if value["ready"] else 2
    path = run_ordered_uniqueness(confirm=args.confirm_run)
    print(json.dumps({"uniqueness_audit_path": str(path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
