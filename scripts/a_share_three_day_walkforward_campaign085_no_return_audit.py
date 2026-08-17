#!/usr/bin/env python3
"""Run Campaign085's frozen coverage-first no-return uniqueness audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts import a_share_three_day_compact_comparator_cache_v4 as cache_v4
from scripts import (
    a_share_three_day_walkforward_campaign077_no_return_audit_v2 as c77_v2,
)
from scripts import (
    a_share_three_day_walkforward_campaign083_no_return_audit_v3 as c83_v3,
)
from scripts import (
    a_share_three_day_walkforward_campaign084_no_return_audit as c84_audit,
)
from scripts import a_share_three_day_walkforward_campaign085_features as candidate

REPO_ROOT = Path(__file__).resolve().parents[1]
FACTOR_NAME = candidate.FACTOR_NAME
DEFAULT_DATA_ROOT = candidate.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_085/no_return_v4"
)
SNAPSHOT_MANIFEST_PATH = (
    candidate.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "fb8ea4bdb2b2f783a8c1d4e020f1dcdfca1697c779c732e50233fe7b040b4d28"
)
SNAPSHOT_DATASET_SHA256 = (
    "368f7cb96c15186cd511ccd4120e89b577141aa9687df8b39f9dd17320db8fb9"
)
SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_085_feature_snapshot_binding_20260806.json"
)
SNAPSHOT_BINDING_SHA256 = (
    "ce70c107d654b1d6151fde87bd5f177ee458cb2db825080cf1c6206df249ba4f"
)
AUDIT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_085_no_return_audit_implementation_freeze_v4_20260807.json"
)
AUDIT_ACTIVATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_085_no_return_audit_activation_binding_v4_20260807.json"
)
REPAIR_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_085_no_return_audit_repair_protocol_v4_20260807.json"
)
REPAIR_PROTOCOL_SHA256 = (
    "55395871191233404c84707f37361e651de5afefd0c71dde7c12f54557b6d2d2"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign085_no_return_audit.py"
)
EXPECTED_ROWS = 1_331_759
EXPECTED_PARTITIONS = 7
EXPECTED_ELIGIBLE_ROWS = 1_328_065
EXPECTED_SESSIONS = 1_632
EXPECTED_COMPARISON_COUNT = 114
EXPECTED_COMPLETE_DEFINITION_COUNT = 116
C84_SNAPSHOT_MANIFEST_PATH = (
    candidate.c84.output_root(candidate.c84.DEFAULT_DATA_ROOT)
    / "snapshot_manifest.json"
)
STRUCTURALLY_NONNUMERIC_FACTOR = (
    "intraday_cross_sectional_standardized_return_state_stability_236p"
)
PREVALUE_TERMINAL_NONNUMERIC_FACTOR = "signal_day_turnover_rate_pct"


class Campaign085NoReturnAuditError(RuntimeError):
    """Fail-closed Campaign085 no-return audit error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign085NoReturnAuditError(f"{label} changed: {path}")


