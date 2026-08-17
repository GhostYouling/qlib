#!/usr/bin/env python3
"""Run Campaign136's frozen structural coverage gate before comparators."""

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
import pyarrow.dataset as pa_dataset

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import a_share_three_day_walkforward_campaign136_features as candidate
from scripts import a_share_three_day_walkforward_campaign136_formula as formula


REPO_ROOT = Path(__file__).resolve().parents[1]
FACTOR_NAME = formula.FACTOR_NAME
SNAPSHOT_ROOT = candidate.DEFAULT_OUTPUT_ROOT
SNAPSHOT_MANIFEST_PATH = SNAPSHOT_ROOT / candidate.MANIFEST_NAME
SNAPSHOT_MANIFEST_SHA256 = (
    "9a5c9ff824de22af6595d312b76230a3e4cf283c6e1d42e882aae96d11367b93"
)
SNAPSHOT_DATASET_SHA256 = (
    "c84b1f85eec3731736a4da411691c144a70a81e38b5013e5aeea5370f3c417ec"
)
SNAPSHOT_ROWS = 7751950
SNAPSHOT_ELIGIBLE_ROWS = 7750120
SOURCE_PUBLICATION_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_136_source_snapshot_publication_20260814.json"
)
SOURCE_PUBLICATION_SHA256 = (
    "27bfda432f405248021068ebc275b2cca679c8e8bd49bed0e388f73c3b32b232"
)
COVERAGE_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_136_coverage_implementation_freeze_20260814.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign136_coverage_audit.py"
)
OUTPUT_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_136/coverage/campaign136_coverage_audit.json"
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
NUMERIC_COMPARATOR_COUNT = 140
NUMERIC_COMPARATOR_ORDER_SHA256 = (
    "c71bfe27486c9567afd3aca21e4b04053658c23ac651e7f4df7fd014b0c31efd"
)


