#!/usr/bin/env python3
"""Build the frozen Campaign058 point-in-time operating-leverage factor.

The factor reads only stock-day identity from the accepted minute snapshot and
the two already-effective quarterly growth states.  It never reads a minute or
daily price, a forward return, or a Candidate49 historical outcome.
"""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign057_features.py"
BASE_RUNNER_SHA256 = "3706ac11c551dd02c8d6d8cf30c95a6f076d6a6e6c5dbba4beb07dde10aca66a"
BASE_FACTOR = "intraday_day_over_day_absolute_return_profile_similarity_238b"
FACTOR_NAME = "quarterly_profit_revenue_growth_spread_pp"
FACTOR_FORMULA = "profit_yoy_state_t - revenue_yoy_state_t"
PROTOCOL_SHA256 = "e3c04b8f736604dca4adb21de367550bb281d4a156b8f990fa942c8757f8011a"
MECHANISM_AUDIT_SHA256 = "226d7535047b0321cf2fece05e63455254b381ae75bac42f3a2d0e184bd5a97f"
COMPARISON_COUNT = 89
COMPARISON_ORDER_SHA256 = "c4100bc923fad2ea5fb8898ccb102afe44307c8ab03ee2df8b0972d9b71bbbc1"
RAW_COLUMNS = ("datetime", "symbol", "provider")
BASE_COLUMNS = ("trade_date", "symbol", "provider")
EVENT_FIELDS = (
    "instrument",
    "report_date",
    "announcement_date",
    "revenue_yoy",
    "profit_yoy",
)
QUARTERLY_PATH = REPO_ROOT / "data/raw/a_share/fundamentals/quarterly_quality.parquet"
QUARTERLY_SHA256 = "3ac901a97928d2ed81ac72e3eaac9bdc148d36cf67b6abe70223699235ef059f"
QUARTERLY_MANIFEST_PATH = REPO_ROOT / "data/metadata/quarterly_quality_manifest.json"
QUARTERLY_MANIFEST_SHA256 = "e3cf654babe37a82393c5530696bc1cc242b736cb88e1947b8444b638125ba8c"
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign058_feature_library_v1"
)
FLOAT_MAX = float(np.finfo(np.float64).max)


def _local_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _local_sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign057 feature runner changed")

_module_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign057", "Campaign058"),
    ("campaign057", "campaign058"),
    ("campaign_057", "campaign_058"),
    (BASE_FACTOR, FACTOR_NAME),
    ("9eb8607e91e952b9e22e436374d68de0a90df251065720bed8a6285f2e3b7ff1", PROTOCOL_SHA256),
    ("c4d81c004de89e9a94bfbea344bd92b5fd56e5fcaa74aa8f9bdcde40a4093e9f", MECHANISM_AUDIT_SHA256),
    ("67e70655596658de91c8285ff998c17e8d2a7d83d0f571d416182e635e8180ae", COMPARISON_ORDER_SHA256),
    ("COMPARISON_COUNT = 80", "COMPARISON_COUNT = 89"),
    ('RAW_COLUMNS = ("datetime", "symbol", "provider", "close")', 'RAW_COLUMNS = ("datetime", "symbol", "provider")'),
):
    _module_source = _module_source.replace(_old, _new)

_old_flag_rewrite = """    ('\"source_open_high_low_close_volume_read\": False,', '\"source_open_high_low_close_volume_read\": True,\\n            \"source_close_read\": True,'),"""
_new_flag_rewrite = """    ('\"source_open_high_low_close_volume_read\": False,', '\"source_open_high_low_close_volume_read\": False,\\n            \"source_close_read\": False,\\n            \"quarterly_value_fields_read\": [\"revenue_yoy\", \"profit_yoy\"],'),"""
if _old_flag_rewrite not in _module_source:
    raise RuntimeError("Campaign057 source-flag adapter was not found")
_module_source = _module_source.replace(_old_flag_rewrite, _new_flag_rewrite, 1)