def load_protocol() -> dict[str, Any]:
    spec = candidate.load_protocol()
    comparisons = candidate.reconstruct_comparisons()
    complete = candidate.reconstruct_complete_definitions()
    complete_names = [str(item["name"]) for item in complete]
    comparison_names = [str(item["name"]) for item in comparisons]
    if not (
        len(comparisons) == EXPECTED_COMPARISON_COUNT
        and candidate._comparison_order_digest(comparisons)
        == candidate.COMPARISON_ORDER_SHA256
        and len(complete) == EXPECTED_COMPLETE_DEFINITION_COUNT
        and candidate._comparison_order_digest(complete)
        == candidate.FULL_DEFINITION_ORDER_SHA256
        and STRUCTURALLY_NONNUMERIC_FACTOR in complete_names
        and STRUCTURALLY_NONNUMERIC_FACTOR not in comparison_names
        and PREVALUE_TERMINAL_NONNUMERIC_FACTOR in complete_names
        and PREVALUE_TERMINAL_NONNUMERIC_FACTOR not in comparison_names
    ):
        raise Campaign085NoReturnAuditError("Campaign085 comparison order changed")
    spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ] = comparisons
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not AUDIT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign085NoReturnAuditError("audit implementation freeze is absent")
    record = json.loads(AUDIT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign085_no_return_audit_implementation_freeze_v4"
        and record.get("status")
        == "v4_frozen_after_campaign083_adapter_before_coverage_or_comparison_values"
        and (record.get("audit_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and (record.get("repair_protocol") or {}).get("sha256")
        == REPAIR_PROTOCOL_SHA256
        and (record.get("snapshot_binding") or {}).get("sha256")
        == SNAPSHOT_BINDING_SHA256
        and record.get("coverage_or_capacity_metrics_computed_before_freeze") is False
        and record.get("comparison_values_read_before_freeze") is False
        and record.get("historical_daily_price_fields_read_before_freeze") == []
        and record.get("historical_forward_returns_read_before_freeze") is False
        and record.get("provider_request_issued_before_freeze") is False
    ):
        raise Campaign085NoReturnAuditError("audit implementation freeze changed")
    return record


def _load_activation_binding() -> dict[str, Any]:
    _load_implementation_freeze()
    if not AUDIT_ACTIVATION_BINDING.is_file():
        raise Campaign085NoReturnAuditError("audit activation binding is absent")
    record = json.loads(AUDIT_ACTIVATION_BINDING.read_text(encoding="utf-8"))
    snapshot = record.get("candidate_snapshot") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign085_no_return_audit_activation_binding_v4"
        and record.get("status") == "v4_frozen_before_full_restart_or_comparison_values"
        and (record.get("implementation_freeze") or {}).get("sha256")
        == _sha256(AUDIT_IMPLEMENTATION_FREEZE)
        and (record.get("snapshot_binding") or {}).get("sha256")
        == SNAPSHOT_BINDING_SHA256
        and snapshot.get("path") == str(SNAPSHOT_MANIFEST_PATH.resolve())
        and snapshot.get("sha256") == SNAPSHOT_MANIFEST_SHA256
        and snapshot.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and record.get("coverage_or_capacity_metrics_computed_before_activation")
        is False
        and record.get("comparison_values_read_before_activation") is False
        and record.get("historical_daily_price_fields_read_before_activation") == []
        and record.get("historical_forward_returns_read_before_activation") is False
        and record.get("provider_request_issued_before_activation") is False
    ):
        raise Campaign085NoReturnAuditError("audit activation binding changed")
    return record


def verify_candidate_snapshot() -> dict[str, Any]:
    _require(SNAPSHOT_MANIFEST_PATH, SNAPSHOT_MANIFEST_SHA256, "candidate snapshot")
    result = candidate.verify_snapshot_files(SNAPSHOT_MANIFEST_PATH)
    if not (
        result.get("status") == "verified"
        and result.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and result.get("partitions") == EXPECTED_PARTITIONS
        and result.get("rows") == EXPECTED_ROWS
        and result.get("eligible_rows") == EXPECTED_ELIGIBLE_ROWS
        and result.get("comparison_values_read") is False
    ):
        raise Campaign085NoReturnAuditError("candidate snapshot verification changed")
    return result


def verify_static_bindings() -> dict[str, Any]:
    _load_activation_binding()
    _require(REPAIR_PROTOCOL, REPAIR_PROTOCOL_SHA256, "repair protocol")
    _require(SNAPSHOT_BINDING, SNAPSHOT_BINDING_SHA256, "snapshot binding")
    report = candidate.bindings.validate_record(
        SNAPSHOT_BINDING, data_root=DEFAULT_DATA_ROOT
    )
    if report.get("all_bindings_passed") is not True:
        raise Campaign085NoReturnAuditError("snapshot binding validation failed")
    return {
        "audit_implementation_freeze_sha256": _sha256(AUDIT_IMPLEMENTATION_FREEZE),
        "audit_activation_binding_sha256": _sha256(AUDIT_ACTIVATION_BINDING),
        "repair_protocol_sha256": REPAIR_PROTOCOL_SHA256,
        "snapshot_binding_sha256": SNAPSHOT_BINDING_SHA256,
        "candidate_manifest_sha256": SNAPSHOT_MANIFEST_SHA256,
        "candidate_dataset_sha256": SNAPSHOT_DATASET_SHA256,
        "candidate_eligible_rows": EXPECTED_ELIGIBLE_ROWS,
        "comparison_count": EXPECTED_COMPARISON_COUNT,
        "comparison_order_sha256": candidate.COMPARISON_ORDER_SHA256,
        "complete_definition_count": EXPECTED_COMPLETE_DEFINITION_COUNT,
        "complete_definition_order_sha256": candidate.FULL_DEFINITION_ORDER_SHA256,
        "comparator_values_read": False,
    }


def load_candidate_arrays() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    keys: list[np.ndarray] = []
    values: list[np.ndarray] = []
    years: list[np.ndarray] = []
    for record in manifest.get("files") or []:
        frame = pd.read_parquet(
            SNAPSHOT_MANIFEST_PATH.parent / str(record["path"]),
            columns=["stock_day_key", FACTOR_NAME],
        )
        keys.append(frame["stock_day_key"].to_numpy(dtype=np.int64))
        values.append(frame[FACTOR_NAME].to_numpy(dtype=np.float64))
        years.append(np.full(len(frame), int(record["year"]), dtype=np.int64))
    all_keys = np.concatenate(keys)
    all_values = np.concatenate(values)
    all_years = np.concatenate(years)
    if not (
        len(all_keys) == EXPECTED_ROWS
        and all_years.shape == all_keys.shape
        and len(np.unique(all_keys)) == EXPECTED_ROWS
        and np.all(all_keys[1:] > all_keys[:-1])
        and int(np.isfinite(all_values).sum()) == EXPECTED_ELIGIBLE_ROWS
        and np.array_equal(np.unique(all_years), np.arange(2019, 2026))
    ):
        raise Campaign085NoReturnAuditError("candidate arrays changed")
    return all_keys, all_values, all_years


def coverage_and_capacity(
    keys: np.ndarray,
    values: np.ndarray,
    years: np.ndarray,
    spec: dict[str, Any],
) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    stock_day_keys = np.asarray(keys, dtype=np.int64)
    candidate_values = np.asarray(values, dtype=np.float64)
    explicit_years = np.asarray(years, dtype=np.int64)
    if (
        stock_day_keys.ndim != 1
        or candidate_values.shape != stock_day_keys.shape
        or explicit_years.shape != stock_day_keys.shape
        or len(stock_day_keys) == 0
        or len(np.unique(stock_day_keys)) != len(stock_day_keys)
    ):
        raise Campaign085NoReturnAuditError("coverage arrays changed")
    sessions = stock_day_keys // 4_000_000
    frame = pd.DataFrame(
        {
            "session": sessions,
            "year": explicit_years,
            "finite": np.isfinite(candidate_values).astype(np.int64),
        }
    )
    if int(frame.groupby("session", sort=False)["year"].nunique().max()) != 1:
        raise Campaign085NoReturnAuditError(
            "one session maps to multiple explicit snapshot years"
        )
    daily = (
        frame.groupby("session", sort=True)
        .agg(
            candidate_eligible_names=("finite", "sum"),
            quality_listing_eligible_names=("finite", "size"),
            year=("year", "first"),
        )
        .reset_index()
    )
    daily["coverage"] = (
        daily["candidate_eligible_names"] / daily["quality_listing_eligible_names"]
    )
    gate = spec["ordered_no_return_gates"][
        "coverage_and_capacity_before_comparison_values"
    ]
    qualified = daily["candidate_eligible_names"] >= int(
        gate["minimum_p05_eligible_names"]
    )
    observed_years = sorted(
        int(value) for value in daily.loc[qualified, "year"].unique()
    )
    cohorts = sum(
        int((qualified & (daily["year"] == year)).sum()) // 3 for year in observed_years
    )
    median_coverage = float(daily["coverage"].median())
    p05_coverage = float(daily["coverage"].quantile(0.05))
    p05_names = float(daily["candidate_eligible_names"].quantile(0.05))
    passed = bool(
        median_coverage >= float(gate["minimum_median_coverage"])
        and p05_coverage >= float(gate["minimum_p05_coverage"])
        and p05_names >= float(gate["minimum_p05_eligible_names"])
        and cohorts >= int(gate["minimum_non_overlapping_three_session_cohorts"])
        and len(observed_years) >= int(gate["minimum_observed_calendar_years"])
    )
    daily_records = [
        {
            "session": int(row.session),
            "year": int(row.year),
            "candidate_eligible_names": int(row.candidate_eligible_names),
            "quality_listing_eligible_names": int(row.quality_listing_eligible_names),
            "coverage": float(row.coverage),
        }
        for row in daily.itertuples(index=False)
    ]
    worst = sorted(
        daily_records,
        key=lambda item: (
            item["coverage"],
            item["candidate_eligible_names"],
            item["session"],
        ),
    )[:10]
    finite = np.isfinite(candidate_values)
    result = {
        "calendar_sessions": len(daily),
        "quality_listing_eligible_rows": len(stock_day_keys),
        "candidate_eligible_rows": int(finite.sum()),
        "median_coverage": median_coverage,
        "p05_coverage": p05_coverage,
        "eligible_names_median": float(daily["candidate_eligible_names"].median()),
        "eligible_names_min": int(daily["candidate_eligible_names"].min()),
        "eligible_names_p05": p05_names,
        "potential_non_overlapping_three_session_cohorts": cohorts,
        "observed_cohort_years": observed_years,
        "gate": {
            "minimum_median_coverage": gate["minimum_median_coverage"],
            "minimum_p05_coverage": gate["minimum_p05_coverage"],
            "minimum_p05_eligible_names": gate["minimum_p05_eligible_names"],
            "minimum_non_overlapping_three_session_cohorts": gate[
                "minimum_non_overlapping_three_session_cohorts"
            ],
            "minimum_observed_calendar_years": gate["minimum_observed_calendar_years"],
        },
        "gate_passed_before_comparison_values": passed,
        "daily_coverage_frame_sha256": _json_digest(daily_records),
        "worst_ten_sessions": worst,
    }
    return result, stock_day_keys[finite], candidate_values[finite]


def _install_frozen_ranges(engine: Any) -> None:
    c84_audit._install_frozen_ranges(engine)
    ranges = dict(getattr(engine, "FACTOR_RANGES", {}))
    if FACTOR_NAME in ranges and tuple(ranges[FACTOR_NAME]) != (0.0, 1.0):
        raise Campaign085NoReturnAuditError("conflicting Campaign085 range")
    ranges[FACTOR_NAME] = (0.0, 1.0)
    engine.FACTOR_RANGES = ranges


def _load_comparisons_after_coverage(
    *,
    coverage: dict[str, Any],
    candidate_keys: np.ndarray,
    candidate_values: np.ndarray,
    gate: dict[str, Any],
    engine: Any,
    comparison_engine: Any,
    workers: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    c77_v2.load_repair_protocol()
    c77_v2._load_implementation_freeze()
    c83_v3.load_repair_protocol()
    c83_v3._load_implementation_freeze()
    c83_v3.v2.load_repair_protocol()
    c83_v3.v2._load_implementation_freeze()
    c83_v3.v2.require_exact_runtime()
    with c77_v2._temporary_runtime_version_binding(), c83_v3._temporary_candidate_verifier_binding():
        comparisons, receipts = c84_audit._load_comparisons_after_coverage(
            coverage=coverage,
            candidate_keys=candidate_keys,
            candidate_values=candidate_values,
            gate=gate,
            engine=engine,
            comparison_engine=comparison_engine,
            workers=workers,
        )
    helper = (
        c84_audit.c83_audit.c82_audit.c81_audit.c80_audit.c78_audit.c77_audit.c76_audit.c75_v5.v4.v3.v1.base.base._append_snapshot_comparison
    )
    result, receipt = helper(
        manifest_path=C84_SNAPSHOT_MANIFEST_PATH,
        factor=candidate.c84.FACTOR_NAME,
        candidate_keys=candidate_keys,
        candidate_values=candidate_values,
        gate=gate,
        engine=engine,
        comparison_engine=comparison_engine,
        workers=workers,
        verifier=lambda _path, workers=workers: c84_audit.verify_candidate_snapshot(
            workers=workers
        ),
    )
    comparisons.append(result)
    receipts["campaign084_snapshot"] = receipt
    receipts.pop("all_113_sources_loaded_in_frozen_order", None)
    receipts["all_114_sources_loaded_in_frozen_order"] = True
    if len(comparisons) != EXPECTED_COMPARISON_COUNT:
        raise Campaign085NoReturnAuditError("Campaign085 comparison count changed")
    return comparisons, receipts


def _run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    static = verify_static_bindings()
    spec = load_protocol()
    if data_root.expanduser().resolve() != DEFAULT_DATA_ROOT.resolve():
        raise Campaign085NoReturnAuditError("Campaign085 data root changed")
    experiment_root = experiment_root.expanduser().resolve()
    if list(experiment_root.glob("*_campaign085_no_return_audit_v4.json")):
        raise Campaign085NoReturnAuditError(
            "Campaign085 no-return audit already exists"
        )
    verification = verify_candidate_snapshot()
    keys, values, years = load_candidate_arrays()
    coverage, finite_keys, finite_values = coverage_and_capacity(
        keys, values, years, spec
    )
    comparisons: list[dict[str, Any]] = []
    receipts: dict[str, Any] = {}
    if coverage["gate_passed_before_comparison_values"]:
        gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
        context = (
            cache_v4.v1.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
        )
        _, _, engine, _, _, comparison_engine = context
        _install_frozen_ranges(engine)
        comparisons, receipts = _load_comparisons_after_coverage(
            coverage=coverage,
            candidate_keys=finite_keys,
            candidate_values=finite_values,
            gate=gate,
            engine=engine,
            comparison_engine=comparison_engine,
            workers=workers,
        )
    all_comparisons_passed = bool(comparisons) and all(
        item.get("gate_passed") is True for item in comparisons
    )
    maximum_correlation = (
        max(
            float(item["absolute_median_daily_rank_correlation"])
            for item in comparisons
            if item.get("absolute_median_daily_rank_correlation") is not None
        )
        if comparisons
        else None
    )
    admissible = int(
        coverage["gate_passed_before_comparison_values"]
        and all_comparisons_passed
        and len(comparisons) == EXPECTED_COMPARISON_COUNT
    )
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign085_no_return_audit_v4",
        "status": (
            "completed_one_admissible_factor_ready_for_frozen_development_trial"
            if admissible
            else "completed_zero_admissible_factors_stop_before_historical_daily_prices_or_returns"
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": f"{run_id}_campaign085_no_return_audit_v4",
        "protocol": {
            "path": str(candidate.DEFAULT_PROTOCOL.resolve()),
            "sha256": candidate.PROTOCOL_SHA256,
        },
        "candidate_snapshot": {
            "path": str(SNAPSHOT_MANIFEST_PATH.resolve()),
            "sha256": SNAPSHOT_MANIFEST_SHA256,
            "dataset_sha256": SNAPSHOT_DATASET_SHA256,
        },
        "static_bindings": static,
        "snapshot_file_verification": verification,
        "coverage_and_capacity": {FACTOR_NAME: coverage},
        "uniqueness": {
            FACTOR_NAME: {
                "comparison_values_loaded_after_coverage_pass": bool(comparisons),
                "comparison_factor_count": len(comparisons),
                "comparison_order_matches_preregistration": (
                    [item["comparison_factor"] for item in comparisons]
                    == [
                        item["name"]
                        for item in spec["ordered_no_return_gates"][
                            "uniqueness_after_coverage_only"
                        ]["comparison_factors"]
                    ]
                    if comparisons
                    else False
                ),
                "all_required_numeric_comparisons_passed": all_comparisons_passed,
                "maximum_observed_absolute_median_daily_rank_correlation": maximum_correlation,
                "comparisons": comparisons,
                "comparison_source_verification": receipts,
                "structurally_nonnumeric_mechanism_challenges": [
                    {
                        "name": STRUCTURALLY_NONNUMERIC_FACTOR,
                        "numeric_status": "undefined_not_pass_not_fail",
                        "mechanism_overlap_status": "explicitly_challenged_before_values",
                    },
                    {
                        "name": PREVALUE_TERMINAL_NONNUMERIC_FACTOR,
                        "numeric_status": "ineligible_no_values_exist",
                        "mechanism_overlap_status": "explicitly_challenged_before_values",
                    },
                ],
            }
        },
        "admissible_factor_count": admissible,
        "admissible_factor_names": [FACTOR_NAME] if admissible else [],
        "failed_factor_names": [] if admissible else [FACTOR_NAME],
        "next_action": (
            "freeze and run exactly the preregistered single development trial"
            if admissible
            else "record this no-return rejection and begin only a genuinely new campaign"
        ),
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "training_or_model_fitting_performed": False,
        "candidate49_historical_return_read": False,
        "candidate49_prospective_ledgers_changed": False,
        "second_prospective_candidate_created": False,
        "provider_request_issued": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
        "current_listing_snapshot_survivorship_limitation": True,
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    path = experiment_root / f"{payload['run_id']}.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def status(experiment_root: Path = DEFAULT_EXPERIMENT_ROOT) -> dict[str, Any]:
    return {
        "status": (
            "ready_for_single_v4_audit"
            if AUDIT_ACTIVATION_BINDING.is_file()
            else "activation_binding_absent"
        ),
        "candidate_snapshot_exists": SNAPSHOT_MANIFEST_PATH.is_file(),
        "audit_count": len(
            list(
                experiment_root.expanduser()
                .resolve()
                .glob("*_campaign085_no_return_audit_v4.json")
            )
        ),
        "coverage_or_capacity_metrics_computed": False,
        "comparison_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "run"))
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--confirm-run", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "status":
        payload: Any = status(args.experiment_root)
    else:
        if not args.confirm_run:
            raise Campaign085NoReturnAuditError("run requires --confirm-run")
        path = _run_no_return_audit(
            data_root=args.data_root,
            experiment_root=args.experiment_root,
            workers=args.workers,
        )
        payload = {"status": "completed", "audit_path": str(path)}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
