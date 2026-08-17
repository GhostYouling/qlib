#!/usr/bin/env python3
"""Build Campaign082's range/amount peak-timing-alignment snapshot without returns."""

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
from scripts import a_share_three_day_walkforward_campaign081_features as c81


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = c74.DEFAULT_DATA_ROOT
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_082_no_return_preregistration.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_082_feature_implementation_freeze_20260806.json"
)

FACTOR_NAME = "intraday_range_amount_peak_timing_alignment_240m"
FACTOR_FORMULA = (
    "r_i=log(high_i/low_i); i_range=last_argmax(r_i); "
    "i_amount=last_argmax(amount_i); 1-abs(i_range-i_amount)/239"
)
PROTOCOL_SHA256 = "acc55fb8b3a4b79f005ab23033dccb781dca1fd71b162a71dfeb04f7aa91bf88"
MECHANISM_AUDIT_SHA256 = (
    "1bd30fc809c54eb1503fd30170313cd0d5a3b567f4d9875bc0f60e2ce944f282"
)
NUMERIC_POLICY_SHA256 = (
    "32b863a9e10ff26c665a9854f0863bb38e6b91dda25115cb44a57b452f97db36"
)
CURRENT_STATE_SHA256 = (
    "43969f9d6e4610b54f947904cdbc4672af6451973ccf37affc0d358970dbed8d"
)
RAW_MANIFEST_SHA256 = c74.RAW_MANIFEST_SHA256
CLEAN_MANIFEST_SHA256 = c74.CLEAN_MANIFEST_SHA256
CLEAN_DATASET_SHA256 = c74.CLEAN_DATASET_SHA256
EXPECTED_PARTITIONS = c74.EXPECTED_PARTITIONS
EXPECTED_ROWS = c74.EXPECTED_ROWS
FULL_DEFINITION_COUNT = 113
FULL_DEFINITION_ORDER_SHA256 = (
    "0938f041bcdd591bc8977204d78df502514aa1230942199b006e8fd72bdb68a2"
)
COMPARISON_COUNT = 111
COMPARISON_ORDER_SHA256 = (
    "591432918754f7da24f468d152bbbc1b337127dd5fdc30f0f214ea776ca757aa"
)
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign082_feature_library_v1"
)

RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low", "amount")
IDENTITY_COLUMNS = c74.IDENTITY_COLUMNS
CONTINUOUS_MINUTE_CODES = c74.CONTINUOUS_MINUTE_CODES
CONTINUOUS_MINUTE_CODE_SET = c74.CONTINUOUS_MINUTE_CODE_SET
SOURCE_MINUTE_CODE_SET = c74.SOURCE_MINUTE_CODE_SET
SELECTED_BAR_COUNT = c74.SELECTED_BAR_COUNT
SOURCE_BAR_COUNT = c74.SOURCE_BAR_COUNT
NORMALIZATION_DISTANCE = 239.0
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
C81_FACTOR = c81.FACTOR_NAME
C81_BINDING_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_081_feature_snapshot_binding_20260806.json"
)
C81_BINDING_SHA256 = "d7de059bb486189b3a29ebda76c42362120cabaac9b23460df444cf781393fad"
C81_MANIFEST_PATH = c81.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
C81_MANIFEST_SHA256 = "fb8bed1defb00cffb4508e78b74ad79a00e4d9dad64c7a9b48c5de206051f1ab"
C81_DATASET_SHA256 = "7fecf302d703fd040ae710a31f5fb78949d60a021751cf94414aec607d73eeac"


