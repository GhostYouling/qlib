#!/usr/bin/env python3
"""Build the frozen Campaign068 profit/revenue acceleration-rank-gap snapshot."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign066_features.py"
BASE_RUNNER_SHA256 = "ff8bd4aef61f7eec00299d1b38e21c30e15a4e7b010d157b0ea60d0576adf614"
BASE_FACTOR = "quarterly_quality_rank_balance_3f"
FACTOR_NAME = "quarterly_profit_revenue_acceleration_rank_gap_2r"
FACTOR_FORMULA = "r_profit_yoy_acceleration-r_revenue_yoy_acceleration"
PROTOCOL_SHA256 = "64aeee6a3534f00f878259b3406a09bc4f3b5d0ea3157bde86d0050f56b82061"
MECHANISM_AUDIT_SHA256 = "9cd5be63ea23807448662ac2f453ff643a129d766175828295605bcb9e8568be"
FULL_DEFINITION_COUNT = 99
FULL_DEFINITION_ORDER_SHA256 = "74564d4d2d01a52371ddd6906db38b5d913acb743656a04bbe5c4f229c84ad53"
COMPARISON_COUNT = 98
COMPARISON_ORDER_SHA256 = "bca0ba26252fcb74afa3a31ee1baf63c9cedfe3db5fc86ef71b3d7d93bf88f81"
C67_FACTOR = "quarterly_roe_profit_scale_efficiency_gap_2r"
EVENT_FIELDS = (
    "instrument",
    "report_date",
    "announcement_date",
    "revenue_yoy",
    "profit_yoy",
)
STATE_FIELDS = (
    "profit_yoy_acceleration",
    "revenue_yoy_acceleration",
)
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if not BASE_RUNNER.is_file() or _sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign066 feature runner changed")


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign066", "Campaign068"),
    ("campaign066", "campaign068"),
    ("campaign_066", "campaign_068"),
    (BASE_FACTOR, FACTOR_NAME),
    (
        "1-(max(r_roe,r_profit,r_revenue)-min(r_roe,r_profit,r_revenue))",
        FACTOR_FORMULA,
    ),
    (
        "ab850ef8ff194c1172070e2ffd388eff2d7924354abf06a8b32c5bd43584a278",
        PROTOCOL_SHA256,
    ),
    (
        "1e5fe44c0cde5097646cf058ec8149c189cf65e2ce62093e221c0d5022b98b8b",
        MECHANISM_AUDIT_SHA256,
    ),
    ("FULL_DEFINITION_COUNT = 97", "FULL_DEFINITION_COUNT = 99"),
    (
        "bc66abb94f62bef5fe9912059ade232c6c86b16b82f162df577fa8d74afeca7d",
        FULL_DEFINITION_ORDER_SHA256,
    ),
    ("COMPARISON_COUNT = 96", "COMPARISON_COUNT = 98"),
    (
        "794dff48d649b8dec1fdf609583ad87260c3e71a681a48b9a0ce77726de4763b",
        COMPARISON_ORDER_SHA256,
    ),
    ("C65_FACTOR", "C67_FACTOR"),
    ("intraday_range_weak_order_time_reversal_divergence_236t", C67_FACTOR),
    ("campaign065", "campaign067"),
    (
        'EVENT_FIELDS = ("instrument", "report_date", "announcement_date", "roe", "profit_yoy", "revenue_yoy")',
        'EVENT_FIELDS = ("instrument", "report_date", "announcement_date", "revenue_yoy", "profit_yoy")',
    ),
    (
        'STATE_FIELDS = ("roe", "profit_yoy", "revenue_yoy")',
        'STATE_FIELDS = ("profit_yoy_acceleration", "revenue_yoy_acceleration")',
    ),
    (
        "states = np.full((len(out), 3), np.nan, dtype=np.float64)",
        "states = np.full((len(out), 2), np.nan, dtype=np.float64)",
    ),
):
    _source = _source.replace(_old, _new)

_runtime: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign068_features_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _runtime)


Campaign068FeatureError = _runtime["Campaign068FeatureError"]
bindings = _runtime["bindings"]
DEFAULT_DATA_ROOT: Path = _runtime["DEFAULT_DATA_ROOT"]
DEFAULT_PROTOCOL = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_068_no_return_preregistration.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_068_feature_implementation_freeze_20260806.json"
)
DEFAULT_CALENDAR: Path = _runtime["DEFAULT_CALENDAR"]
CLEAN_MANIFEST_RELATIVE: Path = _runtime["CLEAN_MANIFEST_RELATIVE"]
QUARTERLY_PATH: Path = _runtime["QUARTERLY_PATH"]
QUARTERLY_MANIFEST_PATH: Path = _runtime["QUARTERLY_MANIFEST_PATH"]
EXPECTED_PARTITIONS = int(_runtime["EXPECTED_PARTITIONS"])
EXPECTED_ROWS = int(_runtime["EXPECTED_ROWS"])


def reconstruct_comparisons(
    spec: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    spec = spec or json.loads(DEFAULT_PROTOCOL.read_text(encoding="utf-8"))
    link = (
        (spec.get("source_chain") or {}).get(
            "campaign067_completed_numeric_comparison_catalog"
        )
        or {}
    )
    path = REPO_ROOT / str(link.get("path") or "")
    if not path.is_file() or _sha256(path) != str(link.get("sha256") or ""):
        raise Campaign068FeatureError("Campaign067 comparison catalog changed")
    audit = json.loads(path.read_text(encoding="utf-8"))
    previous = (audit.get("uniqueness") or {}).get(C67_FACTOR) or {}
    items = [
        {
            "name": str(item["comparison_factor"]),
            "score_direction": str(item["score_direction"]),
        }
        for item in previous.get("comparisons") or []
    ]
    items.append({"name": C67_FACTOR, "score_direction": "higher"})
    if (
        len(items) != COMPARISON_COUNT
        or _runtime["_comparison_order_digest"](items) != COMPARISON_ORDER_SHA256
    ):
        raise Campaign068FeatureError("Campaign068 comparison order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.is_file() or _sha256(path) != PROTOCOL_SHA256:
        raise Campaign068FeatureError(f"Campaign068 protocol changed: {path}")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign068FeatureError("Campaign068 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    unique = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    comparisons = reconstruct_comparisons(spec)
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign068_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign068_source_candidate_comparison_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and tuple(candidate.get("quarterly_source_projection") or ()) == EVENT_FIELDS
        and candidate.get("combination_rule", "").startswith(
            "Exactly r_profit_yoy_acceleration-r_revenue_yoy_acceleration"
        )
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and unique.get("complete_definition_count") == FULL_DEFINITION_COUNT
        and unique.get("complete_definition_order_sha256")
        == FULL_DEFINITION_ORDER_SHA256
        and unique.get("numeric_comparator_count") == COMPARISON_COUNT
        and unique.get("numeric_comparator_order_sha256")
        == COMPARISON_ORDER_SHA256
        and unique.get("all_98_numeric_comparators_must_pass") is True
        and len(comparisons) == COMPARISON_COUNT
        and finite.get("trial_id")
        == "wf068_quarterly_profit_revenue_acceleration_rank_gap_2r_single_higher"
        and finite.get("expected_trial_count") == 1
        and boundary.get("quarterly_or_minute_source_rows_read_before_this_freeze")
        is False
        and boundary.get("candidate_or_comparison_values_read_before_this_freeze")
        is False
        and boundary.get("historical_forward_return_fields_read") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign068FeatureError("Campaign068 protocol semantics changed")
    return spec


def compute_gap_values(ranks: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(ranks, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 2:
        raise Campaign068FeatureError("acceleration rank gap requires an n-by-2 array")
    eligible = np.isfinite(values).all(axis=1) & (
        ((values >= 0.0) & (values <= 1.0)).all(axis=1)
    )
    result = np.full(len(values), np.nan, dtype=np.float64)
    result[eligible] = values[eligible, 0] - values[eligible, 1]
    if ((result[eligible] < -1.0) | (result[eligible] > 1.0)).any():
        raise Campaign068FeatureError("acceleration rank gap escaped [-1,1]")
    return result, eligible


def prepare_events(
    events: pd.DataFrame, calendar: pd.DatetimeIndex
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Compute same-quarter accelerations before strict-next-session activation."""

    if tuple(events.columns) != EVENT_FIELDS:
        raise Campaign068FeatureError("quarterly source projection changed")
    work = events.copy()
    work["instrument"] = work["instrument"].astype(str).str.upper()
    for column in ("report_date", "announcement_date"):
        work[column] = pd.to_datetime(work[column], errors="coerce").dt.normalize()
    for column in ("revenue_yoy", "profit_yoy"):
        work[column] = pd.to_numeric(work[column], errors="coerce")
    if (
        work.empty
        or work[["instrument", "report_date", "announcement_date"]]
        .isna()
        .any()
        .any()
        or work.duplicated(["instrument", "report_date"]).any()
    ):
        raise Campaign068FeatureError("quarterly event identities changed")
    work = work.sort_values(
        ["instrument", "report_date", "announcement_date"], kind="stable"
    )
    work["_report_month"] = work["report_date"].dt.month
    work["revenue_yoy_acceleration"] = work.groupby(
        ["instrument", "_report_month"], sort=False
    )["revenue_yoy"].diff()
    work["profit_yoy_acceleration"] = work.groupby(
        ["instrument", "_report_month"], sort=False
    )["profit_yoy"].diff()
    calendar_values = calendar.to_numpy(dtype="datetime64[ns]")
    positions = np.searchsorted(
        calendar_values,
        work["announcement_date"].to_numpy(dtype="datetime64[ns]"),
        side="right",
    )
    valid = positions < len(calendar_values)
    work = work.loc[valid].copy()
    work["effective_position"] = positions[valid]
    work = (
        work.sort_values(
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
    result: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for symbol, group in work.groupby("instrument", sort=False):
        states = group.loc[:, STATE_FIELDS].ffill().to_numpy(dtype=np.float64)
        result[str(symbol)] = (
            group["effective_position"].to_numpy(dtype=np.int64),
            states,
        )
    return result


def rank_and_gap_year_frame(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    ranks = [
        work.groupby("trade_date", sort=False)[column].rank(
            method="average", pct=True
        )
        for column in STATE_FIELDS
    ]
    rank_matrix = np.column_stack(
        [series.to_numpy(dtype=np.float64) for series in ranks]
    )
    values, eligible = compute_gap_values(rank_matrix)
    work[FACTOR_NAME] = values
    work[f"{FACTOR_NAME}_eligible"] = eligible
    work["provider"] = "eastmoney_quarterly_quality"
    return work


for _name, _value in {
    "FACTOR_NAME": FACTOR_NAME,
    "FACTOR_FORMULA": FACTOR_FORMULA,
    "PROTOCOL_SHA256": PROTOCOL_SHA256,
    "MECHANISM_AUDIT_SHA256": MECHANISM_AUDIT_SHA256,
    "FULL_DEFINITION_COUNT": FULL_DEFINITION_COUNT,
    "FULL_DEFINITION_ORDER_SHA256": FULL_DEFINITION_ORDER_SHA256,
    "COMPARISON_COUNT": COMPARISON_COUNT,
    "COMPARISON_ORDER_SHA256": COMPARISON_ORDER_SHA256,
    "C67_FACTOR": C67_FACTOR,
    "EVENT_FIELDS": EVENT_FIELDS,
    "STATE_FIELDS": STATE_FIELDS,
    "OUTPUT_COLUMNS": OUTPUT_COLUMNS,
    "DEFAULT_PROTOCOL": DEFAULT_PROTOCOL,
    "DEFAULT_IMPLEMENTATION_FREEZE": DEFAULT_IMPLEMENTATION_FREEZE,
    "reconstruct_comparisons": reconstruct_comparisons,
    "load_protocol": load_protocol,
    "compute_balance_values": compute_gap_values,
    "prepare_events": prepare_events,
    "rank_and_balance_year_frame": rank_and_gap_year_frame,
}.items():
    _runtime[_name] = _value


_runtime["FACTOR_RANGES"] = {FACTOR_NAME: (-1.0, 1.0)}
_runtime["FACTOR_FORMULAS"] = {FACTOR_NAME: FACTOR_FORMULA}

_comparison_order_digest = _runtime["_comparison_order_digest"]
attach_states = _runtime["attach_states"]
output_root = _runtime["output_root"]
build_snapshot = _runtime["build_snapshot"]
verify_snapshot_files = _runtime["verify_snapshot_files"]
status = _runtime["status"]
main = _runtime["main"]


if __name__ == "__main__":
    raise SystemExit(main())
