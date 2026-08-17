#!/usr/bin/env python3
"""Run Campaign097's frozen coverage-first no-return uniqueness audit."""

from __future__ import annotations

import argparse
import gc
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from scripts import a_share_three_day_compact_comparator_cache_v4 as cache_v4
from scripts import (
    a_share_three_day_walkforward_campaign087_no_return_audit_v2 as compact_helper,
)
from scripts import (
    a_share_three_day_walkforward_campaign096_no_return_audit as c96_audit,
)
from scripts import a_share_three_day_walkforward_campaign097_features as definitions


REPO_ROOT = Path(__file__).resolve().parents[1]
FACTOR_NAME = definitions.FACTOR_NAME
DEFAULT_DATA_ROOT = definitions.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_097/no_return"
)
SNAPSHOT_MANIFEST_PATH = (
    definitions.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "12e43008b4595a338bdd67ac21dcd543772e0517993623837770bec3bd31e0df"
)
SNAPSHOT_DATASET_SHA256 = (
    "ab5b0f747600a4040c38e1d6453a0ec4242342803bc7acff257cc88f95ccfdb5"
)
SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_097_feature_snapshot_binding_20260807.json"
)
SNAPSHOT_BINDING_SHA256 = (
    "fd83658021023e30b1dd4d3ae4c3750dc054ec349f1a4e6839a3796dc0005def"
)
AUDIT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_097_no_return_audit_implementation_freeze_20260807.json"
)
AUDIT_ACTIVATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_097_no_return_audit_activation_binding_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign097_no_return_audit.py"
)
ELIGIBILITY_MANIFEST_PATH = (
    DEFAULT_DATA_ROOT
    / "derived/a_share/rich/tushare/compact_comparator_cache"
    / "campaign067_terminal_numeric98_v4/snapshot_manifest.json"
)
ELIGIBILITY_MANIFEST_SHA256 = (
    "3d81068f07ac61fe4cd04bd1a893e58759c06d88213263135fec5244e309b57b"
)
C96_MANIFEST_PATH = c96_audit.SNAPSHOT_MANIFEST_PATH
C96_MANIFEST_SHA256 = c96_audit.SNAPSHOT_MANIFEST_SHA256
C96_FACTOR_NAME = c96_audit.FACTOR_NAME
EXPECTED_RAW_PARTITIONS = 33_015
EXPECTED_RAW_ROWS = 7_724_498
EXPECTED_RAW_ELIGIBLE_ROWS = 7_699_914
EXPECTED_ROWS = 1_331_759
EXPECTED_PARTITIONS = 7
EXPECTED_SESSIONS = 1_632
EXPECTED_COMPARISON_COUNT = 125
EXPECTED_COMPLETE_DEFINITION_COUNT = 128
STRUCTURALLY_NONNUMERIC_FACTORS = (
    "intraday_cross_sectional_standardized_return_state_stability_236p",
    "signal_day_turnover_rate_pct",
    "intraday_own_bar_close_location_entropy_10b_240m",
)


class Campaign097NoReturnAuditError(RuntimeError):
    """Fail-closed Campaign097 no-return audit error."""


def _sha256(path: Path) -> str:
    return definitions._sha256(path)


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign097NoReturnAuditError(f"Campaign097 {label} changed: {path}")


