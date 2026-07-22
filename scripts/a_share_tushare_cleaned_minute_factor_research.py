#!/usr/bin/env python3
"""Diagnose the fingerprint-bound, cleaned Tushare one-minute factor set once.

The raw and cleaned minute snapshots remain immutable.  This module joins the
joint-clean base with the small fieldwise exception overlay, applies a separate
eligibility mask to each retained factor, and stops before forward returns if
any preregistered coverage gate fails.  Once the historical return read starts,
a durable consumption marker prevents the same protocol from being rerun.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import gc
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.dataset as pa_dataset

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_short_horizon_factor_research as research


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREGISTRATION = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_cleaned_four_factor_exploratory_preregistration.json"
)
PREREGISTRATION_SHA256 = (
    "88e08350aff470e8c7b92fe5f5971f770297d2ca513593971e24d59f07105ca7"
)
DIAGNOSTIC_PURPOSE = (
    "development_only_preregistered_tushare_cleaned_four_factor_"
    "exploratory_diagnostic_research_not_investment_advice"
)
CONSUMPTION_FILENAME = "tushare_cleaned_four_factor_v1_consumption.json"
FACTOR_NAMES = (
    "late_return_30m",
    "late_amount_share_30m",
    "late_vwap_to_day_vwap_30m",
    "intraday_realized_volatility",
)
FACTOR_DIRECTIONS = ("higher", "higher", "higher", "lower")
FACTOR_ELIGIBILITY_COLUMNS = tuple(f"{name}_eligible" for name in FACTOR_NAMES)
BASE_COLUMNS = ("trade_date", "symbol", *FACTOR_NAMES)
OVERLAY_COLUMNS = (*BASE_COLUMNS, *FACTOR_ELIGIBILITY_COLUMNS)


class CleanedMinuteResearchError(RuntimeError):
    """Raised when a frozen source or research invariant no longer holds."""


def _require_exact_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    observed = research.file_sha256(path)
    if observed != expected_sha256:
        raise CleanedMinuteResearchError(
            f"{label} fingerprint mismatch: expected {expected_sha256}, got {observed}"
        )


def _record_path(path_value: str) -> Path:
    path = Path(path_value).expanduser()
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def load_preregistration(
    path: Path = DEFAULT_PREREGISTRATION,
) -> dict[str, Any]:
    """Load and strictly validate the one authorized four-factor protocol."""

    path = path.expanduser().resolve()
    _require_exact_file(path, PREREGISTRATION_SHA256, "cleaned-minute preregistration")
    spec = research.load_json_record(
        path, kind="a_share_tushare_cleaned_four_factor_exploratory_preregistration"
    )
    factors = list(spec.get("factors") or [])
    names = tuple(str(item.get("name")) for item in factors)
    directions = tuple(str(item.get("diagnostic_direction")) for item in factors)
    holding = spec.get("holding_protocol") or {}
    coverage = spec.get("coverage_gate_before_forward_returns") or {}
    diagnostic = spec.get("historical_diagnostic") or {}
    aggregation = spec.get("post_diagnostic_aggregation_policy") or {}
    boundary = spec.get("research_boundary") or {}
    valid = (
        spec.get("version") == 1
        and spec.get("status")
        == "frozen_before_first_cleaned_four_factor_forward_return_read"
        and names == FACTOR_NAMES
        and directions == FACTOR_DIRECTIONS
        and (spec.get("explicit_exclusion") or {}).get("factor")
        == "opening_gap_digestion"
        and holding.get("universe") == "buyable_main_chinext"
        and holding.get("minimum_listing_sessions") == research.MIN_LISTING_SESSIONS
        and holding.get("holding_period_trading_days") == 3
        and holding.get("non_overlapping_cohorts") is True
        and holding.get("topk") == 3
        and holding.get("open_cost") == 0.00012
        and holding.get("close_cost") == 0.00062
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_names_per_factor_cross_section") == 50
        and coverage.get("minimum_potential_non_overlapping_three_session_cohorts")
        == research.FACTOR_STABILITY_MIN_COHORTS
        and coverage.get("all_four_factors_must_pass") is True
        and diagnostic.get("development_start") == "2019-01-01"
        and diagnostic.get("development_end") == "2025-12-31"
        and diagnostic.get("minimum_observed_calendar_years")
        == research.FACTOR_STABILITY_MIN_CALENDAR_YEARS
        and diagnostic.get("minimum_non_overlapping_cohorts")
        == research.FACTOR_STABILITY_MIN_COHORTS
        and diagnostic.get("selection_or_promotion_allowed") is False
        and aggregation.get("minimum_qualified_factor_count") == 2
        and tuple(aggregation.get("factor_order") or []) == FACTOR_NAMES
        and aggregation.get("weighting") == "equal_one_over_qualified_factor_count"
        and aggregation.get(
            "no_subset_direction_window_threshold_weight_or_aggregation_search"
        )
        is True
        and aggregation.get("same_history_combination_return_evaluation_allowed")
        is False
        and boundary.get("forward_return_fields_read_before_registration") is False
        and boundary.get("current_scoring_selection_sizing_or_orders_allowed") is False
    )
    if not valid:
        raise CleanedMinuteResearchError(
            "cleaned-minute preregistration no longer matches its frozen protocol"
        )
    return spec


def validate_repository_source_records(spec: dict[str, Any]) -> dict[str, Any]:
    """Validate repository-side cleaning, price-basis, quality, and policy links."""

    evidence: dict[str, Any] = {}
    records = (spec.get("source_chain") or {}).get("repository_records") or {}
    for name, link in records.items():
        path = _record_path(str(link.get("path") or ""))
        expected = str(link.get("sha256") or "")
        _require_exact_file(path, expected, name.replace("_", " "))
        evidence[name] = {"path": str(path), "sha256": expected}

    price = spec.get("accepted_daily_price_basis") or {}
    price_path = _record_path(str(price.get("path") or ""))
    _require_exact_file(
        price_path, str(price.get("sha256") or ""), "accepted daily price basis"
    )
    price_record = research.load_json_record(price_path)
    if (
        price_record.get("price_basis") != price.get("price_basis")
        or price_record.get("daily_sources") != [price.get("provider")]
        or price_record.get("status") != "passed"
    ):
        raise CleanedMinuteResearchError(
            "accepted daily price-basis record conflicts with the preregistration"
        )
    evidence["accepted_daily_price_basis"] = {
        "path": str(price_path),
        "sha256": str(price["sha256"]),
        "price_basis": str(price["price_basis"]),
    }

    quality = spec.get("quarterly_quality") or {}
    for path_key, hash_key, label in (
        ("path", "sha256", "quarterly quality snapshot"),
        ("manifest_path", "manifest_sha256", "quarterly quality manifest"),
    ):
        path = _record_path(str(quality.get(path_key) or ""))
        _require_exact_file(path, str(quality.get(hash_key) or ""), label)
        evidence[path_key] = {
            "path": str(path),
            "sha256": str(quality[hash_key]),
        }

    policies = spec.get("execution_policies") or {}
    for name in ("prospective_execution", "pilot_execution"):
        link = policies.get(name) or {}
        path = _record_path(str(link.get("path") or ""))
        _require_exact_file(path, str(link.get("sha256") or ""), name)
        evidence[name] = {"path": str(path), "sha256": str(link["sha256"])}
    return evidence


def validate_external_source_manifests(
    spec: dict[str, Any], minute_data_root: Path
) -> tuple[dict[str, Any], dict[str, Any], Path, Path]:
    """Validate the external joint-clean and fieldwise overlay manifests."""

    source = spec.get("source_chain") or {}
    joint_link = source.get("joint_clean_manifest") or {}
    fieldwise_link = source.get("fieldwise_clean_manifest") or {}
    joint_path = minute_data_root / str(joint_link.get("path_below_data_root") or "")
    fieldwise_path = minute_data_root / str(
        fieldwise_link.get("path_below_data_root") or ""
    )
    joint_path = joint_path.expanduser().resolve()
    fieldwise_path = fieldwise_path.expanduser().resolve()
    _require_exact_file(
        joint_path, str(joint_link.get("sha256") or ""), "joint-clean manifest"
    )
    _require_exact_file(
        fieldwise_path,
        str(fieldwise_link.get("sha256") or ""),
        "fieldwise-clean manifest",
    )
    joint = research.load_json_record(
        joint_path, kind="a_share_tushare_one_minute_sentiment_clean_snapshot"
    )
    fieldwise = research.load_json_record(
        fieldwise_path, kind="a_share_tushare_one_minute_fieldwise_clean_snapshot"
    )
    if (
        joint.get("status")
        != "cleaned_sentiment_coverage_passed_pending_separate_no_return_research_protocol"
        or joint.get("dataset_sha256") != joint_link.get("dataset_sha256")
        or joint.get("rows") != joint_link.get("rows")
        or joint.get("partitions") != joint_link.get("partitions")
        or tuple(joint.get("feature_columns") or []) != FACTOR_NAMES
        or joint.get("forward_return_fields_read") is not False
        or joint.get("promotion_allowed") is not False
    ):
        raise CleanedMinuteResearchError(
            "joint-clean manifest conflicts with the frozen research source"
        )
    if (
        fieldwise.get("status")
        != "fieldwise_factor_coverage_passed_pending_separate_exploratory_research_preregistration"
        or fieldwise.get("joint_manifest_sha256") != joint_link.get("sha256")
        or fieldwise.get("joint_base_rows") != joint_link.get("rows")
        or fieldwise.get("overlay_rows") != fieldwise_link.get("overlay_rows")
        or fieldwise.get("overlay_byte_sha256")
        != fieldwise_link.get("overlay_byte_sha256")
        or fieldwise.get("overlay_frame_sha256")
        != fieldwise_link.get("overlay_frame_sha256")
        or tuple(fieldwise.get("factor_columns") or []) != FACTOR_NAMES
        or tuple(fieldwise.get("factor_eligibility_columns") or [])
        != FACTOR_ELIGIBILITY_COLUMNS
        or fieldwise.get("all_factor_coverage_gates_passed") is not True
        or fieldwise.get("forward_return_fields_read") is not False
        or fieldwise.get("training_or_model_fitting_performed") is not False
        or fieldwise.get("promotion_allowed") is not False
    ):
        raise CleanedMinuteResearchError(
            "fieldwise-clean manifest conflicts with the frozen research source"
        )
    overlay_path = (
        (
            minute_data_root
            / str(fieldwise_link.get("overlay_path_below_data_root") or "")
        )
        .expanduser()
        .resolve()
    )
    _require_exact_file(
        overlay_path,
        str(fieldwise_link.get("overlay_byte_sha256") or ""),
        "fieldwise exception overlay",
    )
    return joint, fieldwise, joint_path, overlay_path


def verify_joint_partition_bytes(
    joint_manifest: dict[str, Any], joint_manifest_path: Path, workers: int = 8
) -> dict[str, Any]:
    """Verify every cleaned partition byte hash before loading factor values."""

    records = list(joint_manifest.get("files") or [])
    expected_count = int(joint_manifest.get("partitions") or 0)
    if len(records) != expected_count:
        raise CleanedMinuteResearchError(
            f"joint manifest lists {len(records)} files, expected {expected_count}"
        )
    partitions_root = (joint_manifest_path.parent / "partitions").resolve()

    def verify(record: dict[str, Any]) -> tuple[int, int]:
        path = Path(str(record.get("path") or "")).expanduser().resolve()
        try:
            path.relative_to(partitions_root)
        except ValueError as error:
            raise CleanedMinuteResearchError(
                f"joint-clean partition escapes its frozen root: {path}"
            ) from error
        _require_exact_file(
            path,
            str(record.get("output_byte_sha256") or ""),
            "joint-clean partition",
        )
        return int(record.get("rows") or 0), path.stat().st_size

    rows = 0
    bytes_verified = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for index, (partition_rows, partition_bytes) in enumerate(
            pool.map(verify, records), start=1
        ):
            rows += partition_rows
            bytes_verified += partition_bytes
            if index % 5000 == 0 or index == len(records):
                print(
                    f"verified cleaned minute partitions {index}/{len(records)}",
                    flush=True,
                )
    if rows != int(joint_manifest.get("rows") or -1):
        raise CleanedMinuteResearchError(
            f"joint partition row total changed: expected {joint_manifest.get('rows')}, got {rows}"
        )
    return {
        "partitions_verified": len(records),
        "manifest_rows_verified": rows,
        "partition_bytes_verified": bytes_verified,
    }


def _validate_factor_values(frame: pd.DataFrame, eligibility: pd.DataFrame) -> None:
    for factor in FACTOR_NAMES:
        values = pd.to_numeric(frame[factor], errors="coerce")
        eligible = eligibility[f"{factor}_eligible"].fillna(False).astype(bool)
        if not np.isfinite(values.loc[eligible].to_numpy(dtype=float)).all():
            raise CleanedMinuteResearchError(
                f"eligible cleaned-minute values are not finite for {factor}"
            )
        if (
            factor in {"late_return_30m", "late_vwap_to_day_vwap_30m"}
            and (values.loc[eligible] <= -1.0).any()
        ):
            raise CleanedMinuteResearchError(f"invalid return-like value for {factor}")
        if (
            factor == "late_amount_share_30m"
            and not values.loc[eligible].between(0.0, 1.0).all()
        ):
            raise CleanedMinuteResearchError("late amount share is outside [0, 1]")
        if (
            factor == "intraday_realized_volatility"
            and (values.loc[eligible] < 0.0).any()
        ):
            raise CleanedMinuteResearchError("realized volatility is negative")
        frame[factor] = values.astype("float64")


def load_cleaned_minute_features(
    joint_manifest: dict[str, Any],
    joint_manifest_path: Path,
    overlay_path: Path,
    expected_overlay_frame_sha256: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Materialize the four-factor base and fieldwise overlay as one narrow frame."""

    partitions_root = joint_manifest_path.parent / "partitions"
    print("loading cleaned four-factor base", flush=True)
    dataset = pa_dataset.dataset(str(partitions_root), format="parquet")
    table = dataset.to_table(columns=list(BASE_COLUMNS), use_threads=True)
    base = table.to_pandas(split_blocks=True, self_destruct=True)
    del table, dataset
    gc.collect()
    if len(base) != int(joint_manifest.get("rows") or -1):
        raise CleanedMinuteResearchError(
            f"joint-clean row count changed: expected {joint_manifest.get('rows')}, got {len(base)}"
        )
    overlay = pd.read_parquet(overlay_path)
    if research.dataframe_content_sha256(overlay) != expected_overlay_frame_sha256:
        raise CleanedMinuteResearchError("fieldwise overlay frame fingerprint mismatch")
    if len(overlay) == 0:
        raise CleanedMinuteResearchError("fieldwise overlay is unexpectedly empty")
    if missing := sorted(set(OVERLAY_COLUMNS) - set(overlay.columns)):
        raise CleanedMinuteResearchError(
            "fieldwise overlay is missing columns: " + ", ".join(missing)
        )
    overlay = overlay.loc[:, list(OVERLAY_COLUMNS)].copy()

    base["trade_date"] = pd.to_datetime(
        base["trade_date"], errors="coerce"
    ).dt.normalize()
    overlay["trade_date"] = pd.to_datetime(
        overlay["trade_date"], errors="coerce"
    ).dt.normalize()
    base["symbol"] = base["symbol"].astype(str).str.upper()
    overlay["symbol"] = overlay["symbol"].astype(str).str.upper()
    for column in FACTOR_ELIGIBILITY_COLUMNS:
        base[column] = True
        overlay[column] = overlay[column].astype("boolean").fillna(False).astype(bool)
    _validate_factor_values(base, base[list(FACTOR_ELIGIBILITY_COLUMNS)])
    _validate_factor_values(overlay, overlay[list(FACTOR_ELIGIBILITY_COLUMNS)])
    combined = pd.concat(
        [base[list(OVERLAY_COLUMNS)], overlay[list(OVERLAY_COLUMNS)]],
        ignore_index=True,
        copy=False,
    )
    del base, overlay
    gc.collect()
    if (
        combined["trade_date"].isna().any()
        or combined["symbol"].str.fullmatch(r"(?:SH|SZ)\d{6}").ne(True).any()
        or combined.duplicated(["trade_date", "symbol"]).any()
    ):
        raise CleanedMinuteResearchError(
            "cleaned four-factor frame has an invalid or duplicate stock-day key"
        )
    combined["symbol"] = combined["symbol"].astype("category")
    observed = {
        "rows": int(len(combined)),
        "joint_base_rows": int(joint_manifest["rows"]),
        "fieldwise_overlay_rows": int(len(combined) - int(joint_manifest["rows"])),
        "instruments": int(combined["symbol"].nunique()),
        "calendar_start": combined["trade_date"].min().date().isoformat(),
        "calendar_end": combined["trade_date"].max().date().isoformat(),
    }
    return combined, observed


