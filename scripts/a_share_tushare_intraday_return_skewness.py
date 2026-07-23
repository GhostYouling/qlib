#!/usr/bin/env python3
"""Build and audit the preregistered intraday return-skewness candidate.

The candidate reads only minute identity and close from the immutable Tushare
source. It computes the population standardized third central moment of the
238 within-half adjacent log returns. The build and ordered no-return audit
never read a daily price or forward return, and terminal comparison values
load only after coverage and capacity pass.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import gc
import hashlib
import json
import math
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.dataset as pa_dataset


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_tushare_intraday_return_variance_entropy as previous  # noqa: E402


foundation = previous.foundation
research = previous.research
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREGISTRATION = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_intraday_return_skewness_no_return_preregistration.json"
)
DEFAULT_TERMINAL_RECORD = (
    REPO_ROOT / "docs" / "a_share_tushare_intraday_return_skewness_research_record.json"
)
PREREGISTRATION_SHA256 = (
    "b7d20fade0436e706cbefc9abdf909f8b9ec7e2e565516af722ebda9864a3936"
)
TERMINAL_RECORD_SHA256 = (
    "2a58052992102b08e9310e9521b946ddc0382c3d07b2fa06f9a21eef546b879b"
)
NO_RETURN_AUDIT_SHA256 = (
    "812f3c95d953218ad0e93c8eca6847127b53ca9b041e06b083f02418443dc59b"
)
MECHANISM_AUDIT_SHA256 = (
    "e87d343ff41a32ee19497767420a4a01dd4a00e902f12842d3da8824dfc416c0"
)
CURRENT_STATUS_SHA256 = (
    "730ab664a45dfa939e553966704f59cd048a790cf43d0804557d324b0c57dd3e"
)
PREVIOUS_TERMINAL_RECORD_SHA256 = previous.TERMINAL_RECORD_SHA256
RAW_MANIFEST_SHA256 = foundation.RAW_MANIFEST_SHA256
JOINT_MANIFEST_SHA256 = foundation.JOINT_MANIFEST_SHA256
RETURN_VARIANCE_ENTROPY_MANIFEST_SHA256 = previous.CANDIDATE_MANIFEST_SHA256
RETURN_VARIANCE_ENTROPY_DATASET_SHA256 = previous.CANDIDATE_DATASET_SHA256
SOURCE_RUN_ID = foundation.SOURCE_RUN_ID
OUTPUT_RUN_ID = f"{SOURCE_RUN_ID}_intraday_return_skewness_v1"
FACTOR_NAME = "intraday_return_skewness_238m"
FACTOR_FORMULA = (
    "m3 / m2^(3/2), mean_r = Sum(r_hj)/238, "
    "m2 = Sum((r_hj-mean_r)^2)/238, "
    "m3 = Sum((r_hj-mean_r)^3)/238, "
    "r_hj = log(close_hj/close_h,j-1), "
    "h in {morning,afternoon}, j=2..120"
)
COMPARISON_FACTORS = (*previous.COMPARISON_FACTORS, previous.FACTOR_NAME)
COMPARISON_DIRECTIONS = (*previous.COMPARISON_DIRECTIONS, "higher")
RAW_COLUMNS = ("datetime", "symbol", "provider", "close")
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
SOURCE_MINUTE_CODE_SET = previous.SOURCE_MINUTE_CODE_SET
CONTINUOUS_MINUTE_CODES = previous.CONTINUOUS_MINUTE_CODES
MORNING_MINUTE_CODES = previous.MORNING_MINUTE_CODES
AFTERNOON_MINUTE_CODES = previous.AFTERNOON_MINUTE_CODES

# Filled only after the no-return build creates an immutable external snapshot.
CANDIDATE_MANIFEST_SHA256 = (
    "f4ff8ec91db7e86a56113ca3dab507f19537392c26de4912095aeed9b4f8c392"
)
CANDIDATE_DATASET_SHA256 = (
    "f9bcf84e41e7607a4a7891ef3de822ff8fa602e952b0a22d73ed51fedfacd13a"
)
EXPECTED_ELIGIBLE_ROWS = 7_695_088
EXPECTED_ZERO_SECOND_MOMENT_ROWS = 29_410


class IntradayReturnSkewnessError(RuntimeError):
    """Raised when a frozen source, factor, or no-return gate is violated."""


def _repository_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    observed = foundation.file_digest(path)
    if observed != expected_sha256:
        raise IntradayReturnSkewnessError(
            f"{label} fingerprint mismatch: expected {expected_sha256}, got {observed}"
        )


def empty_output_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="string"),
            "provider": pd.Series(dtype="string"),
            FACTOR_NAME: pd.Series(dtype="float64"),
            f"{FACTOR_NAME}_eligible": pd.Series(dtype="bool"),
        }
    ).loc[:, OUTPUT_COLUMNS]


def load_preregistration(
    path: Path = DEFAULT_PREREGISTRATION,
) -> dict[str, Any]:
    """Load and enforce the protocol frozen before candidate values."""

    path = path.expanduser().resolve()
    _require_file(path, PREREGISTRATION_SHA256, "return-skewness protocol")
    spec = research.load_json_record(
        path,
        kind="a_share_tushare_intraday_return_skewness_no_return_preregistration",
    )
    previous_spec = previous.load_preregistration()
    current = spec.get("current_research_state") or {}
    chain = spec.get("source_chain") or {}
    candidate = spec.get("candidate") or {}
    grid = candidate.get("bar_grid") or {}
    validity = candidate.get("validity") or {}
    output = spec.get("derived_snapshot") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    comparisons = list(uniqueness.get("comparison_factors") or [])
    boundary = spec.get("research_boundary") or {}
    mechanism = chain.get("mechanism_overlap_reaudit") or {}
    predecessor = chain.get("prior_terminal_record") or {}
    entropy_manifest = chain.get("return_variance_entropy_comparison_manifest") or {}
    if not (
        spec.get("version") == 1
        and spec.get("status")
        == "frozen_before_candidate_factor_values_comparison_values_or_forward_returns"
        and current.get("sha256") == CURRENT_STATUS_SHA256
        and current.get("status")
        == "aggregation_blocked_after_intraday_return_variance_entropy_terminal_rejection_zero_dual_gate_factors"
        and current.get("terminal_mechanism_count_before_this_candidate") == 42
        and current.get("topk_qualified_factor_count") == 0
        and current.get("dual_gate_qualified_factor_count") == 0
        and current.get("aggregation_allowed") is False
        and spec.get("point_in_time_context")
        == previous_spec.get("point_in_time_context")
        and mechanism.get("sha256") == MECHANISM_AUDIT_SHA256
        and predecessor.get("sha256") == PREVIOUS_TERMINAL_RECORD_SHA256
        and entropy_manifest.get("sha256") == RETURN_VARIANCE_ENTROPY_MANIFEST_SHA256
        and entropy_manifest.get("dataset_sha256")
        == RETURN_VARIANCE_ENTROPY_DATASET_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("diagnostic_direction") == "higher"
        and tuple(candidate.get("source_fields_allowed") or ()) == RAW_COLUMNS
        and set(candidate.get("source_fields_forbidden") or ())
        == {
            "open",
            "high",
            "low",
            "volume",
            "amount",
            "any_daily_price",
            "any_forward_return",
        }
        and grid.get("required_full_source_rows") == 241
        and grid.get("excluded_source_bar_end") == "09:30"
        and grid.get("continuous_closes") == 240
        and grid.get("within_morning_adjacent_log_returns") == 119
        and grid.get("within_afternoon_adjacent_log_returns") == 119
        and grid.get("return_observations") == 238
        and grid.get("cross_lunch_return_included") is False
        and grid.get("standalone_09_30_row_included") is False
        and candidate.get("formula") == FACTOR_FORMULA
        and validity.get("all_240_continuous_closes_finite_and_strictly_positive")
        is True
        and validity.get("all_238_within_half_log_returns_finite") is True
        and validity.get(
            "finite_strictly_positive_population_second_centered_moment_required"
        )
        is True
        and validity.get("finite_population_third_centered_moment_required") is True
        and validity.get("finite_standardized_skewness_required") is True
        and validity.get("theoretical_range") == "unbounded_real"
        and validity.get("zero_second_centered_moment_policy") == "missing"
        and validity.get("fisher_finite_sample_bias_correction_applied") is False
        and output.get("output_run_id") == OUTPUT_RUN_ID
        and output.get("provider_request_allowed") is False
        and output.get("forward_return_fields_read") is False
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and coverage.get("holding_period_sessions") == 3
        and tuple(item.get("name") for item in comparisons) == COMPARISON_FACTORS
        and tuple(item.get("score_direction") for item in comparisons)
        == COMPARISON_DIRECTIONS
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        == 0.8
        and uniqueness.get("all_eighteen_comparisons_must_pass") is True
        and boundary.get("candidate_factor_values_observed_before_registration")
        is False
        and boundary.get(
            "terminal_factor_comparison_values_observed_for_this_candidate_before_registration"
        )
        is False
        and boundary.get("forward_return_fields_read_before_registration") is False
    ):
        raise IntradayReturnSkewnessError(
            "return-skewness protocol no longer matches its frozen definition"
        )
    return spec


def validate_repository_chain(spec: dict[str, Any]) -> dict[str, Any]:
    """Validate current append-only state while preserving its frozen fingerprint."""

    evidence = previous.validate_repository_chain(previous.load_preregistration())
    state = research.load_three_day_iteration_status()
    mechanisms = list(state.get("post_frontier_terminal_mechanisms") or [])
    summary = state.get("post_frontier_summary") or {}
    decision = state.get("decision") or {}
    predecessor_state = (
        state.get("status")
        == "aggregation_blocked_after_intraday_return_variance_entropy_terminal_rejection_zero_dual_gate_factors"
        and summary.get("terminal_mechanism_count") == 42
        and len(mechanisms) == 42
        and mechanisms[-1].get("mechanism")
        == "tushare_intraday_return_variance_entropy_238m"
    )
    terminal_state = (
        (
            state.get("status")
            == "aggregation_blocked_after_intraday_return_skewness_no_return_uniqueness_rejection_zero_dual_gate_factors"
            and summary.get("terminal_mechanism_count") == 43
            and len(mechanisms) == 43
            and mechanisms[-2].get("mechanism")
            == "tushare_intraday_return_variance_entropy_238m"
            and mechanisms[-1].get("mechanism")
            == "tushare_intraday_return_skewness_238m"
        )
        or (
            state.get("status")
            == "aggregation_blocked_after_intraday_bar_vwap_close_pressure_terminal_rejection_zero_dual_gate_factors"
            and summary.get("terminal_mechanism_count") == 44
            and len(mechanisms) == 44
            and mechanisms[-2].get("mechanism")
            == "tushare_intraday_return_skewness_238m"
            and mechanisms[-1].get("mechanism")
            == "tushare_intraday_bar_vwap_close_pressure_240m"
        )
        or (
            state.get("status")
            == "aggregation_blocked_after_intraday_price_update_share_terminal_rejection_zero_dual_gate_factors"
            and summary.get("terminal_mechanism_count") == 45
            and len(mechanisms) == 45
            and mechanisms[-2].get("mechanism")
            == "tushare_intraday_bar_vwap_close_pressure_240m"
            and mechanisms[-1].get("mechanism")
            == "tushare_intraday_price_update_share_238m"
        )
    )
    append_only_successor_state = (
        research.terminal_mechanism_is_preserved_in_append_only_status(
            state,
            mechanism="tushare_intraday_return_skewness_238m",
            terminal_ordinal=43,
        )
    )
    if not (
        (predecessor_state or terminal_state or append_only_successor_state)
        and summary.get("admitted_factor_count") == 0
        and summary.get("aggregation_candidate_count") == 0
        and decision.get("aggregation_allowed") is False
        and decision.get("current_scoring_allowed") is False
        and decision.get("selection_allowed") is False
    ):
        raise IntradayReturnSkewnessError(
            "authoritative three-day state changed after skewness preregistration"
        )
    previous_record = previous.load_terminal_record_if_present()
    if previous_record is None:
        raise IntradayReturnSkewnessError(
            "return-variance-entropy terminal record is required"
        )
    mechanism = spec["source_chain"]["mechanism_overlap_reaudit"]
    mechanism_path = _repository_path(str(mechanism["path"]))
    _require_file(mechanism_path, MECHANISM_AUDIT_SHA256, "mechanism overlap audit")
    evidence["preregistered_current_research_state"] = {
        "path": str(_repository_path(str(spec["current_research_state"]["path"]))),
        "sha256": CURRENT_STATUS_SHA256,
        "terminal_mechanism_count_before_this_candidate": 42,
        "historical_binding_not_reinterpreted_as_current_file_bytes": True,
    }
    evidence["return_variance_entropy_terminal_record"] = {
        "path": str(previous.DEFAULT_TERMINAL_RECORD.resolve()),
        "sha256": PREVIOUS_TERMINAL_RECORD_SHA256,
    }
    evidence["return_skewness_mechanism_overlap_audit"] = {
        "path": str(mechanism_path),
        "sha256": MECHANISM_AUDIT_SHA256,
    }
    return evidence


def load_terminal_record_if_present() -> dict[str, Any] | None:
    """Validate the immutable terminal record when this branch is closed."""

    if not DEFAULT_TERMINAL_RECORD.is_file():
        return None
    _require_file(
        DEFAULT_TERMINAL_RECORD,
        TERMINAL_RECORD_SHA256,
        "intraday-return-skewness research record",
    )
    record = research.load_json_record(
        DEFAULT_TERMINAL_RECORD,
        kind="a_share_tushare_intraday_return_skewness_research_record",
    )
    protocol = (record.get("ordered_protocol") or {}).get(
        "no_return_preregistration"
    ) or {}
    audit = (record.get("ordered_protocol") or {}).get("no_return_audit") or {}
    candidate = (record.get("source_chain") or {}).get("candidate_manifest") or {}
    results = record.get("no_return_results") or {}
    decision = record.get("decision") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("status") == "terminal_rejected_at_no_return_uniqueness_gate"
        and protocol.get("sha256") == PREREGISTRATION_SHA256
        and candidate.get("sha256") == CANDIDATE_MANIFEST_SHA256
        and candidate.get("dataset_sha256") == CANDIDATE_DATASET_SHA256
        and audit.get("sha256") == NO_RETURN_AUDIT_SHA256
        and audit.get("status") == "terminal_rejected_at_no_return_uniqueness_gate"
        and audit.get("daily_price_fields_loaded") == []
        and audit.get("forward_return_fields_read") is False
        and results.get("coverage_and_capacity_gate_passed") is True
        and results.get("comparison_factor_count") == 18
        and results.get("passed_comparison_factor_count") == 17
        and results.get("maximum_absolute_median_daily_rank_correlation")
        == 0.8625548973627292
        and results.get("failed_comparison_factor")
        == "intraday_upside_semivariance_share_239m"
        and results.get("all_eighteen_uniqueness_gates_passed") is False
        and decision.get("terminally_reject_exact_factor_direction") is True
        and decision.get("return_diagnostic_allowed") is False
        and decision.get("aggregation_candidate_added") is False
        and decision.get("aggregation_allowed") is False
        and decision.get("selection_allowed") is False
        and decision.get("level2_intake_justified") is False
        and boundary.get("daily_price_fields_loaded") == []
        and boundary.get("forward_return_fields_read") is False
        and boundary.get("training_or_model_fitting_performed") is False
    ):
        raise IntradayReturnSkewnessError(
            "intraday-return-skewness research record is inconsistent"
        )
    return record


def _validate_entropy_manifest(
    spec: dict[str, Any], data_root: Path
) -> tuple[dict[str, Any], Path]:
    link = (spec.get("source_chain") or {}).get(
        "return_variance_entropy_comparison_manifest"
    ) or {}
    path = (data_root / str(link.get("path_below_data_root"))).resolve()
    _require_file(
        path,
        RETURN_VARIANCE_ENTROPY_MANIFEST_SHA256,
        "return-variance-entropy comparison manifest",
    )
    manifest = research.load_json_record(
        path,
        kind="a_share_tushare_intraday_return_variance_entropy_snapshot",
    )
    quality = manifest.get("quality") or {}
    if not (
        manifest.get("status")
        == "candidate_feature_complete_pending_ordered_no_return_coverage_capacity_and_uniqueness"
        and manifest.get("factor_name") == previous.FACTOR_NAME
        and manifest.get("factor_direction") == "higher"
        and manifest.get("dataset_sha256") == RETURN_VARIANCE_ENTROPY_DATASET_SHA256
        and manifest.get("partitions") == 33_015
        and manifest.get("rows") == 7_724_498
        and manifest.get("eligible_rows") == 7_695_088
        and quality.get("zero_realized_variance_rows") == 29_410
        and quality.get("invalid_required_close_rows") == 0
        and quality.get("invalid_required_value_rows") == 0
        and quality.get("nonfinite_log_return_rows") == 0
        and quality.get("nonfinite_entropy_component_rows") == 0
        and quality.get("nonfinite_entropy_rows") == 0
        and manifest.get("source_close_read") is True
        and manifest.get("source_amount_read") is False
        and manifest.get("source_open_high_low_or_volume_read") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("forward_return_fields_read") is False
    ):
        raise IntradayReturnSkewnessError(
            "return-variance-entropy comparison manifest identity is rejected"
        )
    return manifest, path


def validate_external_chain(spec: dict[str, Any], data_root: Path) -> tuple[Any, ...]:
    chain = previous.validate_external_chain(previous.load_preregistration(), data_root)
    entropy_manifest, entropy_path = _validate_entropy_manifest(spec, data_root)
    return (*chain, entropy_manifest, entropy_path)


def compute_partition_frame(
    raw: pd.DataFrame,
    base: pd.DataFrame,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Compute population skewness of the 238 within-half log returns."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise IntradayReturnSkewnessError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    empty_quality = {
        "base_rows": 0,
        "eligible_rows": 0,
        "invalid_required_close_rows": 0,
        "invalid_required_value_rows": 0,
        "nonfinite_log_return_rows": 0,
        "zero_second_centered_moment_rows": 0,
        "nonfinite_second_centered_moment_rows": 0,
        "nonfinite_third_centered_moment_rows": 0,
        "nonfinite_standardized_skewness_rows": 0,
    }
    if missing := sorted({"trade_date", "symbol"} - set(base.columns)):
        raise IntradayReturnSkewnessError(
            "joint base partition is missing columns: " + ", ".join(missing)
        )
    if base.empty:
        return empty_output_frame(), empty_quality
    base_work = base[["trade_date", "symbol"]].copy()
    base_work["trade_date"] = pd.to_datetime(
        base_work["trade_date"], errors="coerce"
    ).dt.normalize()
    base_work["symbol"] = base_work["symbol"].astype(str).str.upper()
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(
        drop=True
    )
    if (
        base_work["trade_date"].isna().any()
        or set(base_work["symbol"]) != {symbol}
        or base_work.duplicated(["trade_date", "symbol"]).any()
    ):
        raise IntradayReturnSkewnessError(
            f"joint base identity is invalid for {symbol}"
        )
    if raw.empty:
        raise IntradayReturnSkewnessError(
            f"raw source is empty for nonempty base partition {symbol}"
        )
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["close"] = pd.to_numeric(work["close"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise IntradayReturnSkewnessError(
            f"raw identity or timestamp violation for {symbol}"
        )
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise IntradayReturnSkewnessError(
            f"every source stock-day must retain the exact 241-row grid for {symbol}"
        )
    observed_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(value) for value in values))
    if not observed_codes.eq(SOURCE_MINUTE_CODE_SET).all():
        raise IntradayReturnSkewnessError(f"source minute grid changed for {symbol}")
    continuous = work.loc[
        work["minute_code"].isin(CONTINUOUS_MINUTE_CODES),
        ["trade_date", "minute_code", "close"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"],
        categories=CONTINUOUS_MINUTE_CODES,
        ordered=True,
    )
    continuous = continuous.sort_values(["trade_date", "minute_code"])
    closes = continuous["close"].to_numpy(dtype=float).reshape(-1, 2, 120)
    required_closes_valid = np.isfinite(closes).all(axis=(1, 2)) & (closes > 0.0).all(
        axis=(1, 2)
    )
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        log_returns = np.diff(np.log(closes), axis=2).reshape(-1, 238)
        mean_return = log_returns.mean(axis=1)
        centered = log_returns - mean_return[:, None]
        second_moment = np.square(centered).mean(axis=1)
        third_moment = np.power(centered, 3).mean(axis=1)
        values = third_moment / np.power(second_moment, 1.5)
    log_returns_finite = np.isfinite(log_returns).all(axis=1)
    required_valid = required_closes_valid & log_returns_finite
    second_finite = np.isfinite(second_moment)
    second_positive = second_finite & (second_moment > 0.0)
    third_finite = np.isfinite(third_moment)
    skewness_finite = np.isfinite(values)
    eligible = required_valid & second_positive & third_finite & skewness_finite
    expected_dates = pd.Index(source_counts.index)
    if (
        not base_work["trade_date"]
        .reset_index(drop=True)
        .equals(pd.Series(expected_dates).reset_index(drop=True))
    ):
        raise IntradayReturnSkewnessError(
            f"joint-clean base dates do not match raw dates for {symbol}"
        )
    output = pd.DataFrame(
        {
            "trade_date": base_work["trade_date"],
            "symbol": symbol,
            "provider": "tushare",
            FACTOR_NAME: np.where(eligible, values, np.nan),
            f"{FACTOR_NAME}_eligible": eligible,
        }
    ).loc[:, OUTPUT_COLUMNS]
    invalid_required = ~required_closes_valid
    return output, {
        "base_rows": int(len(output)),
        "eligible_rows": int(eligible.sum()),
        "invalid_required_close_rows": int(invalid_required.sum()),
        "invalid_required_value_rows": int(invalid_required.sum()),
        "nonfinite_log_return_rows": int(
            ((~log_returns_finite) & ~invalid_required).sum()
        ),
        "zero_second_centered_moment_rows": int(
            (required_valid & second_finite & (second_moment == 0.0)).sum()
        ),
        "nonfinite_second_centered_moment_rows": int(
            (required_valid & ~second_finite).sum()
        ),
        "nonfinite_third_centered_moment_rows": int(
            (required_valid & second_positive & ~third_finite).sum()
        ),
        "nonfinite_standardized_skewness_rows": int(
            (required_valid & second_positive & third_finite & ~skewness_finite).sum()
        ),
    }


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived/a_share/rich/tushare/minute_intraday_return_skewness"
        / OUTPUT_RUN_ID
    )


def _load_checkpoint(
    raw_record: dict[str, Any],
    joint_record: dict[str, Any],
    paths: Any,
) -> tuple[dict[str, Any], Counter[str]] | None:
    if not paths.partial_sidecar.exists():
        paths.partial_data.unlink(missing_ok=True)
        return None
    record = json.loads(paths.partial_sidecar.read_text(encoding="utf-8"))
    raw_path = Path(str(raw_record["path"]))
    base_path = Path(str(joint_record["path"]))
    valid = (
        record.get("kind") == "a_share_tushare_intraday_return_skewness_partition"
        and record.get("protocol_sha256") == PREREGISTRATION_SHA256
        and record.get("raw_manifest_sha256") == RAW_MANIFEST_SHA256
        and record.get("joint_manifest_sha256") == JOINT_MANIFEST_SHA256
        and record.get("raw_source_byte_sha256") == raw_record.get("byte_sha256")
        and record.get("joint_base_byte_sha256")
        == joint_record.get("output_byte_sha256")
        and paths.partial_data.is_file()
        and foundation.file_digest(raw_path) == raw_record.get("byte_sha256")
        and foundation.file_digest(base_path) == joint_record.get("output_byte_sha256")
        and foundation.file_digest(paths.partial_data)
        == record.get("output_byte_sha256")
    )
    if not valid:
        raise IntradayReturnSkewnessError(
            f"completed return-skewness checkpoint changed: {paths.partial_sidecar}"
        )
    output = pd.read_parquet(paths.partial_data)
    if len(output) != int(record.get("rows", -1)) or foundation.frame_digest(
        output
    ) != record.get("output_frame_sha256"):
        raise IntradayReturnSkewnessError(
            f"completed return-skewness frame changed: {paths.partial_data}"
        )
    dates = Counter(
        pd.to_datetime(output.loc[output[f"{FACTOR_NAME}_eligible"], "trade_date"])
        .dt.strftime("%Y-%m-%d")
        .tolist()
    )
    return record, dates


def _process_partition(
    raw_record: dict[str, Any],
    joint_record: dict[str, Any],
    *,
    partial_root: Path,
    final_root: Path,
) -> tuple[dict[str, Any], Counter[str], bool]:
    paths = foundation.partition_paths(partial_root, final_root, joint_record)
    completed = _load_checkpoint(raw_record, joint_record, paths)
    if completed is not None:
        record, dates = completed
        return record, dates, True
    raw_path = Path(str(raw_record["path"]))
    base_path = Path(str(joint_record["path"]))
    if foundation.file_digest(raw_path) != raw_record.get("byte_sha256"):
        raise IntradayReturnSkewnessError(f"raw partition changed: {raw_path}")
    if foundation.file_digest(base_path) != joint_record.get("output_byte_sha256"):
        raise IntradayReturnSkewnessError(f"joint-base partition changed: {base_path}")
    raw = pd.read_parquet(raw_path, columns=list(RAW_COLUMNS))
    base = pd.read_parquet(base_path, columns=["trade_date", "symbol"])
    output, quality = compute_partition_frame(
        raw, base, symbol=str(joint_record["symbol"])
    )
    foundation.atomic_write_frame(output, paths.partial_data)
    record = {
        "schema_version": 1,
        "kind": "a_share_tushare_intraday_return_skewness_partition",
        "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "protocol_sha256": PREREGISTRATION_SHA256,
        "raw_manifest_sha256": RAW_MANIFEST_SHA256,
        "joint_manifest_sha256": JOINT_MANIFEST_SHA256,
        "output_run_id": OUTPUT_RUN_ID,
        "symbol": str(joint_record["symbol"]),
        "code": str(joint_record["code"]),
        "year": int(joint_record["year"]),
        "raw_source_path": str(raw_path),
        "raw_source_rows": int(raw_record["rows"]),
        "raw_source_byte_sha256": str(raw_record["byte_sha256"]),
        "joint_base_path": str(base_path),
        "joint_base_rows": int(joint_record["rows"]),
        "joint_base_byte_sha256": str(joint_record["output_byte_sha256"]),
        "path": str(paths.final_data),
        "sidecar_path": str(paths.final_sidecar),
        "rows": int(len(output)),
        "eligible_rows": int(output[f"{FACTOR_NAME}_eligible"].sum()),
        "output_byte_sha256": foundation.file_digest(paths.partial_data),
        "output_frame_sha256": foundation.frame_digest(output),
        "quality": quality,
        "source_fields_read": list(RAW_COLUMNS),
        "minute_price_fields_read": ["close"],
        "minute_amount_or_volume_fields_read": [],
        "minute_open_high_low_fields_read": [],
        "daily_price_fields_read": [],
        "comparison_factor_values_read": False,
        "forward_return_fields_read": False,
    }
    foundation.atomic_write_json(record, paths.partial_sidecar)
    dates = Counter(
        pd.to_datetime(output.loc[output[f"{FACTOR_NAME}_eligible"], "trade_date"])
        .dt.strftime("%Y-%m-%d")
        .tolist()
    )
    return record, dates, False


def _process_symbol(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    *,
    partial_root: Path,
    final_root: Path,
) -> tuple[list[dict[str, Any]], Counter[str], int]:
    records: list[dict[str, Any]] = []
    eligible_dates: Counter[str] = Counter()
    resumed = 0
    for raw_record, joint_record in sorted(
        pairs, key=lambda pair: int(pair[1]["year"])
    ):
        record, dates, was_resumed = _process_partition(
            raw_record,
            joint_record,
            partial_root=partial_root,
            final_root=final_root,
        )
        records.append(record)
        eligible_dates.update(dates)
        resumed += int(was_resumed)
    return records, eligible_dates, resumed


def _validate_snapshot_manifest(
    manifest: dict[str, Any],
    *,
    require_fingerprint_constants: bool,
) -> None:
    quality = manifest.get("quality") or {}
    if not (
        manifest.get("kind") == "a_share_tushare_intraday_return_skewness_snapshot"
        and manifest.get("status")
        == "candidate_feature_complete_pending_ordered_no_return_coverage_capacity_and_uniqueness"
        and manifest.get("protocol_sha256") == PREREGISTRATION_SHA256
        and manifest.get("raw_manifest_sha256") == RAW_MANIFEST_SHA256
        and manifest.get("joint_manifest_sha256") == JOINT_MANIFEST_SHA256
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("factor_name") == FACTOR_NAME
        and manifest.get("factor_direction") == "higher"
        and manifest.get("partitions") == 33_015
        and manifest.get("rows") == 7_724_498
        and quality.get("invalid_required_close_rows") == 0
        and quality.get("invalid_required_value_rows") == 0
        and quality.get("nonfinite_log_return_rows") == 0
        and quality.get("nonfinite_second_centered_moment_rows") == 0
        and quality.get("nonfinite_third_centered_moment_rows") == 0
        and quality.get("nonfinite_standardized_skewness_rows") == 0
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_close_read") is True
        and manifest.get("source_amount_read") is False
        and manifest.get("source_open_high_low_or_volume_read") is False
        and manifest.get("standalone_09_30_row_excluded_from_formula") is True
        and manifest.get("cross_lunch_return_included") is False
        and manifest.get("within_half_log_return_observations") == 238
        and manifest.get("population_centered_moment_orders") == [2, 3]
        and manifest.get("fisher_bias_correction_applied") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("forward_return_fields_read") is False
    ):
        raise IntradayReturnSkewnessError(
            "return-skewness snapshot identity is rejected"
        )
    if require_fingerprint_constants and not (
        CANDIDATE_MANIFEST_SHA256
        and CANDIDATE_DATASET_SHA256
        and EXPECTED_ELIGIBLE_ROWS > 0
        and EXPECTED_ZERO_SECOND_MOMENT_ROWS >= 0
        and manifest.get("dataset_sha256") == CANDIDATE_DATASET_SHA256
        and manifest.get("eligible_rows") == EXPECTED_ELIGIBLE_ROWS
        and quality.get("zero_second_centered_moment_rows")
        == EXPECTED_ZERO_SECOND_MOMENT_ROWS
    ):
        raise IntradayReturnSkewnessError(
            "candidate fingerprint and aggregate constants are not bound"
        )


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    """Build all symbol-year partitions with resumable local checkpoints."""

    if workers < 1 or workers > 8:
        raise ValueError("--workers must be between 1 and 8")
    data_root = data_root.expanduser().resolve()
    spec = load_preregistration()
    final_root = output_root(data_root)
    partial_root = final_root.parent / f".{OUTPUT_RUN_ID}.partial"
    final_manifest = final_root / "snapshot_manifest.json"
    if final_root.exists():
        if not final_manifest.is_file():
            raise IntradayReturnSkewnessError(
                f"published return-skewness root has no manifest: {final_root}"
            )
        if not CANDIDATE_MANIFEST_SHA256:
            raise IntradayReturnSkewnessError(
                "bind the published candidate manifest before reusing it"
            )
        _require_file(
            final_manifest,
            CANDIDATE_MANIFEST_SHA256,
            "published return-skewness manifest",
        )
        load_terminal_record_if_present()
        manifest = research.load_json_record(final_manifest)
        _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
        return final_manifest
    repository_evidence = validate_repository_chain(spec)
    chain = validate_external_chain(spec, data_root)
    raw, joint, raw_manifest_path, joint_manifest_path = chain[:4]
    if shutil.disk_usage(data_root).free < 5 * 1024**3:
        raise IntradayReturnSkewnessError("external data root has less than 5 GiB free")
    raw_records = list(raw.get("files") or [])
    joint_records = list(joint.get("files") or [])
    raw_by_key = {
        (str(item["symbol"]), int(item["year"])): item for item in raw_records
    }
    joint_by_key = {
        (str(item["symbol"]), int(item["year"])): item for item in joint_records
    }
    if (
        len(raw_by_key) != 33_015
        or len(joint_by_key) != 33_015
        or set(raw_by_key) != set(joint_by_key)
    ):
        raise IntradayReturnSkewnessError(
            "raw and joint-clean partition identities do not match exactly"
        )
    by_symbol: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for key in sorted(joint_by_key):
        raw_record = raw_by_key[key]
        joint_record = joint_by_key[key]
        if (
            joint_record.get("source_byte_sha256") != raw_record.get("byte_sha256")
            or Path(str(joint_record.get("source_path"))).resolve()
            != Path(str(raw_record.get("path"))).resolve()
        ):
            raise IntradayReturnSkewnessError(
                f"joint-clean raw source binding changed for {key[0]}/{key[1]}"
            )
        by_symbol.setdefault(key[0], []).append((raw_record, joint_record))
    lock_path = data_root / ".a_share_tushare_intraday_return_skewness.lock"
    with foundation.ProcessLock(lock_path):
        partial_root.mkdir(parents=True, exist_ok=True)
        all_records: list[dict[str, Any]] = []
        eligible_dates: Counter[str] = Counter()
        resumed = 0
        completed_symbols = 0
        print(
            f"building {len(joint_records):,} return-skewness partitions "
            f"across {len(by_symbol):,} symbols with {workers} workers",
            flush=True,
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    _process_symbol,
                    pairs,
                    partial_root=partial_root,
                    final_root=final_root,
                ): symbol
                for symbol, pairs in sorted(by_symbol.items())
            }
            try:
                for future in concurrent.futures.as_completed(futures):
                    futures.pop(future)
                    records, dates, resumed_count = future.result()
                    all_records.extend(records)
                    eligible_dates.update(dates)
                    resumed += resumed_count
                    completed_symbols += 1
                    if completed_symbols % 25 == 0 or completed_symbols == len(
                        by_symbol
                    ):
                        print(
                            f"progress symbols={completed_symbols:,}/{len(by_symbol):,} "
                            f"partitions={len(all_records):,}/{len(joint_records):,} "
                            f"eligible_rows={sum(eligible_dates.values()):,} "
                            f"resumed={resumed:,}",
                            flush=True,
                        )
            except BaseException:
                for future in futures:
                    future.cancel()
                raise
        if len(all_records) != 33_015:
            raise IntradayReturnSkewnessError(
                "not every source partition produced a return-skewness checkpoint"
            )
        _require_file(raw_manifest_path, RAW_MANIFEST_SHA256, "raw minute manifest")
        _require_file(
            joint_manifest_path, JOINT_MANIFEST_SHA256, "joint-clean manifest"
        )
        all_records.sort(key=lambda item: (str(item["symbol"]), int(item["year"])))
        quality = foundation._aggregate_quality(all_records)
        dataset_payload = "\n".join(
            f"{item['symbol']}|{item['year']}|{item['output_byte_sha256']}"
            for item in all_records
        ).encode("utf-8")
        manifest = {
            "schema_version": 1,
            "kind": "a_share_tushare_intraday_return_skewness_snapshot",
            "status": "candidate_feature_complete_pending_ordered_no_return_coverage_capacity_and_uniqueness",
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "output_run_id": OUTPUT_RUN_ID,
            "protocol_path": str(DEFAULT_PREREGISTRATION.resolve()),
            "protocol_sha256": PREREGISTRATION_SHA256,
            "raw_manifest_path": str(raw_manifest_path),
            "raw_manifest_sha256": RAW_MANIFEST_SHA256,
            "joint_manifest_path": str(joint_manifest_path),
            "joint_manifest_sha256": JOINT_MANIFEST_SHA256,
            "dataset_sha256": hashlib.sha256(dataset_payload).hexdigest(),
            "factor_name": FACTOR_NAME,
            "factor_direction": "higher",
            "files": all_records,
            "partitions": len(all_records),
            "rows": int(quality.get("base_rows", -1)),
            "eligible_rows": int(quality.get("eligible_rows", -1)),
            "quality": quality,
            "eligible_names_by_date": dict(sorted(eligible_dates.items())),
            "source_fields_read": list(RAW_COLUMNS),
            "source_close_read": True,
            "source_amount_read": False,
            "source_open_high_low_or_volume_read": False,
            "standalone_09_30_row_excluded_from_formula": True,
            "cross_lunch_return_included": False,
            "within_half_log_return_observations": 238,
            "population_centered_moment_orders": [2, 3],
            "fisher_bias_correction_applied": False,
            "daily_price_fields_read": [],
            "comparison_factor_values_read": False,
            "forward_return_fields_read": False,
            "training_or_model_fitting_performed": False,
            "aggregation_scoring_selection_sizing_or_orders_performed": False,
            "promotion_allowed": False,
            "resumed_partitions": resumed,
            "repository_evidence": repository_evidence,
        }
        _validate_snapshot_manifest(manifest, require_fingerprint_constants=False)
        foundation.atomic_write_json(manifest, partial_root / "snapshot_manifest.json")
        final_root.parent.mkdir(parents=True, exist_ok=True)
        partial_root.replace(final_root)
        return final_manifest


def verify_snapshot_files(
    manifest: dict[str, Any],
    manifest_path: Path,
    workers: int,
) -> dict[str, int]:
    records = list(manifest.get("files") or [])
    if len(records) != 33_015:
        raise IntradayReturnSkewnessError("candidate snapshot partition count changed")
    partition_root = (manifest_path.parent / "partitions").resolve()

    def verify(record: dict[str, Any]) -> tuple[int, int, int]:
        path = Path(str(record["path"])).resolve()
        try:
            path.relative_to(partition_root)
        except ValueError as exc:
            raise IntradayReturnSkewnessError(
                f"candidate partition escapes its frozen root: {path}"
            ) from exc
        _require_file(path, str(record["output_byte_sha256"]), "candidate partition")
        _require_file(
            Path(str(record["raw_source_path"])),
            str(record["raw_source_byte_sha256"]),
            "raw source partition",
        )
        _require_file(
            Path(str(record["joint_base_path"])),
            str(record["joint_base_byte_sha256"]),
            "joint-base partition",
        )
        return (
            int(record["rows"]),
            int(record["eligible_rows"]),
            path.stat().st_size,
        )

    rows = eligible = byte_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for index, result in enumerate(pool.map(verify, records), start=1):
            partition_rows, partition_eligible, partition_bytes = result
            rows += partition_rows
            eligible += partition_eligible
            byte_count += partition_bytes
            if index % 5000 == 0 or index == len(records):
                print(
                    f"verified candidate partitions {index}/{len(records)}",
                    flush=True,
                )
    if rows != manifest.get("rows") or eligible != manifest.get("eligible_rows"):
        raise IntradayReturnSkewnessError("candidate snapshot aggregate counts changed")
    return {
        "partitions_verified": len(records),
        "rows_verified": rows,
        "eligible_rows_verified": eligible,
        "partition_bytes_verified": byte_count,
    }


def load_candidate_frame(manifest_path: Path, manifest: dict[str, Any]) -> pd.DataFrame:
    dataset = pa_dataset.dataset(
        str(manifest_path.parent / "partitions"), format="parquet"
    )
    table = dataset.to_table(columns=list(OUTPUT_COLUMNS), use_threads=True)
    frame = table.to_pandas(split_blocks=True, self_destruct=True)
    del table, dataset
    gc.collect()
    if len(frame) != int(manifest.get("rows", -1)):
        raise IntradayReturnSkewnessError("candidate frame row count changed")
    frame["trade_date"] = pd.to_datetime(
        frame["trade_date"], errors="coerce"
    ).dt.normalize()
    frame["symbol"] = frame["symbol"].astype(str).str.upper()
    frame[f"{FACTOR_NAME}_eligible"] = (
        frame[f"{FACTOR_NAME}_eligible"].astype("boolean").fillna(False).astype(bool)
    )
    frame[FACTOR_NAME] = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"]
    if (
        frame["trade_date"].isna().any()
        or frame.duplicated(["trade_date", "symbol"]).any()
        or not np.isfinite(frame.loc[eligible, FACTOR_NAME].to_numpy(dtype=float)).all()
        or frame.loc[~eligible, FACTOR_NAME].notna().any()
    ):
        raise IntradayReturnSkewnessError("candidate frame values or keys are invalid")
    frame["symbol"] = frame["symbol"].astype("category")
    return frame


def coverage_and_capacity(
    candidate: pd.DataFrame,
    eligible_keys: pd.DataFrame,
    spec: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    previous_name = previous.FACTOR_NAME
    previous.FACTOR_NAME = FACTOR_NAME
    try:
        return previous.coverage_and_capacity(candidate, eligible_keys, spec)
    finally:
        previous.FACTOR_NAME = previous_name


def _daily_directional_rank_correlations(
    frame: pd.DataFrame,
    comparison: str,
    direction: str,
    minimum_names: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for trade_date, group in frame[["trade_date", FACTOR_NAME, comparison]].groupby(
        "trade_date", observed=True, sort=True
    ):
        pair = group[[FACTOR_NAME, comparison]].apply(pd.to_numeric, errors="coerce")
        pair = pair.replace([np.inf, -np.inf], np.nan).dropna()
        if len(pair) < minimum_names or pair.nunique().min() < 2:
            continue
        candidate_score = pair[FACTOR_NAME].rank(method="average", pct=True)
        comparison_score = pair[comparison].rank(
            method="average",
            pct=True,
            ascending=(direction == "higher"),
        )
        correlation = candidate_score.corr(comparison_score, method="pearson")
        if math.isfinite(float(correlation)):
            rows.append(
                {
                    "trade_date": pd.Timestamp(trade_date),
                    "pairwise_names": int(len(pair)),
                    "rank_correlation": float(correlation),
                }
            )
    return pd.DataFrame(rows)


def _one_comparison_result(
    candidate_quality: pd.DataFrame,
    comparison_frame: pd.DataFrame,
    comparison: str,
    direction: str,
    gate: dict[str, Any],
) -> dict[str, Any]:
    comparison_frame = comparison_frame.copy()
    comparison_frame["symbol"] = comparison_frame["symbol"].astype(str)
    candidate = candidate_quality.copy()
    candidate["symbol"] = candidate["symbol"].astype(str)
    merged = candidate.merge(
        comparison_frame,
        on=["trade_date", "symbol"],
        how="left",
        validate="one_to_one",
    )
    daily = _daily_directional_rank_correlations(
        merged,
        comparison,
        direction,
        int(gate["minimum_pairwise_names_per_session"]),
    )
    sessions = int(len(daily))
    median = float(daily["rank_correlation"].median()) if sessions else math.nan
    passed = bool(
        sessions >= int(gate["minimum_pairwise_sessions_per_comparison"])
        and math.isfinite(median)
        and abs(median)
        < float(gate["maximum_allowed_absolute_median_daily_rank_correlation"])
    )
    return {
        "comparison_factor": comparison,
        "score_direction": direction,
        "pairwise_sessions": sessions,
        "minimum_pairwise_names_observed": (
            int(daily["pairwise_names"].min()) if sessions else 0
        ),
        "median_daily_rank_correlation": (median if math.isfinite(median) else None),
        "absolute_median_daily_rank_correlation": (
            abs(median) if math.isfinite(median) else None
        ),
        "daily_rank_correlation_p05": (
            float(daily["rank_correlation"].quantile(0.05)) if sessions else None
        ),
        "daily_rank_correlation_p95": (
            float(daily["rank_correlation"].quantile(0.95)) if sessions else None
        ),
        "daily_correlation_frame_sha256": (
            research.dataframe_content_sha256(daily) if sessions else None
        ),
        "gate_passed": passed,
    }


def uniqueness_audit(
    candidate_quality: pd.DataFrame,
    chain: tuple[Any, ...],
    spec: dict[str, Any],
    workers: int,
) -> dict[str, Any]:
    (
        _,
        _,
        _,
        joint_manifest_path,
        efficiency_manifest,
        efficiency_manifest_path,
        recovery_manifest,
        recovery_manifest_path,
        amount_entropy_manifest,
        amount_entropy_manifest_path,
        profile_manifest,
        profile_manifest_path,
        upside_manifest,
        upside_manifest_path,
        terminal_manifest,
        terminal_manifest_path,
        sign_run_manifest,
        sign_run_manifest_path,
        volatility_manifest,
        volatility_manifest_path,
        amount_lead_manifest,
        amount_lead_manifest_path,
        amount_center_manifest,
        amount_center_manifest_path,
        up_move_manifest,
        up_move_manifest_path,
        diffusive_manifest,
        diffusive_manifest_path,
        coupling_manifest,
        coupling_manifest_path,
        entropy_manifest,
        entropy_manifest_path,
    ) = chain
    print(
        "coverage passed; loading eighteen terminal comparison factors",
        flush=True,
    )
    previous_name = previous.FACTOR_NAME
    previous.FACTOR_NAME = FACTOR_NAME
    try:
        first_seventeen = previous.uniqueness_audit(
            candidate_quality,
            joint_manifest_path,
            efficiency_manifest,
            efficiency_manifest_path,
            recovery_manifest,
            recovery_manifest_path,
            amount_entropy_manifest,
            amount_entropy_manifest_path,
            profile_manifest,
            profile_manifest_path,
            upside_manifest,
            upside_manifest_path,
            terminal_manifest,
            terminal_manifest_path,
            sign_run_manifest,
            sign_run_manifest_path,
            volatility_manifest,
            volatility_manifest_path,
            amount_lead_manifest,
            amount_lead_manifest_path,
            amount_center_manifest,
            amount_center_manifest_path,
            up_move_manifest,
            up_move_manifest_path,
            diffusive_manifest,
            diffusive_manifest_path,
            coupling_manifest,
            coupling_manifest_path,
            spec,
            workers,
        )
    finally:
        previous.FACTOR_NAME = previous_name
    entropy_verification = previous.verify_snapshot_files(
        entropy_manifest, entropy_manifest_path, workers
    )
    entropy_frame = previous.load_candidate_frame(
        entropy_manifest_path, entropy_manifest
    )[["trade_date", "symbol", previous.FACTOR_NAME]]
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    entropy_result = _one_comparison_result(
        candidate_quality,
        entropy_frame,
        previous.FACTOR_NAME,
        "higher",
        gate,
    )
    results = [
        *list(first_seventeen.get("comparisons") or []),
        entropy_result,
    ]
    observed = [
        item["absolute_median_daily_rank_correlation"]
        for item in results
        if item["absolute_median_daily_rank_correlation"] is not None
    ]
    verifications = dict(
        first_seventeen.get("prior_candidate_snapshot_file_verification") or {}
    )
    verifications["return_variance_entropy"] = entropy_verification
    return {
        "comparison_values_loaded_after_coverage_pass": True,
        "comparison_field_count": len(results),
        "prior_candidate_snapshot_file_verification": verifications,
        "minimum_pairwise_names_per_session": int(
            gate["minimum_pairwise_names_per_session"]
        ),
        "minimum_pairwise_sessions_per_comparison": int(
            gate["minimum_pairwise_sessions_per_comparison"]
        ),
        "maximum_allowed_absolute_median_daily_rank_correlation": float(
            gate["maximum_allowed_absolute_median_daily_rank_correlation"]
        ),
        "comparisons": results,
        "maximum_observed_absolute_median_daily_rank_correlation": (
            max(observed) if observed else None
        ),
        "base_seventeen_comparisons_passed": bool(
            first_seventeen.get("all_seventeen_comparisons_passed")
        ),
        "all_eighteen_comparisons_passed": bool(
            len(results) == 18 and all(item["gate_passed"] for item in results)
        ),
    }


def _find_existing_audit(experiment_root: Path, manifest_sha256: str) -> Path | None:
    for path in sorted(
        experiment_root.glob("*_intraday_return_skewness_no_return_audit.json")
    ):
        record = research.load_json_record(path)
        if (
            record.get("kind")
            == "a_share_tushare_intraday_return_skewness_no_return_audit"
            and (record.get("candidate_snapshot") or {}).get("sha256")
            == manifest_sha256
        ):
            return path
    return None


def run_no_return_audit(
    *,
    data_root: Path,
    experiment_root: Path,
    workers: int,
) -> Path:
    """Run coverage/capacity before loading the eighteen comparison values."""

    if not CANDIDATE_MANIFEST_SHA256:
        raise IntradayReturnSkewnessError(
            "candidate snapshot fingerprint must be bound before audit"
        )
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_preregistration()
    terminal_record = load_terminal_record_if_present()
    if terminal_record is not None:
        manifest_path = output_root(data_root) / "snapshot_manifest.json"
        _require_file(
            manifest_path,
            CANDIDATE_MANIFEST_SHA256,
            "terminal candidate snapshot manifest",
        )
        audit_link = (terminal_record.get("ordered_protocol") or {}).get(
            "no_return_audit"
        ) or {}
        audit_path = _repository_path(str(audit_link.get("path", "")))
        _require_file(
            audit_path,
            NO_RETURN_AUDIT_SHA256,
            "terminal no-return audit",
        )
        audit = research.load_json_record(
            audit_path,
            kind="a_share_tushare_intraday_return_skewness_no_return_audit",
        )
        if not (
            audit.get("status") == "terminal_rejected_at_no_return_uniqueness_gate"
            and (audit.get("candidate_snapshot") or {}).get("sha256")
            == CANDIDATE_MANIFEST_SHA256
            and (audit.get("coverage_and_capacity") or {}).get(
                "gate_passed_before_comparison_values"
            )
            is True
            and (audit.get("uniqueness") or {}).get("all_eighteen_comparisons_passed")
            is False
            and (audit.get("decision") or {}).get(
                "separate_return_diagnostic_preregistration_allowed"
            )
            is False
            and audit.get("daily_price_fields_loaded") == []
            and audit.get("forward_return_fields_read") is False
        ):
            raise IntradayReturnSkewnessError(
                "terminal no-return audit is inconsistent"
            )
        return audit_path
    repository_evidence = validate_repository_chain(spec)
    chain = validate_external_chain(spec, data_root)
    joint = chain[1]
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    _require_file(
        manifest_path,
        CANDIDATE_MANIFEST_SHA256,
        "return-skewness candidate manifest",
    )
    manifest = research.load_json_record(manifest_path)
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    manifest_sha256 = foundation.file_digest(manifest_path)
    existing = _find_existing_audit(experiment_root, manifest_sha256)
    if existing is not None:
        return existing
    verification = verify_snapshot_files(manifest, manifest_path, workers)
    candidate = load_candidate_frame(manifest_path, manifest)
    print("building no-price quality/listing eligibility", flush=True)
    eligible_keys = foundation.quality_listing_eligible_keys(spec)
    candidate_quality, coverage = coverage_and_capacity(candidate, eligible_keys, spec)
    del candidate, eligible_keys
    gc.collect()
    uniqueness: dict[str, Any] = {
        "comparison_values_loaded_after_coverage_pass": False,
        "all_eighteen_comparisons_passed": False,
        "comparisons": [],
    }
    if coverage["gate_passed_before_comparison_values"]:
        uniqueness = uniqueness_audit(candidate_quality, chain, spec, workers)
    del candidate_quality
    gc.collect()
    passed = bool(
        coverage["gate_passed_before_comparison_values"]
        and uniqueness["all_eighteen_comparisons_passed"]
    )
    status = (
        "passed_no_return_coverage_capacity_and_uniqueness_pending_separate_return_diagnostic_preregistration"
        if passed
        else (
            "terminal_rejected_at_no_return_uniqueness_gate"
            if coverage["gate_passed_before_comparison_values"]
            else "terminal_rejected_at_no_return_coverage_or_capacity_gate"
        )
    )
    audit = {
        "schema_version": 1,
        "kind": "a_share_tushare_intraday_return_skewness_no_return_audit",
        "status": status,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "purpose": "ordered_candidate_coverage_capacity_then_eighteen_terminal_factor_uniqueness_without_daily_prices_or_forward_returns",
        "preregistration": {
            "path": str(DEFAULT_PREREGISTRATION.resolve()),
            "sha256": PREREGISTRATION_SHA256,
            "preregistered_at": spec["preregistered_at"],
        },
        "candidate_snapshot": {
            "path": str(manifest_path),
            "sha256": manifest_sha256,
            "dataset_sha256": str(manifest["dataset_sha256"]),
            "rows": int(manifest["rows"]),
            "eligible_rows": int(manifest["eligible_rows"]),
        },
        "source_chain": {
            "raw_manifest_sha256": RAW_MANIFEST_SHA256,
            "joint_manifest_sha256": JOINT_MANIFEST_SHA256,
            "joint_dataset_sha256": str(joint["dataset_sha256"]),
            "return_variance_entropy_manifest_sha256": RETURN_VARIANCE_ENTROPY_MANIFEST_SHA256,
            "repository_evidence": repository_evidence,
            "snapshot_file_verification": verification,
        },
        "candidate": {
            "name": FACTOR_NAME,
            "direction": "higher",
            "formula": spec["candidate"]["formula"],
        },
        "coverage_and_capacity": coverage,
        "uniqueness": uniqueness,
        "decision": {
            "all_no_return_gates_passed": passed,
            "separate_return_diagnostic_preregistration_allowed": passed,
            "return_diagnostic_authorized_without_separate_preregistration": False,
            "aggregation_allowed": False,
            "current_scoring_allowed": False,
            "selection_allowed": False,
            "sizing_or_orders_allowed": False,
            "level2_intake_justified": False,
        },
        "source_fields_loaded": list(RAW_COLUMNS),
        "minute_price_fields_loaded": ["close"],
        "minute_amount_or_volume_fields_loaded": [],
        "minute_open_high_low_fields_loaded": [],
        "comparison_fields_loaded": (
            list(COMPARISON_FACTORS)
            if uniqueness["comparison_values_loaded_after_coverage_pass"]
            else []
        ),
        "daily_price_fields_loaded": [],
        "forward_return_fields_read": False,
        "training_or_model_fitting_performed": False,
        "investment_advice": False,
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = experiment_root / f"{run_id}_intraday_return_skewness_no_return_audit.json"
    foundation.atomic_write_json(audit, path)
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser(
        "build", help="Build the external candidate snapshot"
    )
    build_parser.add_argument("--data-root", type=Path, required=True)
    build_parser.add_argument("--workers", type=int, default=4)
    audit_parser = subparsers.add_parser(
        "audit",
        help="Run ordered coverage/capacity and uniqueness without returns",
    )
    audit_parser.add_argument("--data-root", type=Path, required=True)
    audit_parser.add_argument(
        "--experiment-root",
        type=Path,
        default=REPO_ROOT / "data/experiments/short_horizon",
    )
    audit_parser.add_argument("--workers", type=int, default=8)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "build":
        path = build_snapshot(data_root=args.data_root, workers=args.workers)
    else:
        path = run_no_return_audit(
            data_root=args.data_root,
            experiment_root=args.experiment_root,
            workers=args.workers,
        )
    print(json.dumps({"status": "ok", "path": str(path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
