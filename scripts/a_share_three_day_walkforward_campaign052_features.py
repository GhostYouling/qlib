#!/usr/bin/env python3
"""Build and audit Campaign052 quarterly announcement-delay consistency."""

from __future__ import annotations

import argparse
import copy
import gc
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    import scripts.a_share_three_day_preregistration_binding_validator as bindings
    import scripts.a_share_three_day_walkforward_campaign051_features_v7 as previous_entry
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_three_day_walkforward_campaign051_features_v7 as previous_entry


REPO_ROOT = Path(__file__).resolve().parents[1]
previous = previous_entry.runner
FACTOR_NAME = "quarterly_announcement_delay_consistency_4q"
FACTOR_FORMULA = (
    "For the latest four distinct effective reports whose report dates are four "
    "consecutive calendar quarter ends, let d_j be the nonnegative integer "
    "calendar days from report_date_j to announcement_date_j. Let sigma be the "
    "population standard deviation of the four d_j values. Return 1/(1+sigma)."
)
MECHANISM_AUDIT_SHA256 = (
    "a7e505bb65890dd90f505b4f999e028c03893ed434b18c6923c943a9086371ee"
)
PROTOCOL_SHA256 = "3cb9468f7cf113c5ada33a7d766e94ee3689811522f3550450ab0135b748ab0b"
IMPLEMENTATION_FREEZE_SHA256 = ""
SNAPSHOT_MANIFEST_SHA256 = ""
SNAPSHOT_DATASET_SHA256 = ""
SNAPSHOT_PUBLICATION_BINDING_SHA256 = ""
NO_RETURN_AUDIT_SHA256 = ""

TERMINAL_LIBRARY_COUNT = 66
COMPARISON_COUNT = 75
INHERITED_COMPARISON_COUNT = 74
INHERITED_COMPARISON_ORDER_SHA256 = (
    "08639819d24bbb65f1181a31edd788dfc5ac4a6ee56312f600861612d2dec573"
)
COMPARISON_ORDER_SHA256 = (
    "8c30647dde2f246dce84222ba7b4b18e61424f784cf522f97c95a6ee7dd802ec"
)
LOOKBACK_REPORTS = 4
LOWER_BOUND = 0.0
UPPER_BOUND = 1.0
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign052_feature_library_v1"
)
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_052_no_return_preregistration.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_052_feature_implementation_freeze_20260803.json"
)
DEFAULT_SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_052_snapshot_publication_binding_20260803.json"
)
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_052/no_return"
)
DEFAULT_DATA_ROOT = previous.DEFAULT_DATA_ROOT
RAW_COLUMNS = ("datetime", "symbol", "provider")
BASE_COLUMNS = previous.BASE_COLUMNS
EVENT_FIELDS = ("instrument", "report_date", "announcement_date")
FORBIDDEN_EVENT_VALUE_FIELDS = ("roe", "net_profit", "revenue_yoy", "profit_yoy")
DISCLOSURE_PATH = (
    REPO_ROOT / "data/raw/a_share/fundamentals/quarterly_quality.parquet"
)
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
C51_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign051_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign051_feature_library_v1/snapshot_manifest.json"
)
C51_SNAPSHOT_SHA256 = (
    "13a2b7862cb2118dd8e42bcd94653973de603d840bd09f0762be219b840f032e"
)
C51_DATASET_SHA256 = (
    "2930b47c228f3e033f8130d9960e55668e688e02ba020a02d02ffa60987cabbd"
)
C51_FACTOR_NAME = "intraday_close_range_occupancy_entropy_10b"

_generated = previous._generated
_engine_globals = previous._engine_globals
market = previous.market
campaign044 = previous.campaign044
campaign045 = previous.campaign045
campaign046 = previous.campaign046
campaign047_reference = previous.campaign047_reference
campaign048_reference = previous.campaign048_reference
_DISCLOSURE_EVENT_CACHE: Any = None


