#!/usr/bin/env python3
"""Build and no-return audit Campaign026 market-direction asymmetry.

Campaign025 supplies the tested snapshot and comparison orchestration. This
wrapper changes only the campaign namespace and candidate computation, reads
the close path plus the frozen leave-one-out market benchmark, and appends the
Campaign025 terminal snapshot as comparison 47.
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
    import scripts.a_share_three_day_walkforward_campaign021_features as campaign021
    import scripts.a_share_three_day_walkforward_campaign025_features as campaign025
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_three_day_walkforward_campaign004_features as campaign004
    import a_share_three_day_walkforward_campaign021_features as campaign021
    import a_share_three_day_walkforward_campaign025_features as campaign025


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN025_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign025_features.py"
)
CAMPAIGN025_FEATURE_RUNNER_SHA256 = (
    "27f79dbf8e86ae17f71a8cc1e4626b8517d8dde62aa74901a1f9447dd6c0e03d"
)
OLD_FACTOR = "intraday_extreme_arrival_order_240m"
FACTOR_NAME = "intraday_market_up_down_correlation_asymmetry_238m"
MECHANISM_AUDIT_SHA256 = (
    "4725b9e7740a4e07e80e63123d23887164368a72cd6e5c5cbbe6b0dfb33432c4"
)
PROTOCOL_SHA256 = (
    "b40643706488fb46d789db49aea24a0439a7f8c069bdc542d3c7f0f9e80e1e26"
)
NO_RETURN_CONTEXT_REPAIR = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_026_no_return_context_repair_20260730.json"
)
NO_RETURN_CONTEXT_REPAIR_SHA256 = (
    "a1c704c5c1308827908620809d0bdd56b676728b9a62b1192e2d0400676ea584"
)

# Bind these immutable fingerprints only after the corresponding artifacts exist.
SNAPSHOT_MANIFEST_SHA256 = (
    "1a946ab1a6960100679a4090451ec1c2f3f13950a3f36d8cfc4ff635966537dc"
)
SNAPSHOT_DATASET_SHA256 = (
    "c95e3b2551a4bfc6baf68b55f48add9dd044dcde44bf2e981c403624d0fe958f"
)
NO_RETURN_AUDIT_SHA256 = (
    "933657c2893a7b5f19b274153c91825d52fe5869584695e6262d828e63ceb243"
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
MINIMUM_POSITIONS_PER_MARKET_SIGN = 30
ENDPOINT_TOLERANCE = 1e-12

C25_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign025_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign025_feature_library_v1/snapshot_manifest.json"
)
C25_SNAPSHOT_SHA256 = (
    "4f7b9b335f6df9c8a69ebc7d137abb92e88d5be579fd98231b80c5403bb69def"
)
C25_DATASET_SHA256 = (
    "57871e9955670b3e8610fa249a14accf53830a41b88d0d66e05b80dc212c1056"
)
C25_FACTOR_NAMES = ("intraday_extreme_arrival_order_240m",)
C25_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C25_FACTOR_NAMES[0],
    f"{C25_FACTOR_NAMES[0]}_eligible",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN025_FEATURE_RUNNER) != CAMPAIGN025_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign025 feature orchestration fingerprint changed")

_source = campaign025._source
for _old, _new in (
    ("Campaign025", "Campaign026"),
    ("campaign025", "campaign026"),
    ("campaign_025", "campaign_026"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "09fa633ffbc90e0edcb9ea4edcaeacd96fc8639577492e2c9e40ed2c90dad62f",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "008d83fcb047601b99a74e6810d58eb26524bb6ebc08add230f4525eb7884904",
        PROTOCOL_SHA256,
    ),
    (
        "4f7b9b335f6df9c8a69ebc7d137abb92e88d5be579fd98231b80c5403bb69def",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "57871e9955670b3e8610fa249a14accf53830a41b88d0d66e05b80dc212c1056",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "e67df10a429b902246450823ea7cb9645e88a8b027ab97965afca6029989b238",
        NO_RETURN_AUDIT_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_source = _source.replace(
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")',
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "close")',
    1,
)
_source = _source.replace(
    "FACTOR_RANGES = {FACTOR_NAME: (-1.0, 1.0)}",
    "FACTOR_RANGES = {FACTOR_NAME: (-2.0, 2.0)}",
    1,
)
_old_formula = '''FACTOR_FORMULA = (
    "(first_index(global_max(high)) - first_index(global_min(low))) / 239 "
    "over the ordered 240-bar continuous-session grid"
)'''
_new_formula = '''FACTOR_FORMULA = (
    "population PearsonCorr(stock_return, leave_one_out_market_return | "
    "leave_one_out_market_return>0) minus population PearsonCorr("
    "stock_return, leave_one_out_market_return | "
    "leave_one_out_market_return<0) over exactly 238 within-half "
    "return positions"
)'''
if _old_formula not in _source:
    raise RuntimeError("Campaign025 formula block was not found")
_source = _source.replace(_old_formula, _new_formula, 1)

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
    '''        and (
            manifest.get("source_close_read") is False
            if require_fingerprint_constants
            else manifest.get("source_close_read") in {None, False}
        )''',
    '''        and (
            manifest.get("source_close_read") is True
            if require_fingerprint_constants
            else manifest.get("source_close_read") in {None, True}
        )''',
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
    'value["source_close_read"] = False',
    'value["source_close_read"] = True',
    1,
)
_source = _source.replace(
    '''        "minute_open_high_low_read_by_status": True,
        "minute_open_read_by_status": False,
        "minute_close_read_by_status": False,''',
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
_source = _source.replace(
    '''        "source_fields_read": list(RAW_COLUMNS),''',
    '''        "source_fields_read": list(RAW_COLUMNS),
        "market_benchmark_fields_read": list(market.BENCHMARK_COLUMNS),''',
    1,
)

_verify_c24 = '''        c24_manifest, c24_verification = executor._verify_prior_snapshot(
            path=C24_SNAPSHOT_PATH,
            manifest_sha256=C24_SNAPSHOT_SHA256,
            dataset_sha256=C24_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign024_feature_snapshot",
            factor_names=C24_FACTOR_NAMES,
            output_columns=C24_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
_verify_c25 = _verify_c24 + '''        c25_manifest, c25_verification = executor._verify_prior_snapshot(
            path=C25_SNAPSHOT_PATH,
            manifest_sha256=C25_SNAPSHOT_SHA256,
            dataset_sha256=C25_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign025_feature_snapshot",
            factor_names=C25_FACTOR_NAMES,
            output_columns=C25_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
if _verify_c24 not in _source:
    raise RuntimeError("Campaign025 prior-snapshot verification block was not found")
_source = _source.replace(_verify_c24, _verify_c25, 1)

_compare_c24 = '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c24_manifest,
                factors=C24_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
_compare_c25 = _compare_c24 + '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c25_manifest,
                factors=C25_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
if _compare_c24 not in _source:
    raise RuntimeError("Campaign025 comparison extension block was not found")
_source = _source.replace(_compare_c24, _compare_c25, 1)
_source = _source.replace(
    "Apply coverage before all 46 frozen uniqueness comparisons.",
    "Apply coverage before all 47 frozen uniqueness comparisons.",
    1,
)
_source = _source.replace("len(comparisons) == 46", "len(comparisons) == 47")
_source = _source.replace(
    '''            "campaign024_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    '''            "campaign024_terminal_comparison_count": 1,
            "campaign025_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    1,
)
_source = _source.replace(
    '''            "campaign024_snapshot_file_verification": c24_verification,
            "comparisons": comparisons,''',
    '''            "campaign024_snapshot_file_verification": c24_verification,
            "campaign025_snapshot_file_verification": c25_verification,
            "comparisons": comparisons,''',
    1,
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign026_features_generated",
    "MARKET_BENCHMARK_LOADER": campaign004._load_market_benchmark,
    "MARKET_BENCHMARK_MANIFEST_SHA256": MARKET_BENCHMARK_MANIFEST_SHA256,
    "MARKET_BENCHMARK_BYTE_SHA256": MARKET_BENCHMARK_BYTE_SHA256,
    "MARKET_BENCHMARK_FRAME_SHA256": MARKET_BENCHMARK_FRAME_SHA256,
}
for _campaign in (9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24):
    for _suffix in (
        "SNAPSHOT_PATH",
        "SNAPSHOT_SHA256",
        "DATASET_SHA256",
        "FACTOR_NAMES",
        "OUTPUT_COLUMNS",
    ):
        _key = f"C{_campaign}_{_suffix}"
        _generated[_key] = campaign025.engine_namespace[_key]
_generated.update(
    {
        "C25_SNAPSHOT_PATH": C25_SNAPSHOT_PATH,
        "C25_SNAPSHOT_SHA256": C25_SNAPSHOT_SHA256,
        "C25_DATASET_SHA256": C25_DATASET_SHA256,
        "C25_FACTOR_NAMES": C25_FACTOR_NAMES,
        "C25_OUTPUT_COLUMNS": C25_OUTPUT_COLUMNS,
    }
)
exec(compile(_source, str(CAMPAIGN025_FEATURE_RUNNER), "exec"), _generated)

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
market = campaign021.market

Campaign026FeatureError = _generated["Campaign026FeatureError"]


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate every frozen Campaign026 binding and no-return semantic."""

    path = path.expanduser().resolve()
    if _sha256(path) != PROTOCOL_SHA256:
        raise Campaign026FeatureError("Campaign026 no-return protocol changed")
    validation = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if not validation["all_bindings_passed"]:
        raise Campaign026FeatureError(
            "Campaign026 no-return protocol has a failed file binding"
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
    if not (
        spec.get("version") == 1
        and spec.get("kind")
        == "a_share_three_day_walkforward_campaign026_no_return_preregistration"
        and spec.get("status")
        == (
            "frozen_before_campaign026_candidate_benchmark_or_comparison_"
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
        and candidate.get("minimum_positions_per_nonzero_market_sign")
        == MINIMUM_POSITIONS_PER_MARKET_SIGN
        and candidate.get("correlation_estimator")
        == "population_pearson_equal_pair_weight"
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
        and len(comparisons) == 47
        and str(comparisons[-1].get("name") or "") == C25_FACTOR_NAMES[0]
        and boundary.get("binding_validation_required_before_candidate_values")
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
        and boundary.get("provider_request_allowed") is False
    ):
        raise Campaign026FeatureError("Campaign026 no-return semantics changed")
    if _sha256(NO_RETURN_CONTEXT_REPAIR) != NO_RETURN_CONTEXT_REPAIR_SHA256:
        raise Campaign026FeatureError(
            "Campaign026 no-return context repair changed"
        )
    repair_validation = bindings.validate_record(
        NO_RETURN_CONTEXT_REPAIR,
        data_root=DEFAULT_DATA_ROOT,
    )
    if not repair_validation["all_bindings_passed"]:
        raise Campaign026FeatureError(
            "Campaign026 no-return context repair has a failed file binding"
        )
    repair = json.loads(NO_RETURN_CONTEXT_REPAIR.read_text(encoding="utf-8"))
    repair_boundary = repair.get("repair_boundary") or {}
    point_in_time_context = repair.get("point_in_time_context") or {}
    frozen_precedent_context = campaign025.load_protocol().get(
        "point_in_time_context"
    )
    comparable_context = dict(point_in_time_context)
    comparable_precedent_context = dict(frozen_precedent_context or {})
    comparable_context.pop("survivorship_limitation", None)
    comparable_precedent_context.pop("survivorship_limitation", None)
    if not (
        repair.get("version") == 1
        and repair.get("kind")
        == "a_share_three_day_walkforward_campaign026_no_return_context_repair"
        and repair.get("status")
        == "frozen_before_candidate_or_comparison_values_or_returns"
        and repair_boundary.get("original_preregistration_remains_immutable")
        is True
        and repair_boundary.get("candidate_formula_or_direction_changed")
        is False
        and repair_boundary.get("coverage_or_uniqueness_threshold_changed")
        is False
        and repair_boundary.get("comparison_library_changed") is False
        and repair_boundary.get("finite_search_plan_changed") is False
        and repair_boundary.get(
            "development_or_stress_return_boundary_changed"
        )
        is False
        and repair_boundary.get("only_missing_point_in_time_context_supplied")
        is True
        and comparable_context == comparable_precedent_context
        and point_in_time_context.get("survivorship_limitation")
        == (
            "The current-listing-derived holding universe may introduce "
            "survivorship bias. Campaign026 is research-only and cannot be "
            "promoted without point-in-time listing and delisting history."
        )
    ):
        raise Campaign026FeatureError(
            "Campaign026 no-return context repair semantics changed"
        )
    spec["point_in_time_context"] = point_in_time_context
    return spec


def _masked_population_correlation(
    left: np.ndarray,
    right: np.ndarray,
    mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    counts = mask.sum(axis=1).astype(np.int64)
    safe_counts = np.where(counts > 0, counts, 1)
    left_mean = np.sum(np.where(mask, left, 0.0), axis=1) / safe_counts
    right_mean = np.sum(np.where(mask, right, 0.0), axis=1) / safe_counts
    left_centered = np.where(mask, left - left_mean[:, None], 0.0)
    right_centered = np.where(mask, right - right_mean[:, None], 0.0)
    left_energy = np.sum(left_centered * left_centered, axis=1)
    right_energy = np.sum(right_centered * right_centered, axis=1)
    denominator = np.sqrt(left_energy * right_energy)
    with np.errstate(divide="ignore", invalid="ignore"):
        correlation = np.divide(
            np.sum(left_centered * right_centered, axis=1),
            denominator,
            out=np.full(len(left), np.nan, dtype=float),
            where=denominator > 0.0,
        )
    return correlation, denominator, counts


def compute_factor_values(
    *,
    within_half_returns: np.ndarray,
    leave_one_out_market_returns: np.ndarray,
    sufficient_peers: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute frozen same-minute up-minus-down market dependence."""

    stock = np.asarray(within_half_returns, dtype=float)
    market_returns = np.asarray(leave_one_out_market_returns, dtype=float)
    sufficient_peers = np.asarray(sufficient_peers, dtype=bool)
    if (
        stock.ndim != 2
        or stock.shape[1] != RETURN_POSITIONS
        or market_returns.shape != stock.shape
        or sufficient_peers.shape != (len(stock),)
    ):
        raise Campaign026FeatureError("Campaign026 return arrays are invalid")

    finite_vectors = np.isfinite(stock).all(axis=1) & np.isfinite(
        market_returns
    ).all(axis=1)
    up_mask = market_returns > 0.0
    down_mask = market_returns < 0.0
    up_correlation, up_denominator, up_counts = _masked_population_correlation(
        stock,
        market_returns,
        up_mask,
    )
    down_correlation, down_denominator, down_counts = (
        _masked_population_correlation(
            stock,
            market_returns,
            down_mask,
        )
    )
    enough_sign_support = (
        (up_counts >= MINIMUM_POSITIONS_PER_MARKET_SIGN)
        & (down_counts >= MINIMUM_POSITIONS_PER_MARKET_SIGN)
    )
    positive_variance = (up_denominator > 0.0) & (down_denominator > 0.0)
    values = up_correlation - down_correlation
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
    eligible = (
        finite_vectors
        & sufficient_peers
        & enough_sign_support
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
        f"{FACTOR_NAME}__insufficient_market_sign_support_rows": int(
            (finite_vectors & sufficient_peers & ~enough_sign_support).sum()
        ),
        f"{FACTOR_NAME}__degenerate_correlation_rows": int(
            (
                finite_vectors
                & sufficient_peers
                & enough_sign_support
                & ~positive_variance
            ).sum()
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
                & enough_sign_support
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


def _campaign026_market_benchmark() -> Any:
    global _MARKET_BENCHMARK_CACHE
    if _MARKET_BENCHMARK_CACHE is None:
        _MARKET_BENCHMARK_CACHE = campaign004._load_market_benchmark(
            DEFAULT_DATA_ROOT
        )
        if (
            getattr(_MARKET_BENCHMARK_CACHE, "frame_sha256", None)
            != MARKET_BENCHMARK_FRAME_SHA256
        ):
            raise Campaign026FeatureError("market benchmark fingerprint changed")
    return _MARKET_BENCHMARK_CACHE


def compute_partition_frame(
    raw: pd.DataFrame,
    base: pd.DataFrame,
    _unused_benchmark: Any,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Validate one stock-year close path and compute Campaign026."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign026FeatureError(
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
    benchmark = _campaign026_market_benchmark()
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
        raise Campaign026FeatureError(f"return validity changed for {symbol}")
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
