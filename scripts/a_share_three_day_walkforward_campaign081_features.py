#!/usr/bin/env python3
"""Build Campaign081's intraday amount-path-efficiency snapshot without returns."""

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
from scripts import a_share_three_day_walkforward_campaign080_features as c80


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = c74.DEFAULT_DATA_ROOT
DEFAULT_PROTOCOL = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_081_no_return_preregistration.json"
DEFAULT_IMPLEMENTATION_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_081_feature_implementation_freeze_20260806.json"
DEFAULT_CALENDAR = c74.DEFAULT_CALENDAR
RAW_MANIFEST_RELATIVE = c74.RAW_MANIFEST_RELATIVE
CLEAN_MANIFEST_RELATIVE = c74.CLEAN_MANIFEST_RELATIVE

FACTOR_NAME = "intraday_amount_path_efficiency_238p"
FACTOR_FORMULA = (
    "x_i=log1p(amount_i); sum of absolute half-session endpoint displacements "
    "divided by summed absolute within-half variation over 238 transitions"
)
PROTOCOL_SHA256 = "84400ac6f7dca933333dcfbd314753328e9e00f905d94c68632528c8767a6853"
MECHANISM_AUDIT_SHA256 = "cd8700591703f2b35ecf33103bbc26d092fefd90d3aa33b15fa78d4dfdb873c1"
NUMERIC_POLICY_SHA256 = "ac8c3a4aa6a0ea62aea0d3294ca522ce47b4fe38c83e059a32db31a4f07085e8"
CURRENT_STATE_SHA256 = "6faab964c6a35ccfba859844b12a5caf7471be37dae910438dd8aa69d76d9309"
RAW_MANIFEST_SHA256 = c74.RAW_MANIFEST_SHA256
CLEAN_MANIFEST_SHA256 = c74.CLEAN_MANIFEST_SHA256
CLEAN_DATASET_SHA256 = c74.CLEAN_DATASET_SHA256
CALENDAR_SHA256 = c74.CALENDAR_SHA256
EXPECTED_PARTITIONS = c74.EXPECTED_PARTITIONS
EXPECTED_ROWS = c74.EXPECTED_ROWS
FULL_DEFINITION_COUNT = 112
FULL_DEFINITION_ORDER_SHA256 = "a31457db36af9a8ddac4e08890c87f50ef6554bb46918f022749bd9cccbc1c55"
COMPARISON_COUNT = 110
COMPARISON_ORDER_SHA256 = "dc6319ac2f7c9d5811a8bee3f8fd9dbd174d2451739ef201aad31c36a9f25ce3"
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign081_feature_library_v1"
)

RAW_COLUMNS = c74.RAW_COLUMNS
IDENTITY_COLUMNS = c74.IDENTITY_COLUMNS
CONTINUOUS_MINUTE_CODES = c74.CONTINUOUS_MINUTE_CODES
CONTINUOUS_MINUTE_CODE_SET = c74.CONTINUOUS_MINUTE_CODE_SET
SOURCE_MINUTE_CODE_SET = c74.SOURCE_MINUTE_CODE_SET
SELECTED_BAR_COUNT = c74.SELECTED_BAR_COUNT
SOURCE_BAR_COUNT = c74.SOURCE_BAR_COUNT
HALF_SESSION_BAR_COUNT = 120
WITHIN_HALF_TRANSITION_COUNT = 119
POOLED_TRANSITION_COUNT = 238
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
C80_FACTOR = c80.FACTOR_NAME
C80_BINDING_PATH = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_080_feature_snapshot_binding_20260806.json"
C80_BINDING_SHA256 = "2e12b961571639f12768687d53408b5f4d48e8b63148a4950a5cd2b54d4e2887"
C80_MANIFEST_PATH = c80.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
C80_MANIFEST_SHA256 = "64c883cc669425f9b8ab49ad2885de7c4239d7dc49f9944dab0ee3241f2c84b7"
C80_DATASET_SHA256 = "53c89fa15b46e21269c8956284707fe6bde09e77ca308d3506a3336d40e6ef62"


