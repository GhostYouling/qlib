#!/usr/bin/env python3
"""Build Campaign139's frozen local forecast-realization event snapshot."""

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
SOURCE_RANGE_FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_139_single_rowgroup_source_range_failure_20260814.json"
)
SOURCE_RANGE_FAILURE_SHA256 = (
    "a4f54925a33c6b6c04c28e272750437302326a4f18d4458f821da0318169a7a0"
)
FORMULA_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_139_formula_implementation_freeze_20260814.json"
)
FORMULA_FREEZE_SHA256 = (
    "82a16f747a6204641430bb1cc187469b175e9156d708c1c8bf14217604c1703a"
)
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_139_source_implementation_freeze_20260814.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign139_source.py"
)

FORECAST_PATH = (
    REPO_ROOT / "data/raw/a_share/fundamentals/performance_forecasts.parquet"
)
FORECAST_SHA256 = "48bc11ea6749a590fcc260f6a5728e853f59f228f6cef7c5b0183f206895d734"
FORECAST_MANIFEST_PATH = REPO_ROOT / "data/metadata/performance_forecasts_manifest.json"
FORECAST_MANIFEST_SHA256 = (
    "d824bf8194b871fc21ce66cab80f1f9158814fff0e9a5d77a2cfbaec967e562c"
)
QUALITY_PATH = REPO_ROOT / "data/raw/a_share/fundamentals/quarterly_quality.parquet"
QUALITY_SHA256 = "3ac901a97928d2ed81ac72e3eaac9bdc148d36cf67b6abe70223699235ef059f"
QUALITY_MANIFEST_PATH = REPO_ROOT / "data/metadata/quarterly_quality_manifest.json"
QUALITY_MANIFEST_SHA256 = (
    "e3cf654babe37a82393c5530696bc1cc242b736cb88e1947b8444b638125ba8c"
)
CALENDAR_PATH = REPO_ROOT / "data/qlib/cn_a_share/calendars/day.txt"
CALENDAR_SHA256 = "fda506597d26bcec953cdc0882042a5046ec1587db60490e16a01627fd43f53a"
CANDIDATE49_SIGNAL_LEDGER = (
    REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
CANDIDATE49_SIGNAL_SHA256 = (
    "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
)
CANDIDATE49_EXECUTION_LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
CANDIDATE49_EXECUTION_SHA256 = (
    "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
)

FORECAST_COLUMNS = (
    "instrument",
    "report_date",
    "announcement_date",
    "forecast_profit_yoy",
)
QUALITY_COLUMNS = (
    "instrument",
    "report_date",
    "announcement_date",
    "profit_yoy",
)
OUTPUT_COLUMNS = (
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
)
OUTPUT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_139/source_snapshot_v1"
)
OUTPUT_DATA_NAME = "campaign139_forecast_realization_events.parquet"
OUTPUT_MANIFEST_NAME = "snapshot_manifest.json"
MIN_REPORT_DATE = pd.Timestamp("2019-03-31")
MAX_REPORT_DATE = pd.Timestamp("2025-12-31")
MAX_REALIZED_ANNOUNCEMENT = pd.Timestamp("2025-12-31")
MAX_EFFECTIVE_DATE = pd.Timestamp("2025-12-31")