_insertion_marker = "_generated: dict[str, Any] = {"
if _module_source.count(_insertion_marker) != 1:
    raise RuntimeError("Campaign057 generated-namespace marker changed")
_inner_source_adapter = r'''
_source = _source.replace(
    '            "source_fields_read": list(RAW_COLUMNS),\n',
    '            "source_fields_read": list(RAW_COLUMNS),\n'
    '            "quarterly_source_path": str(QUARTERLY_PATH.resolve()),\n'
    '            "quarterly_source_sha256": QUARTERLY_SHA256,\n'
    '            "quarterly_manifest_path": str(QUARTERLY_MANIFEST_PATH.resolve()),\n'
    '            "quarterly_manifest_sha256": QUARTERLY_MANIFEST_SHA256,\n'
    '            "quarterly_fields_read": list(EVENT_FIELDS),\n',
    1,
)
_source = _source.replace(
    '            "cross_session_lookback": 1,\n'
    '            "prior_session_rule": "immediately_preceding_accepted_local_market_session",\n',
    '            "cross_session_lookback": 0,\n'
    '            "quarterly_state_rule": "strict_next_session_then_independent_per_field_forward_fill",\n',
    1,
)
'''
_module_source = _module_source.replace(
    _insertion_marker,
    _inner_source_adapter + "\n" + _insertion_marker,
    1,
)

_runtime: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign058_features_runtime",
    "QUARTERLY_PATH": QUARTERLY_PATH,
    "QUARTERLY_SHA256": QUARTERLY_SHA256,
    "QUARTERLY_MANIFEST_PATH": QUARTERLY_MANIFEST_PATH,
    "QUARTERLY_MANIFEST_SHA256": QUARTERLY_MANIFEST_SHA256,
    "EVENT_FIELDS": EVENT_FIELDS,
}
exec(compile(_module_source, str(BASE_RUNNER), "exec"), _runtime)
_engine: dict[str, Any] = _runtime["_generated"]

Campaign058FeatureError = _runtime["Campaign058FeatureError"]
DEFAULT_DATA_ROOT: Path = _runtime["DEFAULT_DATA_ROOT"]
DEFAULT_PROTOCOL: Path = _runtime["DEFAULT_PROTOCOL"]
DEFAULT_IMPLEMENTATION_FREEZE: Path = _runtime["DEFAULT_IMPLEMENTATION_FREEZE"]
DEFAULT_CALENDAR: Path = _runtime["DEFAULT_CALENDAR"]
RAW_MANIFEST_RELATIVE: Path = _runtime["RAW_MANIFEST_RELATIVE"]
CLEAN_MANIFEST_RELATIVE: Path = _runtime["CLEAN_MANIFEST_RELATIVE"]
RAW_MANIFEST_SHA256 = _runtime["RAW_MANIFEST_SHA256"]
CLEAN_MANIFEST_SHA256 = _runtime["CLEAN_MANIFEST_SHA256"]
CLEAN_DATASET_SHA256 = _runtime["CLEAN_DATASET_SHA256"]
CALENDAR_SHA256 = _runtime["CALENDAR_SHA256"]
EXPECTED_PARTITIONS = int(_runtime["EXPECTED_PARTITIONS"])
EXPECTED_ROWS = int(_runtime["EXPECTED_ROWS"])
SOURCE_MINUTE_CODES = tuple(_runtime["SOURCE_MINUTE_CODES"])
SOURCE_MINUTE_CODE_SET = frozenset(_runtime["SOURCE_MINUTE_CODE_SET"])
foundation = _runtime["foundation"]
bindings = _runtime["bindings"]
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
FACTOR_NAMES = (FACTOR_NAME,)
FACTOR_DIRECTIONS = {FACTOR_NAME: "higher"}
FACTOR_RANGES = {FACTOR_NAME: (-FLOAT_MAX, FLOAT_MAX)}
FACTOR_FORMULAS = {FACTOR_NAME: FACTOR_FORMULA}


