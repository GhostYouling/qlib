#!/usr/bin/env python3
"""Build and no-return audit the frozen Campaign021 market-delay factor.

Campaign019 supplies the tested checkpoint and comparison orchestration.
This wrapper changes only the campaign namespace and candidate computation,
loads the already-frozen leave-one-out market benchmark, and appends the
terminal Campaign019 and Campaign020 factors as comparisons 41 and 42.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

try:
    import scripts.a_share_three_day_walkforward_campaign004_features as campaign004
    import scripts.a_share_three_day_walkforward_campaign019_features as campaign019
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign004_features as campaign004
    import a_share_three_day_walkforward_campaign019_features as campaign019


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN019_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign019_features.py"
)
CAMPAIGN019_FEATURE_RUNNER_SHA256 = (
    "79c39072bc2515541acdaffdb3c3f43a5fabb1e4e8d13ba0e47c8ee4e6477a48"
)
OLD_FACTOR = "intraday_bar_direction_continuity_238p"
FACTOR_NAME = "intraday_market_response_delay_asymmetry_236p"
MECHANISM_AUDIT_SHA256 = (
    "056988a36deb220a221fe46bde5e9554628cd078f258684869ca9dc30c262ad7"
)
PROTOCOL_SHA256 = (
    "6daee3570af9fa29ca29bb0e3b642b525d9822c8f94b99e3b1e36e20e37e43b7"
)

# Bind these immutable fingerprints only after the corresponding artifacts exist.
SNAPSHOT_MANIFEST_SHA256 = (
    "05b1d511d9c53c1167ee97015c762b0882ab21469258fd9562eab7b28e8a24f2"
)
SNAPSHOT_DATASET_SHA256 = (
    "1557eb872713ee5456fdfd0caef1d6aae6b2e9d43951afd5ca7f7b93766429a2"
)
NO_RETURN_AUDIT_SHA256 = (
    "b198a2deec6d31634adb4ac00b10f8c22a18cd70739f8ce10c2dd2cd70068623"
)

MARKET_BENCHMARK_MANIFEST_SHA256 = (
    "954b71d571bcd89cbf4eae4eedad014091a9b40e6b2b083e0071cbf870634ef0"
)
MARKET_BENCHMARK_BYTE_SHA256 = (
    "5437805f84c5c637904a62664cc3ec677e0155f5a215b0df7c38ed0cc35b88bf"
)
MARKET_BENCHMARK_FRAME_SHA256 = (
    "5412520f379a3d7584f18a0fd5a0b55fd8b68ed3a49d76ff6430a330eee9d4a1"
)
MINIMUM_LEAVE_ONE_OUT_PEERS = 50
RETURN_POSITIONS = 238
WITHIN_HALF_ADJACENT_PAIR_COUNT = 236
ENDPOINT_TOLERANCE = 1e-12

C19_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign019_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign019_feature_library_v1/snapshot_manifest.json"
)
C19_SNAPSHOT_SHA256 = (
    "7c4f7268f33af3274a9057241b9bd45df3c2565729a684a07f48105cdf9474cb"
)
C19_DATASET_SHA256 = (
    "66efe683268dbcc681591ee9918ba2948f3c4420232c4e1f4c57371d0ac24ecc"
)
C19_FACTOR_NAMES = ("intraday_bar_direction_continuity_238p",)
C19_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C19_FACTOR_NAMES[0],
    f"{C19_FACTOR_NAMES[0]}_eligible",
)

C20_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign020_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign020_feature_library_v1/snapshot_manifest.json"
)
C20_SNAPSHOT_SHA256 = (
    "a776c1bcfb3d573ea7583be843ee42b1b6a368ccc8d80dbd382bf56fa2115fdd"
)
C20_DATASET_SHA256 = (
    "39cda0c04c87c94886ac9f0f99453a2db627fa5cd64096ba33ef92df91223faa"
)
C20_FACTOR_NAMES = ("quarterly_announcement_freshness_60s",)
C20_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C20_FACTOR_NAMES[0],
    f"{C20_FACTOR_NAMES[0]}_eligible",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN019_FEATURE_RUNNER) != CAMPAIGN019_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign019 feature orchestration fingerprint changed")

_source = campaign019._source
for _old, _new in (
    ("Campaign019", "Campaign021"),
    ("campaign019", "campaign021"),
    ("campaign_019", "campaign_021"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "29e7dc24776e458cd471414a076029dfb232fb5299f10fd333b6f9c4e7522606",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "de68ec246a0b0944ef75edc2594e8909c89b9118de3cd01bdad7cc1b902f011f",
        PROTOCOL_SHA256,
    ),
    (
        "7c4f7268f33af3274a9057241b9bd45df3c2565729a684a07f48105cdf9474cb",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "66efe683268dbcc681591ee9918ba2948f3c4420232c4e1f4c57371d0ac24ecc",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "ccb7c4582a4944fe6c26423d07d25cefc488f3200fb70e45ec738ea8c716f10e",
        NO_RETURN_AUDIT_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_source = _source.replace(
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "open", "close")',
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "close")',
    1,
)
_source = _source.replace(
    "FACTOR_RANGES = {FACTOR_NAME: (0.0, 1.0)}",
    "FACTOR_RANGES = {FACTOR_NAME: (-2.0, 2.0)}",
    1,
)
_old_formula = '''FACTOR_FORMULA = (
    "count(s_i*s_(i+1)>0) / count(s_i!=0 and s_(i+1)!=0) across "
    "exactly 238 within-half adjacent pairs, where "
    "s_i=sign(log(close_i/open_i))"
)'''
_new_formula = '''FACTOR_FORMULA = (
    "population PearsonCorr(r_i,t,m_-i,t-1) minus population "
    "PearsonCorr(r_i,t-1,m_-i,t) over exactly 236 adjacent return "
    "pairs wholly inside the two trading halves"
)'''
if _old_formula not in _source:
    raise RuntimeError("Campaign019 formula block was not found")
_source = _source.replace(_old_formula, _new_formula, 1)
if "ENDPOINT_TOLERANCE = None" not in _source:
    raise RuntimeError("Campaign019 endpoint constant was not found")
_source = _source.replace(
    "ENDPOINT_TOLERANCE = None",
    "ENDPOINT_TOLERANCE = 1e-12",
    1,
)

_new_loader = r'''def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate the protocol frozen before any Campaign021 value."""

    path = path.expanduser().resolve()
    if not PROTOCOL_SHA256:
        raise Campaign021FeatureError(
            "bind PROTOCOL_SHA256 before building or auditing Campaign021 values"
        )
    _require_file(path, PROTOCOL_SHA256, "Campaign021 no-return protocol")
    _require_file(
        MECHANISM_AUDIT,
        MECHANISM_AUDIT_SHA256,
        "Campaign021 mechanism-overlap audit",
    )
    spec = research.load_json_record(
        path,
        kind="a_share_three_day_walkforward_campaign021_no_return_preregistration",
    )
    candidates = list(spec.get("candidates") or [])
    names = tuple(str(item.get("name") or "") for item in candidates)
    formulas = {
        str(item.get("name") or ""): str(item.get("formula") or "")
        for item in candidates
    }
    directions = {
        str(item.get("name") or ""): str(item.get("direction") or "")
        for item in candidates
    }
    audit = spec.get("ordered_no_return_gates") or {}
    coverage = audit.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = audit.get("uniqueness_after_coverage_only") or {}
    comparisons = list(uniqueness.get("comparison_factors") or [])
    boundary = spec.get("research_boundary") or {}
    mechanism = (spec.get("source_chain") or {}).get(
        "mechanism_overlap_audit"
    ) or {}
    benchmark = (spec.get("source_chain") or {}).get(
        "frozen_market_benchmark"
    ) or {}
    candidate = candidates[0] if len(candidates) == 1 else {}
    if not (
        spec.get("version") == 1
        and spec.get("status")
        == "frozen_before_campaign021_candidate_or_comparison_values_or_returns"
        and len(candidates) == 1
        and names == FACTOR_NAMES
        and formulas == FACTOR_FORMULAS
        and directions == FACTOR_DIRECTIONS
        and tuple(candidate.get("source_fields_allowed") or ()) == RAW_COLUMNS
        and tuple(candidate.get("source_fields_used_by_formula") or ())
        == RAW_COLUMNS
        and tuple(candidate.get("benchmark_fields_allowed") or ())
        == tuple(market.BENCHMARK_COLUMNS)
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("within_half_return_count") == RETURN_POSITIONS
        and candidate.get("within_half_adjacent_pair_count")
        == WITHIN_HALF_ADJACENT_PAIR_COUNT
        and candidate.get("minimum_leave_one_out_peers_per_return_position")
        == MINIMUM_LEAVE_ONE_OUT_PEERS
        and candidate.get("correlation_estimator")
        == "population_pearson_equal_pair_weight"
        and candidate.get("endpoint_canonicalization_tolerance")
        == ENDPOINT_TOLERANCE
        and candidate.get("valid_range") == [-2.0, 2.0]
        and mechanism.get("sha256") == MECHANISM_AUDIT_SHA256
        and benchmark.get("manifest_sha256")
        == MARKET_BENCHMARK_MANIFEST_SHA256
        and benchmark.get("frame_byte_sha256")
        == MARKET_BENCHMARK_BYTE_SHA256
        and benchmark.get("frame_sha256")
        == MARKET_BENCHMARK_FRAME_SHA256
        and tuple(benchmark.get("projected_columns") or ())
        == tuple(market.BENCHMARK_COLUMNS)
        and benchmark.get("return_positions_per_date") == RETURN_POSITIONS
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.90
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and uniqueness.get(
            "maximum_allowed_absolute_median_daily_rank_correlation"
        )
        == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and len(comparisons) == 42
        and str(comparisons[-1].get("name") or "") == C20_FACTOR_NAMES[0]
        and uniqueness.get("campaign013_is_semantic_only_due_low_coverage")
        is True
        and boundary.get(
            "minute_datetime_symbol_provider_close_fields_read_before_admissibility"
        )
        is True
        and boundary.get(
            "frozen_market_benchmark_sum_count_fields_read_before_admissibility"
        )
        is True
        and boundary.get(
            "minute_open_high_low_volume_amount_fields_read_before_admissibility"
        )
        is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility")
        is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate50_prospective_activation_allowed") is False
        and boundary.get("current_scoring_selection_sizing_or_orders_allowed")
        is False
    ):
        raise Campaign021FeatureError(
            "Campaign021 no-return protocol semantics changed"
        )
    return spec


