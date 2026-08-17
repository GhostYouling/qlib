#!/usr/bin/env python3
"""Build Campaign073's terminal nominal-price affordability-rank snapshot.

The builder reads only the frozen ``datetime,symbol,provider,close`` minute
projection and the joint-clean stock-day identity.  It never reads daily
prices, forward returns, comparator values, or Candidate49 outcomes.
"""

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

from scripts import a_share_three_day_compact_comparator_cache_v4 as cache_v4
from scripts import a_share_three_day_preregistration_binding_validator as bindings


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_073_no_return_preregistration.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_073_feature_implementation_freeze_20260806.json"
)
DEFAULT_CALENDAR = REPO_ROOT / "data/qlib/cn_a_share/calendars/day.txt"
RAW_MANIFEST_RELATIVE = Path(
    "raw/a_share/rich/tushare/minutes/1m/snapshots/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f/snapshot_manifest.json"
)
CLEAN_MANIFEST_RELATIVE = Path(
    "derived/a_share/rich/tushare/minute_sentiment_clean/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_sentiment_clean_v1/"
    "snapshot_manifest.json"
)

FACTOR_NAME = "intraday_terminal_nominal_share_price_affordability_rank_240m"
FACTOR_FORMULA = (
    "validate 240 continuous-session positive finite closes, select raw 15:00 "
    "nominal CNY close, and return 1 minus its same-day average-tie percentile rank"
)
PROTOCOL_SHA256 = "473373e71a97b9daf25f97062682ec4ad1f8b05a778efad161c887aa586d5280"
MECHANISM_AUDIT_SHA256 = "3f50568eacf9610583c91e531ea2d066b790ac57742d750e92d44308b9988885"
NUMERIC_POLICY_SHA256 = "c936e9df4bd8ac8cdb23ee27d16796a612341c84577ee60f727e8a3cf72cb1db"
RAW_MANIFEST_SHA256 = "9b3d959563c9d182f38981c6a36bdb3bc9b415de08487a9e1f9e850825c0839f"
CLEAN_MANIFEST_SHA256 = "453c6719cb3c7da42fed8807b28a2bfe988700283e9625a6db97912534f368de"
CLEAN_DATASET_SHA256 = "0e4fe7c05536cdfcecc2936bc880726902f5560061188ffff82ef7ee6f346983"
CALENDAR_SHA256 = "fda506597d26bcec953cdc0882042a5046ec1587db60490e16a01627fd43f53a"
EXPECTED_PARTITIONS = 33015
EXPECTED_ROWS = 7724498
FULL_DEFINITION_COUNT = 104
FULL_DEFINITION_ORDER_SHA256 = "45686a0e92d16896d3c1702938f73aa173cb44252d9b76b482623c617d2bda5d"
COMPARISON_COUNT = 103
COMPARISON_ORDER_SHA256 = "28dd90482da7c263873f829e0268fbf4d4fffa53561a9e628797ced4c54991cc"
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign073_feature_library_v1"
)

RAW_COLUMNS = ("datetime", "symbol", "provider", "close")
IDENTITY_COLUMNS = ("trade_date", "symbol", "provider")
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
CONTINUOUS_MINUTE_CODES = tuple(
    [*range(9 * 60 + 31, 11 * 60 + 31), *range(13 * 60 + 1, 15 * 60 + 1)]
)
SOURCE_MINUTE_CODES = (9 * 60 + 30, *CONTINUOUS_MINUTE_CODES)
CONTINUOUS_MINUTE_CODE_SET = frozenset(CONTINUOUS_MINUTE_CODES)
SOURCE_MINUTE_CODE_SET = frozenset(SOURCE_MINUTE_CODES)
SELECTED_BAR_COUNT = 240
SOURCE_BAR_COUNT = 241

