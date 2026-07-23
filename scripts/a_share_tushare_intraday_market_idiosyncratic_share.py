#!/usr/bin/env python3
"""Build and no-return audit the preregistered market-idiosyncratic share.

The candidate uses only the immutable Tushare minute identity and close fields.
It first constructs an equal-weight same-minute market-return accumulator from
the exact joint-clean stock-day pool.  It then removes each stock from that
accumulator and computes ``1 - correlation(stock, market_without_stock) ** 2``
over the 238 within-half minute returns.  Coverage and capacity are evaluated
before any comparison values are loaded.  This module never reads daily prices
or forward returns.
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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd
import pyarrow.dataset as pa_dataset


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_tushare_intraday_price_update_share as previous  # noqa: E402


foundation = previous.foundation
research = previous.research
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREGISTRATION = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_intraday_market_idiosyncratic_share_no_return_preregistration.json"
)
PREREGISTRATION_SHA256 = (
    "6f1f4108cd54357e94e44cee8793e917a2bc627af9da885af6d2b50b76c4078a"
)
DEFAULT_DIAGNOSTIC_PREREGISTRATION = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_intraday_market_idiosyncratic_share_diagnostic_preregistration.json"
)
DIAGNOSTIC_PREREGISTRATION_SHA256 = (
    "06101c155c81b9fb6128327db25da9b078bfcd045f160fce2e56f2ece0020b75"
)
DEFAULT_NO_RETURN_AUDIT_INFRASTRUCTURE_REPAIR = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_intraday_market_idiosyncratic_share_no_return_audit_infrastructure_repair.json"
)
NO_RETURN_AUDIT_INFRASTRUCTURE_REPAIR_SHA256 = (
    "d4c31cff26b1fc44eabac83480101388d2414a4c8022343e4578e949239a2c93"
)
DEFAULT_TERMINAL_RECORD = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_intraday_market_idiosyncratic_share_research_record.json"
)
TERMINAL_RECORD_SHA256 = (
    "cb6829903b5cc4254bb1965e9308fdff5902ce420467a3a552a5484091a22b61"
)
DIAGNOSTIC_SHA256 = "78659065220f61db5119c0091383be0f4ff984f8ece2c6f7687f3e1e2b228a5b"
STABILITY_AUDIT_SHA256 = (
    "748f5f14e5b4f0c4ca8c1b5d0de263c6bbc0c7ce043106ad8f52d5cc1adcecff"
)
TOPK_AUDIT_SHA256 = "7e3726a2a6890327dca3fc1bab68f6f2c4552492d266c2a81ed4ce3fc6cdc701"
CONSUMPTION_MARKER_SHA256 = (
    "5ea43c65a6200608413a33792d7a54fd1f20d9b61018ba73225d8d3fa285bafd"
)
DEFAULT_MECHANISM_AUDIT = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_intraday_market_idiosyncratic_share_mechanism_overlap_reaudit_20260723.json"
)
MECHANISM_AUDIT_SHA256 = (
    "ae446992ad28bc867e33e8210bf5129fae9ba5a0d55de184ae68b72aa5fbd10b"
)
DEFAULT_CURRENT_STATUS = (
    REPO_ROOT / "docs" / "a_share_three_day_iteration_status_20260721.json"
)
CURRENT_STATUS_SHA256 = (
    "3b4cf44a5ab13ae88c69651f4607cda14c9eb469575d40adea69257d9e146ab9"
)
TERMINAL_CURRENT_STATUS_SHA256 = (
    "14e8edaf98c7f94a10f0c63e64d8af1d6e3bb1b45dac3c3bb9aabdf2cb83e2b1"
)
PREVIOUS_TERMINAL_RECORD_SHA256 = previous.TERMINAL_RECORD_SHA256
PREVIOUS_MANIFEST_SHA256 = previous.CANDIDATE_MANIFEST_SHA256
PREVIOUS_DATASET_SHA256 = previous.CANDIDATE_DATASET_SHA256
RAW_MANIFEST_SHA256 = foundation.RAW_MANIFEST_SHA256
JOINT_MANIFEST_SHA256 = foundation.JOINT_MANIFEST_SHA256
SOURCE_RUN_ID = foundation.SOURCE_RUN_ID
OUTPUT_RUN_ID = f"{SOURCE_RUN_ID}_intraday_market_idiosyncratic_share_v1"
FACTOR_NAME = "intraday_market_idiosyncratic_share_238m"
FACTOR_FORMULA = (
    "1 - Corr(r_i,t, mean(r_j,t for all valid j != i))^2 over the 238 "
    "within-half one-minute log returns"
)
DIAGNOSTIC_PURPOSE = (
    "single_preregistered_intraday_market_idiosyncratic_share_"
    "three_session_diagnostic"
)
CONSUMPTION_FILENAME = (
    "intraday_market_idiosyncratic_share_238m_historical_consumption.json"
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
BENCHMARK_COLUMNS = (
    "trade_date",
    "return_position",
    "return_sum",
    "valid_stock_count",
)
BENCHMARK_FILENAME = "market_benchmark_238m.parquet"
SOURCE_MINUTE_CODE_SET = previous.SOURCE_MINUTE_CODE_SET
CONTINUOUS_MINUTE_CODES = previous.CONTINUOUS_MINUTE_CODES
RETURN_POSITIONS = 238
MINIMUM_LEAVE_ONE_OUT_PEERS = 50
ENDPOINT_TOLERANCE = 1e-12

# Bound after the first deterministic no-return build published the snapshot.
CANDIDATE_MANIFEST_SHA256 = (
    "954b71d571bcd89cbf4eae4eedad014091a9b40e6b2b083e0071cbf870634ef0"
)
CANDIDATE_DATASET_SHA256 = (
    "e30578d063c16bafc77873e8d061d8b3985c4d3b9beb8a5994514db292f8c430"
)
EXPECTED_ELIGIBLE_ROWS = 7_695_088
EXPECTED_INVALID_REQUIRED_CLOSE_ROWS = 0
EXPECTED_INSUFFICIENT_PEER_ROWS = 0
EXPECTED_CONSTANT_STOCK_RETURN_ROWS = 29_410
EXPECTED_CONSTANT_MARKET_RETURN_ROWS = 0
NO_RETURN_AUDIT_SHA256 = (
    "44e9a2279aebc55d265378aa8bf4dad4a562cc4c2438973925c638b89ec0b34b"
)


class IntradayMarketIdiosyncraticShareError(RuntimeError):
    """Raised when a frozen source, factor, or no-return gate is violated."""


@dataclass(frozen=True)
class MarketBenchmark:
    """Dense same-date, same-position return sums and valid-stock counts."""

    dates: pd.DatetimeIndex
    return_sums: np.ndarray
    valid_stock_counts: np.ndarray
    date_to_index: dict[pd.Timestamp, int]
    frame_sha256: str


def _repository_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    observed = foundation.file_digest(path)
    if observed != expected_sha256:
        raise IntradayMarketIdiosyncraticShareError(
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
    _require_file(path, PREREGISTRATION_SHA256, "market-idiosyncratic protocol")
    spec = research.load_json_record(
        path,
        kind=(
            "a_share_tushare_intraday_market_idiosyncratic_share_"
            "no_return_preregistration"
        ),
    )
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
    prior_manifest = chain.get("price_update_share_comparison_manifest") or {}
    forbidden = {
        "open",
        "high",
        "low",
        "volume",
        "amount",
        "index_price",
        "industry_or_board_label",
        "market_cap_or_weight",
        "any_daily_price",
        "any_forward_return",
    }
    if not (
        spec.get("version") == 1
        and spec.get("status")
        == "frozen_before_candidate_factor_values_comparison_values_or_forward_returns"
        and current.get("sha256") == CURRENT_STATUS_SHA256
        and current.get("status")
        == "aggregation_blocked_after_intraday_price_update_share_terminal_rejection_zero_dual_gate_factors"
        and current.get("terminal_mechanism_count_before_this_candidate") == 45
        and current.get("topk_qualified_factor_count") == 0
        and current.get("dual_gate_qualified_factor_count") == 0
        and current.get("aggregation_allowed") is False
        and mechanism.get("sha256") == MECHANISM_AUDIT_SHA256
        and predecessor.get("sha256") == PREVIOUS_TERMINAL_RECORD_SHA256
        and prior_manifest.get("sha256") == PREVIOUS_MANIFEST_SHA256
        and prior_manifest.get("dataset_sha256") == PREVIOUS_DATASET_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("diagnostic_direction") == "higher"
        and tuple(candidate.get("source_fields_allowed") or ()) == RAW_COLUMNS
        and set(candidate.get("source_fields_forbidden") or ()) == forbidden
        and grid.get("required_full_source_rows") == 241
        and grid.get("closes_per_half") == 120
        and grid.get("within_half_adjacent_returns_per_half") == 119
        and grid.get("total_within_half_adjacent_returns") == RETURN_POSITIONS
        and grid.get("lunch_boundary_included") is False
        and grid.get("standalone_09_30_row_included") is False
        and candidate.get("formula") == FACTOR_FORMULA
        and validity.get("all_240_selected_closes_finite_and_strictly_positive") is True
        and validity.get("all_238_stock_returns_finite") is True
        and validity.get("minimum_leave_one_out_peers_at_every_position")
        == MINIMUM_LEAVE_ONE_OUT_PEERS
        and validity.get("ordinary_pearson_with_intercept") is True
        and validity.get("constant_stock_return_vector_policy") == "missing"
        and validity.get("constant_leave_one_out_market_vector_policy") == "missing"
        and validity.get("allowed_closed_interval") == [0, 1]
        and validity.get("endpoint_canonicalization_tolerance") == ENDPOINT_TOLERANCE
        and output.get("output_run_id") == OUTPUT_RUN_ID
        and output.get("market_benchmark_artifact") == BENCHMARK_FILENAME
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
        and uniqueness.get("all_twenty_one_comparisons_must_pass") is True
        and boundary.get("candidate_factor_values_observed_before_registration")
        is False
        and boundary.get(
            "terminal_factor_comparison_values_observed_for_this_candidate_before_registration"
        )
        is False
        and boundary.get("daily_price_fields_read_before_registration") is False
        and boundary.get("forward_return_fields_read_before_registration") is False
    ):
        raise IntradayMarketIdiosyncraticShareError(
            "market-idiosyncratic protocol no longer matches its frozen definition"
        )
    return spec


def validate_repository_chain(spec: dict[str, Any]) -> dict[str, Any]:
    """Validate the append-only state and immediate terminal predecessor."""

    evidence: dict[str, Any] = {}
    for name in (
        "mechanism_overlap_reaudit",
        "prior_no_return_protocol",
        "prior_terminal_record",
    ):
        link = spec["source_chain"][name]
        path = _repository_path(str(link["path"]))
        expected = str(link["sha256"])
        _require_file(path, expected, name.replace("_", " "))
        evidence[name] = {"path": str(path), "sha256": expected}
    _require_file(
        DEFAULT_CURRENT_STATUS,
        TERMINAL_CURRENT_STATUS_SHA256,
        "authoritative three-day research state",
    )
    state = research.load_three_day_iteration_status()
    summary = state.get("post_frontier_summary") or {}
    terminal = list(state.get("post_frontier_terminal_mechanisms") or [])
    decision = state.get("decision") or {}
    predecessor_state = (
        state.get("status")
        == "aggregation_blocked_after_intraday_price_update_share_terminal_rejection_zero_dual_gate_factors"
        and summary.get("terminal_mechanism_count") == 45
        and len(terminal) == 45
        and terminal[-1].get("mechanism") == "tushare_intraday_price_update_share_238m"
        and (terminal[-1].get("record") or {}).get("sha256")
        == PREVIOUS_TERMINAL_RECORD_SHA256
    )
    terminal_state = (
        state.get("status")
        == "aggregation_blocked_after_intraday_market_idiosyncratic_share_terminal_rejection_zero_dual_gate_factors"
        and summary.get("terminal_mechanism_count") == 46
        and len(terminal) == 46
        and terminal[-2].get("mechanism") == "tushare_intraday_price_update_share_238m"
        and terminal[-1].get("mechanism")
        == "tushare_intraday_market_idiosyncratic_share_238m"
        and (terminal[-1].get("record") or {}).get("sha256") == TERMINAL_RECORD_SHA256
    )
    if not (
        (predecessor_state or terminal_state)
        and summary.get("admitted_factor_count") == 0
        and summary.get("aggregation_candidate_count") == 0
        and decision.get("aggregation_allowed") is False
        and decision.get("current_scoring_allowed") is False
        and decision.get("selection_allowed") is False
    ):
        raise IntradayMarketIdiosyncraticShareError(
            "authoritative three-day state changed after preregistration"
        )
    if previous.load_terminal_record_if_present() is None:
        raise IntradayMarketIdiosyncraticShareError(
            "price-update-share terminal record is required"
        )
    evidence["preregistered_current_research_state"] = {
        "path": str(_repository_path(str(spec["current_research_state"]["path"]))),
        "sha256": CURRENT_STATUS_SHA256,
        "terminal_mechanism_count_before_this_candidate": 45,
        "historical_binding_not_reinterpreted_as_current_file_bytes": True,
    }
    evidence["authoritative_current_research_state"] = {
        "path": str(DEFAULT_CURRENT_STATUS.resolve()),
        "sha256": TERMINAL_CURRENT_STATUS_SHA256,
        "terminal_mechanism_count": int(summary["terminal_mechanism_count"]),
    }
    context = spec.get("point_in_time_context") or {}
    for name in ("source_universe", "holding_universe", "calendar"):
        link = context.get(name) or {}
        path = _repository_path(str(link["path"]))
        expected = str(link["sha256"])
        _require_file(path, expected, name.replace("_", " "))
        evidence[name] = {"path": str(path), "sha256": expected}
    quality = context.get("quarterly_quality") or {}
    for path_key, hash_key in (
        ("path", "sha256"),
        ("manifest_path", "manifest_sha256"),
    ):
        path = _repository_path(str(quality[path_key]))
        expected = str(quality[hash_key])
        _require_file(path, expected, path_key.replace("_", " "))
        evidence[f"quarterly_quality_{path_key}"] = {
            "path": str(path),
            "sha256": expected,
        }
    return evidence


def load_terminal_record_if_present() -> dict[str, Any] | None:
    """Validate the immutable terminal record once this candidate is closed."""

    if not DEFAULT_TERMINAL_RECORD.is_file():
        return None
    _require_file(
        DEFAULT_TERMINAL_RECORD,
        TERMINAL_RECORD_SHA256,
        "market-idiosyncratic research record",
    )
    _require_file(
        DEFAULT_NO_RETURN_AUDIT_INFRASTRUCTURE_REPAIR,
        NO_RETURN_AUDIT_INFRASTRUCTURE_REPAIR_SHA256,
        "market-idiosyncratic no-return audit infrastructure repair",
    )
    record = research.load_json_record(
        DEFAULT_TERMINAL_RECORD,
        kind=("a_share_tushare_intraday_market_idiosyncratic_share_" "research_record"),
    )
    protocol = (record.get("ordered_protocol") or {}).get(
        "no_return_preregistration"
    ) or {}
    repair = (record.get("ordered_protocol") or {}).get(
        "no_return_audit_infrastructure_repair"
    ) or {}
    audit = (record.get("ordered_protocol") or {}).get("no_return_audit") or {}
    diagnostic_protocol = (record.get("ordered_protocol") or {}).get(
        "diagnostic_preregistration"
    ) or {}
    candidate = (record.get("source_chain") or {}).get("candidate_manifest") or {}
    no_return = record.get("no_return_results") or {}
    results = record.get("return_results") or {}
    artifacts = record.get("historical_artifacts") or {}
    decision = record.get("decision") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("status")
        == "terminal_rejected_at_association_stability_and_executable_topk_gates"
        and protocol.get("sha256") == PREREGISTRATION_SHA256
        and repair.get("sha256") == NO_RETURN_AUDIT_INFRASTRUCTURE_REPAIR_SHA256
        and repair.get("formula_direction_comparisons_order_or_gates_changed") is False
        and repair.get("forward_returns_read_during_failed_attempts_or_repair") is False
        and candidate.get("sha256") == CANDIDATE_MANIFEST_SHA256
        and candidate.get("dataset_sha256") == CANDIDATE_DATASET_SHA256
        and candidate.get("eligible_rows") == EXPECTED_ELIGIBLE_ROWS
        and candidate.get("market_benchmark_byte_sha256")
        == "5437805f84c5c637904a62664cc3ec677e0155f5a215b0df7c38ed0cc35b88bf"
        and audit.get("sha256") == NO_RETURN_AUDIT_SHA256
        and audit.get("status")
        == "passed_no_return_coverage_capacity_and_uniqueness_pending_separate_return_diagnostic_preregistration"
        and audit.get("forward_returns_read") is False
        and diagnostic_protocol.get("sha256") == DIAGNOSTIC_PREREGISTRATION_SHA256
        and no_return.get("coverage_and_capacity_gate_passed") is True
        and no_return.get("comparison_factor_count") == 21
        and no_return.get("all_twenty_one_uniqueness_gates_passed") is True
        and no_return.get(
            "maximum_absolute_median_daily_rank_correlation_to_twenty_one_terminal_factors"
        )
        == 0.2656277856229116
        and results.get("cohorts") == 539
        and results.get("mean_rank_ic") == -0.011522848933218546
        and results.get("association_stability_gate_passed") is False
        and results.get("topk_viability_gate_passed") is False
        and results.get("dual_gate_passed") is False
        and results.get("execution_aware_top3_net_cumulative_return")
        == -0.585483219525998
        and results.get("execution_aware_top3_maximum_drawdown") == -0.7893551168099013
        and results.get("pilot_net_cumulative_return_at_ten_bp_each_side")
        == -0.18375337712907258
        and results.get("pilot_board_lot_affordability_rate") == 0.931077694235589
        and results.get("pilot_maximum_daily_amount_participation")
        == 0.010161411961011476
        and (artifacts.get("diagnostic") or {}).get("sha256") == DIAGNOSTIC_SHA256
        and (artifacts.get("stability_audit") or {}).get("sha256")
        == STABILITY_AUDIT_SHA256
        and (artifacts.get("topk_viability_audit") or {}).get("sha256")
        == TOPK_AUDIT_SHA256
        and (artifacts.get("single_use_consumption_marker") or {}).get("sha256")
        == CONSUMPTION_MARKER_SHA256
        and decision.get("terminally_reject_exact_factor_direction") is True
        and decision.get("aggregation_candidate_added") is False
        and decision.get("aggregation_allowed") is False
        and decision.get("selection_allowed") is False
        and decision.get("level2_intake_justified") is False
        and boundary.get("same_history_combination_return_evaluation_performed")
        is False
        and boundary.get("current_stock_list_generated") is False
    ):
        raise IntradayMarketIdiosyncraticShareError(
            "market-idiosyncratic research record is inconsistent"
        )
    return record


def _validate_previous_manifest(
    spec: dict[str, Any],
    data_root: Path,
) -> tuple[dict[str, Any], Path]:
    link = spec["source_chain"]["price_update_share_comparison_manifest"]
    path = (data_root / str(link["path_below_data_root"])).resolve()
    _require_file(path, PREVIOUS_MANIFEST_SHA256, "price-update-share manifest")
    manifest = research.load_json_record(
        path, kind="a_share_tushare_intraday_price_update_share_snapshot"
    )
    previous._validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    if manifest.get("dataset_sha256") != PREVIOUS_DATASET_SHA256:
        raise IntradayMarketIdiosyncraticShareError(
            "price-update-share comparison dataset changed"
        )
    return manifest, path


def validate_external_chain(spec: dict[str, Any], data_root: Path) -> tuple[Any, ...]:
    chain = previous.validate_external_chain(previous.load_preregistration(), data_root)
    prior_manifest, prior_path = _validate_previous_manifest(spec, data_root)
    return (*chain, prior_manifest, prior_path)


def _normalized_base(base: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if missing := sorted({"trade_date", "symbol"} - set(base.columns)):
        raise IntradayMarketIdiosyncraticShareError(
            "joint base partition is missing columns: " + ", ".join(missing)
        )
    symbol = symbol.upper()
    work = base[["trade_date", "symbol"]].copy()
    work["trade_date"] = pd.to_datetime(
        work["trade_date"], errors="coerce"
    ).dt.normalize()
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work = work.sort_values("trade_date", kind="stable").reset_index(drop=True)
    if (
        work["trade_date"].isna().any()
        or (not work.empty and set(work["symbol"]) != {symbol})
        or work.duplicated(["trade_date", "symbol"]).any()
    ):
        raise IntradayMarketIdiosyncraticShareError(
            f"joint base identity is invalid for {symbol}"
        )
    return work


def extract_partition_returns(
    raw: pd.DataFrame,
    base: pd.DataFrame,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """Extract the frozen 238-return vectors without any market or outcome data."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise IntradayMarketIdiosyncraticShareError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    base_work = _normalized_base(base, symbol)
    if base_work.empty:
        return base_work, np.empty((0, RETURN_POSITIONS)), np.empty(0, dtype=bool)
    symbol = symbol.upper()
    if raw.empty:
        raise IntradayMarketIdiosyncraticShareError(
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
        raise IntradayMarketIdiosyncraticShareError(
            f"raw identity or timestamp violation for {symbol}"
        )
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise IntradayMarketIdiosyncraticShareError(
            f"every source stock-day must retain the exact 241-row grid for {symbol}"
        )
    observed_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(value) for value in values))
    if not observed_codes.eq(SOURCE_MINUTE_CODE_SET).all():
        raise IntradayMarketIdiosyncraticShareError(
            f"source minute grid changed for {symbol}"
        )
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise IntradayMarketIdiosyncraticShareError(
            f"joint-clean base dates do not match raw dates for {symbol}"
        )
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
    closes = continuous["close"].to_numpy(dtype=float).reshape(-1, 240)
    close_valid = np.isfinite(closes).all(axis=1) & (closes > 0.0).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        log_closes = np.log(closes)
        morning = log_closes[:, 1:120] - log_closes[:, :119]
        afternoon = log_closes[:, 121:240] - log_closes[:, 120:239]
    returns = np.concatenate([morning, afternoon], axis=1)
    return_valid = np.isfinite(returns).all(axis=1)
    valid = close_valid & return_valid
    returns[~valid, :] = np.nan
    return base_work, returns, valid