class Campaign136CoverageAuditError(RuntimeError):
    """Fail closed when a Campaign136 coverage invariant changes."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_file(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or file_sha256(path) != expected:
        raise Campaign136CoverageAuditError(f"Campaign136 {label} binding changed")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Campaign136CoverageAuditError(f"expected JSON object: {path}")
    return value


def relative(path: Path) -> str:
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
        "candidate_value_range": "finite [0,+infinity)",
        "cross_sectional_distinctness": "exact finite float values without rounding tolerance or binning",
    }


def load_protocol() -> dict[str, Any]:
    try:
        spec = formula.load_protocol()
    except formula.Campaign136FormulaError as exc:
        raise Campaign136CoverageAuditError(str(exc)) from exc
    gates = list(spec.get("ordered_no_return_gates") or [])
    coverage_text = str(gates[1].get("rule") or "") if len(gates) == 3 else ""
    uniqueness_text = str(gates[2].get("rule") or "") if len(gates) == 3 else ""
    if not (
        [item.get("gate") for item in gates] == [1, 2, 3]
        and ">=0.95" in coverage_text
        and ">=0.90" in coverage_text
        and ">=50" in coverage_text
        and "at least 200" in coverage_text
        and "at least five" in coverage_text
        and "finite and nonnegative" in coverage_text
        and "all 140" in uniqueness_text
        and "at least 50" in uniqueness_text
        and "at least 100" in uniqueness_text
        and "strictly below 0.8" in uniqueness_text
    ):
        raise Campaign136CoverageAuditError("Campaign136 numeric gate text changed")
    return spec


def validate_source_publication() -> dict[str, Any]:
    require_file(SOURCE_PUBLICATION_PATH, SOURCE_PUBLICATION_SHA256, "publication")
    record = load_json(SOURCE_PUBLICATION_PATH)
    run = record.get("confirmed_run") or {}
    verification = record.get("read_only_verification") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign136_source_snapshot_publication"
        and record.get("status")
        == "immutable_candidate_snapshot_published_and_read_only_verified_before_coverage"
        and run.get("output_manifest_path") == relative(SNAPSHOT_MANIFEST_PATH)
        and run.get("output_manifest_sha256") == SNAPSHOT_MANIFEST_SHA256
        and run.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and run.get("partitions") == 5396
        and run.get("rows") == SNAPSHOT_ROWS
        and run.get("eligible_rows") == SNAPSHOT_ELIGIBLE_ROWS
        and run.get("source_fields_read") == list(candidate.SOURCE_COLUMNS)
        and run.get("historical_daily_ohlcv_fields_read") == []
        and verification.get("exit_code") == 0
        and verification.get("manifest_sha256") == SNAPSHOT_MANIFEST_SHA256
        and verification.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and boundary.get("comparison_values_read") is False
        and boundary.get("historical_daily_ohlcv_fields_read") == []
        and boundary.get("historical_forward_returns_read") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign136CoverageAuditError("Campaign136 publication semantics changed")
    return record


def validate_coverage_freeze() -> dict[str, Any]:
    if not COVERAGE_FREEZE_PATH.is_file():
        raise Campaign136CoverageAuditError("Campaign136 coverage freeze is absent")
    record = load_json(COVERAGE_FREEZE_PATH)
    frozen = record.get("frozen_implementation") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign136_coverage_implementation_freeze"
        and record.get("status")
        == "coverage_only_runner_frozen_before_candidate_coverage_values"
        and frozen.get("runner_sha256") == file_sha256(Path(__file__).resolve())
        and frozen.get("test_sha256") == file_sha256(TEST_PATH)
        and frozen.get("source_publication_sha256") == SOURCE_PUBLICATION_SHA256
        and frozen.get("snapshot_manifest_sha256") == SNAPSHOT_MANIFEST_SHA256
        and frozen.get("snapshot_dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and frozen.get("snapshot_rows") == SNAPSHOT_ROWS
        and frozen.get("snapshot_eligible_rows") == SNAPSHOT_ELIGIBLE_ROWS
        and frozen.get("expected_gate") == expected_gate()
        and frozen.get("numeric_comparator_count") == NUMERIC_COMPARATOR_COUNT
        and frozen.get("numeric_comparator_order_sha256")
        == NUMERIC_COMPARATOR_ORDER_SHA256
        and frozen.get("output_path") == relative(OUTPUT_PATH)
        and boundary.get("candidate_coverage_values_read_before_freeze") is False
        and boundary.get("comparator_values_read") is False
        and boundary.get("historical_daily_ohlcv_fields_read") == []
        and boundary.get("historical_forward_returns_read") is False
    ):
        raise Campaign136CoverageAuditError("Campaign136 coverage freeze changed")
    return record


def validate_static_bindings() -> dict[str, Any]:
    load_protocol()
    candidate.validate_implementation_freeze()
    publication = validate_source_publication()
    freeze = validate_coverage_freeze()
    for path, expected, label in (
        (SNAPSHOT_MANIFEST_PATH, SNAPSHOT_MANIFEST_SHA256, "snapshot manifest"),
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
    return {
        "source_publication_sha256": SOURCE_PUBLICATION_SHA256,
        "candidate_manifest_sha256": SNAPSHOT_MANIFEST_SHA256,
        "candidate_dataset_sha256": SNAPSHOT_DATASET_SHA256,
        "coverage_implementation_freeze_sha256": file_sha256(COVERAGE_FREEZE_PATH),
        "candidate49_signal_ledger_sha256": CANDIDATE49_SIGNAL_LEDGER_SHA256,
        "candidate49_execution_ledger_sha256": CANDIDATE49_EXECUTION_LEDGER_SHA256,
        "candidate_values_read": False,
        "comparator_values_read": False,
        "historical_daily_ohlcv_fields_read": [],
        "historical_forward_returns_read": False,
        "provider_request_issued": False,
        "publication_status": publication["status"],
        "freeze_status": freeze["status"],
    }


def build_plan(output_path: Path = OUTPUT_PATH) -> dict[str, Any]:
    static = validate_static_bindings()
    target = output_path.resolve()
    blockers = ["coverage_audit_output_already_exists"] if target.exists() else []
    return {
        "kind": "a_share_three_day_walkforward_campaign136_coverage_audit_plan",
        "ready": not blockers,
        "blockers": blockers,
        "output_path": str(target),
        "coverage_gate": expected_gate(),
        "static_bindings": static,
        "candidate_values_read": False,
        "comparator_values_read": False,
        "historical_daily_ohlcv_fields_read": [],
        "historical_forward_returns_read": False,
        "provider_request_issued": False,
    }


def daily_frame_sha256(daily: pd.DataFrame) -> str:
    rows = [
        [
            pd.Timestamp(item.trade_date).date().isoformat(),
            int(item.quality_listing_eligible_names),
            int(item.candidate_eligible_names),
            float(item.coverage),
            int(item.distinct_candidate_values),
        ]
        for item in daily.itertuples(index=False)
    ]
    payload = json.dumps(
        rows,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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
        raise Campaign136CoverageAuditError("candidate coverage columns changed")
    if not {"trade_date", "symbol"}.issubset(eligible_keys.columns):
        raise Campaign136CoverageAuditError("eligible-key columns changed")
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
        raise Campaign136CoverageAuditError("coverage identities are invalid")
    right_values = pd.to_numeric(right[factor], errors="coerce")
    right_declared = (
        right[f"{factor}_eligible"].astype("boolean").fillna(False).astype(bool)
    )
    finite = right_values.loc[right_declared].to_numpy(dtype=np.float64)
    if (
        not np.isfinite(finite).all()
        or (finite < 0.0).any()
        or right_values.loc[~right_declared].notna().any()
    ):
        raise Campaign136CoverageAuditError("coverage candidate values are invalid")
    right[factor] = right_values
    right[f"{factor}_eligible"] = right_declared
    merged = left.merge(
        right,
        on=["trade_date", "symbol"],
        how="left",
        validate="one_to_one",
    )
    numeric = pd.to_numeric(merged[factor], errors="coerce")
    declared = merged[f"{factor}_eligible"].astype("boolean").fillna(False).astype(bool)
    if declared.any() and numeric.loc[declared].isna().any():
        raise Campaign136CoverageAuditError("declared candidate value is missing")
    merged[factor] = numeric
    denominators = merged.groupby("trade_date", observed=True, sort=True).size()
    numerators = (
        merged.loc[declared]
        .groupby("trade_date", observed=True, sort=True)
        .size()
        .reindex(denominators.index, fill_value=0)
    )
    distinct = (
        merged.loc[declared]
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
        raise Campaign136CoverageAuditError("coverage aggregate is invalid")
    return {
        "quality_listing_eligible_rows": int(len(left)),
        "candidate_eligible_rows": int(declared.sum()),
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
        "daily_aggregate_frame_sha256": daily_frame_sha256(daily),
        "coverage_gate": expected_gate(),
    }


def load_candidate_frame() -> pd.DataFrame:
    manifest = load_json(SNAPSHOT_MANIFEST_PATH)
    paths = [str(SNAPSHOT_ROOT / str(item["path"])) for item in manifest["partitions"]]
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
    if len(frame) != SNAPSHOT_ROWS:
        raise Campaign136CoverageAuditError("candidate frame row count changed")
    eligible = (
        frame[f"{FACTOR_NAME}_eligible"].astype("boolean").fillna(False).astype(bool)
    )
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    finite = values.loc[eligible].to_numpy(dtype=np.float64)
    if (
        int(eligible.sum()) != SNAPSHOT_ELIGIBLE_ROWS
        or not np.isfinite(finite).all()
        or (finite < 0.0).any()
        or values.loc[~eligible].notna().any()
    ):
        raise Campaign136CoverageAuditError("candidate value semantics changed")
    frame[FACTOR_NAME] = values
    frame[f"{FACTOR_NAME}_eligible"] = eligible
    return frame


def quality_listing_eligible_keys() -> pd.DataFrame:
    from scripts import (  # noqa: PLC0415
        a_share_three_day_walkforward_campaign117_no_return_audit as base,
    )

    return base._quality_listing_eligible_keys()


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
            raise Campaign136CoverageAuditError(
                "coverage audit output already exists"
            ) from exc
    finally:
        temporary.unlink(missing_ok=True)


def run_coverage_audit(*, confirm: bool) -> Path:
    if not confirm:
        raise Campaign136CoverageAuditError(
            "coverage audit requires --confirm-coverage-audit"
        )
    plan = build_plan()
    if plan["ready"] is not True:
        raise Campaign136CoverageAuditError("coverage audit plan is not ready")
    snapshot_verification = candidate.verify_snapshot(verify_source=True)
    candidate_frame = load_candidate_frame()
    eligible_keys = quality_listing_eligible_keys()
    coverage = coverage_and_variation(candidate_frame, eligible_keys)
    del candidate_frame, eligible_keys
    gc.collect()
    passed = coverage["gate_passed_before_comparator_values"] is True
    result = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign136_coverage_audit",
        "status": (
            "coverage_passed_ready_to_freeze_all_140_ordered_comparator_audit"
            if passed
            else "coverage_failed_terminal_before_all_comparator_values"
        ),
        "recorded_at": datetime.now(UTC).isoformat(),
        "factor": FACTOR_NAME,
        "direction": formula.SCORE_DIRECTION,
        "static_bindings": plan["static_bindings"],
        "snapshot_verification": snapshot_verification,
        "coverage_and_variation": coverage,
        "comparator_values_read": False,
        "numeric_comparator_count_read": 0,
        "historical_daily_ohlcv_fields_read": [],
        "historical_forward_return_fields_read": False,
        "stress_2024_2025_return_values_opened": False,
        "training_or_model_fitting_performed": False,
        "provider_request_issued": False,
        "credential_loaded": False,
        "candidate49_historical_backfill_performed": False,
        "candidate49_ledgers_changed": False,
        "second_prospective_candidate_created": False,
        "current_scoring_selection_sizing_positions_or_orders_performed": False,
        "investment_advice": False,
        "next_action": (
            "freeze an exact all-140 ordered no-return comparator audit before reading any comparator value"
            if passed
            else "terminalize Campaign136 without reading comparator, OHLCV, or return values"
        ),
    }
    atomic_exclusive_json(OUTPUT_PATH, result)
    return OUTPUT_PATH


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    sub = value.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    run = sub.add_parser("run")
    run.add_argument("--confirm-coverage-audit", action="store_true")
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "plan":
            value = build_plan()
            print(json.dumps(value, ensure_ascii=False, sort_keys=True))
            return 0 if value["ready"] else 2
        path = run_coverage_audit(confirm=args.confirm_coverage_audit)
        print(json.dumps({"coverage_audit_path": str(path)}, sort_keys=True))
        return 0
    except Campaign136CoverageAuditError as exc:
        print(
            json.dumps(
                {
                    "ready": False,
                    "error_code": "campaign136_coverage_contract_failure",
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