C68_FACTOR = "quarterly_profit_revenue_acceleration_rank_gap_2r"
C69_FACTOR = "quarterly_profit_growth_roe_transition_gap_2r"
C70_FACTOR = "quarterly_announcement_delay_improvement_yoy_rank_1y"
C71_FACTOR = "quarterly_net_profit_scale_rank"
C72_FACTOR = "quarterly_joint_profit_revenue_growth_floor_rank"
C68_MANIFEST_SHA256 = "9878e6c0249cb9e965dbfade2ce2b3a355bed5e6a46bf68667c82fc568672004"
C69_MANIFEST_SHA256 = "6023becea579d0f6ed6ac27316421294f13fd6759d6d51790a31940526e363b7"
C70_MANIFEST_SHA256 = "f828ee06ac609580880eb0bfcd2d1fbcaba590e872f57fe5639a468c67edcbd7"
C71_MANIFEST_SHA256 = "438db2c72a0e5a166f87e680109024be7b28ed710edbd6b4d5ce6968e4a3f7fd"
C72_MANIFEST_SHA256 = "14ca00ed8b9a233475445a2cedc4a0bbd57c35030e6de2948c80177156c98c2c"
C72_DATASET_SHA256 = "7baf6939336261bb307fd3dc13ccb8e9676eacbcc7e7d1139e019fb3b96f90b3"
C72_RECORD_SHA256 = "ca554c1db619c640821037a1ee47401b205644b284cff15390f605e94c202209"
C72_BINDING_SHA256 = "eb36b61ecc800b13e40f8947da5b0fd049542df784baafc8f86a3c38c82b2d1d"
CACHE_PUBLICATION_SHA256 = "244f70b88be0396f7473c6664835cbb3cdad9135b6692b77c74018b1d53c925b"
CACHE_MANIFEST_SHA256 = "3d81068f07ac61fe4cd04bd1a893e58759c06d88213263135fec5244e309b57b"


class Campaign073FeatureError(RuntimeError):
    """Fail-closed Campaign073 feature error."""


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


def _resolve_repo_path(raw: Any) -> Path:
    path = Path(str(raw or "")).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign073FeatureError(f"Campaign073 {label} changed: {path}")


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = [
        {"name": str(item["name"]), "score_direction": str(item["score_direction"])}
        for item in cache_v4._library_layout()["definitions"]
    ]
    items.extend(
        [
            {"name": C68_FACTOR, "score_direction": "higher"},
            {"name": C69_FACTOR, "score_direction": "higher"},
            {"name": C70_FACTOR, "score_direction": "higher"},
            {"name": C71_FACTOR, "score_direction": "higher"},
            {"name": C72_FACTOR, "score_direction": "higher"},
        ]
    )
    if (
        len(items) != COMPARISON_COUNT
        or _comparison_order_digest(items) != COMPARISON_ORDER_SHA256
        or items[-1] != {"name": C72_FACTOR, "score_direction": "higher"}
    ):
        raise Campaign073FeatureError("Campaign073 numeric comparison order changed")
    return items


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = [
        {"name": str(item["name"]), "score_direction": str(item["score_direction"])}
        for item in cache_v4._library_layout()["complete_definitions"]
    ]
    items.extend(reconstruct_comparisons()[-5:])
    if (
        len(items) != FULL_DEFINITION_COUNT
        or _comparison_order_digest(items) != FULL_DEFINITION_ORDER_SHA256
    ):
        raise Campaign073FeatureError("Campaign073 complete definition order changed")
    return items


