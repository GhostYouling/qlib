#!/usr/bin/env python3
"""Build the frozen Campaign059 market-direction sign-agreement factor.

The factor uses only the canonical continuous-session close-return grid and
the already frozen leave-one-out market return sum/count benchmark.  It never
reads a daily price, forward return, or Candidate49 historical outcome.
"""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign004_features as campaign004


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign057_features.py"
BASE_RUNNER_SHA256 = "3706ac11c551dd02c8d6d8cf30c95a6f076d6a6e6c5dbba4beb07dde10aca66a"
MARKET_HELPER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign004_features.py"
MARKET_HELPER_SHA256 = "46b4c8b36698e64612b4b2c98e8cb4e81041100327d93e862722a3c5fb84b33c"
BASE_FACTOR = "intraday_day_over_day_absolute_return_profile_similarity_238b"
FACTOR_NAME = "intraday_market_directional_sign_agreement_238m"
FACTOR_FORMULA = (
    "equal-sign informative position count divided by jointly nonzero informative "
    "position count across exactly 238 synchronous within-half stock and frozen "
    "leave-one-out market signed log-close returns"
)
PROTOCOL_SHA256 = "50cf7b067b1dfd5dc31d6c6ef85090788abdf6a2bbc054eda6e7c3824d5c60d6"
MECHANISM_AUDIT_SHA256 = "46d7c44bb35993a36ff1b53f126049d2e1f50d40768857d138a3e2f32b91c45e"
COMPARISON_COUNT = 90
COMPARISON_ORDER_SHA256 = "09bc36308ce5d3af7a484fd9b233a02a9f5d3f37cd5169d400ab72737071caee"
MARKET_BENCHMARK_MANIFEST_SHA256 = "954b71d571bcd89cbf4eae4eedad014091a9b40e6b2b083e0071cbf870634ef0"
MARKET_BENCHMARK_BYTE_SHA256 = "5437805f84c5c637904a62664cc3ec677e0155f5a215b0df7c38ed0cc35b88bf"
MARKET_BENCHMARK_FRAME_SHA256 = "5412520f379a3d7584f18a0fd5a0b55fd8b68ed3a49d76ff6430a330eee9d4a1"
MINIMUM_LEAVE_ONE_OUT_PEERS = 50
MINIMUM_INFORMATIVE_POSITIONS = 60
SELECTED_CLOSE_COUNT = 240
SELECTED_BAR_COUNT = 238
RAW_COLUMNS = ("datetime", "symbol", "provider", "close")
BASE_COLUMNS = ("trade_date", "symbol", "provider")
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign059_feature_library_v1"
)


def _local_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


for _path, _expected, _label in (
    (BASE_RUNNER, BASE_RUNNER_SHA256, "frozen Campaign057 feature runner"),
    (MARKET_HELPER, MARKET_HELPER_SHA256, "frozen market benchmark helper"),
):
    if _local_sha256(_path) != _expected:
        raise RuntimeError(f"{_label} changed")

_module_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign057", "Campaign059"),
    ("campaign057", "campaign059"),
    ("campaign_057", "campaign_059"),
    (BASE_FACTOR, FACTOR_NAME),
    ("9eb8607e91e952b9e22e436374d68de0a90df251065720bed8a6285f2e3b7ff1", PROTOCOL_SHA256),
    ("c4d81c004de89e9a94bfbea344bd92b5fd56e5fcaa74aa8f9bdcde40a4093e9f", MECHANISM_AUDIT_SHA256),
    ("67e70655596658de91c8285ff998c17e8d2a7d83d0f571d416182e635e8180ae", COMPARISON_ORDER_SHA256),
    ("COMPARISON_COUNT = 80", "COMPARISON_COUNT = 90"),
):
    _module_source = _module_source.replace(_old, _new)

_insertion_marker = "_generated: dict[str, Any] = {"
if _module_source.count(_insertion_marker) != 1:
    raise RuntimeError("Campaign057 generated-namespace marker changed")
