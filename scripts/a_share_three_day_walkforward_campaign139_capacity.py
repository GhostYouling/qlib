#!/usr/bin/env python3
"""Run Campaign139's frozen quality/listing event-capacity gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import a_share_three_day_walkforward_campaign139_formula as formula


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_V1_PATH = formula.PROTOCOL_PATH
PROTOCOL_V1_SHA256 = formula.PROTOCOL_SHA256
PROTOCOL_V2_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_139_no_return_preregistration_v2_20260814.json"
)
PROTOCOL_V2_SHA256 = "eaeffa8e446ee8aa683b2eadee8b20a6c9430978d6d31bdd5696c9a6d4e373b3"
PROTOCOL_V3_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_139_no_return_preregistration_v3_20260814.json"
)
PROTOCOL_V3_SHA256 = "33c1fcb340a925bfa11f58700ee58225388f0dd06f1b050cb276d68c80914edf"
SOURCE_PUBLICATION_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_139_source_snapshot_publication_20260814.json"
)
SOURCE_PUBLICATION_SHA256 = (
    "811c1ba91b9f6e5bb7857028f27648cc20c4b8f7b02c4f955ad97224dd12802f"
)
SOURCE_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_139/source_snapshot_v1"
)
SOURCE_MANIFEST_PATH = SOURCE_ROOT / "snapshot_manifest.json"
SOURCE_MANIFEST_SHA256 = (
    "82eac4501fb72dd5fe1972dd0f42c3fa2cd16f8975a0b5f55e2b4018401a38a5"
)
SOURCE_DATA_PATH = SOURCE_ROOT / "campaign139_forecast_realization_events.parquet"
SOURCE_DATA_SHA256 = "ce8de0d0a4e8c59746ba06c917399c75515d6e486f159ee6ab7b85df2c272a1a"
CALENDAR_PATH = REPO_ROOT / "data/qlib/cn_a_share/calendars/day.txt"
CALENDAR_SHA256 = "fda506597d26bcec953cdc0882042a5046ec1587db60490e16a01627fd43f53a"
QUALITY_KEY_HELPER_PATH = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign117_no_return_audit.py"
)
QUALITY_KEY_HELPER_SHA256 = (
    "8ea3a1b2e0cc369ea6a1192304af101b54fecdfebc5334fa199dbe53807331a5"
)
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_139_capacity_implementation_freeze_20260814.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign139_capacity.py"
)
OUTPUT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_139/capacity"
)
OUTPUT_AUDIT_NAME = "campaign139_capacity_audit.json"
OUTPUT_CANDIDATE_NAME = "campaign139_development_candidate_signal_snapshot.parquet"

DEVELOPMENT_START = pd.Timestamp("2019-01-01")
DEVELOPMENT_END = pd.Timestamp("2023-12-31")
HOLDING_PERIOD_SESSIONS = 3
MINIMUM_NAMES = 6
MINIMUM_DISTINCT_VALUES = 2
MINIMUM_COHORTS = 200
MINIMUM_YEARS = 5
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    "raw_surprise",
    formula.FACTOR_NAME,
)


class Campaign139CapacityError(RuntimeError):
    """Fail closed when a Campaign139 capacity binding changes."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_file(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or file_sha256(path) != expected:
        raise Campaign139CapacityError(f"Campaign139 {label} binding changed")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Campaign139CapacityError(f"expected JSON object: {path}")
    return value


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def expected_gate() -> dict[str, Any]:
    return {
        "development_signal_start": DEVELOPMENT_START.date().isoformat(),
        "development_signal_end": DEVELOPMENT_END.date().isoformat(),
        "holding_period_signal_sessions": HOLDING_PERIOD_SESSIONS,
        "minimum_quality_listing_eligible_names": MINIMUM_NAMES,
        "minimum_distinct_raw_surprise_values": MINIMUM_DISTINCT_VALUES,
        "minimum_non_overlapping_three_signal_session_cohorts": MINIMUM_COHORTS,
        "minimum_observed_cohort_years": MINIMUM_YEARS,
        "grid_origin": "first accepted local session on or after 2019-01-01",
        "grid_step_sessions": 3,
        "t_plus_3_must_exist_inside_development_interval": True,
    }


