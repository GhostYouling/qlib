#!/usr/bin/env python3
"""Build Campaign075's accepted-instrument session-youth snapshot.

The builder projects only stock-day identity from the immutable Campaign074
snapshot and combines it with the accepted instrument intervals and calendar.
It never reads Campaign074 factor values, market fields, returns, or Candidate49
outcomes.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow as pa

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign074_features as c74


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = c74.DEFAULT_DATA_ROOT
DEFAULT_PROTOCOL = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_075_no_return_preregistration.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_075_feature_implementation_freeze_20260806.json"
)
DEFAULT_CALENDAR = REPO_ROOT / "data/qlib/cn_a_share/calendars/day.txt"
DEFAULT_INSTRUMENTS = REPO_ROOT / "data/qlib/cn_a_share/instruments/all.txt"
C74_MANIFEST_PATH = c74.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"

FACTOR_NAME = "accepted_instrument_session_youth_20s"
FACTOR_FORMULA = (
    "negative inclusive accepted-session count from accepted instrument start "
    "through signal date, defined only at age at least 20"
)
PROTOCOL_SHA256 = "fa2100154a66ec2f4037d86c6481a676e7c8fa2839ea5b55eec4c578e21b31b3"
MECHANISM_AUDIT_SHA256 = "583831e57554ae7fe0c3de434a01b029ceb5ac7df8c70bd4d1ccd0cb90c4b181"
NUMERIC_POLICY_SHA256 = "2b01d476308a1a286825a2727a26eefb1aef20706a132d7e6cb3ea4664fa0d48"
CALENDAR_SHA256 = "fda506597d26bcec953cdc0882042a5046ec1587db60490e16a01627fd43f53a"
INSTRUMENTS_SHA256 = "cdded13c831b78045f4cfe80ba5d9a49f82152c615fef4267d00f992e7f53762"
C74_MANIFEST_SHA256 = "5a993ce8b71c541a0b2d2402627d5f2b7f562cf1266bebcafe0606945086a3cd"
C74_DATASET_SHA256 = "d4fbb9eb8135674df16a50c96b5817f63e6461e99ee48df96537cd8ed930a4b5"
EXPECTED_PARTITIONS = 33_015
EXPECTED_ROWS = 7_724_498
FULL_DEFINITION_COUNT = 106
FULL_DEFINITION_ORDER_SHA256 = (
    "9e36bbe2532e09294f2c677615c6245609abdb94c44557ee776e040c9f270b0c"
)
COMPARISON_COUNT = 105
COMPARISON_ORDER_SHA256 = (
    "533f22783f42d7d00b51fcceda879a2881e1a484f4d70fc0f2ecb5a0210e6fcc"
)
MINIMUM_AGE_SESSIONS = 20
IDENTITY_COLUMNS = ("trade_date", "symbol", "provider")
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign075_feature_library_v1"
)
C74_FACTOR = c74.FACTOR_NAME


class Campaign075FeatureError(RuntimeError):
    """Fail-closed Campaign075 feature error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _comparison_order_digest(items: Iterable[dict[str, Any]]) -> str:
    return _json_digest(
        [[str(item["name"]), str(item["score_direction"])] for item in items]
    )


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign075FeatureError(f"Campaign075 {label} changed: {path}")


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = c74.reconstruct_comparisons()
    items.append({"name": C74_FACTOR, "score_direction": "higher"})
    if (
        len(items) != COMPARISON_COUNT
        or _comparison_order_digest(items) != COMPARISON_ORDER_SHA256
    ):
        raise Campaign075FeatureError("Campaign075 numeric comparison order changed")
    return items


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = c74.reconstruct_complete_definitions()
    items.append({"name": C74_FACTOR, "score_direction": "higher"})
    if (
        len(items) != FULL_DEFINITION_COUNT
        or _comparison_order_digest(items) != FULL_DEFINITION_ORDER_SHA256
    ):
        raise Campaign075FeatureError("Campaign075 complete definition order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    _require(path, PROTOCOL_SHA256, "protocol")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign075FeatureError("Campaign075 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    chain = spec.get("source_chain") or {}
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    unique = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("version") == 1
        and spec.get("kind")
        == "a_share_three_day_walkforward_campaign075_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign075_instrument_source_candidate_comparison_daily_price_or_return_values"
        and (chain.get("numeric_comparator_policy_v10") or {}).get("sha256")
        == NUMERIC_POLICY_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and tuple(candidate.get("identity_projection") or ()) == IDENTITY_COLUMNS
        and candidate.get("minimum_age_sessions") == MINIMUM_AGE_SESSIONS
        and candidate.get("age_clock")
        == "accepted local market sessions, inclusive of the accepted instrument start and signal date"
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and unique.get("complete_definition_count") == FULL_DEFINITION_COUNT
        and unique.get("complete_definition_order_sha256")
        == FULL_DEFINITION_ORDER_SHA256
        and unique.get("numeric_comparator_count") == COMPARISON_COUNT
        and unique.get("numeric_comparator_order_sha256") == COMPARISON_ORDER_SHA256
        and unique.get("all_105_numeric_comparators_must_pass") is True
        and unique.get("maximum_allowed_absolute_median_daily_rank_correlation")
        == 0.8
        and unique.get("minimum_pairwise_names_per_session") == 50
        and unique.get("minimum_pairwise_sessions_per_comparison") == 100
        and len(reconstruct_comparisons()) == COMPARISON_COUNT
        and len(reconstruct_complete_definitions()) == FULL_DEFINITION_COUNT
        and finite.get("trial_id")
        == "wf075_accepted_instrument_session_youth_20s_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("expected_trial_count") == 1
        and boundary.get("campaign074_factor_values_read_for_candidate_materialization")
        is False
        and boundary.get("comparison_values_read_before_coverage_pass") is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign075FeatureError("Campaign075 protocol semantics changed")
    return spec


def load_calendar(path: Path = DEFAULT_CALENDAR) -> pd.DatetimeIndex:
    dates = pd.to_datetime(
        [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()],
        errors="raise",
    )
    calendar = pd.DatetimeIndex(dates).normalize()
    if calendar.empty or calendar.has_duplicates or not calendar.is_monotonic_increasing:
        raise Campaign075FeatureError("accepted calendar semantics changed")
    return calendar


def parse_instrument_intervals(path: Path = DEFAULT_INSTRUMENTS) -> pd.DataFrame:
    frame = pd.read_csv(
        path,
        sep="\t",
        header=None,
        names=["instrument", "accepted_start", "accepted_end"],
        dtype={"instrument": "string"},
    )
    if frame.shape[1] != 3 or frame.empty:
        raise Campaign075FeatureError("accepted instrument interval schema changed")
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    frame["accepted_start"] = pd.to_datetime(
        frame["accepted_start"], errors="coerce"
    ).dt.normalize()
    frame["accepted_end"] = pd.to_datetime(
        frame["accepted_end"], errors="coerce"
    ).dt.normalize()
    if (
        frame.isna().any().any()
        or frame["instrument"].eq("").any()
        or frame.duplicated("instrument").any()
        or frame["accepted_start"].gt(frame["accepted_end"]).any()
    ):
        raise Campaign075FeatureError("accepted instrument interval identities changed")
    return frame.sort_values("instrument", kind="stable").reset_index(drop=True)


def compute_session_youth(
    identity: pd.DataFrame,
    *,
    accepted_start: pd.Timestamp,
    accepted_end: pd.Timestamp,
    calendar: pd.DatetimeIndex,
    symbol: str,
) -> pd.DataFrame:
    if tuple(identity.columns) != IDENTITY_COLUMNS:
        raise Campaign075FeatureError(f"identity projection changed for {symbol}")
    work = identity.copy()
    work["trade_date"] = pd.to_datetime(work["trade_date"], errors="coerce").dt.normalize()
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    if work.empty:
        return empty_output_frame()
    if (
        work["trade_date"].isna().any()
        or work.duplicated(["trade_date", "symbol"]).any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
    ):
        raise Campaign075FeatureError(f"identity semantics changed for {symbol}")
    start = pd.Timestamp(accepted_start).normalize()
    end = pd.Timestamp(accepted_end).normalize()
    calendar_values = calendar.to_numpy(dtype="datetime64[ns]")
    boundary_values = np.asarray([start, end], dtype="datetime64[ns]")
    boundary_positions = np.searchsorted(calendar_values, boundary_values)
    if (
        (boundary_positions >= len(calendar_values)).any()
        or not np.array_equal(calendar_values[boundary_positions], boundary_values)
        or start > end
    ):
        raise Campaign075FeatureError(f"instrument boundaries leave calendar for {symbol}")
    dates = work["trade_date"].to_numpy(dtype="datetime64[ns]")
    positions = np.searchsorted(calendar_values, dates)
    if (
        (positions >= len(calendar_values)).any()
        or not np.array_equal(calendar_values[positions], dates)
        or (dates < np.datetime64(start)).any()
        or (dates > np.datetime64(end)).any()
    ):
        raise Campaign075FeatureError(f"identity dates leave interval for {symbol}")
    ages = positions - int(boundary_positions[0]) + 1
    eligible = ages >= MINIMUM_AGE_SESSIONS
    values = np.full(len(work), np.nan, dtype=np.float64)
    values[eligible] = -ages[eligible].astype(np.float64)
    work[FACTOR_NAME] = values
    work[f"{FACTOR_NAME}_eligible"] = eligible
    return work.loc[:, OUTPUT_COLUMNS]


def empty_output_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="object"),
            "provider": pd.Series(dtype="object"),
            FACTOR_NAME: pd.Series(dtype="float64"),
            f"{FACTOR_NAME}_eligible": pd.Series(dtype="bool"),
        }
    ).loc[:, OUTPUT_COLUMNS]