class Campaign081FeatureError(RuntimeError):
    """Fail-closed Campaign081 feature error."""


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
        raise Campaign081FeatureError(f"Campaign081 {label} changed: {path}")


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = c80.reconstruct_comparisons()
    items.append({"name": C80_FACTOR, "score_direction": "higher"})
    if (
        len(items) != COMPARISON_COUNT
        or _comparison_order_digest(items) != COMPARISON_ORDER_SHA256
    ):
        raise Campaign081FeatureError("Campaign081 numeric comparison order changed")
    return items


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = c80.reconstruct_complete_definitions()
    items.append({"name": C80_FACTOR, "score_direction": "higher"})
    if (
        len(items) != FULL_DEFINITION_COUNT
        or _comparison_order_digest(items) != FULL_DEFINITION_ORDER_SHA256
    ):
        raise Campaign081FeatureError("Campaign081 complete definition order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    _require(path, PROTOCOL_SHA256, "protocol")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign081FeatureError("Campaign081 protocol binding failed")
    for required, expected, label in (
        (C80_BINDING_PATH, C80_BINDING_SHA256, "Campaign080 snapshot binding"),
        (C80_MANIFEST_PATH, C80_MANIFEST_SHA256, "Campaign080 snapshot manifest"),
    ):
        _require(required, expected, label)
    previous = json.loads(C80_MANIFEST_PATH.read_text(encoding="utf-8"))
    spec = json.loads(path.read_text(encoding="utf-8"))
    chain = spec.get("source_chain") or {}
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    unique = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    c80_link = chain.get("campaign080_terminal_numeric_comparator") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign081_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign081_minute_source_candidate_comparison_daily_price_or_return_values"
        and (chain.get("numeric_comparator_policy_v16") or {}).get("sha256")
        == NUMERIC_POLICY_SHA256
        and (chain.get("authoritative_iteration_state") or {}).get("sha256")
        == CURRENT_STATE_SHA256
        and c80_link.get("factor") == C80_FACTOR
        and c80_link.get("score_direction") == "higher"
        and c80_link.get("dataset_sha256") == C80_DATASET_SHA256
        and previous.get("dataset_sha256") == C80_DATASET_SHA256
        and previous.get("factor_names") == [C80_FACTOR]
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and tuple(candidate.get("minute_source_projection") or ()) == RAW_COLUMNS
        and tuple(candidate.get("stock_day_identity_projection") or ())
        == IDENTITY_COLUMNS
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("half_session_bar_count") == HALF_SESSION_BAR_COUNT
        and candidate.get("within_half_transition_count")
        == WITHIN_HALF_TRANSITION_COUNT
        and candidate.get("pooled_transition_count") == POOLED_TRANSITION_COUNT
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
        and unique.get("all_110_numeric_comparators_must_pass") is True
        and len(reconstruct_comparisons()) == COMPARISON_COUNT
        and len(reconstruct_complete_definitions()) == FULL_DEFINITION_COUNT
        and finite.get("trial_id")
        == "wf081_intraday_amount_path_efficiency_238p_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("expected_trial_count") == 1
        and boundary.get("comparison_values_read_before_coverage_pass") is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign081FeatureError("Campaign081 protocol semantics changed")
    return spec


def extract_amount_path_efficiency(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign081FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    empty = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "amount_path_efficiency": pd.Series(dtype="float64"),
        }
    )
    quality = {
        "source_rows": 0,
        "source_sessions": 0,
        "valid_amount_path_efficiency_sessions": 0,
        "invalid_amount_grid_sessions": 0,
        "zero_total_variation_sessions": 0,
        "invalid_path_score_sessions": 0,
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
        raise Campaign081FeatureError(f"raw minute identity changed for {symbol}")
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
        raise Campaign081FeatureError(f"raw minute grid changed for {symbol}")
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
        raise Campaign081FeatureError(f"continuous minute grid changed for {symbol}")
    matrix = continuous["amount"].to_numpy(dtype=np.float64).reshape(
        len(dates), SELECTED_BAR_COUNT
    )
    amount_valid = np.isfinite(matrix).all(axis=1) & (matrix >= 0.0).all(axis=1)
    score = np.full(len(dates), np.nan, dtype=np.float64)
    zero_variation = np.zeros(len(dates), dtype=bool)
    invalid_path_score = np.zeros(len(dates), dtype=bool)
    if amount_valid.any():
        accepted = matrix[amount_valid]
        transformed = np.log1p(accepted)
        morning = transformed[:, :HALF_SESSION_BAR_COUNT]
        afternoon = transformed[:, HALF_SESSION_BAR_COUNT:]
        endpoint = np.abs(morning[:, -1] - morning[:, 0]) + np.abs(
            afternoon[:, -1] - afternoon[:, 0]
        )
        variation = np.abs(np.diff(morning, axis=1)).sum(
            axis=1, dtype=np.float64
        ) + np.abs(np.diff(afternoon, axis=1)).sum(axis=1, dtype=np.float64)
        denominator_valid = np.isfinite(variation) & (variation > 0.0)
        candidate_score = np.full(len(accepted), np.nan, dtype=np.float64)
        candidate_score[denominator_valid] = (
            endpoint[denominator_valid] / variation[denominator_valid]
        )
        candidate_valid = (
            denominator_valid
            & np.isfinite(endpoint)
            & np.isfinite(candidate_score)
            & (candidate_score >= 0.0)
            & (candidate_score <= 1.0)
        )
        accepted_positions = np.flatnonzero(amount_valid)
        score[accepted_positions[candidate_valid]] = candidate_score[candidate_valid]
        zero_variation[accepted_positions] = np.isfinite(variation) & (
            variation == 0.0
        )
        invalid_path_score[accepted_positions] = denominator_valid & ~candidate_valid
    range_valid = np.isfinite(score) & (score >= 0.0) & (score <= 1.0)
    score[~range_valid] = np.nan
    return pd.DataFrame(
        {"trade_date": dates, "amount_path_efficiency": score}
    ), {
        "source_rows": int(len(work)),
        "source_sessions": int(len(dates)),
        "valid_amount_path_efficiency_sessions": int(range_valid.sum()),
        "invalid_amount_grid_sessions": int((~amount_valid).sum()),
        "zero_total_variation_sessions": int(zero_variation.sum()),
        "invalid_path_score_sessions": int(invalid_path_score.sum()),
    }


def attach_amount_path_efficiency(
    identity: pd.DataFrame, values: pd.DataFrame, *, symbol: str
) -> pd.DataFrame:
    if tuple(identity.columns) != IDENTITY_COLUMNS:
        raise Campaign081FeatureError(f"identity projection changed for {symbol}")
    base = identity.copy()
    base["trade_date"] = pd.to_datetime(
        base["trade_date"], errors="coerce"
    ).dt.normalize()
    base["symbol"] = base["symbol"].astype(str).str.upper()
    base["provider"] = base["provider"].astype(str).str.lower()
    if base.empty:
        base["amount_path_efficiency"] = pd.Series(dtype="float64")
        return base
    if (
        base["trade_date"].isna().any()
        or base.duplicated(["trade_date", "symbol"]).any()
        or set(base["symbol"].unique()) != {symbol.upper()}
        or set(base["provider"].unique()) != {"tushare"}
    ):
        raise Campaign081FeatureError(f"joint-clean identity changed for {symbol}")
    if values.empty or values.duplicated(["trade_date"]).any():
        raise Campaign081FeatureError(f"Campaign081 value identity changed for {symbol}")
    out = base.merge(values, on="trade_date", how="left", validate="one_to_one")
    if any(date not in set(values["trade_date"].tolist()) for date in out["trade_date"]):
        raise Campaign081FeatureError(
            f"accepted session absent from raw source for {symbol}"
        )
    return out


def finalize_feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = (*IDENTITY_COLUMNS, "amount_path_efficiency")
    if not set(required).issubset(frame.columns):
        raise Campaign081FeatureError("Campaign081 input columns changed")
    work = frame.copy()
    values = pd.to_numeric(work["amount_path_efficiency"], errors="coerce")
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
        raise Campaign081FeatureError("Campaign081 output columns changed")
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"].astype(bool)
    if (
        values[eligible].isna().any()
        or ((values[eligible] < 0.0) | (values[eligible] > 1.0)).any()
        or values[~eligible].notna().any()
    ):
        raise Campaign081FeatureError("Campaign081 value semantics changed")
    return int(len(frame)), int(eligible.sum())


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived/a_share/rich/tushare/minute_walkforward_campaign081_feature_library"
        / OUTPUT_RUN_ID
    )


