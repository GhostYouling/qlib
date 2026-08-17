#!/usr/bin/env python3
"""Build and no-return audit Campaign032 reporting timeliness."""

from __future__ import annotations

import gc
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    import scripts.a_share_three_day_preregistration_binding_validator as bindings
    import scripts.a_share_three_day_walkforward_campaign020_features as campaign020
    import scripts.a_share_three_day_walkforward_campaign031_features as campaign031
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_three_day_walkforward_campaign020_features as campaign020
    import a_share_three_day_walkforward_campaign031_features as campaign031


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN020_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign020_features.py"
)
CAMPAIGN020_FEATURE_RUNNER_SHA256 = (
    "d98b32e9b975aaaf82871c77d8442130f24fb3ba0439a92a7e51ecbd91939456"
)
OLD_FACTOR = "quarterly_announcement_freshness_60s"
FACTOR_NAME = "quarterly_announcement_timeliness_days"
MECHANISM_AUDIT_SHA256 = (
    "3b736aea9d09e4cd3f8ce371f015c73d0fac6f0b261e8426306b403cc0395bca"
)
BASE_PROTOCOL_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_032_no_return_preregistration.json"
)
BASE_PROTOCOL_SHA256 = (
    "4b788fa9f5119f24ed6875c977eb80ecb303a12a3db3fcac38ec0c2df50348ac"
)
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_032_no_return_preregistration_v2.json"
)
PROTOCOL_SHA256 = (
    "d03dc148d2169622cc2fdbe2248dbe336ccbd5c316f8a4faa708b16a69e44f8a"
)
REPORTING_ACTIVATION_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_032_"
    "reporting_semantics_activation_20260730.json"
)
REPORTING_ACTIVATION_SHA256 = (
    "07ca7a3589671cabc96c736058a2bf6068e8daca402a96c78037913bdfb88b89"
)

# Bind these after the immutable candidate snapshot and audit are published.
SNAPSHOT_MANIFEST_SHA256 = (
    "8e64ad897fe725ab4ed800b0203ddd88a6c1431e2386744e1d2b13867d848c65"
)
SNAPSHOT_DATASET_SHA256 = (
    "c72008162f6655e7ce34da114641f451aa04d32df61ac4c77222f7f8ad1d787f"
)
NO_RETURN_AUDIT_SHA256 = (
    "6096b9d725f5fc1e7f98467bb334a211350bcc86edda28132439fc98f28f8af9"
)

DISCLOSURE_PATH = campaign020.DISCLOSURE_PATH
DISCLOSURE_SHA256 = campaign020.DISCLOSURE_SHA256
DISCLOSURE_MANIFEST_PATH = campaign020.DISCLOSURE_MANIFEST_PATH
DISCLOSURE_MANIFEST_SHA256 = campaign020.DISCLOSURE_MANIFEST_SHA256
CALENDAR_PATH = campaign020.CALENDAR_PATH
CALENDAR_SHA256 = campaign020.CALENDAR_SHA256
EVENT_FIELDS = campaign020.EVENT_FIELDS
FORBIDDEN_EVENT_VALUE_FIELDS = campaign020.FORBIDDEN_EVENT_VALUE_FIELDS
RAW_COLUMNS = ("datetime", "symbol", "provider")
FACTOR_FORMULA = (
    "-1 * integer calendar days between report_date and announcement_date "
    "for the latest quarterly report effective at signal session t"
)
COMPARISON_ORDER_SHA256 = (
    "8ea05e33f57dfb24b0e8453109d74570ba2f3522b381095b5c5a21840c948339"
)
CAMPAIGN031_AUDIT_PATH = (
    REPO_ROOT
    / "data"
    / "experiments"
    / "short_horizon"
    / "historical_walkforward"
    / "campaign_031"
    / "no_return"
    / "20260730T140740Z_campaign031_no_return_audit.json"
)
CAMPAIGN031_AUDIT_SHA256 = (
    "659c3282bd02d85f5b3da99e555ba25ec227bf6c8546e50f12bc5e8ad97e30d9"
)
C31_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign031_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign031_feature_library_v1/snapshot_manifest.json"
)
C31_SNAPSHOT_SHA256 = (
    "4df07ce452454d742521e835f2b7954fe53c597ba47ec31438cb47fd2abbd086"
)
C31_DATASET_SHA256 = (
    "9858378a035142b36f19bf00b0b8c7847802e428f6798dc1900b2ae003bcd6b1"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN020_FEATURE_RUNNER) != CAMPAIGN020_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign020 feature orchestration changed")