def validate_value_semantics(frame: pd.DataFrame) -> tuple[int, int]:
    if tuple(frame.columns) != OUTPUT_COLUMNS:
        raise Campaign075FeatureError("Campaign075 output columns changed")
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"].astype(bool)
    selected = values[eligible].to_numpy(dtype=np.float64)
    if (
        values[eligible].isna().any()
        or values[~eligible].notna().any()
        or (selected > -float(MINIMUM_AGE_SESSIONS)).any()
        or not np.equal(selected, np.floor(selected)).all()
    ):
        raise Campaign075FeatureError("Campaign075 value semantics changed")
    return int(len(frame)), int(eligible.sum())


def _frame_sha256(frame: pd.DataFrame) -> str:
    sink = pa.BufferOutputStream()
    table = pa.Table.from_pandas(frame, preserve_index=False)
    with pa.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    return hashlib.sha256(sink.getvalue().to_pybytes()).hexdigest()


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived/a_share/rich/tushare/minute_walkforward_campaign075_feature_library"
        / OUTPUT_RUN_ID
    )


def _validate_implementation_freeze() -> dict[str, Any]:
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign075FeatureError("Campaign075 implementation freeze is absent")
    freeze = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    runner = freeze.get("feature_runner") or {}
    tests = freeze.get("tests") or {}
    test_path = REPO_ROOT / str(tests.get("path") or "")
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign075_feature_implementation_freeze"
        and freeze.get("status")
        == "frozen_before_campaign075_instrument_source_or_candidate_values"
        and runner.get("path")
        == "scripts/a_share_three_day_walkforward_campaign075_features.py"
        and runner.get("sha256") == _sha256(Path(__file__).resolve())
        and test_path.is_file()
        and tests.get("sha256") == _sha256(test_path)
        and (freeze.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (freeze.get("mechanism_overlap_audit") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and (freeze.get("research_boundary") or {}).get(
            "accepted_instrument_rows_read_before_freeze"
        )
        is False
        and (freeze.get("research_boundary") or {}).get(
            "candidate_values_read_before_freeze"
        )
        is False
    ):
        raise Campaign075FeatureError("Campaign075 implementation freeze changed")
    return freeze


def _require_inputs() -> tuple[dict[str, Any], pd.DatetimeIndex, pd.DataFrame, dict[str, Any]]:
    load_protocol()
    freeze = _validate_implementation_freeze()
    for path, expected, label in (
        (C74_MANIFEST_PATH, C74_MANIFEST_SHA256, "Campaign074 manifest"),
        (DEFAULT_CALENDAR, CALENDAR_SHA256, "calendar"),
        (DEFAULT_INSTRUMENTS, INSTRUMENTS_SHA256, "instrument intervals"),
    ):
        _require(path, expected, label)
    manifest = json.loads(C74_MANIFEST_PATH.read_text(encoding="utf-8"))
    if not (
        manifest.get("dataset_sha256") == C74_DATASET_SHA256
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and manifest.get("rows") == EXPECTED_ROWS
        and len(manifest.get("files") or []) == EXPECTED_PARTITIONS
    ):
        raise Campaign075FeatureError("Campaign074 identity source changed")
    calendar = load_calendar()
    intervals = parse_instrument_intervals()
    return manifest, calendar, intervals, freeze


def _load_partition(
    index: int,
    item: dict[str, Any],
    interval: tuple[pd.Timestamp, pd.Timestamp],
    calendar: pd.DatetimeIndex,
) -> tuple[int, pd.DataFrame]:
    symbol = str(item["symbol"]).upper()
    path = Path(str(item["path"])).expanduser().resolve()
    frame = pd.read_parquet(path, columns=list(IDENTITY_COLUMNS))
    out = compute_session_youth(
        frame,
        accepted_start=interval[0],
        accepted_end=interval[1],
        calendar=calendar,
        symbol=symbol,
    )
    return index, out


def build_snapshot(*, data_root: Path, workers: int = 4) -> Path:
    data_root = data_root.expanduser().resolve()
    if data_root != DEFAULT_DATA_ROOT.resolve():
        raise Campaign075FeatureError("Campaign075 data root changed")
    manifest, calendar, intervals, freeze = _require_inputs()
    interval_map = {
        str(row.instrument).upper(): (row.accepted_start, row.accepted_end)
        for row in intervals.itertuples(index=False)
    }
    files = list(manifest["files"])
    missing_symbols = sorted(
        {str(item["symbol"]).upper() for item in files} - set(interval_map)
    )
    if missing_symbols:
        raise Campaign075FeatureError(
            f"Campaign075 instrument intervals missing {len(missing_symbols)} symbols"
        )
    root = output_root(data_root)
    manifest_path = root / "snapshot_manifest.json"
    if manifest_path.exists():
        raise Campaign075FeatureError(
            "Campaign075 snapshot already exists; verify it instead of rebuilding"
        )
    records: list[dict[str, Any] | None] = [None] * len(files)
    totals = {"eligible": 0, "missing": 0}

    def publish(index: int, out: pd.DataFrame) -> None:
        item = files[index]
        out = out.sort_values("trade_date", kind="stable").reset_index(drop=True)
        validate_value_semantics(out)
        relative = Path("partitions") / str(item["symbol"]).lower() / f"{int(item['year'])}.parquet"
        path = root / relative
        c74._atomic_parquet(out, path)
        eligible = int(out[f"{FACTOR_NAME}_eligible"].sum())
        missing = int(len(out) - eligible)
        totals["eligible"] += eligible
        totals["missing"] += missing
        records[index] = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign075_feature_partition",
            "status": "complete_pending_aggregate_publication",
            "path": str(path.resolve()),
            "relative_path": str(relative),
            "symbol": str(item["symbol"]),
            "code": str(item["code"]),
            "year": int(item["year"]),
            "rows": int(len(out)),
            "output_byte_sha256": _sha256(path),
            "output_frame_sha256": _frame_sha256(out),
            "campaign074_identity_path": str(item["path"]),
            "campaign074_identity_byte_sha256": str(item["output_byte_sha256"]),
            "campaign074_identity_fields_read": list(IDENTITY_COLUMNS),
            "campaign074_factor_values_read": False,
            "instrument_interval_source_sha256": INSTRUMENTS_SHA256,
            "calendar_sha256": CALENDAR_SHA256,
            "factor_eligible_rows": {FACTOR_NAME: eligible},
            "quality": {
                "base_rows": int(len(out)),
                f"{FACTOR_NAME}__eligible_rows": eligible,
                f"{FACTOR_NAME}__missing_rows": missing,
            },
            "protocol_sha256": PROTOCOL_SHA256,
            "implementation_freeze_sha256": _sha256(DEFAULT_IMPLEMENTATION_FREEZE),
            "daily_price_fields_read": [],
            "forward_return_fields_read": False,
            "comparison_factor_values_read": False,
            "provider_request_issued": False,
        }

    by_year: dict[int, list[int]] = {}
    for index, item in enumerate(files):
        by_year.setdefault(int(item["year"]), []).append(index)
    for year in sorted(by_year):
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = [
                pool.submit(
                    _load_partition,
                    index,
                    files[index],
                    interval_map[str(files[index]["symbol"]).upper()],
                    calendar,
                )
                for index in by_year[year]
            ]
            for future in concurrent.futures.as_completed(futures):
                index, out = future.result()
                publish(index, out)
        print(
            f"Campaign075 built year={year} partitions={len(by_year[year])} "
            f"eligible_rows={totals['eligible']}",
            flush=True,
        )
    completed = [item for item in records if item is not None]
    if (
        len(completed) != EXPECTED_PARTITIONS
        or sum(int(item["rows"]) for item in completed) != EXPECTED_ROWS
    ):
        raise Campaign075FeatureError("Campaign075 publication totals changed")
    digest_rows = [
        [
            item["relative_path"],
            item["output_byte_sha256"],
            item["output_frame_sha256"],
            item["rows"],
        ]
        for item in completed
    ]
    result = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign075_feature_snapshot",
        "status": "feature_library_complete_pending_ordered_no_return_gates",
        "output_run_id": OUTPUT_RUN_ID,
        "dataset_sha256": _json_digest(digest_rows),
        "partitions": EXPECTED_PARTITIONS,
        "rows": EXPECTED_ROWS,
        "files": completed,
        "factor_names": [FACTOR_NAME],
        "factor_directions": {FACTOR_NAME: "higher"},
        "factor_ranges": {FACTOR_NAME: [None, -float(MINIMUM_AGE_SESSIONS)]},
        "factor_formulas": {FACTOR_NAME: FACTOR_FORMULA},
        "factor_eligible_rows": {FACTOR_NAME: totals["eligible"]},
        "quality": {
            "base_rows": EXPECTED_ROWS,
            f"{FACTOR_NAME}__eligible_rows": totals["eligible"],
            f"{FACTOR_NAME}__missing_rows": totals["missing"],
        },
        "campaign074_identity_manifest_sha256": C74_MANIFEST_SHA256,
        "campaign074_identity_dataset_sha256": C74_DATASET_SHA256,
        "campaign074_identity_fields_read": list(IDENTITY_COLUMNS),
        "campaign074_factor_values_read": False,
        "accepted_instrument_intervals_sha256": INSTRUMENTS_SHA256,
        "accepted_calendar_sha256": CALENDAR_SHA256,
        "minimum_age_sessions": MINIMUM_AGE_SESSIONS,
        "age_clock": "inclusive accepted local market sessions",
        "left_censoring_rule": "accepted instrument start is used exactly",
        "protocol_sha256": PROTOCOL_SHA256,
        "mechanism_overlap_audit_sha256": MECHANISM_AUDIT_SHA256,
        "implementation_freeze_sha256": _sha256(DEFAULT_IMPLEMENTATION_FREEZE),
        "implementation_freeze_status": freeze.get("status"),
        "daily_price_fields_read": [],
        "forward_return_fields_read": False,
        "comparison_factor_values_read": False,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
        "training_or_model_fitting_performed": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
        "prospective_candidate_activation_created": False,
        "provider_request_issued": False,
    }
    c74._atomic_json(result, manifest_path)
    return manifest_path


