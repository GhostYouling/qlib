#!/usr/bin/env python3
"""Build the frozen Campaign066 point-in-time quality-rank balance snapshot."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from scripts import a_share_three_day_preregistration_binding_validator as bindings


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
DEFAULT_PROTOCOL = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_066_no_return_preregistration.json"
DEFAULT_IMPLEMENTATION_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_066_feature_implementation_freeze_v2_20260805.json"
DEFAULT_CALENDAR = REPO_ROOT / "data/qlib/cn_a_share/calendars/day.txt"
CLEAN_MANIFEST_RELATIVE = Path("derived/a_share/rich/tushare/minute_sentiment_clean/tushare_stk_mins_1m_2019_2025_ea0cbb8f_sentiment_clean_v1/snapshot_manifest.json")
QUARTERLY_PATH = REPO_ROOT / "data/raw/a_share/fundamentals/quarterly_quality.parquet"
QUARTERLY_MANIFEST_PATH = REPO_ROOT / "data/metadata/quarterly_quality_manifest.json"
FACTOR_NAME = "quarterly_quality_rank_balance_3f"
FACTOR_FORMULA = "1-(max(r_roe,r_profit,r_revenue)-min(r_roe,r_profit,r_revenue))"
PROTOCOL_SHA256 = "ab850ef8ff194c1172070e2ffd388eff2d7924354abf06a8b32c5bd43584a278"
MECHANISM_AUDIT_SHA256 = "1e5fe44c0cde5097646cf058ec8149c189cf65e2ce62093e221c0d5022b98b8b"
CLEAN_MANIFEST_SHA256 = "453c6719cb3c7da42fed8807b28a2bfe988700283e9625a6db97912534f368de"
CLEAN_DATASET_SHA256 = "0e4fe7c05536cdfcecc2936bc880726902f5560061188ffff82ef7ee6f346983"
QUARTERLY_SHA256 = "3ac901a97928d2ed81ac72e3eaac9bdc148d36cf67b6abe70223699235ef059f"
QUARTERLY_MANIFEST_SHA256 = "e3cf654babe37a82393c5530696bc1cc242b736cb88e1947b8444b638125ba8c"
CALENDAR_SHA256 = "fda506597d26bcec953cdc0882042a5046ec1587db60490e16a01627fd43f53a"
EXPECTED_PARTITIONS = 33015
EXPECTED_ROWS = 7724498
FULL_DEFINITION_COUNT = 97
FULL_DEFINITION_ORDER_SHA256 = "bc66abb94f62bef5fe9912059ade232c6c86b16b82f162df577fa8d74afeca7d"
COMPARISON_COUNT = 96
COMPARISON_ORDER_SHA256 = "794dff48d649b8dec1fdf609583ad87260c3e71a681a48b9a0ce77726de4763b"
C65_FACTOR = "intraday_range_weak_order_time_reversal_divergence_236t"
C63_FACTOR = "intraday_cross_sectional_standardized_return_state_stability_236p"
OUTPUT_RUN_ID = "tushare_stk_mins_1m_2019_2025_ea0cbb8f_walkforward_campaign066_feature_library_v1"
EVENT_FIELDS = ("instrument", "report_date", "announcement_date", "roe", "profit_yoy", "revenue_yoy")
STATE_FIELDS = ("roe", "profit_yoy", "revenue_yoy")
OUTPUT_COLUMNS = ("trade_date", "symbol", "provider", FACTOR_NAME, f"{FACTOR_NAME}_eligible")


class Campaign066FeatureError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _comparison_order_digest(items: Iterable[dict[str, Any]]) -> str:
    return _json_digest([[str(item["name"]), str(item["score_direction"])] for item in items])


def reconstruct_comparisons(spec: dict[str, Any] | None = None) -> list[dict[str, str]]:
    spec = spec or json.loads(DEFAULT_PROTOCOL.read_text(encoding="utf-8"))
    link = (spec.get("source_chain") or {}).get("campaign065_completed_numeric_comparison_catalog") or {}
    path = REPO_ROOT / str(link.get("path") or "")
    if not path.is_file() or _sha256(path) != str(link.get("sha256") or ""):
        raise Campaign066FeatureError("Campaign065 comparison catalog changed")
    audit = json.loads(path.read_text(encoding="utf-8"))
    previous = (audit.get("uniqueness") or {}).get(C65_FACTOR) or {}
    items = [
        {"name": str(item["comparison_factor"]), "score_direction": str(item["score_direction"])}
        for item in previous.get("comparisons") or []
    ]
    items.append({"name": C65_FACTOR, "score_direction": "higher"})
    if len(items) != COMPARISON_COUNT or _comparison_order_digest(items) != COMPARISON_ORDER_SHA256:
        raise Campaign066FeatureError("Campaign066 comparison order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.is_file() or _sha256(path) != PROTOCOL_SHA256:
        raise Campaign066FeatureError(f"Campaign066 protocol changed: {path}")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign066FeatureError("Campaign066 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    unique = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    comparisons = reconstruct_comparisons(spec)
    if not (
        spec.get("kind") == "a_share_three_day_walkforward_campaign066_no_return_preregistration"
        and spec.get("status") == "frozen_before_campaign066_source_candidate_comparison_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("component_definition_inputs") == ["quality_roe", "quality_profit", "quality_revenue"]
        and tuple(candidate.get("quarterly_source_projection") or ()) == EVENT_FIELDS
        and candidate.get("combination_rule") == "Exactly one minus the maximum rank minus minimum rank; component weights or fitted transformations do not exist."
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and unique.get("complete_definition_count") == FULL_DEFINITION_COUNT
        and unique.get("complete_definition_order_sha256") == FULL_DEFINITION_ORDER_SHA256
        and unique.get("numeric_comparator_count") == COMPARISON_COUNT
        and unique.get("numeric_comparator_order_sha256") == COMPARISON_ORDER_SHA256
        and len(comparisons) == COMPARISON_COUNT
        and unique.get("all_96_numeric_comparators_must_pass") is True
        and unique.get("structurally_nonnumeric_mechanism_challenges") == [C63_FACTOR]
        and finite.get("trial_id") == "wf066_quarterly_quality_rank_balance_3f_single_higher"
        and finite.get("expected_trial_count") == 1
        and boundary.get("quarterly_or_minute_source_rows_read_before_this_freeze") is False
        and boundary.get("candidate_or_comparison_values_read_before_this_freeze") is False
        and boundary.get("historical_forward_return_fields_read") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign066FeatureError("Campaign066 protocol semantics changed")
    return spec


def compute_balance_values(ranks: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(ranks, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 3:
        raise Campaign066FeatureError("quality ranks must be an n-by-3 array")
    finite = np.isfinite(values).all(axis=1)
    in_range = ((values >= 0.0) & (values <= 1.0)).all(axis=1)
    eligible = finite & in_range
    result = np.full(len(values), np.nan, dtype=np.float64)
    result[eligible] = 1.0 - (values[eligible].max(axis=1) - values[eligible].min(axis=1))
    if not ((result[eligible] >= 0.0).all() and (result[eligible] <= 1.0).all()):
        raise Campaign066FeatureError("quality rank balance escaped [0,1]")
    return result, eligible


def prepare_events(events: pd.DataFrame, calendar: pd.DatetimeIndex) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    if tuple(events.columns) != EVENT_FIELDS:
        raise Campaign066FeatureError("quarterly source projection changed")
    work = events.copy()
    work["instrument"] = work["instrument"].astype(str).str.upper()
    for column in ("report_date", "announcement_date"):
        work[column] = pd.to_datetime(work[column], errors="coerce").dt.normalize()
    for column in STATE_FIELDS:
        work[column] = pd.to_numeric(work[column], errors="coerce")
    if work.empty or work[["instrument", "report_date", "announcement_date"]].isna().any().any() or work.duplicated(["instrument", "report_date"]).any():
        raise Campaign066FeatureError("quarterly event identities changed")
    calendar_values = calendar.to_numpy(dtype="datetime64[ns]")
    positions = np.searchsorted(calendar_values, work["announcement_date"].to_numpy(dtype="datetime64[ns]"), side="right")
    work = work.loc[positions < len(calendar_values)].copy()
    work["effective_position"] = positions[positions < len(calendar_values)]
    work = work.sort_values(["instrument", "effective_position", "report_date", "announcement_date"], kind="stable").drop_duplicates(["instrument", "effective_position"], keep="last")
    result: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for symbol, group in work.groupby("instrument", sort=False):
        states = group.loc[:, STATE_FIELDS].ffill().to_numpy(dtype=np.float64)
        result[str(symbol)] = (group["effective_position"].to_numpy(dtype=np.int64), states)
    return result


def attach_states(frame: pd.DataFrame, *, symbol: str, calendar: pd.DatetimeIndex, events_by_symbol: dict[str, tuple[np.ndarray, np.ndarray]]) -> pd.DataFrame:
    required = ("trade_date", "symbol", "provider")
    if tuple(frame.columns) != required:
        raise Campaign066FeatureError("joint-clean identity projection changed")
    out = frame.copy()
    out["trade_date"] = pd.to_datetime(out["trade_date"], errors="coerce").dt.normalize()
    out["symbol"] = out["symbol"].astype(str).str.upper()
    out["provider"] = out["provider"].astype(str).str.lower()
    if out.empty:
        for column in STATE_FIELDS:
            out[column] = pd.Series(dtype="float64")
        return out
    if out["trade_date"].isna().any() or set(out["symbol"].unique()) != {symbol.upper()} or out.duplicated(["trade_date", "symbol"]).any():
        raise Campaign066FeatureError(f"joint-clean identity changed for {symbol}")
    calendar_values = calendar.to_numpy(dtype="datetime64[ns]")
    dates = out["trade_date"].to_numpy(dtype="datetime64[ns]")
    positions = np.searchsorted(calendar_values, dates, side="left")
    if (positions >= len(calendar_values)).any() or not np.array_equal(calendar_values[positions], dates):
        raise Campaign066FeatureError(f"joint-clean dates escaped calendar for {symbol}")
    states = np.full((len(out), 3), np.nan, dtype=np.float64)
    event_state = events_by_symbol.get(symbol.upper())
    if event_state is not None:
        event_positions, event_values = event_state
        chosen = np.searchsorted(event_positions, positions, side="right") - 1
        valid = chosen >= 0
        states[valid] = event_values[chosen[valid]]
    for index, column in enumerate(STATE_FIELDS):
        out[column] = states[:, index]
    return out


def rank_and_balance_year_frame(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    ranks = []
    for column in STATE_FIELDS:
        ranks.append(work.groupby("trade_date", sort=False)[column].rank(method="average", pct=True))
    rank_matrix = np.column_stack([series.to_numpy(dtype=np.float64) for series in ranks])
    values, eligible = compute_balance_values(rank_matrix)
    work[FACTOR_NAME] = values
    work[f"{FACTOR_NAME}_eligible"] = eligible
    work["provider"] = "eastmoney_quarterly_quality"
    return work


def _frame_sha256(frame: pd.DataFrame) -> str:
    sink = pa.BufferOutputStream()
    table = pa.Table.from_pandas(frame, preserve_index=False)
    with pa.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    return hashlib.sha256(sink.getvalue().to_pybytes()).hexdigest()


def output_root(data_root: Path) -> Path:
    return data_root / "derived/a_share/rich/tushare/minute_walkforward_campaign066_feature_library" / OUTPUT_RUN_ID


def _atomic_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temporary_path = Path(temporary)
    try:
        pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), temporary_path, compression="zstd")
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temporary_path = Path(temporary)
    try:
        temporary_path.write_text(text, encoding="utf-8")
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _require_inputs(data_root: Path) -> tuple[dict[str, Any], dict[str, Any], pd.DatetimeIndex]:
    load_protocol()
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign066FeatureError("Campaign066 implementation freeze is absent")
    freeze = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    runner = freeze.get("feature_runner") or {}
    if runner.get("path") != "scripts/a_share_three_day_walkforward_campaign066_features.py" or runner.get("sha256") != _sha256(Path(__file__)):
        raise Campaign066FeatureError("Campaign066 implementation freeze does not bind this runner")
    clean_path = data_root / CLEAN_MANIFEST_RELATIVE
    for path, expected, label in ((clean_path, CLEAN_MANIFEST_SHA256, "joint-clean manifest"), (QUARTERLY_PATH, QUARTERLY_SHA256, "quarterly source"), (QUARTERLY_MANIFEST_PATH, QUARTERLY_MANIFEST_SHA256, "quarterly manifest"), (DEFAULT_CALENDAR, CALENDAR_SHA256, "calendar")):
        if not path.is_file() or _sha256(path) != expected:
            raise Campaign066FeatureError(f"{label} changed")
    clean = json.loads(clean_path.read_text(encoding="utf-8"))
    if clean.get("dataset_sha256") != CLEAN_DATASET_SHA256 or clean.get("partitions") != EXPECTED_PARTITIONS or clean.get("rows") != EXPECTED_ROWS:
        raise Campaign066FeatureError("joint-clean aggregate semantics changed")
    calendar = pd.DatetimeIndex(pd.to_datetime([line.strip() for line in DEFAULT_CALENDAR.read_text().splitlines() if line.strip()], errors="raise")).normalize()
    return clean, freeze, calendar


def build_snapshot(*, data_root: Path, workers: int = 4) -> Path:
    clean, freeze, calendar = _require_inputs(data_root.expanduser().resolve())
    events = pd.read_parquet(QUARTERLY_PATH, columns=list(EVENT_FIELDS), filters=[("announcement_date", "<", pd.Timestamp("2026-01-01"))])
    events_by_symbol = prepare_events(events, calendar)
    files = list(clean.get("files") or [])
    by_year: dict[int, list[tuple[int, dict[str, Any]]]] = {}
    for index, item in enumerate(files):
        by_year.setdefault(int(item["year"]), []).append((index, item))
    root = output_root(data_root)
    records: list[dict[str, Any] | None] = [None] * len(files)
    total_eligible = 0
    total_missing = 0
    for year in sorted(by_year):
        pieces = []
        for index, item in by_year[year]:
            identity = pd.read_parquet(item["path"], columns=["trade_date", "symbol", "provider"])
            attached = attach_states(identity, symbol=str(item["symbol"]), calendar=calendar, events_by_symbol=events_by_symbol)
            attached["_partition_index"] = index
            pieces.append(attached)
        year_frame = rank_and_balance_year_frame(pd.concat(pieces, ignore_index=True))
        grouped = {int(index): group for index, group in year_frame.groupby("_partition_index", sort=False)}
        for index, item in by_year[year]:
            group = grouped.get(index)
            if group is None:
                out = pd.DataFrame({
                    "trade_date": pd.Series(dtype="datetime64[ns]"),
                    "symbol": pd.Series(dtype="object"),
                    "provider": pd.Series(dtype="object"),
                    FACTOR_NAME: pd.Series(dtype="float64"),
                    f"{FACTOR_NAME}_eligible": pd.Series(dtype="bool"),
                }).loc[:, OUTPUT_COLUMNS]
            else:
                out = group.loc[:, OUTPUT_COLUMNS].sort_values("trade_date", kind="stable").reset_index(drop=True)
            relative = Path("partitions") / str(item["symbol"]).lower() / f"{int(item['year'])}.parquet"
            path = root / relative
            _atomic_parquet(out, path)
            eligible = int(out[f"{FACTOR_NAME}_eligible"].sum())
            missing = int(len(out) - eligible)
            total_eligible += eligible
            total_missing += missing
            records[index] = {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign066_feature_partition",
                "status": "complete_pending_aggregate_publication",
                "path": str(path.resolve()),
                "relative_path": str(relative),
                "symbol": str(item["symbol"]),
                "code": str(item["code"]),
                "year": int(item["year"]),
                "rows": int(len(out)),
                "output_byte_sha256": _sha256(path),
                "output_frame_sha256": _frame_sha256(out),
                "joint_clean_path": str(item["path"]),
                "joint_clean_byte_sha256": str(item["output_byte_sha256"]),
                "factor_eligible_rows": {FACTOR_NAME: eligible},
                "quality": {"base_rows": int(len(out)), f"{FACTOR_NAME}__eligible_rows": eligible, f"{FACTOR_NAME}__missing_or_nonfinite_state_rows": missing},
                "protocol_sha256": PROTOCOL_SHA256,
                "implementation_freeze_sha256": _sha256(DEFAULT_IMPLEMENTATION_FREEZE),
                "daily_price_fields_read": [],
                "forward_return_fields_read": False,
                "comparison_factor_values_read": False,
                "provider_request_issued": False,
            }
    completed = [item for item in records if item is not None]
    if len(completed) != EXPECTED_PARTITIONS or sum(int(item["rows"]) for item in completed) != EXPECTED_ROWS:
        raise Campaign066FeatureError("Campaign066 publication partition totals changed")
    digest_rows = [[item["relative_path"], item["output_byte_sha256"], item["output_frame_sha256"], item["rows"]] for item in completed]
    manifest = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign066_feature_snapshot",
        "status": "feature_library_complete_pending_ordered_no_return_gates",
        "output_run_id": OUTPUT_RUN_ID,
        "dataset_sha256": _json_digest(digest_rows),
        "partitions": EXPECTED_PARTITIONS,
        "rows": EXPECTED_ROWS,
        "files": completed,
        "factor_names": [FACTOR_NAME],
        "factor_directions": {FACTOR_NAME: "higher"},
        "factor_formulas": {FACTOR_NAME: FACTOR_FORMULA},
        "factor_eligible_rows": {FACTOR_NAME: total_eligible},
        "quality": {"base_rows": EXPECTED_ROWS, f"{FACTOR_NAME}__eligible_rows": total_eligible, f"{FACTOR_NAME}__missing_or_nonfinite_state_rows": total_missing},
        "source_fields_read": ["trade_date", "symbol", "provider"],
        "quarterly_fields_read": list(EVENT_FIELDS),
        "quarterly_source_path": str(QUARTERLY_PATH.resolve()),
        "quarterly_source_sha256": QUARTERLY_SHA256,
        "quarterly_manifest_sha256": QUARTERLY_MANIFEST_SHA256,
        "point_in_time_rule": "strict_next_session_then_independent_per_field_forward_fill",
        "cross_section_rank_rule": "average_tie_percentile_on_each_stock_day",
        "combination_rule": FACTOR_FORMULA,
        "protocol_sha256": PROTOCOL_SHA256,
        "mechanism_overlap_audit_sha256": MECHANISM_AUDIT_SHA256,
        "implementation_freeze_sha256": _sha256(DEFAULT_IMPLEMENTATION_FREEZE),
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
    manifest_path = root / "snapshot_manifest.json"
    _atomic_json(manifest, manifest_path)
    return manifest_path


def _validate_manifest(manifest: dict[str, Any]) -> None:
    if not (
        manifest.get("kind") == "a_share_three_day_walkforward_campaign066_feature_snapshot"
        and manifest.get("status") == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and manifest.get("rows") == EXPECTED_ROWS
        and len(manifest.get("files") or []) == EXPECTED_PARTITIONS
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == {FACTOR_NAME: "higher"}
        and manifest.get("factor_formulas") == {FACTOR_NAME: FACTOR_FORMULA}
        and manifest.get("protocol_sha256") == PROTOCOL_SHA256
        and manifest.get("mechanism_overlap_audit_sha256") == MECHANISM_AUDIT_SHA256
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("candidate49_ledgers_changed") is False
        and manifest.get("provider_request_issued") is False
    ):
        raise Campaign066FeatureError("Campaign066 snapshot semantics changed")


def verify_snapshot_files(manifest_path: Path, *, workers: int = 4) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_manifest(manifest)
    def verify(item: dict[str, Any]) -> tuple[int, int]:
        path = Path(item["path"])
        if _sha256(path) != item["output_byte_sha256"]:
            raise Campaign066FeatureError(f"partition byte hash changed: {path}")
        frame = pd.read_parquet(path)
        if tuple(frame.columns) != OUTPUT_COLUMNS or len(frame) != item["rows"] or _frame_sha256(frame) != item["output_frame_sha256"]:
            raise Campaign066FeatureError(f"partition frame changed: {path}")
        values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
        eligible = frame[f"{FACTOR_NAME}_eligible"].astype(bool)
        if values[eligible].isna().any() or ((values[eligible] < 0.0) | (values[eligible] > 1.0)).any() or values[~eligible].notna().any():
            raise Campaign066FeatureError(f"partition value semantics changed: {path}")
        return len(frame), int(eligible.sum())
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        totals = list(pool.map(verify, manifest["files"]))
    digest_rows = [[item["relative_path"], item["output_byte_sha256"], item["output_frame_sha256"], item["rows"]] for item in manifest["files"]]
    if _json_digest(digest_rows) != manifest["dataset_sha256"] or sum(x[0] for x in totals) != EXPECTED_ROWS:
        raise Campaign066FeatureError("aggregate dataset identity changed")
    return {"status": "verified", "partitions": len(totals), "rows": sum(x[0] for x in totals), "eligible_rows": sum(x[1] for x in totals), "dataset_sha256": manifest["dataset_sha256"]}


def status(data_root: Path = DEFAULT_DATA_ROOT) -> dict[str, Any]:
    load_protocol()
    path = output_root(data_root) / "snapshot_manifest.json"
    return {"status": "snapshot_present" if path.is_file() else "snapshot_absent_pre_build", "snapshot_manifest": str(path), "protocol_sha256": PROTOCOL_SHA256, "candidate_or_comparison_values_read_by_status": False, "daily_price_fields_read_by_status": [], "historical_forward_return_fields_read_by_status": False, "provider_request_issued_by_status": False}


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
        payload = {"snapshot_manifest": str(build_snapshot(data_root=args.data_root, workers=args.workers))}
    elif args.command == "verify":
        payload = verify_snapshot_files(args.manifest, workers=args.workers)
    else:
        payload = status(args.data_root)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