class Campaign052FeatureError(RuntimeError):
    """Fail-closed Campaign052 feature boundary error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected_sha256:
        raise Campaign052FeatureError(f"{label} changed")


def _comparison_order_digest(comparisons: list[dict[str, Any]]) -> str:
    payload = json.dumps(
        [(str(item["name"]), str(item["score_direction"])) for item in comparisons],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def output_root(data_root: Path) -> Path:
    return (
        data_root.expanduser().resolve()
        / "derived/a_share/rich/tushare/minute_walkforward_campaign052_feature_library"
        / OUTPUT_RUN_ID
    )


def _load_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE_SHA256:
        raise Campaign052FeatureError("Campaign052 implementation freeze is not bound")
    _require_file(
        DEFAULT_IMPLEMENTATION_FREEZE,
        IMPLEMENTATION_FREEZE_SHA256,
        "Campaign052 implementation freeze",
    )
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    runner = record.get("feature_runner") or {}
    protocol = record.get("no_return_protocol") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign052_feature_implementation_freeze"
        and record.get("status") == "frozen_before_campaign052_candidate_values"
        and Path(str(runner.get("path"))).resolve() == Path(__file__).resolve()
        and runner.get("sha256") == _sha256(Path(__file__).resolve())
        and protocol.get("sha256") == PROTOCOL_SHA256
        and record.get("candidate_values_read_before_freeze") is False
        and record.get("comparison_values_read_before_freeze") is False
        and record.get("historical_forward_returns_read_before_freeze") is False
    ):
        raise Campaign052FeatureError("Campaign052 implementation freeze semantics changed")
    return record


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate every Campaign052 binding and exact frozen semantic."""

    path = path.expanduser().resolve()
    _require_file(path, PROTOCOL_SHA256, "Campaign052 no-return protocol")
    validation = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if validation.get("all_bindings_passed") is not True:
        raise Campaign052FeatureError("Campaign052 protocol has a failed binding")
    spec = json.loads(path.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    source = spec.get("source_chain") or {}
    inherited = previous.load_protocol()
    inherited_comparisons = copy.deepcopy(
        inherited["ordered_no_return_gates"]["uniqueness_after_coverage_only"].get(
            "comparison_factors"
        )
        or []
    )
    comparisons = inherited_comparisons + [
        copy.deepcopy(uniqueness.get("final_comparison_factor") or {})
    ]
    if not (
        spec.get("version") == 1
        and spec.get("kind")
        == "a_share_three_day_walkforward_campaign052_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign052_candidate_comparison_daily_price_or_return_values"
        and (source.get("mechanism_overlap_audit") or {}).get("sha256")
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
        and candidate.get("lookback_reports") == LOOKBACK_REPORTS
        and candidate.get("fiscal_quarter_calendar") == "Q-DEC"
        and candidate.get("availability_rule")
        == "announcement_date is strictly earlier than the accepted stock-day"
        and candidate.get("dispersion_estimator")
        == "equal-weight population standard deviation over exactly four delays"
        and candidate.get("normalization") == "1/(1+sigma)"
        and candidate.get("endpoint_canonicalization_tolerance") is None
        and candidate.get("valid_range")
        == {
            "lower": 0.0,
            "lower_inclusive": False,
            "upper": 1.0,
            "upper_inclusive": True,
        }
        and candidate.get("transform_scale_clip_threshold_filter") == "none"
        and candidate.get(
            "alternate_field_window_estimator_direction_scale_board_year_cost_regime_fit_combination_or_model_search"
        )
        is False
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation")
        == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and uniqueness.get("inherited_campaign051_comparison_factor_count")
        == INHERITED_COMPARISON_COUNT
        and uniqueness.get("inherited_campaign051_comparison_factor_order_sha256")
        == INHERITED_COMPARISON_ORDER_SHA256
        and uniqueness.get("comparison_factor_count") == COMPARISON_COUNT
        and uniqueness.get("comparison_factor_order_sha256")
        == COMPARISON_ORDER_SHA256
        and len(inherited_comparisons) == INHERITED_COMPARISON_COUNT
        and len(comparisons) == COMPARISON_COUNT
        and _comparison_order_digest(comparisons) == COMPARISON_ORDER_SHA256
        and comparisons[-1]
        == {"name": C51_FACTOR_NAME, "score_direction": "higher"}
        and finite.get("trial_id")
        == "wf052_quarterly_announcement_delay_consistency_4q_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("expected_trial_count") == 1
        and boundary.get("quarterly_value_fields_read_by_candidate_before_admissibility")
        is False
        and boundary.get("minute_price_volume_amount_fields_read_before_admissibility")
        is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("second_prospective_candidate_created") is False
        and boundary.get("current_scoring_selection_sizing_or_orders_allowed")
        is False
    ):
        raise Campaign052FeatureError("Campaign052 protocol semantics changed")
    spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ] = comparisons
    return spec