class Campaign139SourceError(RuntimeError):
    """Fail closed when Campaign139 source semantics or bindings change."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_file(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or file_sha256(path) != expected:
        raise Campaign139SourceError(f"Campaign139 {label} binding changed")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Campaign139SourceError(f"expected JSON object: {path}")
    return value


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def validate_protocols() -> dict[str, Any]:
    try:
        v1 = formula.load_protocol()
    except formula.Campaign139FormulaError as exc:
        raise Campaign139SourceError(str(exc)) from exc
    require_file(PROTOCOL_V2_PATH, PROTOCOL_V2_SHA256, "v2 preregistration")
    require_file(PROTOCOL_V3_PATH, PROTOCOL_V3_SHA256, "v3 preregistration")
    require_file(
        SOURCE_RANGE_FAILURE_PATH,
        SOURCE_RANGE_FAILURE_SHA256,
        "single-rowgroup failure record",
    )
    v2 = load_json(PROTOCOL_V2_PATH)
    v3 = load_json(PROTOCOL_V3_PATH)
    effective = v2.get("effective_source_decode_contract") or {}
    unchanged = v2.get("unchanged_contract") or {}
    boundary = v2.get("research_boundary") or {}
    if not (
        v2.get("kind")
        == "a_share_three_day_walkforward_campaign139_no_return_preregistration_additive_correction"
        and v2.get("status")
        == "effective_v2_frozen_before_source_values_for_single_rowgroup_decode_and_date_filter_semantics"
        and (v2.get("supersedes_without_rewriting") or {}).get("sha256")
        == PROTOCOL_V1_SHA256
        and unchanged.get("factor") == formula.FACTOR_NAME
        and unchanged.get("direction") == formula.SCORE_DIRECTION
        and unchanged.get("raw_formula") == "profit_yoy - forecast_profit_yoy"
        and unchanged.get("event_age_calendar_days") == 3
        and unchanged.get("candidate_count") == 1
        and unchanged.get("numeric_comparator_count") == 141
        and unchanged.get("numeric_comparator_order_sha256")
        == "ec1aebcb939ad516c58037a36a4aaadd4ad8b2abbd3c884705895c58da85a2ee"
        and effective.get("historical_price_or_forward_return_fields_allowed") == []
        and effective.get("provider_request_allowed") is False
        and effective.get("credential_required") is False
        and boundary.get("parquet_source_column_values_read_before_v2") is False
        and boundary.get("candidate_or_comparator_values_read_before_v2") is False
        and boundary.get("historical_price_or_return_values_read") is False
        and boundary.get("stress_2024_2025_opened") is False
        and v3.get("kind")
        == "a_share_three_day_walkforward_campaign139_no_return_preregistration_binding_correction"
        and v3.get("status")
        == "effective_v3_failure_binding_completed_before_source_values_without_semantic_change"
        and (v3.get("supersedes_without_rewriting") or {}).get("sha256")
        == PROTOCOL_V2_SHA256
        and (v3.get("corrected_binding") or {})
        .get("effective_evidence", {})
        .get("sha256")
        == SOURCE_RANGE_FAILURE_SHA256
        and v3.get("semantic_change") is False
    ):
        raise Campaign139SourceError("Campaign139 effective preregistration changed")
    return {
        "v1_status": v1["status"],
        "v2_status": v2["status"],
        "v3_status": v3["status"],
    }


def validate_source_metadata() -> dict[str, Any]:
    for path, expected, label in (
        (FORECAST_PATH, FORECAST_SHA256, "forecast source"),
        (FORECAST_MANIFEST_PATH, FORECAST_MANIFEST_SHA256, "forecast manifest"),
        (QUALITY_PATH, QUALITY_SHA256, "quality source"),
        (QUALITY_MANIFEST_PATH, QUALITY_MANIFEST_SHA256, "quality manifest"),
        (CALENDAR_PATH, CALENDAR_SHA256, "calendar"),
        (FORMULA_FREEZE_PATH, FORMULA_FREEZE_SHA256, "formula freeze"),
        (
            CANDIDATE49_SIGNAL_LEDGER,
            CANDIDATE49_SIGNAL_SHA256,
            "Candidate49 signal ledger",
        ),
        (
            CANDIDATE49_EXECUTION_LEDGER,
            CANDIDATE49_EXECUTION_SHA256,
            "Candidate49 execution ledger",
        ),
    ):
        require_file(path, expected, label)
    forecast_schema = pq.read_schema(FORECAST_PATH).names
    quality_schema = pq.read_schema(QUALITY_PATH).names
    if not set(FORECAST_COLUMNS).issubset(forecast_schema):
        raise Campaign139SourceError("forecast source projection changed")
    if not set(QUALITY_COLUMNS).issubset(quality_schema):
        raise Campaign139SourceError("quality source projection changed")
    forecast_metadata = pq.ParquetFile(FORECAST_PATH).metadata
    quality_metadata = pq.ParquetFile(QUALITY_PATH).metadata
    if not (
        forecast_metadata.num_rows == 42206
        and forecast_metadata.num_row_groups == 1
        and quality_metadata.num_rows == 143776
        and quality_metadata.num_row_groups == 1
    ):
        raise Campaign139SourceError("source row-group metadata changed")
    return {
        "forecast_schema": forecast_schema,
        "quality_schema": quality_schema,
        "forecast_rows": forecast_metadata.num_rows,
        "quality_rows": quality_metadata.num_rows,
        "forecast_row_groups": forecast_metadata.num_row_groups,
        "quality_row_groups": quality_metadata.num_row_groups,
        "source_values_read": False,
        "historical_price_or_return_values_read": False,
        "provider_request_issued": False,
        "credential_loaded": False,
    }


def validate_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE_PATH.is_file():
        raise Campaign139SourceError(
            "Campaign139 source implementation freeze is absent"
        )
    record = load_json(IMPLEMENTATION_FREEZE_PATH)
    frozen = record.get("frozen_implementation") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign139_source_implementation_freeze"
        and record.get("status")
        == "source_builder_frozen_before_campaign139_source_column_values"
        and frozen.get("runner_sha256") == file_sha256(Path(__file__).resolve())
        and frozen.get("test_sha256") == file_sha256(TEST_PATH)
        and frozen.get("protocol_v1_sha256") == PROTOCOL_V1_SHA256
        and frozen.get("protocol_v2_sha256") == PROTOCOL_V2_SHA256
        and frozen.get("protocol_v3_sha256") == PROTOCOL_V3_SHA256
        and frozen.get("formula_sha256")
        == file_sha256(Path(formula.__file__).resolve())
        and frozen.get("forecast_source_sha256") == FORECAST_SHA256
        and frozen.get("quality_source_sha256") == QUALITY_SHA256
        and frozen.get("calendar_sha256") == CALENDAR_SHA256
        and frozen.get("forecast_projection") == list(FORECAST_COLUMNS)
        and frozen.get("quality_projection") == list(QUALITY_COLUMNS)
        and frozen.get("output_columns") == list(OUTPUT_COLUMNS)
        and frozen.get("output_root") == relative(OUTPUT_ROOT)
        and boundary.get("source_column_values_read_before_freeze") is False
        and boundary.get("candidate_or_comparator_values_read_before_freeze") is False
        and boundary.get("historical_price_or_return_values_read") is False
    ):
        raise Campaign139SourceError("Campaign139 source implementation freeze changed")
    return record


def validate_static_bindings() -> dict[str, Any]:
    protocols = validate_protocols()
    metadata = validate_source_metadata()
    freeze = validate_implementation_freeze()
    return {
        "protocols": protocols,
        "source_metadata": metadata,
        "implementation_freeze_status": freeze["status"],
        "source_values_read": False,
        "candidate_values_read": False,
        "comparator_values_read": False,
        "historical_price_or_return_values_read": False,
        "provider_request_issued": False,
        "credential_loaded": False,
    }


def build_plan(output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    bindings = validate_static_bindings()
    target = output_root.expanduser().resolve()
    blockers = ["source_snapshot_output_already_exists"] if target.exists() else []
    return {
        "kind": "a_share_three_day_walkforward_campaign139_source_plan",
        "ready": not blockers,
        "blockers": blockers,
        "output_root": str(target),
        "static_bindings": bindings,
        "source_values_read": False,
        "candidate_values_read": False,
        "comparator_values_read": False,
        "historical_price_or_return_values_read": False,
        "stress_2024_2025_opened": False,
        "provider_request_issued": False,
        "credential_loaded": False,
    }


def _normalize_source(
    frame: pd.DataFrame,
    *,
    value_column: str,
    expected_columns: tuple[str, ...],
) -> pd.DataFrame:
    missing = sorted(set(expected_columns) - set(frame.columns))
    if missing:
        raise Campaign139SourceError(f"source is missing columns: {', '.join(missing)}")
    work = frame.loc[:, list(expected_columns)].copy()
    work["instrument"] = work["instrument"].astype("string")
    work["report_date"] = pd.to_datetime(work["report_date"], errors="coerce")
    work["announcement_date"] = pd.to_datetime(
        work["announcement_date"], errors="coerce"
    )
    work[value_column] = pd.to_numeric(work[value_column], errors="coerce")
    standard_quarter = (
        work["report_date"].dt.month.isin([3, 6, 9, 12])
        & work["report_date"].dt.is_month_end
    )
    work = work.loc[
        work["instrument"].notna()
        & work["report_date"].between(MIN_REPORT_DATE, MAX_REPORT_DATE)
        & standard_quarter
        & work["announcement_date"].notna()
    ].copy()
    return work.reset_index(drop=True)


def _collapse_realized(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    work = _normalize_source(
        frame, value_column="profit_yoy", expected_columns=QUALITY_COLUMNS
    )
    before_date = len(work)
    work = work.loc[work["announcement_date"] <= MAX_REALIZED_ANNOUNCEMENT].copy()
    exact = work.drop_duplicates(list(QUALITY_COLUMNS), keep="first")
    grouped = exact.groupby(["instrument", "report_date"], dropna=False).size()
    conflicts = grouped[grouped > 1]
    if len(conflicts):
        raise Campaign139SourceError("conflicting realized event key")
    result = exact.drop_duplicates(["instrument", "report_date"], keep="first")
    return result.reset_index(drop=True), {
        "normalized_realized_rows": before_date,
        "realized_rows_through_2025": len(work),
        "exact_realized_duplicates_collapsed": len(work) - len(exact),
        "unique_realized_keys": len(result),
    }


def _collapse_forecasts(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    work = _normalize_source(
        frame,
        value_column="forecast_profit_yoy",
        expected_columns=FORECAST_COLUMNS,
    )
    exact = work.drop_duplicates(list(FORECAST_COLUMNS), keep="first")
    grouped = exact.groupby(
        ["instrument", "report_date", "announcement_date"], dropna=False
    )["forecast_profit_yoy"].nunique(dropna=False)
    conflicts = grouped[grouped > 1]
    if len(conflicts):
        raise Campaign139SourceError("conflicting forecast event key")
    return exact.reset_index(drop=True), {
        "normalized_forecast_rows": len(work),
        "exact_forecast_duplicates_collapsed": len(work) - len(exact),
        "unique_forecast_event_rows": len(exact),
    }


def _calendar_values(calendar: pd.DatetimeIndex) -> np.ndarray:
    if not calendar.is_monotonic_increasing or calendar.has_duplicates:
        raise Campaign139SourceError("accepted calendar must be sorted and unique")
    return calendar.to_numpy(dtype="datetime64[ns]")


def _first_session_strictly_after(
    dates: pd.Series, calendar: pd.DatetimeIndex
) -> pd.Series:
    values = _calendar_values(calendar)
    requested = pd.to_datetime(dates, errors="coerce").to_numpy(dtype="datetime64[ns]")
    indexes = np.searchsorted(values, requested, side="right")
    result = np.full(len(requested), np.datetime64("NaT"), dtype="datetime64[ns]")
    valid = (~pd.isna(requested)) & (indexes < len(values))
    result[valid] = values[indexes[valid]]
    return pd.Series(pd.to_datetime(result), index=dates.index)


def build_event_frame(
    forecasts: pd.DataFrame,
    realized: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Create the exact joined event frame from already loaded bound projections."""

    realized_clean, realized_quality = _collapse_realized(realized)
    forecast_clean, forecast_quality = _collapse_forecasts(forecasts)
    joined = realized_clean.rename(
        columns={
            "announcement_date": "realized_announcement_date",
            "profit_yoy": "realized_profit_yoy",
        }
    ).merge(
        forecast_clean.rename(
            columns={"announcement_date": "forecast_announcement_date"}
        ),
        on=["instrument", "report_date"],
        how="left",
        validate="one_to_many",
    )
    finite = np.isfinite(
        joined["realized_profit_yoy"].to_numpy(dtype=np.float64)
    ) & np.isfinite(joined["forecast_profit_yoy"].to_numpy(dtype=np.float64))
    prior = joined["forecast_announcement_date"] < joined["realized_announcement_date"]
    eligible_pairs = joined.loc[finite & prior.fillna(False)].copy()
    eligible_pairs = eligible_pairs.sort_values(
        [
            "instrument",
            "report_date",
            "forecast_announcement_date",
        ],
        kind="stable",
    )
    latest = eligible_pairs.drop_duplicates(
        ["instrument", "report_date"], keep="last"
    ).reset_index(drop=True)
    same_key = np.ones(len(latest), dtype=bool)
    valid = np.ones(len(latest), dtype=bool)
    raw, formula_eligible, formula_quality = formula.compute_raw_surprise(
        latest["realized_profit_yoy"].to_numpy(dtype=np.float64),
        latest["forecast_profit_yoy"].to_numpy(dtype=np.float64),
        same_key,
        valid,
        valid,
    )
    if not formula_eligible.all():
        raise Campaign139SourceError("clean latest event unexpectedly failed formula")
    latest["raw_surprise"] = raw
    latest["effective_date"] = _first_session_strictly_after(
        latest["realized_announcement_date"], calendar
    )
    latest = latest.loc[
        latest["effective_date"].notna()
        & (latest["effective_date"] <= MAX_EFFECTIVE_DATE)
    ].copy()
    latest["event_expiry_date"] = latest["effective_date"] + pd.Timedelta(days=3)
    latest["provider"] = "eastmoney"
    output = latest.rename(columns={"forecast_profit_yoy": "forecast_profit_yoy"}).loc[
        :, list(OUTPUT_COLUMNS)
    ]
    output = output.sort_values(
        ["effective_date", "instrument", "report_date"], kind="stable"
    ).reset_index(drop=True)
    if output.duplicated(["instrument", "report_date"]).any():
        raise Campaign139SourceError("duplicate output realized key")
    if not (
        np.isfinite(output["raw_surprise"].to_numpy(dtype=np.float64)).all()
        and (
            output["forecast_announcement_date"] < output["realized_announcement_date"]
        ).all()
        and (output["effective_date"] > output["realized_announcement_date"]).all()
        and (output["effective_date"] <= MAX_EFFECTIVE_DATE).all()
    ):
        raise Campaign139SourceError("output event semantics changed")
    quality: dict[str, Any] = {
        **realized_quality,
        **forecast_quality,
        "joined_candidate_pairs": len(joined),
        "finite_strictly_prior_pairs": len(eligible_pairs),
        "latest_prior_matched_events_before_calendar": len(latest),
        "published_events": len(output),
        "formula_quality": formula_quality,
    }
    return output, quality


