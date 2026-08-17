#!/usr/bin/env python3
"""Build and no-return audit Campaign030 market-correlation resolution.

Campaign029 supplies the tested snapshot and comparison orchestration. This
wrapper changes only the campaign namespace and candidate computation, reads
the close path plus the frozen leave-one-out market benchmark, and appends the
terminal Campaign029 snapshot as comparison 51.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    import scripts.a_share_three_day_preregistration_binding_validator as bindings
    import scripts.a_share_three_day_walkforward_campaign004_features as campaign004
    import scripts.a_share_three_day_walkforward_campaign029_features as campaign029
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_three_day_walkforward_campaign004_features as campaign004
    import a_share_three_day_walkforward_campaign029_features as campaign029


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN029_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign029_features.py"
)
CAMPAIGN029_FEATURE_RUNNER_SHA256 = (
    "7d32f69017db131a78ebdfea82273b01630eb2cb3c4a085789bf8f956101d9cb"
)
OLD_FACTOR = "intraday_market_shock_magnitude_decoupling_238m"
FACTOR_NAME = "intraday_market_correlation_resolution_119p"
MECHANISM_AUDIT_SHA256 = (
    "e32bd7824c8bf752d632d852b617ba5fca1b8be4059beccf79d82ebf7f33d6fb"
)
PROTOCOL_SHA256 = (
    "15a7a9c3d255d1cae56d5b8ee3e3b0b69bb78a1a85a741a3c0b364ac0ee340f0"
)

# Bind these after the corresponding artifacts are created.
SNAPSHOT_MANIFEST_SHA256 = (
    "bc34e382f427d02380b6bf7858ad364064540cf1ec9be3b91e878bfefc84ab42"
)
SNAPSHOT_DATASET_SHA256 = (
    "10953d752e924d0be3692c5bd0a392cb27d7009c3e7c3358c8602215d70dc549"
)
NO_RETURN_AUDIT_SHA256 = (
    "3cec65d23b1d7952813e67db2e9b1d7486be797925e470703c3a9b4a5cf97a3b"
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
POSITIONS_PER_HALF = 119
ENDPOINT_TOLERANCE = 1e-12

C29_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign029_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign029_feature_library_v1/snapshot_manifest.json"
)
C29_SNAPSHOT_SHA256 = (
    "6dbf652eab4b787773d235cdcb4342ee82bbfb34c42d1a161c5d071c1c9df6a9"
)
C29_DATASET_SHA256 = (
    "e37d17aa9f915425d2cd49e869d899045a0b385ffd04d74bb1bec543772de201"
)
C29_FACTOR_NAMES = ("intraday_market_shock_magnitude_decoupling_238m",)
C29_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C29_FACTOR_NAMES[0],
    f"{C29_FACTOR_NAMES[0]}_eligible",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN029_FEATURE_RUNNER) != CAMPAIGN029_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign029 feature orchestration fingerprint changed")

_source = campaign029._source
for _old, _new in (
    ("Campaign029", "Campaign030"),
    ("campaign029", "campaign030"),
    ("campaign_029", "campaign_030"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "a1085b91b0d0fb697d36befbc913cd2066900b7e94434e86c63548e329573dfa",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "6bf84e6a6b9b40338447e3ff08784a09df2a76f780cbdfb09980e93f0268baf3",
        PROTOCOL_SHA256,
    ),
    (
        "6dbf652eab4b787773d235cdcb4342ee82bbfb34c42d1a161c5d071c1c9df6a9",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "e37d17aa9f915425d2cd49e869d899045a0b385ffd04d74bb1bec543772de201",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "6188912d099f969c1b8c6a2e5436161a9e51496b4634fa2b80ebe0e7c97260f0",
        NO_RETURN_AUDIT_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_old_formula = '''FACTOR_FORMULA = (
    "negative population PearsonCorr(abs(stock_return), "
    "abs(leave_one_out_market_return)) over exactly 238 synchronous "
    "within-half return positions"
)'''
_new_formula = '''FACTOR_FORMULA = (
    "population PearsonCorr(stock_return, leave_one_out_market_return) "
    "over the 119 morning within-half return positions minus the same "
    "population Pearson correlation over the 119 afternoon within-half "
    "return positions"
)'''
if _old_formula not in _source:
    raise RuntimeError("Campaign029 formula block was not found")
_source = _source.replace(_old_formula, _new_formula, 1)

_verify_c28 = '''        c28_manifest, c28_verification = executor._verify_prior_snapshot(
            path=C28_SNAPSHOT_PATH,
            manifest_sha256=C28_SNAPSHOT_SHA256,
            dataset_sha256=C28_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign028_feature_snapshot",
            factor_names=C28_FACTOR_NAMES,
            output_columns=C28_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
_verify_c29 = _verify_c28 + '''        c29_manifest, c29_verification = executor._verify_prior_snapshot(
            path=C29_SNAPSHOT_PATH,
            manifest_sha256=C29_SNAPSHOT_SHA256,
            dataset_sha256=C29_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign029_feature_snapshot",
            factor_names=C29_FACTOR_NAMES,
            output_columns=C29_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
if _verify_c28 not in _source:
    raise RuntimeError("Campaign029 prior-snapshot verification block was not found")
_source = _source.replace(_verify_c28, _verify_c29, 1)

_compare_c28 = '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c28_manifest,
                factors=C28_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
_compare_c29 = _compare_c28 + '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c29_manifest,
                factors=C29_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
if _compare_c28 not in _source:
    raise RuntimeError("Campaign029 comparison extension block was not found")
_source = _source.replace(_compare_c28, _compare_c29, 1)
_source = _source.replace(
    "Apply coverage before all 50 frozen uniqueness comparisons.",
    "Apply coverage before all 51 frozen uniqueness comparisons.",
    1,
)
_source = _source.replace("len(comparisons) == 50", "len(comparisons) == 51")
_source = _source.replace(
    '''            "campaign028_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    '''            "campaign028_terminal_comparison_count": 1,
            "campaign029_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    1,
)
_source = _source.replace(
    '''            "campaign028_snapshot_file_verification": c28_verification,
            "comparisons": comparisons,''',
    '''            "campaign028_snapshot_file_verification": c28_verification,
            "campaign029_snapshot_file_verification": c29_verification,
            "comparisons": comparisons,''',
    1,
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign030_features_generated",
    "MARKET_BENCHMARK_MANIFEST_SHA256": MARKET_BENCHMARK_MANIFEST_SHA256,
    "MARKET_BENCHMARK_BYTE_SHA256": MARKET_BENCHMARK_BYTE_SHA256,
    "MARKET_BENCHMARK_FRAME_SHA256": MARKET_BENCHMARK_FRAME_SHA256,
}
for _campaign in (
    9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26,
    27, 28,
):
    for _suffix in (
        "SNAPSHOT_PATH",
        "SNAPSHOT_SHA256",
        "DATASET_SHA256",
        "FACTOR_NAMES",
        "OUTPUT_COLUMNS",
    ):
        _key = f"C{_campaign}_{_suffix}"
        _generated[_key] = campaign029.engine_namespace[_key]
_generated.update(
    {
        "C29_SNAPSHOT_PATH": C29_SNAPSHOT_PATH,
        "C29_SNAPSHOT_SHA256": C29_SNAPSHOT_SHA256,
        "C29_DATASET_SHA256": C29_DATASET_SHA256,
        "C29_FACTOR_NAMES": C29_FACTOR_NAMES,
        "C29_OUTPUT_COLUMNS": C29_OUTPUT_COLUMNS,
    }
)
exec(
    compile(_source, str(CAMPAIGN029_FEATURE_RUNNER), "exec"),
    _generated,
)

RAW_COLUMNS = ("datetime", "symbol", "provider", "close")
BASE_COLUMNS = _generated["BASE_COLUMNS"]
SELECTED_BAR_COUNT = _generated["SELECTED_BAR_COUNT"]
OUTPUT_COLUMNS = _generated["OUTPUT_COLUMNS"]
FACTOR_NAMES = _generated["FACTOR_NAMES"]
FACTOR_DIRECTIONS = _generated["FACTOR_DIRECTIONS"]
FACTOR_RANGES = _generated["FACTOR_RANGES"]
FACTOR_FORMULA = _generated["FACTOR_FORMULA"]
FACTOR_FORMULAS = _generated["FACTOR_FORMULAS"]
DEFAULT_PROTOCOL = _generated["DEFAULT_PROTOCOL"]
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT = _generated["DEFAULT_EXPERIMENT_ROOT"]
market = _generated["market"]

Campaign030FeatureError = _generated["Campaign030FeatureError"]


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate every frozen binding and exact Campaign030 semantics."""

    path = path.expanduser().resolve()
    if _sha256(path) != PROTOCOL_SHA256:
        raise Campaign030FeatureError("Campaign030 no-return protocol changed")
    validation = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if not validation["all_bindings_passed"]:
        raise Campaign030FeatureError(
            "Campaign030 no-return protocol has a failed file binding"
        )
    spec = json.loads(path.read_text(encoding="utf-8"))
    candidate_list = list(spec.get("candidates") or [])
    candidate = candidate_list[0] if len(candidate_list) == 1 else {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    comparisons = list(uniqueness.get("comparison_factors") or [])
    boundary = spec.get("research_boundary") or {}
    source_chain = spec.get("source_chain") or {}
    mechanism = source_chain.get("mechanism_overlap_audit") or {}
    benchmark_manifest = source_chain.get("frozen_market_benchmark_manifest") or {}
    benchmark_frame = source_chain.get("frozen_market_benchmark_frame") or {}
    finite_search = spec.get("finite_post_admissibility_search") or {}
    trial = finite_search.get("trial") or {}
    if not (
        spec.get("version") == 1
        and spec.get("kind")
        == "a_share_three_day_walkforward_campaign030_no_return_preregistration"
        and spec.get("status")
        == (
            "frozen_before_campaign030_candidate_benchmark_or_comparison_"
            "values_or_returns"
        )
        and len(candidate_list) == 1
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_fields_allowed") or ()) == RAW_COLUMNS
        and tuple(candidate.get("source_fields_used_by_formula") or ())
        == RAW_COLUMNS
        and tuple(candidate.get("benchmark_fields_allowed") or ())
        == tuple(market.BENCHMARK_COLUMNS)
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("within_half_return_count") == RETURN_POSITIONS
        and candidate.get("positions_per_half") == POSITIONS_PER_HALF
        and candidate.get("minimum_leave_one_out_peers_per_return_position")
        == MINIMUM_LEAVE_ONE_OUT_PEERS
        and candidate.get("correlation_estimator")
        == "population_pearson_equal_position_weight_separately_by_half"
        and candidate.get("half_difference_semantics")
        == (
            "Subtract the complete afternoon signed-return correlation from "
            "the complete morning signed-return correlation exactly once."
        )
        and candidate.get("zero_return_semantics")
        == (
            "Retain every exact-zero stock or leave-one-out market signed "
            "return at its fixed position."
        )
        and candidate.get("variance_semantics")
        == (
            "Require strictly positive population variance in both stock and "
            "both leave-one-out market 119-element half vectors."
        )
        and candidate.get("endpoint_canonicalization_tolerance")
        == ENDPOINT_TOLERANCE
        and candidate.get("valid_range") == [-2.0, 2.0]
        and mechanism.get("sha256") == MECHANISM_AUDIT_SHA256
        and benchmark_manifest.get("sha256")
        == MARKET_BENCHMARK_MANIFEST_SHA256
        and benchmark_frame.get("sha256") == MARKET_BENCHMARK_BYTE_SHA256
        and benchmark_frame.get("frame_sha256")
        == MARKET_BENCHMARK_FRAME_SHA256
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
        and len(comparisons) == 51
        and str(comparisons[-1].get("name") or "") == C29_FACTOR_NAMES[0]
        and finite_search.get("candidate_factor_count") == 1
        and finite_search.get("development_trial_count") == 1
        and trial.get("factor") == FACTOR_NAME
        and trial.get("direction") == "higher"
        and trial.get("transform") == "none"
        and trial.get("threshold") == "none"
        and trial.get("filter") == "none"
        and trial.get("combination") == "none"
        and boundary.get("binding_validation_required_before_candidate_values")
        is True
        and boundary.get(
            "minute_datetime_symbol_provider_close_fields_read_before_admissibility"
        )
        is True
        and boundary.get(
            "minute_open_high_low_volume_amount_fields_read_before_admissibility"
        )
        is False
        and boundary.get(
            "frozen_market_benchmark_sum_count_fields_read_before_admissibility"
        )
        is True
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility")
        is False
        and boundary.get("comparison_values_read_before_coverage_pass") is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate49_signal_or_execution_ledger_changed")
        is False
        and boundary.get("candidate50_prospective_activation_allowed") is False
        and boundary.get("current_scoring_selection_sizing_or_orders_allowed")
        is False
        and boundary.get("provider_request_allowed") is False
    ):
        raise Campaign030FeatureError("Campaign030 no-return semantics changed")
    return spec


def _population_correlation(
    stock: np.ndarray,
    market_returns: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    stock_centered = stock - stock.mean(axis=1)[:, None]
    market_centered = market_returns - market_returns.mean(axis=1)[:, None]
    stock_energy = np.sum(stock_centered * stock_centered, axis=1)
    market_energy = np.sum(market_centered * market_centered, axis=1)
    denominator = np.sqrt(stock_energy * market_energy)
    with np.errstate(divide="ignore", invalid="ignore"):
        correlation = np.divide(
            np.sum(stock_centered * market_centered, axis=1),
            denominator,
            out=np.full(len(stock), np.nan, dtype=float),
            where=denominator > 0.0,
        )
    correlation = np.where(
        (correlation < -1.0)
        & (correlation >= -1.0 - ENDPOINT_TOLERANCE),
        -1.0,
        correlation,
    )
    correlation = np.where(
        (correlation > 1.0)
        & (correlation <= 1.0 + ENDPOINT_TOLERANCE),
        1.0,
        correlation,
    )
    return correlation, stock_energy, market_energy


def compute_factor_values(
    *,
    within_half_returns: np.ndarray,
    leave_one_out_market_returns: np.ndarray,
    sufficient_peers: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute frozen morning-minus-afternoon signed market correlation."""

    stock = np.asarray(within_half_returns, dtype=float)
    market_returns = np.asarray(leave_one_out_market_returns, dtype=float)
    sufficient_peers = np.asarray(sufficient_peers, dtype=bool)
    if (
        stock.ndim != 2
        or stock.shape[1] != RETURN_POSITIONS
        or market_returns.shape != stock.shape
        or sufficient_peers.shape != (len(stock),)
    ):
        raise Campaign030FeatureError("Campaign030 return arrays are invalid")
    finite_vectors = np.isfinite(stock).all(axis=1) & np.isfinite(
        market_returns
    ).all(axis=1)
    morning_stock = stock[:, :POSITIONS_PER_HALF]
    afternoon_stock = stock[:, POSITIONS_PER_HALF:]
    morning_market = market_returns[:, :POSITIONS_PER_HALF]
    afternoon_market = market_returns[:, POSITIONS_PER_HALF:]
    morning_corr, morning_stock_energy, morning_market_energy = (
        _population_correlation(morning_stock, morning_market)
    )
    afternoon_corr, afternoon_stock_energy, afternoon_market_energy = (
        _population_correlation(afternoon_stock, afternoon_market)
    )
    positive_variance = (
        (morning_stock_energy > 0.0)
        & (morning_market_energy > 0.0)
        & (afternoon_stock_energy > 0.0)
        & (afternoon_market_energy > 0.0)
    )
    component_in_range = (
        np.isfinite(morning_corr)
        & np.isfinite(afternoon_corr)
        & (morning_corr >= -1.0)
        & (morning_corr <= 1.0)
        & (afternoon_corr >= -1.0)
        & (afternoon_corr <= 1.0)
    )
    values = morning_corr - afternoon_corr
    finite_values = np.isfinite(values)
    in_range = (values >= -2.0) & (values <= 2.0)
    eligible = (
        finite_vectors
        & sufficient_peers
        & positive_variance
        & component_in_range
        & finite_values
        & in_range
    )
    quality = {
        "base_rows": int(len(stock)),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__invalid_stock_or_market_return_rows": int(
            (~finite_vectors).sum()
        ),
        f"{FACTOR_NAME}__insufficient_peer_rows": int(
            (finite_vectors & ~sufficient_peers).sum()
        ),
        f"{FACTOR_NAME}__degenerate_morning_stock_variance_rows": int(
            (
                finite_vectors
                & sufficient_peers
                & ~(morning_stock_energy > 0.0)
            ).sum()
        ),
        f"{FACTOR_NAME}__degenerate_morning_market_variance_rows": int(
            (
                finite_vectors
                & sufficient_peers
                & ~(morning_market_energy > 0.0)
            ).sum()
        ),
        f"{FACTOR_NAME}__degenerate_afternoon_stock_variance_rows": int(
            (
                finite_vectors
                & sufficient_peers
                & ~(afternoon_stock_energy > 0.0)
            ).sum()
        ),
        f"{FACTOR_NAME}__degenerate_afternoon_market_variance_rows": int(
            (
                finite_vectors
                & sufficient_peers
                & ~(afternoon_market_energy > 0.0)
            ).sum()
        ),
        f"{FACTOR_NAME}__exact_zero_stock_return_positions": int(
            (stock == 0.0).sum()
        ),
        f"{FACTOR_NAME}__exact_zero_market_return_positions": int(
            (market_returns == 0.0).sum()
        ),
        f"{FACTOR_NAME}__invalid_component_or_final_range_rows": int(
            (
                finite_vectors
                & sufficient_peers
                & positive_variance
                & (~component_in_range | ~finite_values | ~in_range)
            ).sum()
        ),
    }
    return (
        {FACTOR_NAME: np.where(eligible, values, np.nan)},
        {FACTOR_NAME: eligible},
        quality,
    )


_MARKET_BENCHMARK_CACHE: Any = None


def _campaign030_market_benchmark() -> Any:
    global _MARKET_BENCHMARK_CACHE
    if _MARKET_BENCHMARK_CACHE is None:
        _MARKET_BENCHMARK_CACHE = campaign004._load_market_benchmark(
            DEFAULT_DATA_ROOT
        )
        if (
            getattr(_MARKET_BENCHMARK_CACHE, "frame_sha256", None)
            != MARKET_BENCHMARK_FRAME_SHA256
        ):
            raise Campaign030FeatureError("market benchmark fingerprint changed")
    return _MARKET_BENCHMARK_CACHE


def compute_partition_frame(
    raw: pd.DataFrame,
    base: pd.DataFrame,
    _unused_benchmark: Any,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Validate one stock-year close path and compute Campaign030."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign030FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    base_work, within_half_returns, return_valid = (
        market.extract_partition_returns(raw, base, symbol=symbol)
    )
    if base_work.empty:
        return _generated["empty_output_frame"](), {"base_rows": 0}
    benchmark = _campaign030_market_benchmark()
    sums, counts = market._benchmark_for_dates(
        benchmark,
        list(base_work["trade_date"]),
    )
    own = np.where(np.isfinite(within_half_returns), within_half_returns, 0.0)
    own_count = np.isfinite(within_half_returns).astype(np.int32)
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
    values, eligible, quality = compute_factor_values(
        within_half_returns=within_half_returns,
        leave_one_out_market_returns=leave_one_out,
        sufficient_peers=sufficient,
    )
    if not np.array_equal(
        return_valid,
        np.isfinite(within_half_returns).all(axis=1),
    ):
        raise Campaign030FeatureError(f"return validity changed for {symbol}")
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


_generated["load_protocol"] = load_protocol
_generated["compute_factor_values"] = compute_factor_values
_generated["compute_partition_frame"] = compute_partition_frame

empty_output_frame = _generated["empty_output_frame"]
output_root = _generated["output_root"]
build_snapshot = _generated["build_snapshot"]
verify_snapshot_files = _generated["verify_snapshot_files"]
run_no_return_audit = _generated["run_no_return_audit"]
status = _generated["status"]
parser = _generated["parser"]
main = _generated["main"]
_validate_snapshot_manifest = _generated["_validate_snapshot_manifest"]
engine_namespace = run_no_return_audit.__globals__


if __name__ == "__main__":
    raise SystemExit(main())