def compute_factor_values(
    *, delays: np.ndarray, consecutive_quarters: np.ndarray
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the frozen four-quarter delay-consistency score."""

    delays = np.asarray(delays, dtype=float)
    consecutive_quarters = np.asarray(consecutive_quarters, dtype=bool)
    if delays.ndim != 2 or delays.shape[1] != LOOKBACK_REPORTS:
        raise Campaign052FeatureError("Campaign052 delay shape is invalid")
    if consecutive_quarters.shape != (len(delays),):
        raise Campaign052FeatureError("Campaign052 consecutive-quarter shape is invalid")
    finite = np.isfinite(delays).all(axis=1)
    integer = np.equal(delays, np.floor(delays)).all(axis=1)
    nonnegative = (delays >= 0.0).all(axis=1)
    with np.errstate(invalid="ignore", over="ignore", divide="ignore"):
        sigma = np.std(delays, axis=1, ddof=0)
        score = 1.0 / (1.0 + sigma)
    score_finite = np.isfinite(score)
    score_in_range = (score > LOWER_BOUND) & (score <= UPPER_BOUND)
    eligible = (
        consecutive_quarters
        & finite
        & integer
        & nonnegative
        & score_finite
        & score_in_range
    )
    quality = {
        "base_rows": int(len(delays)),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__fewer_than_four_effective_reports_rows": 0,
        f"{FACTOR_NAME}__nonconsecutive_quarter_rows": int(
            (~consecutive_quarters).sum()
        ),
        f"{FACTOR_NAME}__nonfinite_delay_rows": int((~finite).sum()),
        f"{FACTOR_NAME}__noninteger_delay_rows": int((finite & ~integer).sum()),
        f"{FACTOR_NAME}__negative_delay_rows": int(
            (finite & integer & ~nonnegative).sum()
        ),
        f"{FACTOR_NAME}__zero_dispersion_rows": int(
            (eligible & (sigma == 0.0)).sum()
        ),
        f"{FACTOR_NAME}__range_or_nonfinite_score_rows": int(
            (
                consecutive_quarters
                & finite
                & integer
                & nonnegative
                & (~score_finite | ~score_in_range)
            ).sum()
        ),
    }
    return (
        {FACTOR_NAME: np.where(eligible, score, np.nan)},
        {FACTOR_NAME: eligible},
        quality,
    )


def _load_disclosure_events() -> tuple[np.ndarray, dict[str, dict[str, np.ndarray]]]:
    """Load only frozen quarterly disclosure identity/timing columns."""

    global _DISCLOSURE_EVENT_CACHE
    if _DISCLOSURE_EVENT_CACHE is not None:
        return _DISCLOSURE_EVENT_CACHE
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
        raise Campaign052FeatureError("accepted calendar contains invalid dates")
    calendar = pd.DatetimeIndex(calendar).normalize().unique().sort_values()
    calendar_values = calendar.to_numpy(dtype="datetime64[ns]")
    events = pd.read_parquet(
        DISCLOSURE_PATH,
        columns=list(EVENT_FIELDS),
        filters=[("announcement_date", "<", pd.Timestamp("2026-01-01"))],
    )
    if tuple(events.columns) != EVENT_FIELDS:
        raise Campaign052FeatureError("quarterly disclosure projection changed")
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
        raise Campaign052FeatureError("quarterly disclosure identities changed")
    quarter_period = events["report_date"].dt.to_period("Q-DEC")
    quarter_end = quarter_period.dt.end_time.dt.normalize()
    events["is_exact_quarter_end"] = events["report_date"].eq(quarter_end)
    events["quarter_ordinal"] = quarter_period.astype("int64")
    events["delay_days"] = (
        events["announcement_date"] - events["report_date"]
    ).dt.days.astype(float)
    effective_positions = np.searchsorted(
        calendar_values,
        events["announcement_date"].to_numpy(dtype="datetime64[ns]"),
        side="right",
    )
    in_range = effective_positions < len(calendar_values)
    events = events.loc[in_range].copy()
    events["effective_position"] = effective_positions[in_range]
    events = events.sort_values(
        ["instrument", "quarter_ordinal", "effective_position"], kind="stable"
    ).reset_index(drop=True)
    by_symbol: dict[str, dict[str, np.ndarray]] = {}
    for symbol, group in events.groupby("instrument", sort=False):
        by_symbol[str(symbol)] = {
            "quarter_ordinal": group["quarter_ordinal"].to_numpy(dtype=np.int64),
            "effective_position": group["effective_position"].to_numpy(
                dtype=np.int64
            ),
            "delay_days": group["delay_days"].to_numpy(dtype=float),
            "is_exact_quarter_end": group["is_exact_quarter_end"].to_numpy(
                dtype=bool
            ),
        }
    _DISCLOSURE_EVENT_CACHE = (calendar_values, by_symbol)
    return _DISCLOSURE_EVENT_CACHE


def compute_partition_frame(
    raw: pd.DataFrame,
    base_frame: pd.DataFrame,
    _unused_benchmark: Any,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Validate one stock-year identity grid and compute Campaign052."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign052FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign052FeatureError(
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
        raise Campaign052FeatureError(f"joint-base identity changed for {symbol}")
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
        raise Campaign052FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign052FeatureError(
            f"every source stock-day must retain 241 identity rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(value) for value in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign052FeatureError(f"source minute identity grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign052FeatureError(f"source and joint-base dates changed for {symbol}")

    calendar_values, events_by_symbol = _load_disclosure_events()
    trade_values = base_work["trade_date"].to_numpy(dtype="datetime64[ns]")
    trade_positions = np.searchsorted(calendar_values, trade_values, side="left")
    bounded = trade_positions < len(calendar_values)
    if (
        not bounded.all()
        or not np.array_equal(calendar_values[trade_positions], trade_values)
    ):
        raise Campaign052FeatureError(
            f"base dates are outside the accepted calendar for {symbol}"
        )

    delays = np.full((len(trade_positions), LOOKBACK_REPORTS), np.nan, dtype=float)
    consecutive = np.zeros(len(trade_positions), dtype=bool)
    fewer_than_four = np.ones(len(trade_positions), dtype=bool)
    event = events_by_symbol.get(symbol.upper())
    if event is not None:
        for row_index, trade_position in enumerate(trade_positions):
            usable = (
                (event["effective_position"] <= trade_position)
                & event["is_exact_quarter_end"]
            )
            positions = np.flatnonzero(usable)
            if len(positions) < LOOKBACK_REPORTS:
                continue
            selected = positions[-LOOKBACK_REPORTS:]
            fewer_than_four[row_index] = False
            ordinals = event["quarter_ordinal"][selected]
            consecutive[row_index] = bool(np.all(np.diff(ordinals) == 1))
            delays[row_index] = event["delay_days"][selected]
    values, eligible, quality = compute_factor_values(
        delays=delays, consecutive_quarters=consecutive
    )
    quality[f"{FACTOR_NAME}__fewer_than_four_effective_reports_rows"] = int(
        fewer_than_four.sum()
    )
    quality[f"{FACTOR_NAME}__nonconsecutive_quarter_rows"] = int(
        ((~fewer_than_four) & (~consecutive)).sum()
    )
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
        manifest["kind"] = "a_share_three_day_walkforward_campaign052_feature_snapshot"
        manifest["source_open_high_low_read"] = False
        manifest["source_close_read"] = False
        manifest["source_volume_read"] = False
        manifest["source_amount_read"] = False
        evidence = {
            key: value
            for key, value in (manifest.get("protocol_evidence") or {}).items()
            if not key.startswith("campaign051_")
            and not key.startswith("campaign052_")
        }
        evidence["campaign052_mechanism_overlap_audit_sha256"] = (
            MECHANISM_AUDIT_SHA256
        )
        evidence["campaign052_no_return_preregistration_sha256"] = PROTOCOL_SHA256
        evidence["campaign052_implementation_freeze_sha256"] = (
            IMPLEMENTATION_FREEZE_SHA256
        )
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
        == "a_share_three_day_walkforward_campaign052_feature_snapshot"
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
        and evidence.get("campaign052_mechanism_overlap_audit_sha256")
        == MECHANISM_AUDIT_SHA256
        and evidence.get("campaign052_no_return_preregistration_sha256")
        == PROTOCOL_SHA256
        and evidence.get("campaign052_implementation_freeze_sha256")
        == IMPLEMENTATION_FREEZE_SHA256
        and manifest.get("quarterly_disclosure_source_sha256") == DISCLOSURE_SHA256
        and manifest.get("quarterly_disclosure_manifest_sha256")
        == DISCLOSURE_MANIFEST_SHA256
        and tuple(manifest.get("quarterly_disclosure_fields_read") or ())
        == EVENT_FIELDS
        and manifest.get("quarterly_value_fields_read") == []
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
        raise Campaign052FeatureError("Campaign052 snapshot semantics changed")
    if require_fingerprint_constants and not (
        SNAPSHOT_MANIFEST_SHA256
        and SNAPSHOT_DATASET_SHA256
        and manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
    ):
        raise Campaign052FeatureError("Campaign052 snapshot fingerprint is not bound")


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
            == "a_share_three_day_walkforward_campaign052_feature_snapshot"
            and value.get("output_run_id") == OUTPUT_RUN_ID
        ):
            value = dict(value)
            value.update(
                {
                    "source_open_high_low_read": False,
                    "source_close_read": False,
                    "source_volume_read": False,
                    "source_amount_read": False,
                    "quarterly_disclosure_source_path": str(
                        DISCLOSURE_PATH.resolve()
                    ),
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


def _load_candidate_frame(
    manifest_path: Path, manifest: dict[str, Any]
) -> pd.DataFrame:
    _, _, engine, _, _, _ = campaign044._context()
    return engine.load_factor_frame(manifest_path, manifest, FACTOR_NAME)


def _extra_comparison_sources() -> list[tuple[str, Path, str, str | None, str, Any]]:
    c50 = previous.previous
    base = c50._base
    return [
        (
            "campaign044",
            base.C44_SNAPSHOT_PATH,
            base.C44_SNAPSHOT_SHA256,
            None,
            base.C44_FACTOR_NAME,
            campaign044,
        ),
        (
            "campaign045",
            base.C45_SNAPSHOT_PATH,
            base.C45_SNAPSHOT_SHA256,
            base.C45_DATASET_SHA256,
            base.C45_FACTOR_NAME,
            campaign045,
        ),
        (
            "campaign046",
            base.C46_SNAPSHOT_PATH,
            base.C46_SNAPSHOT_SHA256,
            base.C46_DATASET_SHA256,
            base.C46_FACTOR_NAME,
            campaign046,
        ),
        (
            "campaign047",
            base.C47_SNAPSHOT_PATH,
            base.C47_SNAPSHOT_SHA256,
            base.C47_DATASET_SHA256,
            base.C47_FACTOR_NAME,
            campaign047_reference,
        ),
        (
            "campaign048",
            base.C48_SNAPSHOT_PATH,
            base.C48_SNAPSHOT_SHA256,
            base.C48_DATASET_SHA256,
            base.C48_FACTOR_NAME,
            campaign048_reference,
        ),
        (
            "campaign049",
            c50.C49_SNAPSHOT_PATH,
            c50.C49_SNAPSHOT_SHA256,
            c50.C49_DATASET_SHA256,
            c50.C49_FACTOR_NAME,
            c50._base,
        ),
        (
            "campaign050",
            previous.C50_SNAPSHOT_PATH,
            previous.C50_SNAPSHOT_SHA256,
            previous.C50_DATASET_SHA256,
            previous.C50_FACTOR_NAME,
            c50,
        ),
        (
            "campaign051",
            C51_SNAPSHOT_PATH,
            C51_SNAPSHOT_SHA256,
            C51_DATASET_SHA256,
            C51_FACTOR_NAME,
            previous,
        ),
    ]


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    _load_implementation_freeze()
    if not (
        SNAPSHOT_MANIFEST_SHA256
        and SNAPSHOT_DATASET_SHA256
        and SNAPSHOT_PUBLICATION_BINDING_SHA256
    ):
        raise Campaign052FeatureError(
            "bind Campaign052 snapshot and publication record before audit"
        )
    _require_file(
        DEFAULT_SNAPSHOT_BINDING,
        SNAPSHOT_PUBLICATION_BINDING_SHA256,
        "Campaign052 snapshot publication binding",
    )
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_protocol()
    _install_engine_globals()
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    _require_file(
        manifest_path, SNAPSHOT_MANIFEST_SHA256, "Campaign052 snapshot manifest"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    existing = sorted(experiment_root.glob("*_campaign052_no_return_audit.json"))
    if existing:
        if (
            len(existing) != 1
            or not NO_RETURN_AUDIT_SHA256
            or _sha256(existing[0]) != NO_RETURN_AUDIT_SHA256
        ):
            raise Campaign052FeatureError(
                "existing Campaign052 audit is ambiguous or unbound"
            )
        return existing[0]
    verification = verify_snapshot_files(manifest, manifest_path, workers)
    prior, foundation, engine, _, candidate49, comparison_engine = campaign044._context()
    eligible_keys = foundation.quality_listing_eligible_keys(prior.load_protocol())
    candidate = _load_candidate_frame(manifest_path, manifest)
    quality_frame, coverage = engine.coverage_and_capacity(
        candidate, eligible_keys, spec, FACTOR_NAME
    )
    del candidate, eligible_keys
    gc.collect()
    if coverage["gate_passed_before_comparison_values"]:
        gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
        expected_order = [str(item["name"]) for item in gate["comparison_factors"]]
        directions = {
            str(item["name"]): str(item["score_direction"])
            for item in gate["comparison_factors"]
        }
        keys, values = engine._sorted_candidate_arrays(quality_frame, FACTOR_NAME)
        catalog, source_verifications = campaign044._build_source_catalog(
            data_root=data_root, workers=workers, verify_files=True
        )
        comparisons: list[dict[str, Any]] = []
        for source in catalog:
            aligned = campaign044._load_aligned_source_values(source, keys)
            for factor in source["factors"]:
                comparisons.append(
                    comparison_engine._aligned_comparison_result(
                        candidate_keys=keys,
                        candidate_values=values,
                        comparison_values=aligned.pop(factor),
                        comparison=factor,
                        direction=directions[factor],
                        gate=gate,
                    )
                )
            del aligned
            gc.collect()
        if len(comparisons) != TERMINAL_LIBRARY_COUNT:
            raise Campaign052FeatureError("complete 66-factor catalog changed")
        _, candidate49_path, candidate49_manifest = engine._comparison_chain(data_root)
        candidate49_verification = candidate49.verify_snapshot_files(
            candidate49_manifest, candidate49_path, workers
        )
        candidate49_values = engine._load_filtered_comparison_values_explicit(
            candidate49_manifest, [candidate49.FACTOR_NAME], keys
        )[candidate49.FACTOR_NAME]
        comparisons.append(
            comparison_engine._aligned_comparison_result(
                candidate_keys=keys,
                candidate_values=values,
                comparison_values=candidate49_values,
                comparison=candidate49.FACTOR_NAME,
                direction="higher",
                gate=gate,
            )
        )
        del candidate49_values
        gc.collect()
        extra_verifications: dict[str, Any] = {}
        for label, source_path, expected_sha, expected_dataset, factor, module in (
            _extra_comparison_sources()
        ):
            _require_file(source_path, expected_sha, f"{label} snapshot manifest")
            source_manifest = json.loads(source_path.read_text(encoding="utf-8"))
            if (
                expected_dataset is not None
                and source_manifest.get("dataset_sha256") != expected_dataset
            ):
                raise Campaign052FeatureError(f"{label} snapshot dataset changed")
            extra_verifications[label] = module.verify_snapshot_files(
                source_manifest, source_path, workers
            )
            comparison_values = engine._load_filtered_comparison_values_explicit(
                source_manifest, [factor], keys
            )[factor]
            comparisons.append(
                comparison_engine._aligned_comparison_result(
                    candidate_keys=keys,
                    candidate_values=values,
                    comparison_values=comparison_values,
                    comparison=factor,
                    direction="higher",
                    gate=gate,
                )
            )
            del comparison_values
            gc.collect()
        observed_order = [str(item["comparison_factor"]) for item in comparisons]
        observed_correlations = [
            float(item["absolute_median_daily_rank_correlation"])
            for item in comparisons
            if item["absolute_median_daily_rank_correlation"] is not None
        ]
        passed = (
            observed_order == expected_order
            and len(comparisons) == COMPARISON_COUNT
            and all(item["gate_passed"] for item in comparisons)
        )
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": True,
            "comparison_factor_count": len(comparisons),
            "comparison_order_matches_preregistration": observed_order
            == expected_order,
            "terminal_66_source_snapshot_verification": source_verifications,
            "candidate49_snapshot_file_verification": candidate49_verification,
            **{
                f"{key}_snapshot_file_verification": value
                for key, value in extra_verifications.items()
            },
            "comparisons": comparisons,
            "maximum_observed_absolute_median_daily_rank_correlation": max(
                observed_correlations
            )
            if observed_correlations
            else None,
            "all_required_comparisons_passed": passed,
        }
        del keys, values
        gc.collect()
    else:
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": False,
            "comparisons": [],
            "all_required_comparisons_passed": False,
            "failure_reason": "coverage_gate_failed",
        }
    admitted = bool(
        coverage["gate_passed_before_comparison_values"]
        and uniqueness["all_required_comparisons_passed"]
    )
    research = prior.research
    run_id = f"{research._timestamp()}_campaign052_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign052_no_return_audit",
        "status": "completed_with_one_admissible_factor_pending_walkforward_preregistration"
        if admitted
        else "completed_zero_admissible_factors_stop_before_historical_returns",
        "run_id": run_id,
        "created_at": research._timestamp(),
        "protocol": {
            "path": str(DEFAULT_PROTOCOL.resolve()),
            "sha256": PROTOCOL_SHA256,
        },
        "candidate_snapshot": {
            "path": str(manifest_path),
            "sha256": SNAPSHOT_MANIFEST_SHA256,
            "dataset_sha256": SNAPSHOT_DATASET_SHA256,
        },
        "snapshot_publication_binding": {
            "path": str(DEFAULT_SNAPSHOT_BINDING.resolve()),
            "sha256": SNAPSHOT_PUBLICATION_BINDING_SHA256,
        },
        "snapshot_file_verification": verification,
        "coverage_and_capacity": {FACTOR_NAME: coverage},
        "uniqueness": {FACTOR_NAME: uniqueness},
        "admissible_factor_names": [FACTOR_NAME] if admitted else [],
        "admissible_factor_count": 1 if admitted else 0,
        "failed_factor_names": [] if admitted else [FACTOR_NAME],
        "next_action": "freeze the exact one-trial Campaign052 walk-forward catalog before reading 2019-2023 returns"
        if admitted
        else "record the no-return rejection and design a genuinely new campaign",
        "source_fields_read": list(RAW_COLUMNS),
        "quarterly_disclosure_fields_read": list(EVENT_FIELDS),
        "quarterly_value_fields_read": [],
        "minute_open_high_low_close_volume_amount_fields_read": [],
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "candidate49_prospective_ledgers_changed": False,
        "second_prospective_candidate_created": False,
        "training_or_model_fitting_performed": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    destination = experiment_root / f"{run_id}.json"
    foundation.atomic_write_json(record, destination)
    return destination


def status(data_root: Path, experiment_root: Path) -> dict[str, Any]:
    _install_engine_globals()
    manifest_path = output_root(data_root.expanduser().resolve()) / "snapshot_manifest.json"
    audits = sorted(
        experiment_root.expanduser().resolve().glob("*_campaign052_no_return_audit.json")
    )
    result = {
        "protocol_path": str(DEFAULT_PROTOCOL.resolve()),
        "protocol_sha256_bound": True,
        "implementation_freeze_sha256_bound": bool(IMPLEMENTATION_FREEZE_SHA256),
        "snapshot_manifest_path": str(manifest_path),
        "snapshot_exists": manifest_path.is_file(),
        "snapshot_sha256_bound": bool(SNAPSHOT_MANIFEST_SHA256),
        "audit_count": len(audits),
        "no_return_audit_sha256_bound": bool(NO_RETURN_AUDIT_SHA256),
        "stock_day_identity_fields_read_by_status": list(RAW_COLUMNS),
        "quarterly_disclosure_fields_read_by_status": list(EVENT_FIELDS),
        "quarterly_value_fields_read_by_status": [],
        "minute_price_volume_amount_fields_read_by_status": [],
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
    for name in ("status", "build", "no-return-audit"):
        command = subparsers.add_parser(name)
        command.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
        command.add_argument("--workers", type=int, default=4)
        if name in {"status", "no-return-audit"}:
            command.add_argument(
                "--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT
            )
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "status":
        payload = status(args.data_root, args.experiment_root)
    elif args.command == "build":
        payload = {
            "manifest": str(build_snapshot(data_root=args.data_root, workers=args.workers))
        }
    else:
        payload = {
            "audit": str(
                run_no_return_audit(
                    data_root=args.data_root,
                    experiment_root=args.experiment_root,
                    workers=args.workers,
                )
            )
        }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