def validate_static_metadata() -> dict[str, Any]:
    for path, expected, label in (
        (PROTOCOL_V1_PATH, PROTOCOL_V1_SHA256, "v1 preregistration"),
        (PROTOCOL_V2_PATH, PROTOCOL_V2_SHA256, "v2 preregistration"),
        (PROTOCOL_V3_PATH, PROTOCOL_V3_SHA256, "v3 preregistration"),
        (SOURCE_PUBLICATION_PATH, SOURCE_PUBLICATION_SHA256, "source publication"),
        (SOURCE_MANIFEST_PATH, SOURCE_MANIFEST_SHA256, "source manifest"),
        (SOURCE_DATA_PATH, SOURCE_DATA_SHA256, "source data"),
        (CALENDAR_PATH, CALENDAR_SHA256, "calendar"),
        (
            QUALITY_KEY_HELPER_PATH,
            QUALITY_KEY_HELPER_SHA256,
            "quality/listing key helper",
        ),
    ):
        require_file(path, expected, label)
    manifest = load_json(SOURCE_MANIFEST_PATH)
    output = manifest.get("output") or {}
    boundary = manifest.get("research_boundary") or {}
    publication = load_json(SOURCE_PUBLICATION_PATH)
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign139_source_snapshot"
        and manifest.get("status")
        == "immutable_local_event_snapshot_built_before_capacity_comparators_prices_or_returns"
        and manifest.get("factor") == formula.FACTOR_NAME
        and manifest.get("direction") == formula.SCORE_DIRECTION
        and output.get("sha256") == SOURCE_DATA_SHA256
        and output.get("rows") == 37185
        and output.get("columns")
        == [
            "effective_date",
            "event_expiry_date",
            "instrument",
            "provider",
            "report_date",
            "realized_announcement_date",
            "forecast_announcement_date",
            "realized_profit_yoy",
            "forecast_profit_yoy",
            "raw_surprise",
        ]
        and boundary.get("comparator_values_read") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
        and boundary.get("stress_2024_2025_opened") is False
        and publication.get("status")
        == "immutable_local_event_snapshot_published_before_capacity_comparators_prices_or_returns"
        and pq.read_schema(SOURCE_DATA_PATH).names == output.get("columns")
    ):
        raise Campaign139CapacityError("Campaign139 source publication changed")
    return {
        "source_manifest_status": manifest["status"],
        "source_rows": output["rows"],
        "source_values_read": False,
        "candidate_values_read": False,
        "comparator_values_read": False,
        "historical_price_or_return_values_read": False,
        "provider_request_issued": False,
        "credential_loaded": False,
    }


def validate_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE_PATH.is_file():
        raise Campaign139CapacityError("Campaign139 capacity freeze is absent")
    record = load_json(IMPLEMENTATION_FREEZE_PATH)
    frozen = record.get("frozen_implementation") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign139_capacity_implementation_freeze"
        and record.get("status")
        == "capacity_only_runner_frozen_before_quality_listing_keys_or_candidate_signal_values"
        and frozen.get("runner_sha256") == file_sha256(Path(__file__).resolve())
        and frozen.get("test_sha256") == file_sha256(TEST_PATH)
        and frozen.get("source_manifest_sha256") == SOURCE_MANIFEST_SHA256
        and frozen.get("source_data_sha256") == SOURCE_DATA_SHA256
        and frozen.get("quality_key_helper_sha256") == QUALITY_KEY_HELPER_SHA256
        and frozen.get("expected_gate") == expected_gate()
        and frozen.get("output_columns") == list(OUTPUT_COLUMNS)
        and frozen.get("output_root") == relative(OUTPUT_ROOT)
        and boundary.get("quality_listing_key_values_read_before_freeze") is False
        and boundary.get("candidate_signal_values_read_before_freeze") is False
        and boundary.get("comparator_values_read") is False
        and boundary.get("historical_price_or_return_values_read") is False
    ):
        raise Campaign139CapacityError("Campaign139 capacity freeze changed")
    return record


