#!/usr/bin/env python3
"""Run Campaign117's frozen coverage-first no-return audit."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.dataset as pa_dataset

from scripts import a_share_three_day_walkforward_campaign117_features as candidate


REPO_ROOT = Path(__file__).resolve().parents[1]
FACTOR_NAME = candidate.FACTOR_NAME
DEFAULT_DATA_ROOT = candidate.DEFAULT_DATA_ROOT
SNAPSHOT_MANIFEST_PATH = (
    candidate.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
)
ACTIVATION_BINDING_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_117_coverage_activation_binding_20260813.json"
)
OUTPUT_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_117/coverage/campaign117_coverage_audit.json"
)
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

MINIMUM_MEDIAN_COVERAGE = 0.95
MINIMUM_P05_COVERAGE = 0.90
MINIMUM_P05_ELIGIBLE_NAMES = 50
MINIMUM_NON_OVERLAPPING_COHORTS = 200
MINIMUM_OBSERVED_COHORT_YEARS = 5
MINIMUM_NONCONSTANT_CROSS_SECTIONAL_SESSIONS = 200
HOLDING_PERIOD_SESSIONS = 3


class Campaign117NoReturnAuditError(RuntimeError):
    """Fail closed when Campaign117's ordered no-return boundary changes."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    target = path.expanduser().resolve()
    if not target.is_file() or _sha256(target) != expected:
        raise Campaign117NoReturnAuditError(f"{label} fingerprint changed: {target}")


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Campaign117NoReturnAuditError(f"expected JSON object: {path}")
    return value


def _relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def expected_gate() -> dict[str, Any]:
    return {
        "holding_period_sessions": HOLDING_PERIOD_SESSIONS,
        "minimum_median_daily_coverage": MINIMUM_MEDIAN_COVERAGE,
        "minimum_p05_daily_coverage": MINIMUM_P05_COVERAGE,
        "minimum_p05_eligible_names": MINIMUM_P05_ELIGIBLE_NAMES,
        "minimum_non_overlapping_three_signal_session_cohorts": MINIMUM_NON_OVERLAPPING_COHORTS,
        "minimum_observed_cohort_years": MINIMUM_OBSERVED_COHORT_YEARS,
        "minimum_nonconstant_cross_sectional_sessions": MINIMUM_NONCONSTANT_CROSS_SECTIONAL_SESSIONS,
        "cross_sectional_distinctness": "exact finite float values without rounding tolerance or binning",
    }


def load_protocol() -> dict[str, Any]:
    spec = candidate.load_protocol()
    gates = list(spec.get("ordered_no_return_gates") or [])
    if [item.get("gate") for item in gates] != [1, 2, 3]:
        raise Campaign117NoReturnAuditError("Campaign117 gate order changed")
    coverage_text = str(gates[1].get("rule") or "")
    uniqueness_text = str(gates[2].get("rule") or "")
    if not (
        ">=0.95" in coverage_text
        and ">=0.90" in coverage_text
        and ">=50" in coverage_text
        and "at least 200" in coverage_text
        and "at least five" in coverage_text
        and "all 134" in uniqueness_text
        and "at least 50" in uniqueness_text
        and "at least 100" in uniqueness_text
        and "strictly below 0.8" in uniqueness_text
    ):
        raise Campaign117NoReturnAuditError("Campaign117 numeric gate text changed")
    return spec


def _load_activation() -> dict[str, Any]:
    candidate._validate_implementation_freeze()
    if not ACTIVATION_BINDING_PATH.is_file():
        raise Campaign117NoReturnAuditError("Campaign117 coverage activation is absent")
    record = _load_json(ACTIVATION_BINDING_PATH)
    implementation = record.get("implementation_freeze") or {}
    snapshot = record.get("candidate_snapshot") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign117_coverage_activation_binding"
        and record.get("status")
        == "frozen_after_verified_snapshot_before_candidate_coverage_values"
        and implementation.get("path")
        == _relative(candidate.DEFAULT_IMPLEMENTATION_FREEZE)
        and implementation.get("sha256")
        == _sha256(candidate.DEFAULT_IMPLEMENTATION_FREEZE)
        and snapshot.get("path") == str(SNAPSHOT_MANIFEST_PATH.resolve())
        and len(str(snapshot.get("sha256") or "")) == 64
        and len(str(snapshot.get("dataset_sha256") or "")) == 64
        and snapshot.get("partitions") == candidate.EXPECTED_PARTITIONS
        and snapshot.get("rows") == candidate.EXPECTED_ROWS
        and 0 <= int(snapshot.get("eligible_rows", -1)) <= candidate.EXPECTED_ROWS
        and record.get("coverage_gate") == expected_gate()
        and record.get("numeric_comparator_count") == 134
        and record.get("numeric_comparator_order_sha256")
        == candidate.NUMERIC_COMPARATOR_ORDER_SHA256
        and record.get("output_path") == _relative(OUTPUT_PATH)
        and record.get("single_use") is True
        and boundary.get("candidate_snapshot_values_read_before_activation") is False
        and boundary.get("comparator_values_read_before_activation") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("credential_loaded") is False
    ):
        raise Campaign117NoReturnAuditError("Campaign117 activation semantics changed")
    return record