'''

_new_compute = r'''def _population_correlation(
    left: np.ndarray,
    right: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Return row-wise population Pearson correlations and valid denominators."""

    left_centered = left - np.mean(left, axis=1, keepdims=True)
    right_centered = right - np.mean(right, axis=1, keepdims=True)
    left_energy = np.sum(left_centered * left_centered, axis=1)
    right_energy = np.sum(right_centered * right_centered, axis=1)
    denominator = np.sqrt(left_energy * right_energy)
    with np.errstate(divide="ignore", invalid="ignore"):
        values = np.divide(
            np.sum(left_centered * right_centered, axis=1),
            denominator,
            out=np.full(len(left), np.nan, dtype=float),
            where=denominator > 0.0,
        )
    return values, denominator


def compute_factor_values(
    *,
    within_half_returns: np.ndarray,
    leave_one_out_market_returns: np.ndarray,
    sufficient_peers: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the frozen one-minute market-response delay asymmetry."""

    within_half_returns = np.asarray(within_half_returns, dtype=float)
    leave_one_out_market_returns = np.asarray(
        leave_one_out_market_returns,
        dtype=float,
    )
    sufficient_peers = np.asarray(sufficient_peers, dtype=bool)
    if (
        within_half_returns.ndim != 2
        or within_half_returns.shape[1] != RETURN_POSITIONS
        or leave_one_out_market_returns.shape != within_half_returns.shape
        or sufficient_peers.shape != (len(within_half_returns),)
    ):
        raise Campaign021FeatureError("Campaign021 return arrays are invalid")

    stock_current = np.concatenate(
        [within_half_returns[:, 1:119], within_half_returns[:, 120:238]],
        axis=1,
    )
    stock_previous = np.concatenate(
        [within_half_returns[:, 0:118], within_half_returns[:, 119:237]],
        axis=1,
    )
    market_current = np.concatenate(
        [
            leave_one_out_market_returns[:, 1:119],
            leave_one_out_market_returns[:, 120:238],
        ],
        axis=1,
    )
    market_previous = np.concatenate(
        [
            leave_one_out_market_returns[:, 0:118],
            leave_one_out_market_returns[:, 119:237],
        ],
        axis=1,
    )
    if not (
        stock_current.shape[1] == WITHIN_HALF_ADJACENT_PAIR_COUNT
        and stock_previous.shape == stock_current.shape
        and market_current.shape == stock_current.shape
        and market_previous.shape == stock_current.shape
    ):
        raise Campaign021FeatureError("Campaign021 pair grid changed")

    finite_vectors = (
        np.isfinite(within_half_returns).all(axis=1)
        & np.isfinite(leave_one_out_market_returns).all(axis=1)
    )
    lag_correlation, lag_denominator = _population_correlation(
        stock_current,
        market_previous,
    )
    lead_correlation, lead_denominator = _population_correlation(
        stock_previous,
        market_current,
    )
    values = lag_correlation - lead_correlation
    low = -2.0
    high = 2.0
    canonicalized = (
        ((values < low) & (values >= low - ENDPOINT_TOLERANCE))
        | ((values > high) & (values <= high + ENDPOINT_TOLERANCE))
    )
    values = np.where(
        (values < low) & (values >= low - ENDPOINT_TOLERANCE),
        low,
        values,
    )
    values = np.where(
        (values > high) & (values <= high + ENDPOINT_TOLERANCE),
        high,
        values,
    )
    finite_values = np.isfinite(values)
    in_range = (values >= low) & (values <= high)
    positive_variance = (lag_denominator > 0.0) & (lead_denominator > 0.0)
    eligible = (
        finite_vectors
        & sufficient_peers
        & positive_variance
        & finite_values
        & in_range
    )
    quality = {
        "base_rows": int(len(within_half_returns)),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__invalid_stock_or_market_return_rows": int(
            (~finite_vectors).sum()
        ),
        f"{FACTOR_NAME}__insufficient_peer_rows": int(
            (finite_vectors & ~sufficient_peers).sum()
        ),
        f"{FACTOR_NAME}__degenerate_correlation_rows": int(
            (finite_vectors & sufficient_peers & ~positive_variance).sum()
        ),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int(
            (eligible & canonicalized).sum()
        ),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (
                finite_vectors
                & sufficient_peers
                & positive_variance
                & (~finite_values | ~in_range)
            ).sum()
        ),
    }
    return (
        {FACTOR_NAME: np.where(eligible, values, np.nan)},
        {FACTOR_NAME: eligible},
        quality,
    )