def _validate_manifest(manifest: dict[str, Any]) -> None:
    quality = manifest.get("quality") or {}
    files = list(manifest.get("files") or [])
    eligible = (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign075_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and len(files) == EXPECTED_PARTITIONS
        and manifest.get("rows") == EXPECTED_ROWS
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == {FACTOR_NAME: "higher"}
        and manifest.get("factor_ranges")
        == {FACTOR_NAME: [None, -float(MINIMUM_AGE_SESSIONS)]}
        and manifest.get("factor_formulas") == {FACTOR_NAME: FACTOR_FORMULA}
        and manifest.get("campaign074_identity_manifest_sha256")
        == C74_MANIFEST_SHA256
        and manifest.get("campaign074_identity_dataset_sha256")
        == C74_DATASET_SHA256
        and manifest.get("campaign074_identity_fields_read")
        == list(IDENTITY_COLUMNS)
        and manifest.get("campaign074_factor_values_read") is False
        and manifest.get("accepted_instrument_intervals_sha256")
        == INSTRUMENTS_SHA256
        and manifest.get("accepted_calendar_sha256") == CALENDAR_SHA256
        and manifest.get("minimum_age_sessions") == MINIMUM_AGE_SESSIONS
        and manifest.get("protocol_sha256") == PROTOCOL_SHA256
        and manifest.get("mechanism_overlap_audit_sha256")
        == MECHANISM_AUDIT_SHA256
        and quality.get("base_rows") == EXPECTED_ROWS
        and quality.get(f"{FACTOR_NAME}__eligible_rows") == eligible
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("candidate49_historical_return_read") is False
        and manifest.get("candidate49_ledgers_changed") is False
        and manifest.get("training_or_model_fitting_performed") is False
        and manifest.get("current_scoring_selection_sizing_or_orders_performed")
        is False
        and manifest.get("prospective_candidate_activation_created") is False
        and manifest.get("provider_request_issued") is False
    ):
        raise Campaign075FeatureError("Campaign075 manifest semantics changed")


