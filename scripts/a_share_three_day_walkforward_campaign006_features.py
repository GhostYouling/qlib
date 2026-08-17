#!/usr/bin/env python3
"""Build and audit the one no-return feature mechanism for Campaign006.

The exact formula is frozen in the Campaign006 mechanism-overlap record before
this module may open an external minute partition.  The builder reads only
datetime, symbol, provider, close, volume, and amount.  Coverage/capacity is
evaluated before any comparison values; a coverage passer is then challenged
against the 25 pre-Campaign004 comparisons, three terminal Campaign004 factors,
and the terminal Campaign005 factor.  No daily price or return is read here.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import gc
import hashlib
import json
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_three_day_walkforward_campaign004_features as engine  # noqa: E402


foundation = engine.foundation
research = engine.research
candidate49 = engine.candidate49
market = engine.market
comparison_engine = engine.comparison_engine
REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_006_no_return_preregistration.json"
)
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data"
    / "experiments"
    / "short_horizon"
    / "historical_walkforward"
    / "campaign_006"
    / "no_return"
)
MECHANISM_AUDIT = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_006_mechanism_overlap_audit.json"
)
MECHANISM_AUDIT_SHA256 = (
    "6178638773f4ababdcbd91e93c925a6c2c768fe692e02ed029f5f8174a0d9e7d"
)

# Bound in order after the corresponding immutable artifact exists.
PROTOCOL_SHA256 = (
    "fbe683e54705b458f7d13f56f3ccbd87235ff62a1cd67e1b5ced8b5538bda579"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "1f32cbe4c9d93ef2fbecf27b74cc4d15caddb5f62ca77e9818395c1c1743e0ab"
)
SNAPSHOT_DATASET_SHA256 = (
    "170381f7624e9b3d2e45170c9e363eea877ecec0f1f3945d03945ac2238f3c04"
)
NO_RETURN_AUDIT_SHA256 = (
    "dbc6f63904e7a064f26f9fee12f979cb1702ecc2e61eec5422d341fe62b0db8a"
)

SOURCE_RUN_ID = market.SOURCE_RUN_ID
OUTPUT_RUN_ID = (
    f"{SOURCE_RUN_ID}_walkforward_campaign006_feature_library_v1"
)
RAW_COLUMNS = (
    "datetime",
    "symbol",
    "provider",
    "close",
    "volume",
    "amount",
)
BASE_COLUMNS = ("trade_date", "symbol")
FACTOR_NAME = "intraday_transaction_price_path_confirmation_238p"
FACTOR_NAMES = (FACTOR_NAME,)
FACTOR_DIRECTIONS = {FACTOR_NAME: "higher"}
FACTOR_RANGES = {FACTOR_NAME: (-1.0, 1.0)}
FACTOR_FORMULA = (
    "PearsonCorr(log(close_t/close_t-1), "
    "log((amount_t/volume_t)/(amount_t-1/volume_t-1))) over retained "
    "within-half adjacent active-bar pairs"
)
FACTOR_FORMULAS = {FACTOR_NAME: FACTOR_FORMULA}
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
EXPECTED_PARTITIONS = 33_015
EXPECTED_ROWS = 7_724_498
EXPECTED_SYMBOLS = 5_396
MAXIMUM_PAIRS = 238
MINIMUM_RETAINED_PAIRS = 120
ENDPOINT_TOLERANCE = 1e-12

C4_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign004_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign004_feature_library_v1/snapshot_manifest.json"
)
C4_SNAPSHOT_SHA256 = (
    "8eefc381d006997f1dcd95edcd9be4db8485e0c4954d6166d94f1981ae3b57fe"
)
C4_DATASET_SHA256 = (
    "1359e755e669c7b949b26b2086d1c1328ec0cdf53b45ce7e67d117a274c7fc8a"
)
C4_FACTOR_NAMES = (
    "intraday_market_neutral_late_residual_drift_238m",
    "intraday_negative_return_absorption_rate_236p",
    "intraday_signed_path_efficiency_239m",
)
C4_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C4_FACTOR_NAMES[0],
    f"{C4_FACTOR_NAMES[0]}_eligible",
    C4_FACTOR_NAMES[1],
    f"{C4_FACTOR_NAMES[1]}_eligible",
    C4_FACTOR_NAMES[2],
    f"{C4_FACTOR_NAMES[2]}_eligible",
)

C5_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign005_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign005_feature_library_v1/snapshot_manifest.json"
)
C5_SNAPSHOT_SHA256 = (
    "7f48bd252d381f85deb416ed282b6f62aacee0ca492c37c99fdb901d2e241675"
)
C5_DATASET_SHA256 = (
    "5c7f9e7e534cc4e4678c7ea746c69f5809dcc6415d9a652b93ff63899413fd75"
)
C5_FACTOR_NAMES = (
    "intraday_zero_return_amount_intensity_238m",
    "intraday_lunch_repricing_persistence_119m",
    "intraday_directional_price_impact_asymmetry_238m",
)
C5_COMPARISON_FACTOR = C5_FACTOR_NAMES[0]
C5_OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    C5_FACTOR_NAMES[0],
    f"{C5_FACTOR_NAMES[0]}_eligible",
    C5_FACTOR_NAMES[1],
    f"{C5_FACTOR_NAMES[1]}_eligible",
    C5_FACTOR_NAMES[2],
    f"{C5_FACTOR_NAMES[2]}_eligible",
)


class Campaign006FeatureError(RuntimeError):
    """Fail-closed Campaign006 feature or no-return audit error."""


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    observed = foundation.file_digest(path)
    if observed != expected_sha256:
        raise Campaign006FeatureError(
            f"{label} fingerprint mismatch: expected {expected_sha256}, "
            f"got {observed}"
        )


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived/a_share/rich/tushare/"
        "minute_walkforward_campaign006_feature_library"
        / OUTPUT_RUN_ID
    )


def empty_output_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            "symbol": pd.Series(dtype="string"),
            "provider": pd.Series(dtype="string"),
            FACTOR_NAME: pd.Series(dtype="float64"),
            f"{FACTOR_NAME}_eligible": pd.Series(dtype="bool"),
        }
    ).loc[:, OUTPUT_COLUMNS]


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate the protocol frozen before any Campaign006 historical value."""

    path = path.expanduser().resolve()
    if not PROTOCOL_SHA256:
        raise Campaign006FeatureError(
            "bind PROTOCOL_SHA256 before building or auditing Campaign006 values"
        )
    _require_file(path, PROTOCOL_SHA256, "Campaign006 no-return protocol")
    _require_file(
        MECHANISM_AUDIT,
        MECHANISM_AUDIT_SHA256,
        "Campaign006 mechanism-overlap audit",
    )
    spec = research.load_json_record(
        path,
        kind="a_share_three_day_walkforward_campaign006_no_return_preregistration",
    )
    candidates = list(spec.get("candidates") or [])
    names = tuple(str(item.get("name") or "") for item in candidates)
    formulas = {
        str(item.get("name") or ""): str(item.get("formula") or "")
        for item in candidates
    }
    directions = {
        str(item.get("name") or ""): str(item.get("direction") or "")
        for item in candidates
    }
    audit = spec.get("ordered_no_return_gates") or {}
    coverage = audit.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = audit.get("uniqueness_after_coverage_only") or {}
    comparisons = list(uniqueness.get("comparison_factors") or [])
    boundary = spec.get("research_boundary") or {}
    mechanism = (spec.get("source_chain") or {}).get(
        "mechanism_overlap_audit"
    ) or {}
    if not (
        spec.get("version") == 1
        and spec.get("status")
        == "frozen_before_campaign006_candidate_or_comparison_values_or_returns"
        and names == FACTOR_NAMES
        and formulas == FACTOR_FORMULAS
        and directions == FACTOR_DIRECTIONS
        and tuple(candidates[0].get("source_fields_allowed") or ())
        == RAW_COLUMNS
        and candidates[0].get("minimum_retained_pairs")
        == MINIMUM_RETAINED_PAIRS
        and mechanism.get("sha256") == MECHANISM_AUDIT_SHA256
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.90
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
        and len(comparisons) == 29
        and [str(item.get("name") or "") for item in comparisons[-4:-1]]
        == list(C4_FACTOR_NAMES)
        and str(comparisons[-1].get("name") or "") == C5_COMPARISON_FACTOR
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility")
        is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate50_prospective_activation_allowed") is False
        and boundary.get("current_scoring_selection_sizing_or_orders_allowed")
        is False
    ):
        raise Campaign006FeatureError(
            "Campaign006 no-return protocol semantics changed"
        )
    return spec


