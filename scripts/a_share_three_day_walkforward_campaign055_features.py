#!/usr/bin/env python3
"""Build the frozen Campaign055 price-update clock-entropy feature."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    import scripts.a_share_three_day_preregistration_binding_validator as bindings
    import scripts.a_share_three_day_walkforward_campaign054_features as previous
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_three_day_walkforward_campaign054_features as previous


REPO_ROOT = Path(__file__).resolve().parents[1]
FACTOR_NAME = "intraday_price_update_clock_entropy_10b_238m"
FACTOR_FORMULA = (
    "On the exact 240-bar continuous grid, form 119 adjacent close comparisons "
    "separately within each half. Define an update event as exact close_t != "
    "close_t-1. For transition index k=0..118, map morning events to "
    "floor(5*k/119) and afternoon events to 5+floor(5*k/119). For ten event "
    "counts c_b and N=sum(c_b), return -sum over c_b>0 of "
    "(c_b/N)*ln(c_b/N)/ln(10)."
)
MECHANISM_AUDIT_SHA256 = (
    "01fe62e9bafafe600e7bf62cb31db884735705b06b14fc782af8780621f69a11"
)
PROTOCOL_SHA256 = (
    "f469879dd83a22a15d497d903bc81c772d5d96dae81d4ac7e32edfba1ef0732f"
)
IMPLEMENTATION_FREEZE_SHA256 = ""
SNAPSHOT_MANIFEST_SHA256 = ""
SNAPSHOT_DATASET_SHA256 = ""
SNAPSHOT_PUBLICATION_BINDING_SHA256 = ""
NO_RETURN_AUDIT_SHA256 = ""

SELECTED_BAR_COUNT = 240
HALF_BAR_COUNT = 120
WITHIN_HALF_TRANSITION_COUNT = 119
TOTAL_TRANSITION_COUNT = 238
BIN_COUNT = 10
MINIMUM_UPDATE_EVENTS = 20
INHERITED_COMPARISON_COUNT = 77
COMPARISON_COUNT = 78
INHERITED_COMPARISON_ORDER_SHA256 = (
    "f6ec66bf87ae76240e1ad890699cb2a82856f32a327a2f9be52d3d1f0b753de2"
)
COMPARISON_ORDER_SHA256 = (
    "2a9d3188624bd7dd2556de5754f1ce401b0b04c2b47ca8cf15dae46a56253de6"
)
LOWER_BOUND = 0.0
UPPER_BOUND = 1.0
ENDPOINT_TOLERANCE = 1e-12
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign055_feature_library_v1"
)
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_055_no_return_preregistration.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_055_feature_implementation_freeze_20260804.json"
)
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_055/no_return"
)
DEFAULT_DATA_ROOT = previous.DEFAULT_DATA_ROOT
RAW_COLUMNS = ("datetime", "symbol", "provider", "close")
BASE_COLUMNS = previous.BASE_COLUMNS
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
FACTOR_NAMES = (FACTOR_NAME,)
FACTOR_DIRECTIONS = {FACTOR_NAME: "higher"}
FACTOR_RANGES = {FACTOR_NAME: (LOWER_BOUND, UPPER_BOUND)}
FACTOR_FORMULAS = {FACTOR_NAME: FACTOR_FORMULA}

_HALF_BIN_INDEX = np.floor(
    5.0 * np.arange(WITHIN_HALF_TRANSITION_COUNT) / WITHIN_HALF_TRANSITION_COUNT
).astype(np.int64)
TRANSITION_BIN_INDEX = np.concatenate([_HALF_BIN_INDEX, 5 + _HALF_BIN_INDEX])

_generated = previous._generated
_engine_globals = previous._engine_globals
market = previous.market


class Campaign055FeatureError(RuntimeError):
    """Fail-closed Campaign055 feature-boundary error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected_sha256:
        raise Campaign055FeatureError(f"{label} changed")