_inner_source_adapter = r'''
_source = _source.replace(
    '            "cross_session_lookback": 1,\n'
    '            "prior_session_rule": "immediately_preceding_accepted_local_market_session",\n'
    '            "bridge_missing_or_suspended_prior_session": False,\n',
    '            "cross_session_lookback": 0,\n'
    '            "market_benchmark_manifest_sha256": MARKET_BENCHMARK_MANIFEST_SHA256,\n'
    '            "market_benchmark_byte_sha256": MARKET_BENCHMARK_BYTE_SHA256,\n'
    '            "market_benchmark_frame_sha256": MARKET_BENCHMARK_FRAME_SHA256,\n'
    '            "market_benchmark_fields_read": list(campaign004.market.BENCHMARK_COLUMNS),\n'
    '            "minimum_leave_one_out_peers_per_position": MINIMUM_LEAVE_ONE_OUT_PEERS,\n'
    '            "minimum_informative_positions": MINIMUM_INFORMATIVE_POSITIONS,\n',
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
    "__name__": "a_share_three_day_walkforward_campaign059_features_runtime",
    "campaign004": campaign004,
    "MARKET_BENCHMARK_MANIFEST_SHA256": MARKET_BENCHMARK_MANIFEST_SHA256,
    "MARKET_BENCHMARK_BYTE_SHA256": MARKET_BENCHMARK_BYTE_SHA256,
    "MARKET_BENCHMARK_FRAME_SHA256": MARKET_BENCHMARK_FRAME_SHA256,
    "MINIMUM_LEAVE_ONE_OUT_PEERS": MINIMUM_LEAVE_ONE_OUT_PEERS,
    "MINIMUM_INFORMATIVE_POSITIONS": MINIMUM_INFORMATIVE_POSITIONS,
}
exec(compile(_module_source, str(BASE_RUNNER), "exec"), _runtime)
_engine: dict[str, Any] = _runtime["_generated"]

Campaign059FeatureError = _runtime["Campaign059FeatureError"]
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
CONTINUOUS_MINUTE_CODES = tuple(_runtime["CONTINUOUS_MINUTE_CODES"])
CONTINUOUS_MINUTE_CODE_SET = frozenset(_runtime["CONTINUOUS_MINUTE_CODE_SET"])
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
FACTOR_RANGES = {FACTOR_NAME: (0.0, 1.0)}
FACTOR_FORMULAS = {FACTOR_NAME: FACTOR_FORMULA}


def _comparison_order_digest(items: Iterable[dict[str, Any]]) -> str:
    payload = json.dumps(
        [[str(item["name"]), str(item["score_direction"])] for item in items],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def reconstruct_comparisons(spec: dict[str, Any]) -> list[dict[str, str]]:
    prior_link = (spec.get("source_chain") or {}).get("prior_comparison_catalog") or {}
    prior_path = REPO_ROOT / str(prior_link.get("path") or "")
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    older_link = (prior.get("source_chain") or {}).get("prior_comparison_catalog") or {}
    older_path = REPO_ROOT / str(older_link.get("path") or "")
    older = json.loads(older_path.read_text(encoding="utf-8"))
    inherited = list(
        ((older.get("ordered_no_return_gates") or {}).get("uniqueness_after_coverage_only") or {}).get("comparison_factors")
        or []
    )
    prior_appended = list(
        ((prior.get("ordered_no_return_gates") or {}).get("uniqueness_after_coverage_only") or {}).get("appended_comparison_factors")
        or []
    )
    current_appended = list(
        ((spec.get("ordered_no_return_gates") or {}).get("uniqueness_after_coverage_only") or {}).get("appended_comparison_factors")
        or []
    )
    return [
        {"name": str(item["name"]), "score_direction": str(item["score_direction"])}
        for item in [*inherited, *prior_appended, *current_appended]
    ]


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.is_file() or _local_sha256(path) != PROTOCOL_SHA256:
        raise Campaign059FeatureError(f"Campaign059 no-return protocol changed: {path}")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign059FeatureError("Campaign059 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    source_chain = spec.get("source_chain") or {}
    benchmark_manifest = source_chain.get("frozen_market_benchmark_manifest") or {}
    benchmark_frame = source_chain.get("frozen_market_benchmark_frame") or {}
    comparisons = reconstruct_comparisons(spec)
    if not (
        spec.get("version") == 1
        and spec.get("kind") == "a_share_three_day_walkforward_campaign059_no_return_preregistration"
        and spec.get("status") == "frozen_before_campaign059_source_benchmark_candidate_comparison_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_fields_allowed") or ()) == RAW_COLUMNS
        and tuple(candidate.get("source_fields_used_by_formula") or ()) == RAW_COLUMNS
        and tuple(candidate.get("benchmark_fields_allowed") or ()) == tuple(campaign004.market.BENCHMARK_COLUMNS)
        and candidate.get("selected_close_count") == SELECTED_CLOSE_COUNT
        and candidate.get("within_half_return_count") == SELECTED_BAR_COUNT
        and candidate.get("minimum_leave_one_out_peers_per_return_position") == MINIMUM_LEAVE_ONE_OUT_PEERS
        and candidate.get("minimum_informative_positions") == MINIMUM_INFORMATIVE_POSITIONS
        and candidate.get("valid_range") == [0.0, 1.0]
        and benchmark_manifest.get("sha256") == MARKET_BENCHMARK_MANIFEST_SHA256
        and benchmark_frame.get("sha256") == MARKET_BENCHMARK_BYTE_SHA256
        and benchmark_frame.get("frame_sha256") == MARKET_BENCHMARK_FRAME_SHA256
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
        and uniqueness.get("all_90_must_pass") is True
        and uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation") == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and finite.get("trial_id") == f"wf059_{FACTOR_NAME}_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("expected_trial_count") == 1
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign059FeatureError("Campaign059 protocol semantics changed")
    return spec


def compute_sign_agreement_values(
    stock_returns: np.ndarray,
    market_returns: np.ndarray,
    sufficient_peers: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    stock = np.asarray(stock_returns, dtype=float)
    market = np.asarray(market_returns, dtype=float)
    peers = np.asarray(sufficient_peers, dtype=bool)
    if (
        stock.ndim != 2
        or stock.shape[1] != SELECTED_BAR_COUNT
        or market.shape != stock.shape
        or peers.shape != (len(stock),)
    ):
        raise Campaign059FeatureError("Campaign059 return arrays are invalid")
    finite_vectors = np.isfinite(stock).all(axis=1) & np.isfinite(market).all(axis=1)
    informative = (stock != 0.0) & (market != 0.0)
    informative_count = informative.sum(axis=1)
    agreements = informative & (np.signbit(stock) == np.signbit(market))
    agreement_count = agreements.sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        values = np.divide(
            agreement_count,
            informative_count,
            out=np.full(len(stock), np.nan, dtype=float),
            where=informative_count > 0,
        )
    finite_values = np.isfinite(values)
    in_range = (values >= 0.0) & (values <= 1.0)
    enough_informative = informative_count >= MINIMUM_INFORMATIVE_POSITIONS
    eligible = finite_vectors & peers & enough_informative & finite_values & in_range
    return (
        np.where(eligible, values, np.nan),
        eligible,
        {
            "rows": int(len(stock)),
            "eligible_rows": int(eligible.sum()),
            "nonfinite_stock_or_market_vector_rows": int((~finite_vectors).sum()),
            "insufficient_peer_rows": int((finite_vectors & ~peers).sum()),
            "insufficient_informative_position_rows": int((finite_vectors & peers & ~enough_informative).sum()),
            "informative_positions": int(informative[finite_vectors & peers].sum()),
            "agreement_positions": int(agreements[finite_vectors & peers].sum()),
            "exact_zero_stock_return_positions": int((stock == 0.0).sum()),
            "exact_zero_market_return_positions": int((market == 0.0).sum()),
            "range_or_nonfinite_score_rows": int((finite_vectors & peers & enough_informative & (~finite_values | ~in_range)).sum()),
        },
    )


def extract_signed_return_profiles(
    raw: pd.DataFrame,
    *,
    symbol: str,
) -> tuple[dict[pd.Timestamp, np.ndarray], dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign059FeatureError(f"unexpected raw columns for {symbol}: {tuple(raw.columns)}")
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["close"] = pd.to_numeric(work["close"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or work.empty
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign059FeatureError(f"raw identity changed for {symbol}")
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
        raise Campaign059FeatureError(f"raw minute grid changed for {symbol}")
    continuous = work.loc[
        work["minute_code"].isin(CONTINUOUS_MINUTE_CODE_SET),
        ["trade_date", "minute_code", "close"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"], categories=CONTINUOUS_MINUTE_CODES, ordered=True
    )
    continuous = continuous.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = tuple(pd.Timestamp(value) for value in counts.index)
    if len(continuous) != len(dates) * SELECTED_CLOSE_COUNT:
        raise Campaign059FeatureError(f"continuous grid changed for {symbol}")
    closes = continuous["close"].to_numpy(dtype=float).reshape(len(dates), SELECTED_CLOSE_COUNT)
    finite = np.isfinite(closes).all(axis=1)
    positive = (closes > 0.0).all(axis=1)
    valid = finite & positive
    returns = np.full((len(dates), SELECTED_BAR_COUNT), np.nan, dtype=float)
    if valid.any():
        log_close = np.log(closes[valid])
        returns[valid, :119] = np.diff(log_close[:, :120], axis=1)
        returns[valid, 119:] = np.diff(log_close[:, 120:], axis=1)
    return (
        {date: returns[index].copy() for index, date in enumerate(dates)},
        {
            "source_sessions": len(dates),
            "source_rows": len(work),
            "source_nonfinite_close_grid_rows": int((~finite).sum()),
            "source_nonpositive_close_grid_rows": int((finite & ~positive).sum()),
            "source_valid_close_grid_rows": int(valid.sum()),
            "source_exact_zero_return_positions": int((returns[valid] == 0.0).sum()),
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


_MARKET_BENCHMARK_CACHE: Any = None
_MARKET_BENCHMARK_LOCK = threading.Lock()


def _load_market_benchmark() -> Any:
    global _MARKET_BENCHMARK_CACHE
    with _MARKET_BENCHMARK_LOCK:
        if _MARKET_BENCHMARK_CACHE is None:
            value = campaign004._load_market_benchmark(DEFAULT_DATA_ROOT)
            if getattr(value, "frame_sha256", None) != MARKET_BENCHMARK_FRAME_SHA256:
                raise Campaign059FeatureError("frozen market benchmark changed")
            _MARKET_BENCHMARK_CACHE = value
    return _MARKET_BENCHMARK_CACHE


def compute_output_frame(
    base_frame: pd.DataFrame,
    profiles: dict[pd.Timestamp, np.ndarray],
    _calendar_previous: dict[pd.Timestamp, pd.Timestamp],
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign059FeatureError(f"unexpected base columns for {symbol}: {tuple(base_frame.columns)}")
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
        raise Campaign059FeatureError(f"base identity changed for {symbol}")
    base = base.sort_values("trade_date", kind="stable").reset_index(drop=True)
    missing = np.full(SELECTED_BAR_COUNT, np.nan, dtype=float)
    stock = np.empty((len(base), SELECTED_BAR_COUNT), dtype=float)
    current_missing = np.zeros(len(base), dtype=bool)
    for index, date in enumerate(base["trade_date"]):
        value = profiles.get(pd.Timestamp(date))
        if value is None:
            current_missing[index] = True
            stock[index] = missing
        else:
            stock[index] = value
    if current_missing.any():
        raise Campaign059FeatureError(f"base current session is absent from raw source for {symbol}")
    benchmark = _load_market_benchmark()
    sums, counts = campaign004.market._benchmark_for_dates(
        benchmark, list(base["trade_date"])
    )
    own = np.where(np.isfinite(stock), stock, 0.0)
    own_count = np.isfinite(stock).astype(np.int32)
    peer_counts = counts.astype(np.int64) - own_count
    peer_sums = sums - own
    sufficient = (peer_counts >= MINIMUM_LEAVE_ONE_OUT_PEERS).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        leave_one_out = np.divide(
            peer_sums,
            peer_counts,
            out=np.full_like(peer_sums, np.nan, dtype=float),
            where=peer_counts > 0,
        )
    values, eligible, pair_quality = compute_sign_agreement_values(
        stock, leave_one_out, sufficient
    )
    frame = pd.DataFrame(
        {
            "trade_date": base["trade_date"],
            "symbol": symbol.upper(),
            "provider": "tushare_leave_one_out_market",
            FACTOR_NAME: values,
            f"{FACTOR_NAME}_eligible": eligible,
        }
    ).loc[:, OUTPUT_COLUMNS]
    quality = {
        "base_rows": int(len(frame)),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
    }
    for key, value in pair_quality.items():
        if key not in {"rows", "eligible_rows"}:
            quality[f"{FACTOR_NAME}__{key}"] = value
    return frame, quality


def _validate_manifest(manifest: dict[str, Any]) -> None:
    files = list(manifest.get("files") or [])
    quality = manifest.get("quality") or {}
    eligible = (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    if not (
        manifest.get("schema_version") == 1
        and manifest.get("kind") == "a_share_three_day_walkforward_campaign059_feature_snapshot"
        and manifest.get("status") == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_open_high_low_close_volume_read") is True
        and manifest.get("source_close_read") is True
        and manifest.get("source_amount_read") is False
        and manifest.get("cross_session_lookback") == 0
        and manifest.get("market_benchmark_manifest_sha256") == MARKET_BENCHMARK_MANIFEST_SHA256
        and manifest.get("market_benchmark_byte_sha256") == MARKET_BENCHMARK_BYTE_SHA256
        and manifest.get("market_benchmark_frame_sha256") == MARKET_BENCHMARK_FRAME_SHA256
        and manifest.get("market_benchmark_fields_read") == list(campaign004.market.BENCHMARK_COLUMNS)
        and manifest.get("minimum_leave_one_out_peers_per_position") == MINIMUM_LEAVE_ONE_OUT_PEERS
        and manifest.get("minimum_informative_positions") == MINIMUM_INFORMATIVE_POSITIONS
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
        raise Campaign059FeatureError("Campaign059 snapshot semantics changed")


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
    "SELECTED_BAR_COUNT": SELECTED_BAR_COUNT,
    "RAW_COLUMNS": RAW_COLUMNS,
    "BASE_COLUMNS": BASE_COLUMNS,
    "OUTPUT_COLUMNS": OUTPUT_COLUMNS,
    "OUTPUT_RUN_ID": OUTPUT_RUN_ID,
    "LOWER_BOUND": 0.0,
    "UPPER_BOUND": 1.0,
    "_load_protocol": load_protocol,
    "extract_amount_profiles": extract_signed_return_profiles,
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
            "market_benchmark_manifest_sha256": MARKET_BENCHMARK_MANIFEST_SHA256,
            "market_benchmark_byte_sha256": MARKET_BENCHMARK_BYTE_SHA256,
            "market_benchmark_frame_sha256": MARKET_BENCHMARK_FRAME_SHA256,
            "market_benchmark_fields_read_by_build": list(campaign004.market.BENCHMARK_COLUMNS),
            "daily_price_or_forward_return_read_by_build": False,
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