def _validate_comparator_sources(spec: dict[str, Any]) -> None:
    chain = spec.get("source_chain") or {}
    required = (
        (
            (chain.get("compact_comparator_cache_v4") or {}).get(
                "publication_binding_path"
            ),
            CACHE_PUBLICATION_SHA256,
            "compact-cache publication",
        ),
        (
            (chain.get("compact_comparator_cache_v4") or {}).get("manifest_path"),
            CACHE_MANIFEST_SHA256,
            "compact-cache manifest",
        ),
        (
            (chain.get("campaign068_terminal_comparator") or {}).get(
                "snapshot_manifest_path"
            ),
            C68_MANIFEST_SHA256,
            "Campaign068 manifest",
        ),
        (
            (chain.get("campaign069_terminal_comparator") or {}).get(
                "snapshot_manifest_path"
            ),
            C69_MANIFEST_SHA256,
            "Campaign069 manifest",
        ),
        (
            (chain.get("campaign070_terminal_comparator") or {}).get(
                "snapshot_manifest_path"
            ),
            C70_MANIFEST_SHA256,
            "Campaign070 manifest",
        ),
        (
            (chain.get("campaign071_terminal_comparator") or {}).get(
                "snapshot_manifest_path"
            ),
            C71_MANIFEST_SHA256,
            "Campaign071 manifest",
        ),
        (
            (chain.get("campaign072_terminal_comparator") or {}).get(
                "research_record_path"
            ),
            C72_RECORD_SHA256,
            "Campaign072 record",
        ),
        (
            (chain.get("campaign072_terminal_comparator") or {}).get(
                "snapshot_binding_path"
            ),
            C72_BINDING_SHA256,
            "Campaign072 snapshot binding",
        ),
        (
            (chain.get("campaign072_terminal_comparator") or {}).get(
                "snapshot_manifest_path"
            ),
            C72_MANIFEST_SHA256,
            "Campaign072 manifest",
        ),
    )
    for raw, expected, label in required:
        _require(_resolve_repo_path(raw), expected, label)
    c72 = chain.get("campaign072_terminal_comparator") or {}
    c72_manifest = json.loads(
        _resolve_repo_path(c72.get("snapshot_manifest_path")).read_text(
            encoding="utf-8"
        )
    )
    if not (
        c72.get("factor") == C72_FACTOR
        and c72.get("score_direction") == "higher"
        and c72.get("dataset_sha256") == C72_DATASET_SHA256
        and c72_manifest.get("dataset_sha256") == C72_DATASET_SHA256
        and c72_manifest.get("factor_names") == [C72_FACTOR]
    ):
        raise Campaign073FeatureError("Campaign072 comparator semantics changed")


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    _require(path, PROTOCOL_SHA256, "protocol")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign073FeatureError("Campaign073 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    _validate_comparator_sources(spec)
    chain = spec.get("source_chain") or {}
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    unique = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign073_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign073_minute_source_candidate_comparison_daily_price_or_return_values"
        and (chain.get("numeric_comparison_policy") or {}).get("sha256")
        == NUMERIC_POLICY_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and tuple(candidate.get("minute_source_projection") or ()) == RAW_COLUMNS
        and tuple(candidate.get("stock_day_identity_projection") or ())
        == IDENTITY_COLUMNS
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("terminal_anchor")
        == "Exactly the selected 15:00 close, positive and finite."
        and candidate.get("valid_range")
        == {
            "lower": 0.0,
            "lower_inclusive": True,
            "upper": 1.0,
            "upper_inclusive": False,
        }
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and unique.get("complete_definition_count") == FULL_DEFINITION_COUNT
        and unique.get("complete_definition_order_sha256")
        == FULL_DEFINITION_ORDER_SHA256
        and unique.get("numeric_comparator_count") == COMPARISON_COUNT
        and unique.get("numeric_comparator_order_sha256")
        == COMPARISON_ORDER_SHA256
        and unique.get("all_103_numeric_comparators_must_pass") is True
        and len(reconstruct_comparisons()) == COMPARISON_COUNT
        and len(reconstruct_complete_definitions()) == FULL_DEFINITION_COUNT
        and finite.get("trial_id")
        == "wf073_intraday_terminal_nominal_share_price_affordability_rank_240m_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("complexity") == 1
        and finite.get("expected_trial_count") == 1
        and boundary.get("minute_or_stock_day_source_rows_read_before_this_freeze")
        is False
        and boundary.get("candidate_or_comparison_values_read_before_this_freeze")
        is False
        and boundary.get("historical_forward_return_fields_read") is False
        and boundary.get("market_data_provider_request_issued") is False
    ):
        raise Campaign073FeatureError("Campaign073 protocol semantics changed")
    return spec