def _comparison_order_digest(comparisons: list[dict[str, Any]]) -> str:
    payload = json.dumps(
        [
            (str(item["name"]), str(item["score_direction"]))
            for item in comparisons
        ],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def output_root(data_root: Path) -> Path:
    return (
        data_root.expanduser().resolve()
        / "derived/a_share/rich/tushare/minute_walkforward_campaign055_feature_library"
        / OUTPUT_RUN_ID
    )


def _load_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE_SHA256:
        raise Campaign055FeatureError(
            "Campaign055 implementation freeze is not bound"
        )
    _require_file(
        DEFAULT_IMPLEMENTATION_FREEZE,
        IMPLEMENTATION_FREEZE_SHA256,
        "Campaign055 implementation freeze",
    )
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    runner = record.get("feature_runner") or {}
    protocol = record.get("no_return_protocol") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign055_feature_implementation_freeze"
        and record.get("status") == "frozen_before_campaign055_candidate_values"
        and Path(str(runner.get("path"))).resolve() == Path(__file__).resolve()
        and runner.get("sha256") == _sha256(Path(__file__).resolve())
        and protocol.get("sha256") == PROTOCOL_SHA256
        and record.get("candidate_values_read_before_freeze") is False
        and record.get("comparison_values_read_before_freeze") is False
        and record.get(
            "historical_daily_price_or_forward_returns_read_before_freeze"
        )
        is False
    ):
        raise Campaign055FeatureError(
            "Campaign055 implementation freeze semantics changed"
        )
    return record


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    _require_file(path, PROTOCOL_SHA256, "Campaign055 no-return protocol")
    validation = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if validation.get("all_bindings_passed") is not True:
        raise Campaign055FeatureError("Campaign055 protocol has a failed binding")
    spec = json.loads(path.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    inherited = previous.load_protocol()
    inherited_comparisons = copy.deepcopy(
        inherited["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
            "comparison_factors"
        ]
    )
    comparisons = inherited_comparisons + [
        copy.deepcopy(uniqueness.get("final_comparison_factor") or {})
    ]
    if not (
        spec.get("version") == 1
        and spec.get("kind")
        == "a_share_three_day_walkforward_campaign055_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign055_candidate_comparison_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_projection") or ()) == RAW_COLUMNS
        and candidate.get("forbidden_source_columns")
        == ["open", "high", "low", "volume", "amount"]
        and candidate.get("within_half_transition_count")
        == WITHIN_HALF_TRANSITION_COUNT
        and candidate.get("total_transition_count") == TOTAL_TRANSITION_COUNT
        and candidate.get("clock_bin_count") == BIN_COUNT
        and candidate.get("minimum_update_events") == MINIMUM_UPDATE_EVENTS
        and candidate.get(
            "alternate_bin_count_minimum_event_direction_window_transform_scale_clip_threshold_filter_subset_board_year_cost_regime_fit_combination_or_model_search"
        )
        is False
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and uniqueness.get(
            "maximum_allowed_absolute_median_daily_rank_correlation"
        )
        == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and uniqueness.get("inherited_campaign054_comparison_factor_count")
        == INHERITED_COMPARISON_COUNT
        and uniqueness.get(
            "inherited_campaign054_comparison_factor_order_sha256"
        )
        == INHERITED_COMPARISON_ORDER_SHA256
        and uniqueness.get("comparison_factor_count") == COMPARISON_COUNT
        and uniqueness.get("comparison_factor_order_sha256")
        == COMPARISON_ORDER_SHA256
        and len(inherited_comparisons) == INHERITED_COMPARISON_COUNT
        and len(comparisons) == COMPARISON_COUNT
        and _comparison_order_digest(comparisons) == COMPARISON_ORDER_SHA256
        and finite.get("trial_id") == f"wf055_{FACTOR_NAME}_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("expected_trial_count") == 1
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility")
        is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign055FeatureError("Campaign055 protocol semantics changed")
    result = copy.deepcopy(spec)
    result["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ] = comparisons
    return result


def compute_factor_values(
    closes: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute frozen ten-bin entropy of within-half close-update clock locations."""

    closes = np.asarray(closes, dtype=float)
    if closes.ndim != 2 or closes.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign055FeatureError("closes must have shape (n, 240)")
    rows = len(closes)
    finite_close = np.isfinite(closes).all(axis=1)
    positive_close = (closes > 0.0).all(axis=1)
    morning_updates = closes[:, 1:HALF_BAR_COUNT] != closes[:, : HALF_BAR_COUNT - 1]
    afternoon_updates = (
        closes[:, HALF_BAR_COUNT + 1 :] != closes[:, HALF_BAR_COUNT:-1]
    )
    updates = np.concatenate([morning_updates, afternoon_updates], axis=1)
    if updates.shape[1] != TOTAL_TRANSITION_COUNT:
        raise Campaign055FeatureError("within-half transition grid changed")
    update_count = updates.sum(axis=1)
    counts = np.stack(
        [
            updates[:, TRANSITION_BIN_INDEX == index].sum(axis=1)
            for index in range(BIN_COUNT)
        ],
        axis=1,
    )
    denominator = np.where(update_count > 0, update_count, 1).astype(float)
    probabilities = counts.astype(float) / denominator[:, None]
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        terms = np.where(
            probabilities > 0.0,
            probabilities * np.log(probabilities),
            0.0,
        )
        raw_score = -np.sum(terms, axis=1) / np.log(float(BIN_COUNT))
    low_fix = (raw_score < LOWER_BOUND) & (
        raw_score >= LOWER_BOUND - ENDPOINT_TOLERANCE
    )
    high_fix = (raw_score > UPPER_BOUND) & (
        raw_score <= UPPER_BOUND + ENDPOINT_TOLERANCE
    )
    score = np.where(low_fix, LOWER_BOUND, raw_score)
    score = np.where(high_fix, UPPER_BOUND, score)
    score_finite = np.isfinite(score)
    score_in_range = (score >= LOWER_BOUND) & (score <= UPPER_BOUND)
    sufficient_updates = update_count >= MINIMUM_UPDATE_EVENTS
    eligible = (
        finite_close
        & positive_close
        & sufficient_updates
        & score_finite
        & score_in_range
    )
    input_valid = finite_close & positive_close
    quality = {
        "base_rows": int(rows),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__nonfinite_close_rows": int((~finite_close).sum()),
        f"{FACTOR_NAME}__nonpositive_close_rows": int(
            (finite_close & ~positive_close).sum()
        ),
        f"{FACTOR_NAME}__insufficient_update_event_rows": int(
            (input_valid & ~sufficient_updates).sum()
        ),
        f"{FACTOR_NAME}__eligible_update_events": int(update_count[eligible].sum()),
        f"{FACTOR_NAME}__eligible_empty_bin_positions": int(
            (counts[eligible] == 0).sum()
        ),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int(
            (eligible & (low_fix | high_fix)).sum()
        ),
        f"{FACTOR_NAME}__range_or_nonfinite_score_rows": int(
            (input_valid & sufficient_updates & (~score_finite | ~score_in_range)).sum()
        ),
    }
    return (
        {FACTOR_NAME: np.where(eligible, score, np.nan)},
        {FACTOR_NAME: eligible},
        quality,
    )


def compute_partition_frame(
    raw: pd.DataFrame,
    base_frame: pd.DataFrame,
    _unused_benchmark: Any,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign055FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign055FeatureError(
            f"unexpected joint-base columns for {symbol}: {tuple(base_frame.columns)}"
        )
    base_work = base_frame.copy()
    base_work["trade_date"] = pd.to_datetime(
        base_work["trade_date"], errors="coerce"
    ).dt.normalize()
    base_work["symbol"] = base_work["symbol"].astype(str).str.upper()
    if (
        base_work["trade_date"].isna().any()
        or (
            not base_work.empty
            and set(base_work["symbol"].unique()) != {symbol.upper()}
        )
        or base_work.duplicated(["trade_date", "symbol"]).any()
    ):
        raise Campaign055FeatureError(f"joint-base identity changed for {symbol}")
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(
        drop=True
    )
    if base_work.empty:
        return empty_output_frame(), {"base_rows": 0}
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["close"] = pd.to_numeric(work["close"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign055FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign055FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(value) for value in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign055FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign055FeatureError(
            f"source and joint-base dates changed for {symbol}"
        )
    continuous = work.loc[
        work["minute_code"].isin(market.CONTINUOUS_MINUTE_CODES),
        ["trade_date", "minute_code", "close"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"],
        categories=market.CONTINUOUS_MINUTE_CODES,
        ordered=True,
    )
    continuous = continuous.sort_values(
        ["trade_date", "minute_code"], kind="stable"
    )
    if len(continuous) != len(base_work) * SELECTED_BAR_COUNT:
        raise Campaign055FeatureError(f"continuous minute grid changed for {symbol}")
    closes = continuous["close"].to_numpy(dtype=float).reshape(
        -1, SELECTED_BAR_COUNT
    )
    values, eligible, quality = compute_factor_values(closes)
    frame = pd.DataFrame(
        {
            "trade_date": base_work["trade_date"],
            "symbol": symbol.upper(),
            "provider": "tushare",
            FACTOR_NAME: values[FACTOR_NAME],
            f"{FACTOR_NAME}_eligible": eligible[FACTOR_NAME],
        }
    )
    return frame.loc[:, OUTPUT_COLUMNS], quality


def _validate_snapshot_manifest(
    manifest: dict[str, Any], *, require_fingerprint_constants: bool
) -> None:
    if not require_fingerprint_constants:
        manifest["kind"] = (
            "a_share_three_day_walkforward_campaign055_feature_snapshot"
        )
        manifest["source_open_high_low_read"] = False
        manifest["source_close_read"] = True
        manifest["source_volume_read"] = False
        manifest["source_amount_read"] = False
        evidence = {
            key: value
            for key, value in (manifest.get("protocol_evidence") or {}).items()
            if not key.startswith("campaign054_")
            and not key.startswith("campaign055_")
        }
        evidence["campaign055_mechanism_overlap_audit_sha256"] = (
            MECHANISM_AUDIT_SHA256
        )
        evidence["campaign055_no_return_preregistration_sha256"] = PROTOCOL_SHA256
        evidence["campaign055_implementation_freeze_sha256"] = (
            IMPLEMENTATION_FREEZE_SHA256
        )
        manifest["protocol_evidence"] = evidence
    evidence = manifest.get("protocol_evidence") or {}
    quality = manifest.get("quality") or {}
    files = list(manifest.get("files") or [])
    eligible_rows = (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    if not (
        manifest.get("schema_version") == 1
        and manifest.get("kind")
        == "a_share_three_day_walkforward_campaign055_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_open_high_low_read") is False
        and manifest.get("source_close_read") is True
        and manifest.get("source_volume_read") is False
        and manifest.get("source_amount_read") is False
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == FACTOR_DIRECTIONS
        and manifest.get("factor_formulas") == FACTOR_FORMULAS
        and manifest.get("protocol_sha256") == PROTOCOL_SHA256
        and evidence.get("campaign055_mechanism_overlap_audit_sha256")
        == MECHANISM_AUDIT_SHA256
        and evidence.get("campaign055_no_return_preregistration_sha256")
        == PROTOCOL_SHA256
        and evidence.get("campaign055_implementation_freeze_sha256")
        == IMPLEMENTATION_FREEZE_SHA256
        and isinstance(manifest.get("rows"), int)
        and manifest["rows"] > 0
        and manifest.get("partitions") == len(files)
        and quality.get("base_rows") == manifest.get("rows")
        and quality.get(f"{FACTOR_NAME}__eligible_rows") == eligible_rows
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("candidate49_historical_return_read") is False
        and manifest.get("training_or_model_fitting_performed") is False
        and manifest.get("current_scoring_selection_sizing_or_orders_performed")
        is False
        and manifest.get("prospective_candidate_activation_created") is False
    ):
        raise Campaign055FeatureError("Campaign055 snapshot semantics changed")
    if require_fingerprint_constants and not (
        SNAPSHOT_MANIFEST_SHA256
        and SNAPSHOT_DATASET_SHA256
        and manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
    ):
        raise Campaign055FeatureError(
            "Campaign055 snapshot fingerprint is not bound"
        )


def _install_engine_globals() -> None:
    values = {
        "DEFAULT_PROTOCOL": DEFAULT_PROTOCOL,
        "DEFAULT_EXPERIMENT_ROOT": DEFAULT_EXPERIMENT_ROOT,
        "RAW_COLUMNS": RAW_COLUMNS,
        "FACTOR_NAME": FACTOR_NAME,
        "FACTOR_NAMES": FACTOR_NAMES,
        "FACTOR_DIRECTIONS": FACTOR_DIRECTIONS,
        "FACTOR_RANGES": FACTOR_RANGES,
        "FACTOR_FORMULA": FACTOR_FORMULA,
        "FACTOR_FORMULAS": FACTOR_FORMULAS,
        "OUTPUT_COLUMNS": OUTPUT_COLUMNS,
        "OUTPUT_RUN_ID": OUTPUT_RUN_ID,
        "PROTOCOL_SHA256": PROTOCOL_SHA256,
        "SNAPSHOT_MANIFEST_SHA256": SNAPSHOT_MANIFEST_SHA256,
        "SNAPSHOT_DATASET_SHA256": SNAPSHOT_DATASET_SHA256,
        "NO_RETURN_AUDIT_SHA256": NO_RETURN_AUDIT_SHA256,
        "load_protocol": load_protocol,
        "compute_factor_values": compute_factor_values,
        "compute_partition_frame": compute_partition_frame,
        "_validate_snapshot_manifest": _validate_snapshot_manifest,
        "output_root": output_root,
    }
    _generated.update(values)
    _engine_globals.update(values)


_install_engine_globals()
empty_output_frame = _generated["empty_output_frame"]
verify_snapshot_files = _generated["verify_snapshot_files"]


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    _load_implementation_freeze()
    _install_engine_globals()
    inherited = _generated["_inherited_build_snapshot"]
    inherited_writer = inherited.__globals__["_inherited_build_snapshot"]
    publication_foundation = inherited_writer.__globals__["foundation"]
    original = publication_foundation.atomic_write_json

    def write_with_truth(value: dict[str, Any], path: Path) -> None:
        if (
            value.get("kind")
            == "a_share_three_day_walkforward_campaign055_feature_snapshot"
            and value.get("output_run_id") == OUTPUT_RUN_ID
        ):
            value = dict(value)
            value.update(
                {
                    "source_open_high_low_read": False,
                    "source_close_read": True,
                    "source_volume_read": False,
                    "source_amount_read": False,
                    "quarterly_disclosure_fields_read": [],
                    "quarterly_value_fields_read": [],
                }
            )
        original(value, path)

    publication_foundation.atomic_write_json = write_with_truth
    try:
        return inherited(data_root=data_root, workers=workers)
    finally:
        publication_foundation.atomic_write_json = original


def status(data_root: Path, experiment_root: Path) -> dict[str, Any]:
    _install_engine_globals()
    manifest_path = output_root(data_root.expanduser().resolve()) / "snapshot_manifest.json"
    audits = sorted(
        experiment_root.expanduser().resolve().glob(
            "*_campaign055_no_return_audit.json"
        )
    )
    result = {
        "protocol_path": str(DEFAULT_PROTOCOL.resolve()),
        "protocol_sha256_bound": True,
        "implementation_freeze_sha256_bound": bool(
            IMPLEMENTATION_FREEZE_SHA256
        ),
        "snapshot_manifest_path": str(manifest_path),
        "snapshot_exists": manifest_path.is_file(),
        "snapshot_sha256_bound": bool(SNAPSHOT_MANIFEST_SHA256),
        "audit_count": len(audits),
        "no_return_audit_sha256_bound": bool(NO_RETURN_AUDIT_SHA256),
        "source_fields_read_by_status": list(RAW_COLUMNS),
        "daily_price_fields_read_by_status": False,
        "forward_return_fields_read_by_status": False,
        "candidate49_historical_return_read": False,
        "second_prospective_candidate_created": False,
    }
    if manifest_path.is_file():
        result["snapshot_observed_sha256"] = _sha256(manifest_path)
    if audits:
        result["latest_audit"] = str(audits[-1])
        result["latest_audit_observed_sha256"] = _sha256(audits[-1])
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    build.add_argument("--workers", type=int, default=4)
    inspect = subparsers.add_parser("status")
    inspect.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    inspect.add_argument(
        "--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "build":
        payload = {
            "manifest": str(
                build_snapshot(data_root=args.data_root, workers=args.workers)
            )
        }
    else:
        payload = status(args.data_root, args.experiment_root)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