'''

_new_partition = r'''_MARKET_BENCHMARK_CACHE: Any = None


def _campaign021_market_benchmark() -> Any:
    """Load and fingerprint-check the frozen benchmark once per process."""

    global _MARKET_BENCHMARK_CACHE
    if _MARKET_BENCHMARK_CACHE is None:
        _MARKET_BENCHMARK_CACHE = MARKET_BENCHMARK_LOADER(DEFAULT_DATA_ROOT)
        if (
            getattr(_MARKET_BENCHMARK_CACHE, "frame_sha256", None)
            != MARKET_BENCHMARK_FRAME_SHA256
        ):
            raise Campaign021FeatureError("market benchmark fingerprint changed")
    return _MARKET_BENCHMARK_CACHE


def compute_partition_frame(
    raw: pd.DataFrame,
    base: pd.DataFrame,
    _unused_benchmark: Any,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Validate one stock-year close path and compute the frozen factor."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign021FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    base_work, within_half_returns, return_valid = market.extract_partition_returns(
        raw,
        base,
        symbol=symbol,
    )
    if base_work.empty:
        return empty_output_frame(), {"base_rows": 0}
    benchmark = _campaign021_market_benchmark()
    sums, counts = market._benchmark_for_dates(
        benchmark,
        list(base_work["trade_date"]),
    )
    own = np.where(np.isfinite(within_half_returns), within_half_returns, 0.0)
    own_count = np.isfinite(within_half_returns).astype(np.int32)
    peer_counts = counts.astype(np.int64) - own_count
    peer_sums = sums - own
    sufficient = (
        peer_counts >= MINIMUM_LEAVE_ONE_OUT_PEERS
    ).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        leave_one_out = np.divide(
            peer_sums,
            peer_counts,
            out=np.full_like(peer_sums, np.nan, dtype=float),
            where=peer_counts > 0,
        )
    values, eligible, quality = compute_factor_values(
        within_half_returns=within_half_returns,
        leave_one_out_market_returns=leave_one_out,
        sufficient_peers=sufficient,
    )
    if not np.array_equal(
        return_valid,
        np.isfinite(within_half_returns).all(axis=1),
    ):
        raise Campaign021FeatureError(f"return validity changed for {symbol}")
    return (
        pd.DataFrame(
            {
                "trade_date": base_work["trade_date"],
                "symbol": symbol.upper(),
                "provider": "tushare_leave_one_out_market",
                FACTOR_NAME: values[FACTOR_NAME],
                f"{FACTOR_NAME}_eligible": eligible[FACTOR_NAME],
            }
        ).loc[:, OUTPUT_COLUMNS],
        quality,
    )