def verify_snapshot_files(manifest_path: Path, *, workers: int = 4) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    expected = (output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json").resolve()
    if manifest_path != expected:
        raise Campaign075FeatureError("Campaign075 manifest path changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_manifest(manifest)
    partition_root = (manifest_path.parent / "partitions").resolve()

    def verify(item: dict[str, Any]) -> tuple[int, int]:
        path = Path(str(item["path"])).expanduser().resolve()
        path.relative_to(partition_root)
        if _sha256(path) != item["output_byte_sha256"]:
            raise Campaign075FeatureError(f"partition byte hash changed: {path}")
        frame = pd.read_parquet(path)
        if len(frame) != item["rows"] or _frame_sha256(frame) != item["output_frame_sha256"]:
            raise Campaign075FeatureError(f"partition frame changed: {path}")
        return validate_value_semantics(frame)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        verified = list(pool.map(verify, manifest["files"]))
    digest_rows = [
        [
            item["relative_path"],
            item["output_byte_sha256"],
            item["output_frame_sha256"],
            item["rows"],
        ]
        for item in manifest["files"]
    ]
    if not (
        _json_digest(digest_rows) == manifest["dataset_sha256"]
        and len(verified) == EXPECTED_PARTITIONS
        and sum(value[0] for value in verified) == EXPECTED_ROWS
        and sum(value[1] for value in verified)
        == (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    ):
        raise Campaign075FeatureError("Campaign075 aggregate identity changed")
    return {
        "status": "verified",
        "partitions": len(verified),
        "rows": sum(value[0] for value in verified),
        "eligible_rows": sum(value[1] for value in verified),
        "dataset_sha256": manifest["dataset_sha256"],
        "comparison_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def status(data_root: Path) -> dict[str, Any]:
    load_protocol()
    path = output_root(data_root.expanduser().resolve()) / "snapshot_manifest.json"
    return {
        "status": "snapshot_present" if path.is_file() else "snapshot_absent_pre_build",
        "snapshot_manifest": str(path),
        "source_rows_or_candidate_values_read_by_status": False,
        "comparison_values_read_by_status": False,
        "historical_daily_price_or_forward_return_values_read_by_status": False,
        "provider_request_issued_by_status": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    build.add_argument("--workers", type=int, default=4)
    inspect = subparsers.add_parser("status")
    inspect.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.command == "build":
        payload = {
            "snapshot_manifest": str(
                build_snapshot(data_root=args.data_root, workers=args.workers)
            )
        }
    elif args.command == "verify":
        payload = verify_snapshot_files(args.manifest, workers=args.workers)
    else:
        payload = status(args.data_root)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