def attach_factor_specific_scores(
    market: pd.DataFrame,
    features: pd.DataFrame,
    spec: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Attach and rank each factor under its own cleaned eligibility mask."""

    required_market = {
        "datetime",
        "instrument",
        "open",
        "close",
        "quality_eligible",
        "fundamental_quality_eligible",
        "listing_seasoning_eligible",
        "listing_age_sessions",
    }
    if missing := sorted(required_market - set(market.columns)):
        raise CleanedMinuteResearchError(
            "market frame is missing columns: " + ", ".join(missing)
        )
    minute = features.rename(
        columns={"trade_date": "datetime", "symbol": "instrument"}
    ).copy()
    minute["datetime"] = pd.to_datetime(minute["datetime"]).dt.normalize()
    categories = pd.Index(
        sorted(
            set(minute["instrument"].astype(str).unique())
            | set(market["instrument"].astype(str).unique())
        )
    )
    symbol_dtype = pd.CategoricalDtype(categories=categories)
    minute["instrument"] = minute["instrument"].astype(str).astype(symbol_dtype)
    market = market.copy()
    market["instrument"] = market["instrument"].astype(str).astype(symbol_dtype)
    result = market.merge(
        minute[["datetime", "instrument", *FACTOR_NAMES, *FACTOR_ELIGIBILITY_COLUMNS]],
        on=["datetime", "instrument"],
        how="left",
        validate="one_to_one",
    )
    del minute, market
    gc.collect()

    quality_eligible = result["quality_eligible"].fillna(False).astype(bool)
    feature_start = features["trade_date"].min()
    feature_end = features["trade_date"].max()
    in_feature_span = result["datetime"].between(feature_start, feature_end)
    quality_counts = (
        result.loc[in_feature_span & quality_eligible]
        .groupby("datetime", observed=True, sort=True)
        .size()
    )
    if quality_counts.empty or (quality_counts <= 0).any():
        raise CleanedMinuteResearchError(
            "quality-eligible coverage denominator is empty"
        )

    coverage_spec = spec["coverage_gate_before_forward_returns"]
    minimum_median = float(coverage_spec["minimum_median_coverage"])
    minimum_p05 = float(coverage_spec["minimum_p05_coverage"])
    minimum_names = int(coverage_spec["minimum_names_per_factor_cross_section"])
    minimum_cohorts = int(
        coverage_spec["minimum_potential_non_overlapping_three_session_cohorts"]
    )
    hold_days = int(spec["holding_protocol"]["holding_period_trading_days"])
    coverage: dict[str, Any] = {
        "coverage_basis": str(coverage_spec["coverage_basis"]),
        "quality_eligible_dates_in_feature_span": int(len(quality_counts)),
        "quality_eligible_rows_in_feature_span": int(quality_counts.sum()),
        "factor_coverage": {},
        "listing_gate_applied_before_cross_sectional_ranking": True,
    }
    for factor, direction in zip(FACTOR_NAMES, FACTOR_DIRECTIONS):
        eligibility_column = f"{factor}_eligible"
        result[eligibility_column] = (
            result[eligibility_column].astype("boolean").fillna(False).astype(bool)
        )
        values = pd.to_numeric(result[factor], errors="coerce")
        values = values.where(np.isfinite(values))
        factor_eligible = (
            in_feature_span
            & quality_eligible
            & result[eligibility_column]
            & values.notna()
        )
        eligible_counts = (
            result.loc[factor_eligible]
            .groupby("datetime", observed=True, sort=True)
            .size()
            .reindex(quality_counts.index, fill_value=0)
        )
        coverage_by_date = eligible_counts / quality_counts
        cross_section_dates = eligible_counts.index[eligible_counts.ge(minimum_names)]
        rank_eligible = factor_eligible & result["datetime"].isin(cross_section_dates)
        scores = (
            values.loc[rank_eligible]
            .groupby(result.loc[rank_eligible, "datetime"], sort=False)
            .rank(method="average", pct=True, ascending=(direction == "higher"))
        )
        result[factor] = np.nan
        result.loc[scores.index, factor] = scores.astype("float64")
        potential_indices = np.arange(
            0, max(len(eligible_counts) - hold_days, 0), hold_days
        )
        potential_cohorts = int(
            eligible_counts.iloc[potential_indices].ge(minimum_names).sum()
        )
        median_coverage = float(coverage_by_date.median())
        p05_coverage = float(coverage_by_date.quantile(0.05))
        names_p05 = float(eligible_counts.quantile(0.05))
        observed_years = sorted(
            int(year)
            for year in pd.DatetimeIndex(cross_section_dates).year.unique().tolist()
        )
        passed = bool(
            median_coverage >= minimum_median
            and p05_coverage >= minimum_p05
            and names_p05 >= minimum_names
            and potential_cohorts >= minimum_cohorts
            and len(observed_years)
            >= int(spec["historical_diagnostic"]["minimum_observed_calendar_years"])
        )
        coverage["factor_coverage"][factor] = {
            "direction": direction,
            "quality_and_factor_eligible_rows": int(factor_eligible.sum()),
            "rank_eligible_rows": int(rank_eligible.sum()),
            "rank_eligible_dates": int(len(cross_section_dates)),
            "eligible_names_per_date_min": int(eligible_counts.min()),
            "eligible_names_per_date_p05": names_p05,
            "eligible_names_per_date_median": float(eligible_counts.median()),
            "median_coverage": median_coverage,
            "p05_coverage": p05_coverage,
            "potential_non_overlapping_three_session_cohorts": potential_cohorts,
            "observed_calendar_years": observed_years,
            "coverage_gate_passed": passed,
        }
    coverage["coverage_policy"] = {
        "minimum_median_coverage": minimum_median,
        "minimum_p05_coverage": minimum_p05,
        "minimum_names_per_factor_cross_section": minimum_names,
        "minimum_potential_non_overlapping_three_session_cohorts": minimum_cohorts,
        "minimum_observed_calendar_years": int(
            spec["historical_diagnostic"]["minimum_observed_calendar_years"]
        ),
        "all_four_factors_must_pass": True,
    }
    coverage["coverage_gate_passed"] = all(
        item["coverage_gate_passed"] for item in coverage["factor_coverage"].values()
    )
    return result, coverage


def require_unconsumed(experiment_root: Path) -> None:
    marker = experiment_root / CONSUMPTION_FILENAME
    if marker.exists():
        raise CleanedMinuteResearchError(
            f"cleaned four-factor historical protocol is already consumed: {marker}"
        )
    for path in sorted(experiment_root.glob("*_factor_diagnostic.json")):
        record = research.load_json_record(path)
        if record.get("purpose") == DIAGNOSTIC_PURPOSE:
            raise CleanedMinuteResearchError(
                f"cleaned four-factor historical diagnostic already exists: {path}"
            )


def write_coverage_audit(
    experiment_root: Path,
    spec: dict[str, Any],
    coverage: dict[str, Any],
    source_evidence: dict[str, Any],
    price_basis: dict[str, Any],
) -> Path:
    run_id = research._timestamp()
    audit = {
        "run_id": run_id,
        "status": "insufficient_data_coverage",
        "purpose": "tushare_cleaned_four_factor_coverage_gate_before_forward_returns",
        "preregistration": {
            "path": str(DEFAULT_PREREGISTRATION.resolve()),
            "sha256": PREREGISTRATION_SHA256,
            "preregistered_at": spec["preregistered_at"],
        },
        "source_evidence": source_evidence,
        "data": price_basis,
        "coverage": coverage,
        "forward_return_fields_read": False,
        "selection_or_promotion_allowed": False,
    }
    path = experiment_root / f"{run_id}_tushare_cleaned_minute_coverage_audit.json"
    research._atomic_write_text(
        path,
        json.dumps(audit, ensure_ascii=False, indent=2, default=research._json_default)
        + "\n",
    )
    return path


def run_diagnostic(args: argparse.Namespace) -> dict[str, Any]:
    """Run the one authorized historical diagnostic and persist its audit trail."""

    minute_data_root = Path(args.minute_data_root).expanduser().resolve()
    provider_uri = Path(args.provider_uri).expanduser().resolve()
    fundamentals_path = Path(args.fundamentals).expanduser().resolve()
    experiment_root = Path(args.experiment_root).expanduser().resolve()
    experiment_root.mkdir(parents=True, exist_ok=True)
    require_unconsumed(experiment_root)
    spec = load_preregistration()
    repository_evidence = validate_repository_source_records(spec)
    joint, fieldwise, joint_manifest_path, overlay_path = (
        validate_external_source_manifests(spec, minute_data_root)
    )
    byte_evidence = verify_joint_partition_bytes(
        joint, joint_manifest_path, workers=args.verification_workers
    )
    fieldwise_link = spec["source_chain"]["fieldwise_clean_manifest"]
    features, feature_evidence = load_cleaned_minute_features(
        joint,
        joint_manifest_path,
        overlay_path,
        str(fieldwise_link["overlay_frame_sha256"]),
    )
    start = str(spec["historical_diagnostic"]["development_start"])
    end = str(spec["historical_diagnostic"]["development_end"])
    if (
        feature_evidence["calendar_start"] < start
        or feature_evidence["calendar_end"] > end
    ):
        raise CleanedMinuteResearchError(
            "cleaned feature dates escape the frozen development window"
        )
    print("loading accepted daily execution and quality context", flush=True)
    price_basis = research.research_price_basis_metadata(provider_uri)
    fundamentals = research.load_fundamentals(fundamentals_path)
    market = research.load_market_execution_data(
        provider_uri, start, end, args.batch_size
    )
    if pd.Timestamp(market["datetime"].max()) > pd.Timestamp(end):
        raise CleanedMinuteResearchError("daily market context exceeds development end")
    market = research.attach_quality_asof(
        market,
        fundamentals,
        max_age_days=int(spec["quarterly_quality"]["maximum_age_days"]),
    )
    del fundamentals
    gc.collect()
    quality_counts = {
        "fundamental_eligible_rows_before_listing_gate": int(
            market["fundamental_quality_eligible"].fillna(False).sum()
        ),
        "eligible_rows_after_listing_gate": int(
            market["quality_eligible"].fillna(False).sum()
        ),
        "fundamental_rows_excluded_by_listing_gate": int(
            (
                market["fundamental_quality_eligible"].fillna(False)
                & ~market["listing_seasoning_eligible"].fillna(False)
            ).sum()
        ),
    }
    market_rows = int(len(market))
    market_start = market["datetime"].min().date().isoformat()
    market_end = market["datetime"].max().date().isoformat()
    ranked, coverage = attach_factor_specific_scores(market, features, spec)
    del market, features
    gc.collect()
    source_evidence = {
        "repository_records": repository_evidence,
        "joint_clean_manifest": {
            "path": str(joint_manifest_path),
            "sha256": spec["source_chain"]["joint_clean_manifest"]["sha256"],
            "dataset_sha256": joint["dataset_sha256"],
            **byte_evidence,
        },
        "fieldwise_clean_manifest": {
            "path": str(
                minute_data_root
                / spec["source_chain"]["fieldwise_clean_manifest"][
                    "path_below_data_root"
                ]
            ),
            "sha256": fieldwise_link["sha256"],
            "overlay_path": str(overlay_path),
            "overlay_byte_sha256": fieldwise["overlay_byte_sha256"],
            "overlay_frame_sha256": fieldwise["overlay_frame_sha256"],
        },
        "materialized_features": feature_evidence,
        "forward_return_fields_read": False,
    }
    if not coverage["coverage_gate_passed"]:
        audit_path = write_coverage_audit(
            experiment_root, spec, coverage, source_evidence, price_basis
        )
        return {
            "status": "insufficient_data_coverage",
            "audit_path": str(audit_path),
            "coverage": coverage,
            "forward_return_fields_read": False,
        }

    execution_policy = research.load_prospective_execution_policy()
    holding = spec["holding_protocol"]
    research.require_prospective_execution_policy_compatibility(
        execution_policy,
        hold_days=int(holding["holding_period_trading_days"]),
        topk=int(holding["topk"]),
        open_cost=float(holding["open_cost"]),
        close_cost=float(holding["close_cost"]),
    )
    pilot_policy = research.load_pilot_execution_policy()
    marker_path = experiment_root / CONSUMPTION_FILENAME
    marker = {
        "kind": "a_share_tushare_cleaned_four_factor_historical_consumption",
        "status": "historical_forward_return_read_started",
        "started_at": research._timestamp(),
        "preregistration_path": str(DEFAULT_PREREGISTRATION.resolve()),
        "preregistration_sha256": PREREGISTRATION_SHA256,
        "joint_manifest_sha256": spec["source_chain"]["joint_clean_manifest"]["sha256"],
        "fieldwise_manifest_sha256": fieldwise_link["sha256"],
        "forward_return_fields_read": True,
        "selection_or_promotion_allowed": False,
    }
    research._atomic_write_text(
        marker_path,
        json.dumps(marker, ensure_ascii=False, indent=2) + "\n",
    )
    print(
        "coverage passed; beginning the single authorized forward-return read",
        flush=True,
    )
    forward_returns = research.forward_factor_return_frame(
        ranked, int(holding["holding_period_trading_days"])
    )
    summaries = research.summarize_factor_diagnostics(
        forward_returns,
        FACTOR_NAMES,
        hold_days=int(holding["holding_period_trading_days"]),
        topk=int(holding["topk"]),
        open_cost=float(holding["open_cost"]),
        close_cost=float(holding["close_cost"]),
    )
    del forward_returns
    gc.collect()
    summary_by_factor = {str(item["factor"]): item for item in summaries}
    summaries = [
        summary_by_factor.get(
            factor,
            research.unavailable_factor_diagnostic_summary(
                factor, int(holding["holding_period_trading_days"])
            ),
        )
        for factor in FACTOR_NAMES
    ]
    for index, summary in enumerate(summaries, start=1):
        factor = str(summary["factor"])
        print(f"simulating execution policy for factor {index}/4: {factor}", flush=True)
        summary["execution_aware_topk"] = research.simulate_prospective_execution_topk(
            ranked, factor, policy=execution_policy
        )
        summary["pilot_execution_topk"] = research.simulate_pilot_execution_topk(
            ranked,
            factor,
            execution_policy=execution_policy,
            pilot_policy=pilot_policy,
        )
        gc.collect()

    run_id = research._timestamp()
    diagnostic = {
        "run_id": run_id,
        "status": "completed",
        "purpose": DIAGNOSTIC_PURPOSE,
        "factor_catalog": list(FACTOR_NAMES),
        "factor_directions": dict(zip(FACTOR_NAMES, FACTOR_DIRECTIONS)),
        "strategy_timing": {
            "universe": holding["universe"],
            "minimum_listing_sessions": research.MIN_LISTING_SESSIONS,
            "listing_gate_applied_before_cross_sectional_ranking": True,
            "holding_period_trading_days": int(holding["holding_period_trading_days"]),
            "rebalancing": "non_overlapping_every_holding_period",
            "signal_time": "cleaned one-minute factors known after signal-session close",
            "same_session_trade_allowed": False,
            "entry": "next local trading-session open",
            "exit": "local close after holding_period_trading_days",
            "diagnostic_topk": int(holding["topk"]),
            "open_cost": float(holding["open_cost"]),
            "close_cost": float(holding["close_cost"]),
            "parameters_read_from_preregistration": True,
        },
        "quality_gate": {
            "source": str(fundamentals_path),
            "sha256": research.file_sha256(fundamentals_path),
            "effective_date": "strictly next local trading session after announcement_date",
            "max_quality_age_days": int(spec["quarterly_quality"]["maximum_age_days"]),
            **quality_counts,
        },
        "cleaned_minute_features": {
            "provider": "tushare",
            "frequency": "1m",
            "source_evidence": source_evidence,
            "coverage": coverage,
            "opening_gap_digestion_excluded": True,
            "raw_minute_rows_mutated": False,
            "daily_prices_substituted_into_minute_rows": False,
            "forward_return_fields_stored_in_feature_source": False,
            "selection_or_promotion_allowed": False,
        },
        "data": {
            "provider_uri": str(provider_uri),
            **price_basis,
            "calendar_start": market_start,
            "calendar_end": market_end,
            "development_start": start,
            "development_end": end,
            "market_rows": market_rows,
            "eligible_rows": quality_counts["eligible_rows_after_listing_gate"],
            "minimum_listing_sessions": research.MIN_LISTING_SESSIONS,
            "test_period_used_for_factor_design": False,
        },
        "prospective_execution_policy": {
            "path": str(research.DEFAULT_PROSPECTIVE_EXECUTION_POLICY),
            "sha256": research.PROSPECTIVE_EXECUTION_POLICY_SHA256,
            "frozen_at": execution_policy["frozen_at"],
            "applied_to_every_reported_factor": True,
        },
        "pilot_execution_policy": {
            "path": str(research.DEFAULT_PILOT_EXECUTION_POLICY),
            "sha256": research.PILOT_EXECUTION_POLICY_SHA256,
            "frozen_at": pilot_policy["frozen_at"],
            "applied_to_every_reported_factor": True,
            "initial_capital_cny": 200000.0,
            "buy_lot_size_shares": 100,
            "primary_slippage_rate_each_side": 0.001,
            "maximum_daily_amount_participation": 0.01,
        },
        "preregistration": {
            "path": str(DEFAULT_PREREGISTRATION.resolve()),
            "sha256": PREREGISTRATION_SHA256,
            "preregistered_at": spec["preregistered_at"],
            "factor_returns_observed_before_registration": False,
            "single_use_marker": str(marker_path),
        },
        "ranking_by_development_rank_ic": sorted(
            summaries,
            key=lambda item: (
                -math.inf
                if item.get("mean_rank_ic") is None
                else float(item["mean_rank_ic"])
            ),
            reverse=True,
        ),
        "post_diagnostic_aggregation_policy": spec[
            "post_diagnostic_aggregation_policy"
        ],
        "forward_return_fields_read": True,
        "selection_or_promotion_allowed": False,
        "limitations": [
            "This is an exploratory 2019-2025 diagnostic, not a pristine holdout and not investment advice.",
            "Only the four directions frozen before this return read were evaluated; the rejected opening factor was not reconstructed.",
            "A failed factor may not be inverted, re-windowed, or retested on this history.",
            "No same-history factor subset, weight, threshold, or aggregation search is authorized.",
            "Any dual-gate intersection of at least two factors requires a separately dated future-only paper protocol before current scoring or selection.",
            "Daily execution bars cannot reconstruct exact queue priority, partial fills, or realized market impact.",
        ],
    }
    destination = experiment_root / f"{run_id}_factor_diagnostic.json"
    research._atomic_write_text(
        destination,
        json.dumps(
            diagnostic, ensure_ascii=False, indent=2, default=research._json_default
        )
        + "\n",
    )
    marker.update(
        {
            "status": "historical_diagnostic_completed",
            "completed_at": research._timestamp(),
            "diagnostic_path": str(destination),
            "diagnostic_sha256": research.file_sha256(destination),
        }
    )
    research._atomic_write_text(
        marker_path, json.dumps(marker, ensure_ascii=False, indent=2) + "\n"
    )
    return {
        "status": "completed",
        "audit_path": str(destination),
        "consumption_marker": str(marker_path),
        "factor_count": len(summaries),
        "coverage_gate_passed": True,
        "top_factors_by_development_rank_ic": diagnostic[
            "ranking_by_development_rank_ic"
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the frozen cleaned Tushare four-factor research protocol"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    diagnose = subparsers.add_parser(
        "diagnose",
        help="validate the source chain and consume the one historical diagnostic",
    )
    diagnose.add_argument(
        "--minute-data-root",
        required=True,
        help="external root containing derived/a_share/rich/tushare minute snapshots",
    )
    diagnose.add_argument("--provider-uri", default=str(research.DEFAULT_PROVIDER_URI))
    diagnose.add_argument(
        "--fundamentals", default=str(research.DEFAULT_QUARTERLY_FUNDAMENTALS)
    )
    diagnose.add_argument(
        "--experiment-root", default=str(research.DEFAULT_EXPERIMENT_ROOT)
    )
    diagnose.add_argument("--batch-size", type=int, default=500)
    diagnose.add_argument("--verification-workers", type=int, default=8)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command != "diagnose":
        raise CleanedMinuteResearchError(f"unsupported command: {args.command}")
    result = run_diagnostic(args)
    print(
        json.dumps(result, ensure_ascii=False, indent=2, default=research._json_default)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