_source = campaign020._source
for _old, _new in (
    ("Campaign020", "Campaign032"),
    ("campaign020", "campaign032"),
    ("campaign_020", "campaign_032"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "e61185b024e9d2a1a0f7d34769819c1c7a274d30f8f8ce235727daa626e606ad",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "cbd04a23d73c1535886a063cdf26bacc4d86b2ebec16bc0e8724efc82b4bc1e6",
        PROTOCOL_SHA256,
    ),
    (
        "a776c1bcfb3d573ea7583be843ee42b1b6a368ccc8d80dbd382bf56fa2115fdd",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "39cda0c04c87c94886ac9f0f99453a2db627fa5cd64096ba33ef92df91223faa",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "08752d1a28411d52fe59d574951065ba14b0eb729620c6c8a75b63efceb72794",
        NO_RETURN_AUDIT_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign032_features_generated",
    "DISCLOSURE_PATH": DISCLOSURE_PATH,
    "DISCLOSURE_SHA256": DISCLOSURE_SHA256,
    "DISCLOSURE_MANIFEST_PATH": DISCLOSURE_MANIFEST_PATH,
    "DISCLOSURE_MANIFEST_SHA256": DISCLOSURE_MANIFEST_SHA256,
    "CALENDAR_PATH": CALENDAR_PATH,
    "CALENDAR_SHA256": CALENDAR_SHA256,
    "EVENT_FIELDS": EVENT_FIELDS,
    "FORBIDDEN_EVENT_VALUE_FIELDS": FORBIDDEN_EVENT_VALUE_FIELDS,
    "DECAY_SCALE_SESSIONS": campaign020.DECAY_SCALE_SESSIONS,
}
for _campaign in (9, 10, 11, 12, 14, 15, 16, 17, 18, 19):
    for _suffix in (
        "SNAPSHOT_PATH",
        "SNAPSHOT_SHA256",
        "DATASET_SHA256",
        "FACTOR_NAMES",
        "OUTPUT_COLUMNS",
    ):
        _key = f"C{_campaign}_{_suffix}"
        _generated[_key] = campaign020.engine_namespace[_key]
exec(compile(_source, str(CAMPAIGN020_FEATURE_RUNNER), "exec"), _generated)

Campaign032FeatureError = _generated["Campaign032FeatureError"]
foundation = _generated["foundation"]
research = _generated["research"]
engine = _generated["engine"]
executor = _generated["executor"]
market = _generated["market"]
BASE_COLUMNS = _generated["BASE_COLUMNS"]
EXPECTED_PARTITIONS = int(_generated["EXPECTED_PARTITIONS"])
EXPECTED_ROWS = int(_generated["EXPECTED_ROWS"])
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT = _generated["DEFAULT_EXPERIMENT_ROOT"]
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
FACTOR_NAMES = (FACTOR_NAME,)
FACTOR_DIRECTIONS = {FACTOR_NAME: "higher"}
FACTOR_RANGES = {
    FACTOR_NAME: (-np.finfo(np.float64).max, 0.0),
}
FACTOR_FORMULAS = {FACTOR_NAME: FACTOR_FORMULA}

_generated["DEFAULT_PROTOCOL"] = DEFAULT_PROTOCOL
_generated["RAW_COLUMNS"] = RAW_COLUMNS
_generated["FACTOR_NAME"] = FACTOR_NAME
_generated["FACTOR_NAMES"] = FACTOR_NAMES
_generated["FACTOR_DIRECTIONS"] = FACTOR_DIRECTIONS
_generated["FACTOR_RANGES"] = FACTOR_RANGES
_generated["FACTOR_FORMULA"] = FACTOR_FORMULA
_generated["FACTOR_FORMULAS"] = FACTOR_FORMULAS
_generated["OUTPUT_COLUMNS"] = OUTPUT_COLUMNS


def _comparison_order_digest(comparisons: list[dict[str, Any]]) -> str:
    values = [
        (str(item["name"]), str(item["score_direction"]))
        for item in comparisons
    ]
    payload = json.dumps(
        values,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate the additive v2 freeze and return its complete effective spec."""

    path = path.expanduser().resolve()
    if _sha256(path) != PROTOCOL_SHA256:
        raise Campaign032FeatureError("Campaign032 v2 protocol changed")
    validation = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if not validation["all_bindings_passed"]:
        raise Campaign032FeatureError("Campaign032 v2 binding validation failed")
    if (
        _sha256(BASE_PROTOCOL_PATH) != BASE_PROTOCOL_SHA256
        or _sha256(REPORTING_ACTIVATION_PATH) != REPORTING_ACTIVATION_SHA256
        or _sha256(CAMPAIGN031_AUDIT_PATH) != CAMPAIGN031_AUDIT_SHA256
    ):
        raise Campaign032FeatureError("Campaign032 bound evidence changed")
    base = json.loads(BASE_PROTOCOL_PATH.read_text(encoding="utf-8"))
    overlay = json.loads(path.read_text(encoding="utf-8"))
    source_chain = base.get("source_chain") or {}
    stale = source_chain.get("campaign031_no_return_audit") or {}
    correction = overlay.get("sole_correction") or {}
    candidates = list(base.get("candidates") or [])
    candidate = candidates[0] if len(candidates) == 1 else {}
    gates = base.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    comparisons = list(uniqueness.get("comparison_factors") or [])
    finite = base.get("finite_post_admissibility_search") or {}
    trial = finite.get("trial") or {}
    boundary = base.get("research_boundary") or {}
    source = source_chain.get("quarterly_disclosure_source") or {}
    if not (
        overlay.get("version") == 2
        and overlay.get("status")
        == (
            "corrected_additive_freeze_before_campaign032_stock_day_"
            "quarterly_candidate_comparison_or_return_values"
        )
        and stale.get("sha256")
        == "b994169eeecbb3d47cdca32cbbfbb873be5299493209321da5e3895631211334"
        and correction.get("path") == stale.get("path")
        and correction.get("sha256") == CAMPAIGN031_AUDIT_SHA256
        and base.get("version") == 1
        and base.get("status")
        == (
            "frozen_before_campaign032_stock_day_quarterly_candidate_"
            "comparison_or_return_values"
        )
        and len(candidates) == 1
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("stock_day_identity_fields") or ())
        == RAW_COLUMNS
        and tuple(candidate.get("event_fields_allowed") or ()) == EVENT_FIELDS
        and tuple(candidate.get("event_fields_used_by_formula") or ())
        == EVENT_FIELDS
        and tuple(candidate.get("event_value_fields_forbidden") or ())
        == FORBIDDEN_EVENT_VALUE_FIELDS
        and candidate.get("direction_transform")
        == "multiply the nonnegative delay by exact negative one"
        and candidate.get("transform_scale_clip_threshold_filter") == "none"
        and candidate.get("valid_range") == [None, 0]
        and source.get("sha256") == DISCLOSURE_SHA256
        and source.get("manifest_sha256") == DISCLOSURE_MANIFEST_SHA256
        and tuple(source.get("projected_columns") or ()) == EVENT_FIELDS
        and tuple(source.get("forbidden_value_columns") or ())
        == FORBIDDEN_EVENT_VALUE_FIELDS
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
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
        and len(comparisons) == 53
        and len({str(item.get("name")) for item in comparisons}) == 53
        and comparisons[-1]
        == {
            "name": "intraday_market_dispersion_decoupling_238m",
            "score_direction": "higher",
        }
        and _comparison_order_digest(comparisons) == COMPARISON_ORDER_SHA256
        and finite.get("candidate_factor_count") == 1
        and finite.get("development_trial_count") == 1
        and trial.get("factor") == FACTOR_NAME
        and trial.get("direction") == "higher"
        and trial.get("transform") == "none"
        and trial.get("threshold") == "none"
        and trial.get("filter") == "none"
        and trial.get("combination") == "none"
        and boundary.get(
            "binding_validation_required_before_stock_day_quarterly_or_"
            "candidate_values"
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
        and boundary.get("forward_return_fields_read_before_admissibility")
        is False
        and boundary.get("comparison_values_read_before_coverage_pass") is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("provider_request_allowed") is False
    ):
        raise Campaign032FeatureError("Campaign032 protocol semantics changed")
    source_chain["campaign031_no_return_audit"] = dict(correction)
    return base


_EVENT_CACHE: Any = None


def _load_effective_events() -> tuple[np.ndarray, dict[str, tuple[np.ndarray, np.ndarray]]]:
    """Load only frozen quarterly identity/timing fields once per process."""

    global _EVENT_CACHE
    if _EVENT_CACHE is not None:
        return _EVENT_CACHE
    if (
        _sha256(DISCLOSURE_PATH) != DISCLOSURE_SHA256
        or _sha256(DISCLOSURE_MANIFEST_PATH) != DISCLOSURE_MANIFEST_SHA256
        or _sha256(CALENDAR_PATH) != CALENDAR_SHA256
    ):
        raise Campaign032FeatureError("quarterly or calendar evidence changed")
    calendar = pd.to_datetime(
        CALENDAR_PATH.read_text(encoding="utf-8").splitlines(),
        errors="coerce",
    )
    if pd.isna(calendar).any():
        raise Campaign032FeatureError("accepted calendar contains invalid dates")
    calendar = pd.DatetimeIndex(calendar).normalize().unique().sort_values()
    calendar_values = calendar.to_numpy(dtype="datetime64[ns]")
    events = pd.read_parquet(
        DISCLOSURE_PATH,
        columns=list(EVENT_FIELDS),
        filters=[("announcement_date", "<", pd.Timestamp("2026-01-01"))],
    )
    if tuple(events.columns) != EVENT_FIELDS:
        raise Campaign032FeatureError("quarterly projection changed")
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
        raise Campaign032FeatureError("quarterly event identities changed")
    delay_days = (
        events["announcement_date"] - events["report_date"]
    ).dt.days.to_numpy(dtype=np.int64)
    if (delay_days < 0).any():
        events = events.loc[delay_days >= 0].copy()
        delay_days = delay_days[delay_days >= 0]
    events["score"] = -delay_days.astype(np.float64)
    effective_positions = np.searchsorted(
        calendar_values,
        events["announcement_date"].to_numpy(dtype="datetime64[ns]"),
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
        str(symbol): (
            group["effective_position"].to_numpy(dtype=np.int64),
            group["score"].to_numpy(dtype=np.float64),
        )
        for symbol, group in events.groupby("instrument", sort=False)
    }
    _EVENT_CACHE = (calendar_values, by_symbol)
    return _EVENT_CACHE


def compute_factor_values(
    latest_scores: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Validate the frozen negative calendar-day reporting-delay score."""

    values = np.asarray(latest_scores, dtype=float)
    if values.ndim != 1:
        raise Campaign032FeatureError("Campaign032 score vector is invalid")
    finite = np.isfinite(values)
    nonpositive = values <= 0.0
    integer_days = np.equal(values, np.floor(values))
    eligible = finite & nonpositive & integer_days
    quality = {
        "base_rows": int(len(values)),
        f"{FACTOR_NAME}__no_prior_effective_disclosure_rows": int(
            (~finite).sum()
        ),
        f"{FACTOR_NAME}__positive_or_noninteger_delay_score_rows": int(
            (finite & (~nonpositive | ~integer_days)).sum()
        ),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
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
    """Validate one stock-year key grid and compute reporting timeliness."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign032FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign032FeatureError(
            f"unexpected joint-base columns for {symbol}: "
            f"{tuple(base_frame.columns)}"
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
        raise Campaign032FeatureError(f"joint-base identity changed for {symbol}")
    base_work = base_work.sort_values(
        "trade_date", kind="stable"
    ).reset_index(drop=True)
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
        raise Campaign032FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not counts.eq(241).all():
        raise Campaign032FeatureError(
            f"every source stock-day must retain 241 rows for {symbol}"
        )
    codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].agg(lambda values: frozenset(int(value) for value in values))
    if not codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign032FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign032FeatureError(
            f"source and joint-base dates changed for {symbol}"
        )
    calendar_values, events_by_symbol = _load_effective_events()
    trade_values = base_work["trade_date"].to_numpy(dtype="datetime64[ns]")
    trade_positions = np.searchsorted(calendar_values, trade_values, side="left")
    bounded = trade_positions < len(calendar_values)
    if (
        not bounded.all()
        or not np.array_equal(calendar_values[trade_positions], trade_values)
    ):
        raise Campaign032FeatureError(
            f"base dates are outside accepted calendar for {symbol}"
        )
    latest_scores = np.full(len(trade_positions), np.nan, dtype=float)
    event_state = events_by_symbol.get(symbol.upper())
    if event_state is not None:
        event_positions, event_scores = event_state
        selected = np.searchsorted(
            event_positions, trade_positions, side="right"
        ) - 1
        has_event = selected >= 0
        latest_scores[has_event] = event_scores[selected[has_event]]
    values, eligible, quality = compute_factor_values(latest_scores)
    frame = pd.DataFrame(
        {
            "trade_date": base_work["trade_date"],
            "symbol": symbol.upper(),
            "provider": "eastmoney_disclosure_timeliness",
            FACTOR_NAME: values[FACTOR_NAME],
            f"{FACTOR_NAME}_eligible": eligible[FACTOR_NAME],
        }
    )
    return frame.loc[:, OUTPUT_COLUMNS], quality


_generated["load_protocol"] = load_protocol
_generated["compute_factor_values"] = compute_factor_values
_generated["compute_partition_frame"] = compute_partition_frame

empty_output_frame = _generated["empty_output_frame"]
output_root = _generated["output_root"]
build_snapshot = _generated["build_snapshot"]
verify_snapshot_files = _generated["verify_snapshot_files"]
_validate_snapshot_manifest = _generated["_validate_snapshot_manifest"]


def _snapshot_specs_from_campaign031() -> list[dict[str, Any]]:
    """Rebuild the hash-bound post-Candidate49 comparison snapshot catalog."""

    if _sha256(CAMPAIGN031_AUDIT_PATH) != CAMPAIGN031_AUDIT_SHA256:
        raise Campaign032FeatureError("Campaign031 no-return audit changed")
    audit = json.loads(CAMPAIGN031_AUDIT_PATH.read_text(encoding="utf-8"))
    uniqueness = (
        (audit.get("uniqueness") or {}).get(
            "intraday_market_dispersion_decoupling_238m"
        )
        or {}
    )
    specs: list[dict[str, Any]] = []
    for campaign in [4, 5, 6, 7, *range(9, 32)]:
        if campaign == 8 or campaign == 13:
            continue
        key = f"campaign{campaign:03d}_snapshot_file_verification"
        if campaign == 31:
            verification = {
                "path": str(C31_SNAPSHOT_PATH),
                "sha256": C31_SNAPSHOT_SHA256,
                "dataset_sha256": C31_DATASET_SHA256,
            }
        else:
            verification = uniqueness.get(key) or {}
        path = Path(str(verification.get("path") or "")).expanduser().resolve()
        expected_sha = str(verification.get("sha256") or "")
        dataset_sha = str(verification.get("dataset_sha256") or "")
        if not path.is_file() or _sha256(path) != expected_sha:
            raise Campaign032FeatureError(
                f"Campaign{campaign:03d} comparison snapshot changed"
            )
        manifest = json.loads(path.read_text(encoding="utf-8"))
        all_factors = tuple(str(value) for value in manifest.get("factor_names") or ())
        if not all_factors:
            raise Campaign032FeatureError(
                f"Campaign{campaign:03d} factor catalog is empty"
            )
        output_columns: list[str] = ["trade_date", "symbol", "provider"]
        for factor in all_factors:
            output_columns.extend([factor, f"{factor}_eligible"])
        specs.append(
            {
                "campaign": campaign,
                "path": path,
                "sha256": expected_sha,
                "dataset_sha256": dataset_sha,
                "kind": str(manifest.get("kind") or ""),
                "all_factors": all_factors,
                "output_columns": tuple(output_columns),
            }
        )
    return specs


def run_no_return_audit(
    *,
    data_root: Path,
    experiment_root: Path,
    workers: int,
) -> Path:
    """Apply coverage before the complete 53-factor uniqueness library."""

    if not SNAPSHOT_MANIFEST_SHA256 or not SNAPSHOT_DATASET_SHA256:
        raise Campaign032FeatureError(
            "bind Campaign032 snapshot fingerprints before audit"
        )
    _generated["_bind_executor"]()
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_protocol()
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    if _sha256(manifest_path) != SNAPSHOT_MANIFEST_SHA256:
        raise Campaign032FeatureError("Campaign032 snapshot manifest changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    existing = sorted(experiment_root.glob("*_campaign032_no_return_audit.json"))
    if existing:
        if len(existing) != 1 or not NO_RETURN_AUDIT_SHA256:
            raise Campaign032FeatureError(
                "existing Campaign032 audit is ambiguous or unbound"
            )
        if _sha256(existing[0]) != NO_RETURN_AUDIT_SHA256:
            raise Campaign032FeatureError("Campaign032 audit changed")
        return existing[0]
    verification = verify_snapshot_files(manifest, manifest_path, workers)
    print("building Campaign032 no-price quality/listing eligibility", flush=True)
    eligible_keys = foundation.quality_listing_eligible_keys(spec)
    candidate = engine.load_factor_frame(manifest_path, manifest, FACTOR_NAME)
    quality_frame, coverage = engine.coverage_and_capacity(
        candidate,
        eligible_keys,
        spec,
        FACTOR_NAME,
    )
    del candidate, eligible_keys
    gc.collect()
    if coverage["gate_passed_before_comparison_values"]:
        gate = spec["ordered_no_return_gates"][
            "uniqueness_after_coverage_only"
        ]
        expected_order = [
            str(item["name"]) for item in gate["comparison_factors"]
        ]
        keys, values = engine._sorted_candidate_arrays(
            quality_frame,
            FACTOR_NAME,
        )
        chain, candidate49_manifest_path, candidate49_manifest = (
            engine._comparison_chain(data_root)
        )
        comparisons, frozen_verifications = (
            engine._uniqueness_against_frozen_library(
                candidate_keys=keys,
                candidate_values=values,
                chain=chain,
                candidate49_manifest_path=candidate49_manifest_path,
                candidate49_manifest=candidate49_manifest,
                gate=gate,
                workers=workers,
                frozen_verifications=None,
            )
        )
        snapshot_verifications: dict[str, Any] = {}
        for snapshot_spec in _snapshot_specs_from_campaign031():
            prior_manifest, prior_verification = executor._verify_prior_snapshot(
                path=snapshot_spec["path"],
                manifest_sha256=snapshot_spec["sha256"],
                dataset_sha256=snapshot_spec["dataset_sha256"],
                kind=snapshot_spec["kind"],
                factor_names=snapshot_spec["all_factors"],
                output_columns=snapshot_spec["output_columns"],
                workers=workers,
            )
            selected = tuple(
                factor
                for factor in snapshot_spec["all_factors"]
                if factor in expected_order
            )
            if selected:
                comparisons.extend(
                    executor._prior_comparisons(
                        candidate_keys=keys,
                        candidate_values=values,
                        manifest=prior_manifest,
                        factors=selected,
                        gate=gate,
                    )
                )
            snapshot_verifications[
                f"campaign{snapshot_spec['campaign']:03d}"
            ] = prior_verification
        observed_order = [
            str(item["comparison_factor"]) for item in comparisons
        ]
        observed = [
            float(item["absolute_median_daily_rank_correlation"])
            for item in comparisons
            if item["absolute_median_daily_rank_correlation"] is not None
        ]
        passed = bool(
            observed_order == expected_order
            and len(comparisons) == 53
            and all(item["gate_passed"] for item in comparisons)
        )
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": True,
            "comparison_factor_count": len(comparisons),
            "comparison_order_matches_preregistration": (
                observed_order == expected_order
            ),
            "pre_campaign004_comparison_count": 25,
            "post_campaign003_snapshot_verification": snapshot_verifications,
            "prior_snapshot_file_verification": frozen_verifications,
            "comparisons": comparisons,
            "maximum_observed_absolute_median_daily_rank_correlation": (
                max(observed) if observed else None
            ),
            "all_required_comparisons_passed": passed,
        }
    else:
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": False,
            "comparisons": [],
            "all_required_comparisons_passed": False,
            "failure_reason": "coverage_gate_failed",
        }
    admitted = bool(
        coverage["gate_passed_before_comparison_values"]
        and uniqueness["all_required_comparisons_passed"]
    )
    run_id = f"{research._timestamp()}_campaign032_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign032_no_return_audit",
        "status": (
            "completed_with_one_admissible_factor_pending_walkforward_preregistration"
            if admitted
            else "completed_zero_admissible_factors_stop_before_historical_returns"
        ),
        "run_id": run_id,
        "created_at": research._timestamp(),
        "mechanism_overlap_audit": {
            "path": str(_generated["MECHANISM_AUDIT"].resolve()),
            "sha256": MECHANISM_AUDIT_SHA256,
        },
        "protocol": {
            "path": str(DEFAULT_PROTOCOL.resolve()),
            "sha256": PROTOCOL_SHA256,
            "complete_spec_base_path": str(BASE_PROTOCOL_PATH.resolve()),
            "complete_spec_base_sha256": BASE_PROTOCOL_SHA256,
        },
        "candidate_snapshot": {
            "path": str(manifest_path),
            "sha256": SNAPSHOT_MANIFEST_SHA256,
            "dataset_sha256": SNAPSHOT_DATASET_SHA256,
        },
        "snapshot_file_verification": verification,
        "coverage_and_capacity": {FACTOR_NAME: coverage},
        "uniqueness": {FACTOR_NAME: uniqueness},
        "admissible_factor_names": [FACTOR_NAME] if admitted else [],
        "admissible_factor_count": 1 if admitted else 0,
        "failed_factor_names": [] if admitted else [FACTOR_NAME],
        "next_action": (
            "freeze the exact one-trial Campaign032 walk-forward catalog "
            "before reading 2019-2023 returns"
            if admitted
            else "record the no-return rejection and design a new campaign"
        ),
        "source_fields_read": list(RAW_COLUMNS),
        "quarterly_disclosure_fields_read": list(EVENT_FIELDS),
        "quarterly_value_fields_read": [],
        "minute_price_volume_amount_fields_read": [],
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "candidate49_prospective_ledgers_changed": False,
        "candidate50_prospective_activation_created": False,
        "training_or_model_fitting_performed": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    destination = experiment_root / f"{run_id}.json"
    foundation.atomic_write_json(record, destination)
    return destination


def status(data_root: Path, experiment_root: Path) -> dict[str, Any]:
    manifest_path = output_root(
        data_root.expanduser().resolve()
    ) / "snapshot_manifest.json"
    audits = sorted(
        experiment_root.expanduser().resolve().glob(
            "*_campaign032_no_return_audit.json"
        )
    )
    result: dict[str, Any] = {
        "protocol_path": str(DEFAULT_PROTOCOL.resolve()),
        "protocol_sha256_bound": True,
        "snapshot_manifest_path": str(manifest_path),
        "snapshot_exists": manifest_path.is_file(),
        "snapshot_sha256_bound": bool(SNAPSHOT_MANIFEST_SHA256),
        "audit_count": len(audits),
        "no_return_audit_sha256_bound": bool(NO_RETURN_AUDIT_SHA256),
        "stock_day_identity_fields_read_by_status": list(RAW_COLUMNS),
        "quarterly_disclosure_fields_read_by_status": list(EVENT_FIELDS),
        "quarterly_value_fields_read_by_status": [],
        "minute_price_volume_amount_fields_read_by_status": [],
        "daily_price_fields_read_by_status": False,
        "forward_return_fields_read_by_status": False,
        "candidate49_historical_return_read": False,
    }
    if manifest_path.is_file():
        result["snapshot_observed_sha256"] = _sha256(manifest_path)
    if audits:
        result["latest_audit"] = str(audits[-1])
        result["latest_audit_observed_sha256"] = _sha256(audits[-1])
    return result


_generated["run_no_return_audit"] = run_no_return_audit
_generated["status"] = status

parser = _generated["parser"]
main = _generated["main"]
engine_namespace = _generated


if __name__ == "__main__":
    raise SystemExit(main())