def _comparison_order_digest(items: Iterable[dict[str, Any]]) -> str:
    payload = json.dumps(
        [[str(item["name"]), str(item["score_direction"])] for item in items],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _reconstruct_comparisons(spec: dict[str, Any]) -> list[dict[str, str]]:
    prior_link = (spec.get("source_chain") or {}).get("prior_comparison_catalog") or {}
    prior_path = REPO_ROOT / str(prior_link.get("path") or "")
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    inherited = list(
        ((prior.get("ordered_no_return_gates") or {}).get("uniqueness_after_coverage_only") or {}).get("comparison_factors")
        or []
    )
    appended = list(
        (((spec.get("ordered_no_return_gates") or {}).get("uniqueness_after_coverage_only") or {}).get("appended_comparison_factors"))
        or []
    )
    return [
        {"name": str(item["name"]), "score_direction": str(item["score_direction"])}
        for item in [*inherited, *appended]
    ]


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.is_file() or _local_sha256(path) != PROTOCOL_SHA256:
        raise Campaign058FeatureError(f"Campaign058 no-return protocol changed: {path}")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign058FeatureError("Campaign058 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    comparisons = _reconstruct_comparisons(spec)
    if not (
        spec.get("version") == 1
        and spec.get("kind") == "a_share_three_day_walkforward_campaign058_no_return_preregistration"
        and spec.get("status") == "frozen_before_campaign058_source_candidate_comparison_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("stock_day_identity_fields") or ()) == RAW_COLUMNS
        and tuple(candidate.get("quarterly_event_fields") or ()) == EVENT_FIELDS
        and candidate.get("unit") == "percentage_points"
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and uniqueness.get("comparison_factor_count") == COMPARISON_COUNT
        and len(comparisons) == COMPARISON_COUNT
        and uniqueness.get("comparison_factor_order_sha256") == COMPARISON_ORDER_SHA256
        and _comparison_order_digest(comparisons) == COMPARISON_ORDER_SHA256
        and uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation") == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and finite.get("trial_id") == f"wf058_{FACTOR_NAME}_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("expected_trial_count") == 1
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign058FeatureError("Campaign058 protocol semantics changed")
    return spec


def compute_spread_values(
    profit_yoy: np.ndarray, revenue_yoy: np.ndarray
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    profit = np.asarray(profit_yoy, dtype=np.float64)
    revenue = np.asarray(revenue_yoy, dtype=np.float64)
    if profit.ndim != 1 or revenue.shape != profit.shape:
        raise Campaign058FeatureError("growth-state arrays must be same-length vectors")
    profit_finite = np.isfinite(profit)
    revenue_finite = np.isfinite(revenue)
    with np.errstate(over="ignore", invalid="ignore"):
        spread = profit - revenue
    spread_finite = np.isfinite(spread)
    eligible = profit_finite & revenue_finite & spread_finite
    return (
        np.where(eligible, spread, np.nan),
        eligible,
        {
            "rows": int(len(profit)),
            "eligible_rows": int(eligible.sum()),
            "nonfinite_profit_state_rows": int((~profit_finite).sum()),
            "nonfinite_revenue_state_rows": int((~revenue_finite).sum()),
            "nonfinite_subtraction_rows": int((profit_finite & revenue_finite & ~spread_finite).sum()),
        },
    )


_QUARTERLY_CACHE: tuple[np.ndarray, dict[str, tuple[np.ndarray, np.ndarray]]] | None = None
_QUARTERLY_CACHE_LOCK = threading.Lock()


def _load_quarterly_states() -> tuple[np.ndarray, dict[str, tuple[np.ndarray, np.ndarray]]]:
    global _QUARTERLY_CACHE
    with _QUARTERLY_CACHE_LOCK:
        if _QUARTERLY_CACHE is not None:
            return _QUARTERLY_CACHE
        if (
            _local_sha256(QUARTERLY_PATH) != QUARTERLY_SHA256
            or _local_sha256(QUARTERLY_MANIFEST_PATH) != QUARTERLY_MANIFEST_SHA256
        ):
            raise Campaign058FeatureError("quarterly quality source changed")
        calendar = pd.DatetimeIndex(_engine["load_calendar"]()).normalize()
        calendar_values = calendar.to_numpy(dtype="datetime64[ns]")
        events = pd.read_parquet(
            QUARTERLY_PATH,
            columns=list(EVENT_FIELDS),
            filters=[("announcement_date", "<", pd.Timestamp("2026-01-01"))],
        )
        if tuple(events.columns) != EVENT_FIELDS:
            raise Campaign058FeatureError("quarterly source projection changed")
        events["instrument"] = events["instrument"].astype(str).str.upper()
        for column in ("report_date", "announcement_date"):
            events[column] = pd.to_datetime(events[column], errors="coerce").dt.normalize()
        for column in ("revenue_yoy", "profit_yoy"):
            events[column] = pd.to_numeric(events[column], errors="coerce")
        if (
            events.empty
            or events[["instrument", "report_date", "announcement_date"]].isna().any().any()
            or events.duplicated(["instrument", "report_date"]).any()
        ):
            raise Campaign058FeatureError("quarterly event identities changed")
        announcements = events["announcement_date"].to_numpy(dtype="datetime64[ns]")
        positions = np.searchsorted(calendar_values, announcements, side="right")
        events = events.loc[positions < len(calendar_values)].copy()
        events["effective_position"] = positions[positions < len(calendar_values)]
        events = (
            events.sort_values(
                ["instrument", "effective_position", "report_date", "announcement_date"],
                kind="stable",
            )
            .drop_duplicates(["instrument", "effective_position"], keep="last")
            .reset_index(drop=True)
        )
        by_symbol: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for symbol, group in events.groupby("instrument", sort=False):
            states = group[["revenue_yoy", "profit_yoy"]].ffill()
            values, _, _ = compute_spread_values(
                states["profit_yoy"].to_numpy(dtype=np.float64),
                states["revenue_yoy"].to_numpy(dtype=np.float64),
            )
            by_symbol[str(symbol)] = (
                group["effective_position"].to_numpy(dtype=np.int64),
                values,
            )
        _QUARTERLY_CACHE = (calendar_values, by_symbol)
        return _QUARTERLY_CACHE


def extract_quarterly_spread_states(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[dict[pd.Timestamp, float], dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign058FeatureError(
            f"unexpected raw identity columns for {symbol}: {tuple(raw.columns)}"
        )
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    if (
        work.empty
        or work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign058FeatureError(f"raw stock-day identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    codes = work.groupby("trade_date", sort=True, observed=True)["minute_code"].agg(
        lambda values: frozenset(int(value) for value in values)
    )
    if (
        counts.empty
        or not counts.eq(len(SOURCE_MINUTE_CODES)).all()
        or not codes.eq(SOURCE_MINUTE_CODE_SET).all()
    ):
        raise Campaign058FeatureError(f"raw 241-row identity grid changed for {symbol}")
    dates = pd.DatetimeIndex(counts.index).normalize()
    calendar_values, states_by_symbol = _load_quarterly_states()
    trade_values = dates.to_numpy(dtype="datetime64[ns]")
    trade_positions = np.searchsorted(calendar_values, trade_values, side="left")
    if (
        (trade_positions >= len(calendar_values)).any()
        or not np.array_equal(calendar_values[trade_positions], trade_values)
    ):
        raise Campaign058FeatureError(f"raw dates are outside the accepted calendar for {symbol}")
    values = np.full(len(dates), np.nan, dtype=np.float64)
    state = states_by_symbol.get(symbol.upper())
    has_effective_event = np.zeros(len(dates), dtype=bool)
    if state is not None:
        event_positions, event_values = state
        selected = np.searchsorted(event_positions, trade_positions, side="right") - 1
        has_effective_event = selected >= 0
        values[has_effective_event] = event_values[selected[has_effective_event]]
    return (
        {pd.Timestamp(date): float(values[index]) for index, date in enumerate(dates)},
        {
            "source_sessions": int(len(dates)),
            "source_identity_rows": int(len(work)),
            "sessions_without_prior_effective_quarterly_event": int((~has_effective_event).sum()),
            "sessions_with_nonfinite_growth_spread_state": int((has_effective_event & ~np.isfinite(values)).sum()),
            "sessions_with_finite_growth_spread_state": int(np.isfinite(values).sum()),
        },
    )


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


def compute_output_frame(
    base_frame: pd.DataFrame,
    states: dict[pd.Timestamp, float],
    _calendar_previous: dict[pd.Timestamp, pd.Timestamp],
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign058FeatureError(
            f"unexpected joint-base columns for {symbol}: {tuple(base_frame.columns)}"
        )
    base = base_frame.copy()
    base["trade_date"] = pd.to_datetime(base["trade_date"], errors="coerce").dt.normalize()
    base["symbol"] = base["symbol"].astype(str).str.upper()
    base["provider"] = base["provider"].astype(str).str.lower()
    if base.empty:
        return empty_output_frame(), {"base_rows": 0}
    if (
        base["trade_date"].isna().any()
        or base.duplicated(["trade_date", "symbol"]).any()
        or set(base["symbol"].unique()) != {symbol.upper()}
        or set(base["provider"].unique()) != {"tushare"}
    ):
        raise Campaign058FeatureError(f"joint-base identity changed for {symbol}")
    base = base.sort_values("trade_date", kind="stable").reset_index(drop=True)
    missing_source_dates = [date for date in base["trade_date"] if pd.Timestamp(date) not in states]
    if missing_source_dates:
        raise Campaign058FeatureError(f"joint-base date is absent from raw identity for {symbol}")
    values = np.asarray([states[pd.Timestamp(date)] for date in base["trade_date"]], dtype=np.float64)
    eligible = np.isfinite(values)
    frame = pd.DataFrame(
        {
            "trade_date": base["trade_date"],
            "symbol": symbol.upper(),
            "provider": "eastmoney_quarterly_quality",
            FACTOR_NAME: np.where(eligible, values, np.nan),
            f"{FACTOR_NAME}_eligible": eligible,
        }
    ).loc[:, OUTPUT_COLUMNS]
    return frame, {
        "base_rows": int(len(frame)),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__missing_or_nonfinite_state_rows": int((~eligible).sum()),
    }


def _validate_manifest(manifest: dict[str, Any]) -> None:
    files = list(manifest.get("files") or [])
    quality = manifest.get("quality") or {}
    eligible = (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    if not (
        manifest.get("schema_version") == 1
        and manifest.get("kind") == "a_share_three_day_walkforward_campaign058_feature_snapshot"
        and manifest.get("status") == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_open_high_low_close_volume_read") is False
        and manifest.get("source_close_read") is False
        and manifest.get("source_amount_read") is False
        and manifest.get("quarterly_value_fields_read") == ["revenue_yoy", "profit_yoy"]
        and manifest.get("quarterly_source_path") == str(QUARTERLY_PATH.resolve())
        and manifest.get("quarterly_source_sha256") == QUARTERLY_SHA256
        and manifest.get("quarterly_manifest_path") == str(QUARTERLY_MANIFEST_PATH.resolve())
        and manifest.get("quarterly_manifest_sha256") == QUARTERLY_MANIFEST_SHA256
        and manifest.get("quarterly_fields_read") == list(EVENT_FIELDS)
        and manifest.get("cross_session_lookback") == 0
        and manifest.get("quarterly_state_rule") == "strict_next_session_then_independent_per_field_forward_fill"
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == FACTOR_DIRECTIONS
        and manifest.get("factor_formulas") == FACTOR_FORMULAS
        and manifest.get("protocol_sha256") == PROTOCOL_SHA256
        and manifest.get("mechanism_overlap_audit_sha256") == MECHANISM_AUDIT_SHA256
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and len(files) == EXPECTED_PARTITIONS
        and manifest.get("rows") == EXPECTED_ROWS
        and quality.get("base_rows") == EXPECTED_ROWS
        and quality.get(f"{FACTOR_NAME}__eligible_rows") == eligible
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("candidate49_historical_return_read") is False
        and manifest.get("candidate49_ledgers_changed") is False
        and manifest.get("training_or_model_fitting_performed") is False
        and manifest.get("current_scoring_selection_sizing_or_orders_performed") is False
        and manifest.get("prospective_candidate_activation_created") is False
        and manifest.get("provider_request_issued") is False
    ):
        raise Campaign058FeatureError("Campaign058 snapshot semantics changed")


for _name, _value in {
    "DEFAULT_PROTOCOL": DEFAULT_PROTOCOL,
    "FACTOR_NAME": FACTOR_NAME,
    "FACTOR_FORMULA": FACTOR_FORMULA,
    "FACTOR_NAMES": FACTOR_NAMES,
    "FACTOR_DIRECTIONS": FACTOR_DIRECTIONS,
    "FACTOR_RANGES": FACTOR_RANGES,
    "FACTOR_FORMULAS": FACTOR_FORMULAS,
    "PROTOCOL_SHA256": PROTOCOL_SHA256,
    "MECHANISM_AUDIT_SHA256": MECHANISM_AUDIT_SHA256,
    "COMPARISON_COUNT": COMPARISON_COUNT,
    "COMPARISON_ORDER_SHA256": COMPARISON_ORDER_SHA256,
    "RAW_COLUMNS": RAW_COLUMNS,
    "BASE_COLUMNS": BASE_COLUMNS,
    "OUTPUT_COLUMNS": OUTPUT_COLUMNS,
    "OUTPUT_RUN_ID": OUTPUT_RUN_ID,
    "LOWER_BOUND": -FLOAT_MAX,
    "UPPER_BOUND": FLOAT_MAX,
    "QUARTERLY_PATH": QUARTERLY_PATH,
    "QUARTERLY_SHA256": QUARTERLY_SHA256,
    "QUARTERLY_MANIFEST_PATH": QUARTERLY_MANIFEST_PATH,
    "QUARTERLY_MANIFEST_SHA256": QUARTERLY_MANIFEST_SHA256,
    "EVENT_FIELDS": EVENT_FIELDS,
    "_load_protocol": load_protocol,
    "extract_amount_profiles": extract_quarterly_spread_states,
    "empty_output_frame": empty_output_frame,
    "compute_output_frame": compute_output_frame,
    "_validate_manifest": _validate_manifest,
}.items():
    _engine[_name] = _value

build_snapshot = _engine["build_snapshot"]
verify_snapshot_files = _engine["verify_snapshot_files"]
output_root = _engine["output_root"]


def status(data_root: Path) -> dict[str, Any]:
    result = _engine["status"](data_root)
    result.update(
        {
            "quarterly_source_path": str(QUARTERLY_PATH.resolve()),
            "quarterly_source_sha256": QUARTERLY_SHA256,
            "quarterly_fields_read_by_build": list(EVENT_FIELDS),
            "minute_price_or_activity_fields_read_by_build": False,
        }
    )
    return result


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    build.add_argument("--workers", type=int, default=4)
    inspect = subparsers.add_parser("status")
    inspect.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.command == "build":
        payload = {"snapshot_manifest": str(build_snapshot(data_root=args.data_root, workers=args.workers))}
    elif args.command == "verify":
        payload = verify_snapshot_files(args.manifest, workers=args.workers)
    else:
        payload = status(args.data_root)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