def compute_factor_values(
    *,
    closes: np.ndarray,
    volumes: np.ndarray,
    amounts: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the frozen transaction-price path confirmation."""

    if (
        closes.ndim != 2
        or closes.shape[1] != 240
        or volumes.shape != closes.shape
        or amounts.shape != closes.shape
    ):
        raise Campaign006FeatureError(
            "Campaign006 aligned array shapes are invalid"
        )
    close_valid = np.isfinite(closes).all(axis=1) & (closes > 0.0).all(axis=1)
    volume_valid = (
        np.isfinite(volumes).all(axis=1) & (volumes >= 0.0).all(axis=1)
    )
    amount_valid = (
        np.isfinite(amounts).all(axis=1) & (amounts >= 0.0).all(axis=1)
    )
    one_sided_zero = ((volumes == 0.0) != (amounts == 0.0)).any(axis=1)
    active = (volumes > 0.0) & (amounts > 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        log_closes = np.log(closes)
        transaction_prices = np.divide(
            amounts,
            volumes,
            out=np.full_like(amounts, np.nan, dtype=float),
            where=active,
        )
        log_transaction_prices = np.log(transaction_prices)
    close_returns = np.concatenate(
        [
            log_closes[:, 1:120] - log_closes[:, :119],
            log_closes[:, 121:240] - log_closes[:, 120:239],
        ],
        axis=1,
    )
    transaction_returns = np.concatenate(
        [
            log_transaction_prices[:, 1:120]
            - log_transaction_prices[:, :119],
            log_transaction_prices[:, 121:240]
            - log_transaction_prices[:, 120:239],
        ],
        axis=1,
    )
    retained = np.concatenate(
        [
            active[:, 1:120] & active[:, :119],
            active[:, 121:240] & active[:, 120:239],
        ],
        axis=1,
    )
    pair_count = retained.sum(axis=1)
    x = np.where(retained, close_returns, 0.0)
    y = np.where(retained, transaction_returns, 0.0)
    n = pair_count.astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        sum_x = x.sum(axis=1)
        sum_y = y.sum(axis=1)
        sum_x2 = np.square(x).sum(axis=1)
        sum_y2 = np.square(y).sum(axis=1)
        sum_xy = (x * y).sum(axis=1)
        centered_x2 = sum_x2 - np.square(sum_x) / n
        centered_y2 = sum_y2 - np.square(sum_y) / n
        centered_xy = sum_xy - sum_x * sum_y / n
        values = centered_xy / np.sqrt(centered_x2 * centered_y2)
    low_near = (values < -1.0) & (values >= -1.0 - ENDPOINT_TOLERANCE)
    high_near = (values > 1.0) & (values <= 1.0 + ENDPOINT_TOLERANCE)
    canonicalized = low_near | high_near
    values = np.where(low_near, -1.0, np.where(high_near, 1.0, values))
    finite = np.isfinite(values)
    in_range = (values >= -1.0) & (values <= 1.0)
    eligible = (
        close_valid
        & volume_valid
        & amount_valid
        & ~one_sided_zero
        & (pair_count >= MINIMUM_RETAINED_PAIRS)
        & (centered_x2 > 0.0)
        & (centered_y2 > 0.0)
        & finite
        & in_range
    )
    quality = {
        "base_rows": int(len(closes)),
        "invalid_required_close_rows": int((~close_valid).sum()),
        "invalid_required_volume_rows": int(
            (close_valid & ~volume_valid).sum()
        ),
        "invalid_required_amount_rows": int(
            (close_valid & volume_valid & ~amount_valid).sum()
        ),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__one_sided_zero_activity_rows": int(
            (
                close_valid
                & volume_valid
                & amount_valid
                & one_sided_zero
            ).sum()
        ),
        f"{FACTOR_NAME}__fewer_than_120_pairs_rows": int(
            (
                close_valid
                & volume_valid
                & amount_valid
                & ~one_sided_zero
                & (pair_count < MINIMUM_RETAINED_PAIRS)
            ).sum()
        ),
        f"{FACTOR_NAME}__constant_close_return_rows": int(
            (
                close_valid
                & volume_valid
                & amount_valid
                & ~one_sided_zero
                & (pair_count >= MINIMUM_RETAINED_PAIRS)
                & (centered_x2 <= 0.0)
            ).sum()
        ),
        f"{FACTOR_NAME}__constant_transaction_return_rows": int(
            (
                close_valid
                & volume_valid
                & amount_valid
                & ~one_sided_zero
                & (pair_count >= MINIMUM_RETAINED_PAIRS)
                & (centered_y2 <= 0.0)
            ).sum()
        ),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int(
            (canonicalized & eligible).sum()
        ),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (
                close_valid
                & volume_valid
                & amount_valid
                & ~one_sided_zero
                & (pair_count >= MINIMUM_RETAINED_PAIRS)
                & (centered_x2 > 0.0)
                & (centered_y2 > 0.0)
                & (~finite | ~in_range)
            ).sum()
        ),
    }
    return (
        {FACTOR_NAME: np.where(eligible, values, np.nan)},
        {FACTOR_NAME: eligible},
        quality,
    )


def compute_partition_frame(
    raw: pd.DataFrame,
    base: pd.DataFrame,
    _unused_benchmark: Any,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Validate one source partition and compute the frozen feature."""

    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign006FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    base_work, _, _ = market.extract_partition_returns(
        raw.loc[:, market.RAW_COLUMNS],
        base,
        symbol=symbol,
    )
    if base_work.empty:
        return empty_output_frame(), {"base_rows": 0}
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    for field in ("close", "volume", "amount"):
        work[field] = pd.to_numeric(work[field], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign006FeatureError(f"raw identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = (
        work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    )
    continuous = work.loc[
        work["minute_code"].isin(market.CONTINUOUS_MINUTE_CODES),
        ["trade_date", "minute_code", "close", "volume", "amount"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"],
        categories=market.CONTINUOUS_MINUTE_CODES,
        ordered=True,
    )
    continuous = continuous.sort_values(
        ["trade_date", "minute_code"],
        kind="stable",
    )
    if len(continuous) != len(base_work) * 240:
        raise Campaign006FeatureError(
            f"continuous minute grid changed for {symbol}"
        )
    closes = continuous["close"].to_numpy(dtype=float).reshape(-1, 240)
    volumes = continuous["volume"].to_numpy(dtype=float).reshape(-1, 240)
    amounts = continuous["amount"].to_numpy(dtype=float).reshape(-1, 240)
    values, eligible, quality = compute_factor_values(
        closes=closes,
        volumes=volumes,
        amounts=amounts,
    )
    return (
        pd.DataFrame(
            {
                "trade_date": base_work["trade_date"],
                "symbol": symbol.upper(),
                "provider": "tushare",
                FACTOR_NAME: values[FACTOR_NAME],
                f"{FACTOR_NAME}_eligible": eligible[FACTOR_NAME],
            }
        ).loc[:, OUTPUT_COLUMNS],
        quality,
    )


def _configure_engine() -> None:
    """Point reusable Campaign004 mechanics at the Campaign006 contract."""

    engine.DEFAULT_PROTOCOL = DEFAULT_PROTOCOL
    engine.DEFAULT_EXPERIMENT_ROOT = DEFAULT_EXPERIMENT_ROOT
    engine.PROTOCOL_SHA256 = PROTOCOL_SHA256
    engine.SNAPSHOT_MANIFEST_SHA256 = SNAPSHOT_MANIFEST_SHA256
    engine.SNAPSHOT_DATASET_SHA256 = SNAPSHOT_DATASET_SHA256
    engine.NO_RETURN_AUDIT_SHA256 = NO_RETURN_AUDIT_SHA256
    engine.OUTPUT_RUN_ID = OUTPUT_RUN_ID
    engine.RAW_COLUMNS = RAW_COLUMNS
    engine.BASE_COLUMNS = BASE_COLUMNS
    engine.FACTOR_NAMES = FACTOR_NAMES
    engine.FACTOR_DIRECTIONS = FACTOR_DIRECTIONS
    engine.FACTOR_RANGES = FACTOR_RANGES
    engine.FACTOR_FORMULAS = FACTOR_FORMULAS
    engine.OUTPUT_COLUMNS = OUTPUT_COLUMNS
    engine.EXPECTED_PARTITIONS = EXPECTED_PARTITIONS
    engine.EXPECTED_ROWS = EXPECTED_ROWS
    engine.EXPECTED_SYMBOLS = EXPECTED_SYMBOLS
    engine.output_root = output_root
    engine.empty_output_frame = empty_output_frame
    engine.load_protocol = load_protocol
    engine.compute_partition_frame = compute_partition_frame


def _validate_snapshot_manifest(
    manifest: dict[str, Any],
    *,
    require_fingerprint_constants: bool,
) -> None:
    eligible = manifest.get("factor_eligible_rows") or {}
    if not (
        manifest.get("schema_version") == 1
        and manifest.get("kind")
        == "a_share_three_day_walkforward_campaign006_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("protocol_sha256") == PROTOCOL_SHA256
        and manifest.get("mechanism_overlap_audit_sha256")
        == MECHANISM_AUDIT_SHA256
        and manifest.get("raw_manifest_sha256") == market.RAW_MANIFEST_SHA256
        and manifest.get("joint_manifest_sha256") == market.JOINT_MANIFEST_SHA256
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("factor_names") == list(FACTOR_NAMES)
        and manifest.get("factor_directions") == FACTOR_DIRECTIONS
        and manifest.get("factor_formulas") == FACTOR_FORMULAS
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and manifest.get("rows") == EXPECTED_ROWS
        and len(manifest.get("files") or []) == EXPECTED_PARTITIONS
        and isinstance(eligible.get(FACTOR_NAME), int)
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_open_high_low_read") is False
        and manifest.get("source_volume_read") is True
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("candidate49_historical_return_read") is False
        and manifest.get("current_scoring_selection_sizing_or_orders_performed")
        is False
    ):
        raise Campaign006FeatureError("Campaign006 snapshot semantics changed")
    if require_fingerprint_constants and not (
        SNAPSHOT_MANIFEST_SHA256
        and SNAPSHOT_DATASET_SHA256
        and manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
    ):
        raise Campaign006FeatureError(
            "Campaign006 snapshot fingerprint constants are not bound"
        )


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    """Build the factor without comparison values or returns."""

    if workers < 1 or workers > 8:
        raise ValueError("--workers must be between 1 and 8")
    _configure_engine()
    data_root = data_root.expanduser().resolve()
    load_protocol()
    final_root = output_root(data_root)
    final_manifest = final_root / "snapshot_manifest.json"
    partial_root = final_root.parent / f".{OUTPUT_RUN_ID}.partial"
    if final_root.exists():
        if not final_manifest.is_file() or not SNAPSHOT_MANIFEST_SHA256:
            raise Campaign006FeatureError(
                "published Campaign006 snapshot exists but is not fingerprint-bound"
            )
        _require_file(
            final_manifest,
            SNAPSHOT_MANIFEST_SHA256,
            "Campaign006 snapshot manifest",
        )
        _validate_snapshot_manifest(
            research.load_json_record(final_manifest),
            require_fingerprint_constants=True,
        )
        return final_manifest
    if shutil.disk_usage(data_root).free < 10 * 1024**3:
        raise Campaign006FeatureError(
            "external data root has less than 10 GiB free"
        )
    candidate49_spec = candidate49.load_preregistration()
    chain = candidate49.validate_external_chain(candidate49_spec, data_root)
    raw, joint, raw_manifest_path, joint_manifest_path = chain[:4]
    _, joint_by_key, by_symbol = market._partition_maps(raw, joint)
    if (
        len(joint_by_key) != EXPECTED_PARTITIONS
        or len(by_symbol) != EXPECTED_SYMBOLS
    ):
        raise Campaign006FeatureError(
            "Campaign006 source partition map changed"
        )
    lock_path = data_root / ".a_share_walkforward_campaign006_features.lock"
    with foundation.ProcessLock(lock_path):
        partial_root.mkdir(parents=True, exist_ok=True)
        all_records: list[dict[str, Any]] = []
        eligible_dates: Counter[str] = Counter()
        resumed = 0
        completed_symbols = 0
        print(
            f"building {EXPECTED_PARTITIONS:,} Campaign006 partitions across "
            f"{EXPECTED_SYMBOLS:,} symbols with {workers} workers",
            flush=True,
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    engine._process_symbol,
                    pairs,
                    partial_root=partial_root,
                    final_root=final_root,
                    benchmark=None,
                ): symbol
                for symbol, pairs in sorted(by_symbol.items())
            }
            try:
                for future in concurrent.futures.as_completed(futures):
                    futures.pop(future)
                    records, dates, resumed_count = future.result()
                    all_records.extend(records)
                    eligible_dates.update(dates)
                    resumed += resumed_count
                    completed_symbols += 1
                    if (
                        completed_symbols % 25 == 0
                        or completed_symbols == len(by_symbol)
                    ):
                        print(
                            f"Campaign006 progress symbols={completed_symbols:,}/"
                            f"{len(by_symbol):,} partitions={len(all_records):,}/"
                            f"{len(joint_by_key):,} resumed={resumed:,}",
                            flush=True,
                        )
            except BaseException:
                for future in futures:
                    future.cancel()
                raise
    if len(all_records) != EXPECTED_PARTITIONS:
        raise Campaign006FeatureError(
            "not every source partition produced a Campaign006 checkpoint"
        )
    _require_file(
        Path(raw_manifest_path),
        market.RAW_MANIFEST_SHA256,
        "raw minute manifest",
    )
    _require_file(
        Path(joint_manifest_path),
        market.JOINT_MANIFEST_SHA256,
        "joint-clean manifest",
    )
    all_records.sort(
        key=lambda item: (str(item["symbol"]), int(item["year"]))
    )
    quality = engine._aggregate_quality(all_records)
    factor_eligible_rows = {
        FACTOR_NAME: int(
            sum(
                int(
                    (record.get("factor_eligible_rows") or {}).get(
                        FACTOR_NAME,
                        0,
                    )
                )
                for record in all_records
            )
        )
    }
    dataset_payload = "\n".join(
        f"{item['symbol']}|{item['year']}|{item['output_byte_sha256']}"
        for item in all_records
    ).encode("utf-8")
    eligible_names_by_date: dict[str, dict[str, int]] = {FACTOR_NAME: {}}
    for key, value in sorted(eligible_dates.items()):
        name, trade_date = key.split("|", 1)
        eligible_names_by_date[name][trade_date] = int(value)
    manifest = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign006_feature_snapshot",
        "status": "feature_library_complete_pending_ordered_no_return_gates",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "output_run_id": OUTPUT_RUN_ID,
        "protocol_path": str(DEFAULT_PROTOCOL.resolve()),
        "protocol_sha256": PROTOCOL_SHA256,
        "mechanism_overlap_audit_path": str(MECHANISM_AUDIT.resolve()),
        "mechanism_overlap_audit_sha256": MECHANISM_AUDIT_SHA256,
        "raw_manifest_path": str(raw_manifest_path),
        "raw_manifest_sha256": market.RAW_MANIFEST_SHA256,
        "joint_manifest_path": str(joint_manifest_path),
        "joint_manifest_sha256": market.JOINT_MANIFEST_SHA256,
        "dataset_sha256": hashlib.sha256(dataset_payload).hexdigest(),
        "factor_names": list(FACTOR_NAMES),
        "factor_directions": FACTOR_DIRECTIONS,
        "factor_formulas": FACTOR_FORMULAS,
        "factor_eligible_rows": factor_eligible_rows,
        "eligible_names_by_date": eligible_names_by_date,
        "files": all_records,
        "partitions": len(all_records),
        "rows": int(quality.get("base_rows", -1)),
        "quality": quality,
        "source_fields_read": list(RAW_COLUMNS),
        "source_open_high_low_read": False,
        "source_volume_read": True,
        "daily_price_fields_read": [],
        "comparison_factor_values_read": False,
        "forward_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "training_or_model_fitting_performed": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
        "prospective_candidate_activation_created": False,
        "resumed_partitions": resumed,
        "protocol_evidence": {
            "campaign006_mechanism_overlap_audit_sha256": (
                MECHANISM_AUDIT_SHA256
            ),
            "campaign006_no_return_preregistration_sha256": PROTOCOL_SHA256,
            "candidate49_no_return_protocol_sha256": (
                candidate49.PREREGISTRATION_SHA256
            ),
        },
    }
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=False)
    foundation.atomic_write_json(manifest, partial_root / "snapshot_manifest.json")
    final_root.parent.mkdir(parents=True, exist_ok=True)
    partial_root.replace(final_root)
    return final_manifest