'''

_loader_start = _source.index("def load_protocol(")
_compute_start = _source.index("def compute_factor_values(", _loader_start)
_partition_start = _source.index("def compute_partition_frame(", _compute_start)
_configure_start = _source.index("def _configure_engine(", _partition_start)
_source = (
    _source[:_loader_start]
    + _new_loader
    + _new_compute
    + _new_partition
    + _source[_configure_start:]
)

# Final Campaign021 manifests truthfully record close plus benchmark reads.
_source = _source.replace(
    '''        and (
            manifest.get("source_open_high_low_read") is True
            if require_fingerprint_constants
            else manifest.get("source_open_high_low_read") is False
        )''',
    '''        and manifest.get("source_open_high_low_read") is False''',
    1,
)
_source = _source.replace(
    '''        and manifest.get("daily_price_fields_read") == []''',
    '''        and manifest.get("daily_price_fields_read") == []
        and (
            manifest.get("market_benchmark_manifest_sha256")
            == MARKET_BENCHMARK_MANIFEST_SHA256
            if require_fingerprint_constants
            else manifest.get("market_benchmark_manifest_sha256") is None
        )
        and (
            manifest.get("market_benchmark_byte_sha256")
            == MARKET_BENCHMARK_BYTE_SHA256
            if require_fingerprint_constants
            else manifest.get("market_benchmark_byte_sha256") is None
        )
        and (
            manifest.get("market_benchmark_frame_sha256")
            == MARKET_BENCHMARK_FRAME_SHA256
            if require_fingerprint_constants
            else manifest.get("market_benchmark_frame_sha256") is None
        )''',
    1,
)
_source = _source.replace(
    'value["source_open_high_low_read"] = True',
    'value["source_open_high_low_read"] = False',
    1,
)
_source = _source.replace(
    '''        "minute_open_high_low_read_by_status": True,
        "minute_open_read_by_status": True,
        "minute_close_read_by_status": True,''',
    '''        "minute_open_high_low_read_by_status": False,
        "minute_open_read_by_status": False,
        "minute_close_read_by_status": True,''',
    1,
)
_source = _source.replace(
    '''            value["source_amount_read"] = False''',
    '''            value["source_amount_read"] = False
            value["market_benchmark_manifest_sha256"] = (
                MARKET_BENCHMARK_MANIFEST_SHA256
            )
            value["market_benchmark_byte_sha256"] = (
                MARKET_BENCHMARK_BYTE_SHA256
            )
            value["market_benchmark_frame_sha256"] = (
                MARKET_BENCHMARK_FRAME_SHA256
            )
            value["market_benchmark_fields_read"] = list(
                market.BENCHMARK_COLUMNS
            )''',
    1,
)

_verify_c18 = '''        c18_manifest, c18_verification = executor._verify_prior_snapshot(
            path=C18_SNAPSHOT_PATH,
            manifest_sha256=C18_SNAPSHOT_SHA256,
            dataset_sha256=C18_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign018_feature_snapshot",
            factor_names=C18_FACTOR_NAMES,
            output_columns=C18_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
_verify_c20 = _verify_c18 + '''        c19_manifest, c19_verification = executor._verify_prior_snapshot(
            path=C19_SNAPSHOT_PATH,
            manifest_sha256=C19_SNAPSHOT_SHA256,
            dataset_sha256=C19_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign019_feature_snapshot",
            factor_names=C19_FACTOR_NAMES,
            output_columns=C19_OUTPUT_COLUMNS,
            workers=workers,
        )
        c20_manifest, c20_verification = executor._verify_prior_snapshot(
            path=C20_SNAPSHOT_PATH,
            manifest_sha256=C20_SNAPSHOT_SHA256,
            dataset_sha256=C20_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign020_feature_snapshot",
            factor_names=C20_FACTOR_NAMES,
            output_columns=C20_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
if _verify_c18 not in _source:
    raise RuntimeError("Campaign019 prior-snapshot verification block was not found")
_source = _source.replace(_verify_c18, _verify_c20, 1)

_compare_c18 = '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c18_manifest,
                factors=C18_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
_compare_c20 = _compare_c18 + '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c19_manifest,
                factors=C19_FACTOR_NAMES,
                gate=gate,
            )
        )
        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c20_manifest,
                factors=C20_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
if _compare_c18 not in _source:
    raise RuntimeError("Campaign019 comparison extension block was not found")
_source = _source.replace(_compare_c18, _compare_c20, 1)
_source = _source.replace(
    "Apply coverage before all 40 frozen uniqueness comparisons.",
    "Apply coverage before all 42 frozen uniqueness comparisons.",
    1,
)
_source = _source.replace("len(comparisons) == 40", "len(comparisons) == 42", 1)
_source = _source.replace(
    '''            "campaign018_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    '''            "campaign018_terminal_comparison_count": 1,
            "campaign019_terminal_comparison_count": 1,
            "campaign020_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    1,
)
_source = _source.replace(
    '''            "campaign018_snapshot_file_verification": c18_verification,
            "comparisons": comparisons,''',
    '''            "campaign018_snapshot_file_verification": c18_verification,
            "campaign019_snapshot_file_verification": c19_verification,
            "campaign020_snapshot_file_verification": c20_verification,
            "comparisons": comparisons,''',
    1,
)
_source = _source.replace(
    '''        "source_fields_read": list(RAW_COLUMNS),''',
    '''        "source_fields_read": list(RAW_COLUMNS),
        "market_benchmark_fields_read": list(market.BENCHMARK_COLUMNS),''',
    1,
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign021_features_generated",
    "MARKET_BENCHMARK_LOADER": campaign004._load_market_benchmark,
    "MARKET_BENCHMARK_MANIFEST_SHA256": MARKET_BENCHMARK_MANIFEST_SHA256,
    "MARKET_BENCHMARK_BYTE_SHA256": MARKET_BENCHMARK_BYTE_SHA256,
    "MARKET_BENCHMARK_FRAME_SHA256": MARKET_BENCHMARK_FRAME_SHA256,
    "MINIMUM_LEAVE_ONE_OUT_PEERS": MINIMUM_LEAVE_ONE_OUT_PEERS,
    "RETURN_POSITIONS": RETURN_POSITIONS,
    "WITHIN_HALF_ADJACENT_PAIR_COUNT": WITHIN_HALF_ADJACENT_PAIR_COUNT,
}
for _campaign in (9, 10, 11, 12, 14, 15, 16, 17, 18):
    for _suffix in (
        "SNAPSHOT_PATH",
        "SNAPSHOT_SHA256",
        "DATASET_SHA256",
        "FACTOR_NAMES",
        "OUTPUT_COLUMNS",
    ):
        _key = f"C{_campaign}_{_suffix}"
        _generated[_key] = campaign019.engine_namespace[_key]
