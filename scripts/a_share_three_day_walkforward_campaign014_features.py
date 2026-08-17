#!/usr/bin/env python3
"""Build and audit the frozen Campaign014 global range-revisit factor.

Campaign013 supplies the already-tested checkpoint, snapshot, coverage, and
35-factor comparison orchestration.  This wrapper changes the campaign
namespace, replaces the factor calculation with the independently frozen
session-wide high-low interval union, and deliberately does not add sparse
Campaign013 values to the statistical comparison catalog.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

try:
    import scripts.a_share_three_day_walkforward_campaign013_features as campaign013
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign013_features as campaign013


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN013_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign013_features.py"
)
CAMPAIGN013_FEATURE_RUNNER_SHA256 = (
    "9b7020b61a03fae5a648cce4a48bf7828d8fd1dfe27ab22f69c771c3432a4054"
)
OLD_FACTOR = "intraday_transaction_vwap_envelope_asymmetry_240m"
FACTOR_NAME = "intraday_global_price_range_revisit_240m"
MECHANISM_AUDIT_SHA256 = (
    "2c5db4acd886d57649e7ac7cc0ce2232ae8efe957412d1fdc4804fcb7bb96890"
)

# Bind these in sequence after their immutable artifacts exist.
PROTOCOL_SHA256 = (
    "82e5cf3e26b6f2edc34e37651bf49026bb90d0409b97fd19bc853d71778cd16c"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "62469bb340ea9be6ee93321f4f81707c6753c30f4395ebcdd1db967efb360a67"
)
SNAPSHOT_DATASET_SHA256 = (
    "7bea5c1047c4c5fdde5043d5b102a337a0f28deb26bb17c94eff82b65cb317bf"
)
NO_RETURN_AUDIT_SHA256 = (
    "827fa9d5079ad86e9c25545fcbe680b2e26bc17edc1506dd1d3a7c883f44819f"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN013_FEATURE_RUNNER) != CAMPAIGN013_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign013 feature orchestration fingerprint changed")

_source = campaign013._source
for _old, _new in (
    ("Campaign013", "Campaign014"),
    ("campaign013", "campaign014"),
    ("campaign_013", "campaign_014"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "78262a1e90af0de4561329a21217ab5304925d7694877b9f84d61771fe77a715",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "0a5c0225cba49ab11056e232b6ba9875f65c2734d318ef7644031472a9d76764",
        PROTOCOL_SHA256,
    ),
    (
        "706e71aacb802a2b34cf7b52236823bb3e63cd30d3f0e8340456344c7ef184d7",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "45ee0352936be01714efba01fef80118bb9fe97ee3cdfcdba65f429bf01b528b",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "105ac63bc01828cf512be282377f835c87359a2356f29b7ff998734dcf4467b6",
        NO_RETURN_AUDIT_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_source = _source.replace(
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low", '
    '"volume", "amount")',
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")',
    1,
)
_old_formula = '''FACTOR_FORMULA = (
    "(sum(u_i) - sum(d_i)) / (sum(u_i) + sum(d_i)) over active "
    "09:31-11:30 and 13:01-15:00 bars, where vwap_i=amount_i/volume_i, "
    "u_i=log(high_i/vwap_i), and d_i=log(vwap_i/low_i)"
)'''
_new_formula = '''FACTOR_FORMULA = (
    "(S-U)/S, where S is the sum of all 240 log high-low interval "
    "lengths and U is the exact length of their merged session-wide "
    "union in log-price space"
)'''
if _old_formula not in _source:
    raise RuntimeError("Campaign013 formula block was not found")
_source = _source.replace(_old_formula, _new_formula, 1)
_source = _source.replace(
    "FACTOR_RANGES = {FACTOR_NAME: (-1.0, 1.0)}",
    "FACTOR_RANGES = {FACTOR_NAME: (0.0, 1.0)}",
    1,
)
_source = _source.replace(
    """SELECTED_BAR_COUNT = 240
MINIMUM_INFORMATIVE_ACTIVE_BARS = 120
ENDPOINT_TOLERANCE = 1e-12
IDENTITY_TOLERANCE = 1e-12""",
    """SELECTED_BAR_COUNT = 240