class Campaign082FeatureError(RuntimeError):
    """Fail-closed Campaign082 feature error."""


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
        raise Campaign082FeatureError(f"Campaign082 {label} changed: {path}")


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = c81.reconstruct_comparisons()
    items.append({"name": C81_FACTOR, "score_direction": "higher"})
    if (
        len(items) != COMPARISON_COUNT
        or _comparison_order_digest(items) != COMPARISON_ORDER_SHA256
    ):
        raise Campaign082FeatureError("Campaign082 numeric comparison order changed")
    return items


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = c81.reconstruct_complete_definitions()
    items.append({"name": C81_FACTOR, "score_direction": "higher"})
    if (
        len(items) != FULL_DEFINITION_COUNT
        or _comparison_order_digest(items) != FULL_DEFINITION_ORDER_SHA256
    ):
        raise Campaign082FeatureError("Campaign082 complete definition order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    _require(path, PROTOCOL_SHA256, "protocol")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign082FeatureError("Campaign082 protocol binding failed")
    _require(C81_BINDING_PATH, C81_BINDING_SHA256, "Campaign081 snapshot binding")
    _require(C81_MANIFEST_PATH, C81_MANIFEST_SHA256, "Campaign081 snapshot manifest")
    previous = json.loads(C81_MANIFEST_PATH.read_text(encoding="utf-8"))
    spec = json.loads(path.read_text(encoding="utf-8"))
    chain = spec.get("source_chain") or {}
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    unique = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    c81_link = chain.get("campaign081_terminal_numeric_comparator") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign082_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign082_minute_source_candidate_comparison_daily_price_or_return_values"
        and (chain.get("numeric_comparator_policy_v17") or {}).get("sha256")
        == NUMERIC_POLICY_SHA256
        and (chain.get("authoritative_iteration_state") or {}).get("sha256")
        == CURRENT_STATE_SHA256
        and c81_link.get("factor") == C81_FACTOR
        and c81_link.get("score_direction") == "higher"
        and c81_link.get("dataset_sha256") == C81_DATASET_SHA256
        and previous.get("dataset_sha256") == C81_DATASET_SHA256
        and previous.get("factor_names") == [C81_FACTOR]
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and tuple(candidate.get("minute_source_projection") or ()) == RAW_COLUMNS
        and tuple(candidate.get("stock_day_identity_projection") or ())
        == IDENTITY_COLUMNS
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
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
        and unique.get("all_111_numeric_comparators_must_pass") is True
        and len(reconstruct_comparisons()) == COMPARISON_COUNT
        and len(reconstruct_complete_definitions()) == FULL_DEFINITION_COUNT
        and finite.get("trial_id")
        == "wf082_intraday_range_amount_peak_timing_alignment_240m_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("expected_trial_count") == 1
        and boundary.get("comparison_values_read_before_coverage_pass") is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign082FeatureError("Campaign082 protocol semantics changed")
    return spec


def extract_range_amount_peak_timing_alignment(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign082FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    empty = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "peak_timing_alignment": pd.Series(dtype="float64"),
        }
    )
    quality = {
        "source_rows": 0,
        "source_sessions": 0,
        "valid_peak_timing_alignment_sessions": 0,
        "invalid_high_low_grid_sessions": 0,
        "invalid_amount_grid_sessions": 0,
        "nonpositive_maximum_range_sessions": 0,
        "nonpositive_maximum_amount_sessions": 0,
        "invalid_alignment_score_sessions": 0,
    }
    if raw.empty:
        return empty, quality
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    for column in ("high", "low", "amount"):
        work[column] = pd.to_numeric(work[column], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign082FeatureError(f"raw minute identity changed for {symbol}")
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
        raise Campaign082FeatureError(f"raw minute grid changed for {symbol}")
    continuous = work.loc[
        work["minute_code"].isin(CONTINUOUS_MINUTE_CODE_SET),
        ["trade_date", "minute_code", "high", "low", "amount"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"], categories=CONTINUOUS_MINUTE_CODES, ordered=True
    )
    continuous = continuous.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(counts.index).normalize()
    if len(continuous) != len(dates) * SELECTED_BAR_COUNT:
        raise Campaign082FeatureError(f"continuous minute grid changed for {symbol}")
    highs = (
        continuous["high"]
        .to_numpy(dtype=np.float64)
        .reshape(len(dates), SELECTED_BAR_COUNT)
    )
    lows = (
        continuous["low"]
        .to_numpy(dtype=np.float64)
        .reshape(len(dates), SELECTED_BAR_COUNT)
    )
    amounts = (
        continuous["amount"]
        .to_numpy(dtype=np.float64)
        .reshape(len(dates), SELECTED_BAR_COUNT)
    )
    price_valid = (
        np.isfinite(highs).all(axis=1)
        & np.isfinite(lows).all(axis=1)
        & (highs > 0.0).all(axis=1)
        & (lows > 0.0).all(axis=1)
        & (lows <= highs).all(axis=1)
    )
    amount_valid = np.isfinite(amounts).all(axis=1) & (amounts >= 0.0).all(axis=1)
    score = np.full(len(dates), np.nan, dtype=np.float64)
    positive_range = np.zeros(len(dates), dtype=bool)
    positive_amount = np.zeros(len(dates), dtype=bool)
    valid_inputs = price_valid & amount_valid
    if valid_inputs.any():
        accepted_positions = np.flatnonzero(valid_inputs)
        ranges = np.log(highs[valid_inputs] / lows[valid_inputs])
        accepted_amounts = amounts[valid_inputs]
        max_ranges = np.max(ranges, axis=1)
        max_amounts = np.max(accepted_amounts, axis=1)
        positive_range[accepted_positions] = np.isfinite(max_ranges) & (
            max_ranges > 0.0
        )
        positive_amount[accepted_positions] = np.isfinite(max_amounts) & (
            max_amounts > 0.0
        )
        eligible_local = (max_ranges > 0.0) & (max_amounts > 0.0)
        if eligible_local.any():
            selected = accepted_positions[eligible_local]
            selected_ranges = ranges[eligible_local]
            selected_amounts = accepted_amounts[eligible_local]
            range_last = (
                SELECTED_BAR_COUNT - 1 - np.argmax(selected_ranges[:, ::-1], axis=1)
            )
            amount_last = (
                SELECTED_BAR_COUNT - 1 - np.argmax(selected_amounts[:, ::-1], axis=1)
            )
            candidate = 1.0 - np.abs(range_last - amount_last) / NORMALIZATION_DISTANCE
            candidate_valid = (
                np.isfinite(candidate) & (candidate >= 0.0) & (candidate <= 1.0)
            )
            score[selected[candidate_valid]] = candidate[candidate_valid]
    valid_score = np.isfinite(score) & (score >= 0.0) & (score <= 1.0)
    score[~valid_score] = np.nan
    return pd.DataFrame({"trade_date": dates, "peak_timing_alignment": score}), {
        "source_rows": int(len(work)),
        "source_sessions": int(len(dates)),
        "valid_peak_timing_alignment_sessions": int(valid_score.sum()),
        "invalid_high_low_grid_sessions": int((~price_valid).sum()),
        "invalid_amount_grid_sessions": int((~amount_valid).sum()),
        "nonpositive_maximum_range_sessions": int(
            (valid_inputs & ~positive_range).sum()
        ),
        "nonpositive_maximum_amount_sessions": int(
            (valid_inputs & ~positive_amount).sum()
        ),
        "invalid_alignment_score_sessions": int(
            (valid_inputs & positive_range & positive_amount & ~valid_score).sum()
        ),
    }


def attach_values(
    identity: pd.DataFrame, values: pd.DataFrame, *, symbol: str
) -> pd.DataFrame:
    if tuple(identity.columns) != IDENTITY_COLUMNS:
        raise Campaign082FeatureError(f"identity projection changed for {symbol}")
    base = identity.copy()
    base["trade_date"] = pd.to_datetime(
        base["trade_date"], errors="coerce"
    ).dt.normalize()
    base["symbol"] = base["symbol"].astype(str).str.upper()
    base["provider"] = base["provider"].astype(str).str.lower()
    if base.empty:
        base["peak_timing_alignment"] = pd.Series(dtype="float64")
        return base
    if (
        base["trade_date"].isna().any()
        or base.duplicated(["trade_date", "symbol"]).any()
        or set(base["symbol"].unique()) != {symbol.upper()}
        or set(base["provider"].unique()) != {"tushare"}
    ):
        raise Campaign082FeatureError(f"joint-clean identity changed for {symbol}")
    if values.empty or values.duplicated(["trade_date"]).any():
        raise Campaign082FeatureError(
            f"Campaign082 value identity changed for {symbol}"
        )
    out = base.merge(values, on="trade_date", how="left", validate="one_to_one")
    if any(
        date not in set(values["trade_date"].tolist()) for date in out["trade_date"]
    ):
        raise Campaign082FeatureError(
            f"accepted session absent from raw source for {symbol}"
        )
    return out


def finalize_feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = (*IDENTITY_COLUMNS, "peak_timing_alignment")
    if not set(required).issubset(frame.columns):
        raise Campaign082FeatureError("Campaign082 input columns changed")
    work = frame.copy()
    values = pd.to_numeric(work["peak_timing_alignment"], errors="coerce")
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
        raise Campaign082FeatureError("Campaign082 output columns changed")
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"].astype(bool)
    if (
        values[eligible].isna().any()
        or ((values[eligible] < 0.0) | (values[eligible] > 1.0)).any()
        or values[~eligible].notna().any()
    ):
        raise Campaign082FeatureError("Campaign082 value semantics changed")
    return int(len(frame)), int(eligible.sum())


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived/a_share/rich/tushare/minute_walkforward_campaign082_feature_library"
        / OUTPUT_RUN_ID
    )


def _validate_implementation_freeze() -> dict[str, Any]:
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign082FeatureError("Campaign082 implementation freeze is absent")
    freeze = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    test = freeze.get("tests") or {}
    test_path = REPO_ROOT / str(test.get("path") or "")
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign082_feature_implementation_freeze"
        and freeze.get("status") == "frozen_before_campaign082_minute_source_values"
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
        raise Campaign082FeatureError("Campaign082 implementation freeze changed")
    return freeze


def _load_attached(
    index: int, clean_item: dict[str, Any], raw_item: dict[str, Any]
) -> tuple[int, pd.DataFrame, dict[str, int]]:
    symbol = str(clean_item["symbol"]).upper()
    identity = pd.read_parquet(clean_item["path"], columns=list(IDENTITY_COLUMNS))
    raw_path = Path(str(raw_item["path"])).expanduser().resolve()
    if not raw_path.is_file() or pq.ParquetFile(raw_path).metadata.num_rows != int(
        raw_item["rows"]
    ):
        raise Campaign082FeatureError(f"raw partition changed: {raw_path}")
    raw = pd.read_parquet(raw_path, columns=list(RAW_COLUMNS))
    values, quality = extract_range_amount_peak_timing_alignment(raw, symbol=symbol)
    out = attach_values(identity, values, symbol=symbol)
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
        raise Campaign082FeatureError(
            "Campaign082 snapshot already exists; verify instead"
        )
    records: list[dict[str, Any] | None] = [None] * len(files)
    totals = {
        "eligible": 0,
        "missing": 0,
        "source_rows": 0,
        "source_sessions": 0,
        "invalid_high_low_grid_sessions": 0,
        "invalid_amount_grid_sessions": 0,
        "nonpositive_maximum_range_sessions": 0,
        "nonpositive_maximum_amount_sessions": 0,
        "invalid_alignment_score_sessions": 0,
    }
    for year in sorted(by_year):
        jobs = []
        for index, item in by_year[year]:
            raw_item = raw_by_key.get((str(item["symbol"]).upper(), int(item["year"])))
            if raw_item is None:
                raise Campaign082FeatureError("raw partition missing")
            jobs.append((index, item, raw_item))
        pieces: list[pd.DataFrame] = []
        quality_by_index: dict[int, dict[str, int]] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = [pool.submit(_load_attached, *job) for job in jobs]
            for future in concurrent.futures.as_completed(futures):
                index, attached, quality = future.result()
                pieces.append(attached)
                quality_by_index[index] = quality
                for key in totals:
                    if key not in {"eligible", "missing"}:
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
            relative = (
                Path("partitions")
                / str(item["symbol"]).lower()
                / f"{int(item['year'])}.parquet"
            )
            path = root / relative
            c74._atomic_parquet(out, path)
            eligible = int(out[f"{FACTOR_NAME}_eligible"].sum())
            missing = int(len(out) - eligible)
            totals["eligible"] += eligible
            totals["missing"] += missing
            raw_item = raw_by_key[(str(item["symbol"]).upper(), int(item["year"]))]
            records[index] = {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign082_feature_partition",
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
            f"Campaign082 built year={year} partitions={len(by_year[year])} "
            f"eligible_rows={totals['eligible']}",
            flush=True,
        )
    completed = [record for record in records if record is not None]
    if (
        len(completed) != EXPECTED_PARTITIONS
        or sum(int(record["rows"]) for record in completed) != EXPECTED_ROWS
    ):
        raise Campaign082FeatureError("Campaign082 publication totals changed")
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
        "kind": "a_share_three_day_walkforward_campaign082_feature_snapshot",
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
            **{
                key: value
                for key, value in totals.items()
                if key not in {"eligible", "missing", "source_rows", "source_sessions"}
            },
        },
        "source_fields_read": list(RAW_COLUMNS),
        "joint_clean_identity_fields_read": list(IDENTITY_COLUMNS),
        "source_selected_bar_count": SELECTED_BAR_COUNT,
        "source_minute_grid": "09:30 plus 09:31-11:30 and 13:01-15:00; factor excludes 09:30",
        "range_rule": "numpy.log(float64 high/low) for all valid selected bars",
        "tie_rule": "last exact occurrence of each maximum via reverse-axis argmax",
        "normalization_distance": NORMALIZATION_DISTANCE,
        "peak_timing_alignment_rule": FACTOR_FORMULA,
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
        == "a_share_three_day_walkforward_campaign082_feature_snapshot"
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
        and manifest.get("normalization_distance") == NORMALIZATION_DISTANCE
        and manifest.get("peak_timing_alignment_rule") == FACTOR_FORMULA
        and manifest.get("protocol_sha256") == PROTOCOL_SHA256
        and manifest.get("mechanism_overlap_audit_sha256") == MECHANISM_AUDIT_SHA256
        and quality.get("base_rows") == EXPECTED_ROWS
        and quality.get(f"{FACTOR_NAME}__eligible_rows") == eligible
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("candidate49_ledgers_changed") is False
        and manifest.get("provider_request_issued") is False
    ):
        raise Campaign082FeatureError("Campaign082 manifest semantics changed")


def verify_snapshot_files(manifest_path: Path, *, workers: int = 4) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    expected = (output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json").resolve()
    if manifest_path != expected:
        raise Campaign082FeatureError("Campaign082 manifest path changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_manifest(manifest)
    partition_root = (manifest_path.parent / "partitions").resolve()

    def verify(item: dict[str, Any]) -> tuple[int, int]:
        path = Path(str(item["path"])).expanduser().resolve()
        path.relative_to(partition_root)
        if _sha256(path) != item["output_byte_sha256"]:
            raise Campaign082FeatureError(f"partition byte hash changed: {path}")
        frame = pd.read_parquet(path)
        if (
            len(frame) != item["rows"]
            or c74._frame_sha256(frame) != item["output_frame_sha256"]
        ):
            raise Campaign082FeatureError(f"partition frame changed: {path}")
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
        or sum(eligible for _rows, eligible in verified)
        != (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    ):
        raise Campaign082FeatureError("Campaign082 aggregate identity changed")
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