def load_protocol() -> dict[str, Any]:
    spec = definitions.load_protocol()
    complete = definitions.reconstruct_complete_definitions()
    comparisons = definitions.reconstruct_comparisons()
    complete_names = [str(item["name"]) for item in complete]
    comparison_names = [str(item["name"]) for item in comparisons]
    if not (
        len(complete) == EXPECTED_COMPLETE_DEFINITION_COUNT
        and definitions._order_digest(complete)
        == definitions.FULL_DEFINITION_ORDER_SHA256
        and len(comparisons) == EXPECTED_COMPARISON_COUNT
        and definitions._order_digest(comparisons)
        == definitions.COMPARISON_ORDER_SHA256
        and comparisons[-1] == {"name": C96_FACTOR_NAME, "score_direction": "higher"}
        and all(name in complete_names for name in STRUCTURALLY_NONNUMERIC_FACTORS)
        and not any(
            name in comparison_names for name in STRUCTURALLY_NONNUMERIC_FACTORS
        )
    ):
        raise Campaign097NoReturnAuditError("Campaign097 definition order changed")
    spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ] = comparisons
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not AUDIT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign097NoReturnAuditError("audit implementation freeze is absent")
    record = json.loads(AUDIT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign097_no_return_audit_implementation_freeze"
        and record.get("status")
        == "frozen_before_campaign097_coverage_or_comparison_values"
        and (record.get("audit_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and (record.get("snapshot_binding") or {}).get("sha256")
        == SNAPSHOT_BINDING_SHA256
        and (record.get("eligibility_identity_source") or {}).get("sha256")
        == ELIGIBILITY_MANIFEST_SHA256
        and record.get("eligibility_source_columns_allowed_before_coverage")
        == ["stock_day_key"]
        and record.get("coverage_or_capacity_metrics_computed_before_freeze") is False
        and record.get("comparison_values_read_before_freeze") is False
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and record.get("provider_request_issued_before_freeze") is False
    ):
        raise Campaign097NoReturnAuditError("audit implementation freeze changed")
    return record


def _load_activation_binding() -> dict[str, Any]:
    _load_implementation_freeze()
    if not AUDIT_ACTIVATION_BINDING.is_file():
        raise Campaign097NoReturnAuditError("audit activation binding is absent")
    record = json.loads(AUDIT_ACTIVATION_BINDING.read_text(encoding="utf-8"))
    snapshot = record.get("candidate_snapshot") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign097_no_return_audit_activation_binding"
        and record.get("status")
        == "frozen_before_campaign097_coverage_or_comparison_values"
        and (record.get("implementation_freeze") or {}).get("sha256")
        == _sha256(AUDIT_IMPLEMENTATION_FREEZE)
        and (record.get("snapshot_binding") or {}).get("sha256")
        == SNAPSHOT_BINDING_SHA256
        and snapshot.get("path") == str(SNAPSHOT_MANIFEST_PATH.resolve())
        and snapshot.get("sha256") == SNAPSHOT_MANIFEST_SHA256
        and snapshot.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and (record.get("eligibility_identity_source") or {}).get("sha256")
        == ELIGIBILITY_MANIFEST_SHA256
        and record.get("coverage_or_capacity_metrics_computed_before_activation")
        is False
        and record.get("comparison_values_read_before_activation") is False
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_activation"
        )
        is False
        and record.get("provider_request_issued_before_activation") is False
    ):
        raise Campaign097NoReturnAuditError("audit activation binding changed")
    return record


def verify_candidate_snapshot() -> dict[str, Any]:
    _require(SNAPSHOT_MANIFEST_PATH, SNAPSHOT_MANIFEST_SHA256, "candidate snapshot")
    result = definitions.verify_snapshot_files(SNAPSHOT_MANIFEST_PATH)
    if not (
        result.get("status") == "verified"
        and result.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and result.get("partitions") == EXPECTED_RAW_PARTITIONS
        and result.get("rows") == EXPECTED_RAW_ROWS
        and result.get("eligible_rows") == EXPECTED_RAW_ELIGIBLE_ROWS
        and result.get("comparison_values_read") is False
    ):
        raise Campaign097NoReturnAuditError("candidate snapshot verification changed")
    return result


def verify_static_bindings() -> dict[str, Any]:
    _load_activation_binding()
    _require(SNAPSHOT_BINDING, SNAPSHOT_BINDING_SHA256, "snapshot binding")
    _require(
        ELIGIBILITY_MANIFEST_PATH,
        ELIGIBILITY_MANIFEST_SHA256,
        "eligibility identity manifest",
    )
    report = definitions.bindings.validate_record(
        SNAPSHOT_BINDING, data_root=DEFAULT_DATA_ROOT
    )
    if report.get("all_bindings_passed") is not True:
        raise Campaign097NoReturnAuditError("snapshot binding validation failed")
    return {
        "audit_implementation_freeze_sha256": _sha256(AUDIT_IMPLEMENTATION_FREEZE),
        "audit_activation_binding_sha256": _sha256(AUDIT_ACTIVATION_BINDING),
        "snapshot_binding_sha256": SNAPSHOT_BINDING_SHA256,
        "candidate_manifest_sha256": SNAPSHOT_MANIFEST_SHA256,
        "candidate_dataset_sha256": SNAPSHOT_DATASET_SHA256,
        "eligibility_identity_manifest_sha256": ELIGIBILITY_MANIFEST_SHA256,
        "eligibility_source_columns_read_before_coverage": ["stock_day_key"],
        "quality_listing_eligible_rows": EXPECTED_ROWS,
        "comparison_count": EXPECTED_COMPARISON_COUNT,
        "comparison_order_sha256": definitions.COMPARISON_ORDER_SHA256,
        "complete_definition_count": EXPECTED_COMPLETE_DEFINITION_COUNT,
        "complete_definition_order_sha256": definitions.FULL_DEFINITION_ORDER_SHA256,
        "comparator_values_read": False,
    }


