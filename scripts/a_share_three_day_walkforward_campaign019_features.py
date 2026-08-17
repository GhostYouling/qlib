#!/usr/bin/env python3
"""Build and audit the frozen Campaign019 bar-direction continuity factor.

Campaign018 supplies the tested checkpoint, snapshot, coverage, and first
39-factor comparison orchestration. This wrapper changes only the campaign
namespace and candidate formula, projects open/close, and appends the terminal
Campaign018 factor as comparison 40.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

try:
    import scripts.a_share_three_day_walkforward_campaign018_features as campaign018
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign018_features as campaign018


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN018_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign018_features.py"
)
CAMPAIGN018_FEATURE_RUNNER_SHA256 = (
    "f14ba9878bfe7c15f05dad05655610c5c131fa4d8c2abb6ed26c4833c271a332"
)
OLD_FACTOR = "intraday_range_share_volume_confirmation_240m"
FACTOR_NAME = "intraday_bar_direction_continuity_238p"
MECHANISM_AUDIT_SHA256 = (
    "29e7dc24776e458cd471414a076029dfb232fb5299f10fd333b6f9c4e7522606"
)
PROTOCOL_SHA256 = (
    "de68ec246a0b0944ef75edc2594e8909c89b9118de3cd01bdad7cc1b902f011f"
)

# Bind these immutable fingerprints only after the corresponding artifacts exist.
SNAPSHOT_MANIFEST_SHA256 = (
    "7c4f7268f33af3274a9057241b9bd45df3c2565729a684a07f48105cdf9474cb"
)
SNAPSHOT_DATASET_SHA256 = (
    "66efe683268dbcc681591ee9918ba2948f3c4420232c4e1f4c57371d0ac24ecc"
)
NO_RETURN_AUDIT_SHA256 = (
    "ccb7c4582a4944fe6c26423d07d25cefc488f3200fb70e45ec738ea8c716f10e"
)

C18_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign018_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign018_feature_library_v1/snapshot_manifest.json"
)
C18_SNAPSHOT_SHA256 = (
    "9fe343dc34d57e59c3a5d12fb3d159b10e9d98cdd02cf1ce8c82b77fbbdb37a0"
)
C18_DATASET_SHA256 = (
    "7762728e0a7d94dcddb1bcfb21531d4b66f98620a0282ffe501767c7e4f607be"
)
C18_FACTOR_NAMES = ("intraday_range_share_volume_confirmation_240m",)
C18_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C18_FACTOR_NAMES[0],
    f"{C18_FACTOR_NAMES[0]}_eligible",
)
MINIMUM_INFORMATIVE_PAIR_COUNT = 120


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN018_FEATURE_RUNNER) != CAMPAIGN018_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign018 feature orchestration fingerprint changed")

_source = campaign018._source
for _old, _new in (
    ("Campaign018", "Campaign019"),
    ("campaign018", "campaign019"),
    ("campaign_018", "campaign_019"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "20cab7f44607e53c9af0a3bf95eee96a13711c3e72b051038d1b0bcccbf044e5",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "5cc74329648ce47787291d2f4b5c960084ca1a0fc148284170e1a23d429c1fe6",
        PROTOCOL_SHA256,
    ),
    (
        "9fe343dc34d57e59c3a5d12fb3d159b10e9d98cdd02cf1ce8c82b77fbbdb37a0",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "7762728e0a7d94dcddb1bcfb21531d4b66f98620a0282ffe501767c7e4f607be",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "16e8c23e8a4cac9d7e0e70649cf9f1b01e809b61459c7dbbc71b55870a4f58ff",
        NO_RETURN_AUDIT_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_source = _source.replace(
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low", "volume")',
    'RAW_COLUMNS = ("datetime", "symbol", "provider", "open", "close")',
    1,
)
_source = _source.replace(
    "FACTOR_RANGES = {FACTOR_NAME: (-1.0, 1.0)}",
    "FACTOR_RANGES = {FACTOR_NAME: (0.0, 1.0)}",
    1,
)
_old_formula = '''FACTOR_FORMULA = (
    "population Pearson correlation "
    "Corr(log(high_i/low_i),log1p(volume_i)) across exactly 240 "
    "continuous-session bars"
)'''
_new_formula = '''FACTOR_FORMULA = (
    "count(s_i*s_(i+1)>0) / count(s_i!=0 and s_(i+1)!=0) across "
    "exactly 238 within-half adjacent pairs, where "
    "s_i=sign(log(close_i/open_i))"
)'''
if _old_formula not in _source:
    raise RuntimeError("Campaign018 formula block was not found")
_source = _source.replace(_old_formula, _new_formula, 1)
if "ENDPOINT_TOLERANCE = 1e-12" not in _source:
    raise RuntimeError("Campaign018 endpoint constant was not found")
_source = _source.replace("ENDPOINT_TOLERANCE = 1e-12", "ENDPOINT_TOLERANCE = None", 1)

_new_loader = r'''def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate the protocol frozen before any Campaign019 value."""

    path = path.expanduser().resolve()
    if not PROTOCOL_SHA256:
        raise Campaign019FeatureError(
            "bind PROTOCOL_SHA256 before building or auditing Campaign019 values"
        )
    _require_file(path, PROTOCOL_SHA256, "Campaign019 no-return protocol")
    _require_file(
        MECHANISM_AUDIT,
        MECHANISM_AUDIT_SHA256,
        "Campaign019 mechanism-overlap audit",
    )
    spec = research.load_json_record(
        path,
        kind="a_share_three_day_walkforward_campaign019_no_return_preregistration",
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
        == "frozen_before_campaign019_candidate_or_comparison_values_or_returns"
        and len(candidates) == 1
        and names == FACTOR_NAMES
        and formulas == FACTOR_FORMULAS
        and directions == FACTOR_DIRECTIONS
        and tuple(candidates[0].get("source_fields_allowed") or ())
        == RAW_COLUMNS
        and tuple(candidates[0].get("source_fields_used_by_formula") or ())
        == RAW_COLUMNS
        and tuple(candidates[0].get("source_fields_used_only_for_validation") or ())
        == ()
        and candidates[0].get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidates[0].get("within_half_pair_count") == WITHIN_HALF_PAIR_COUNT
        and candidates[0].get("minimum_nonzero_pair_count")
        == MINIMUM_INFORMATIVE_PAIR_COUNT
        and candidates[0].get("endpoint_canonicalization_tolerance")
        == ENDPOINT_TOLERANCE
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
        and len(comparisons) == 40
        and str(comparisons[-1].get("name") or "")
        == C18_FACTOR_NAMES[0]
        and uniqueness.get("campaign013_is_semantic_only_due_low_coverage")
        is True
        and boundary.get(
            "minute_open_close_fields_read_before_admissibility"
        )
        is True
        and boundary.get(
            "minute_high_low_volume_amount_fields_read_before_admissibility"
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
        raise Campaign019FeatureError(
            "Campaign019 no-return protocol semantics changed"
        )
    return spec


'''

_new_compute = r'''def compute_factor_values(
    *,
    opens: np.ndarray,
    closes: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the frozen within-bar direction-continuity fraction."""

    if (
        opens.ndim != 2
        or opens.shape[1] != SELECTED_BAR_COUNT
        or closes.shape != opens.shape
    ):
        raise Campaign019FeatureError("Campaign019 aligned array shapes are invalid")
    finite = np.isfinite(opens).all(axis=1) & np.isfinite(closes).all(axis=1)
    positive = (opens > 0.0).all(axis=1) & (closes > 0.0).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        bodies = np.log(closes) - np.log(opens)
    components_finite = np.isfinite(bodies).all(axis=1)
    signs = np.sign(bodies)
    left_positions = np.concatenate(
        (
            np.arange(0, 119, dtype=np.int64),
            np.arange(120, 239, dtype=np.int64),
        )
    )
    right_positions = left_positions + 1
    left = signs[:, left_positions]
    right = signs[:, right_positions]
    informative = (left != 0.0) & (right != 0.0)
    informative_count = informative.sum(axis=1)
    same_direction_count = (informative & (left == right)).sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        raw_values = same_direction_count / informative_count

    required_valid = finite & positive & components_finite
    support_valid = (
        required_valid
        & (informative_count >= MINIMUM_INFORMATIVE_PAIR_COUNT)
        & (informative_count > 0)
    )
    value_finite = np.isfinite(raw_values)
    in_range = (raw_values >= 0.0) & (raw_values <= 1.0)
    eligible = support_valid & value_finite & in_range
    zero_body_observations = signs == 0.0
    quality = {
        "base_rows": int(len(opens)),
        "invalid_required_open_close_rows": int((~finite).sum()),
        f"{FACTOR_NAME}__nonpositive_open_close_rows": int(
            (finite & ~positive).sum()
        ),
        f"{FACTOR_NAME}__nonfinite_log_body_rows": int(
            (finite & positive & ~components_finite).sum()
        ),
        f"{FACTOR_NAME}__zero_body_observations": int(
            zero_body_observations.sum()
        ),
        f"{FACTOR_NAME}__rows_with_zero_body": int(
            zero_body_observations.any(axis=1).sum()
        ),
        f"{FACTOR_NAME}__insufficient_informative_pair_rows": int(
            (required_valid & (informative_count < MINIMUM_INFORMATIVE_PAIR_COUNT)).sum()
        ),
        f"{FACTOR_NAME}__zero_denominator_rows": int(
            (required_valid & (informative_count == 0)).sum()
        ),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (support_valid & (~value_finite | ~in_range)).sum()
        ),
    }
    return (
        {FACTOR_NAME: np.where(eligible, raw_values, np.nan)},
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
    """Validate one source partition and compute bar-direction continuity."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign019FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign019FeatureError(
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
        raise Campaign019FeatureError(f"joint-base identity changed for {symbol}")
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(drop=True)
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    for field in ("open", "close"):
        work[field] = pd.to_numeric(work[field], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign019FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign019FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(v) for v in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign019FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign019FeatureError(
            f"source and joint-base dates changed for {symbol}"
        )
    fields = ["trade_date", "minute_code", "open", "close"]
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
        raise Campaign019FeatureError(
            f"continuous minute grid changed for {symbol}"
        )
    arrays = {
        field: continuous[field].to_numpy(dtype=float).reshape(
            -1, SELECTED_BAR_COUNT
        )
        for field in ("open", "close")
    }
    values, eligible, quality = compute_factor_values(
        opens=arrays["open"],
        closes=arrays["close"],
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

# Campaign019 reads open/close and forbids high/low/volume/amount. The reused
# Campaign018 builder presents its inherited temporary manifest with the old
# volume flag until the atomic-write adapter emits the Campaign019 manifest.
_source = _source.replace(
    '''        "minute_open_high_low_read": True,
        "minute_open_read": False,
        "minute_close_read": False,
        "minute_volume_read": True,
        "minute_amount_read": False,''',
    '''        "minute_open_high_low_read": True,
        "minute_open_read": True,
        "minute_close_read": True,
        "minute_volume_read": False,
        "minute_amount_read": False,''',
    1,
)
_source = _source.replace(
    '''        "minute_open_high_low_read_by_status": True,
        "minute_open_read_by_status": False,
        "minute_close_read_by_status": False,
        "minute_volume_read_by_status": True,''',
    '''        "minute_open_high_low_read_by_status": True,
        "minute_open_read_by_status": True,
        "minute_close_read_by_status": True,
        "minute_volume_read_by_status": False,''',
    1,
)
_source = _source.replace(
    '''        and manifest.get("source_volume_read") is True''',
    '''        and (
            manifest.get("source_volume_read") is False
            if require_fingerprint_constants
            else manifest.get("source_volume_read") is True
        )''',
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
            else manifest.get("source_close_read") in {None, False}
        )''',
    1,
)
_source = _source.replace(
    'value["source_volume_read"] = True',
    'value["source_volume_read"] = False',
    1,
)
_source = _source.replace(
    'value["source_close_read"] = False',
    'value["source_close_read"] = True',
    1,
)

_verify_c17 = '''        c17_manifest, c17_verification = executor._verify_prior_snapshot(
            path=C17_SNAPSHOT_PATH,
            manifest_sha256=C17_SNAPSHOT_SHA256,
            dataset_sha256=C17_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign017_feature_snapshot",
            factor_names=C17_FACTOR_NAMES,
            output_columns=C17_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
_verify_c18 = _verify_c17 + '''        c18_manifest, c18_verification = executor._verify_prior_snapshot(
            path=C18_SNAPSHOT_PATH,
            manifest_sha256=C18_SNAPSHOT_SHA256,
            dataset_sha256=C18_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign018_feature_snapshot",
            factor_names=C18_FACTOR_NAMES,
            output_columns=C18_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
if _verify_c17 not in _source:
    raise RuntimeError("Campaign018 prior-snapshot verification block was not found")
_source = _source.replace(_verify_c17, _verify_c18, 1)

_compare_c17 = '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c17_manifest,
                factors=C17_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
_compare_c18 = _compare_c17 + '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c18_manifest,
                factors=C18_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
if _compare_c17 not in _source:
    raise RuntimeError("Campaign018 comparison extension block was not found")
_source = _source.replace(_compare_c17, _compare_c18, 1)
_source = _source.replace(
    "Apply coverage before all 39 frozen uniqueness comparisons.",
    "Apply coverage before all 40 frozen uniqueness comparisons.",
    1,
)
_source = _source.replace("len(comparisons) == 39", "len(comparisons) == 40", 1)
_source = _source.replace(
    '''            "campaign017_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    '''            "campaign017_terminal_comparison_count": 1,
            "campaign018_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    1,
)
_source = _source.replace(
    '''            "campaign017_snapshot_file_verification": c17_verification,
            "comparisons": comparisons,''',
    '''            "campaign017_snapshot_file_verification": c17_verification,
            "campaign018_snapshot_file_verification": c18_verification,
            "comparisons": comparisons,''',
    1,
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign019_features_generated",
    "MINIMUM_INFORMATIVE_PAIR_COUNT": MINIMUM_INFORMATIVE_PAIR_COUNT,
}
for _campaign in (9, 10, 11, 12, 14, 15, 16, 17):
    for _suffix in (
        "SNAPSHOT_PATH",
        "SNAPSHOT_SHA256",
        "DATASET_SHA256",
        "FACTOR_NAMES",
        "OUTPUT_COLUMNS",
    ):
        _key = f"C{_campaign}_{_suffix}"
        _generated[_key] = campaign018.engine_namespace[_key]
_generated.update(
    {
        "C18_SNAPSHOT_PATH": C18_SNAPSHOT_PATH,
        "C18_SNAPSHOT_SHA256": C18_SNAPSHOT_SHA256,
        "C18_DATASET_SHA256": C18_DATASET_SHA256,
        "C18_FACTOR_NAMES": C18_FACTOR_NAMES,
        "C18_OUTPUT_COLUMNS": C18_OUTPUT_COLUMNS,
    }
)
exec(compile(_source, str(CAMPAIGN018_FEATURE_RUNNER), "exec"), _generated)

Campaign019FeatureError = _generated["Campaign019FeatureError"]
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
    "WITHIN_HALF_PAIR_COUNT",
    "ENDPOINT_TOLERANCE",
    "market",
):
    globals()[_export_name] = _generated[_export_name]


if __name__ == "__main__":
    raise SystemExit(main())