def build_plan(output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    metadata = validate_static_metadata()
    freeze = validate_implementation_freeze()
    target = output_root.expanduser().resolve()
    blockers = ["capacity_output_already_exists"] if target.exists() else []
    return {
        "kind": "a_share_three_day_walkforward_campaign139_capacity_plan",
        "ready": not blockers,
        "blockers": blockers,
        "output_root": str(target),
        "capacity_gate": expected_gate(),
        "static_metadata": metadata,
        "implementation_freeze_status": freeze["status"],
        "quality_listing_key_values_read": False,
        "candidate_signal_values_read": False,
        "comparator_values_read": False,
        "historical_price_or_return_values_read": False,
        "stress_2024_2025_opened": False,
        "provider_request_issued": False,
        "credential_loaded": False,
    }


def _calendar() -> pd.DatetimeIndex:
    values = [
        line.strip()
        for line in CALENDAR_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    calendar = pd.DatetimeIndex(pd.to_datetime(values, errors="raise"))
    calendar = calendar[(calendar >= DEVELOPMENT_START) & (calendar <= DEVELOPMENT_END)]
    if not calendar.is_monotonic_increasing or calendar.has_duplicates:
        raise Campaign139CapacityError("development calendar is not sorted unique")
    return calendar


def expand_live_events(
    events: pd.DataFrame, calendar: pd.DatetimeIndex
) -> pd.DataFrame:
    required = {
        "effective_date",
        "event_expiry_date",
        "instrument",
        "provider",
        "report_date",
        "raw_surprise",
    }
    missing = sorted(required - set(events.columns))
    if missing:
        raise Campaign139CapacityError(f"event frame missing: {', '.join(missing)}")
    work = events.loc[:, sorted(required)].copy()
    for column in ("effective_date", "event_expiry_date", "report_date"):
        work[column] = pd.to_datetime(work[column], errors="coerce")
    work["raw_surprise"] = pd.to_numeric(work["raw_surprise"], errors="coerce")
    work = work.loc[
        work["effective_date"].notna()
        & work["event_expiry_date"].notna()
        & work["instrument"].notna()
        & np.isfinite(work["raw_surprise"].to_numpy(dtype=np.float64))
        & (work["effective_date"] <= DEVELOPMENT_END)
    ].copy()
    rows: list[pd.DataFrame] = []
    for date in calendar:
        live = work.loc[
            (work["effective_date"] <= date) & (work["event_expiry_date"] >= date)
        ].copy()
        if live.empty:
            continue
        live["trade_date"] = date
        rows.append(live)
    if not rows:
        return pd.DataFrame(
            columns=["trade_date", "symbol", "provider", "raw_surprise"]
        )
    expanded = pd.concat(rows, ignore_index=True)
    expanded = expanded.sort_values(
        ["trade_date", "instrument", "effective_date", "report_date"],
        kind="stable",
    ).drop_duplicates(["trade_date", "instrument"], keep="last")
    return expanded.rename(columns={"instrument": "symbol"})[
        ["trade_date", "symbol", "provider", "raw_surprise"]
    ].reset_index(drop=True)


def normalize_quality_listing_keys(keys: pd.DataFrame) -> pd.DataFrame:
    required = {"trade_date", "symbol"}
    missing = sorted(required - set(keys.columns))
    if missing:
        raise Campaign139CapacityError(
            f"quality/listing keys missing: {', '.join(missing)}"
        )
    result = keys.loc[:, ["trade_date", "symbol"]].copy()
    result["trade_date"] = pd.to_datetime(result["trade_date"], errors="coerce")
    result["symbol"] = result["symbol"].astype("string")
    result = result.loc[
        result["trade_date"].between(DEVELOPMENT_START, DEVELOPMENT_END)
        & result["symbol"].notna()
    ].drop_duplicates(["trade_date", "symbol"])
    return result.sort_values(["trade_date", "symbol"], kind="stable").reset_index(
        drop=True
    )


def candidate_signal_frame(
    events: pd.DataFrame,
    quality_listing_keys: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> pd.DataFrame:
    expanded = expand_live_events(events, calendar)
    keys = normalize_quality_listing_keys(quality_listing_keys)
    merged = keys.merge(
        expanded,
        on=["trade_date", "symbol"],
        how="inner",
        validate="one_to_one",
    )
    merged[formula.FACTOR_NAME] = merged.groupby("trade_date", sort=False)[
        "raw_surprise"
    ].rank(method="average", pct=True)
    merged = merged.loc[np.isfinite(merged[formula.FACTOR_NAME])].copy()
    return (
        merged.loc[:, list(OUTPUT_COLUMNS)]
        .sort_values(["trade_date", "symbol"], kind="stable")
        .reset_index(drop=True)
    )


def capacity_metrics(
    candidate: pd.DataFrame, calendar: pd.DatetimeIndex
) -> dict[str, Any]:
    grouped = candidate.groupby("trade_date", sort=True)
    names = grouped.size().reindex(calendar, fill_value=0)
    distinct = (
        grouped["raw_surprise"].nunique(dropna=True).reindex(calendar, fill_value=0)
    )
    grid_indexes = np.arange(
        0,
        max(len(calendar) - HOLDING_PERIOD_SESSIONS, 0),
        HOLDING_PERIOD_SESSIONS,
    )
    grid_dates = calendar[grid_indexes]
    qualified = names.loc[grid_dates].ge(MINIMUM_NAMES) & distinct.loc[grid_dates].ge(
        MINIMUM_DISTINCT_VALUES
    )
    qualified_dates = pd.DatetimeIndex(grid_dates[qualified.to_numpy(dtype=bool)])
    years = sorted(int(value) for value in qualified_dates.year.unique())
    year_counts = {
        str(year): int((qualified_dates.year == year).sum())
        for year in range(2019, 2024)
    }
    passed = bool(
        len(qualified_dates) >= MINIMUM_COHORTS and len(years) >= MINIMUM_YEARS
    )
    return {
        "quality_listing_candidate_signal_rows": int(len(candidate)),
        "calendar_sessions": int(len(calendar)),
        "sessions_with_at_least_one_candidate": int((names > 0).sum()),
        "maximum_names_in_one_session": int(names.max()),
        "maximum_distinct_values_in_one_session": int(distinct.max()),
        "non_overlapping_grid_dates": int(len(grid_dates)),
        "potential_complete_cohorts": int(len(qualified_dates)),
        "observed_cohort_years": years,
        "cohorts_by_year": year_counts,
        "capacity_gate_passed_before_comparator_values": passed,
        "gate": expected_gate(),
    }


def load_quality_listing_keys() -> pd.DataFrame:
    from scripts import (  # noqa: PLC0415
        a_share_three_day_walkforward_campaign117_no_return_audit as base,
    )

    return base._quality_listing_eligible_keys()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def run_capacity(output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    plan = build_plan(output_root)
    if not plan["ready"]:
        raise Campaign139CapacityError(f"capacity plan not ready: {plan['blockers']}")
    target = output_root.expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix="campaign139-capacity-", dir=target.parent)
    )
    try:
        events = pd.read_parquet(SOURCE_DATA_PATH)
        keys = load_quality_listing_keys()
        calendar = _calendar()
        candidate = candidate_signal_frame(events, keys, calendar)
        metrics = capacity_metrics(candidate, calendar)
        candidate_path = temporary / OUTPUT_CANDIDATE_NAME
        candidate.to_parquet(candidate_path, index=False)
        result = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign139_capacity_audit",
            "status": (
                "capacity_passed_ready_to_freeze_all_141_ordered_comparator_audit"
                if metrics["capacity_gate_passed_before_comparator_values"]
                else "capacity_failed_terminal_before_all_comparator_values"
            ),
            "recorded_at": datetime.now(UTC).isoformat(),
            "factor": formula.FACTOR_NAME,
            "direction": formula.SCORE_DIRECTION,
            "static_plan": plan,
            "candidate_snapshot": {
                "path": OUTPUT_CANDIDATE_NAME,
                "sha256": file_sha256(candidate_path),
                "rows": len(candidate),
                "columns": list(candidate.columns),
            },
            "capacity": metrics,
            "numeric_comparator_count_read": 0,
            "comparator_values_read": False,
            "historical_daily_price_or_forward_return_values_read": False,
            "stress_2024_2025_opened": False,
            "training_or_model_fitting_performed": False,
            "provider_request_issued": False,
            "credential_loaded": False,
            "candidate49_historical_backfill_performed": False,
            "candidate49_ledgers_changed": False,
            "current_scoring_selection_sizing_positions_or_orders_performed": False,
            "investment_advice": False,
        }
        _atomic_json(temporary / OUTPUT_AUDIT_NAME, result)
        if target.exists():
            raise Campaign139CapacityError("capacity output appeared during run")
        temporary.replace(target)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return load_json(target / OUTPUT_AUDIT_NAME)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    run = subparsers.add_parser("run")
    run.add_argument("--confirm-capacity-audit", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "plan":
        plan = build_plan()
        print(json.dumps(plan, ensure_ascii=False, sort_keys=True, allow_nan=False))
        return 0 if plan["ready"] else 2
    if not args.confirm_capacity_audit:
        raise Campaign139CapacityError("run requires --confirm-capacity-audit")
    result = run_capacity()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