_generated.update(
    {
        "C19_SNAPSHOT_PATH": C19_SNAPSHOT_PATH,
        "C19_SNAPSHOT_SHA256": C19_SNAPSHOT_SHA256,
        "C19_DATASET_SHA256": C19_DATASET_SHA256,
        "C19_FACTOR_NAMES": C19_FACTOR_NAMES,
        "C19_OUTPUT_COLUMNS": C19_OUTPUT_COLUMNS,
        "C20_SNAPSHOT_PATH": C20_SNAPSHOT_PATH,
        "C20_SNAPSHOT_SHA256": C20_SNAPSHOT_SHA256,
        "C20_DATASET_SHA256": C20_DATASET_SHA256,
        "C20_FACTOR_NAMES": C20_FACTOR_NAMES,
        "C20_OUTPUT_COLUMNS": C20_OUTPUT_COLUMNS,
    }
)
exec(compile(_source, str(CAMPAIGN019_FEATURE_RUNNER), "exec"), _generated)

Campaign021FeatureError = _generated["Campaign021FeatureError"]
compute_factor_values = _generated["compute_factor_values"]
compute_partition_frame = _generated["compute_partition_frame"]
empty_output_frame = _generated["empty_output_frame"]
load_protocol = _generated["load_protocol"]
output_root = _generated["output_root"]
build_snapshot = _generated["build_snapshot"]
verify_snapshot_files = _generated["verify_snapshot_files"]
run_no_return_audit = _generated["run_no_return_audit"]
status = _generated["status"]
parser = _generated["parser"]
main = _generated["main"]
_validate_snapshot_manifest = _generated["_validate_snapshot_manifest"]
engine_namespace = run_no_return_audit.__globals__
for _export_name in (
    "DEFAULT_PROTOCOL",
    "DEFAULT_DATA_ROOT",
    "DEFAULT_EXPERIMENT_ROOT",
    "RAW_COLUMNS",
    "BASE_COLUMNS",
    "FACTOR_NAMES",
    "FACTOR_DIRECTIONS",
    "FACTOR_RANGES",
    "FACTOR_FORMULA",
    "FACTOR_FORMULAS",
    "OUTPUT_COLUMNS",
    "SELECTED_BAR_COUNT",
    "ENDPOINT_TOLERANCE",
    "market",
):
    globals()[_export_name] = _generated[_export_name]


if __name__ == "__main__":
    raise SystemExit(main())
