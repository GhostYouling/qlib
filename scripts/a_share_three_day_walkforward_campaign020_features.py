#!/usr/bin/env python3
"""Build and audit the frozen Campaign020 disclosure-freshness factor.

Campaign019 supplies the tested checkpoint, snapshot, coverage, and first
40-factor comparison orchestration. This wrapper changes only the campaign
namespace and candidate formula, projects stock-day identity without price or
activity fields, binds the frozen quarterly disclosure source, and appends the
terminal Campaign019 factor as comparison 41.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

try:
    import scripts.a_share_three_day_walkforward_campaign019_features as campaign019
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign019_features as campaign019


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN019_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign019_features.py"
)
CAMPAIGN019_FEATURE_RUNNER_SHA256 = (
    "79c39072bc2515541acdaffdb3c3f43a5fabb1e4e8d13ba0e47c8ee4e6477a48"
)
OLD_FACTOR = "intraday_bar_direction_continuity_238p"
FACTOR_NAME = "quarterly_announcement_freshness_60s"
MECHANISM_AUDIT_SHA256 = (
    "e61185b024e9d2a1a0f7d34769819c1c7a274d30f8f8ce235727daa626e606ad"
)
PROTOCOL_SHA256 = (
    "cbd04a23d73c1535886a063cdf26bacc4d86b2ebec16bc0e8724efc82b4bc1e6"
)

# Bind these immutable fingerprints only after the corresponding artifacts exist.
SNAPSHOT_MANIFEST_SHA256 = (
    "a776c1bcfb3d573ea7583be843ee42b1b6a368ccc8d80dbd382bf56fa2115fdd"
)
SNAPSHOT_DATASET_SHA256 = (
    "39cda0c04c87c94886ac9f0f99453a2db627fa5cd64096ba33ef92df91223faa"
)
NO_RETURN_AUDIT_SHA256 = (
    "08752d1a28411d52fe59d574951065ba14b0eb729620c6c8a75b63efceb72794"
)

DISCLOSURE_PATH = (
    REPO_ROOT / "data" / "raw" / "a_share" / "fundamentals"
    / "quarterly_quality.parquet"
)
DISCLOSURE_SHA256 = (
    "3ac901a97928d2ed81ac72e3eaac9bdc148d36cf67b6abe70223699235ef059f"
)
DISCLOSURE_MANIFEST_PATH = (
    REPO_ROOT / "data" / "metadata" / "quarterly_quality_manifest.json"
)
DISCLOSURE_MANIFEST_SHA256 = (
    "e3cf654babe37a82393c5530696bc1cc242b736cb88e1947b8444b638125ba8c"
)
CALENDAR_PATH = REPO_ROOT / "data" / "qlib" / "cn_a_share" / "calendars" / "day.txt"
CALENDAR_SHA256 = (
    "fda506597d26bcec953cdc0882042a5046ec1587db60490e16a01627fd43f53a"
)
EVENT_FIELDS = ("instrument", "report_date", "announcement_date")
FORBIDDEN_EVENT_VALUE_FIELDS = ("roe", "net_profit", "revenue_yoy", "profit_yoy")
DECAY_SCALE_SESSIONS = 60

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
    ("Campaign019", "Campaign020"),
    ("campaign019", "campaign020"),
    ("campaign_019", "campaign_020"),
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
    'RAW_COLUMNS = ("datetime", "symbol", "provider")',
    1,
)
_source = _source.replace(
    "FACTOR_RANGES = {FACTOR_NAME: (0.0, 1.0)}",
    "FACTOR_RANGES = {FACTOR_NAME: (0.0, 1.0)}",
    1,
)
_old_formula = '''FACTOR_FORMULA = (
    "count(s_i*s_(i+1)>0) / count(s_i!=0 and s_(i+1)!=0) across "
    "exactly 238 within-half adjacent pairs, where "
    "s_i=sign(log(close_i/open_i))"
)'''
_new_formula = '''FACTOR_FORMULA = (
    "2 ** (-age_sessions / 60), where age_sessions is the nonnegative "
    "accepted-session distance from the latest effective quarterly "
    "disclosure session to signal session t"
)'''
if _old_formula not in _source:
    raise RuntimeError("Campaign019 formula block was not found")
_source = _source.replace(_old_formula, _new_formula, 1)

_new_loader = r'''def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate the protocol frozen before any Campaign020 value."""

    path = path.expanduser().resolve()
    if not PROTOCOL_SHA256:
        raise Campaign020FeatureError(
            "bind PROTOCOL_SHA256 before building or auditing Campaign020 values"
        )
    _require_file(path, PROTOCOL_SHA256, "Campaign020 no-return protocol")
    _require_file(
        MECHANISM_AUDIT,
        MECHANISM_AUDIT_SHA256,
        "Campaign020 mechanism-overlap audit",
    )
    _require_file(DISCLOSURE_PATH, DISCLOSURE_SHA256, "quarterly disclosure source")
    _require_file(
        DISCLOSURE_MANIFEST_PATH,
        DISCLOSURE_MANIFEST_SHA256,
        "quarterly disclosure manifest",
    )
    _require_file(CALENDAR_PATH, CALENDAR_SHA256, "accepted local calendar")
    spec = research.load_json_record(
        path,
        kind="a_share_three_day_walkforward_campaign020_no_return_preregistration",
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
    source = (spec.get("source_chain") or {}).get("quarterly_disclosure_source") or {}
    mechanism = (spec.get("source_chain") or {}).get("mechanism_overlap_audit") or {}
    candidate = candidates[0] if len(candidates) == 1 else {}
    if not (
        spec.get("version") == 1
        and spec.get("status")
        == "frozen_before_campaign020_candidate_or_comparison_values_or_returns"
        and len(candidates) == 1
        and names == FACTOR_NAMES
        and formulas == FACTOR_FORMULAS
        and directions == FACTOR_DIRECTIONS
        and tuple(candidate.get("stock_day_identity_fields") or ()) == RAW_COLUMNS
        and tuple(candidate.get("event_fields_allowed") or ()) == EVENT_FIELDS
        and tuple(candidate.get("event_fields_used_by_formula") or ()) == EVENT_FIELDS
        and tuple(candidate.get("event_value_fields_forbidden") or ())
        == FORBIDDEN_EVENT_VALUE_FIELDS
        and candidate.get("decay_scale_sessions") == DECAY_SCALE_SESSIONS
        and candidate.get("endpoint_canonicalization_tolerance") is None
        and candidate.get("valid_range") == [0.0, 1.0]
        and candidate.get("valid_range_lower_inclusive") is False
        and candidate.get("valid_range_upper_inclusive") is True
        and mechanism.get("sha256") == MECHANISM_AUDIT_SHA256
        and source.get("sha256") == DISCLOSURE_SHA256
        and source.get("manifest_sha256") == DISCLOSURE_MANIFEST_SHA256
        and tuple(source.get("projected_columns") or ()) == EVENT_FIELDS
        and tuple(source.get("forbidden_value_columns") or ())
        == FORBIDDEN_EVENT_VALUE_FIELDS
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
        and len(comparisons) == 41
        and str(comparisons[-1].get("name") or "") == C19_FACTOR_NAMES[0]
        and uniqueness.get("campaign013_is_semantic_only_due_low_coverage") is True
        and boundary.get(
            "stock_day_datetime_symbol_provider_identity_read_before_admissibility"
        )
        is True
        and boundary.get(
            "quarterly_instrument_report_announcement_fields_read_before_admissibility"
        )
        is True
        and boundary.get(
            "quarterly_value_fields_read_by_candidate_before_admissibility"
        )
        is False
        and boundary.get(
            "minute_price_volume_amount_fields_read_before_admissibility"
        )
        is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate50_prospective_activation_allowed") is False
        and boundary.get("current_scoring_selection_sizing_or_orders_allowed")
        is False
    ):
        raise Campaign020FeatureError(
            "Campaign020 no-return protocol semantics changed"
        )
    return spec


'''

_new_compute = r'''def compute_factor_values(
    *,
    trade_positions: np.ndarray,
    effective_event_positions: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the frozen accepted-session disclosure-freshness decay."""

    trade_positions = np.asarray(trade_positions, dtype=np.int64)
    effective_event_positions = np.asarray(
        effective_event_positions, dtype=np.int64
    )
    if (
        trade_positions.ndim != 1
        or effective_event_positions.shape != trade_positions.shape
    ):
        raise Campaign020FeatureError("Campaign020 position arrays are invalid")
    has_event = effective_event_positions >= 0
    age_sessions = trade_positions - effective_event_positions
    nonnegative_age = age_sessions >= 0
    with np.errstate(over="ignore", invalid="ignore"):
        values = np.exp2(-age_sessions.astype(float) / DECAY_SCALE_SESSIONS)
    finite = np.isfinite(values)
    in_range = (values > 0.0) & (values <= 1.0)
    eligible = has_event & nonnegative_age & finite & in_range
    quality = {
        "base_rows": int(len(trade_positions)),
        f"{FACTOR_NAME}__no_prior_effective_disclosure_rows": int(
            (~has_event).sum()
        ),
        f"{FACTOR_NAME}__negative_session_age_rows": int(
            (has_event & ~nonnegative_age).sum()
        ),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (has_event & nonnegative_age & (~finite | ~in_range)).sum()
        ),
    }
    return (
        {FACTOR_NAME: np.where(eligible, values, np.nan)},
        {FACTOR_NAME: eligible},
        quality,
    )


'''

_new_partition = r'''_DISCLOSURE_EVENT_CACHE: Any = None


def _load_disclosure_events() -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Load only frozen disclosure identity/timing columns once per process."""

    global _DISCLOSURE_EVENT_CACHE
    if _DISCLOSURE_EVENT_CACHE is not None:
        return _DISCLOSURE_EVENT_CACHE
    _require_file(DISCLOSURE_PATH, DISCLOSURE_SHA256, "quarterly disclosure source")
    _require_file(
        DISCLOSURE_MANIFEST_PATH,
        DISCLOSURE_MANIFEST_SHA256,
        "quarterly disclosure manifest",
    )
    _require_file(CALENDAR_PATH, CALENDAR_SHA256, "accepted local calendar")
    calendar = pd.to_datetime(
        CALENDAR_PATH.read_text(encoding="utf-8").splitlines(),
        errors="coerce",
    )
    if pd.isna(calendar).any():
        raise Campaign020FeatureError("accepted calendar contains invalid dates")
    calendar = pd.DatetimeIndex(calendar).normalize().unique().sort_values()
    calendar_values = calendar.to_numpy(dtype="datetime64[ns]")
    events = pd.read_parquet(
        DISCLOSURE_PATH,
        columns=list(EVENT_FIELDS),
        filters=[("announcement_date", "<", pd.Timestamp("2026-01-01"))],
    )
    if tuple(events.columns) != EVENT_FIELDS:
        raise Campaign020FeatureError("quarterly disclosure projection changed")
    events["instrument"] = events["instrument"].astype(str).str.upper()
    events["report_date"] = pd.to_datetime(
        events["report_date"], errors="coerce"
    ).dt.normalize()
    events["announcement_date"] = pd.to_datetime(
        events["announcement_date"], errors="coerce"
    ).dt.normalize()
    if (
        events.empty
        or events.isna().any().any()
        or events.duplicated(["instrument", "report_date"]).any()
    ):
        raise Campaign020FeatureError("quarterly disclosure identities changed")
    announcement_values = events["announcement_date"].to_numpy(
        dtype="datetime64[ns]"
    )
    effective_positions = np.searchsorted(
        calendar_values,
        announcement_values,
        side="right",
    )
    in_range = effective_positions < len(calendar_values)
    events = events.loc[in_range].copy()
    events["effective_position"] = effective_positions[in_range]
    events = (
        events.sort_values(
            [
                "instrument",
                "effective_position",
                "report_date",
                "announcement_date",
            ],
            kind="stable",
        )
        .drop_duplicates(["instrument", "effective_position"], keep="last")
        .reset_index(drop=True)
    )
    by_symbol = {
        str(symbol): group["effective_position"].to_numpy(dtype=np.int64)
        for symbol, group in events.groupby("instrument", sort=False)
    }
    _DISCLOSURE_EVENT_CACHE = (calendar_values, by_symbol)
    return _DISCLOSURE_EVENT_CACHE


def compute_partition_frame(
    raw: pd.DataFrame,
    base_frame: pd.DataFrame,
    _unused_benchmark: Any,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Validate one stock-year key grid and compute disclosure freshness."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign020FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign020FeatureError(
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
        raise Campaign020FeatureError(f"joint-base identity changed for {symbol}")
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(drop=True)
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign020FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign020FeatureError(
            f"every source stock-day must retain 241 identity rows for {symbol}"
        )
    source_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(v) for v in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign020FeatureError(f"source minute identity grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign020FeatureError(
            f"source and joint-base dates changed for {symbol}"
        )

    calendar_values, events_by_symbol = _load_disclosure_events()
    trade_values = base_work["trade_date"].to_numpy(dtype="datetime64[ns]")
    trade_positions = np.searchsorted(calendar_values, trade_values, side="left")
    bounded = trade_positions < len(calendar_values)
    if (
        not bounded.all()
        or not np.array_equal(calendar_values[trade_positions], trade_values)
    ):
        raise Campaign020FeatureError(
            f"base dates are outside the accepted calendar for {symbol}"
        )
    event_positions = events_by_symbol.get(symbol.upper())
    latest_effective = np.full(len(trade_positions), -1, dtype=np.int64)
    if event_positions is not None and len(event_positions):
        selected = np.searchsorted(event_positions, trade_positions, side="right") - 1
        has_event = selected >= 0
        latest_effective[has_event] = event_positions[selected[has_event]]
    values, eligible, quality = compute_factor_values(
        trade_positions=trade_positions,
        effective_event_positions=latest_effective,
    )
    return (
        pd.DataFrame(
            {
                "trade_date": base_work["trade_date"],
                "symbol": symbol.upper(),
                "provider": "eastmoney_disclosure_timing",
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

# The inherited temporary manifest reflects Campaign018's source flags until
# the Campaign020 atomic adapter publishes the event-timing contract.
_source = _source.replace(
    '''        "minute_open_high_low_read": True,
        "minute_open_read": True,
        "minute_close_read": True,
        "minute_volume_read": False,
        "minute_amount_read": False,''',
    '''        "stock_day_datetime_symbol_provider_identity_read": True,
        "quarterly_instrument_report_announcement_fields_read": True,
        "quarterly_value_fields_read": False,
        "minute_open_high_low_read": False,
        "minute_open_read": False,
        "minute_close_read": False,
        "minute_volume_read": False,
        "minute_amount_read": False,''',
    1,
)
_source = _source.replace(
    '''        "minute_open_high_low_read_by_status": True,
        "minute_open_read_by_status": True,
        "minute_close_read_by_status": True,
        "minute_volume_read_by_status": False,''',
    '''        "stock_day_datetime_symbol_provider_identity_read_by_status": True,
        "quarterly_instrument_report_announcement_fields_read_by_status": True,
        "quarterly_value_fields_read_by_status": False,
        "minute_open_high_low_read_by_status": False,
        "minute_open_read_by_status": False,
        "minute_close_read_by_status": False,
        "minute_volume_read_by_status": False,''',
    1,
)
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
            manifest.get("source_close_read") is True
            if require_fingerprint_constants
            else manifest.get("source_close_read") in {None, False}
        )''',
    '''        and (
            manifest.get("source_close_read") is False
            if require_fingerprint_constants
            else manifest.get("source_close_read") in {None, False}
        )''',
    1,
)
_source = _source.replace(
    '''        and manifest.get("daily_price_fields_read") == []''',
    '''        and manifest.get("daily_price_fields_read") == []
        and (
            manifest.get("quarterly_disclosure_source_sha256")
            == DISCLOSURE_SHA256
            if require_fingerprint_constants
            else manifest.get("quarterly_disclosure_source_sha256") is None
        )
        and (
            manifest.get("quarterly_disclosure_manifest_sha256")
            == DISCLOSURE_MANIFEST_SHA256
            if require_fingerprint_constants
            else manifest.get("quarterly_disclosure_manifest_sha256") is None
        )
        and (
            tuple(manifest.get("quarterly_disclosure_fields_read") or ())
            == EVENT_FIELDS
            if require_fingerprint_constants
            else manifest.get("quarterly_disclosure_fields_read") is None
        )
        and (
            manifest.get("quarterly_value_fields_read") == []
            if require_fingerprint_constants
            else manifest.get("quarterly_value_fields_read") is None
        )''',
    1,
)
_source = _source.replace(
    'value["source_open_high_low_read"] = True',
    'value["source_open_high_low_read"] = False',
    1,
)
_source = _source.replace(
    'value["source_close_read"] = True',
    'value["source_close_read"] = False',
    1,
)
_source = _source.replace(
    '''            value["source_amount_read"] = False''',
    '''            value["source_amount_read"] = False
            value["quarterly_disclosure_source_path"] = str(
                DISCLOSURE_PATH.resolve()
            )
            value["quarterly_disclosure_source_sha256"] = DISCLOSURE_SHA256
            value["quarterly_disclosure_manifest_path"] = str(
                DISCLOSURE_MANIFEST_PATH.resolve()
            )
            value["quarterly_disclosure_manifest_sha256"] = (
                DISCLOSURE_MANIFEST_SHA256
            )
            value["quarterly_disclosure_fields_read"] = list(EVENT_FIELDS)
            value["quarterly_value_fields_read"] = []''',
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
_verify_c19 = _verify_c18 + '''        c19_manifest, c19_verification = executor._verify_prior_snapshot(
            path=C19_SNAPSHOT_PATH,
            manifest_sha256=C19_SNAPSHOT_SHA256,
            dataset_sha256=C19_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign019_feature_snapshot",
            factor_names=C19_FACTOR_NAMES,
            output_columns=C19_OUTPUT_COLUMNS,
            workers=workers,
        )
'''
if _verify_c18 not in _source:
    raise RuntimeError("Campaign019 prior-snapshot verification block was not found")
_source = _source.replace(_verify_c18, _verify_c19, 1)

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
_compare_c19 = _compare_c18 + '''        comparisons.extend(
            executor._prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c19_manifest,
                factors=C19_FACTOR_NAMES,
                gate=gate,
            )
        )
'''
if _compare_c18 not in _source:
    raise RuntimeError("Campaign019 comparison extension block was not found")
_source = _source.replace(_compare_c18, _compare_c19, 1)
_source = _source.replace(
    "Apply coverage before all 40 frozen uniqueness comparisons.",
    "Apply coverage before all 41 frozen uniqueness comparisons.",
    1,
)
_source = _source.replace("len(comparisons) == 40", "len(comparisons) == 41", 1)
_source = _source.replace(
    '''            "campaign018_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    '''            "campaign018_terminal_comparison_count": 1,
            "campaign019_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,''',
    1,
)
_source = _source.replace(
    '''            "campaign018_snapshot_file_verification": c18_verification,
            "comparisons": comparisons,''',
    '''            "campaign018_snapshot_file_verification": c18_verification,
            "campaign019_snapshot_file_verification": c19_verification,
            "comparisons": comparisons,''',
    1,
)
_source = _source.replace(
    '''        "source_fields_read": list(RAW_COLUMNS),''',
    '''        "source_fields_read": list(RAW_COLUMNS),
        "quarterly_disclosure_fields_read": list(EVENT_FIELDS),
        "quarterly_value_fields_read": [],''',
    1,
)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign020_features_generated",
    "DISCLOSURE_PATH": DISCLOSURE_PATH,
    "DISCLOSURE_SHA256": DISCLOSURE_SHA256,
    "DISCLOSURE_MANIFEST_PATH": DISCLOSURE_MANIFEST_PATH,
    "DISCLOSURE_MANIFEST_SHA256": DISCLOSURE_MANIFEST_SHA256,
    "CALENDAR_PATH": CALENDAR_PATH,
    "CALENDAR_SHA256": CALENDAR_SHA256,
    "EVENT_FIELDS": EVENT_FIELDS,
    "FORBIDDEN_EVENT_VALUE_FIELDS": FORBIDDEN_EVENT_VALUE_FIELDS,
    "DECAY_SCALE_SESSIONS": DECAY_SCALE_SESSIONS,
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
    }
)
exec(compile(_source, str(CAMPAIGN019_FEATURE_RUNNER), "exec"), _generated)

Campaign020FeatureError = _generated["Campaign020FeatureError"]
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
    "market",
):
    globals()[_export_name] = _generated[_export_name]


if __name__ == "__main__":
    raise SystemExit(main())