def _read_calendar() -> pd.DatetimeIndex:
    values = [
        line.strip()
        for line in CALENDAR_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    calendar = pd.DatetimeIndex(pd.to_datetime(values, errors="raise"))
    return calendar.sort_values()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def run_source_build(output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    plan = build_plan(output_root)
    if not plan["ready"]:
        raise Campaign139SourceError(f"source plan not ready: {plan['blockers']}")
    target = output_root.expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="campaign139-source-", dir=target.parent))
    try:
        forecasts = pd.read_parquet(FORECAST_PATH, columns=list(FORECAST_COLUMNS))
        realized = pd.read_parquet(QUALITY_PATH, columns=list(QUALITY_COLUMNS))
        events, quality = build_event_frame(forecasts, realized, _read_calendar())
        data_path = temporary / OUTPUT_DATA_NAME
        events.to_parquet(data_path, index=False)
        manifest = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign139_source_snapshot",
            "status": "immutable_local_event_snapshot_built_before_capacity_comparators_prices_or_returns",
            "created_at": datetime.now(UTC).isoformat(),
            "factor": formula.FACTOR_NAME,
            "direction": formula.SCORE_DIRECTION,
            "protocol_v1_sha256": PROTOCOL_V1_SHA256,
            "protocol_v2_sha256": PROTOCOL_V2_SHA256,
            "protocol_v3_sha256": PROTOCOL_V3_SHA256,
            "runner_sha256": file_sha256(Path(__file__).resolve()),
            "formula_sha256": file_sha256(Path(formula.__file__).resolve()),
            "source_bindings": {
                "forecast_sha256": FORECAST_SHA256,
                "quality_sha256": QUALITY_SHA256,
                "calendar_sha256": CALENDAR_SHA256,
            },
            "output": {
                "path": OUTPUT_DATA_NAME,
                "sha256": file_sha256(data_path),
                "rows": len(events),
                "columns": list(events.columns),
                "minimum_effective_date": (
                    events["effective_date"].min().date().isoformat()
                    if len(events)
                    else None
                ),
                "maximum_effective_date": (
                    events["effective_date"].max().date().isoformat()
                    if len(events)
                    else None
                ),
            },
            "quality": quality,
            "research_boundary": {
                "source_projected_columns_decoded": {
                    "forecast": list(FORECAST_COLUMNS),
                    "quality": list(QUALITY_COLUMNS),
                },
                "post_2025_rows_excluded_before_candidate_matching": True,
                "candidate_event_values_computed": True,
                "comparator_values_read": False,
                "historical_daily_price_or_forward_return_values_read": False,
                "stress_2024_2025_opened": False,
                "provider_request_issued": False,
                "credential_loaded": False,
                "candidate49_historical_backfill_performed": False,
                "candidate49_ledgers_changed": False,
                "current_scoring_selection_sizing_positions_or_orders_performed": False,
                "investment_advice": False,
            },
        }
        _atomic_json(temporary / OUTPUT_MANIFEST_NAME, manifest)
        if target.exists():
            raise Campaign139SourceError("source output appeared during build")
        temporary.replace(target)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return load_json(target / OUTPUT_MANIFEST_NAME)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    run = subparsers.add_parser("run")
    run.add_argument("--confirm-source-build", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "plan":
        plan = build_plan()
        print(json.dumps(plan, ensure_ascii=False, sort_keys=True, allow_nan=False))
        return 0 if plan["ready"] else 2
    if not args.confirm_source_build:
        raise Campaign139SourceError("run requires --confirm-source-build")
    result = run_source_build()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
