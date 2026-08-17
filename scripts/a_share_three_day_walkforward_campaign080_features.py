#!/usr/bin/env python3
"""Build Campaign080's above-median amount longest-run snapshot without returns."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign074_features as c74
from scripts import a_share_three_day_walkforward_campaign078_features as c78


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = c74.DEFAULT_DATA_ROOT
DEFAULT_PROTOCOL = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_080_no_return_preregistration.json"
DEFAULT_IMPLEMENTATION_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_080_feature_implementation_freeze_20260806.json"
DEFAULT_CALENDAR = c74.DEFAULT_CALENDAR
RAW_MANIFEST_RELATIVE = c74.RAW_MANIFEST_RELATIVE
CLEAN_MANIFEST_RELATIVE = c74.CLEAN_MANIFEST_RELATIVE

FACTOR_NAME = "intraday_above_median_amount_longest_run_240m"
FACTOR_FORMULA = (
    "ordinary full-session median m; b_i=1[amount_i>m]; maximum of the "
    "longest one-run in positions 0..119 and 120..239, divided by 120"
)
PROTOCOL_SHA256 = "4f1061d0daaec767d926cda79762c3c70806b84e55c28c4d198918547df3c0f5"
MECHANISM_AUDIT_SHA256 = "d9dcaa373994f72258dcea37a550258bd2aeac856250bb1693be44effb110b65"
NUMERIC_POLICY_SHA256 = "e4df7ab965b003d8f77cbdffa742127e8f118417e6165b52afa6ae30cc5cfb63"
CURRENT_STATE_SHA256 = "a9898fcded0457b491a82f3678f62c23a27c7c35193c55122156fa322a5d3161"
RAW_MANIFEST_SHA256 = c74.RAW_MANIFEST_SHA256
CLEAN_MANIFEST_SHA256 = c74.CLEAN_MANIFEST_SHA256
CLEAN_DATASET_SHA256 = c74.CLEAN_DATASET_SHA256
CALENDAR_SHA256 = c74.CALENDAR_SHA256
EXPECTED_PARTITIONS = c74.EXPECTED_PARTITIONS
EXPECTED_ROWS = c74.EXPECTED_ROWS
FULL_DEFINITION_COUNT = 111
FULL_DEFINITION_ORDER_SHA256 = "14479cf55ceab31f6705fc12b1e103d9da41f8b07f27ffdf4b87e63cac36ffdb"
COMPARISON_COUNT = 109
COMPARISON_ORDER_SHA256 = "0893e0ff54c0094e48e67def84f0038a453fd11230629631e3e54120480a3529"
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign080_feature_library_v1"
)

RAW_COLUMNS = c74.RAW_COLUMNS
IDENTITY_COLUMNS = c74.IDENTITY_COLUMNS
CONTINUOUS_MINUTE_CODES = c74.CONTINUOUS_MINUTE_CODES
CONTINUOUS_MINUTE_CODE_SET = c74.CONTINUOUS_MINUTE_CODE_SET
SOURCE_MINUTE_CODE_SET = c74.SOURCE_MINUTE_CODE_SET
SELECTED_BAR_COUNT = c74.SELECTED_BAR_COUNT
SOURCE_BAR_COUNT = c74.SOURCE_BAR_COUNT
HALF_SESSION_BAR_COUNT = 120
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
C78_FACTOR = c78.FACTOR_NAME
C79_FACTOR = "signal_day_turnover_rate_pct"
C78_RECORD_PATH = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_078_research_record_v4.json"
C78_RECORD_SHA256 = "44f9402d485c84725378141ec73a96e76121754834752c027b22e730d4e3bfd1"
C78_BINDING_PATH = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_078_feature_snapshot_binding_20260806.json"
C78_BINDING_SHA256 = "75a9fe0927308ddcbeccf128b89145e5f82e5c8272c52404494c6c95f4a9b1dc"
C78_MANIFEST_PATH = c78.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
C78_MANIFEST_SHA256 = "a8d2f2a68dba3f7f3a3f34ac8d203f1381e429612ded6daf6c6447e0ed983071"
C78_DATASET_SHA256 = "225c539824978df0cc3e4b34a9520aa919ffa77ba73246c21e1bdb6122a0227d"


class Campaign080FeatureError(RuntimeError):
    """Fail-closed Campaign080 feature error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _comparison_order_digest(items: Iterable[dict[str, Any]]) -> str:
    return _json_digest(
        [[str(item["name"]), str(item["score_direction"])] for item in items]
    )


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign080FeatureError(f"Campaign080 {label} changed: {path}")


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = c78.reconstruct_comparisons()
    items.append({"name": C78_FACTOR, "score_direction": "higher"})
    if (
        len(items) != COMPARISON_COUNT
        or _comparison_order_digest(items) != COMPARISON_ORDER_SHA256
    ):
        raise Campaign080FeatureError("Campaign080 numeric comparison order changed")
    return items


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = c78.reconstruct_complete_definitions()
    items.extend(
        [
            {"name": C78_FACTOR, "score_direction": "higher"},
            {"name": C79_FACTOR, "score_direction": "higher"},
        ]
    )
    if (
        len(items) != FULL_DEFINITION_COUNT
        or _comparison_order_digest(items) != FULL_DEFINITION_ORDER_SHA256
    ):
        raise Campaign080FeatureError("Campaign080 complete definition order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    _require(path, PROTOCOL_SHA256, "protocol")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign080FeatureError("Campaign080 protocol binding failed")
    for required, expected, label in (
        (C78_RECORD_PATH, C78_RECORD_SHA256, "Campaign078 record"),
        (C78_BINDING_PATH, C78_BINDING_SHA256, "Campaign078 snapshot binding"),
        (C78_MANIFEST_PATH, C78_MANIFEST_SHA256, "Campaign078 snapshot manifest"),
    ):
        _require(required, expected, label)
    previous = json.loads(C78_MANIFEST_PATH.read_text(encoding="utf-8"))
    spec = json.loads(path.read_text(encoding="utf-8"))
    chain = spec.get("source_chain") or {}
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    unique = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    c78_link = chain.get("campaign078_terminal_numeric_comparator") or {}
    c79_link = chain.get("campaign079_semantic_only_terminal_definition") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign080_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign080_minute_source_candidate_comparison_daily_price_or_return_values"
        and (chain.get("numeric_comparator_policy_v15") or {}).get("sha256")
        == NUMERIC_POLICY_SHA256
        and (chain.get("authoritative_iteration_state") or {}).get("sha256")
        == CURRENT_STATE_SHA256
        and c78_link.get("factor") == C78_FACTOR
        and c78_link.get("score_direction") == "higher"
        and c78_link.get("dataset_sha256") == C78_DATASET_SHA256
        and previous.get("dataset_sha256") == C78_DATASET_SHA256
        and previous.get("factor_names") == [C78_FACTOR]
        and c79_link.get("factor") == C79_FACTOR
        and c79_link.get("numeric_comparator_eligible") is False
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and tuple(candidate.get("minute_source_projection") or ()) == RAW_COLUMNS
        and tuple(candidate.get("stock_day_identity_projection") or ())
        == IDENTITY_COLUMNS
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("half_session_bar_count") == HALF_SESSION_BAR_COUNT
        and candidate.get("median_order_statistics_one_indexed") == [120, 121]
        and candidate.get("maximum_run_length") == HALF_SESSION_BAR_COUNT
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
        and unique.get("all_109_numeric_comparators_must_pass") is True
        and len(reconstruct_comparisons()) == COMPARISON_COUNT
        and len(reconstruct_complete_definitions()) == FULL_DEFINITION_COUNT
        and finite.get("trial_id")
        == "wf080_intraday_above_median_amount_longest_run_240m_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("expected_trial_count") == 1
        and boundary.get("comparison_values_read_before_coverage_pass") is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign080FeatureError("Campaign080 protocol semantics changed")
    return spec


def _longest_true_run(mask: np.ndarray) -> np.ndarray:
    if mask.ndim != 2 or mask.shape[1] != HALF_SESSION_BAR_COUNT:
        raise Campaign080FeatureError("Campaign080 half-session shape changed")
    current = np.zeros(mask.shape[0], dtype=np.int16)
    longest = np.zeros(mask.shape[0], dtype=np.int16)
    for offset in range(HALF_SESSION_BAR_COUNT):
        current = np.where(mask[:, offset], current + 1, 0)
        longest = np.maximum(longest, current)
    return longest


def extract_above_median_amount_longest_run(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign080FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    empty = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "above_median_amount_longest_run": pd.Series(dtype="float64"),
        }
    )
    quality = {
        "source_rows": 0,
        "source_sessions": 0,
        "valid_above_median_amount_longest_run_sessions": 0,
        "invalid_amount_grid_sessions": 0,
        "nonpositive_total_amount_sessions": 0,
    }
    if raw.empty:
        return empty, quality
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["amount"] = pd.to_numeric(work["amount"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign080FeatureError(f"raw minute identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    distinct = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].nunique()
    if (
        counts.empty
        or not counts.eq(SOURCE_BAR_COUNT).all()
        or not distinct.eq(SOURCE_BAR_COUNT).all()
        or not work["minute_code"].isin(SOURCE_MINUTE_CODE_SET).all()
    ):
        raise Campaign080FeatureError(f"raw minute grid changed for {symbol}")
    continuous = work.loc[
        work["minute_code"].isin(CONTINUOUS_MINUTE_CODE_SET),
        ["trade_date", "minute_code", "amount"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"], categories=CONTINUOUS_MINUTE_CODES, ordered=True
    )
    continuous = continuous.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(counts.index).normalize()
    if len(continuous) != len(dates) * SELECTED_BAR_COUNT:
        raise Campaign080FeatureError(f"continuous minute grid changed for {symbol}")
    matrix = continuous["amount"].to_numpy(dtype=np.float64).reshape(
        len(dates), SELECTED_BAR_COUNT
    )
    amount_valid = np.isfinite(matrix).all(axis=1) & (matrix >= 0.0).all(axis=1)
    totals = matrix.sum(axis=1, dtype=np.float64)
    total_valid = amount_valid & np.isfinite(totals) & (totals > 0.0)
    score = np.full(len(dates), np.nan, dtype=np.float64)
    if total_valid.any():
        accepted = matrix[total_valid]
        medians = np.median(accepted, axis=1)
        high = accepted > medians[:, None]
        morning = _longest_true_run(high[:, :HALF_SESSION_BAR_COUNT])
        afternoon = _longest_true_run(high[:, HALF_SESSION_BAR_COUNT:])
        longest = np.maximum(morning, afternoon)
        if (longest < 0).any() or (longest > HALF_SESSION_BAR_COUNT).any():
            raise Campaign080FeatureError("Campaign080 longest-run bound changed")
        score[total_valid] = longest.astype(np.float64) / HALF_SESSION_BAR_COUNT
    range_valid = np.isfinite(score) & (score >= 0.0) & (score <= 1.0)
    score[~range_valid] = np.nan
    return pd.DataFrame(
        {"trade_date": dates, "above_median_amount_longest_run": score}
    ), {
        "source_rows": int(len(work)),
        "source_sessions": int(len(dates)),
        "valid_above_median_amount_longest_run_sessions": int(range_valid.sum()),
        "invalid_amount_grid_sessions": int((~amount_valid).sum()),
        "nonpositive_total_amount_sessions": int((amount_valid & ~total_valid).sum()),
    }


def attach_above_median_amount_longest_run(
    identity: pd.DataFrame, values: pd.DataFrame, *, symbol: str
) -> pd.DataFrame:
    if tuple(identity.columns) != IDENTITY_COLUMNS:
        raise Campaign080FeatureError(f"identity projection changed for {symbol}")
    base = identity.copy()
    base["trade_date"] = pd.to_datetime(
        base["trade_date"], errors="coerce"
    ).dt.normalize()
    base["symbol"] = base["symbol"].astype(str).str.upper()
    base["provider"] = base["provider"].astype(str).str.lower()
    if base.empty:
        base["above_median_amount_longest_run"] = pd.Series(dtype="float64")
        return base
    if (
        base["trade_date"].isna().any()
        or base.duplicated(["trade_date", "symbol"]).any()
        or set(base["symbol"].unique()) != {symbol.upper()}
        or set(base["provider"].unique()) != {"tushare"}
    ):
        raise Campaign080FeatureError(f"joint-clean identity changed for {symbol}")
    if values.empty or values.duplicated(["trade_date"]).any():
        raise Campaign080FeatureError(f"Campaign080 value identity changed for {symbol}")
    out = base.merge(values, on="trade_date", how="left", validate="one_to_one")
    if any(date not in set(values["trade_date"].tolist()) for date in out["trade_date"]):
        raise Campaign080FeatureError(
            f"accepted session absent from raw source for {symbol}"
        )
    return out


def finalize_feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = (*IDENTITY_COLUMNS, "above_median_amount_longest_run")
    if not set(required).issubset(frame.columns):
        raise Campaign080FeatureError("Campaign080 input columns changed")
    work = frame.copy()
    values = pd.to_numeric(work["above_median_amount_longest_run"], errors="coerce")
    eligible = np.isfinite(values) & values.ge(0.0) & values.le(1.0)
    work[FACTOR_NAME] = values.where(eligible)
    work[f"{FACTOR_NAME}_eligible"] = eligible
    work["provider"] = "tushare"
    return work


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
        raise Campaign080FeatureError("Campaign080 output columns changed")
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"].astype(bool)
    scaled = values[eligible] * HALF_SESSION_BAR_COUNT
    if (
        values[eligible].isna().any()
        or ((values[eligible] < 0.0) | (values[eligible] > 1.0)).any()
        or not np.allclose(scaled, np.rint(scaled), rtol=0.0, atol=1e-12)
        or values[~eligible].notna().any()
    ):
        raise Campaign080FeatureError("Campaign080 value semantics changed")
    return int(len(frame)), int(eligible.sum())


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived/a_share/rich/tushare/minute_walkforward_campaign080_feature_library"
        / OUTPUT_RUN_ID
    )


def _validate_implementation_freeze() -> dict[str, Any]:
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign080FeatureError("Campaign080 implementation freeze is absent")
    freeze = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    test = freeze.get("tests") or {}
    test_path = REPO_ROOT / str(test.get("path") or "")
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign080_feature_implementation_freeze"
        and freeze.get("status")
        == "frozen_before_campaign080_minute_source_values"
        and (freeze.get("feature_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and test_path.is_file()
        and test.get("sha256") == _sha256(test_path)
        and (freeze.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (freeze.get("mechanism_overlap_audit") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and (freeze.get("research_boundary") or {}).get(
            "candidate_source_rows_read_before_freeze"
        )
        is False
    ):
        raise Campaign080FeatureError("Campaign080 implementation freeze changed")
    return freeze


def _load_attached(
    index: int, clean_item: dict[str, Any], raw_item: dict[str, Any]
) -> tuple[int, pd.DataFrame, dict[str, int]]:
    symbol = str(clean_item["symbol"]).upper()
    identity = pd.read_parquet(clean_item["path"], columns=list(IDENTITY_COLUMNS))
    raw_path = Path(str(raw_item["path"])).expanduser().resolve()
    if (
        not raw_path.is_file()
        or pq.ParquetFile(raw_path).metadata.num_rows != int(raw_item["rows"])
    ):
        raise Campaign080FeatureError(f"raw partition changed: {raw_path}")
    raw = pd.read_parquet(raw_path, columns=list(RAW_COLUMNS))
    values, quality = extract_above_median_amount_longest_run(raw, symbol=symbol)
    out = attach_above_median_amount_longest_run(identity, values, symbol=symbol)
    out["_partition_index"] = index
    return index, out, quality


def build_snapshot(*, data_root: Path, workers: int = 4) -> Path:
    data_root = data_root.expanduser().resolve()
    load_protocol()
    freeze = _validate_implementation_freeze()
    raw, clean, _c74_freeze, _calendar = c74._require_inputs(data_root)
    raw_by_key = c74._raw_file_map(raw)
    files = list(clean.get("files") or [])
    by_year: dict[int, list[tuple[int, dict[str, Any]]]] = {}
    for index, item in enumerate(files):
        by_year.setdefault(int(item["year"]), []).append((index, item))
    root = output_root(data_root)
    manifest_path = root / "snapshot_manifest.json"
    if manifest_path.exists():
        raise Campaign080FeatureError("Campaign080 snapshot already exists; verify instead")
    records: list[dict[str, Any] | None] = [None] * len(files)
    totals = {
        "eligible": 0,
        "missing": 0,
        "source_rows": 0,
        "source_sessions": 0,
        "invalid_amount_grid_sessions": 0,
        "nonpositive_total_amount_sessions": 0,
    }
    for year in sorted(by_year):
        jobs = []
        for index, item in by_year[year]:
            raw_item = raw_by_key.get((str(item["symbol"]).upper(), int(item["year"])))
            if raw_item is None:
                raise Campaign080FeatureError("raw partition missing")
            jobs.append((index, item, raw_item))
        pieces: list[pd.DataFrame] = []
        quality_by_index: dict[int, dict[str, int]] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = [pool.submit(_load_attached, *job) for job in jobs]
            for future in concurrent.futures.as_completed(futures):
                index, attached, quality = future.result()
                pieces.append(attached)
                quality_by_index[index] = quality
                for key in (
                    "source_rows",
                    "source_sessions",
                    "invalid_amount_grid_sessions",
                    "nonpositive_total_amount_sessions",
                ):
                    totals[key] += quality[key]
        year_frame = finalize_feature_frame(pd.concat(pieces, ignore_index=True))
        grouped = {
            int(index): group
            for index, group in year_frame.groupby("_partition_index", sort=False)
        }
        for index, item in by_year[year]:
            group = grouped.get(index)
            out = (
                empty_output_frame()
                if group is None
                else group.loc[:, OUTPUT_COLUMNS]
                .sort_values("trade_date", kind="stable")
                .reset_index(drop=True)
            )
            validate_value_semantics(out)
            relative = Path("partitions") / str(item["symbol"]).lower() / f"{int(item['year'])}.parquet"
            path = root / relative
            c74._atomic_parquet(out, path)
            eligible = int(out[f"{FACTOR_NAME}_eligible"].sum())
            missing = int(len(out) - eligible)
            totals["eligible"] += eligible
            totals["missing"] += missing
            raw_item = raw_by_key[(str(item["symbol"]).upper(), int(item["year"]))]
            records[index] = {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign080_feature_partition",
                "status": "complete_pending_aggregate_publication",
                "path": str(path.resolve()),
                "relative_path": str(relative),
                "symbol": str(item["symbol"]),
                "code": str(item["code"]),
                "year": int(item["year"]),
                "rows": int(len(out)),
                "output_byte_sha256": _sha256(path),
                "output_frame_sha256": c74._frame_sha256(out),
                "joint_clean_path": str(item["path"]),
                "joint_clean_byte_sha256": str(item["output_byte_sha256"]),
                "raw_source_path": str(raw_item["path"]),
                "raw_source_manifest_byte_sha256": str(raw_item["byte_sha256"]),
                "raw_source_rows": int(raw_item["rows"]),
                "source_fields_read": list(RAW_COLUMNS),
                "factor_eligible_rows": {FACTOR_NAME: eligible},
                "quality": {
                    "base_rows": int(len(out)),
                    f"{FACTOR_NAME}__eligible_rows": eligible,
                    f"{FACTOR_NAME}__missing_rows": missing,
                    **quality_by_index[index],
                },
                "protocol_sha256": PROTOCOL_SHA256,
                "implementation_freeze_sha256": _sha256(DEFAULT_IMPLEMENTATION_FREEZE),
                "daily_price_fields_read": [],
                "forward_return_fields_read": False,
                "comparison_factor_values_read": False,
                "provider_request_issued": False,
            }
        print(
            f"Campaign080 built year={year} partitions={len(by_year[year])} "
            f"eligible_rows={totals['eligible']}",
            flush=True,
        )
    completed = [record for record in records if record is not None]
    if (
        len(completed) != EXPECTED_PARTITIONS
        or sum(int(record["rows"]) for record in completed) != EXPECTED_ROWS
    ):
        raise Campaign080FeatureError("Campaign080 publication totals changed")
    digest_rows = [
        [
            record["relative_path"],
            record["output_byte_sha256"],
            record["output_frame_sha256"],
            record["rows"],
        ]
        for record in completed
    ]
    manifest = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign080_feature_snapshot",
        "status": "feature_library_complete_pending_ordered_no_return_gates",
        "output_run_id": OUTPUT_RUN_ID,
        "dataset_sha256": _json_digest(digest_rows),
        "partitions": EXPECTED_PARTITIONS,
        "rows": EXPECTED_ROWS,
        "files": completed,
        "factor_names": [FACTOR_NAME],
        "factor_directions": {FACTOR_NAME: "higher"},
        "factor_ranges": {FACTOR_NAME: [0.0, 1.0]},
        "factor_upper_endpoint_exclusive": {FACTOR_NAME: False},
        "factor_formulas": {FACTOR_NAME: FACTOR_FORMULA},
        "factor_eligible_rows": {FACTOR_NAME: totals["eligible"]},
        "quality": {
            "base_rows": EXPECTED_ROWS,
            f"{FACTOR_NAME}__eligible_rows": totals["eligible"],
            f"{FACTOR_NAME}__missing_rows": totals["missing"],
            "raw_source_rows_read": totals["source_rows"],
            "raw_source_sessions": totals["source_sessions"],
            "invalid_amount_grid_sessions": totals["invalid_amount_grid_sessions"],
            "nonpositive_total_amount_sessions": totals[
                "nonpositive_total_amount_sessions"
            ],
        },
        "source_fields_read": list(RAW_COLUMNS),
        "joint_clean_identity_fields_read": list(IDENTITY_COLUMNS),
        "source_selected_bar_count": SELECTED_BAR_COUNT,
        "source_minute_grid": "09:30 plus 09:31-11:30 and 13:01-15:00; factor excludes 09:30",
        "median_order_statistics_one_indexed": [120, 121],
        "state_rule": "amount strictly greater than ordinary full-session median",
        "lunch_boundary_rule": "longest runs computed separately on positions 0..119 and 120..239",
        "maximum_run_length": HALF_SESSION_BAR_COUNT,
        "amount_longest_run_rule": FACTOR_FORMULA,
        "raw_manifest_sha256": RAW_MANIFEST_SHA256,
        "joint_clean_manifest_sha256": CLEAN_MANIFEST_SHA256,
        "joint_clean_dataset_sha256": CLEAN_DATASET_SHA256,
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
    c74._atomic_json(manifest, manifest_path)
    return manifest_path


def _validate_manifest(manifest: dict[str, Any]) -> None:
    files = list(manifest.get("files") or [])
    eligible = (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    quality = manifest.get("quality") or {}
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign080_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and len(files) == EXPECTED_PARTITIONS
        and manifest.get("rows") == EXPECTED_ROWS
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == {FACTOR_NAME: "higher"}
        and manifest.get("factor_ranges") == {FACTOR_NAME: [0.0, 1.0]}
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("joint_clean_identity_fields_read") == list(IDENTITY_COLUMNS)
        and manifest.get("source_selected_bar_count") == SELECTED_BAR_COUNT
        and manifest.get("median_order_statistics_one_indexed") == [120, 121]
        and manifest.get("maximum_run_length") == HALF_SESSION_BAR_COUNT
        and manifest.get("amount_longest_run_rule") == FACTOR_FORMULA
        and manifest.get("protocol_sha256") == PROTOCOL_SHA256
        and manifest.get("mechanism_overlap_audit_sha256")
        == MECHANISM_AUDIT_SHA256
        and quality.get("base_rows") == EXPECTED_ROWS
        and quality.get(f"{FACTOR_NAME}__eligible_rows") == eligible
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("candidate49_ledgers_changed") is False
        and manifest.get("provider_request_issued") is False
    ):
        raise Campaign080FeatureError("Campaign080 manifest semantics changed")


def verify_snapshot_files(
    manifest_path: Path, *, workers: int = 4
) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    expected = (output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json").resolve()
    if manifest_path != expected:
        raise Campaign080FeatureError("Campaign080 manifest path changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_manifest(manifest)
    partition_root = (manifest_path.parent / "partitions").resolve()

    def verify(item: dict[str, Any]) -> tuple[int, int]:
        path = Path(str(item["path"])).expanduser().resolve()
        path.relative_to(partition_root)
        if _sha256(path) != item["output_byte_sha256"]:
            raise Campaign080FeatureError(f"partition byte hash changed: {path}")
        frame = pd.read_parquet(path)
        if (
            len(frame) != item["rows"]
            or c74._frame_sha256(frame) != item["output_frame_sha256"]
        ):
            raise Campaign080FeatureError(f"partition frame changed: {path}")
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
    if (
        _json_digest(digest_rows) != manifest["dataset_sha256"]
        or len(verified) != EXPECTED_PARTITIONS
        or sum(rows for rows, _eligible in verified) != EXPECTED_ROWS
        or sum(eligible_rows for _rows, eligible_rows in verified)
        != (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    ):
        raise Campaign080FeatureError("Campaign080 aggregate identity changed")
    return {
        "status": "verified",
        "partitions": len(verified),
        "rows": sum(rows for rows, _eligible in verified),
        "eligible_rows": sum(eligible for _rows, eligible in verified),
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
        "source_fields_read_by_status": [],
        "candidate_or_comparison_values_read_by_status": False,
        "historical_daily_price_or_forward_return_values_read_by_status": False,
        "provider_request_issued_by_status": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    build.add_argument("--workers", type=int, default=4)
    inspect = sub.add_parser("status")
    inspect.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    verify = sub.add_parser("verify")
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