MINIMUM_POSITIVE_RANGE_BARS = 120
ENDPOINT_TOLERANCE = 1e-12
UNION_TOLERANCE = 1e-12""",
    1,
)

_new_loader = r'''def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate the protocol frozen before any Campaign014 value."""

    path = path.expanduser().resolve()
    if not PROTOCOL_SHA256:
        raise Campaign014FeatureError(
            "bind PROTOCOL_SHA256 before building or auditing Campaign014 values"
        )
    _require_file(path, PROTOCOL_SHA256, "Campaign014 no-return protocol")
    _require_file(
        MECHANISM_AUDIT,
        MECHANISM_AUDIT_SHA256,
        "Campaign014 mechanism-overlap audit",
    )
    spec = research.load_json_record(
        path,
        kind="a_share_three_day_walkforward_campaign014_no_return_preregistration",
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
    if not (
        spec.get("version") == 1
        and spec.get("status")
        == "frozen_before_campaign014_candidate_or_comparison_values_or_returns"
        and len(candidates) == 1
        and names == FACTOR_NAMES
        and formulas == FACTOR_FORMULAS
        and directions == FACTOR_DIRECTIONS
        and tuple(candidates[0].get("source_fields_allowed") or ())
        == RAW_COLUMNS
        and tuple(candidates[0].get("source_fields_used_by_formula") or ())
        == RAW_COLUMNS
        and candidates[0].get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidates[0].get("minimum_positive_range_bars")
        == MINIMUM_POSITIVE_RANGE_BARS
        and candidates[0].get("interval_union_algorithm")
        == "sort by log-low then log-high and merge touching or overlapping closed intervals"
        and mechanism.get("sha256") == MECHANISM_AUDIT_SHA256
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.90
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts")
        == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and uniqueness.get(
            "maximum_allowed_absolute_median_daily_rank_correlation"
        )
        == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and len(comparisons) == 35
        and str(comparisons[-1].get("name") or "")
        == "intraday_intrabar_range_reversal_238p"
        and uniqueness.get("campaign013_is_semantic_only_due_low_coverage")
        is True
        and boundary.get("minute_high_low_fields_read_before_admissibility")
        is True
        and boundary.get("minute_volume_amount_fields_read_before_admissibility")
        is False
        and boundary.get("minute_open_field_read_before_admissibility") is False
        and boundary.get("minute_close_field_read_before_admissibility") is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility")
        is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate50_prospective_activation_allowed") is False
        and boundary.get("current_scoring_selection_sizing_or_orders_allowed")
        is False
    ):
        raise Campaign014FeatureError(
            "Campaign014 no-return protocol semantics changed"
        )
    return spec


'''

_new_compute = r'''def compute_factor_values(
    *,
    highs: np.ndarray,
    lows: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the frozen session-wide log-price range revisit ratio."""

    if (
        highs.ndim != 2
        or highs.shape[1] != SELECTED_BAR_COUNT
        or lows.shape != highs.shape
    ):
        raise Campaign014FeatureError("Campaign014 aligned array shapes are invalid")
    finite_positive = (
        np.isfinite(highs).all(axis=1)
        & np.isfinite(lows).all(axis=1)
        & (highs > 0.0).all(axis=1)
        & (lows > 0.0).all(axis=1)
    )
    ordering = (lows <= highs).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        log_highs = np.log(highs)
        log_lows = np.log(lows)
        ranges = log_highs - log_lows
    ranges_finite_nonnegative = (
        np.isfinite(ranges).all(axis=1)
        & (ranges >= 0.0).all(axis=1)
    )
    positive_range_count = (highs > lows).sum(axis=1)
    gross_length = ranges.sum(axis=1)

    order = np.lexsort((log_highs, log_lows), axis=1)
    sorted_lows = np.take_along_axis(log_lows, order, axis=1)
    sorted_highs = np.take_along_axis(log_highs, order, axis=1)
    current_low = sorted_lows[:, 0].copy()
    current_high = sorted_highs[:, 0].copy()
    union_length = np.zeros(len(highs), dtype=float)
    for position in range(1, SELECTED_BAR_COUNT):
        next_low = sorted_lows[:, position]
        next_high = sorted_highs[:, position]
        connected = next_low <= current_high
        union_length += np.where(connected, 0.0, current_high - current_low)
        current_low = np.where(connected, current_low, next_low)
        current_high = np.where(
            connected,
            np.maximum(current_high, next_high),
            next_high,
        )
    union_length += current_high - current_low

    required_valid = finite_positive & ordering & ranges_finite_nonnegative
    sufficiently_observed = (
        required_valid
        & (positive_range_count >= MINIMUM_POSITIVE_RANGE_BARS)
    )
    gross_valid = (
        sufficiently_observed
        & np.isfinite(gross_length)
        & (gross_length > 0.0)
    )
    union_finite_positive = np.isfinite(union_length) & (union_length > 0.0)
    union_limit = UNION_TOLERANCE * np.maximum(1.0, np.abs(gross_length))
    union_not_greater = union_length <= gross_length + union_limit
    denominator_valid = gross_valid & union_finite_positive & union_not_greater
    with np.errstate(divide="ignore", invalid="ignore"):
        values = (gross_length - union_length) / gross_length
    negative_near_zero = (
        (values < 0.0) & (values >= -ENDPOINT_TOLERANCE)
    )
    canonicalized = negative_near_zero
    values = np.where(negative_near_zero, 0.0, values)
    finite = np.isfinite(values)
    in_range = (values >= 0.0) & (values < 1.0)
    eligible = denominator_valid & finite & in_range
    quality = {
        "base_rows": int(len(highs)),
        "invalid_required_high_low_rows": int((~finite_positive).sum()),
        f"{FACTOR_NAME}__low_high_ordering_violation_rows": int(
            (finite_positive & ~ordering).sum()
        ),
        f"{FACTOR_NAME}__nonfinite_or_negative_range_rows": int(
            (finite_positive & ordering & ~ranges_finite_nonnegative).sum()
        ),
        f"{FACTOR_NAME}__fewer_than_120_positive_range_bar_rows": int(
            (
                required_valid
                & (positive_range_count < MINIMUM_POSITIVE_RANGE_BARS)
            ).sum()
        ),
        f"{FACTOR_NAME}__nonpositive_or_nonfinite_gross_range_rows": int(
            (
                sufficiently_observed
                & (~np.isfinite(gross_length) | (gross_length <= 0.0))
            ).sum()
        ),
        f"{FACTOR_NAME}__nonpositive_or_nonfinite_union_length_rows": int(
            (gross_valid & ~union_finite_positive).sum()
        ),
        f"{FACTOR_NAME}__union_greater_than_gross_tolerance_rows": int(
            (gross_valid & union_finite_positive & ~union_not_greater).sum()
        ),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int(
            (canonicalized & eligible).sum()
        ),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (denominator_valid & (~finite | ~in_range)).sum()
        ),
    }
    return (
        {FACTOR_NAME: np.where(eligible, values, np.nan)},
        {FACTOR_NAME: eligible},
        quality,
    )


'''

_new_partition = r'''def compute_partition_frame(
    raw: pd.DataFrame,
    base_frame: pd.DataFrame,
    _unused_benchmark: Any,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Validate one source partition and compute the frozen range revisit."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign014FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign014FeatureError(
            f"unexpected joint-base columns for {symbol}: {tuple(base_frame.columns)}"
        )
    base_work = base_frame.copy()
    base_work["trade_date"] = pd.to_datetime(
        base_work["trade_date"], errors="coerce"
    ).dt.normalize()
    base_work["symbol"] = base_work["symbol"].astype(str).str.upper()
    if base_work.empty:
        return empty_output_frame(), {"base_rows": 0}
    if (
        base_work["trade_date"].isna().any()
        or set(base_work["symbol"].unique()) != {symbol.upper()}
        or base_work.duplicated(["trade_date", "symbol"]).any()
    ):
        raise Campaign014FeatureError(f"joint-base identity changed for {symbol}")
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(drop=True)
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    for field in ("high", "low"):
        work[field] = pd.to_numeric(work[field], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign014FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign014FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(v) for v in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign014FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign014FeatureError(
            f"source and joint-base dates changed for {symbol}"
        )
    fields = ["trade_date", "minute_code", "high", "low"]
    continuous = work.loc[
        work["minute_code"].isin(market.CONTINUOUS_MINUTE_CODES), fields
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
        raise Campaign014FeatureError(
            f"continuous minute grid changed for {symbol}"
        )
    arrays = {
        field: continuous[field].to_numpy(dtype=float).reshape(
            -1, SELECTED_BAR_COUNT
        )
        for field in ("high", "low")
    }
    values, eligible, quality = compute_factor_values(
        highs=arrays["high"],
        lows=arrays["low"],
    )
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

# Campaign014 reads only high/low and forbids open/close/volume/amount.
_old_volume_validation = '''        and manifest.get("source_volume_read") is True'''
if _old_volume_validation not in _source:
    raise RuntimeError("Campaign013 volume validation block was not found")
_source = _source.replace(
    _old_volume_validation,
    '''        and (
            manifest.get("source_volume_read") is False
            if require_fingerprint_constants
            else manifest.get("source_volume_read") is True
        )''',
    1,
)
_old_amount_validation = '''        and (
            manifest.get("source_amount_read") is True
            if require_fingerprint_constants
            else manifest.get("source_amount_read") in {None, True}
        )'''
if _old_amount_validation not in _source:
    raise RuntimeError("Campaign013 amount validation block was not found")
_source = _source.replace(
    _old_amount_validation,
    '''        and (
            manifest.get("source_amount_read") is False
            if require_fingerprint_constants
            else manifest.get("source_amount_read") in {None, False}
        )''',
    1,
)
_source = _source.replace(
    '''            value["source_volume_read"] = True
            value["source_close_read"] = False
            value["source_amount_read"] = True''',
    '''            value["source_volume_read"] = False
            value["source_close_read"] = False
            value["source_amount_read"] = False''',
    1,
)
_source = _source.replace(
    '''        "minute_open_high_low_read": True,
        "minute_open_read": False,
        "minute_close_read": False,
        "minute_volume_read": True,
        "minute_amount_read": True,''',
    '''        "minute_open_high_low_read": True,
        "minute_open_read": False,
        "minute_close_read": False,
        "minute_volume_read": False,
        "minute_amount_read": False,''',
    1,
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign014_features_generated",
    "C9_SNAPSHOT_PATH": campaign013.campaign012.campaign011.campaign010.C9_SNAPSHOT_PATH,
    "C9_SNAPSHOT_SHA256": campaign013.campaign012.campaign011.campaign010.C9_SNAPSHOT_SHA256,
    "C9_DATASET_SHA256": campaign013.campaign012.campaign011.campaign010.C9_DATASET_SHA256,
    "C9_FACTOR_NAMES": campaign013.campaign012.campaign011.campaign010.C9_FACTOR_NAMES,
    "C9_OUTPUT_COLUMNS": campaign013.campaign012.campaign011.campaign010.C9_OUTPUT_COLUMNS,
    "C10_SNAPSHOT_PATH": campaign013.campaign012.campaign011.C10_SNAPSHOT_PATH,
    "C10_SNAPSHOT_SHA256": campaign013.campaign012.campaign011.C10_SNAPSHOT_SHA256,
    "C10_DATASET_SHA256": campaign013.campaign012.campaign011.C10_DATASET_SHA256,
    "C10_FACTOR_NAMES": campaign013.campaign012.campaign011.C10_FACTOR_NAMES,
    "C10_OUTPUT_COLUMNS": campaign013.campaign012.campaign011.C10_OUTPUT_COLUMNS,
    "C11_SNAPSHOT_PATH": campaign013.campaign012.C11_SNAPSHOT_PATH,
    "C11_SNAPSHOT_SHA256": campaign013.campaign012.C11_SNAPSHOT_SHA256,
    "C11_DATASET_SHA256": campaign013.campaign012.C11_DATASET_SHA256,
    "C11_FACTOR_NAMES": campaign013.campaign012.C11_FACTOR_NAMES,
    "C11_OUTPUT_COLUMNS": campaign013.campaign012.C11_OUTPUT_COLUMNS,
    "C12_SNAPSHOT_PATH": campaign013.C12_SNAPSHOT_PATH,
    "C12_SNAPSHOT_SHA256": campaign013.C12_SNAPSHOT_SHA256,
    "C12_DATASET_SHA256": campaign013.C12_DATASET_SHA256,
    "C12_FACTOR_NAMES": campaign013.C12_FACTOR_NAMES,
    "C12_OUTPUT_COLUMNS": campaign013.C12_OUTPUT_COLUMNS,
}
exec(compile(_source, str(CAMPAIGN013_FEATURE_RUNNER), "exec"), _generated)

Campaign014FeatureError = _generated["Campaign014FeatureError"]
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
    "FACTOR_NAME",
    "FACTOR_NAMES",
    "FACTOR_DIRECTIONS",
    "FACTOR_RANGES",
    "FACTOR_FORMULA",
    "FACTOR_FORMULAS",
    "OUTPUT_COLUMNS",
    "SELECTED_BAR_COUNT",
    "MINIMUM_POSITIVE_RANGE_BARS",
    "ENDPOINT_TOLERANCE",
    "UNION_TOLERANCE",
    "market",
):
    globals()[_export_name] = _generated[_export_name]


if __name__ == "__main__":
    raise SystemExit(main())
