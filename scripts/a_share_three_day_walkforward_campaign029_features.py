#!/usr/bin/env python3
"""Build and no-return audit Campaign029 market-shock decoupling.

Campaign028 supplies the tested snapshot and comparison orchestration. This
wrapper changes only the campaign namespace and candidate computation, reads
the close path plus the frozen leave-one-out market benchmark, and appends the
terminal Campaign028 snapshot as comparison 50.
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
    import scripts.a_share_three_day_walkforward_campaign028_features as campaign028
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_three_day_walkforward_campaign004_features as campaign004
    import a_share_three_day_walkforward_campaign028_features as campaign028


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN028_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign028_features.py"
)
CAMPAIGN028_FEATURE_RUNNER_SHA256 = (
    "eb0eeb690c07fd28ccae71c6125021535edb9aa18a0c669110b18dc52457f317"
)
OLD_FACTOR = "intraday_absolute_return_serial_persistence_236p"
FACTOR_NAME = "intraday_market_shock_magnitude_decoupling_238m"
MECHANISM_AUDIT_SHA256 = (
    "a1085b91b0d0fb697d36befbc913cd2066900b7e94434e86c63548e329573dfa"
)
PROTOCOL_SHA256 = (
    "6bf84e6a6b9b40338447e3ff08784a09df2a76f780cbdfb09980e93f0268baf3"
)

# Bind these immutable fingerprints only after the corresponding artifacts exist.
SNAPSHOT_MANIFEST_SHA256 = (
    "6dbf652eab4b787773d235cdcb4342ee82bbfb34c42d1a161c5d071c1c9df6a9"
)
SNAPSHOT_DATASET_SHA256 = (
    "e37d17aa9f915425d2cd49e869d899045a0b385ffd04d74bb1bec543772de201"
)
NO_RETURN_AUDIT_SHA256 = (
    "6188912d099f969c1b8c6a2e5436161a9e51496b4634fa2b80ebe0e7c97260f0"
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
ENDPOINT_TOLERANCE = 1e-12

C28_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign028_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign028_feature_library_v1/snapshot_manifest.json"
)
C28_SNAPSHOT_SHA256 = (
    "b08065c1cb7dbdbf06e4285a0c686338e121d27546fce97bb92dc9251f8366d0"
)
C28_DATASET_SHA256 = (
    "8d3a3368ed85c0215751bf86b7d491bf9ad049762a810cce2e50b1a3b4badadf"
)
C28_FACTOR_NAMES = ("intraday_absolute_return_serial_persistence_236p",)
C28_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C28_FACTOR_NAMES[0],
    f"{C28_FACTOR_NAMES[0]}_eligible",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN028_FEATURE_RUNNER) != CAMPAIGN028_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign028 feature orchestration fingerprint changed")

_source = campaign028._source
for _old, _new in (
    ("Campaign028", "Campaign029"),
    ("campaign028", "campaign029"),
    ("campaign_028", "campaign_029"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "f41e33bb607e7adf6a7ba3c731bae40fbaa85fdc9e5ee054831607bbcd518a2a",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "704dbe2f21624a5b97ac597c9e79b1ca6e7611903eef39624a701a1e0acc10bc",
        PROTOCOL_SHA256,
    ),
    (
        "b08065c1cb7dbdbf06e4285a0c686338e121d27546fce97bb92dc9251f8366d0",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "8d3a3368ed85c0215751bf86b7d491bf9ad049762a810cce2e50b1a3b4badadf",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "9f077d989d0456cbfaf23fbcce4d3737ac3da25380c50435cfddbc7f31fe0963",
        NO_RETURN_AUDIT_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_old_formula = '''FACTOR_FORMULA = (
    "population PearsonCorr(abs(r_t), abs(r_t+1)) across the 118 adjacent "
    "return-magnitude pairs inside each 120-close trading half, pooled to "
    "236 equal-weight pairs"
)'''
_new_formula = '''FACTOR_FORMULA = (
    "negative population PearsonCorr(abs(stock_return), "
    "abs(leave_one_out_market_return)) over exactly 238 synchronous "
    "within-half return positions"
)'''
if _old_formula not in _source:
    raise RuntimeError("Campaign028 formula block was not found")
_source = _source.replace(_old_formula, _new_formula, 1)

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
_source = _source.replace(
    '''        "source_fields_read": list(RAW_COLUMNS),''',
    '''        "source_fields_read": list(RAW_COLUMNS),
        "market_benchmark_fields_read": list(market.BENCHMARK_COLUMNS),''',
    1,
)
_source = _source.replace(
    '''        "minute_amount_read_by_status": False,''',
    '''        "minute_amount_read_by_status": False,
        "market_benchmark_fields_read_by_status": list(
            market.BENCHMARK_COLUMNS
        ),''',
    1,
)

_verify_c27 = '''        c27_manifest, c27_verification = executor._verify_prior_snapshot(
            path=C27_SNAPSHOT_PATH,
            manifest_sha256=C27_SNAPSHOT_SHA256,
            dataset_sha256=C27_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign027_feature_snapshot",
            factor_names=C27_FACTOR_NAMES,
            output_columns=C27_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
_verify_c28 = _verify_c27 + '''        c28_manifest, c28_verification = executor._verify_prior_snapshot(
            path=C28_SNAPSHOT_PATH,
            manifest_sha256=C28_SNAPSHOT_SHA256,
            dataset_sha256=C28_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign028_feature_snapshot",
            factor_names=C28_FACTOR_NAMES,
            output_columns=C28_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
if _verify_c27 not in _source:
    raise RuntimeError("Campaign028 prior-snapshot verification block was not found")
_source = _source.replace(_verify_c27, _verify_c28, 1)

_compare_c27 = '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c27_manifest,
                factors=C27_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
_compare_c28 = _compare_c27 + '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c28_manifest,
                factors=C28_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
if _compare_c27 not in _source:
    raise RuntimeError("Campaign028 comparison extension block was not found")
_source = _source.replace(_compare_c27, _compare_c28, 1)
_source = _source.replace(
    "Apply coverage before all 49 frozen uniqueness comparisons.",
    "Apply coverage before all 50 frozen uniqueness comparisons.",
    1,
)
_source = _source.replace("len(comparisons) == 49", "len(comparisons) == 50")
_source = _source.replace(
    '''            "campaign027_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    '''            "campaign027_terminal_comparison_count": 1,
            "campaign028_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    1,
)
_source = _source.replace(
    '''            "campaign027_snapshot_file_verification": c27_verification,
            "comparisons": comparisons,''',
    '''            "campaign027_snapshot_file_verification": c27_verification,
            "campaign028_snapshot_file_verification": c28_verification,
            "comparisons": comparisons,''',
    1,
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign029_features_generated",
    "MARKET_BENCHMARK_MANIFEST_SHA256": MARKET_BENCHMARK_MANIFEST_SHA256,
    "MARKET_BENCHMARK_BYTE_SHA256": MARKET_BENCHMARK_BYTE_SHA256,
    "MARKET_BENCHMARK_FRAME_SHA256": MARKET_BENCHMARK_FRAME_SHA256,
}
for _campaign in (
    9,
    10,
    11,
    12,
    14,
    15,
    16,
    17,
    18,
    19,
    20,
    21,
    22,
    23,
    24,
    25,
    26,
    27,
):
    for _suffix in (
        "SNAPSHOT_PATH",
        "SNAPSHOT_SHA256",
        "DATASET_SHA256",
        "FACTOR_NAMES",
        "OUTPUT_COLUMNS",
    ):
        _key = f"C{_campaign}_{_suffix}"
        _generated[_key] = campaign028.engine_namespace[_key]
_generated.update(
    {
        "C28_SNAPSHOT_PATH": C28_SNAPSHOT_PATH,
        "C28_SNAPSHOT_SHA256": C28_SNAPSHOT_SHA256,
        "C28_DATASET_SHA256": C28_DATASET_SHA256,
        "C28_FACTOR_NAMES": C28_FACTOR_NAMES,
        "C28_OUTPUT_COLUMNS": C28_OUTPUT_COLUMNS,
    }
)
exec(
    compile(_source, str(CAMPAIGN028_FEATURE_RUNNER), "exec"),
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

Campaign029FeatureError = _generated["Campaign029FeatureError"]


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate every frozen binding and exact Campaign029 semantics."""

    path = path.expanduser().resolve()
    if _sha256(path) != PROTOCOL_SHA256:
        raise Campaign029FeatureError("Campaign029 no-return protocol changed")
    validation = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if not validation["all_bindings_passed"]:
        raise Campaign029FeatureError(
            "Campaign029 no-return protocol has a failed file binding"
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
        == "a_share_three_day_walkforward_campaign029_no_return_preregistration"
        and spec.get("status")
        == (
            "frozen_before_campaign029_candidate_benchmark_or_comparison_"
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
        and candidate.get("minimum_leave_one_out_peers_per_return_position")
        == MINIMUM_LEAVE_ONE_OUT_PEERS
        and candidate.get("magnitude_semantics")
        == (
            "Apply exact absolute value separately to every stock return and "
            "every synchronous leave-one-out market return."
        )
        and candidate.get("correlation_estimator")
        == "population_pearson_equal_position_weight"
        and candidate.get("direction_transform")
        == "multiply_population_correlation_by_exact_negative_one"
        and candidate.get("zero_return_semantics")
        == (
            "Retain every exact-zero stock or leave-one-out market return "
            "magnitude at its fixed position."
        )
        and candidate.get("variance_semantics")
        == (
            "Require strictly positive population variance in both complete "
            "238-element magnitude vectors."
        )
        and candidate.get("endpoint_canonicalization_tolerance")
        == ENDPOINT_TOLERANCE
        and candidate.get("valid_range") == [-1.0, 1.0]
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
        and len(comparisons) == 50
        and str(comparisons[-1].get("name") or "") == C28_FACTOR_NAMES[0]
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
        raise Campaign029FeatureError("Campaign029 no-return semantics changed")
    return spec


def compute_factor_values(
    *,
    within_half_returns: np.ndarray,
    leave_one_out_market_returns: np.ndarray,
    sufficient_peers: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute frozen negative same-minute return-magnitude correlation."""

    stock = np.asarray(within_half_returns, dtype=float)
    market_returns = np.asarray(leave_one_out_market_returns, dtype=float)
    sufficient_peers = np.asarray(sufficient_peers, dtype=bool)
    if (
        stock.ndim != 2
        or stock.shape[1] != RETURN_POSITIONS
        or market_returns.shape != stock.shape
        or sufficient_peers.shape != (len(stock),)
    ):
        raise Campaign029FeatureError("Campaign029 return arrays are invalid")
    stock_magnitudes = np.abs(stock)
    market_magnitudes = np.abs(market_returns)
    finite_vectors = np.isfinite(stock_magnitudes).all(axis=1) & np.isfinite(
        market_magnitudes
    ).all(axis=1)
    stock_centered = stock_magnitudes - stock_magnitudes.mean(axis=1)[:, None]
    market_centered = market_magnitudes - market_magnitudes.mean(axis=1)[:, None]
    stock_energy = np.sum(stock_centered * stock_centered, axis=1)
    market_energy = np.sum(market_centered * market_centered, axis=1)
    denominator = np.sqrt(stock_energy * market_energy)
    positive_variance = denominator > 0.0
    with np.errstate(divide="ignore", invalid="ignore"):
        correlation = np.divide(
            np.sum(stock_centered * market_centered, axis=1),
            denominator,
            out=np.full(len(stock), np.nan, dtype=float),
            where=positive_variance,
        )
    values = -correlation
    low = -1.0
    high = 1.0
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
    eligible = (
        finite_vectors
        & sufficient_peers
        & positive_variance
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
        f"{FACTOR_NAME}__degenerate_stock_magnitude_variance_rows": int(
            (
                finite_vectors
                & sufficient_peers
                & ~(stock_energy > 0.0)
            ).sum()
        ),
        f"{FACTOR_NAME}__degenerate_market_magnitude_variance_rows": int(
            (
                finite_vectors
                & sufficient_peers
                & ~(market_energy > 0.0)
            ).sum()
        ),
        f"{FACTOR_NAME}__exact_zero_stock_return_positions": int(
            (stock == 0.0).sum()
        ),
        f"{FACTOR_NAME}__exact_zero_market_return_positions": int(
            (market_returns == 0.0).sum()
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


_MARKET_BENCHMARK_CACHE: Any = None


def _campaign029_market_benchmark() -> Any:
    global _MARKET_BENCHMARK_CACHE
    if _MARKET_BENCHMARK_CACHE is None:
        _MARKET_BENCHMARK_CACHE = campaign004._load_market_benchmark(
            DEFAULT_DATA_ROOT
        )
        if (
            getattr(_MARKET_BENCHMARK_CACHE, "frame_sha256", None)
            != MARKET_BENCHMARK_FRAME_SHA256
        ):
            raise Campaign029FeatureError("market benchmark fingerprint changed")
    return _MARKET_BENCHMARK_CACHE


def compute_partition_frame(
    raw: pd.DataFrame,
    base: pd.DataFrame,
    _unused_benchmark: Any,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Validate one stock-year close path and compute Campaign029."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign029FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    base_work, within_half_returns, return_valid = (
        market.extract_partition_returns(
            raw,
            base,
            symbol=symbol,
        )
    )
    if base_work.empty:
        return _generated["empty_output_frame"](), {"base_rows": 0}
    benchmark = _campaign029_market_benchmark()
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
        raise Campaign029FeatureError(f"return validity changed for {symbol}")
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