def _benchmark_for_dates(
    benchmark: MarketBenchmark,
    dates: Sequence[pd.Timestamp],
) -> tuple[np.ndarray, np.ndarray]:
    try:
        indices = np.fromiter(
            (
                benchmark.date_to_index[pd.Timestamp(value).normalize()]
                for value in dates
            ),
            dtype=np.int64,
            count=len(dates),
        )
    except KeyError as exc:
        raise IntradayMarketIdiosyncraticShareError(
            f"candidate date is missing from market benchmark: {exc}"
        ) from exc
    return benchmark.return_sums[indices], benchmark.valid_stock_counts[indices]


def compute_partition_frame(
    raw: pd.DataFrame,
    base: pd.DataFrame,
    benchmark: MarketBenchmark,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Compute the frozen leave-one-out market-idiosyncratic share."""

    empty_quality = {
        "base_rows": 0,
        "eligible_rows": 0,
        "invalid_required_close_rows": 0,
        "insufficient_leave_one_out_peer_rows": 0,
        "constant_stock_return_vector_rows": 0,
        "constant_market_return_vector_rows": 0,
        "nonfinite_correlation_rows": 0,
        "endpoint_canonicalized_rows": 0,
        "range_violation_rows": 0,
    }
    base_work, returns, valid = extract_partition_returns(raw, base, symbol=symbol)
    if base_work.empty:
        return empty_output_frame(), empty_quality
    sums, counts = _benchmark_for_dates(benchmark, base_work["trade_date"])
    own = np.where(np.isfinite(returns), returns, 0.0)
    own_count = np.isfinite(returns).astype(np.int32)
    peer_counts = counts.astype(np.int64) - own_count
    peer_sums = sums - own
    sufficient = (peer_counts >= MINIMUM_LEAVE_ONE_OUT_PEERS).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        peer_returns = np.divide(
            peer_sums,
            peer_counts,
            out=np.full_like(peer_sums, np.nan, dtype=float),
            where=peer_counts > 0,
        )
        stock_observations = np.isfinite(returns).sum(axis=1, keepdims=True)
        stock_means = np.divide(
            np.where(np.isfinite(returns), returns, 0.0).sum(axis=1, keepdims=True),
            stock_observations,
            out=np.full((len(returns), 1), np.nan),
            where=stock_observations > 0,
        )
        market_observations = np.isfinite(peer_returns).sum(axis=1, keepdims=True)
        market_means = np.divide(
            np.where(np.isfinite(peer_returns), peer_returns, 0.0).sum(
                axis=1, keepdims=True
            ),
            market_observations,
            out=np.full((len(returns), 1), np.nan),
            where=market_observations > 0,
        )
        stock_centered = returns - stock_means
        market_centered = peer_returns - market_means
        stock_ss = np.nansum(stock_centered * stock_centered, axis=1)
        market_ss = np.nansum(market_centered * market_centered, axis=1)
        covariance = np.nansum(stock_centered * market_centered, axis=1)
        denominator = np.sqrt(stock_ss * market_ss)
        correlation = covariance / denominator
        values = 1.0 - correlation * correlation
    constant_stock = valid & (stock_ss <= 0.0)
    constant_market = valid & sufficient & (market_ss <= 0.0)
    finite = np.isfinite(correlation) & np.isfinite(values)
    low_near = (values < 0.0) & (values >= -ENDPOINT_TOLERANCE)
    high_near = (values > 1.0) & (values <= 1.0 + ENDPOINT_TOLERANCE)
    canonicalized = valid & sufficient & finite & (low_near | high_near)
    values = np.where(low_near, 0.0, np.where(high_near, 1.0, values))
    in_range = (values >= 0.0) & (values <= 1.0)
    eligible = (
        valid & sufficient & ~constant_stock & ~constant_market & finite & in_range
    )
    output = pd.DataFrame(
        {
            "trade_date": base_work["trade_date"],
            "symbol": symbol.upper(),
            "provider": "tushare",
            FACTOR_NAME: np.where(eligible, values, np.nan),
            f"{FACTOR_NAME}_eligible": eligible,
        }
    ).loc[:, OUTPUT_COLUMNS]
    return output, {
        "base_rows": int(len(output)),
        "eligible_rows": int(eligible.sum()),
        "invalid_required_close_rows": int((~valid).sum()),
        "insufficient_leave_one_out_peer_rows": int((valid & ~sufficient).sum()),
        "constant_stock_return_vector_rows": int(constant_stock.sum()),
        "constant_market_return_vector_rows": int(constant_market.sum()),
        "nonfinite_correlation_rows": int(
            (valid & sufficient & ~constant_stock & ~constant_market & ~finite).sum()
        ),
        "endpoint_canonicalized_rows": int(canonicalized.sum()),
        "range_violation_rows": int(
            (
                valid
                & sufficient
                & ~constant_stock
                & ~constant_market
                & finite
                & ~in_range
            ).sum()
        ),
    }


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived/a_share/rich/tushare/minute_intraday_market_idiosyncratic_share"
        / OUTPUT_RUN_ID
    )


def _calendar_dates(spec: dict[str, Any]) -> pd.DatetimeIndex:
    path = _repository_path(str(spec["point_in_time_context"]["calendar"]["path"]))
    values = pd.to_datetime(
        pd.read_csv(path, header=None, names=["trade_date"])["trade_date"],
        errors="coerce",
    )
    dates = pd.DatetimeIndex(
        values.loc[
            values.between(pd.Timestamp("2019-01-01"), pd.Timestamp("2025-12-31"))
        ]
    ).normalize()
    if dates.hasnans or dates.duplicated().any() or not dates.is_monotonic_increasing:
        raise IntradayMarketIdiosyncraticShareError("frozen local calendar is invalid")
    return dates


def _read_verified_returns(
    raw_record: dict[str, Any],
    joint_record: dict[str, Any],
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    raw_path = Path(str(raw_record["path"]))
    base_path = Path(str(joint_record["path"]))
    if foundation.file_digest(raw_path) != raw_record.get("byte_sha256"):
        raise IntradayMarketIdiosyncraticShareError(
            f"raw partition changed: {raw_path}"
        )
    if foundation.file_digest(base_path) != joint_record.get("output_byte_sha256"):
        raise IntradayMarketIdiosyncraticShareError(
            f"joint-base partition changed: {base_path}"
        )
    raw = pd.read_parquet(raw_path, columns=list(RAW_COLUMNS))
    base = pd.read_parquet(base_path, columns=["trade_date", "symbol"])
    return extract_partition_returns(raw, base, symbol=str(joint_record["symbol"]))


def _symbol_market_contribution(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
) -> tuple[str, np.ndarray, np.ndarray, int]:
    symbol = str(pairs[0][1]["symbol"])
    date_parts: list[np.ndarray] = []
    return_parts: list[np.ndarray] = []
    invalid = 0
    for raw_record, joint_record in sorted(
        pairs, key=lambda pair: int(pair[1]["year"])
    ):
        base, returns, valid = _read_verified_returns(raw_record, joint_record)
        date_parts.append(
            pd.to_datetime(base["trade_date"]).to_numpy(dtype="datetime64[ns]")
        )
        return_parts.append(returns)
        invalid += int((~valid).sum())
    dates = (
        np.concatenate(date_parts)
        if date_parts
        else np.empty(0, dtype="datetime64[ns]")
    )
    returns = (
        np.concatenate(return_parts, axis=0)
        if return_parts
        else np.empty((0, RETURN_POSITIONS))
    )
    if pd.Index(dates).duplicated().any():
        raise IntradayMarketIdiosyncraticShareError(
            f"duplicate market-contribution date for {symbol}"
        )
    return symbol, dates, returns, invalid


def _atomic_write_accumulator(
    path: Path,
    *,
    dates: pd.DatetimeIndex,
    return_sums: np.ndarray,
    valid_counts: np.ndarray,
    processed_symbols: set[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.npz")
    np.savez_compressed(
        temporary,
        schema_version=np.array([1], dtype=np.int16),
        protocol_sha256=np.array([PREREGISTRATION_SHA256]),
        raw_manifest_sha256=np.array([RAW_MANIFEST_SHA256]),
        joint_manifest_sha256=np.array([JOINT_MANIFEST_SHA256]),
        dates=dates.to_numpy(dtype="datetime64[ns]"),
        return_sums=return_sums,
        valid_counts=valid_counts,
        processed_symbols=np.array(sorted(processed_symbols), dtype="U16"),
    )
    temporary.replace(path)


def _load_or_create_accumulator(
    path: Path,
    dates: pd.DatetimeIndex,
) -> tuple[np.ndarray, np.ndarray, set[str]]:
    shape = (len(dates), RETURN_POSITIONS)
    if not path.is_file():
        return np.zeros(shape, dtype=np.float64), np.zeros(shape, dtype=np.int32), set()
    try:
        with np.load(path, allow_pickle=False) as state:
            observed_dates = state["dates"].astype("datetime64[ns]")
            return_sums = state["return_sums"].astype(np.float64, copy=True)
            valid_counts = state["valid_counts"].astype(np.int32, copy=True)
            processed = {str(value) for value in state["processed_symbols"].tolist()}
            valid = (
                state["schema_version"].tolist() == [1]
                and state["protocol_sha256"].tolist() == [PREREGISTRATION_SHA256]
                and state["raw_manifest_sha256"].tolist() == [RAW_MANIFEST_SHA256]
                and state["joint_manifest_sha256"].tolist() == [JOINT_MANIFEST_SHA256]
                and np.array_equal(
                    observed_dates, dates.to_numpy(dtype="datetime64[ns]")
                )
                and return_sums.shape == shape
                and valid_counts.shape == shape
                and np.isfinite(return_sums).all()
                and (valid_counts >= 0).all()
            )
    except (OSError, ValueError, KeyError) as exc:
        raise IntradayMarketIdiosyncraticShareError(
            f"market accumulator checkpoint is unreadable: {path}"
        ) from exc
    if not valid:
        raise IntradayMarketIdiosyncraticShareError(
            f"market accumulator checkpoint changed: {path}"
        )
    return return_sums, valid_counts, processed


def _build_market_benchmark(
    *,
    pairs_by_symbol: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]],
    dates: pd.DatetimeIndex,
    partial_root: Path,
    final_root: Path,
    workers: int,
) -> tuple[MarketBenchmark, dict[str, Any]]:
    accumulator_path = partial_root / ".metadata/market_accumulator.npz"
    return_sums, valid_counts, processed = _load_or_create_accumulator(
        accumulator_path, dates
    )
    unexpected = processed - set(pairs_by_symbol)
    if unexpected:
        raise IntradayMarketIdiosyncraticShareError(
            "market accumulator contains unknown processed symbols"
        )
    date_to_index = {pd.Timestamp(value): index for index, value in enumerate(dates)}
    symbols = [symbol for symbol in sorted(pairs_by_symbol) if symbol not in processed]
    invalid_total = 0
    batch_size = max(8, workers * 8)
    print(
        f"building market accumulator for {len(pairs_by_symbol):,} symbols; "
        f"resumed={len(processed):,}",
        flush=True,
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for offset in range(0, len(symbols), batch_size):
            batch = symbols[offset : offset + batch_size]
            results = list(
                pool.map(
                    _symbol_market_contribution,
                    [pairs_by_symbol[symbol] for symbol in batch],
                )
            )
            for symbol, contribution_dates, returns, invalid in results:
                try:
                    indices = np.fromiter(
                        (
                            date_to_index[pd.Timestamp(value).normalize()]
                            for value in contribution_dates
                        ),
                        dtype=np.int64,
                        count=len(contribution_dates),
                    )
                except KeyError as exc:
                    raise IntradayMarketIdiosyncraticShareError(
                        f"market contribution date is outside the frozen calendar: {exc}"
                    ) from exc
                valid_rows = np.isfinite(returns).all(axis=1)
                if valid_rows.any():
                    return_sums[indices[valid_rows], :] += returns[valid_rows, :]
                    valid_counts[indices[valid_rows], :] += 1
                processed.add(symbol)
                invalid_total += invalid
            del results
            gc.collect()
            if (offset // batch_size + 1) % 5 == 0 or offset + batch_size >= len(
                symbols
            ):
                _atomic_write_accumulator(
                    accumulator_path,
                    dates=dates,
                    return_sums=return_sums,
                    valid_counts=valid_counts,
                    processed_symbols=processed,
                )
                print(
                    f"market progress symbols={len(processed):,}/"
                    f"{len(pairs_by_symbol):,}",
                    flush=True,
                )
    if processed != set(pairs_by_symbol):
        raise IntradayMarketIdiosyncraticShareError(
            "market accumulator did not consume every source symbol"
        )
    nonempty = valid_counts.max(axis=1) > 0
    if not nonempty.any():
        raise IntradayMarketIdiosyncraticShareError(
            "market accumulator contains no valid stock-day"
        )
    if not np.equal(valid_counts, valid_counts[:, :1]).all():
        raise IntradayMarketIdiosyncraticShareError(
            "market valid-stock counts differ across frozen return positions"
        )
    active_dates = dates[nonempty]
    active_sums = return_sums[nonempty, :]
    active_counts = valid_counts[nonempty, :]
    frame = pd.DataFrame(
        {
            "trade_date": np.repeat(active_dates.to_numpy(), RETURN_POSITIONS),
            "return_position": np.tile(
                np.arange(RETURN_POSITIONS, dtype=np.int16), len(active_dates)
            ),
            "return_sum": active_sums.reshape(-1),
            "valid_stock_count": active_counts.reshape(-1),
        }
    ).loc[:, BENCHMARK_COLUMNS]
    benchmark_path = partial_root / BENCHMARK_FILENAME
    foundation.atomic_write_frame(frame, benchmark_path)
    frame_sha256 = foundation.frame_digest(frame)
    byte_sha256 = foundation.file_digest(benchmark_path)
    benchmark = MarketBenchmark(
        dates=active_dates,
        return_sums=active_sums,
        valid_stock_counts=active_counts,
        date_to_index={
            pd.Timestamp(value).normalize(): index
            for index, value in enumerate(active_dates)
        },
        frame_sha256=frame_sha256,
    )
    per_date_counts = active_counts[:, 0]
    evidence = {
        "path": str(final_root / BENCHMARK_FILENAME),
        "rows": int(len(frame)),
        "trade_dates": int(len(active_dates)),
        "return_positions_per_date": RETURN_POSITIONS,
        "output_byte_sha256": byte_sha256,
        "output_frame_sha256": frame_sha256,
        "valid_stock_count_minimum": int(per_date_counts.min()),
        "valid_stock_count_p05": float(np.quantile(per_date_counts, 0.05)),
        "valid_stock_count_median": float(np.median(per_date_counts)),
        "valid_stock_count_maximum": int(per_date_counts.max()),
        "invalid_required_close_rows_observed_during_fresh_first_pass": int(
            invalid_total
        ),
        "processed_symbol_count": int(len(processed)),
        "source_fields_read": list(RAW_COLUMNS),
        "daily_price_fields_read": [],
        "comparison_factor_values_read": False,
        "forward_return_fields_read": False,
    }
    return benchmark, evidence


def _load_checkpoint(
    raw_record: dict[str, Any],
    joint_record: dict[str, Any],
    paths: Any,
    benchmark: MarketBenchmark,
) -> tuple[dict[str, Any], Counter[str]] | None:
    if not paths.partial_sidecar.exists():
        paths.partial_data.unlink(missing_ok=True)
        return None
    record = json.loads(paths.partial_sidecar.read_text(encoding="utf-8"))
    raw_path = Path(str(raw_record["path"]))
    base_path = Path(str(joint_record["path"]))
    valid = (
        record.get("kind")
        == "a_share_tushare_intraday_market_idiosyncratic_share_partition"
        and record.get("protocol_sha256") == PREREGISTRATION_SHA256
        and record.get("raw_manifest_sha256") == RAW_MANIFEST_SHA256
        and record.get("joint_manifest_sha256") == JOINT_MANIFEST_SHA256
        and record.get("market_benchmark_frame_sha256") == benchmark.frame_sha256
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
        raise IntradayMarketIdiosyncraticShareError(
            f"completed candidate checkpoint changed: {paths.partial_sidecar}"
        )
    output = pd.read_parquet(paths.partial_data)
    if len(output) != int(record.get("rows", -1)) or foundation.frame_digest(
        output
    ) != record.get("output_frame_sha256"):
        raise IntradayMarketIdiosyncraticShareError(
            f"completed candidate frame changed: {paths.partial_data}"
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
    benchmark: MarketBenchmark,
    partial_root: Path,
    final_root: Path,
) -> tuple[dict[str, Any], Counter[str], bool]:
    paths = foundation.partition_paths(partial_root, final_root, joint_record)
    completed = _load_checkpoint(raw_record, joint_record, paths, benchmark)
    if completed is not None:
        record, dates = completed
        return record, dates, True
    raw_path = Path(str(raw_record["path"]))
    base_path = Path(str(joint_record["path"]))
    if foundation.file_digest(raw_path) != raw_record.get("byte_sha256"):
        raise IntradayMarketIdiosyncraticShareError(
            f"raw partition changed: {raw_path}"
        )
    if foundation.file_digest(base_path) != joint_record.get("output_byte_sha256"):
        raise IntradayMarketIdiosyncraticShareError(
            f"joint-base partition changed: {base_path}"
        )
    raw = pd.read_parquet(raw_path, columns=list(RAW_COLUMNS))
    base = pd.read_parquet(base_path, columns=["trade_date", "symbol"])
    output, quality = compute_partition_frame(
        raw,
        base,
        benchmark,
        symbol=str(joint_record["symbol"]),
    )
    foundation.atomic_write_frame(output, paths.partial_data)
    record = {
        "schema_version": 1,
        "kind": "a_share_tushare_intraday_market_idiosyncratic_share_partition",
        "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "protocol_sha256": PREREGISTRATION_SHA256,
        "raw_manifest_sha256": RAW_MANIFEST_SHA256,
        "joint_manifest_sha256": JOINT_MANIFEST_SHA256,
        "market_benchmark_frame_sha256": benchmark.frame_sha256,
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
    benchmark: MarketBenchmark,
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
            benchmark=benchmark,
            partial_root=partial_root,
            final_root=final_root,
        )
        records.append(record)
        eligible_dates.update(dates)
        resumed += int(was_resumed)
    return records, eligible_dates, resumed


def _aggregate_quality(records: Iterable[dict[str, Any]]) -> dict[str, int]:
    total: Counter[str] = Counter()
    for record in records:
        total.update({key: int(value) for key, value in record["quality"].items()})
    return dict(total)


def _validate_snapshot_manifest(
    manifest: dict[str, Any],
    *,
    require_fingerprint_constants: bool,
) -> None:
    quality = manifest.get("quality") or {}
    benchmark = manifest.get("market_benchmark") or {}
    counter_names = (
        "invalid_required_close_rows",
        "insufficient_leave_one_out_peer_rows",
        "constant_stock_return_vector_rows",
        "constant_market_return_vector_rows",
        "nonfinite_correlation_rows",
        "endpoint_canonicalized_rows",
        "range_violation_rows",
    )
    if not (
        manifest.get("kind")
        == "a_share_tushare_intraday_market_idiosyncratic_share_snapshot"
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
        and all(
            isinstance(quality.get(name), int) and quality.get(name) >= 0
            for name in counter_names
        )
        and benchmark.get("rows") == benchmark.get("trade_dates", -1) * RETURN_POSITIONS
        and benchmark.get("return_positions_per_date") == RETURN_POSITIONS
        and benchmark.get("processed_symbol_count") == 5_396
        and benchmark.get("valid_stock_count_minimum", 0)
        >= MINIMUM_LEAVE_ONE_OUT_PEERS + 1
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_close_read") is True
        and manifest.get("source_volume_or_amount_read") is False
        and manifest.get("source_open_high_low_read") is False
        and manifest.get("standalone_09_30_row_excluded_from_formula") is True
        and manifest.get("lunch_boundary_excluded_from_formula") is True
        and manifest.get("leave_one_out_equal_weight_market") is True
        and manifest.get("minimum_leave_one_out_peers") == MINIMUM_LEAVE_ONE_OUT_PEERS
        and manifest.get("factor_formula") == FACTOR_FORMULA
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("forward_return_fields_read") is False
    ):
        raise IntradayMarketIdiosyncraticShareError(
            "market-idiosyncratic snapshot identity is rejected"
        )
    if require_fingerprint_constants and not (
        CANDIDATE_MANIFEST_SHA256
        and CANDIDATE_DATASET_SHA256
        and EXPECTED_ELIGIBLE_ROWS > 0
        and manifest.get("dataset_sha256") == CANDIDATE_DATASET_SHA256
        and manifest.get("eligible_rows") == EXPECTED_ELIGIBLE_ROWS
        and quality.get("invalid_required_close_rows")
        == EXPECTED_INVALID_REQUIRED_CLOSE_ROWS
        and quality.get("insufficient_leave_one_out_peer_rows")
        == EXPECTED_INSUFFICIENT_PEER_ROWS
        and quality.get("constant_stock_return_vector_rows")
        == EXPECTED_CONSTANT_STOCK_RETURN_ROWS
        and quality.get("constant_market_return_vector_rows")
        == EXPECTED_CONSTANT_MARKET_RETURN_ROWS
    ):
        raise IntradayMarketIdiosyncraticShareError(
            "candidate fingerprint and aggregate constants are not bound"
        )


def _partition_maps(
    raw: dict[str, Any],
    joint: dict[str, Any],
) -> tuple[
    dict[tuple[str, int], dict[str, Any]],
    dict[tuple[str, int], dict[str, Any]],
    dict[str, list[tuple[dict[str, Any], dict[str, Any]]]],
]:
    raw_by_key = {
        (str(item["symbol"]), int(item["year"])): item
        for item in list(raw.get("files") or [])
    }
    joint_by_key = {
        (str(item["symbol"]), int(item["year"])): item
        for item in list(joint.get("files") or [])
    }
    if (
        len(raw_by_key) != 33_015
        or len(joint_by_key) != 33_015
        or set(raw_by_key) != set(joint_by_key)
    ):
        raise IntradayMarketIdiosyncraticShareError(
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
            raise IntradayMarketIdiosyncraticShareError(
                f"joint-clean raw source binding changed for {key[0]}/{key[1]}"
            )
        by_symbol.setdefault(key[0], []).append((raw_record, joint_record))
    if len(by_symbol) != 5_396:
        raise IntradayMarketIdiosyncraticShareError(
            "joint-clean source symbol count changed"
        )
    return raw_by_key, joint_by_key, by_symbol


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    """Build the market benchmark and all resumable candidate partitions."""

    if workers < 1 or workers > 8:
        raise ValueError("--workers must be between 1 and 8")
    data_root = data_root.expanduser().resolve()
    spec = load_preregistration()
    final_root = output_root(data_root)
    partial_root = final_root.parent / f".{OUTPUT_RUN_ID}.partial"
    final_manifest = final_root / "snapshot_manifest.json"
    if final_root.exists():
        if not final_manifest.is_file():
            raise IntradayMarketIdiosyncraticShareError(
                f"published candidate root has no manifest: {final_root}"
            )
        if not CANDIDATE_MANIFEST_SHA256:
            raise IntradayMarketIdiosyncraticShareError(
                "bind the published candidate manifest before reusing it"
            )
        _require_file(
            final_manifest,
            CANDIDATE_MANIFEST_SHA256,
            "published market-idiosyncratic manifest",
        )
        manifest = research.load_json_record(final_manifest)
        _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
        load_terminal_record_if_present()
        return final_manifest
    repository_evidence = validate_repository_chain(spec)
    chain = validate_external_chain(spec, data_root)
    raw, joint, raw_manifest_path, joint_manifest_path = chain[:4]
    if shutil.disk_usage(data_root).free < 10 * 1024**3:
        raise IntradayMarketIdiosyncraticShareError(
            "external data root has less than 10 GiB free"
        )
    _, joint_by_key, by_symbol = _partition_maps(raw, joint)
    lock_path = data_root / ".a_share_tushare_intraday_market_idiosyncratic_share.lock"
    with foundation.ProcessLock(lock_path):
        partial_root.mkdir(parents=True, exist_ok=True)
        benchmark, benchmark_evidence = _build_market_benchmark(
            pairs_by_symbol=by_symbol,
            dates=_calendar_dates(spec),
            partial_root=partial_root,
            final_root=final_root,
            workers=workers,
        )
        all_records: list[dict[str, Any]] = []
        eligible_dates: Counter[str] = Counter()
        resumed = 0
        completed_symbols = 0
        print(
            f"building {len(joint_by_key):,} market-idiosyncratic partitions "
            f"across {len(by_symbol):,} symbols with {workers} workers",
            flush=True,
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    _process_symbol,
                    pairs,
                    benchmark=benchmark,
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
                            f"candidate progress symbols={completed_symbols:,}/"
                            f"{len(by_symbol):,} partitions={len(all_records):,}/"
                            f"{len(joint_by_key):,} "
                            f"eligible_rows={sum(eligible_dates.values()):,} "
                            f"resumed={resumed:,}",
                            flush=True,
                        )
            except BaseException:
                for future in futures:
                    future.cancel()
                raise
        if len(all_records) != 33_015:
            raise IntradayMarketIdiosyncraticShareError(
                "not every source partition produced a candidate checkpoint"
            )
        _require_file(raw_manifest_path, RAW_MANIFEST_SHA256, "raw minute manifest")
        _require_file(
            joint_manifest_path, JOINT_MANIFEST_SHA256, "joint-clean manifest"
        )
        all_records.sort(key=lambda item: (str(item["symbol"]), int(item["year"])))
        quality = _aggregate_quality(all_records)
        dataset_payload = "\n".join(
            [
                f"market|{benchmark_evidence['output_byte_sha256']}",
                *[
                    f"{item['symbol']}|{item['year']}|{item['output_byte_sha256']}"
                    for item in all_records
                ],
            ]
        ).encode("utf-8")
        manifest = {
            "schema_version": 1,
            "kind": ("a_share_tushare_intraday_market_idiosyncratic_share_snapshot"),
            "status": (
                "candidate_feature_complete_pending_ordered_no_return_"
                "coverage_capacity_and_uniqueness"
            ),
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
            "factor_formula": FACTOR_FORMULA,
            "market_benchmark": benchmark_evidence,
            "files": all_records,
            "partitions": len(all_records),
            "rows": int(quality.get("base_rows", -1)),
            "eligible_rows": int(quality.get("eligible_rows", -1)),
            "quality": quality,
            "eligible_names_by_date": dict(sorted(eligible_dates.items())),
            "source_fields_read": list(RAW_COLUMNS),
            "source_close_read": True,
            "source_volume_or_amount_read": False,
            "source_open_high_low_read": False,
            "standalone_09_30_row_excluded_from_formula": True,
            "lunch_boundary_excluded_from_formula": True,
            "leave_one_out_equal_weight_market": True,
            "minimum_leave_one_out_peers": MINIMUM_LEAVE_ONE_OUT_PEERS,
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
        accumulator_path = partial_root / ".metadata/market_accumulator.npz"
        accumulator_path.unlink(missing_ok=True)
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
        raise IntradayMarketIdiosyncraticShareError(
            "candidate snapshot partition count changed"
        )
    partition_root = (manifest_path.parent / "partitions").resolve()
    benchmark = manifest.get("market_benchmark") or {}
    benchmark_path = Path(str(benchmark.get("path"))).resolve()
    try:
        benchmark_path.relative_to(manifest_path.parent.resolve())
    except ValueError as exc:
        raise IntradayMarketIdiosyncraticShareError(
            "market benchmark escapes candidate root"
        ) from exc
    _require_file(
        benchmark_path,
        str(benchmark["output_byte_sha256"]),
        "market benchmark",
    )

    def verify(record: dict[str, Any]) -> tuple[int, int, int]:
        path = Path(str(record["path"])).resolve()
        try:
            path.relative_to(partition_root)
        except ValueError as exc:
            raise IntradayMarketIdiosyncraticShareError(
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
        return int(record["rows"]), int(record["eligible_rows"]), path.stat().st_size

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
        raise IntradayMarketIdiosyncraticShareError(
            "candidate snapshot aggregate counts changed"
        )
    return {
        "partitions_verified": len(records),
        "rows_verified": rows,
        "eligible_rows_verified": eligible,
        "partition_bytes_verified": byte_count,
        "market_benchmark_bytes_verified": int(benchmark_path.stat().st_size),
    }


def load_candidate_frame(
    manifest_path: Path,
    manifest: dict[str, Any],
) -> pd.DataFrame:
    dataset = pa_dataset.dataset(
        str(manifest_path.parent / "partitions"), format="parquet"
    )
    table = dataset.to_table(columns=list(OUTPUT_COLUMNS), use_threads=True)
    frame = table.to_pandas(split_blocks=True, self_destruct=True)
    del table, dataset
    gc.collect()
    if len(frame) != int(manifest.get("rows", -1)):
        raise IntradayMarketIdiosyncraticShareError("candidate frame row count changed")
    frame["trade_date"] = pd.to_datetime(
        frame["trade_date"], errors="coerce"
    ).dt.normalize()
    frame["symbol"] = frame["symbol"].astype(str).str.upper()
    frame[f"{FACTOR_NAME}_eligible"] = (
        frame[f"{FACTOR_NAME}_eligible"].astype("boolean").fillna(False).astype(bool)
    )
    frame[FACTOR_NAME] = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"]
    values = frame.loc[eligible, FACTOR_NAME].to_numpy(dtype=float)
    if (
        frame["trade_date"].isna().any()
        or frame.duplicated(["trade_date", "symbol"]).any()
        or not np.isfinite(values).all()
        or (values < 0.0).any()
        or (values > 1.0).any()
        or frame.loc[~eligible, FACTOR_NAME].notna().any()
    ):
        raise IntradayMarketIdiosyncraticShareError(
            "candidate frame values or keys are invalid"
        )
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
        "median_daily_rank_correlation": median if math.isfinite(median) else None,
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


def _compact_stock_day_keys(
    trade_dates: pd.Series,
    symbols: pd.Series,
) -> np.ndarray:
    """Encode a stock-day identity without retaining Python string objects."""

    dates = pd.to_datetime(trade_dates, errors="coerce").dt.normalize()
    text = symbols.astype("string").str.upper()
    exchange = text.str.slice(0, 2).map({"SH": 1, "SZ": 2, "BJ": 3})
    codes = pd.to_numeric(text.str.slice(2), errors="coerce")
    if dates.isna().any() or exchange.isna().any() or codes.isna().any():
        raise IntradayMarketIdiosyncraticShareError(
            "comparison stock-day identity cannot be compacted"
        )
    day_number = dates.to_numpy(dtype="datetime64[D]").astype(np.int64, copy=False)
    security_number = exchange.to_numpy(dtype=np.int64) * 1_000_000 + codes.to_numpy(
        dtype=np.int64
    )
    return day_number * 4_000_000 + security_number


def _load_filtered_comparison_values(
    dataset_root: Path,
    factors: Sequence[str],
    candidate_keys: np.ndarray,
    *,
    expected_total_rows: int = 7_724_498,
) -> dict[str, np.ndarray]:
    """Scan one immutable snapshot and retain only quality-eligible keys."""

    dataset = pa_dataset.dataset(str(dataset_root), format="parquet")
    scanner = dataset.scanner(
        columns=["trade_date", "symbol", *factors],
        batch_size=262_144,
        use_threads=True,
    )
    candidate_keys = np.asarray(candidate_keys, dtype=np.int64)
    selected_keys: list[np.ndarray] = []
    selected_values: dict[str, list[np.ndarray]] = {factor: [] for factor in factors}
    total_rows = 0
    for batch in scanner.to_batches():
        frame = batch.to_pandas(split_blocks=True, self_destruct=True)
        total_rows += len(frame)
        keys = _compact_stock_day_keys(frame["trade_date"], frame["symbol"])
        positions = np.searchsorted(candidate_keys, keys, side="left")
        mask = positions < len(candidate_keys)
        matched = np.zeros(len(keys), dtype=bool)
        matched[mask] = candidate_keys[positions[mask]] == keys[mask]
        mask = matched
        if mask.any():
            selected_keys.append(keys[mask])
            for factor in factors:
                selected_values[factor].append(
                    pd.to_numeric(frame.loc[mask, factor], errors="coerce").to_numpy(
                        dtype=float
                    )
                )
        del frame, keys, positions, matched, mask, batch
    del scanner, dataset
    gc.collect()
    if total_rows != expected_total_rows:
        raise IntradayMarketIdiosyncraticShareError(
            f"comparison snapshot row count changed: {total_rows}"
        )
    observed_keys = (
        np.concatenate(selected_keys) if selected_keys else np.empty(0, dtype=np.int64)
    )
    if len(observed_keys) != len(candidate_keys):
        raise IntradayMarketIdiosyncraticShareError(
            "comparison snapshot does not cover every candidate stock-day key"
        )
    order = np.argsort(observed_keys, kind="stable")
    observed_keys = observed_keys[order]
    if len(np.unique(observed_keys)) != len(observed_keys) or not np.array_equal(
        observed_keys, candidate_keys
    ):
        raise IntradayMarketIdiosyncraticShareError(
            "comparison snapshot stock-day keys changed"
        )
    aligned: dict[str, np.ndarray] = {}
    for factor in factors:
        values = (
            np.concatenate(selected_values[factor])
            if selected_values[factor]
            else np.empty(0, dtype=float)
        )
        aligned[factor] = values[order]
    return aligned


def _aligned_comparison_result(
    *,
    candidate_keys: np.ndarray,
    candidate_values: np.ndarray,
    comparison_values: np.ndarray,
    comparison: str,
    direction: str,
    gate: dict[str, Any],
) -> dict[str, Any]:
    """Compute the frozen daily rank correlations from compact aligned arrays."""

    days = candidate_keys // 4_000_000
    boundaries = np.flatnonzero(np.r_[True, days[1:] != days[:-1], True])
    minimum_names = int(gate["minimum_pairwise_names_per_session"])
    rows: list[dict[str, Any]] = []
    for start, stop in zip(boundaries[:-1], boundaries[1:]):
        candidate = candidate_values[start:stop]
        values = comparison_values[start:stop]
        finite = np.isfinite(candidate) & np.isfinite(values)
        if int(finite.sum()) < minimum_names:
            continue
        candidate = candidate[finite]
        values = values[finite]
        if np.unique(candidate).size < 2 or np.unique(values).size < 2:
            continue
        candidate_score = pd.Series(candidate).rank(method="average", pct=True)
        comparison_score = pd.Series(values).rank(
            method="average",
            pct=True,
            ascending=(direction == "higher"),
        )
        correlation = candidate_score.corr(comparison_score, method="pearson")
        if math.isfinite(float(correlation)):
            rows.append(
                {
                    "trade_date": pd.Timestamp(np.datetime64(int(days[start]), "D")),
                    "pairwise_names": int(finite.sum()),
                    "rank_correlation": float(correlation),
                }
            )
    daily = pd.DataFrame(rows)
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
        "median_daily_rank_correlation": median if math.isfinite(median) else None,
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


def _verify_comparison_snapshot_outputs(
    manifest: dict[str, Any],
    manifest_path: Path,
    workers: int,
) -> dict[str, int]:
    """Verify immutable comparison bytes without re-reading shared raw sources."""

    records = list(manifest.get("files") or [])
    if len(records) != 33_015:
        raise IntradayMarketIdiosyncraticShareError(
            "comparison snapshot partition count changed"
        )
    partition_root = (manifest_path.parent / "partitions").resolve()

    def verify(record: dict[str, Any]) -> tuple[int, int]:
        path = Path(str(record["path"])).resolve()
        try:
            path.relative_to(partition_root)
        except ValueError as exc:
            raise IntradayMarketIdiosyncraticShareError(
                f"comparison partition escapes its root: {path}"
            ) from exc
        _require_file(
            path,
            str(record["output_byte_sha256"]),
            "comparison candidate partition",
        )
        return int(record["rows"]), path.stat().st_size

    rows = byte_count = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for result in pool.map(verify, records):
            partition_rows, partition_bytes = result
            rows += partition_rows
            byte_count += partition_bytes
    if rows != int(manifest.get("rows", -1)):
        raise IntradayMarketIdiosyncraticShareError(
            "comparison snapshot aggregate row count changed"
        )
    return {
        "partitions_verified": len(records),
        "rows_verified": rows,
        "partition_bytes_verified": byte_count,
        "shared_raw_and_joint_sources_verified_by_current_candidate": True,
    }


def uniqueness_audit(
    candidate_quality: pd.DataFrame,
    chain: tuple[Any, ...],
    spec: dict[str, Any],
    workers: int,
) -> dict[str, Any]:
    """Evaluate all comparisons serially with bounded memory."""

    print(
        "coverage passed; loading twenty-one terminal comparisons serially",
        flush=True,
    )
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    candidate = candidate_quality[["trade_date", "symbol", FACTOR_NAME]].copy()
    candidate_keys = _compact_stock_day_keys(
        candidate["trade_date"], candidate["symbol"]
    )
    candidate_values = pd.to_numeric(candidate[FACTOR_NAME], errors="coerce").to_numpy(
        dtype=float
    )
    order = np.argsort(candidate_keys, kind="stable")
    candidate_keys = candidate_keys[order]
    candidate_values = candidate_values[order]
    if (
        len(np.unique(candidate_keys)) != len(candidate_keys)
        or not np.isfinite(candidate_values).all()
    ):
        raise IntradayMarketIdiosyncraticShareError(
            "candidate quality keys or values changed before uniqueness"
        )
    del candidate, candidate_quality, order
    gc.collect()
    results: list[dict[str, Any]] = []
    verifications: dict[str, Any] = {}

    joint_manifest_path = Path(chain[3])
    base_factors = COMPARISON_FACTORS[:4]
    base_values = _load_filtered_comparison_values(
        joint_manifest_path.parent / "partitions",
        base_factors,
        candidate_keys,
    )
    for factor, direction in zip(base_factors, COMPARISON_DIRECTIONS[:4], strict=True):
        results.append(
            _aligned_comparison_result(
                candidate_keys=candidate_keys,
                candidate_values=candidate_values,
                comparison_values=base_values.pop(factor),
                comparison=factor,
                direction=direction,
                gate=gate,
            )
        )
    del base_values
    gc.collect()

    comparison_pairs = list(zip(chain[4::2], chain[5::2], strict=True))
    expected_factors = COMPARISON_FACTORS[4:]
    if (
        len(comparison_pairs) != len(expected_factors)
        or tuple(str(manifest.get("factor_name")) for manifest, _ in comparison_pairs)
        != expected_factors
    ):
        raise IntradayMarketIdiosyncraticShareError("comparison manifest order changed")
    for index, ((manifest, manifest_path), factor, direction) in enumerate(
        zip(
            comparison_pairs,
            expected_factors,
            COMPARISON_DIRECTIONS[4:],
            strict=True,
        ),
        start=5,
    ):
        manifest_path = Path(manifest_path)
        print(
            f"serial uniqueness comparison {index}/21: {factor}",
            flush=True,
        )
        verifications[factor] = _verify_comparison_snapshot_outputs(
            manifest, manifest_path, workers
        )
        values = _load_filtered_comparison_values(
            manifest_path.parent / "partitions",
            [factor],
            candidate_keys,
        )[factor]
        results.append(
            _aligned_comparison_result(
                candidate_keys=candidate_keys,
                candidate_values=candidate_values,
                comparison_values=values,
                comparison=factor,
                direction=direction,
                gate=gate,
            )
        )
        del values
        gc.collect()
    observed = [
        item["absolute_median_daily_rank_correlation"]
        for item in results
        if item["absolute_median_daily_rank_correlation"] is not None
    ]
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
        "base_four_comparisons_passed": bool(
            len(results) >= 4 and all(item["gate_passed"] for item in results[:4])
        ),
        "all_twenty_one_comparisons_passed": bool(
            len(results) == 21 and all(item["gate_passed"] for item in results)
        ),
    }


def _find_existing_audit(
    experiment_root: Path,
    manifest_sha256: str,
) -> Path | None:
    for path in sorted(
        experiment_root.glob(
            "*_intraday_market_idiosyncratic_share_no_return_audit.json"
        )
    ):
        record = research.load_json_record(path)
        if (
            record.get("kind")
            == "a_share_tushare_intraday_market_idiosyncratic_share_no_return_audit"
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
    """Run coverage/capacity before loading the twenty-one comparisons."""

    if not CANDIDATE_MANIFEST_SHA256:
        raise IntradayMarketIdiosyncraticShareError(
            "candidate snapshot fingerprint must be bound before audit"
        )
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_preregistration()
    repository_evidence = validate_repository_chain(spec)
    chain = validate_external_chain(spec, data_root)
    joint = chain[1]
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    _require_file(
        manifest_path,
        CANDIDATE_MANIFEST_SHA256,
        "market-idiosyncratic candidate manifest",
    )
    manifest = research.load_json_record(manifest_path)
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    manifest_sha256 = foundation.file_digest(manifest_path)
    existing = _find_existing_audit(experiment_root, manifest_sha256)
    if existing is not None:
        load_terminal_record_if_present()
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
        "all_twenty_one_comparisons_passed": False,
        "comparisons": [],
    }
    if coverage["gate_passed_before_comparison_values"]:
        uniqueness = uniqueness_audit(candidate_quality, chain, spec, workers)
    del candidate_quality
    gc.collect()
    passed = bool(
        coverage["gate_passed_before_comparison_values"]
        and uniqueness["all_twenty_one_comparisons_passed"]
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
        "kind": ("a_share_tushare_intraday_market_idiosyncratic_share_no_return_audit"),
        "status": status,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "purpose": (
            "ordered_candidate_coverage_capacity_then_twenty_one_terminal_"
            "factor_uniqueness_without_daily_prices_or_forward_returns"
        ),
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
            "price_update_share_manifest_sha256": PREVIOUS_MANIFEST_SHA256,
            "repository_evidence": repository_evidence,
            "snapshot_file_verification": verification,
        },
        "candidate": {
            "name": FACTOR_NAME,
            "direction": "higher",
            "formula": FACTOR_FORMULA,
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
    path = (
        experiment_root
        / f"{run_id}_intraday_market_idiosyncratic_share_no_return_audit.json"
    )
    foundation.atomic_write_json(audit, path)
    return path


def load_diagnostic_preregistration(
    path: Path = DEFAULT_DIAGNOSTIC_PREREGISTRATION,
) -> dict[str, Any]:
    """Load the frozen single-use return diagnostic protocol."""

    path = path.expanduser().resolve()
    _require_file(
        path,
        DIAGNOSTIC_PREREGISTRATION_SHA256,
        "market-idiosyncratic diagnostic protocol",
    )
    spec = research.load_json_record(
        path,
        kind=(
            "a_share_tushare_intraday_market_idiosyncratic_share_"
            "diagnostic_preregistration"
        ),
    )
    factor = spec.get("factor") or {}
    evidence = spec.get("no_return_evidence") or {}
    snapshot = evidence.get("candidate_snapshot") or {}
    audit = evidence.get("ordered_audit") or {}
    coverage = evidence.get("coverage_and_capacity") or {}
    uniqueness = evidence.get("uniqueness") or {}
    holding = spec.get("holding_protocol") or {}
    gates = spec.get("diagnostic_gates") or {}
    decision = spec.get("post_diagnostic_decision") or {}
    boundary = spec.get("research_boundary") or {}
    comparison_medians = uniqueness.get("comparison_medians") or {}
    quality_expectations = {
        "invalid_required_close_rows": 0,
        "insufficient_leave_one_out_peer_rows": 0,
        "constant_stock_return_vector_rows": 29_410,
        "constant_market_return_vector_rows": 0,
        "nonfinite_correlation_rows": 0,
        "endpoint_canonicalized_rows": 0,
        "range_violation_rows": 0,
    }
    if not (
        spec.get("version") == 1
        and spec.get("status")
        == "frozen_after_no_return_coverage_capacity_and_uniqueness_pass_before_first_forward_return_read"
        and factor.get("name") == FACTOR_NAME
        and factor.get("direction") == "higher"
        and factor.get("formula") == FACTOR_FORMULA
        and factor.get("factor_values_observed_before_no_return_preregistration")
        is False
        and factor.get(
            "forward_returns_observed_before_this_diagnostic_preregistration"
        )
        is False
        and (evidence.get("protocol") or {}).get("sha256") == PREREGISTRATION_SHA256
        and snapshot.get("sha256") == CANDIDATE_MANIFEST_SHA256
        and snapshot.get("dataset_sha256") == CANDIDATE_DATASET_SHA256
        and snapshot.get("partitions") == 33_015
        and snapshot.get("rows") == 7_724_498
        and snapshot.get("eligible_rows") == EXPECTED_ELIGIBLE_ROWS
        and all(
            snapshot.get(name) == value for name, value in quality_expectations.items()
        )
        and snapshot.get("market_benchmark_byte_sha256")
        == "5437805f84c5c637904a62664cc3ec677e0155f5a215b0df7c38ed0cc35b88bf"
        and snapshot.get("market_benchmark_frame_sha256")
        == "5412520f379a3d7584f18a0fd5a0b55fd8b68ed3a49d76ff6430a330eee9d4a1"
        and snapshot.get("market_benchmark_trade_dates") == 1_699
        and snapshot.get("market_benchmark_minimum_valid_stock_count") == 3_549
        and audit.get("sha256") == NO_RETURN_AUDIT_SHA256
        and audit.get("forward_return_fields_read") is False
        and coverage.get("quality_listing_eligible_rows") == 1_331_759
        and coverage.get("candidate_eligible_rows_after_quality_and_listing")
        == 1_328_065
        and coverage.get("median_coverage") == 0.9983183851218558
        and coverage.get("p05_coverage") == 0.9933708902303229
        and coverage.get("p05_eligible_names") == 138
        and coverage.get("potential_non_overlapping_three_session_cohorts") == 540
        and coverage.get("observed_calendar_years")
        == [2019, 2020, 2021, 2022, 2023, 2024, 2025]
        and coverage.get("gate_passed") is True
        and uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        == 0.8
        and uniqueness.get("maximum_observed_absolute_median_daily_rank_correlation")
        == 0.2656277856229116
        and tuple(comparison_medians) == COMPARISON_FACTORS
        and uniqueness.get("all_twenty_one_comparisons_passed") is True
        and holding.get("universe") == "buyable_main_chinext"
        and holding.get("minimum_listing_sessions") == research.MIN_LISTING_SESSIONS
        and holding.get("development_start") == "2019-01-01"
        and holding.get("development_end") == "2025-12-31"
        and holding.get("holding_period_trading_days") == 3
        and holding.get("non_overlapping_cohorts") is True
        and holding.get("topk") == 3
        and holding.get("open_cost") == 0.00012
        and holding.get("close_cost") == 0.00062
        and gates.get("minimum_non_overlapping_cohorts") == 200
        and gates.get("minimum_observed_calendar_years") == 5
        and decision.get("same_history_combination_return_evaluation_allowed") is False
        and decision.get("current_scoring_selection_sizing_or_orders_allowed") is False
        and boundary.get("forward_return_fields_read_before_registration") is False
        and boundary.get("training_or_model_fitting_performed") is False
    ):
        raise IntradayMarketIdiosyncraticShareError(
            "market-idiosyncratic diagnostic protocol no longer matches its "
            "frozen definition"
        )
    return spec


def validate_diagnostic_source_chain(
    spec: dict[str, Any], data_root: Path
) -> tuple[dict[str, Any], dict[str, Any], Path, Path, dict[str, Any]]:
    """Reproduce immutable no-return evidence before reading daily prices."""

    no_return = spec["no_return_evidence"]
    protocol_path = _repository_path(str(no_return["protocol"]["path"]))
    _require_file(protocol_path, PREREGISTRATION_SHA256, "no-return protocol")
    snapshot_link = no_return["candidate_snapshot"]
    manifest_path = (data_root / str(snapshot_link["path_below_data_root"])).resolve()
    _require_file(
        manifest_path,
        CANDIDATE_MANIFEST_SHA256,
        "candidate snapshot manifest",
    )
    manifest = research.load_json_record(
        manifest_path,
        kind=("a_share_tushare_intraday_market_idiosyncratic_share_snapshot"),
    )
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    quality = manifest.get("quality") or {}
    benchmark = manifest.get("market_benchmark") or {}
    if not (
        manifest.get("status")
        == "candidate_feature_complete_pending_ordered_no_return_coverage_capacity_and_uniqueness"
        and manifest.get("protocol_sha256") == PREREGISTRATION_SHA256
        and manifest.get("dataset_sha256") == snapshot_link.get("dataset_sha256")
        and manifest.get("eligible_rows") == EXPECTED_ELIGIBLE_ROWS
        and quality.get("invalid_required_close_rows") == 0
        and quality.get("insufficient_leave_one_out_peer_rows") == 0
        and quality.get("constant_stock_return_vector_rows") == 29_410
        and quality.get("constant_market_return_vector_rows") == 0
        and quality.get("nonfinite_correlation_rows") == 0
        and quality.get("endpoint_canonicalized_rows") == 0
        and quality.get("range_violation_rows") == 0
        and benchmark.get("output_byte_sha256")
        == snapshot_link.get("market_benchmark_byte_sha256")
        and benchmark.get("output_frame_sha256")
        == snapshot_link.get("market_benchmark_frame_sha256")
        and benchmark.get("trade_dates") == 1_699
        and benchmark.get("valid_stock_count_minimum") == 3_549
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_close_read") is True
        and manifest.get("source_open_high_low_read") is False
        and manifest.get("source_volume_or_amount_read") is False
        and manifest.get("standalone_09_30_row_excluded_from_formula") is True
        and manifest.get("lunch_boundary_excluded_from_formula") is True
        and manifest.get("leave_one_out_equal_weight_market") is True
        and manifest.get("minimum_leave_one_out_peers") == MINIMUM_LEAVE_ONE_OUT_PEERS
    ):
        raise IntradayMarketIdiosyncraticShareError(
            "candidate snapshot conflicts with the diagnostic preregistration"
        )
    audit_link = no_return["ordered_audit"]
    audit_path = _repository_path(str(audit_link["path"]))
    _require_file(
        audit_path,
        NO_RETURN_AUDIT_SHA256,
        "ordered no-return audit",
    )
    audit = research.load_json_record(
        audit_path,
        kind=("a_share_tushare_intraday_market_idiosyncratic_share_" "no_return_audit"),
    )
    if not (
        audit.get("status") == audit_link.get("status")
        and (audit.get("candidate_snapshot") or {}).get("sha256")
        == CANDIDATE_MANIFEST_SHA256
        and (audit.get("coverage_and_capacity") or {}).get(
            "gate_passed_before_comparison_values"
        )
        is True
        and (audit.get("uniqueness") or {}).get("all_twenty_one_comparisons_passed")
        is True
        and (audit.get("decision") or {}).get(
            "separate_return_diagnostic_preregistration_allowed"
        )
        is True
        and audit.get("daily_price_fields_loaded") == []
        and audit.get("forward_return_fields_read") is False
    ):
        raise IntradayMarketIdiosyncraticShareError(
            "ordered no-return audit does not authorize the frozen diagnostic"
        )
    repository_evidence = validate_repository_chain(load_preregistration())
    for name, link in (
        ("accepted_daily_price_basis", spec["accepted_daily_price_basis"]),
        ("quarterly_quality", spec["quarterly_quality"]),
    ):
        path = _repository_path(str(link["path"]))
        expected = str(link["sha256"])
        _require_file(path, expected, name.replace("_", " "))
        repository_evidence[name] = {
            "path": str(path),
            "sha256": expected,
        }
    quarterly_quality = spec["quarterly_quality"]
    quality_manifest_path = _repository_path(str(quarterly_quality["manifest_path"]))
    _require_file(
        quality_manifest_path,
        str(quarterly_quality["manifest_sha256"]),
        "quarterly quality manifest",
    )
    repository_evidence["quarterly_quality_manifest"] = {
        "path": str(quality_manifest_path),
        "sha256": str(quarterly_quality["manifest_sha256"]),
    }
    for name, link in spec["execution_policies"].items():
        path = _repository_path(str(link["path"]))
        expected = str(link["sha256"])
        _require_file(path, expected, name.replace("_", " "))
        repository_evidence[name] = {
            "path": str(path),
            "sha256": expected,
        }
    return manifest, audit, manifest_path, audit_path, repository_evidence


def require_diagnostic_unconsumed(experiment_root: Path) -> None:
    """Reject a second read of this candidate's historical returns."""

    marker = experiment_root / CONSUMPTION_FILENAME
    if marker.exists():
        raise IntradayMarketIdiosyncraticShareError(
            "market-idiosyncratic historical diagnostic is already consumed: "
            f"{marker}"
        )
    for path in sorted(experiment_root.glob("*_factor_diagnostic.json")):
        record = research.load_json_record(path)
        if record.get("purpose") == DIAGNOSTIC_PURPOSE:
            raise IntradayMarketIdiosyncraticShareError(
                "market-idiosyncratic historical diagnostic already exists: " f"{path}"
            )


def attach_ranked_candidate(
    market: pd.DataFrame,
    candidate: pd.DataFrame,
    diagnostic_spec: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Reuse the accepted ranking path with the candidate's bound field name."""

    prior_factor_name = foundation.FACTOR_NAME
    foundation.FACTOR_NAME = FACTOR_NAME
    try:
        return foundation.attach_ranked_candidate(
            market,
            candidate,
            diagnostic_spec,
        )
    finally:
        foundation.FACTOR_NAME = prior_factor_name


def run_diagnostic(args: argparse.Namespace) -> Path:
    """Consume the only authorized 2019-2025 three-session diagnostic."""

    data_root = Path(args.data_root).expanduser().resolve()
    provider_uri = Path(args.provider_uri).expanduser().resolve()
    fundamentals_path = Path(args.fundamentals).expanduser().resolve()
    experiment_root = Path(args.experiment_root).expanduser().resolve()
    experiment_root.mkdir(parents=True, exist_ok=True)
    require_diagnostic_unconsumed(experiment_root)
    spec = load_diagnostic_preregistration()
    (
        manifest,
        no_return_audit,
        manifest_path,
        audit_path,
        repository_evidence,
    ) = validate_diagnostic_source_chain(spec, data_root)
    verification = verify_snapshot_files(
        manifest,
        manifest_path,
        int(args.verification_workers),
    )
    candidate = load_candidate_frame(manifest_path, manifest)
    holding = spec["holding_protocol"]
    start = str(holding["development_start"])
    end = str(holding["development_end"])
    if candidate["trade_date"].min() < pd.Timestamp(start) or candidate[
        "trade_date"
    ].max() > pd.Timestamp(end):
        raise IntradayMarketIdiosyncraticShareError(
            "candidate feature dates escape the frozen diagnostic window"
        )
    print("loading accepted daily execution and quality context", flush=True)
    price_basis = research.research_price_basis_metadata(provider_uri)
    fundamentals = research.load_fundamentals(fundamentals_path)
    market = research.load_market_execution_data(
        provider_uri,
        start,
        end,
        int(args.batch_size),
    )
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
    ranked, coverage = attach_ranked_candidate(market, candidate, spec)
    del market, candidate
    gc.collect()

    execution_policy = research.load_prospective_execution_policy()
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
        "kind": (
            "a_share_tushare_intraday_market_idiosyncratic_share_"
            "historical_consumption"
        ),
        "status": "historical_forward_return_read_started",
        "started_at": research._timestamp(),
        "diagnostic_preregistration_path": str(
            DEFAULT_DIAGNOSTIC_PREREGISTRATION.resolve()
        ),
        "diagnostic_preregistration_sha256": (DIAGNOSTIC_PREREGISTRATION_SHA256),
        "candidate_manifest_sha256": CANDIDATE_MANIFEST_SHA256,
        "no_return_audit_sha256": NO_RETURN_AUDIT_SHA256,
        "forward_return_fields_read": True,
        "selection_or_promotion_allowed": False,
    }
    research._atomic_write_text(
        marker_path,
        json.dumps(marker, ensure_ascii=False, indent=2) + "\n",
    )
    print(
        "no-return gates reproduced; beginning the single authorized "
        "forward-return read",
        flush=True,
    )
    forward_returns = research.forward_factor_return_frame(
        ranked,
        int(holding["holding_period_trading_days"]),
    )
    summaries = research.summarize_factor_diagnostics(
        forward_returns,
        [FACTOR_NAME],
        hold_days=int(holding["holding_period_trading_days"]),
        topk=int(holding["topk"]),
        open_cost=float(holding["open_cost"]),
        close_cost=float(holding["close_cost"]),
    )
    del forward_returns
    gc.collect()
    summary = (
        summaries[0]
        if summaries
        else research.unavailable_factor_diagnostic_summary(
            FACTOR_NAME,
            int(holding["holding_period_trading_days"]),
        )
    )
    print(
        "simulating normalized and CNY 200,000 execution policies",
        flush=True,
    )
    summary["execution_aware_topk"] = research.simulate_prospective_execution_topk(
        ranked,
        FACTOR_NAME,
        policy=execution_policy,
    )
    summary["pilot_execution_topk"] = research.simulate_pilot_execution_topk(
        ranked,
        FACTOR_NAME,
        execution_policy=execution_policy,
        pilot_policy=pilot_policy,
    )
    del ranked
    gc.collect()
    run_id = research._timestamp()
    diagnostic = {
        "run_id": run_id,
        "status": "completed",
        "purpose": DIAGNOSTIC_PURPOSE,
        "factor_catalog": [FACTOR_NAME],
        "factor_directions": {FACTOR_NAME: "higher"},
        "strategy_timing": {
            "universe": holding["universe"],
            "minimum_listing_sessions": research.MIN_LISTING_SESSIONS,
            "listing_gate_applied_before_cross_sectional_ranking": True,
            "holding_period_trading_days": int(holding["holding_period_trading_days"]),
            "rebalancing": "non_overlapping_every_holding_period",
            "signal_time": (
                "full-session leave-one-out same-minute market-idiosyncratic "
                "share known after signal-session close"
            ),
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
            "effective_date": (
                "strictly next local trading session after announcement_date"
            ),
            "quality_state_semantics": spec["quarterly_quality"][
                "quality_state_semantics"
            ],
            "max_quality_age_days": int(spec["quarterly_quality"]["maximum_age_days"]),
            **quality_counts,
        },
        "minute_factor": {
            "provider": "tushare",
            "frequency": "1m",
            "name": FACTOR_NAME,
            "direction": "higher",
            "formula": spec["factor"]["formula"],
            "candidate_manifest": {
                "path": str(manifest_path),
                "sha256": CANDIDATE_MANIFEST_SHA256,
                "dataset_sha256": manifest["dataset_sha256"],
                "verification": verification,
            },
            "no_return_audit": {
                "path": str(audit_path),
                "sha256": NO_RETURN_AUDIT_SHA256,
                "status": no_return_audit["status"],
            },
            "coverage": coverage,
            "source_fields_read_for_factor": list(RAW_COLUMNS),
            "source_close_read_for_factor": True,
            "source_volume_or_amount_read_for_factor": False,
            "source_open_high_low_read_for_factor": False,
            "standalone_09_30_row_excluded_from_formula": True,
            "lunch_boundary_excluded_from_formula": True,
            "selected_close_count": 240,
            "within_half_adjacent_return_count": 238,
            "leave_one_out_equal_weight_market": True,
            "minimum_leave_one_out_peers": MINIMUM_LEAVE_ONE_OUT_PEERS,
            "ordinary_pearson_with_intercept": True,
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
            "path": str(DEFAULT_DIAGNOSTIC_PREREGISTRATION.resolve()),
            "sha256": DIAGNOSTIC_PREREGISTRATION_SHA256,
            "preregistered_at": spec["preregistered_at"],
            "factor_returns_observed_before_registration": False,
            "single_use_marker": str(marker_path),
        },
        "repository_evidence": repository_evidence,
        "ranking_by_development_rank_ic": [summary],
        "post_diagnostic_decision": spec["post_diagnostic_decision"],
        "forward_return_fields_read": True,
        "selection_or_promotion_allowed": False,
        "limitations": [
            "This is an exploratory 2019-2025 diagnostic, not a pristine "
            "holdout and not investment advice.",
            "Only the higher direction frozen before this return read was "
            "evaluated.",
            "A failure may not be inverted, reformulated, re-windowed, "
            "re-benchmarked, thresholded, or retested on this history.",
            "A pass admits only one factor and cannot satisfy the two-factor "
            "aggregation minimum by itself.",
            "The source stock-day peer pool inherits the repository's "
            "current-listing-derived universe and is not survivorship-free.",
            "Daily execution bars cannot reconstruct exact queue priority, "
            "partial fills, or realized market impact.",
        ],
    }
    destination = experiment_root / f"{run_id}_factor_diagnostic.json"
    research._atomic_write_text(
        destination,
        json.dumps(
            diagnostic,
            ensure_ascii=False,
            indent=2,
            default=research._json_default,
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
        marker_path,
        json.dumps(marker, ensure_ascii=False, indent=2) + "\n",
    )
    return destination


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
    diagnose_parser = subparsers.add_parser(
        "diagnose",
        help="Consume the single preregistered three-session diagnostic",
    )
    diagnose_parser.add_argument("--data-root", type=Path, required=True)
    diagnose_parser.add_argument(
        "--provider-uri",
        type=Path,
        default=REPO_ROOT / "data/qlib/cn_a_share",
    )
    diagnose_parser.add_argument(
        "--fundamentals",
        type=Path,
        default=(REPO_ROOT / "data/raw/a_share/fundamentals/quarterly_quality.parquet"),
    )
    diagnose_parser.add_argument(
        "--experiment-root",
        type=Path,
        default=REPO_ROOT / "data/experiments/short_horizon",
    )
    diagnose_parser.add_argument("--batch-size", type=int, default=250)
    diagnose_parser.add_argument(
        "--verification-workers",
        type=int,
        default=8,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "build":
        path = build_snapshot(data_root=args.data_root, workers=args.workers)
    elif args.command == "audit":
        path = run_no_return_audit(
            data_root=args.data_root,
            experiment_root=args.experiment_root,
            workers=args.workers,
        )
    else:
        path = run_diagnostic(args)
    print(json.dumps({"status": "ok", "path": str(path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