def validate_static_bindings() -> dict[str, Any]:
    activation = _load_activation()
    snapshot = activation["candidate_snapshot"]
    for path, expected, label in (
        (SNAPSHOT_MANIFEST_PATH, str(snapshot["sha256"]), "candidate manifest"),
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
        _require(path, expected, label)
    return {
        "implementation_freeze_sha256": activation["implementation_freeze"]["sha256"],
        "activation_binding_sha256": _sha256(ACTIVATION_BINDING_PATH),
        "candidate_manifest_sha256": snapshot["sha256"],
        "candidate_dataset_sha256": snapshot["dataset_sha256"],
        "candidate49_signal_ledger_sha256": CANDIDATE49_SIGNAL_LEDGER_SHA256,
        "candidate49_execution_ledger_sha256": CANDIDATE49_EXECUTION_LEDGER_SHA256,
        "candidate_values_read": False,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
        "credential_loaded": False,
    }


def build_plan(output_path: Path = OUTPUT_PATH) -> dict[str, Any]:
    static = validate_static_bindings()
    target = output_path.expanduser().resolve()
    blockers = ["coverage_audit_output_already_exists"] if target.exists() else []
    return {
        "kind": "a_share_three_day_walkforward_campaign117_coverage_audit_plan",
        "ready": not blockers,
        "blockers": blockers,
        "output_path": str(target),
        "coverage_gate": expected_gate(),
        "static_bindings": static,
        "candidate_values_read": False,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
        "credential_loaded": False,
    }


def _daily_frame_sha256(daily: pd.DataFrame) -> str:
    digest = hashlib.sha256()
    for row in daily.itertuples(index=False):
        digest.update(
            (
                f"{pd.Timestamp(row.trade_date).date().isoformat()}|"
                f"{int(row.quality_listing_eligible_names)}|"
                f"{int(row.candidate_eligible_names)}|"
                f"{float(row.coverage).hex()}|"
                f"{int(row.distinct_candidate_values)}\n"
            ).encode("utf-8")
        )
    return digest.hexdigest()


def coverage_and_variation(
    candidate_frame: pd.DataFrame,
    eligible_keys: pd.DataFrame,
    *,
    factor: str = FACTOR_NAME,
) -> dict[str, Any]:
    required_candidate = {
        "trade_date",
        "symbol",
        factor,
        f"{factor}_eligible",
    }
    if not required_candidate.issubset(candidate_frame.columns):
        raise Campaign117NoReturnAuditError("candidate coverage columns changed")
    if not {"trade_date", "symbol"}.issubset(eligible_keys.columns):
        raise Campaign117NoReturnAuditError("eligible-key columns changed")
    left = eligible_keys[["trade_date", "symbol"]].copy()
    right = candidate_frame[list(required_candidate)].copy()
    for frame in (left, right):
        frame["trade_date"] = pd.to_datetime(
            frame["trade_date"], errors="coerce"
        ).dt.normalize()
        frame["symbol"] = frame["symbol"].astype(str).str.upper()
    if (
        left[["trade_date", "symbol"]].isna().any().any()
        or right[["trade_date", "symbol"]].isna().any().any()
        or left.duplicated(["trade_date", "symbol"]).any()
        or right.duplicated(["trade_date", "symbol"]).any()
    ):
        raise Campaign117NoReturnAuditError("coverage identities are invalid")
    merged = left.merge(
        right,
        on=["trade_date", "symbol"],
        how="left",
        validate="one_to_one",
    )
    numeric = pd.to_numeric(merged[factor], errors="coerce")
    declared = merged[f"{factor}_eligible"].astype("boolean").fillna(False).astype(bool)
    candidate_eligible = declared & numeric.notna()
    finite_values = numeric.loc[candidate_eligible].to_numpy(dtype=np.float64)
    if (
        not np.isfinite(finite_values).all()
        or (finite_values < 0.0).any()
        or (finite_values > 1.0).any()
        or numeric.loc[~declared].notna().any()
    ):
        raise Campaign117NoReturnAuditError("coverage candidate values are invalid")
    merged[factor] = numeric
    denominators = merged.groupby("trade_date", observed=True, sort=True).size()
    numerators = (
        merged.loc[candidate_eligible]
        .groupby("trade_date", observed=True, sort=True)
        .size()
        .reindex(denominators.index, fill_value=0)
    )
    distinct = (
        merged.loc[candidate_eligible]
        .groupby("trade_date", observed=True, sort=True)[factor]
        .nunique(dropna=True)
        .reindex(denominators.index, fill_value=0)
    )
    ratios = numerators / denominators
    indices = np.arange(
        0,
        max(len(denominators) - HOLDING_PERIOD_SESSIONS, 0),
        HOLDING_PERIOD_SESSIONS,
    )
    potential_mask = numerators.iloc[indices].ge(MINIMUM_P05_ELIGIBLE_NAMES)
    potential = int(potential_mask.sum())
    cohort_years = sorted(
        int(value)
        for value in pd.DatetimeIndex(
            numerators.index[indices][potential_mask]
        ).year.unique()
    )
    variation_mask = distinct.ge(2)
    variation_sessions = int(variation_mask.sum())
    variation_years = sorted(
        int(value)
        for value in pd.DatetimeIndex(distinct.index[variation_mask]).year.unique()
    )
    median = float(ratios.median())
    p05 = float(ratios.quantile(0.05))
    names_p05 = float(numerators.quantile(0.05))
    base_passed = bool(
        median >= MINIMUM_MEDIAN_COVERAGE
        and p05 >= MINIMUM_P05_COVERAGE
        and names_p05 >= MINIMUM_P05_ELIGIBLE_NAMES
        and potential >= MINIMUM_NON_OVERLAPPING_COHORTS
        and len(cohort_years) >= MINIMUM_OBSERVED_COHORT_YEARS
    )
    variation_passed = bool(
        variation_sessions >= MINIMUM_NONCONSTANT_CROSS_SECTIONAL_SESSIONS
    )
    daily = pd.DataFrame(
        {
            "trade_date": denominators.index,
            "quality_listing_eligible_names": denominators.to_numpy(dtype=int),
            "candidate_eligible_names": numerators.to_numpy(dtype=int),
            "coverage": ratios.to_numpy(dtype=float),
            "distinct_candidate_values": distinct.to_numpy(dtype=int),
        }
    )
    if daily.empty or not all(
        math.isfinite(value) for value in (median, p05, names_p05)
    ):
        raise Campaign117NoReturnAuditError("coverage aggregate is invalid")
    return {
        "quality_listing_eligible_rows": int(len(left)),
        "candidate_eligible_rows": int(candidate_eligible.sum()),
        "calendar_sessions": int(len(denominators)),
        "median_daily_coverage": median,
        "p05_daily_coverage": p05,
        "eligible_names_minimum": int(numerators.min()),
        "eligible_names_p05": names_p05,
        "eligible_names_median": float(numerators.median()),
        "potential_non_overlapping_three_signal_session_cohorts": potential,
        "observed_cohort_years": cohort_years,
        "nonconstant_cross_sectional_sessions": variation_sessions,
        "observed_nonconstant_cross_sectional_years": variation_years,
        "maximum_distinct_candidate_values_in_one_session": int(distinct.max()),
        "coverage_capacity_gate_passed": base_passed,
        "cross_sectional_variation_gate_passed": variation_passed,
        "gate_passed_before_comparator_values": bool(base_passed and variation_passed),
        "daily_aggregate_frame_sha256": _daily_frame_sha256(daily),
        "coverage_gate": expected_gate(),
    }


def _load_candidate_frame(expected_eligible: int) -> pd.DataFrame:
    manifest = _load_json(SNAPSHOT_MANIFEST_PATH)
    paths = [str(Path(str(item["path"])).resolve()) for item in manifest["files"]]
    dataset = pa_dataset.dataset(paths, format="parquet")
    columns = [
        "trade_date",
        "symbol",
        FACTOR_NAME,
        f"{FACTOR_NAME}_eligible",
    ]
    table = dataset.to_table(columns=columns, use_threads=True)
    frame = table.to_pandas(split_blocks=True, self_destruct=True)
    del table, dataset
    gc.collect()
    if len(frame) != candidate.EXPECTED_ROWS:
        raise Campaign117NoReturnAuditError("candidate frame row count changed")
    eligible = (
        frame[f"{FACTOR_NAME}_eligible"].astype("boolean").fillna(False).astype(bool)
    )
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    finite = values.loc[eligible].to_numpy(dtype=np.float64)
    if (
        int(eligible.sum()) != expected_eligible
        or not np.isfinite(finite).all()
        or (finite < 0.0).any()
        or (finite > 1.0).any()
        or values.loc[~eligible].notna().any()
    ):
        raise Campaign117NoReturnAuditError("candidate value semantics changed")
    frame[FACTOR_NAME] = values
    frame[f"{FACTOR_NAME}_eligible"] = eligible
    return frame


def _quality_listing_eligible_keys() -> pd.DataFrame:
    from scripts import (  # noqa: PLC0415
        a_share_three_day_walkforward_campaign105_no_return_audit as c105,
    )

    context = (
        c105.cache_v4.v1.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    )
    prior, foundation, _, _, _, _ = context
    return foundation.quality_listing_eligible_keys(prior.load_protocol())


def _atomic_exclusive_json(path: Path, value: dict[str, Any]) -> None:
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
        except FileExistsError as error:
            raise Campaign117NoReturnAuditError(
                "coverage audit output already exists"
            ) from error
    finally:
        temporary.unlink(missing_ok=True)


def run_coverage_audit(*, workers: int, confirm: bool) -> Path:
    if not confirm:
        raise Campaign117NoReturnAuditError(
            "coverage audit requires --confirm-coverage-audit"
        )
    plan = build_plan()
    if plan["ready"] is not True:
        raise Campaign117NoReturnAuditError("coverage audit plan is not ready")
    activation = _load_activation()
    snapshot_verification = candidate.verify_snapshot_files(
        SNAPSHOT_MANIFEST_PATH, workers=workers
    )
    expected_eligible = int(activation["candidate_snapshot"]["eligible_rows"])
    candidate_frame = _load_candidate_frame(expected_eligible)
    eligible_keys = _quality_listing_eligible_keys()
    coverage = coverage_and_variation(candidate_frame, eligible_keys)
    del candidate_frame, eligible_keys
    gc.collect()
    passed = coverage["gate_passed_before_comparator_values"] is True
    result = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign117_coverage_audit",
        "status": (
            "coverage_passed_ready_to_freeze_all_134_ordered_comparator_audit"
            if passed
            else "coverage_failed_terminal_before_all_comparator_values"
        ),
        "recorded_at": datetime.now(UTC).isoformat(),
        "factor": FACTOR_NAME,
        "direction": "higher",
        "static_bindings": plan["static_bindings"],
        "snapshot_verification": snapshot_verification,
        "coverage_and_variation": coverage,
        "comparator_values_read": False,
        "numeric_comparator_count_read": 0,
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "stress_2024_2025_opened": False,
        "training_or_model_fitting_performed": False,
        "provider_request_issued": False,
        "credential_loaded": False,
        "candidate49_historical_backfill_performed": False,
        "candidate49_ledgers_changed": False,
        "second_prospective_candidate_created": False,
        "current_scoring_selection_sizing_positions_or_orders_performed": False,
        "investment_advice": False,
        "next_action": (
            "freeze an exact all-134 ordered no-return comparator audit before reading any comparator value"
            if passed
            else "terminalize Campaign117 without reading comparator values, daily prices, or returns"
        ),
    }
    _atomic_exclusive_json(OUTPUT_PATH, result)
    return OUTPUT_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--workers", type=int, default=4)
    run_parser.add_argument("--confirm-coverage-audit", action="store_true")
    args = parser.parse_args()
    if args.command == "plan":
        value = build_plan()
        print(json.dumps(value, ensure_ascii=False, sort_keys=True))
        return 0 if value["ready"] else 2
    path = run_coverage_audit(
        workers=args.workers,
        confirm=args.confirm_coverage_audit,
    )
    print(json.dumps({"coverage_audit_path": str(path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