def compact_stock_day_keys(trade_dates: pd.Series, symbols: pd.Series) -> np.ndarray:
    dates = pd.to_datetime(trade_dates, errors="coerce").dt.normalize()
    text = symbols.astype("string").str.upper()
    exchange = text.str.slice(0, 2).map({"SH": 1, "SZ": 2, "BJ": 3})
    codes = pd.to_numeric(text.str.slice(2, 8), errors="coerce")
    if (
        dates.isna().any()
        or exchange.isna().any()
        or codes.isna().any()
        or not text.str.fullmatch(r"(SH|SZ|BJ)[0-9]{6}").all()
    ):
        raise Campaign097NoReturnAuditError("stock-day identity cannot compact")
    day_number = dates.to_numpy(dtype="datetime64[D]").astype(np.int64, copy=False)
    security = exchange.to_numpy(dtype=np.int64) * 1_000_000 + codes.to_numpy(
        dtype=np.int64
    )
    return day_number * 4_000_000 + security


def align_candidate_year(
    *,
    eligible_keys: np.ndarray,
    candidate_keys: np.ndarray,
    candidate_values: np.ndarray,
    year: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    frozen_keys = np.asarray(eligible_keys, dtype=np.int64)
    observed_keys = np.asarray(candidate_keys, dtype=np.int64)
    observed_values = np.asarray(candidate_values, dtype=np.float64)
    if not (
        year in range(2019, 2026)
        and frozen_keys.ndim == 1
        and observed_keys.ndim == 1
        and observed_values.shape == observed_keys.shape
        and len(frozen_keys) > 0
        and len(observed_keys) > 0
        and np.all(frozen_keys[1:] > frozen_keys[:-1])
        and len(np.unique(observed_keys)) == len(observed_keys)
    ):
        raise Campaign097NoReturnAuditError("candidate alignment inputs changed")
    order = np.argsort(observed_keys, kind="stable")
    sorted_keys = observed_keys[order]
    positions = np.searchsorted(sorted_keys, frozen_keys, side="left")
    if not (
        np.all(positions < len(sorted_keys))
        and np.array_equal(sorted_keys[positions], frozen_keys)
    ):
        raise Campaign097NoReturnAuditError(
            f"Campaign097 candidate misses frozen eligible keys in {year}"
        )
    aligned_values = observed_values[order][positions]
    finite = np.isfinite(aligned_values)
    if np.any((aligned_values[finite] < -1.0) | (aligned_values[finite] > 1.0)):
        raise Campaign097NoReturnAuditError("candidate values left frozen range")
    return (
        frozen_keys,
        aligned_values,
        np.full(len(frozen_keys), year, dtype=np.int64),
    )


def _records_by_year(
    records: Iterable[dict[str, Any]]
) -> dict[int, list[dict[str, Any]]]:
    grouped = {year: [] for year in range(2019, 2026)}
    for record in records:
        year = int(record["year"])
        if year not in grouped:
            raise Campaign097NoReturnAuditError("candidate partition year changed")
        grouped[year].append(record)
    return grouped


def load_candidate_arrays() -> (
    tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]
):
    """Align candidate values to eligibility keys without reading comparator columns."""

    candidate_manifest = json.loads(SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    eligibility_manifest = json.loads(
        ELIGIBILITY_MANIFEST_PATH.read_text(encoding="utf-8")
    )
    candidate_by_year = _records_by_year(candidate_manifest.get("files") or [])
    eligibility_by_year = {
        int(record["year"]): record
        for record in eligibility_manifest.get("files") or []
    }
    if not (
        len(candidate_manifest.get("files") or []) == EXPECTED_RAW_PARTITIONS
        and sorted(eligibility_by_year) == list(range(2019, 2026))
        and sum(int(item["rows"]) for item in eligibility_by_year.values())
        == EXPECTED_ROWS
    ):
        raise Campaign097NoReturnAuditError(
            "candidate or eligibility partitions changed"
        )

    all_keys: list[np.ndarray] = []
    all_values: list[np.ndarray] = []
    all_years: list[np.ndarray] = []
    raw_rows_read = 0
    for year in range(2019, 2026):
        eligibility_record = eligibility_by_year[year]
        eligibility_path = ELIGIBILITY_MANIFEST_PATH.parent / str(
            eligibility_record["path"]
        )
        eligible_frame = pd.read_parquet(eligibility_path, columns=["stock_day_key"])
        eligible_keys = eligible_frame["stock_day_key"].to_numpy(dtype=np.int64)
        year_keys: list[np.ndarray] = []
        year_values: list[np.ndarray] = []
        for record in candidate_by_year[year]:
            path = Path(str(record["path"])).expanduser().resolve()
            if not path.is_file() or not path.is_relative_to(
                SNAPSHOT_MANIFEST_PATH.parent.resolve()
            ):
                raise Campaign097NoReturnAuditError(
                    f"candidate partition path changed: {path}"
                )
            frame = pd.read_parquet(path, columns=["trade_date", "symbol", FACTOR_NAME])
            if len(frame) != int(record["rows"]):
                raise Campaign097NoReturnAuditError(
                    f"candidate partition rows changed: {path}"
                )
            year_keys.append(
                compact_stock_day_keys(frame["trade_date"], frame["symbol"])
            )
            year_values.append(frame[FACTOR_NAME].to_numpy(dtype=np.float64))
            raw_rows_read += len(frame)
        keys, values, years = align_candidate_year(
            eligible_keys=eligible_keys,
            candidate_keys=np.concatenate(year_keys),
            candidate_values=np.concatenate(year_values),
            year=year,
        )
        all_keys.append(keys)
        all_values.append(values)
        all_years.append(years)
        del eligible_frame, eligible_keys, year_keys, year_values, keys, values, years
        gc.collect()

    keys = np.concatenate(all_keys)
    values = np.concatenate(all_values)
    years = np.concatenate(all_years)
    if not (
        raw_rows_read == EXPECTED_RAW_ROWS
        and len(keys) == EXPECTED_ROWS
        and values.shape == keys.shape == years.shape
        and len(np.unique(keys)) == EXPECTED_ROWS
        and np.all(keys[1:] > keys[:-1])
        and len(np.unique(keys // 4_000_000)) == EXPECTED_SESSIONS
        and np.array_equal(np.unique(years), np.arange(2019, 2026))
    ):
        raise Campaign097NoReturnAuditError("aligned candidate arrays changed")
    receipt = {
        "loader": "frozen_quality_listing_stock_day_key_identity_only_alignment",
        "eligibility_manifest_sha256": ELIGIBILITY_MANIFEST_SHA256,
        "eligibility_columns_read": ["stock_day_key"],
        "comparison_columns_read": [],
        "candidate_source_columns_read": ["trade_date", "symbol", FACTOR_NAME],
        "candidate_raw_rows_read": raw_rows_read,
        "quality_listing_eligible_rows": len(keys),
        "finite_candidate_rows": int(np.isfinite(values).sum()),
        "comparison_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
    }
    return keys, values, years, receipt


def coverage_and_capacity(
    keys: np.ndarray,
    values: np.ndarray,
    years: np.ndarray,
    spec: dict[str, Any],
) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    return c96_audit.coverage_and_capacity(keys, values, years, spec)


def _install_frozen_ranges(engine: Any) -> None:
    c96_audit._install_frozen_ranges(engine)
    ranges = dict(getattr(engine, "FACTOR_RANGES", {}))
    if FACTOR_NAME in ranges and tuple(ranges[FACTOR_NAME]) != (-1.0, 1.0):
        raise Campaign097NoReturnAuditError("conflicting Campaign097 range")
    ranges[FACTOR_NAME] = (-1.0, 1.0)
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
    if coverage.get("gate_passed_before_comparison_values") is not True:
        raise Campaign097NoReturnAuditError(
            "comparison loader called before coverage pass"
        )
    comparisons, receipts = c96_audit._load_comparisons_after_coverage(
        coverage=coverage,
        candidate_keys=candidate_keys,
        candidate_values=candidate_values,
        gate=gate,
        engine=engine,
        comparison_engine=comparison_engine,
        workers=workers,
    )
    if len(comparisons) != 124:
        raise Campaign097NoReturnAuditError("first 124 comparison order changed")
    result, receipt = compact_helper._compact_snapshot_comparison(
        manifest_path=C96_MANIFEST_PATH,
        expected_manifest_sha256=C96_MANIFEST_SHA256,
        factor=C96_FACTOR_NAME,
        candidate_keys=candidate_keys,
        candidate_values=candidate_values,
        gate=gate,
        comparison_engine=comparison_engine,
        verifier=c96_audit.verify_candidate_snapshot,
    )
    comparisons.append(result)
    receipts["campaign096_compact_snapshot"] = receipt
    receipts.pop("all_124_sources_loaded_in_frozen_order", None)
    receipts["all_125_sources_loaded_in_frozen_order"] = True
    if not (
        len(comparisons) == EXPECTED_COMPARISON_COUNT
        and comparisons[-1]["comparison_factor"] == C96_FACTOR_NAME
    ):
        raise Campaign097NoReturnAuditError("Campaign097 comparison order changed")
    return comparisons, receipts


def _run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int, confirm_run: bool
) -> Path:
    if not confirm_run:
        raise Campaign097NoReturnAuditError("Campaign097 audit requires --confirm-run")
    static = verify_static_bindings()
    spec = load_protocol()
    if data_root.expanduser().resolve() != DEFAULT_DATA_ROOT.resolve():
        raise Campaign097NoReturnAuditError("Campaign097 data root changed")
    experiment_root = experiment_root.expanduser().resolve()
    if list(experiment_root.glob("*_campaign097_no_return_audit.json")):
        raise Campaign097NoReturnAuditError("Campaign097 audit already exists")
    verification = verify_candidate_snapshot()
    keys, values, years, alignment = load_candidate_arrays()
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
    observed_correlations = [
        float(item["absolute_median_daily_rank_correlation"])
        for item in comparisons
        if item.get("absolute_median_daily_rank_correlation") is not None
    ]
    maximum_correlation = max(observed_correlations) if observed_correlations else None
    admissible = int(
        coverage["gate_passed_before_comparison_values"]
        and all_comparisons_passed
        and len(comparisons) == EXPECTED_COMPARISON_COUNT
    )
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign097_no_return_audit",
        "status": (
            "completed_one_admissible_factor_ready_for_frozen_development_trial"
            if admissible
            else "completed_zero_admissible_factors_stop_before_historical_daily_prices_or_returns"
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": f"{run_id}_campaign097_no_return_audit",
        "protocol": {
            "path": str(definitions.DEFAULT_PROTOCOL.resolve()),
            "sha256": definitions.PROTOCOL_SHA256,
        },
        "candidate_snapshot": {
            "path": str(SNAPSHOT_MANIFEST_PATH.resolve()),
            "sha256": SNAPSHOT_MANIFEST_SHA256,
            "dataset_sha256": SNAPSHOT_DATASET_SHA256,
        },
        "static_bindings": static,
        "snapshot_file_verification": verification,
        "candidate_to_quality_listing_alignment": alignment,
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
                        "name": name,
                        "numeric_status": "ineligible_or_undefined_not_pass_not_fail",
                        "mechanism_overlap_status": "explicitly_challenged_before_values",
                    }
                    for name in STRUCTURALLY_NONNUMERIC_FACTORS
                ],
            }
        },
        "admissible_factor_count": admissible,
        "admissible_factor_names": [FACTOR_NAME] if admissible else [],
        "failed_factor_names": [] if admissible else [FACTOR_NAME],
        "next_action": (
            "freeze and run exactly the preregistered single development trial"
            if admissible
            else "record no-return rejection and begin only a genuinely new campaign"
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
            "ready_for_single_audit"
            if AUDIT_ACTIVATION_BINDING.is_file()
            else "activation_binding_absent"
        ),
        "candidate_snapshot_exists": SNAPSHOT_MANIFEST_PATH.is_file(),
        "audit_count": len(
            list(
                experiment_root.expanduser()
                .resolve()
                .glob("*_campaign097_no_return_audit.json")
            )
        ),
        "coverage_or_capacity_metrics_computed_by_status": False,
        "comparison_values_read_by_status": False,
        "historical_daily_price_or_forward_return_values_read_by_status": False,
        "provider_request_issued_by_status": False,
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
        print(json.dumps(status(args.experiment_root), sort_keys=True))
        return 0
    print(
        _run_no_return_audit(
            data_root=args.data_root,
            experiment_root=args.experiment_root,
            workers=args.workers,
            confirm_run=args.confirm_run,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