def extract_terminal_closes(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Validate exact source grids and return one terminal close per session."""
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign073FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    if raw.empty:
        return (
            pd.DataFrame(
                {
                    "trade_date": pd.Series(dtype="datetime64[ns]"),
                    "terminal_close": pd.Series(dtype="float64"),
                }
            ),
            {
                "source_rows": 0,
                "source_sessions": 0,
                "valid_terminal_sessions": 0,
                "invalid_close_grid_sessions": 0,
            },
        )
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["close"] = pd.to_numeric(work["close"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign073FeatureError(f"raw minute identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    distinct_codes = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].nunique()
    if (
        counts.empty
        or not counts.eq(SOURCE_BAR_COUNT).all()
        or not distinct_codes.eq(SOURCE_BAR_COUNT).all()
        or not work["minute_code"].isin(SOURCE_MINUTE_CODE_SET).all()
    ):
        raise Campaign073FeatureError(f"raw minute grid changed for {symbol}")
    continuous = work.loc[
        work["minute_code"].isin(CONTINUOUS_MINUTE_CODE_SET),
        ["trade_date", "minute_code", "close"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"],
        categories=CONTINUOUS_MINUTE_CODES,
        ordered=True,
    )
    continuous = continuous.sort_values(
        ["trade_date", "minute_code"], kind="stable"
    )
    dates = pd.DatetimeIndex(counts.index).normalize()
    if len(continuous) != len(dates) * SELECTED_BAR_COUNT:
        raise Campaign073FeatureError(f"continuous minute grid changed for {symbol}")
    matrix = continuous["close"].to_numpy(dtype=np.float64).reshape(
        len(dates), SELECTED_BAR_COUNT
    )
    valid = np.isfinite(matrix).all(axis=1) & (matrix > 0.0).all(axis=1)
    terminal = np.full(len(dates), np.nan, dtype=np.float64)
    terminal[valid] = matrix[valid, -1]
    return (
        pd.DataFrame({"trade_date": dates, "terminal_close": terminal}),
        {
            "source_rows": int(len(work)),
            "source_sessions": int(len(dates)),
            "valid_terminal_sessions": int(valid.sum()),
            "invalid_close_grid_sessions": int((~valid).sum()),
        },
    )


def attach_terminal_closes(
    identity: pd.DataFrame,
    terminals: pd.DataFrame,
    *,
    symbol: str,
) -> pd.DataFrame:
    if tuple(identity.columns) != IDENTITY_COLUMNS:
        raise Campaign073FeatureError(f"identity projection changed for {symbol}")
    base = identity.copy()
    base["trade_date"] = pd.to_datetime(
        base["trade_date"], errors="coerce"
    ).dt.normalize()
    base["symbol"] = base["symbol"].astype(str).str.upper()
    base["provider"] = base["provider"].astype(str).str.lower()
    if base.empty:
        base["terminal_close"] = pd.Series(dtype="float64")
        return base
    if (
        base["trade_date"].isna().any()
        or base.duplicated(["trade_date", "symbol"]).any()
        or set(base["symbol"].unique()) != {symbol.upper()}
        or set(base["provider"].unique()) != {"tushare"}
    ):
        raise Campaign073FeatureError(f"joint-clean identity changed for {symbol}")
    source = terminals.copy()
    if source.empty or source.duplicated(["trade_date"]).any():
        raise Campaign073FeatureError(f"terminal close identity changed for {symbol}")
    out = base.merge(source, on="trade_date", how="left", validate="one_to_one")
    raw_dates = set(source["trade_date"].tolist())
    if any(date not in raw_dates for date in out["trade_date"]):
        raise Campaign073FeatureError(
            f"accepted session absent from raw source for {symbol}"
        )
    return out


def rank_affordability_year_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = (*IDENTITY_COLUMNS, "terminal_close")
    if not set(required).issubset(frame.columns):
        raise Campaign073FeatureError("affordability rank input columns changed")
    work = frame.copy()
    raw = pd.to_numeric(work["terminal_close"], errors="coerce")
    raw = raw.where(np.isfinite(raw) & raw.gt(0.0))
    price_rank = raw.groupby(work["trade_date"], sort=False).rank(
        method="average", pct=True
    )
    values = 1.0 - price_rank.to_numpy(dtype=np.float64)
    eligible = np.isfinite(values) & (values >= 0.0) & (values < 1.0)
    work[FACTOR_NAME] = np.where(eligible, values, np.nan)
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
        raise Campaign073FeatureError("Campaign073 output columns changed")
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"].astype(bool)
    if (
        values[eligible].isna().any()
        or ((values[eligible] < 0.0) | (values[eligible] >= 1.0)).any()
        or values[~eligible].notna().any()
    ):
        raise Campaign073FeatureError("Campaign073 value semantics changed")
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
        / "derived/a_share/rich/tushare/minute_walkforward_campaign073_feature_library"
        / OUTPUT_RUN_ID
    )


def _atomic_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    os.close(fd)
    temporary_path = Path(temporary)
    try:
        pq.write_table(
            pa.Table.from_pandas(frame, preserve_index=False),
            temporary_path,
            compression="zstd",
        )
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    fd, temporary = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    os.close(fd)
    temporary_path = Path(temporary)
    try:
        temporary_path.write_text(text, encoding="utf-8")
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _validate_implementation_freeze() -> dict[str, Any]:
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign073FeatureError("Campaign073 implementation freeze is absent")
    freeze = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    runner = freeze.get("feature_runner") or {}
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign073_feature_implementation_freeze"
        and freeze.get("status") == "frozen_before_campaign073_minute_source_values"
        and runner.get("path")
        == "scripts/a_share_three_day_walkforward_campaign073_features.py"
        and runner.get("sha256") == _sha256(Path(__file__).resolve())
        and (freeze.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (freeze.get("mechanism_overlap_audit") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and (freeze.get("research_boundary") or {}).get(
            "candidate_source_rows_read_before_freeze"
        )
        is False
    ):
        raise Campaign073FeatureError("Campaign073 implementation freeze changed")
    return freeze


def _require_inputs(
    data_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], pd.DatetimeIndex]:
    load_protocol()
    freeze = _validate_implementation_freeze()
    raw_path = data_root / RAW_MANIFEST_RELATIVE
    clean_path = data_root / CLEAN_MANIFEST_RELATIVE
    for path, expected, label in (
        (raw_path, RAW_MANIFEST_SHA256, "raw minute manifest"),
        (clean_path, CLEAN_MANIFEST_SHA256, "joint-clean manifest"),
        (DEFAULT_CALENDAR, CALENDAR_SHA256, "calendar"),
    ):
        _require(path, expected, label)
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    clean = json.loads(clean_path.read_text(encoding="utf-8"))
    raw_files = list(raw.get("files") or [])
    clean_files = list(clean.get("files") or [])
    if not (
        len(raw_files) == EXPECTED_PARTITIONS
        and len(clean_files) == EXPECTED_PARTITIONS
        and clean.get("dataset_sha256") == CLEAN_DATASET_SHA256
        and clean.get("rows") == EXPECTED_ROWS
        and clean.get("partitions") == EXPECTED_PARTITIONS
    ):
        raise Campaign073FeatureError("Campaign073 source aggregate semantics changed")
    calendar = pd.DatetimeIndex(
        pd.to_datetime(
            [
                line.strip()
                for line in DEFAULT_CALENDAR.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ],
            errors="raise",
        )
    ).normalize()
    return raw, clean, freeze, calendar


def _raw_file_map(raw: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    result: dict[tuple[str, int], dict[str, Any]] = {}
    for item in raw.get("files") or []:
        key = (str(item["symbol"]).upper(), int(item["year"]))
        if key in result:
            raise Campaign073FeatureError(f"duplicate raw partition identity: {key}")
        result[key] = item
    if len(result) != EXPECTED_PARTITIONS:
        raise Campaign073FeatureError("raw partition identity count changed")
    return result


def _load_attached_partition(
    index: int,
    clean_item: dict[str, Any],
    raw_item: dict[str, Any],
) -> tuple[int, pd.DataFrame, dict[str, int]]:
    symbol = str(clean_item["symbol"]).upper()
    identity = pd.read_parquet(clean_item["path"], columns=list(IDENTITY_COLUMNS))
    raw_path = Path(str(raw_item["path"])).expanduser().resolve()
    if not raw_path.is_file():
        raise Campaign073FeatureError(f"raw partition absent: {raw_path}")
    metadata_rows = pq.ParquetFile(raw_path).metadata.num_rows
    if metadata_rows != int(raw_item["rows"]):
        raise Campaign073FeatureError(f"raw partition row count changed: {raw_path}")
    raw = pd.read_parquet(raw_path, columns=list(RAW_COLUMNS))
    terminals, quality = extract_terminal_closes(raw, symbol=symbol)
    attached = attach_terminal_closes(identity, terminals, symbol=symbol)
    attached["_partition_index"] = index
    return index, attached, quality


def build_snapshot(*, data_root: Path, workers: int = 4) -> Path:
    data_root = data_root.expanduser().resolve()
    raw, clean, freeze, _calendar = _require_inputs(data_root)
    del _calendar
    raw_by_key = _raw_file_map(raw)
    files = list(clean.get("files") or [])
    by_year: dict[int, list[tuple[int, dict[str, Any]]]] = {}
    for index, item in enumerate(files):
        by_year.setdefault(int(item["year"]), []).append((index, item))
    root = output_root(data_root)
    records: list[dict[str, Any] | None] = [None] * len(files)
    total_eligible = 0
    total_missing = 0
    source_rows_read = 0
    source_sessions = 0
    invalid_close_grid_sessions = 0
    for year in sorted(by_year):
        jobs: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
        for index, item in by_year[year]:
            key = (str(item["symbol"]).upper(), int(item["year"]))
            raw_item = raw_by_key.get(key)
            if raw_item is None:
                raise Campaign073FeatureError(f"raw partition missing for {key}")
            jobs.append((index, item, raw_item))
        pieces: list[pd.DataFrame] = []
        quality_by_index: dict[int, dict[str, int]] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = [
                pool.submit(_load_attached_partition, index, item, raw_item)
                for index, item, raw_item in jobs
            ]
            for future in concurrent.futures.as_completed(futures):
                index, attached, quality = future.result()
                pieces.append(attached)
                quality_by_index[index] = quality
                source_rows_read += quality["source_rows"]
                source_sessions += quality["source_sessions"]
                invalid_close_grid_sessions += quality["invalid_close_grid_sessions"]
        if not pieces:
            raise Campaign073FeatureError(f"Campaign073 year {year} has no partitions")
        year_frame = rank_affordability_year_frame(pd.concat(pieces, ignore_index=True))
        grouped = {
            int(index): group
            for index, group in year_frame.groupby("_partition_index", sort=False)
        }
        for index, item in by_year[year]:
            group = grouped.get(index)
            if group is None:
                out = empty_output_frame()
            else:
                out = (
                    group.loc[:, OUTPUT_COLUMNS]
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
            _atomic_parquet(out, path)
            eligible = int(out[f"{FACTOR_NAME}_eligible"].sum())
            missing = int(len(out) - eligible)
            total_eligible += eligible
            total_missing += missing
            raw_item = raw_by_key[(str(item["symbol"]).upper(), int(item["year"]))]
            records[index] = {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign073_feature_partition",
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
                "implementation_freeze_sha256": _sha256(
                    DEFAULT_IMPLEMENTATION_FREEZE
                ),
                "daily_price_fields_read": [],
                "forward_return_fields_read": False,
                "comparison_factor_values_read": False,
                "provider_request_issued": False,
            }
    completed = [item for item in records if item is not None]
    if (
        len(completed) != EXPECTED_PARTITIONS
        or sum(int(item["rows"]) for item in completed) != EXPECTED_ROWS
    ):
        raise Campaign073FeatureError("Campaign073 publication totals changed")
    digest_rows = [
        [
            item["relative_path"],
            item["output_byte_sha256"],
            item["output_frame_sha256"],
            item["rows"],
        ]
        for item in completed
    ]
    manifest = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign073_feature_snapshot",
        "status": "feature_library_complete_pending_ordered_no_return_gates",
        "output_run_id": OUTPUT_RUN_ID,
        "dataset_sha256": _json_digest(digest_rows),
        "partitions": EXPECTED_PARTITIONS,
        "rows": EXPECTED_ROWS,
        "files": completed,
        "factor_names": [FACTOR_NAME],
        "factor_directions": {FACTOR_NAME: "higher"},
        "factor_ranges": {FACTOR_NAME: [0.0, 1.0]},
        "factor_upper_endpoint_exclusive": {FACTOR_NAME: True},
        "factor_formulas": {FACTOR_NAME: FACTOR_FORMULA},
        "factor_eligible_rows": {FACTOR_NAME: total_eligible},
        "quality": {
            "base_rows": EXPECTED_ROWS,
            f"{FACTOR_NAME}__eligible_rows": total_eligible,
            f"{FACTOR_NAME}__missing_rows": total_missing,
            "raw_source_rows_read": source_rows_read,
            "raw_source_sessions": source_sessions,
            "invalid_close_grid_sessions": invalid_close_grid_sessions,
        },
        "source_fields_read": list(RAW_COLUMNS),
        "joint_clean_identity_fields_read": list(IDENTITY_COLUMNS),
        "source_selected_bar_count": SELECTED_BAR_COUNT,
        "source_minute_grid": "09:30 plus 09:31-11:30 and 13:01-15:00; factor selects the latter exact 240 bars",
        "terminal_price_anchor": "raw unadjusted 15:00 nominal CNY close",
        "cross_section_rank_rule": "same-day average-tie percentile rank then one minus rank",
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
    manifest_path = root / "snapshot_manifest.json"
    _atomic_json(manifest, manifest_path)
    return manifest_path


def _validate_manifest(manifest: dict[str, Any]) -> None:
    quality = manifest.get("quality") or {}
    files = list(manifest.get("files") or [])
    eligible = (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign073_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and len(files) == EXPECTED_PARTITIONS
        and manifest.get("rows") == EXPECTED_ROWS
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == {FACTOR_NAME: "higher"}
        and manifest.get("factor_ranges") == {FACTOR_NAME: [0.0, 1.0]}
        and manifest.get("factor_upper_endpoint_exclusive")
        == {FACTOR_NAME: True}
        and manifest.get("factor_formulas") == {FACTOR_NAME: FACTOR_FORMULA}
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("joint_clean_identity_fields_read")
        == list(IDENTITY_COLUMNS)
        and manifest.get("source_selected_bar_count") == SELECTED_BAR_COUNT
        and manifest.get("terminal_price_anchor")
        == "raw unadjusted 15:00 nominal CNY close"
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
        raise Campaign073FeatureError("Campaign073 manifest semantics changed")


def verify_snapshot_files(
    manifest_path: Path, *, workers: int = 4
) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    expected = (output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json").resolve()
    if manifest_path != expected:
        raise Campaign073FeatureError("Campaign073 manifest path changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_manifest(manifest)
    partition_root = (manifest_path.parent / "partitions").resolve()

    def verify(item: dict[str, Any]) -> tuple[int, int]:
        path = Path(str(item["path"])).expanduser().resolve()
        path.relative_to(partition_root)
        if _sha256(path) != item["output_byte_sha256"]:
            raise Campaign073FeatureError(f"partition byte hash changed: {path}")
        frame = pd.read_parquet(path)
        if (
            len(frame) != item["rows"]
            or _frame_sha256(frame) != item["output_frame_sha256"]
        ):
            raise Campaign073FeatureError(f"partition frame changed: {path}")
        return validate_value_semantics(frame)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        totals = list(pool.map(verify, manifest["files"]))
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
        and len(totals) == EXPECTED_PARTITIONS
        and sum(value[0] for value in totals) == EXPECTED_ROWS
        and sum(value[1] for value in totals)
        == (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    ):
        raise Campaign073FeatureError("Campaign073 aggregate identity changed")
    return {
        "status": "verified",
        "partitions": len(totals),
        "rows": sum(value[0] for value in totals),
        "eligible_rows": sum(value[1] for value in totals),
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