def _validate_implementation_freeze() -> dict[str, Any]:
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign081FeatureError("Campaign081 implementation freeze is absent")
    freeze = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    test = freeze.get("tests") or {}
    test_path = REPO_ROOT / str(test.get("path") or "")
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign081_feature_implementation_freeze"
        and freeze.get("status")
        == "frozen_before_campaign081_minute_source_values"
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
        raise Campaign081FeatureError("Campaign081 implementation freeze changed")
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
        raise Campaign081FeatureError(f"raw partition changed: {raw_path}")
    raw = pd.read_parquet(raw_path, columns=list(RAW_COLUMNS))
    values, quality = extract_amount_path_efficiency(raw, symbol=symbol)
    out = attach_amount_path_efficiency(identity, values, symbol=symbol)
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
        raise Campaign081FeatureError("Campaign081 snapshot already exists; verify instead")
    records: list[dict[str, Any] | None] = [None] * len(files)
    totals = {
        "eligible": 0,
        "missing": 0,
        "source_rows": 0,
        "source_sessions": 0,
        "invalid_amount_grid_sessions": 0,
        "zero_total_variation_sessions": 0,
        "invalid_path_score_sessions": 0,
    }
    for year in sorted(by_year):
        jobs = []
        for index, item in by_year[year]:
            raw_item = raw_by_key.get((str(item["symbol"]).upper(), int(item["year"])))
            if raw_item is None:
                raise Campaign081FeatureError("raw partition missing")
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
                    "zero_total_variation_sessions",
                    "invalid_path_score_sessions",
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
                "kind": "a_share_three_day_walkforward_campaign081_feature_partition",
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
            f"Campaign081 built year={year} partitions={len(by_year[year])} "
            f"eligible_rows={totals['eligible']}",
            flush=True,
        )
    completed = [record for record in records if record is not None]
    if (
        len(completed) != EXPECTED_PARTITIONS
        or sum(int(record["rows"]) for record in completed) != EXPECTED_ROWS
    ):
        raise Campaign081FeatureError("Campaign081 publication totals changed")
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
        "kind": "a_share_three_day_walkforward_campaign081_feature_snapshot",
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
            "zero_total_variation_sessions": totals["zero_total_variation_sessions"],
            "invalid_path_score_sessions": totals["invalid_path_score_sessions"],
        },
        "source_fields_read": list(RAW_COLUMNS),
        "joint_clean_identity_fields_read": list(IDENTITY_COLUMNS),
        "source_selected_bar_count": SELECTED_BAR_COUNT,
        "source_minute_grid": "09:30 plus 09:31-11:30 and 13:01-15:00; factor excludes 09:30",
        "amount_transform": "numpy.log1p(float64 nonnegative amount)",
        "within_half_transition_count": WITHIN_HALF_TRANSITION_COUNT,
        "pooled_transition_count": POOLED_TRANSITION_COUNT,
        "lunch_boundary_rule": "endpoint displacement and variation computed separately on positions 0..119 and 120..239",
        "amount_path_efficiency_rule": FACTOR_FORMULA,
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
        == "a_share_three_day_walkforward_campaign081_feature_snapshot"
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
        and manifest.get("amount_transform")
        == "numpy.log1p(float64 nonnegative amount)"
        and manifest.get("within_half_transition_count")
        == WITHIN_HALF_TRANSITION_COUNT
        and manifest.get("pooled_transition_count") == POOLED_TRANSITION_COUNT
        and manifest.get("amount_path_efficiency_rule") == FACTOR_FORMULA
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
        raise Campaign081FeatureError("Campaign081 manifest semantics changed")


def verify_snapshot_files(
    manifest_path: Path, *, workers: int = 4
) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    expected = (output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json").resolve()
    if manifest_path != expected:
        raise Campaign081FeatureError("Campaign081 manifest path changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_manifest(manifest)
    partition_root = (manifest_path.parent / "partitions").resolve()

    def verify(item: dict[str, Any]) -> tuple[int, int]:
        path = Path(str(item["path"])).expanduser().resolve()
        path.relative_to(partition_root)
        if _sha256(path) != item["output_byte_sha256"]:
            raise Campaign081FeatureError(f"partition byte hash changed: {path}")
        frame = pd.read_parquet(path)
        if (
            len(frame) != item["rows"]
            or c74._frame_sha256(frame) != item["output_frame_sha256"]
        ):
            raise Campaign081FeatureError(f"partition frame changed: {path}")
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
        raise Campaign081FeatureError("Campaign081 aggregate identity changed")
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
