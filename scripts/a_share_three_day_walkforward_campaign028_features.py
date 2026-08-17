#!/usr/bin/env python3
"""Build and no-return audit Campaign028 absolute-return persistence.

Campaign027 supplies the tested snapshot and comparison orchestration. This
wrapper changes only the campaign namespace and candidate computation, reads
the close path, and appends the terminal Campaign027 snapshot as comparison 49.
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
    import scripts.a_share_three_day_walkforward_campaign027_features as campaign027
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_three_day_walkforward_campaign027_features as campaign027


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN027_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign027_features.py"
)
CAMPAIGN027_FEATURE_RUNNER_SHA256 = (
    "3b1caf58520ad336fb00bcbfcd3484973f0fee43ee5441b743c6dd9784e2a575"
)
OLD_FACTOR = "intraday_morning_afternoon_return_profile_persistence_119p"
FACTOR_NAME = "intraday_absolute_return_serial_persistence_236p"
MECHANISM_AUDIT_SHA256 = (
    "f41e33bb607e7adf6a7ba3c731bae40fbaa85fdc9e5ee054831607bbcd518a2a"
)
PROTOCOL_SHA256 = (
    "704dbe2f21624a5b97ac597c9e79b1ca6e7611903eef39624a701a1e0acc10bc"
)

# Bind these immutable fingerprints only after the corresponding artifacts exist.
SNAPSHOT_MANIFEST_SHA256 = (
    "b08065c1cb7dbdbf06e4285a0c686338e121d27546fce97bb92dc9251f8366d0"
)
SNAPSHOT_DATASET_SHA256 = (
    "8d3a3368ed85c0215751bf86b7d491bf9ad049762a810cce2e50b1a3b4badadf"
)
NO_RETURN_AUDIT_SHA256 = (
    "9f077d989d0456cbfaf23fbcce4d3737ac3da25380c50435cfddbc7f31fe0963"
)

RETURN_COUNT = 238
PAIRED_RETURN_COUNT = 236
ENDPOINT_TOLERANCE = 1e-12

C27_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign027_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign027_feature_library_v1/snapshot_manifest.json"
)
C27_SNAPSHOT_SHA256 = (
    "0c7082a9c249f1567ca85f1490cb63a7affb86fe7583e92fa13b6dc9e88dab50"
)
C27_DATASET_SHA256 = (
    "bdde7057d2f7174afccd7b5789d79c3c01cc56c13a7e14889d9913cd81851365"
)
C27_FACTOR_NAMES = ("intraday_morning_afternoon_return_profile_persistence_119p",)
C27_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C27_FACTOR_NAMES[0],
    f"{C27_FACTOR_NAMES[0]}_eligible",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN027_FEATURE_RUNNER) != CAMPAIGN027_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign027 feature orchestration fingerprint changed")

_source = campaign027._source
for _old, _new in (
    ("Campaign027", "Campaign028"),
    ("campaign027", "campaign028"),
    ("campaign_027", "campaign_028"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "1d11781aa307ea32390e702bd5bb1522008e0b7163a5e8ce13b3cdeca07561ef",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "eb5b83b7b0d957a515c7083d481f4fe6a375f9a3500910270f3c0bc62c2ac7cd",
        PROTOCOL_SHA256,
    ),
    (
        "0c7082a9c249f1567ca85f1490cb63a7affb86fe7583e92fa13b6dc9e88dab50",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "bdde7057d2f7174afccd7b5789d79c3c01cc56c13a7e14889d9913cd81851365",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "efdbdca5b7bb41eb82e7680543d29675675919cbe1df97044289c5e43a1cf1e1",
        NO_RETURN_AUDIT_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_old_formula = '''FACTOR_FORMULA = (
    "population PearsonCorr(r_am,k, r_pm,k) for k=1..119, where each "
    "vector contains adjacent log-close returns inside its own 120-bar "
    "trading half"
)'''
_new_formula = '''FACTOR_FORMULA = (
    "population PearsonCorr(abs(r_t), abs(r_t+1)) across the 118 adjacent "
    "return-magnitude pairs inside each 120-close trading half, pooled to "
    "236 equal-weight pairs"
)'''
if _old_formula not in _source:
    raise RuntimeError("Campaign027 formula block was not found")
_source = _source.replace(_old_formula, _new_formula, 1)

# Campaign027's immutable audit kept two inherited display booleans and added an
# authoritative correction. Campaign028 fixes the display before publication.
_source = _source.replace(
    '''        "minute_open_high_low_read": True,
        "minute_open_read": False,
        "minute_close_read": False,''',
    '''        "minute_open_high_low_read": False,
        "minute_open_read": False,
        "minute_close_read": True,''',
    1,
)

_verify_c26 = '''        c26_manifest, c26_verification = executor._verify_prior_snapshot(
            path=C26_SNAPSHOT_PATH,
            manifest_sha256=C26_SNAPSHOT_SHA256,
            dataset_sha256=C26_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign026_feature_snapshot",
            factor_names=C26_FACTOR_NAMES,
            output_columns=C26_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
_verify_c27 = _verify_c26 + '''        c27_manifest, c27_verification = executor._verify_prior_snapshot(
            path=C27_SNAPSHOT_PATH,
            manifest_sha256=C27_SNAPSHOT_SHA256,
            dataset_sha256=C27_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign027_feature_snapshot",
            factor_names=C27_FACTOR_NAMES,
            output_columns=C27_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
if _verify_c26 not in _source:
    raise RuntimeError("Campaign027 prior-snapshot verification block was not found")
_source = _source.replace(_verify_c26, _verify_c27, 1)

_compare_c26 = '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c26_manifest,
                factors=C26_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
_compare_c27 = _compare_c26 + '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c27_manifest,
                factors=C27_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
if _compare_c26 not in _source:
    raise RuntimeError("Campaign027 comparison extension block was not found")
_source = _source.replace(_compare_c26, _compare_c27, 1)
_source = _source.replace(
    "Apply coverage before all 48 frozen uniqueness comparisons.",
    "Apply coverage before all 49 frozen uniqueness comparisons.",
    1,
)
_source = _source.replace("len(comparisons) == 48", "len(comparisons) == 49")
_source = _source.replace(
    '''            "campaign026_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    '''            "campaign026_terminal_comparison_count": 1,
            "campaign027_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    1,
)
_source = _source.replace(
    '''            "campaign026_snapshot_file_verification": c26_verification,
            "comparisons": comparisons,''',
    '''            "campaign026_snapshot_file_verification": c26_verification,
            "campaign027_snapshot_file_verification": c27_verification,
            "comparisons": comparisons,''',
    1,
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign028_features_generated",
}
for _campaign in (9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26):
    for _suffix in (
        "SNAPSHOT_PATH",
        "SNAPSHOT_SHA256",
        "DATASET_SHA256",
        "FACTOR_NAMES",
        "OUTPUT_COLUMNS",
    ):
        _key = f"C{_campaign}_{_suffix}"
        _generated[_key] = campaign027.engine_namespace[_key]
_generated.update(
    {
        "C27_SNAPSHOT_PATH": C27_SNAPSHOT_PATH,
        "C27_SNAPSHOT_SHA256": C27_SNAPSHOT_SHA256,
        "C27_DATASET_SHA256": C27_DATASET_SHA256,
        "C27_FACTOR_NAMES": C27_FACTOR_NAMES,
        "C27_OUTPUT_COLUMNS": C27_OUTPUT_COLUMNS,
    }
)
exec(
    compile(_source, str(CAMPAIGN027_FEATURE_RUNNER), "exec"),
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

Campaign028FeatureError = _generated["Campaign028FeatureError"]


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate every frozen binding and the exact no-return semantics."""

    path = path.expanduser().resolve()
    if _sha256(path) != PROTOCOL_SHA256:
        raise Campaign028FeatureError("Campaign028 no-return protocol changed")
    validation = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if not validation["all_bindings_passed"]:
        raise Campaign028FeatureError(
            "Campaign028 no-return protocol has a failed file binding"
        )
    spec = json.loads(path.read_text(encoding="utf-8"))
    candidate_list = list(spec.get("candidates") or [])
    candidate = candidate_list[0] if len(candidate_list) == 1 else {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    comparisons = list(uniqueness.get("comparison_factors") or [])
    boundary = spec.get("research_boundary") or {}
    mechanism = (spec.get("source_chain") or {}).get("mechanism_overlap_audit") or {}
    finite_search = spec.get("finite_post_admissibility_search") or {}
    trial = finite_search.get("trial") or {}
    if not (
        spec.get("version") == 1
        and spec.get("kind")
        == "a_share_three_day_walkforward_campaign028_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign028_candidate_or_comparison_values_or_returns"
        and len(candidate_list) == 1
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_fields_allowed") or ()) == RAW_COLUMNS
        and tuple(candidate.get("source_fields_used_by_formula") or ())
        == RAW_COLUMNS
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("return_count") == RETURN_COUNT
        and candidate.get("paired_return_count") == PAIRED_RETURN_COUNT
        and candidate.get("return_semantics")
        == (
            "Natural-log adjacent close returns are formed separately inside "
            "each 120-close half and transformed to exact absolute magnitudes; "
            "no return crosses lunch."
        )
        and candidate.get("pairing_semantics")
        == (
            "Pair magnitude positions 1 through 118 with positions 2 through "
            "119 separately inside each half, then pool 118 morning and 118 "
            "afternoon pairs."
        )
        and candidate.get("correlation_estimator")
        == "population_pearson_equal_pair_weight"
        and candidate.get("zero_return_semantics")
        == (
            "Retain every exact-zero return magnitude at every fixed lag or "
            "lead position."
        )
        and candidate.get("variance_semantics")
        == (
            "Require strictly positive population variance in both complete "
            "236-element lag and lead magnitude vectors."
        )
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
        and len(comparisons) == 49
        and str(comparisons[-1].get("name") or "") == C27_FACTOR_NAMES[0]
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
        and boundary.get("market_benchmark_fields_read_before_admissibility")
        is False
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
        raise Campaign028FeatureError("Campaign028 no-return semantics changed")
    return spec


def compute_factor_values(
    *,
    closes: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute frozen within-half adjacent absolute-return persistence."""

    closes = np.asarray(closes, dtype=float)
    if closes.ndim != 2 or closes.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign028FeatureError("Campaign028 aligned close shape is invalid")
    finite_closes = np.isfinite(closes).all(axis=1)
    positive_closes = (closes > 0.0).all(axis=1)
    required_valid = finite_closes & positive_closes
    safe_closes = np.where(closes > 0.0, closes, 1.0)
    log_closes = np.log(safe_closes)
    morning = np.abs(np.diff(log_closes[:, :120], axis=1))
    afternoon = np.abs(np.diff(log_closes[:, 120:], axis=1))
    if morning.shape[1] != 119 or afternoon.shape != morning.shape:
        raise Campaign028FeatureError("Campaign028 return-vector shape changed")
    lag = np.concatenate((morning[:, :-1], afternoon[:, :-1]), axis=1)
    lead = np.concatenate((morning[:, 1:], afternoon[:, 1:]), axis=1)
    if lag.shape[1] != PAIRED_RETURN_COUNT or lead.shape != lag.shape:
        raise Campaign028FeatureError("Campaign028 pair-vector shape changed")
    finite_returns = np.isfinite(lag).all(axis=1) & np.isfinite(lead).all(axis=1)
    lag_centered = lag - lag.mean(axis=1)[:, None]
    lead_centered = lead - lead.mean(axis=1)[:, None]
    lag_energy = np.sum(lag_centered * lag_centered, axis=1)
    lead_energy = np.sum(lead_centered * lead_centered, axis=1)
    denominator = np.sqrt(lag_energy * lead_energy)
    positive_variance = denominator > 0.0
    with np.errstate(divide="ignore", invalid="ignore"):
        values = np.divide(
            np.sum(lag_centered * lead_centered, axis=1),
            denominator,
            out=np.full(len(closes), np.nan, dtype=float),
            where=positive_variance,
        )
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
        required_valid
        & finite_returns
        & positive_variance
        & finite_values
        & in_range
    )
    quality = {
        "base_rows": int(len(closes)),
        "invalid_required_close_rows": int((~finite_closes).sum()),
        f"{FACTOR_NAME}__nonpositive_close_rows": int(
            (finite_closes & ~positive_closes).sum()
        ),
        f"{FACTOR_NAME}__nonfinite_return_rows": int(
            (required_valid & ~finite_returns).sum()
        ),
        f"{FACTOR_NAME}__degenerate_lag_variance_rows": int(
            (required_valid & finite_returns & ~(lag_energy > 0.0)).sum()
        ),
        f"{FACTOR_NAME}__degenerate_lead_variance_rows": int(
            (required_valid & finite_returns & ~(lead_energy > 0.0)).sum()
        ),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int(
            (required_valid & finite_returns & canonicalized).sum()
        ),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (
                required_valid
                & finite_returns
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
    base_frame: pd.DataFrame,
    _unused_benchmark: Any,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Validate one source partition and compute magnitude persistence."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign028FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign028FeatureError(
            f"unexpected joint-base columns for {symbol}: "
            f"{tuple(base_frame.columns)}"
        )
    base_work = base_frame.copy()
    base_work["trade_date"] = pd.to_datetime(
        base_work["trade_date"], errors="coerce"
    ).dt.normalize()
    base_work["symbol"] = base_work["symbol"].astype(str).str.upper()
    if base_work.empty:
        return _generated["empty_output_frame"](), {"base_rows": 0}
    if (
        base_work["trade_date"].isna().any()
        or set(base_work["symbol"].unique()) != {symbol.upper()}
        or base_work.duplicated(["trade_date", "symbol"]).any()
    ):
        raise Campaign028FeatureError(f"joint-base identity changed for {symbol}")
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(
        drop=True
    )
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["close"] = pd.to_numeric(work["close"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign028FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign028FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(value) for value in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign028FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign028FeatureError(
            f"source and joint-base dates changed for {symbol}"
        )
    continuous = work.loc[
        work["minute_code"].isin(market.CONTINUOUS_MINUTE_CODES),
        ["trade_date", "minute_code", "close"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"],
        categories=market.CONTINUOUS_MINUTE_CODES,
        ordered=True,
    )
    continuous = continuous.sort_values(
        ["trade_date", "minute_code"], kind="stable"
    )
    if len(continuous) != len(base_work) * SELECTED_BAR_COUNT:
        raise Campaign028FeatureError(f"continuous minute grid changed for {symbol}")
    closes = continuous["close"].to_numpy(dtype=float).reshape(
        -1, SELECTED_BAR_COUNT
    )
    values, eligible, quality = compute_factor_values(closes=closes)
    return (
        pd.DataFrame(
            {
                "trade_date": base_work["trade_date"],
                "symbol": symbol.upper(),
                "provider": "tushare",
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
