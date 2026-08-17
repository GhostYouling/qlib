#!/usr/bin/env python3
"""Build the frozen Campaign062 quarterly disclosure-crowding factor.

The feature reads only stock-day identity plus quarterly instrument/report/
announcement dates.  It never reads a quarterly value, minute price/activity,
daily price, forward return, provider API, or Candidate49 outcome.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign052_features as base
from scripts import a_share_three_day_walkforward_campaign061_features as campaign061


REPO_ROOT = Path(__file__).resolve().parents[1]
FACTOR_NAME = "quarterly_announcement_peer_crowding_sparsity"
FACTOR_FORMULA = (
    "For every unique instrument-report_date event, count distinct instruments "
    "sharing its exact report_date and announcement_date in the frozen quarterly "
    "source. For each stock-day select the latest event effective on the first "
    "accepted session strictly after announcement_date, resolving simultaneous "
    "effective events by later report_date then later announcement_date, and "
    "return 1/peer_count."
)
PROTOCOL_SHA256 = "3588dbf1d83764d14abad1784fd93d47c844569f6ff25eb5e97dc6df314fc370"
MECHANISM_AUDIT_SHA256 = (
    "789957bf33c4689a13a0338f31235ef0bc9d5074cefd704a2398873a4977387b"
)
COMPARISON_COUNT = 93
COMPARISON_ORDER_SHA256 = (
    "a2667fbc29a2c3ad0cbe7e1d4d6d51f634170ef5e499b825d9d2147a8b9a24cb"
)
RAW_COLUMNS = ("datetime", "symbol", "provider")
BASE_COLUMNS = base.BASE_COLUMNS
EVENT_FIELDS = ("instrument", "report_date", "announcement_date")
FORBIDDEN_EVENT_VALUE_FIELDS = ("roe", "net_profit", "revenue_yoy", "profit_yoy")
LOWER_BOUND = 0.0
UPPER_BOUND = 1.0
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign062_feature_library_v1"
)
DEFAULT_DATA_ROOT = base.DEFAULT_DATA_ROOT
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_062_no_return_preregistration.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_062_feature_implementation_freeze_v2_20260805.json"
)
DISCLOSURE_PATH = REPO_ROOT / "data/raw/a_share/fundamentals/quarterly_quality.parquet"
DISCLOSURE_SHA256 = (
    "3ac901a97928d2ed81ac72e3eaac9bdc148d36cf67b6abe70223699235ef059f"
)
DISCLOSURE_MANIFEST_PATH = REPO_ROOT / "data/metadata/quarterly_quality_manifest.json"
DISCLOSURE_MANIFEST_SHA256 = (
    "e3cf654babe37a82393c5530696bc1cc242b736cb88e1947b8444b638125ba8c"
)
CALENDAR_PATH = REPO_ROOT / "data/qlib/cn_a_share/calendars/day.txt"
CALENDAR_SHA256 = (
    "fda506597d26bcec953cdc0882042a5046ec1587db60490e16a01627fd43f53a"
)
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
_EVENT_CACHE: Any = None


class Campaign062FeatureError(RuntimeError):
    """Fail-closed Campaign062 feature boundary error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_file(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign062FeatureError(f"{label} changed")


def _comparison_order_digest(items: Iterable[dict[str, Any]]) -> str:
    payload = json.dumps(
        [[str(item["name"]), str(item["score_direction"])] for item in items],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def reconstruct_comparisons(spec: dict[str, Any]) -> list[dict[str, str]]:
    link = (spec.get("source_chain") or {}).get("prior_comparison_catalog") or {}
    path = REPO_ROOT / str(link.get("path") or "")
    if not path.is_file() or _sha256(path) != str(link.get("sha256") or ""):
        raise Campaign062FeatureError("Campaign061 comparison protocol changed")
    prior = json.loads(path.read_text(encoding="utf-8"))
    inherited = campaign061.reconstruct_comparisons(prior)
    appended = list(
        ((spec.get("ordered_no_return_gates") or {}).get("uniqueness_after_coverage_only") or {}).get(
            "appended_comparison_factors"
        )
        or []
    )
    return [
        {"name": str(item["name"]), "score_direction": str(item["score_direction"])}
        for item in [*inherited, *appended]
    ]


def output_root(data_root: Path) -> Path:
    return (
        data_root.expanduser().resolve()
        / "derived/a_share/rich/tushare/minute_walkforward_campaign062_feature_library"
        / OUTPUT_RUN_ID
    )


def _load_implementation_freeze() -> dict[str, Any]:
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign062FeatureError("Campaign062 implementation freeze is absent")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    runner = record.get("feature_runner") or {}
    protocol = record.get("no_return_protocol") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign062_feature_implementation_freeze"
        and record.get("status") == "frozen_before_campaign062_source_values"
        and (REPO_ROOT / str(runner.get("path") or "")).resolve()
        == Path(__file__).resolve()
        and runner.get("sha256") == _sha256(Path(__file__).resolve())
        and protocol.get("sha256") == PROTOCOL_SHA256
        and record.get("source_partition_or_quarterly_values_read_before_freeze") is False
        and record.get("candidate_values_read_before_freeze") is False
        and record.get("comparison_values_read_before_freeze") is False
        and record.get("historical_forward_returns_read_before_freeze") is False
    ):
        raise Campaign062FeatureError("Campaign062 implementation freeze changed")
    return record


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    _require_file(path, PROTOCOL_SHA256, "Campaign062 no-return protocol")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign062FeatureError("Campaign062 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    comparisons = reconstruct_comparisons(spec)
    if not (
        spec.get("version") == 1
        and spec.get("kind")
        == "a_share_three_day_walkforward_campaign062_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign062_source_candidate_comparison_daily_price_or_return_values"
        and (spec.get("source_chain") or {}).get("mechanism_overlap_audit", {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("stock_day_identity_projection") or ()) == RAW_COLUMNS
        and tuple(candidate.get("quarterly_source_projection") or ()) == EVENT_FIELDS
        and tuple(candidate.get("forbidden_quarterly_value_fields") or ())
        == FORBIDDEN_EVENT_VALUE_FIELDS
        and candidate.get("forbidden_minute_source_columns")
        == ["open", "high", "low", "close", "volume", "amount"]
        and candidate.get("event_identity") == ["instrument", "report_date"]
        and candidate.get("event_identity_must_be_unique") is True
        and candidate.get("peer_group_keys") == ["report_date", "announcement_date"]
        and candidate.get("peer_identity") == "distinct instrument"
        and candidate.get("issuer_included_in_peer_count") is True
        and candidate.get("minimum_peer_count") == 1
        and candidate.get("endpoint_canonicalization_tolerance") is None
        and candidate.get("valid_range")
        == {
            "lower": 0.0,
            "lower_inclusive": False,
            "upper": 1.0,
            "upper_inclusive": True,
        }
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and uniqueness.get("comparison_factor_count") == COMPARISON_COUNT
        and uniqueness.get("comparison_factor_order_sha256") == COMPARISON_ORDER_SHA256
        and uniqueness.get("all_93_must_pass") is True
        and len(comparisons) == COMPARISON_COUNT
        and _comparison_order_digest(comparisons) == COMPARISON_ORDER_SHA256
        and comparisons[-1]
        == {
            "name": "intraday_day_over_day_realized_variance_stability_238b",
            "score_direction": "higher",
        }
        and finite.get("trial_id")
        == "wf062_quarterly_announcement_peer_crowding_sparsity_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("expected_trial_count") == 1
        and boundary.get("quarterly_value_fields_read_by_candidate_before_admissibility")
        is False
        and boundary.get("minute_price_volume_amount_fields_read_before_admissibility")
        is False
        and boundary.get("comparison_values_read_before_coverage_pass") is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign062FeatureError("Campaign062 protocol semantics changed")
    return spec


def compute_factor_values(
    peer_counts: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    counts = np.asarray(peer_counts, dtype=float)
    if counts.ndim != 1:
        raise Campaign062FeatureError("peer counts must be one dimensional")
    finite = np.isfinite(counts)
    integer = np.equal(counts, np.floor(counts))
    positive = counts >= 1.0
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        score = 1.0 / counts
    score_finite = np.isfinite(score)
    score_in_range = (score > LOWER_BOUND) & (score <= UPPER_BOUND)
    eligible = finite & integer & positive & score_finite & score_in_range
    quality = {
        "base_rows": int(len(counts)),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__no_prior_effective_disclosure_rows": int((~finite).sum()),
        f"{FACTOR_NAME}__noninteger_peer_count_rows": int((finite & ~integer).sum()),
        f"{FACTOR_NAME}__nonpositive_peer_count_rows": int(
            (finite & integer & ~positive).sum()
        ),
        f"{FACTOR_NAME}__singleton_peer_group_rows": int(
            (eligible & (counts == 1.0)).sum()
        ),
        f"{FACTOR_NAME}__range_or_nonfinite_score_rows": int(
            (finite & integer & positive & (~score_finite | ~score_in_range)).sum()
        ),
    }
    return (
        {FACTOR_NAME: np.where(eligible, score, np.nan)},
        {FACTOR_NAME: eligible},
        quality,
    )


def _load_disclosure_events() -> tuple[np.ndarray, dict[str, dict[str, np.ndarray]]]:
    global _EVENT_CACHE
    if _EVENT_CACHE is not None:
        return _EVENT_CACHE
    _require_file(DISCLOSURE_PATH, DISCLOSURE_SHA256, "quarterly disclosure source")
    _require_file(
        DISCLOSURE_MANIFEST_PATH,
        DISCLOSURE_MANIFEST_SHA256,
        "quarterly disclosure manifest",
    )
    _require_file(CALENDAR_PATH, CALENDAR_SHA256, "accepted local calendar")
    calendar = pd.to_datetime(
        CALENDAR_PATH.read_text(encoding="utf-8").splitlines(), errors="coerce"
    )
    if pd.isna(calendar).any():
        raise Campaign062FeatureError("accepted calendar contains invalid dates")
    calendar = pd.DatetimeIndex(calendar).normalize().unique().sort_values()
    calendar_values = calendar.to_numpy(dtype="datetime64[ns]")
    events = pd.read_parquet(
        DISCLOSURE_PATH,
        columns=list(EVENT_FIELDS),
        filters=[("announcement_date", "<", pd.Timestamp("2026-01-01"))],
    )
    if tuple(events.columns) != EVENT_FIELDS:
        raise Campaign062FeatureError("quarterly disclosure projection changed")
    events["instrument"] = events["instrument"].astype(str).str.upper()
    events["report_date"] = pd.to_datetime(
        events["report_date"], errors="coerce"
    ).dt.normalize()
    events["announcement_date"] = pd.to_datetime(
        events["announcement_date"], errors="coerce"
    ).dt.normalize()
    if (
        events.empty
        or events.isna().any().any()
        or events.duplicated(["instrument", "report_date"]).any()
    ):
        raise Campaign062FeatureError("quarterly disclosure identities changed")
    counts = (
        events.groupby(["report_date", "announcement_date"], observed=True)[
            "instrument"
        ]
        .nunique()
        .rename("peer_count")
        .reset_index()
    )
    events = events.merge(
        counts,
        on=["report_date", "announcement_date"],
        how="left",
        validate="many_to_one",
    )
    effective_positions = np.searchsorted(
        calendar_values,
        events["announcement_date"].to_numpy(dtype="datetime64[ns]"),
        side="right",
    )
    in_range = effective_positions < len(calendar_values)
    events = events.loc[in_range].copy()
    events["effective_position"] = effective_positions[in_range]
    events = (
        events.sort_values(
            ["instrument", "effective_position", "report_date", "announcement_date"],
            kind="stable",
        )
        .drop_duplicates(["instrument", "effective_position"], keep="last")
        .reset_index(drop=True)
    )
    by_symbol: dict[str, dict[str, np.ndarray]] = {}
    for symbol, group in events.groupby("instrument", sort=False):
        by_symbol[str(symbol)] = {
            "effective_position": group["effective_position"].to_numpy(
                dtype=np.int64
            ),
            "peer_count": group["peer_count"].to_numpy(dtype=float),
        }
    _EVENT_CACHE = (calendar_values, by_symbol)
    return _EVENT_CACHE


def empty_output_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype=str),
            "provider": pd.Series(dtype=str),
            FACTOR_NAME: pd.Series(dtype=float),
            f"{FACTOR_NAME}_eligible": pd.Series(dtype=bool),
        }
    ).loc[:, OUTPUT_COLUMNS]


def compute_partition_frame(
    raw: pd.DataFrame,
    base_frame: pd.DataFrame,
    _unused_benchmark: Any,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign062FeatureError(f"unexpected raw columns for {symbol}")
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign062FeatureError(f"unexpected joint-base columns for {symbol}")
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
        raise Campaign062FeatureError(f"joint-base identity changed for {symbol}")
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(
        drop=True
    )
    if base_work.empty:
        return empty_output_frame(), {"base_rows": 0}
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign062FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign062FeatureError(f"source stock-day grid changed for {symbol}")
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(value) for value in values))
    if not source_codes.eq(base.market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign062FeatureError(f"source minute identity grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign062FeatureError(f"source and joint-base dates changed for {symbol}")

    calendar_values, events_by_symbol = _load_disclosure_events()
    trade_values = base_work["trade_date"].to_numpy(dtype="datetime64[ns]")
    trade_positions = np.searchsorted(calendar_values, trade_values, side="left")
    bounded = trade_positions < len(calendar_values)
    if (
        not bounded.all()
        or not np.array_equal(calendar_values[trade_positions], trade_values)
    ):
        raise Campaign062FeatureError(f"base dates outside calendar for {symbol}")
    peer_counts = np.full(len(trade_positions), np.nan, dtype=float)
    event = events_by_symbol.get(symbol.upper())
    if event is not None and len(event["effective_position"]):
        selected = (
            np.searchsorted(event["effective_position"], trade_positions, side="right")
            - 1
        )
        has_event = selected >= 0
        peer_counts[has_event] = event["peer_count"][selected[has_event]]
    values, eligible, quality = compute_factor_values(peer_counts)
    frame = pd.DataFrame(
        {
            "trade_date": base_work["trade_date"],
            "symbol": symbol.upper(),
            "provider": "eastmoney_disclosure_timing",
            FACTOR_NAME: values[FACTOR_NAME],
            f"{FACTOR_NAME}_eligible": eligible[FACTOR_NAME],
        }
    )
    return frame.loc[:, OUTPUT_COLUMNS], quality


def _validate_snapshot_manifest(
    manifest: dict[str, Any], *, require_fingerprint_constants: bool
) -> None:
    if not require_fingerprint_constants:
        manifest["kind"] = "a_share_three_day_walkforward_campaign062_feature_snapshot"
        manifest["source_open_high_low_read"] = False
        manifest["source_close_read"] = False
        manifest["source_volume_read"] = False
        manifest["source_amount_read"] = False
        evidence = {
            key: value
            for key, value in (manifest.get("protocol_evidence") or {}).items()
            if not key.startswith("campaign052_") and not key.startswith("campaign062_")
        }
        evidence["campaign062_mechanism_overlap_audit_sha256"] = MECHANISM_AUDIT_SHA256
        evidence["campaign062_no_return_preregistration_sha256"] = PROTOCOL_SHA256
        manifest["protocol_evidence"] = evidence
        manifest["quarterly_disclosure_source_path"] = str(DISCLOSURE_PATH.resolve())
        manifest["quarterly_disclosure_source_sha256"] = DISCLOSURE_SHA256
        manifest["quarterly_disclosure_manifest_path"] = str(
            DISCLOSURE_MANIFEST_PATH.resolve()
        )
        manifest["quarterly_disclosure_manifest_sha256"] = (
            DISCLOSURE_MANIFEST_SHA256
        )
        manifest["quarterly_disclosure_fields_read"] = list(EVENT_FIELDS)
        manifest["quarterly_value_fields_read"] = []
    evidence = manifest.get("protocol_evidence") or {}
    quality = manifest.get("quality") or {}
    files = list(manifest.get("files") or [])
    eligible_rows = (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    if not (
        manifest.get("schema_version") == 1
        and manifest.get("kind")
        == "a_share_three_day_walkforward_campaign062_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_open_high_low_read") is False
        and manifest.get("source_close_read") is False
        and manifest.get("source_volume_read") is False
        and manifest.get("source_amount_read") is False
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == FACTOR_DIRECTIONS
        and manifest.get("factor_formulas") == FACTOR_FORMULAS
        and manifest.get("protocol_sha256") == PROTOCOL_SHA256
        and evidence.get("campaign062_mechanism_overlap_audit_sha256")
        == MECHANISM_AUDIT_SHA256
        and evidence.get("campaign062_no_return_preregistration_sha256")
        == PROTOCOL_SHA256
        and manifest.get("quarterly_disclosure_source_sha256") == DISCLOSURE_SHA256
        and manifest.get("quarterly_disclosure_manifest_sha256")
        == DISCLOSURE_MANIFEST_SHA256
        and tuple(manifest.get("quarterly_disclosure_fields_read") or ())
        == EVENT_FIELDS
        and manifest.get("quarterly_value_fields_read") == []
        and isinstance(manifest.get("rows"), int)
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
        raise Campaign062FeatureError("Campaign062 snapshot semantics changed")


def _install_engine_globals() -> None:
    values = {
        "DEFAULT_PROTOCOL": DEFAULT_PROTOCOL,
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
        "SNAPSHOT_MANIFEST_SHA256": "",
        "SNAPSHOT_DATASET_SHA256": "",
        "NO_RETURN_AUDIT_SHA256": "",
        "load_protocol": load_protocol,
        "compute_factor_values": compute_factor_values,
        "compute_partition_frame": compute_partition_frame,
        "empty_output_frame": empty_output_frame,
        "_validate_snapshot_manifest": _validate_snapshot_manifest,
        "output_root": output_root,
    }
    base._generated.update(values)
    base._engine_globals.update(values)


_install_engine_globals()
verify_snapshot_files = base._generated["verify_snapshot_files"]


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    _load_implementation_freeze()
    load_protocol()
    _install_engine_globals()
    inherited = base._generated["_inherited_build_snapshot"]
    inherited_writer = inherited.__globals__["_inherited_build_snapshot"]
    publication_foundation = inherited_writer.__globals__["foundation"]
    original = publication_foundation.atomic_write_json

    def write_with_truth(value: dict[str, Any], path: Path) -> None:
        if (
            value.get("kind")
            == "a_share_three_day_walkforward_campaign062_feature_snapshot"
            and value.get("output_run_id") == OUTPUT_RUN_ID
        ):
            value = dict(value)
            value.update(
                {
                    "source_open_high_low_read": False,
                    "source_close_read": False,
                    "source_volume_read": False,
                    "source_amount_read": False,
                    "quarterly_disclosure_source_path": str(DISCLOSURE_PATH.resolve()),
                    "quarterly_disclosure_source_sha256": DISCLOSURE_SHA256,
                    "quarterly_disclosure_manifest_path": str(
                        DISCLOSURE_MANIFEST_PATH.resolve()
                    ),
                    "quarterly_disclosure_manifest_sha256": (
                        DISCLOSURE_MANIFEST_SHA256
                    ),
                    "quarterly_disclosure_fields_read": list(EVENT_FIELDS),
                    "quarterly_value_fields_read": [],
                }
            )
        original(value, path)

    publication_foundation.atomic_write_json = write_with_truth
    try:
        return inherited(data_root=data_root, workers=workers)
    finally:
        publication_foundation.atomic_write_json = original


def status(data_root: Path) -> dict[str, Any]:
    path = output_root(data_root) / "snapshot_manifest.json"
    return {
        "protocol_path": str(DEFAULT_PROTOCOL.resolve()),
        "protocol_sha256": PROTOCOL_SHA256,
        "implementation_freeze_exists": DEFAULT_IMPLEMENTATION_FREEZE.is_file(),
        "snapshot_manifest_path": str(path),
        "snapshot_exists": path.is_file(),
        "source_fields_read_by_status": list(RAW_COLUMNS),
        "quarterly_disclosure_fields_read_by_status": list(EVENT_FIELDS),
        "quarterly_value_fields_read_by_status": [],
        "minute_price_volume_amount_fields_read_by_status": [],
        "daily_price_fields_read_by_status": False,
        "forward_return_fields_read_by_status": False,
        "candidate49_historical_return_read": False,
        "second_prospective_candidate_created": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "build"):
        command = sub.add_parser(name)
        command.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
        command.add_argument("--workers", type=int, default=4)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "status":
        payload = status(args.data_root)
    else:
        payload = {
            "manifest": str(
                build_snapshot(data_root=args.data_root, workers=args.workers)
            )
        }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