def verify_snapshot_files(
    manifest: dict[str, Any],
    manifest_path: Path,
    workers: int,
) -> dict[str, Any]:
    _configure_engine()
    return engine.verify_snapshot_files(manifest, manifest_path, workers)


def _verify_prior_snapshot(
    *,
    path: Path,
    manifest_sha256: str,
    dataset_sha256: str,
    kind: str,
    factor_names: tuple[str, ...],
    output_columns: tuple[str, ...],
    workers: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _require_file(path, manifest_sha256, f"{kind} manifest")
    manifest = research.load_json_record(path)
    records = list(manifest.get("files") or [])
    root = (path.parent / "partitions").resolve()
    if not (
        manifest.get("kind") == kind
        and manifest.get("dataset_sha256") == dataset_sha256
        and tuple(manifest.get("factor_names") or ()) == factor_names
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and manifest.get("rows") == EXPECTED_ROWS
        and len(records) == EXPECTED_PARTITIONS
    ):
        raise Campaign006FeatureError(f"{kind} aggregate changed")

    def verify(record: dict[str, Any]) -> int:
        partition = Path(str(record.get("path") or "")).resolve()
        if partition.parent.parent != root:
            raise Campaign006FeatureError(
                f"{kind} partition escapes root: {partition}"
            )
        _require_file(
            partition,
            str(record.get("output_byte_sha256") or ""),
            f"{kind} partition",
        )
        frame = pd.read_parquet(partition, columns=list(output_columns))
        if (
            len(frame) != int(record.get("rows", -1))
            or foundation.frame_digest(frame)
            != str(record.get("output_frame_sha256") or "")
        ):
            raise Campaign006FeatureError(
                f"{kind} partition frame changed: {partition}"
            )
        return len(frame)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        counts = list(pool.map(verify, records))
    if len(counts) != EXPECTED_PARTITIONS or sum(counts) != EXPECTED_ROWS:
        raise Campaign006FeatureError(f"{kind} verification changed")
    return manifest, {
        "path": str(path),
        "sha256": manifest_sha256,
        "dataset_sha256": dataset_sha256,
        "verified_partitions": len(counts),
        "verified_rows": sum(counts),
        "all_partition_byte_and_frame_hashes_valid": True,
    }


def _prior_comparisons(
    *,
    candidate_keys: np.ndarray,
    candidate_values: np.ndarray,
    manifest: dict[str, Any],
    factors: tuple[str, ...],
    gate: dict[str, Any],
) -> list[dict[str, Any]]:
    values = engine._load_filtered_comparison_values_explicit(
        manifest,
        factors,
        candidate_keys,
    )
    return [
        comparison_engine._aligned_comparison_result(
            candidate_keys=candidate_keys,
            candidate_values=candidate_values,
            comparison_values=values[factor],
            comparison=factor,
            direction="higher",
            gate=gate,
        )
        for factor in factors
    ]


def run_no_return_audit(
    *,
    data_root: Path,
    experiment_root: Path,
    workers: int,
) -> Path:
    """Apply coverage before all 29 frozen uniqueness comparisons."""

    if not SNAPSHOT_MANIFEST_SHA256 or not SNAPSHOT_DATASET_SHA256:
        raise Campaign006FeatureError(
            "bind the Campaign006 snapshot fingerprints before audit"
        )
    _configure_engine()
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_protocol()
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    _require_file(
        manifest_path,
        SNAPSHOT_MANIFEST_SHA256,
        "Campaign006 snapshot manifest",
    )
    manifest = research.load_json_record(manifest_path)
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    existing = sorted(
        experiment_root.glob("*_campaign006_no_return_audit.json")
    )
    if existing:
        if len(existing) != 1 or not NO_RETURN_AUDIT_SHA256:
            raise Campaign006FeatureError(
                "existing Campaign006 audit is ambiguous or not bound"
            )
        _require_file(
            existing[0],
            NO_RETURN_AUDIT_SHA256,
            "Campaign006 audit",
        )
        return existing[0]
    verification = verify_snapshot_files(manifest, manifest_path, workers)
    print("building Campaign006 no-price quality/listing eligibility", flush=True)
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
        chain, candidate49_manifest_path, candidate49_manifest = (
            engine._comparison_chain(data_root)
        )
        c4_manifest, c4_verification = _verify_prior_snapshot(
            path=C4_SNAPSHOT_PATH,
            manifest_sha256=C4_SNAPSHOT_SHA256,
            dataset_sha256=C4_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign004_feature_snapshot",
            factor_names=C4_FACTOR_NAMES,
            output_columns=C4_OUTPUT_COLUMNS,
            workers=workers,
        )
        c5_manifest, c5_verification = _verify_prior_snapshot(
            path=C5_SNAPSHOT_PATH,
            manifest_sha256=C5_SNAPSHOT_SHA256,
            dataset_sha256=C5_DATASET_SHA256,
            kind="a_share_three_day_walkforward_campaign005_feature_snapshot",
            factor_names=C5_FACTOR_NAMES,
            output_columns=C5_OUTPUT_COLUMNS,
            workers=workers,
        )
        gate = spec["ordered_no_return_gates"][
            "uniqueness_after_coverage_only"
        ]
        keys, values = engine._sorted_candidate_arrays(
            quality_frame,
            FACTOR_NAME,
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
        comparisons.extend(
            _prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c4_manifest,
                factors=C4_FACTOR_NAMES,
                gate=gate,
            )
        )
        comparisons.extend(
            _prior_comparisons(
                candidate_keys=keys,
                candidate_values=values,
                manifest=c5_manifest,
                factors=(C5_COMPARISON_FACTOR,),
                gate=gate,
            )
        )
        observed = [
            item["absolute_median_daily_rank_correlation"]
            for item in comparisons
            if item["absolute_median_daily_rank_correlation"] is not None
        ]
        passed = bool(
            len(comparisons) == 29
            and all(item["gate_passed"] for item in comparisons)
        )
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": True,
            "pre_campaign004_comparison_count": 25,
            "campaign004_terminal_comparison_count": 3,
            "campaign005_terminal_comparison_count": 1,
            "prior_snapshot_file_verification": frozen_verifications,
            "campaign004_snapshot_file_verification": c4_verification,
            "campaign005_snapshot_file_verification": c5_verification,
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
    run_id = f"{research._timestamp()}_campaign006_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign006_no_return_audit",
        "status": (
            "completed_with_one_admissible_factor_pending_walkforward_preregistration"
            if admitted
            else "completed_zero_admissible_factors_stop_before_historical_returns"
        ),
        "run_id": run_id,
        "created_at": research._timestamp(),
        "mechanism_overlap_audit": {
            "path": str(MECHANISM_AUDIT.resolve()),
            "sha256": MECHANISM_AUDIT_SHA256,
        },
        "protocol": {
            "path": str(DEFAULT_PROTOCOL.resolve()),
            "sha256": PROTOCOL_SHA256,
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
            "freeze the exact one-trial Campaign006 walk-forward catalog "
            "before reading 2019-2023 returns"
            if admitted
            else "record the no-return rejection and design a new campaign"
        ),
        "source_fields_read": list(RAW_COLUMNS),
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
            "*_campaign006_no_return_audit.json"
        )
    )
    result: dict[str, Any] = {
        "mechanism_overlap_audit_path": str(MECHANISM_AUDIT.resolve()),
        "mechanism_overlap_audit_sha256": MECHANISM_AUDIT_SHA256,
        "protocol_path": str(DEFAULT_PROTOCOL.resolve()),
        "protocol_sha256_bound": bool(PROTOCOL_SHA256),
        "snapshot_manifest_path": str(manifest_path),
        "snapshot_exists": manifest_path.is_file(),
        "snapshot_sha256_bound": bool(SNAPSHOT_MANIFEST_SHA256),
        "audit_count": len(audits),
        "no_return_audit_sha256_bound": bool(NO_RETURN_AUDIT_SHA256),
        "daily_price_fields_read_by_status": False,
        "forward_return_fields_read_by_status": False,
        "candidate49_historical_return_read": False,
    }
    if manifest_path.is_file():
        result["snapshot_observed_sha256"] = foundation.file_digest(
            manifest_path
        )
    if audits:
        result["latest_audit"] = str(audits[-1])
        result["latest_audit_observed_sha256"] = foundation.file_digest(
            audits[-1]
        )
    return result


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Build and no-return audit Campaign006 feature mechanism."
    )
    subparsers = value.add_subparsers(dest="command", required=True)
    for name in ("build", "audit", "status"):
        command = subparsers.add_parser(name)
        command.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
        command.add_argument(
            "--experiment-root",
            default=str(DEFAULT_EXPERIMENT_ROOT),
        )
        if name in {"build", "audit"}:
            command.add_argument("--workers", type=int, default=4)
    return value


def main() -> int:
    args = parser().parse_args()
    data_root = Path(args.data_root)
    experiment_root = Path(args.experiment_root)
    if args.command == "build":
        result: Any = {
            "status": "snapshot_ready",
            "manifest_path": str(
                build_snapshot(data_root=data_root, workers=int(args.workers))
            ),
            "forward_return_fields_read": False,
        }
    elif args.command == "audit":
        result = {
            "status": "no_return_audit_ready",
            "audit_path": str(
                run_no_return_audit(
                    data_root=data_root,
                    experiment_root=experiment_root,
                    workers=int(args.workers),
                )
            ),
            "forward_return_fields_read": False,
        }
    else:
        result = status(data_root, experiment_root)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
