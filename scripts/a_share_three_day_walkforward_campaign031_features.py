#!/usr/bin/env python3
"""Build and no-return audit Campaign031 market-dispersion decoupling."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

try:
    import scripts.a_share_three_day_preregistration_binding_validator as bindings
    import scripts.a_share_three_day_walkforward_campaign030_features as campaign030
    import scripts.a_share_three_day_walkforward_campaign031_dispersion_benchmark as dispersion_builder
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_three_day_walkforward_campaign030_features as campaign030
    import a_share_three_day_walkforward_campaign031_dispersion_benchmark as dispersion_builder


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN030_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign030_features.py"
)
CAMPAIGN030_FEATURE_RUNNER_SHA256 = (
    "1cf79e2686b0ebe246ef552e585a6b7d697811d44fb70ee59467c37f8d9d9644"
)
OLD_FACTOR = "intraday_market_correlation_resolution_119p"
FACTOR_NAME = "intraday_market_dispersion_decoupling_238m"
MECHANISM_AUDIT_SHA256 = (
    "5af9f4a6ebde5e2ab77c2ffb9cb8abc1fef0ab710c0c933ee64272cd74cb3a00"
)
PROTOCOL_SHA256 = (
    "95951a357ffef3eee46f8d220d150fd00223b32f27f6cf93a92c4f6c17452f6d"
)
BENCHMARK_FREEZE_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_031_"
    "dispersion_benchmark_freeze_20260730.json"
)
BENCHMARK_FREEZE_SHA256 = (
    "5512e1025b8c833d9356e2a3e93cedeae42611504e956edf32c062a013c3a5ad"
)

# Bind these only after the corresponding artifacts are created.
SNAPSHOT_MANIFEST_SHA256 = (
    "4df07ce452454d742521e835f2b7954fe53c597ba47ec31438cb47fd2abbd086"
)
SNAPSHOT_DATASET_SHA256 = (
    "9858378a035142b36f19bf00b0b8c7847802e428f6798dc1900b2ae003bcd6b1"
)
NO_RETURN_AUDIT_SHA256 = (
    "659c3282bd02d85f5b3da99e555ba25ec227bf6c8546e50f12bc5e8ad97e30d9"
)

DISPERSION_BENCHMARK_MANIFEST_SHA256 = (
    "bbb82784b4daa21080045a17239868b1063d233607f125d03acab2aefb4fee50"
)
DISPERSION_BENCHMARK_BYTE_SHA256 = (
    "317aa3cb1793498bbce03018b692e6252939e689f0b9982e7c991a0da82d8827"
)
DISPERSION_BENCHMARK_FRAME_SHA256 = (
    "c4933078610a4a14597a35d54ac98f9089a90522b73d8d428cde9e5eec79201f"
)
MINIMUM_LEAVE_ONE_OUT_PEERS = 50
RETURN_POSITIONS = 238
NEGATIVE_VARIANCE_TOLERANCE = 1e-18
ENDPOINT_TOLERANCE = 1e-12

C30_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign030_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign030_feature_library_v1/snapshot_manifest.json"
)
C30_SNAPSHOT_SHA256 = (
    "bc34e382f427d02380b6bf7858ad364064540cf1ec9be3b91e878bfefc84ab42"
)
C30_DATASET_SHA256 = (
    "10953d752e924d0be3692c5bd0a392cb27d7009c3e7c3358c8602215d70dc549"
)
C30_FACTOR_NAMES = ("intraday_market_correlation_resolution_119p",)
C30_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C30_FACTOR_NAMES[0],
    f"{C30_FACTOR_NAMES[0]}_eligible",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN030_FEATURE_RUNNER) != CAMPAIGN030_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign030 feature orchestration fingerprint changed")

_source = campaign030._source
for _old, _new in (
    ("Campaign030", "Campaign031"),
    ("campaign030", "campaign031"),
    ("campaign_030", "campaign_031"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "e32bd7824c8bf752d632d852b617ba5fca1b8be4059beccf79d82ebf7f33d6fb",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "15a7a9c3d255d1cae56d5b8ee3e3b0b69bb78a1a85a741a3c0b364ac0ee340f0",
        PROTOCOL_SHA256,
    ),
    (
        "bc34e382f427d02380b6bf7858ad364064540cf1ec9be3b91e878bfefc84ab42",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "10953d752e924d0be3692c5bd0a392cb27d7009c3e7c3358c8602215d70dc549",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "3cec65d23b1d7952813e67db2e9b1d7486be797925e470703c3a9b4a5cf97a3b",
        NO_RETURN_AUDIT_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_old_formula = '''FACTOR_FORMULA = (
    "population PearsonCorr(stock_return, leave_one_out_market_return) "
    "over the 119 morning within-half return positions minus the same "
    "population Pearson correlation over the 119 afternoon within-half "
    "return positions"
)'''
_new_formula = '''FACTOR_FORMULA = (
    "negative population PearsonCorr(abs(stock_return), "
    "sqrt(population variance of all other valid stock returns at the same "
    "date and return position)) over exactly 238 within-half return positions"
)'''
if _old_formula not in _source:
    raise RuntimeError("Campaign030 formula block was not found")
_source = _source.replace(_old_formula, _new_formula, 1)

_verify_c29 = '''        c29_manifest, c29_verification = executor._verify_prior_snapshot(
            path=C29_SNAPSHOT_PATH,
            manifest_sha256=C29_SNAPSHOT_SHA256,
            dataset_sha256=C29_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign029_feature_snapshot",
            factor_names=C29_FACTOR_NAMES,
            output_columns=C29_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
_verify_c30 = _verify_c29 + '''        c30_manifest, c30_verification = executor._verify_prior_snapshot(
            path=C30_SNAPSHOT_PATH,
            manifest_sha256=C30_SNAPSHOT_SHA256,
            dataset_sha256=C30_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign030_feature_snapshot",
            factor_names=C30_FACTOR_NAMES,
            output_columns=C30_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
if _verify_c29 not in _source:
    raise RuntimeError("Campaign030 prior-snapshot verification block was not found")
_source = _source.replace(_verify_c29, _verify_c30, 1)

_compare_c29 = '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c29_manifest,
                factors=C29_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
_compare_c30 = _compare_c29 + '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c30_manifest,
                factors=C30_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
if _compare_c29 not in _source:
    raise RuntimeError("Campaign030 comparison extension block was not found")
_source = _source.replace(_compare_c29, _compare_c30, 1)
_source = _source.replace(
    "Apply coverage before all 51 frozen uniqueness comparisons.",
    "Apply coverage before all 52 frozen uniqueness comparisons.",
    1,
)
_source = _source.replace("len(comparisons) == 51", "len(comparisons) == 52")
_source = _source.replace(
    '''            "campaign029_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    '''            "campaign029_terminal_comparison_count": 1,
            "campaign030_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    1,
)
_source = _source.replace(
    '''            "campaign029_snapshot_file_verification": c29_verification,
            "comparisons": comparisons,''',
    '''            "campaign029_snapshot_file_verification": c29_verification,
            "campaign030_snapshot_file_verification": c30_verification,
            "comparisons": comparisons,''',
    1,
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign031_features_generated",
    "MARKET_SNAPSHOT_SHA256": DISPERSION_BENCHMARK_MANIFEST_SHA256,
    "MARKET_BENCHMARK_MANIFEST_SHA256": DISPERSION_BENCHMARK_MANIFEST_SHA256,
    "MARKET_BENCHMARK_BYTE_SHA256": DISPERSION_BENCHMARK_BYTE_SHA256,
    "MARKET_BENCHMARK_FRAME_SHA256": DISPERSION_BENCHMARK_FRAME_SHA256,
}
for _campaign in (
    9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26,
    27, 28, 29,
):
    for _suffix in (
        "SNAPSHOT_PATH",
        "SNAPSHOT_SHA256",
        "DATASET_SHA256",
        "FACTOR_NAMES",
        "OUTPUT_COLUMNS",
    ):
        _key = f"C{_campaign}_{_suffix}"
        _generated[_key] = campaign030.engine_namespace[_key]
_generated.update(
    {
        "C30_SNAPSHOT_PATH": C30_SNAPSHOT_PATH,
        "C30_SNAPSHOT_SHA256": C30_SNAPSHOT_SHA256,
        "C30_DATASET_SHA256": C30_DATASET_SHA256,
        "C30_FACTOR_NAMES": C30_FACTOR_NAMES,
        "C30_OUTPUT_COLUMNS": C30_OUTPUT_COLUMNS,
    }
)
exec(
    compile(_source, str(CAMPAIGN030_FEATURE_RUNNER), "exec"),
    _generated,
)


class _MarketProxy:
    """Expose the frozen dispersion schema without mutating prior modules."""

    BENCHMARK_COLUMNS = dispersion_builder.BENCHMARK_COLUMNS

    def __getattr__(self, name: str) -> Any:
        return getattr(campaign030.market, name)


_generated["market"] = _MarketProxy()

RAW_COLUMNS = ("datetime", "symbol", "provider", "close")
BASE_COLUMNS = _generated["BASE_COLUMNS"]
SELECTED_BAR_COUNT = _generated["SELECTED_BAR_COUNT"]
OUTPUT_COLUMNS = _generated["OUTPUT_COLUMNS"]
FACTOR_NAMES = _generated["FACTOR_NAMES"]
FACTOR_DIRECTIONS = _generated["FACTOR_DIRECTIONS"]
FACTOR_RANGES = {FACTOR_NAME: (-1.0, 1.0)}
FACTOR_FORMULA = _generated["FACTOR_FORMULA"]
FACTOR_FORMULAS = {FACTOR_NAME: FACTOR_FORMULA}
DEFAULT_PROTOCOL = _generated["DEFAULT_PROTOCOL"]
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT = _generated["DEFAULT_EXPERIMENT_ROOT"]
market = _generated["market"]

_generated["FACTOR_RANGES"] = FACTOR_RANGES
_generated["FACTOR_FORMULAS"] = FACTOR_FORMULAS

Campaign031FeatureError = _generated["Campaign031FeatureError"]


@dataclass(frozen=True)
class DispersionBenchmark:
    """Dense frozen same-date cross-sectional return moments."""

    dates: pd.DatetimeIndex
    return_sums: np.ndarray
    return_sum_squares: np.ndarray
    valid_stock_counts: np.ndarray
    date_to_index: dict[pd.Timestamp, int]
    frame_sha256: str


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate every frozen binding and exact Campaign031 semantics."""

    path = path.expanduser().resolve()
    if _sha256(path) != PROTOCOL_SHA256:
        raise Campaign031FeatureError("Campaign031 no-return protocol changed")
    for record in (path, BENCHMARK_FREEZE_PATH):
        validation = bindings.validate_record(
            record, data_root=DEFAULT_DATA_ROOT
        )
        if not validation["all_bindings_passed"]:
            raise Campaign031FeatureError(
                "Campaign031 no-return or benchmark-freeze binding failed"
            )
    if _sha256(BENCHMARK_FREEZE_PATH) != BENCHMARK_FREEZE_SHA256:
        raise Campaign031FeatureError(
            "Campaign031 benchmark freeze record changed"
        )
    spec = json.loads(path.read_text(encoding="utf-8"))
    candidate_list = list(spec.get("candidates") or [])
    candidate = candidate_list[0] if len(candidate_list) == 1 else {}
    benchmark = spec.get("dispersion_benchmark") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    comparisons = list(uniqueness.get("comparison_factors") or [])
    boundary = spec.get("research_boundary") or {}
    source_chain = spec.get("source_chain") or {}
    mechanism = source_chain.get("mechanism_overlap_audit") or {}
    finite_search = spec.get("finite_post_admissibility_search") or {}
    trial = finite_search.get("trial") or {}
    if not (
        spec.get("version") == 1
        and spec.get("kind")
        == "a_share_three_day_walkforward_campaign031_no_return_preregistration"
        and spec.get("status")
        == (
            "frozen_before_campaign031_dispersion_benchmark_candidate_"
            "comparison_or_return_values"
        )
        and len(candidate_list) == 1
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_fields_allowed") or ()) == RAW_COLUMNS
        and tuple(candidate.get("source_fields_used_by_formula") or ())
        == RAW_COLUMNS
        and tuple(candidate.get("benchmark_fields_allowed") or ())
        == dispersion_builder.BENCHMARK_COLUMNS
        and tuple(benchmark.get("columns") or ())
        == dispersion_builder.BENCHMARK_COLUMNS
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("within_half_return_count") == RETURN_POSITIONS
        and candidate.get("minimum_leave_one_out_peers_per_return_position")
        == MINIMUM_LEAVE_ONE_OUT_PEERS
        and candidate.get("benchmark_contribution_requires_complete_return_vector")
        is True
        and candidate.get("cross_sectional_variance_estimator")
        == (
            "population_sum_squares_over_n_minus_squared_sum_over_n_"
            "without_bessel_correction"
        )
        and candidate.get("tiny_negative_variance_canonicalization_tolerance")
        == NEGATIVE_VARIANCE_TOLERANCE
        and candidate.get("dispersion_transform") == "nonnegative_square_root"
        and candidate.get("stock_transform") == "exact_absolute_value"
        and candidate.get("correlation_estimator")
        == "population_pearson_equal_position_weight"
        and candidate.get("direction_transform")
        == "multiply_population_correlation_by_exact_negative_one"
        and candidate.get("endpoint_canonicalization_tolerance")
        == ENDPOINT_TOLERANCE
        and candidate.get("valid_range") == [-1.0, 1.0]
        and mechanism.get("sha256") == MECHANISM_AUDIT_SHA256
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
        and len(comparisons) == 52
        and str(comparisons[-1].get("name") or "") == C30_FACTOR_NAMES[0]
        and finite_search.get("candidate_factor_count") == 1
        and finite_search.get("development_trial_count") == 1
        and trial.get("factor") == FACTOR_NAME
        and trial.get("direction") == "higher"
        and trial.get("transform") == "none"
        and trial.get("threshold") == "none"
        and trial.get("filter") == "none"
        and trial.get("combination") == "none"
        and boundary.get(
            "binding_validation_required_before_dispersion_benchmark_or_"
            "candidate_values"
        )
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
            "frozen_dispersion_benchmark_sum_sum_squares_count_fields_read_"
            "before_admissibility"
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
        raise Campaign031FeatureError("Campaign031 no-return semantics changed")
    return spec


def _load_dispersion_benchmark(_data_root: Path) -> DispersionBenchmark:
    """Load and reproduce the fingerprint-frozen dispersion benchmark."""

    manifest_path = (
        dispersion_builder.output_root(DEFAULT_DATA_ROOT)
        / "snapshot_manifest.json"
    )
    if _sha256(manifest_path) != DISPERSION_BENCHMARK_MANIFEST_SHA256:
        raise Campaign031FeatureError(
            "Campaign031 dispersion benchmark manifest changed"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    dispersion_builder._validate_published_manifest(
        manifest, require_bound_fingerprints=True
    )
    frame_path = Path(str((manifest.get("benchmark") or {}).get("path")))
    if _sha256(frame_path) != DISPERSION_BENCHMARK_BYTE_SHA256:
        raise Campaign031FeatureError(
            "Campaign031 dispersion benchmark bytes changed"
        )
    frame = pd.read_parquet(
        frame_path, columns=list(dispersion_builder.BENCHMARK_COLUMNS)
    )
    frame_sha256 = market.foundation.frame_digest(frame)
    if frame_sha256 != DISPERSION_BENCHMARK_FRAME_SHA256:
        raise Campaign031FeatureError(
            "Campaign031 dispersion benchmark frame changed"
        )
    frame["trade_date"] = pd.to_datetime(
        frame["trade_date"], errors="coerce"
    ).dt.normalize()
    frame = frame.sort_values(
        ["trade_date", "return_position"], kind="stable"
    ).reset_index(drop=True)
    dates = pd.DatetimeIndex(frame["trade_date"].drop_duplicates())
    expected_rows = len(dates) * RETURN_POSITIONS
    if (
        len(dates) != dispersion_builder.EXPECTED_TRADE_DATES
        or len(frame) != expected_rows
        or frame["trade_date"].isna().any()
        or frame.duplicated(["trade_date", "return_position"]).any()
        or not np.array_equal(
            frame["return_position"].to_numpy(dtype=np.int16),
            np.tile(
                np.arange(RETURN_POSITIONS, dtype=np.int16), len(dates)
            ),
        )
    ):
        raise Campaign031FeatureError(
            "Campaign031 dispersion benchmark key grid changed"
        )
    sums = pd.to_numeric(
        frame["return_sum"], errors="coerce"
    ).to_numpy(dtype=float).reshape(-1, RETURN_POSITIONS)
    sum_squares = pd.to_numeric(
        frame["return_sum_squares"], errors="coerce"
    ).to_numpy(dtype=float).reshape(-1, RETURN_POSITIONS)
    counts = pd.to_numeric(
        frame["valid_stock_count"], errors="coerce"
    ).to_numpy(dtype=np.int64).reshape(-1, RETURN_POSITIONS)
    if (
        not np.isfinite(sums).all()
        or not np.isfinite(sum_squares).all()
        or (sum_squares < 0.0).any()
        or (counts < MINIMUM_LEAVE_ONE_OUT_PEERS + 1).any()
    ):
        raise Campaign031FeatureError(
            "Campaign031 dispersion benchmark values are invalid"
        )
    return DispersionBenchmark(
        dates=dates,
        return_sums=sums,
        return_sum_squares=sum_squares,
        valid_stock_counts=counts,
        date_to_index={
            pd.Timestamp(value).normalize(): index
            for index, value in enumerate(dates)
        },
        frame_sha256=frame_sha256,
    )


def _benchmark_for_dates(
    benchmark: DispersionBenchmark,
    dates: Sequence[pd.Timestamp],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
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
        raise Campaign031FeatureError(
            f"candidate date is outside dispersion benchmark: {exc}"
        ) from exc
    return (
        benchmark.return_sums[indices],
        benchmark.return_sum_squares[indices],
        benchmark.valid_stock_counts[indices],
    )


_DISPERSION_BENCHMARK_CACHE: DispersionBenchmark | None = None


def _campaign031_dispersion_benchmark() -> DispersionBenchmark:
    """Load the frozen benchmark once per process for inherited orchestration."""

    global _DISPERSION_BENCHMARK_CACHE
    if _DISPERSION_BENCHMARK_CACHE is None:
        _DISPERSION_BENCHMARK_CACHE = _load_dispersion_benchmark(
            DEFAULT_DATA_ROOT
        )
    return _DISPERSION_BENCHMARK_CACHE


def _population_correlation(
    left: np.ndarray,
    right: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    left_centered = left - left.mean(axis=1)[:, None]
    right_centered = right - right.mean(axis=1)[:, None]
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
    low_near = (
        (correlation < -1.0)
        & (correlation >= -1.0 - ENDPOINT_TOLERANCE)
    )
    high_near = (
        (correlation > 1.0)
        & (correlation <= 1.0 + ENDPOINT_TOLERANCE)
    )
    canonicalized = low_near | high_near
    correlation = np.where(
        low_near, -1.0, np.where(high_near, 1.0, correlation)
    )
    return correlation, left_energy, right_energy, canonicalized


def compute_factor_values(
    *,
    within_half_returns: np.ndarray,
    leave_one_out_variances: np.ndarray,
    sufficient_peers: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute frozen negative stock-magnitude/market-dispersion correlation."""

    stock = np.asarray(within_half_returns, dtype=float)
    raw_variances = np.asarray(leave_one_out_variances, dtype=float)
    sufficient_peers = np.asarray(sufficient_peers, dtype=bool)
    if (
        stock.ndim != 2
        or stock.shape[1] != RETURN_POSITIONS
        or raw_variances.shape != stock.shape
        or sufficient_peers.shape != (len(stock),)
    ):
        raise Campaign031FeatureError("Campaign031 input arrays are invalid")
    material_negative = (
        np.isfinite(raw_variances)
        & (raw_variances < -NEGATIVE_VARIANCE_TOLERANCE)
    )
    tiny_negative = (
        np.isfinite(raw_variances)
        & (raw_variances < 0.0)
        & ~material_negative
    )
    variances = np.where(tiny_negative, 0.0, raw_variances)
    with np.errstate(invalid="ignore"):
        dispersion = np.sqrt(variances)
    magnitudes = np.abs(stock)
    finite_vectors = (
        np.isfinite(magnitudes).all(axis=1)
        & np.isfinite(dispersion).all(axis=1)
        & ~material_negative.any(axis=1)
    )
    correlation, magnitude_energy, dispersion_energy, canonicalized = (
        _population_correlation(magnitudes, dispersion)
    )
    positive_variance = (
        (magnitude_energy > 0.0) & (dispersion_energy > 0.0)
    )
    values = -correlation
    finite_values = np.isfinite(values)
    in_range = (values >= -1.0) & (values <= 1.0)
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
        f"{FACTOR_NAME}__invalid_stock_or_dispersion_rows": int(
            (~finite_vectors).sum()
        ),
        f"{FACTOR_NAME}__insufficient_peer_rows": int(
            (finite_vectors & ~sufficient_peers).sum()
        ),
        f"{FACTOR_NAME}__material_negative_variance_rows": int(
            material_negative.any(axis=1).sum()
        ),
        f"{FACTOR_NAME}__tiny_negative_variance_positions_canonicalized": int(
            tiny_negative.sum()
        ),
        f"{FACTOR_NAME}__degenerate_stock_magnitude_variance_rows": int(
            (
                finite_vectors
                & sufficient_peers
                & ~(magnitude_energy > 0.0)
            ).sum()
        ),
        f"{FACTOR_NAME}__degenerate_dispersion_variance_rows": int(
            (
                finite_vectors
                & sufficient_peers
                & ~(dispersion_energy > 0.0)
            ).sum()
        ),
        f"{FACTOR_NAME}__exact_zero_stock_return_positions": int(
            (stock == 0.0).sum()
        ),
        f"{FACTOR_NAME}__exact_zero_dispersion_positions": int(
            (dispersion == 0.0).sum()
        ),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int(
            canonicalized.sum()
        ),
        f"{FACTOR_NAME}__invalid_final_range_rows": int(
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


def compute_partition_frame(
    raw: pd.DataFrame,
    base: pd.DataFrame,
    _unused_benchmark: Any,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Validate one stock-year close path and compute Campaign031."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign031FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    base_work, within_half_returns, return_valid = (
        market.extract_partition_returns(raw, base, symbol=symbol)
    )
    if base_work.empty:
        return _generated["empty_output_frame"](), {"base_rows": 0}
    benchmark = _campaign031_dispersion_benchmark()
    sums, sum_squares, counts = _benchmark_for_dates(
        benchmark, list(base_work["trade_date"])
    )
    own = np.where(return_valid[:, None], within_half_returns, 0.0)
    own_squares = own * own
    own_count = return_valid.astype(np.int64)[:, None]
    peer_counts = counts.astype(np.int64) - own_count
    peer_sums = sums - own
    peer_sum_squares = sum_squares - own_squares
    sufficient = (peer_counts >= MINIMUM_LEAVE_ONE_OUT_PEERS).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        peer_means = np.divide(
            peer_sums,
            peer_counts,
            out=np.full_like(peer_sums, np.nan, dtype=float),
            where=peer_counts > 0,
        )
        peer_second_moments = np.divide(
            peer_sum_squares,
            peer_counts,
            out=np.full_like(peer_sum_squares, np.nan, dtype=float),
            where=peer_counts > 0,
        )
        peer_variances = peer_second_moments - peer_means * peer_means
    values, eligible, quality = compute_factor_values(
        within_half_returns=within_half_returns,
        leave_one_out_variances=peer_variances,
        sufficient_peers=sufficient,
    )
    if not np.array_equal(
        return_valid,
        np.isfinite(within_half_returns).all(axis=1),
    ):
        raise Campaign031FeatureError(f"return validity changed for {symbol}")
    return (
        pd.DataFrame(
            {
                "trade_date": base_work["trade_date"],
                "symbol": symbol.upper(),
                "provider": "tushare_leave_one_out_market_dispersion",
                FACTOR_NAME: values[FACTOR_NAME],
                f"{FACTOR_NAME}_eligible": eligible[FACTOR_NAME],
            }
        ).loc[:, OUTPUT_COLUMNS],
        quality,
    )


_generated["load_protocol"] = load_protocol
_generated["_load_market_benchmark"] = _load_dispersion_benchmark
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
