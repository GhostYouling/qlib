#!/usr/bin/env python3
"""Build and audit the preregistered opening-auction amount share.

The candidate reads only identity and CNY amount from the immutable Tushare
one-minute snapshot.  It divides the separately timestamped 09:30 amount by
the amount summed across the exact 241-row source grid.  Candidate coverage
and capacity are evaluated before any terminal-factor comparison is loaded.
Build and audit never request provider data or read daily prices or returns;
diagnose permits one fingerprint-bound return read after a separate protocol.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import gc
import hashlib
import json
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow.dataset as pa_dataset


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_tushare_intraday_market_idiosyncratic_share as previous  # noqa: E402


foundation = previous.foundation
research = previous.research
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREGISTRATION = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_intraday_opening_auction_amount_share_no_return_preregistration.json"
)
PREREGISTRATION_SHA256 = (
    "3aca85681061bedf7dc049f21e6bfcfaa520f9478938bd007b3d6666814db84b"
)
DEFAULT_DIAGNOSTIC_PREREGISTRATION = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_intraday_opening_auction_amount_share_diagnostic_preregistration.json"
)
DIAGNOSTIC_PREREGISTRATION_SHA256 = (
    "69c18050be829c73c09c988a5d4f37795a310b678b691113a989a94b78b2c1c9"
)
DEFAULT_MECHANISM_AUDIT = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_intraday_opening_auction_amount_share_mechanism_overlap_reaudit_20260723.json"
)
MECHANISM_AUDIT_SHA256 = (
    "f3ada152a88df413e45826ea4a72ced7cd63f043f45fbcd90c0e431b8aa636a7"
)
DEFAULT_TERMINAL_RECORD = (
    REPO_ROOT
    / "docs"
    / "a_share_tushare_intraday_opening_auction_amount_share_research_record.json"
)
TERMINAL_RECORD_SHA256 = (
    "b70a8ec547bdc36db408adc86b809456caac9a774d074de913369b3349899abd"
)
DIAGNOSTIC_SHA256 = "3c801cf4e67d4e6c523d3ea63cc19852243a6183e4a4cc733a2b2584b20a559e"
STABILITY_AUDIT_SHA256 = (
    "cebcc7bb447c14690d951e659fb0a2857b5c2d263a95fe13eee3613e4a9bf855"
)
TOPK_AUDIT_SHA256 = "4c64faab230221687e8a93a31c5559f8fa4df432b63275d47e5b0cf274ce85f3"
CONSUMPTION_MARKER_SHA256 = (
    "c99e094132adf754c4066414ce782e2e56d52d2f4d4fb70c003fde6d5399c09e"
)
DEFAULT_CURRENT_STATUS = (
    REPO_ROOT / "docs" / "a_share_three_day_iteration_status_20260721.json"
)
CURRENT_STATUS_SHA256 = (
    "14e8edaf98c7f94a10f0c63e64d8af1d6e3bb1b45dac3c3bb9aabdf2cb83e2b1"
)
PREVIOUS_TERMINAL_RECORD_SHA256 = previous.TERMINAL_RECORD_SHA256
PREVIOUS_MANIFEST_SHA256 = previous.CANDIDATE_MANIFEST_SHA256
PREVIOUS_DATASET_SHA256 = previous.CANDIDATE_DATASET_SHA256
RAW_MANIFEST_SHA256 = foundation.RAW_MANIFEST_SHA256
JOINT_MANIFEST_SHA256 = foundation.JOINT_MANIFEST_SHA256
SOURCE_RUN_ID = foundation.SOURCE_RUN_ID
OUTPUT_RUN_ID = f"{SOURCE_RUN_ID}_intraday_opening_auction_amount_share_v1"
FACTOR_NAME = "intraday_opening_auction_amount_share_241m"
FACTOR_FORMULA = "amount_09_30 / sum(amount over the exact 241-row source grid)"
DIAGNOSTIC_PURPOSE = (
    "single_preregistered_intraday_opening_auction_amount_share_"
    "three_session_diagnostic"
)
CONSUMPTION_FILENAME = (
    "intraday_opening_auction_amount_share_241m_historical_consumption.json"
)
COMPARISON_FACTORS = (*previous.COMPARISON_FACTORS, previous.FACTOR_NAME)
COMPARISON_DIRECTIONS = (*previous.COMPARISON_DIRECTIONS, "higher")
RAW_COLUMNS = ("datetime", "symbol", "provider", "amount")
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
SOURCE_MINUTE_CODES = (9 * 60 + 30, *previous.CONTINUOUS_MINUTE_CODES)
SOURCE_MINUTE_CODE_SET = frozenset(SOURCE_MINUTE_CODES)
ENDPOINT_TOLERANCE = 1e-12

# Bound only after the deterministic build publishes one immutable snapshot.
CANDIDATE_MANIFEST_SHA256 = (
    "cb6acb3dcbad2ca459ac2f11ea80364593543adc852bf82ea3f177ae58154580"
)
CANDIDATE_DATASET_SHA256 = (
    "9e7cd5b724347bc5193970ed2f23fa8ff1ce1e58f0c460ba46891a86538f8e65"
)
EXPECTED_ELIGIBLE_ROWS = 7_724_498
EXPECTED_INVALID_REQUIRED_AMOUNT_ROWS = 0
EXPECTED_NONPOSITIVE_TOTAL_AMOUNT_ROWS = 0
NO_RETURN_AUDIT_SHA256 = (
    "fb904d0cac194491eff119ad409a63b30603bd8225206284dad391136e34c979"
)


class IntradayOpeningAuctionAmountShareError(RuntimeError):
    """Raised when a frozen source, factor, or no-return gate is violated."""


def _repository_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise IntradayOpeningAuctionAmountShareError(f"{label} is missing: {path}")
    observed = foundation.file_digest(path)
    if observed != expected_sha256:
        raise IntradayOpeningAuctionAmountShareError(
            f"{label} fingerprint changed: expected {expected_sha256}, got {observed}"
        )


def load_terminal_record_if_present() -> dict[str, Any] | None:
    """Validate and return the immutable terminal record when it exists."""

    if not DEFAULT_TERMINAL_RECORD.exists():
        return None
    _require_file(
        DEFAULT_TERMINAL_RECORD,
        TERMINAL_RECORD_SHA256,
        "opening-auction terminal record",
    )
    record = research.load_json_record(
        DEFAULT_TERMINAL_RECORD,
        kind=(
            "a_share_tushare_intraday_opening_auction_amount_share_" "research_record"
        ),
    )
    artifacts = record.get("historical_artifacts") or {}
    result = record.get("return_results") or {}
    decision = record.get("decision") or {}
    expected_artifacts = {
        "diagnostic": DIAGNOSTIC_SHA256,
        "stability_audit": STABILITY_AUDIT_SHA256,
        "topk_viability_audit": TOPK_AUDIT_SHA256,
        "single_use_consumption_marker": CONSUMPTION_MARKER_SHA256,
    }
    for name, expected in expected_artifacts.items():
        link = artifacts.get(name) or {}
        path = _repository_path(str(link.get("path", "")))
        _require_file(path, expected, name.replace("_", " "))
        if link.get("sha256") != expected:
            raise IntradayOpeningAuctionAmountShareError(
                f"terminal record has the wrong {name} fingerprint"
            )
    if not (
        record.get("status")
        == "terminal_rejected_at_association_stability_and_executable_topk_gates"
        and (record.get("factor") or {}).get("name") == FACTOR_NAME
        and (record.get("source_chain") or {})
        .get("candidate_manifest", {})
        .get("sha256")
        == CANDIDATE_MANIFEST_SHA256
        and (record.get("ordered_protocol") or {})
        .get("no_return_audit", {})
        .get("sha256")
        == NO_RETURN_AUDIT_SHA256
        and (record.get("ordered_protocol") or {})
        .get("diagnostic_preregistration", {})
        .get("sha256")
        == DIAGNOSTIC_PREREGISTRATION_SHA256
        and result.get("cohorts") == 539
        and result.get("mean_rank_ic") == -0.0033939055201436417
        and result.get("association_stability_gate_passed") is False
        and result.get("topk_viability_gate_passed") is False
        and result.get("dual_gate_passed") is False
        and decision.get("terminally_reject_exact_factor_direction") is True
        and decision.get("aggregation_candidate_added") is False
        and decision.get("current_scoring_allowed") is False
    ):
        raise IntradayOpeningAuctionAmountShareError(
            "opening-auction terminal record no longer matches its frozen result"
        )
    return record


def empty_output_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="object"),
            "provider": pd.Series(dtype="object"),
            FACTOR_NAME: pd.Series(dtype="float64"),
            f"{FACTOR_NAME}_eligible": pd.Series(dtype="bool"),
        }
    ).loc[:, OUTPUT_COLUMNS]


def load_preregistration(
    path: Path = DEFAULT_PREREGISTRATION,
) -> dict[str, Any]:
    """Load and enforce the protocol frozen before candidate values."""

    path = path.expanduser().resolve()
    _require_file(path, PREREGISTRATION_SHA256, "opening-auction protocol")
    spec = research.load_json_record(
        path,
        kind=(
            "a_share_tushare_intraday_opening_auction_amount_share_"
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
    prior_manifest = chain.get("market_idiosyncratic_share_comparison_manifest") or {}
    forbidden = {
        "open",
        "high",
        "low",
        "close",
        "volume",
        "any_daily_price",
        "any_forward_return",
    }
    if not (
        spec.get("version") == 1
        and spec.get("status")
        == "frozen_before_candidate_factor_values_comparison_values_or_forward_returns"
        and current.get("sha256") == CURRENT_STATUS_SHA256
        and current.get("status")
        == "aggregation_blocked_after_intraday_market_idiosyncratic_share_terminal_rejection_zero_dual_gate_factors"
        and current.get("terminal_mechanism_count_before_this_candidate") == 46
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
        and grid.get("opening_auction_bar_end") == "09:30"
        and grid.get("opening_auction_rows") == 1
        and grid.get("continuous_rows") == 240
        and grid.get("total_rows") == 241
        and grid.get("standalone_09_30_amount_in_numerator") is True
        and grid.get("standalone_09_30_amount_in_denominator") is True
        and grid.get("continuous_amounts_in_denominator") is True
        and grid.get("source_rows_merged") is False
        and candidate.get("formula") == FACTOR_FORMULA
        and validity.get("all_241_amount_values_finite_and_nonnegative") is True
        and validity.get("strictly_positive_full_session_amount") is True
        and validity.get("zero_opening_auction_amount_policy") == "valid_zero"
        and validity.get("allowed_closed_interval") == [0, 1]
        and validity.get("endpoint_canonicalization_tolerance") == ENDPOINT_TOLERANCE
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
        and uniqueness.get("all_twenty_two_comparisons_must_pass") is True
        and boundary.get("candidate_factor_values_observed_before_registration")
        is False
        and boundary.get(
            "terminal_factor_comparison_values_observed_for_this_candidate_before_registration"
        )
        is False
        and boundary.get("daily_price_fields_read_before_registration") is False
        and boundary.get("forward_return_fields_read_before_registration") is False
    ):
        raise IntradayOpeningAuctionAmountShareError(
            "opening-auction protocol no longer matches its frozen definition"
        )
    return spec


def validate_repository_chain(spec: dict[str, Any]) -> dict[str, Any]:
    """Validate the current append-only state and immediate predecessor."""

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
        CURRENT_STATUS_SHA256,
        "authoritative three-day research state",
    )
    state = research._load_three_day_iteration_status_20260721(DEFAULT_CURRENT_STATUS)
    summary = state.get("post_frontier_summary") or {}
    terminal = list(state.get("post_frontier_terminal_mechanisms") or [])
    decision = state.get("decision") or {}
    if not (
        state.get("status")
        == "aggregation_blocked_after_intraday_market_idiosyncratic_share_terminal_rejection_zero_dual_gate_factors"
        and summary.get("terminal_mechanism_count") == 46
        and len(terminal) == 46
        and terminal[-1].get("mechanism")
        == "tushare_intraday_market_idiosyncratic_share_238m"
        and (terminal[-1].get("record") or {}).get("sha256")
        == PREVIOUS_TERMINAL_RECORD_SHA256
        and summary.get("admitted_factor_count") == 0
        and summary.get("aggregation_candidate_count") == 0
        and all(
            decision.get(field) is False
            for field in (
                "aggregation_allowed",
                "current_scoring_allowed",
                "selection_allowed",
                "sizing_allowed",
                "orders_allowed",
                "level2_intake_justified",
            )
        )
    ):
        raise IntradayOpeningAuctionAmountShareError(
            "authoritative three-day state changed after preregistration"
        )
    if previous.load_terminal_record_if_present() is None:
        raise IntradayOpeningAuctionAmountShareError(
            "market-idiosyncratic terminal record is required"
        )
    evidence["authoritative_current_research_state"] = {
        "path": str(DEFAULT_CURRENT_STATUS.resolve()),
        "sha256": CURRENT_STATUS_SHA256,
        "terminal_mechanism_count": 46,
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


def _validate_previous_manifest(
    spec: dict[str, Any],
    data_root: Path,
) -> tuple[dict[str, Any], Path]:
    link = spec["source_chain"]["market_idiosyncratic_share_comparison_manifest"]
    path = (data_root / str(link["path_below_data_root"])).resolve()
    _require_file(path, PREVIOUS_MANIFEST_SHA256, "market-idiosyncratic manifest")
    manifest = research.load_json_record(
        path, kind="a_share_tushare_intraday_market_idiosyncratic_share_snapshot"
    )
    previous._validate_snapshot_manifest(
        manifest,
        require_fingerprint_constants=True,
    )
    if manifest.get("dataset_sha256") != PREVIOUS_DATASET_SHA256:
        raise IntradayOpeningAuctionAmountShareError(
            "market-idiosyncratic comparison dataset changed"
        )
    return manifest, path


def validate_external_chain(spec: dict[str, Any], data_root: Path) -> tuple[Any, ...]:
    chain = previous.validate_external_chain(previous.load_preregistration(), data_root)
    prior_manifest, prior_path = _validate_previous_manifest(spec, data_root)
    return (*chain, prior_manifest, prior_path)


def compute_partition_frame(
    raw: pd.DataFrame,
    base: pd.DataFrame,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Compute the frozen 09:30 amount share without price or outcome data."""

    empty_quality = {
        "base_rows": 0,
        "eligible_rows": 0,
        "invalid_required_amount_rows": 0,
        "nonpositive_total_amount_rows": 0,
        "endpoint_canonicalized_rows": 0,
        "range_violation_rows": 0,
    }
    if tuple(raw.columns) != RAW_COLUMNS:
        raise IntradayOpeningAuctionAmountShareError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    base_work = previous._normalized_base(base, symbol)
    if base_work.empty:
        return empty_output_frame(), empty_quality
    symbol = symbol.upper()
    if raw.empty:
        raise IntradayOpeningAuctionAmountShareError(
            f"raw source is empty for nonempty base partition {symbol}"
        )
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["amount"] = pd.to_numeric(work["amount"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise IntradayOpeningAuctionAmountShareError(
            f"raw identity or timestamp violation for {symbol}"
        )
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise IntradayOpeningAuctionAmountShareError(
            f"every source stock-day must retain the exact 241-row grid for {symbol}"
        )
    observed_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(value) for value in values))
    if not observed_codes.eq(SOURCE_MINUTE_CODE_SET).all():
        raise IntradayOpeningAuctionAmountShareError(
            f"source minute grid changed for {symbol}"
        )
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise IntradayOpeningAuctionAmountShareError(
            f"joint-clean base dates do not match raw dates for {symbol}"
        )
    work["minute_code"] = pd.Categorical(
        work["minute_code"],
        categories=SOURCE_MINUTE_CODES,
        ordered=True,
    )
    work = work.sort_values(["trade_date", "minute_code"], kind="stable")
    amounts = work["amount"].to_numpy(dtype=float).reshape(-1, 241)
    required_valid = np.isfinite(amounts).all(axis=1) & (amounts >= 0.0).all(axis=1)
    totals = np.where(required_valid[:, None], amounts, 0.0).sum(axis=1)
    positive_total = required_valid & np.isfinite(totals) & (totals > 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        values = amounts[:, 0] / totals
    finite = np.isfinite(values)
    low_near = (values < 0.0) & (values >= -ENDPOINT_TOLERANCE)
    high_near = (values > 1.0) & (values <= 1.0 + ENDPOINT_TOLERANCE)
    canonicalized = positive_total & finite & (low_near | high_near)
    values = np.where(low_near, 0.0, np.where(high_near, 1.0, values))
    in_range = (values >= 0.0) & (values <= 1.0)
    eligible = positive_total & finite & in_range
    output = pd.DataFrame(
        {
            "trade_date": base_work["trade_date"],
            "symbol": symbol,
            "provider": "tushare",
            FACTOR_NAME: np.where(eligible, values, np.nan),
            f"{FACTOR_NAME}_eligible": eligible,
        }
    ).loc[:, OUTPUT_COLUMNS]
    return output, {
        "base_rows": int(len(output)),
        "eligible_rows": int(eligible.sum()),
        "invalid_required_amount_rows": int((~required_valid).sum()),
        "nonpositive_total_amount_rows": int((required_valid & ~positive_total).sum()),
        "endpoint_canonicalized_rows": int(canonicalized.sum()),
        "range_violation_rows": int((positive_total & finite & ~in_range).sum()),
    }


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived/a_share/rich/tushare/minute_intraday_opening_auction_amount_share"
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
        record.get("kind")
        == "a_share_tushare_intraday_opening_auction_amount_share_partition"
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
        raise IntradayOpeningAuctionAmountShareError(
            f"completed candidate checkpoint changed: {paths.partial_sidecar}"
        )
    output = pd.read_parquet(paths.partial_data)
    if len(output) != int(record.get("rows", -1)) or foundation.frame_digest(
        output
    ) != record.get("output_frame_sha256"):
        raise IntradayOpeningAuctionAmountShareError(
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
        raise IntradayOpeningAuctionAmountShareError(
            f"raw partition changed: {raw_path}"
        )
    if foundation.file_digest(base_path) != joint_record.get("output_byte_sha256"):
        raise IntradayOpeningAuctionAmountShareError(
            f"joint-base partition changed: {base_path}"
        )
    raw = pd.read_parquet(raw_path, columns=list(RAW_COLUMNS))
    base = pd.read_parquet(base_path, columns=["trade_date", "symbol"])
    output, quality = compute_partition_frame(
        raw,
        base,
        symbol=str(joint_record["symbol"]),
    )
    foundation.atomic_write_frame(output, paths.partial_data)
    record = {
        "schema_version": 1,
        "kind": "a_share_tushare_intraday_opening_auction_amount_share_partition",
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
        "minute_amount_fields_read": ["amount"],
        "minute_price_or_volume_fields_read": [],
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
        pairs,
        key=lambda pair: int(pair[1]["year"]),
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
    counter_names = (
        "invalid_required_amount_rows",
        "nonpositive_total_amount_rows",
        "endpoint_canonicalized_rows",
        "range_violation_rows",
    )
    if not (
        manifest.get("kind")
        == "a_share_tushare_intraday_opening_auction_amount_share_snapshot"
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
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_amount_read") is True
        and manifest.get("source_price_or_volume_read") is False
        and manifest.get("standalone_09_30_amount_in_numerator") is True
        and manifest.get("all_241_amounts_in_denominator") is True
        and manifest.get("source_rows_merged") is False
        and manifest.get("zero_09_30_amount_is_valid_zero") is True
        and manifest.get("factor_formula") == FACTOR_FORMULA
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("forward_return_fields_read") is False
    ):
        raise IntradayOpeningAuctionAmountShareError(
            "opening-auction snapshot identity is rejected"
        )
    if require_fingerprint_constants and not (
        CANDIDATE_MANIFEST_SHA256
        and CANDIDATE_DATASET_SHA256
        and EXPECTED_ELIGIBLE_ROWS > 0
        and manifest.get("dataset_sha256") == CANDIDATE_DATASET_SHA256
        and manifest.get("eligible_rows") == EXPECTED_ELIGIBLE_ROWS
        and quality.get("invalid_required_amount_rows")
        == EXPECTED_INVALID_REQUIRED_AMOUNT_ROWS
        and quality.get("nonpositive_total_amount_rows")
        == EXPECTED_NONPOSITIVE_TOTAL_AMOUNT_ROWS
    ):
        raise IntradayOpeningAuctionAmountShareError(
            "candidate fingerprint and aggregate constants are not bound"
        )


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    """Build all hash-resumable candidate partitions without provider access."""

    if workers < 1 or workers > 8:
        raise ValueError("--workers must be between 1 and 8")
    data_root = data_root.expanduser().resolve()
    spec = load_preregistration()
    final_root = output_root(data_root)
    partial_root = final_root.parent / f".{OUTPUT_RUN_ID}.partial"
    final_manifest = final_root / "snapshot_manifest.json"
    if final_root.exists():
        if not final_manifest.is_file():
            raise IntradayOpeningAuctionAmountShareError(
                f"published candidate root has no manifest: {final_root}"
            )
        if not CANDIDATE_MANIFEST_SHA256:
            raise IntradayOpeningAuctionAmountShareError(
                "bind the published candidate manifest before reusing it"
            )
        _require_file(
            final_manifest,
            CANDIDATE_MANIFEST_SHA256,
            "published opening-auction manifest",
        )
        manifest = research.load_json_record(final_manifest)
        _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
        load_terminal_record_if_present()
        return final_manifest
    repository_evidence = validate_repository_chain(spec)
    chain = validate_external_chain(spec, data_root)
    raw, joint, raw_manifest_path, joint_manifest_path = chain[:4]
    if shutil.disk_usage(data_root).free < 5 * 1024**3:
        raise IntradayOpeningAuctionAmountShareError(
            "external data root has less than 5 GiB free"
        )
    _, joint_by_key, by_symbol = previous._partition_maps(raw, joint)
    lock_path = (
        data_root / ".a_share_tushare_intraday_opening_auction_amount_share.lock"
    )
    with foundation.ProcessLock(lock_path):
        partial_root.mkdir(parents=True, exist_ok=True)
        all_records: list[dict[str, Any]] = []
        eligible_dates: Counter[str] = Counter()
        resumed = 0
        completed_symbols = 0
        print(
            f"building {len(joint_by_key):,} opening-auction partitions "
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
                    if completed_symbols % 50 == 0 or completed_symbols == len(
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
            raise IntradayOpeningAuctionAmountShareError(
                "not every source partition produced a candidate checkpoint"
            )
        _require_file(raw_manifest_path, RAW_MANIFEST_SHA256, "raw minute manifest")
        _require_file(
            joint_manifest_path,
            JOINT_MANIFEST_SHA256,
            "joint-clean manifest",
        )
        all_records.sort(key=lambda item: (str(item["symbol"]), int(item["year"])))
        quality = _aggregate_quality(all_records)
        dataset_payload = "\n".join(
            f"{item['symbol']}|{item['year']}|{item['output_byte_sha256']}"
            for item in all_records
        ).encode("utf-8")
        manifest = {
            "schema_version": 1,
            "kind": "a_share_tushare_intraday_opening_auction_amount_share_snapshot",
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
            "files": all_records,
            "partitions": len(all_records),
            "rows": int(quality.get("base_rows", -1)),
            "eligible_rows": int(quality.get("eligible_rows", -1)),
            "quality": quality,
            "eligible_names_by_date": dict(sorted(eligible_dates.items())),
            "source_fields_read": list(RAW_COLUMNS),
            "source_amount_read": True,
            "source_price_or_volume_read": False,
            "standalone_09_30_amount_in_numerator": True,
            "all_241_amounts_in_denominator": True,
            "source_rows_merged": False,
            "zero_09_30_amount_is_valid_zero": True,
            "daily_price_fields_read": [],
            "comparison_factor_values_read": False,
            "forward_return_fields_read": False,
            "provider_request_issued": False,
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
        raise IntradayOpeningAuctionAmountShareError(
            "candidate snapshot partition count changed"
        )
    partition_root = (manifest_path.parent / "partitions").resolve()

    def verify(record: dict[str, Any]) -> tuple[int, int, int]:
        path = Path(str(record["path"])).resolve()
        try:
            path.relative_to(partition_root)
        except ValueError as exc:
            raise IntradayOpeningAuctionAmountShareError(
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
        raise IntradayOpeningAuctionAmountShareError(
            "candidate snapshot aggregate counts changed"
        )
    return {
        "partitions_verified": len(records),
        "rows_verified": rows,
        "eligible_rows_verified": eligible,
        "partition_bytes_verified": byte_count,
    }


def load_candidate_frame(
    manifest_path: Path,
    manifest: dict[str, Any],
) -> pd.DataFrame:
    dataset = pa_dataset.dataset(
        str(manifest_path.parent / "partitions"),
        format="parquet",
    )
    table = dataset.to_table(columns=list(OUTPUT_COLUMNS), use_threads=True)
    frame = table.to_pandas(split_blocks=True, self_destruct=True)
    del table, dataset
    gc.collect()
    if len(frame) != int(manifest.get("rows", -1)):
        raise IntradayOpeningAuctionAmountShareError(
            "candidate frame row count changed"
        )
    frame["trade_date"] = pd.to_datetime(
        frame["trade_date"],
        errors="coerce",
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
        raise IntradayOpeningAuctionAmountShareError(
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


def uniqueness_audit(
    candidate_quality: pd.DataFrame,
    chain: tuple[Any, ...],
    spec: dict[str, Any],
    workers: int,
) -> dict[str, Any]:
    """Evaluate all 22 comparisons serially with bounded memory."""

    print(
        "coverage passed; loading twenty-two terminal comparisons serially",
        flush=True,
    )
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    candidate = candidate_quality[["trade_date", "symbol", FACTOR_NAME]].copy()
    candidate_keys = previous._compact_stock_day_keys(
        candidate["trade_date"],
        candidate["symbol"],
    )
    candidate_values = pd.to_numeric(
        candidate[FACTOR_NAME],
        errors="coerce",
    ).to_numpy(dtype=float)
    order = np.argsort(candidate_keys, kind="stable")
    candidate_keys = candidate_keys[order]
    candidate_values = candidate_values[order]
    if (
        len(np.unique(candidate_keys)) != len(candidate_keys)
        or not np.isfinite(candidate_values).all()
    ):
        raise IntradayOpeningAuctionAmountShareError(
            "candidate quality keys or values changed before uniqueness"
        )
    del candidate, candidate_quality, order
    gc.collect()
    results: list[dict[str, Any]] = []
    verifications: dict[str, Any] = {}

    joint_manifest_path = Path(chain[3])
    base_factors = COMPARISON_FACTORS[:4]
    base_values = previous._load_filtered_comparison_values(
        joint_manifest_path.parent / "partitions",
        base_factors,
        candidate_keys,
    )
    for factor, direction in zip(
        base_factors,
        COMPARISON_DIRECTIONS[:4],
        strict=True,
    ):
        results.append(
            previous._aligned_comparison_result(
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
        raise IntradayOpeningAuctionAmountShareError(
            "comparison manifest order changed"
        )
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
        print(f"serial uniqueness comparison {index}/22: {factor}", flush=True)
        verifications[factor] = previous._verify_comparison_snapshot_outputs(
            manifest,
            manifest_path,
            workers,
        )
        values = previous._load_filtered_comparison_values(
            manifest_path.parent / "partitions",
            [factor],
            candidate_keys,
        )[factor]
        results.append(
            previous._aligned_comparison_result(
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
        "all_twenty_two_comparisons_passed": bool(
            len(results) == 22 and all(item["gate_passed"] for item in results)
        ),
    }


def _find_existing_audit(
    experiment_root: Path,
    manifest_sha256: str,
) -> Path | None:
    for path in sorted(
        experiment_root.glob(
            "*_intraday_opening_auction_amount_share_no_return_audit.json"
        )
    ):
        record = research.load_json_record(path)
        if (
            record.get("kind")
            == "a_share_tushare_intraday_opening_auction_amount_share_no_return_audit"
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
    """Run coverage/capacity before loading the 22 comparisons."""

    if not CANDIDATE_MANIFEST_SHA256:
        raise IntradayOpeningAuctionAmountShareError(
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
        "opening-auction candidate manifest",
    )
    manifest = research.load_json_record(manifest_path)
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    manifest_sha256 = foundation.file_digest(manifest_path)
    existing = _find_existing_audit(experiment_root, manifest_sha256)
    if existing is not None:
        _require_file(existing, NO_RETURN_AUDIT_SHA256, "ordered no-return audit")
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
        "all_twenty_two_comparisons_passed": False,
        "comparisons": [],
    }
    if coverage["gate_passed_before_comparison_values"]:
        uniqueness = uniqueness_audit(candidate_quality, chain, spec, workers)
    del candidate_quality
    gc.collect()
    passed = bool(
        coverage["gate_passed_before_comparison_values"]
        and uniqueness["all_twenty_two_comparisons_passed"]
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
        "kind": (
            "a_share_tushare_intraday_opening_auction_amount_share_no_return_audit"
        ),
        "status": status,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "purpose": (
            "ordered_candidate_coverage_capacity_then_twenty_two_terminal_"
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
            "market_idiosyncratic_share_manifest_sha256": (PREVIOUS_MANIFEST_SHA256),
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
        "minute_amount_fields_loaded": ["amount"],
        "minute_price_or_volume_fields_loaded": [],
        "comparison_fields_loaded": (
            list(COMPARISON_FACTORS)
            if uniqueness["comparison_values_loaded_after_coverage_pass"]
            else []
        ),
        "daily_price_fields_loaded": [],
        "forward_return_fields_read": False,
        "provider_request_issued": False,
        "training_or_model_fitting_performed": False,
        "investment_advice": False,
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = (
        experiment_root
        / f"{run_id}_intraday_opening_auction_amount_share_no_return_audit.json"
    )
    foundation.atomic_write_json(audit, path)
    return path


def load_diagnostic_preregistration(
    path: Path = DEFAULT_DIAGNOSTIC_PREREGISTRATION,
) -> dict[str, Any]:
    """Load and validate the frozen single-use return diagnostic protocol."""

    path = path.expanduser().resolve()
    _require_file(
        path,
        DIAGNOSTIC_PREREGISTRATION_SHA256,
        "opening-auction diagnostic protocol",
    )
    spec = research.load_json_record(
        path,
        kind=(
            "a_share_tushare_intraday_opening_auction_amount_share_"
            "diagnostic_preregistration"
        ),
    )
    factor = spec.get("factor") or {}
    evidence = spec.get("no_return_evidence") or {}
    snapshot = evidence.get("candidate_snapshot") or {}
    audit = evidence.get("ordered_audit") or {}
    coverage = evidence.get("coverage_and_capacity") or {}
    uniqueness = evidence.get("uniqueness") or {}
    comparison_medians = uniqueness.get("comparison_medians") or {}
    holding = spec.get("holding_protocol") or {}
    gates = spec.get("diagnostic_gates") or {}
    decision = spec.get("post_diagnostic_decision") or {}
    boundary = spec.get("research_boundary") or {}
    quality_expectations = {
        "invalid_required_amount_rows": 0,
        "nonpositive_total_amount_rows": 0,
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
        and audit.get("sha256") == NO_RETURN_AUDIT_SHA256
        and audit.get("forward_return_fields_read") is False
        and coverage.get("quality_listing_eligible_rows") == 1_331_759
        and coverage.get("candidate_eligible_rows_after_quality_and_listing")
        == 1_330_171
        and coverage.get("median_coverage") == 0.9994517542211769
        and coverage.get("p05_coverage") == 0.9956886515772271
        and coverage.get("p05_eligible_names") == 138
        and coverage.get("potential_non_overlapping_three_session_cohorts") == 540
        and coverage.get("observed_calendar_years")
        == [2019, 2020, 2021, 2022, 2023, 2024, 2025]
        and coverage.get("gate_passed") is True
        and uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        == 0.8
        and uniqueness.get("maximum_observed_absolute_median_daily_rank_correlation")
        == 0.3034674493047393
        and tuple(comparison_medians) == COMPARISON_FACTORS
        and uniqueness.get("all_twenty_two_comparisons_passed") is True
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
        raise IntradayOpeningAuctionAmountShareError(
            "opening-auction diagnostic protocol no longer matches its "
            "frozen definition"
        )
    return spec


def validate_diagnostic_source_chain(
    spec: dict[str, Any],
    data_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], Path, Path, dict[str, Any]]:
    """Reproduce the immutable no-return evidence before daily prices."""

    no_return = spec["no_return_evidence"]
    protocol_path = _repository_path(str(no_return["protocol"]["path"]))
    _require_file(protocol_path, PREREGISTRATION_SHA256, "no-return protocol")
    snapshot_link = no_return["candidate_snapshot"]
    manifest_path = (data_root / str(snapshot_link["path_below_data_root"])).resolve()
    _require_file(
        manifest_path,
        CANDIDATE_MANIFEST_SHA256,
        "opening-auction candidate manifest",
    )
    manifest = research.load_json_record(
        manifest_path,
        kind=("a_share_tushare_intraday_opening_auction_amount_share_snapshot"),
    )
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    quality = manifest.get("quality") or {}
    if not (
        manifest.get("status")
        == "candidate_feature_complete_pending_ordered_no_return_coverage_capacity_and_uniqueness"
        and manifest.get("protocol_sha256") == PREREGISTRATION_SHA256
        and manifest.get("dataset_sha256") == snapshot_link.get("dataset_sha256")
        and manifest.get("eligible_rows") == EXPECTED_ELIGIBLE_ROWS
        and quality.get("invalid_required_amount_rows") == 0
        and quality.get("nonpositive_total_amount_rows") == 0
        and quality.get("endpoint_canonicalized_rows") == 0
        and quality.get("range_violation_rows") == 0
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_amount_read") is True
        and manifest.get("source_price_or_volume_read") is False
        and manifest.get("standalone_09_30_amount_in_numerator") is True
        and manifest.get("all_241_amounts_in_denominator") is True
        and manifest.get("zero_09_30_amount_is_valid_zero") is True
    ):
        raise IntradayOpeningAuctionAmountShareError(
            "candidate snapshot conflicts with the diagnostic preregistration"
        )
    audit_link = no_return["ordered_audit"]
    audit_path = _repository_path(str(audit_link["path"]))
    _require_file(audit_path, NO_RETURN_AUDIT_SHA256, "ordered no-return audit")
    audit = research.load_json_record(
        audit_path,
        kind=(
            "a_share_tushare_intraday_opening_auction_amount_share_" "no_return_audit"
        ),
    )
    if not (
        audit.get("status") == audit_link.get("status")
        and (audit.get("candidate_snapshot") or {}).get("sha256")
        == CANDIDATE_MANIFEST_SHA256
        and (audit.get("coverage_and_capacity") or {}).get(
            "gate_passed_before_comparison_values"
        )
        is True
        and (audit.get("uniqueness") or {}).get("all_twenty_two_comparisons_passed")
        is True
        and (audit.get("decision") or {}).get(
            "separate_return_diagnostic_preregistration_allowed"
        )
        is True
        and audit.get("daily_price_fields_loaded") == []
        and audit.get("forward_return_fields_read") is False
    ):
        raise IntradayOpeningAuctionAmountShareError(
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
        repository_evidence[name] = {"path": str(path), "sha256": expected}
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
        repository_evidence[name] = {"path": str(path), "sha256": expected}
    return manifest, audit, manifest_path, audit_path, repository_evidence


def require_diagnostic_unconsumed(experiment_root: Path) -> None:
    """Reject a second read of this candidate's historical returns."""

    marker = experiment_root / CONSUMPTION_FILENAME
    if marker.exists():
        raise IntradayOpeningAuctionAmountShareError(
            "opening-auction historical diagnostic is already consumed: " f"{marker}"
        )
    for path in sorted(experiment_root.glob("*_factor_diagnostic.json")):
        record = research.load_json_record(path)
        if record.get("purpose") == DIAGNOSTIC_PURPOSE:
            raise IntradayOpeningAuctionAmountShareError(
                "opening-auction historical diagnostic already exists: " f"{path}"
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
        raise IntradayOpeningAuctionAmountShareError(
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
            "a_share_tushare_intraday_opening_auction_amount_share_"
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
                "full-session 09:30 opening-auction amount share known after "
                "signal-session close"
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
            "source_amount_read_for_factor": True,
            "source_price_or_volume_read_for_factor": False,
            "standalone_09_30_amount_in_numerator": True,
            "all_241_amounts_in_denominator": True,
            "zero_09_30_amount_is_valid_zero": True,
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
            "thresholded, subsetted, reweighted, or retested on this history.",
            "A pass admits only one factor and cannot satisfy the two-factor "
            "aggregation minimum by itself.",
            "The source universe inherits the repository's current-listing "
            "definition and is not survivorship-free.",
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
    parser = argparse.ArgumentParser(
        description=(
            "Build, no-return audit, and single-use diagnose the preregistered "
            "09:30 opening-auction amount share."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build", help="Build the external snapshot")
    build.add_argument(
        "--data-root",
        default="/Volumes/DIsk/qlib-a-share-tushare-1m",
    )
    build.add_argument("--workers", type=int, default=4)
    audit = subparsers.add_parser(
        "audit",
        help="Run coverage/capacity and uniqueness without returns",
    )
    audit.add_argument(
        "--data-root",
        default="/Volumes/DIsk/qlib-a-share-tushare-1m",
    )
    audit.add_argument(
        "--experiment-root",
        default=str(REPO_ROOT / "data/experiments/short_horizon"),
    )
    audit.add_argument("--verification-workers", type=int, default=4)
    diagnose = subparsers.add_parser(
        "diagnose",
        help="Consume the single preregistered three-session diagnostic",
    )
    diagnose.add_argument(
        "--data-root",
        default="/Volumes/DIsk/qlib-a-share-tushare-1m",
    )
    diagnose.add_argument(
        "--provider-uri",
        default=str(REPO_ROOT / "data/qlib/cn_a_share"),
    )
    diagnose.add_argument(
        "--fundamentals",
        default=str(
            REPO_ROOT / "data/raw/a_share/fundamentals/quarterly_quality.parquet"
        ),
    )
    diagnose.add_argument(
        "--experiment-root",
        default=str(REPO_ROOT / "data/experiments/short_horizon"),
    )
    diagnose.add_argument("--batch-size", type=int, default=250)
    diagnose.add_argument("--verification-workers", type=int, default=8)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "build":
        path = build_snapshot(
            data_root=Path(args.data_root),
            workers=int(args.workers),
        )
    elif args.command == "audit":
        path = run_no_return_audit(
            data_root=Path(args.data_root),
            experiment_root=Path(args.experiment_root),
            workers=int(args.verification_workers),
        )
    else:
        path = run_diagnostic(args)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
