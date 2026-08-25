#!/usr/bin/env python3
"""Run Campaign286's frozen three-trial Alpha158 LightGBM development campaign."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
import statistics
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

import lightgbm as lgb
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.stats import rankdata

from scripts import a_share_three_day_walkforward_campaign as engine
from scripts import a_share_three_day_walkforward_campaign286_design as design
from scripts import (
    a_share_three_day_walkforward_campaign286_design_post_move_verify as design_verify,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_REPO = Path("/Volumes/DIsk/Disk-Coding/qlib")
PROTOCOL_PATH = design.PROTOCOL_PATH
PROTOCOL_SHA256 = design.PROTOCOL_SHA256
CONCEPT_PATH = design.CONCEPT_PATH
CONCEPT_SHA256 = design.CONCEPT_SHA256
DESIGN_MANIFEST_PATH = design_verify.MANIFEST_PATH
DESIGN_MANIFEST_SHA256 = design_verify.MANIFEST_SHA256
DESIGN_AUDIT_PATH = design_verify.AUDIT_PATH
DESIGN_AUDIT_SHA256 = design_verify.AUDIT_SHA256
DESIGN_DATASET_SHA256 = (
    "714f4ccbdf4bfbaccfd04f543ec8c6a0bc345d3cc567ab621d01905130c46252"
)
DESIGN_VERIFIER_PATH = (
    REPO_ROOT
    / "scripts/a_share_three_day_walkforward_campaign286_design_post_move_verify.py"
)
DESIGN_VERIFIER_SHA256 = (
    "3696a2b8e303819e049e4416b4b06e35ffe026b328470333c3ba6eda06eadd0f"
)
DESIGN_VERIFIER_FREEZE_PATH = design_verify.FREEZE_PATH
DESIGN_VERIFIER_FREEZE_SHA256 = (
    "c0c48a60c2e8f9fc79a35c0712dcd8cff0ecf786d913b2652bba1246891eb1f3"
)
ENGINE_PATH = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign.py"
ENGINE_SHA256 = "301f5fe665422b94c9fa110e67995ff0999584a5f323ecdd5f56151a3529f5a7"
LIGHTGBM_WRAPPER_PATH = REPO_ROOT / "qlib/contrib/model/gbdt.py"
LIGHTGBM_WRAPPER_SHA256 = (
    "2c1dd86b85af7730595a7657039c35a3a119d1c0af738d58e38a2357af5763a5"
)
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_286_development_implementation_freeze_20260825.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign286.py"
)
OUTPUT_ROOT = (
    REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_286/"
    "walkforward_v1"
)
SOURCE_PROVIDER_URI = SOURCE_REPO / "data/qlib/cn_a_share"
SOURCE_QUALITY_PATH = (
    SOURCE_REPO / "data/raw/a_share/fundamentals/quarterly_quality.parquet"
)
SOURCE_QUALITY_MANIFEST_PATH = (
    SOURCE_REPO / "data/metadata/quarterly_quality_manifest.json"
)
SOURCE_PRICE_BASIS_PATH = SOURCE_PROVIDER_URI / "price_basis.json"
SOURCE_CALENDAR_PATH = SOURCE_PROVIDER_URI / "calendars/day.txt"
SOURCE_UNIVERSE_PATH = SOURCE_PROVIDER_URI / "instruments/buyable_main_chinext.txt"
SOURCE_SIGNAL_LEDGER_PATH = (
    SOURCE_REPO / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
SOURCE_EXECUTION_LEDGER_PATH = (
    SOURCE_REPO
    / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
SIGNAL_LEDGER_SHA256 = (
    "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
)
EXECUTION_LEDGER_SHA256 = (
    "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
)

FEATURE_COUNT = 158
MINIMUM_FINITE_FEATURES = 119
MIN_SIGNAL_NAMES = 50
PURGE_SIGNAL_SESSIONS = 3
CHAIN_GENESIS = "0" * 64
TRIAL_ORDER = {
    "wf286_lgb_shallow_158f": 0,
    "wf286_lgb_medium_158f": 1,
    "wf286_lgb_deep_158f": 2,
}
INFRASTRUCTURE_FAILURES = (
    "docs/a_share_three_day_walkforward_campaign_286_direct_script_plan_import_failure_20260825.json",
    "docs/a_share_three_day_walkforward_campaign_286_permission_transition_interruption_20260825.json",
    "docs/a_share_three_day_walkforward_campaign_286_recovery_missing_compiled_extension_failure_20260825.json",
    "docs/a_share_three_day_walkforward_campaign_286_recovery_legacy_import_chain_failure_20260825.json",
    "docs/a_share_three_day_walkforward_campaign_286_zero_denominator_coverage_audit_failure_20260825.json",
    "docs/a_share_three_day_walkforward_campaign_286_post_move_verification_path_failure_20260825.json",
)
INFRASTRUCTURE_FAILURE_SHA256 = (
    "3cc64d186a4664c4b7b97ebebbb243f9f539fc9b20045c5246a9b65fe23be39c",
    "7cec04784b90f747b2eed71364b4970f3df84ed346a54e7beaa6548699fd3b58",
    "6ab48c09301213d1fa8cde472ff880e1666a5b7dbc721bbdf90b2f87ba698e02",
    "fc3c92284ee09151567a565bbf4fd98aaf95ed61d1769d9b6e5292122d70e72e",
    "5976d78f8e835c6273e7a6289277cde7bfdee625c4e9ed206b42f2d057149042",
    "f45b2803417c5588c164e3cc53993a449320674e3924996bd076e3fa522f9777",
)
SHARED_MODEL_PARAMETERS = {
    "objective": "regression",
    "metric": "l2",
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 1,
    "verbosity": -1,
    "num_threads": 8,
    "deterministic": True,
    "force_col_wise": True,
    "feature_pre_filter": False,
    "seed": 286,
    "feature_fraction_seed": 286,
    "bagging_seed": 286,
    "data_random_seed": 286,
}


class Campaign286Error(RuntimeError):
    """Fail closed when a frozen development invariant changes."""


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def file_sha256(path: Path) -> str:
    return design.file_sha256(path)


def load_json(path: Path) -> dict[str, Any]:
    return design.load_json(path)


def require_file(path: Path, expected: str, label: str) -> None:
    try:
        design.require_file(path, expected, label)
    except design.Campaign286DesignError as error:
        raise Campaign286Error(str(error)) from error


def atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def model_context() -> dict[str, Any]:
    return {
        "daily_data_bindings": {
            "provider_uri": {"kind": "directory", "path": str(SOURCE_PROVIDER_URI)},
            "quarterly_quality": {"path": str(SOURCE_QUALITY_PATH)},
        }
    }


def trial_catalog(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    trials = list(protocol.get("trial_catalog") or [])
    if [item.get("trial_id") for item in trials] != list(TRIAL_ORDER):
        raise Campaign286Error("Campaign286 trial order changed")
    return trials


def validate_context() -> tuple[dict[str, Any], dict[str, Any]]:
    bindings = (
        (PROTOCOL_PATH, PROTOCOL_SHA256, "Campaign286 protocol"),
        (CONCEPT_PATH, CONCEPT_SHA256, "Campaign286 concept catalog"),
        (DESIGN_MANIFEST_PATH, DESIGN_MANIFEST_SHA256, "Campaign286 design manifest"),
        (DESIGN_AUDIT_PATH, DESIGN_AUDIT_SHA256, "Campaign286 structural audit"),
        (DESIGN_VERIFIER_PATH, DESIGN_VERIFIER_SHA256, "Campaign286 design verifier"),
        (
            DESIGN_VERIFIER_FREEZE_PATH,
            DESIGN_VERIFIER_FREEZE_SHA256,
            "Campaign286 design verifier freeze",
        ),
        (ENGINE_PATH, ENGINE_SHA256, "three-session execution engine"),
        (LIGHTGBM_WRAPPER_PATH, LIGHTGBM_WRAPPER_SHA256, "Qlib LightGBM wrapper"),
        (SOURCE_QUALITY_PATH, design.QUALITY_SHA256, "quarterly quality snapshot"),
        (
            SOURCE_QUALITY_MANIFEST_PATH,
            design.QUALITY_MANIFEST_SHA256,
            "quarterly quality manifest",
        ),
        (SOURCE_PRICE_BASIS_PATH, design.PRICE_BASIS_SHA256, "price basis"),
        (SOURCE_CALENDAR_PATH, design.CALENDAR_SHA256, "provider calendar"),
        (SOURCE_UNIVERSE_PATH, design.UNIVERSE_SHA256, "buyable universe"),
        (SOURCE_SIGNAL_LEDGER_PATH, SIGNAL_LEDGER_SHA256, "Candidate49 signal ledger"),
        (
            SOURCE_EXECUTION_LEDGER_PATH,
            EXECUTION_LEDGER_SHA256,
            "Candidate49 execution ledger",
        ),
    )
    for path, expected, label in bindings:
        require_file(path, expected, label)
    for relative, expected in zip(
        INFRASTRUCTURE_FAILURES, INFRASTRUCTURE_FAILURE_SHA256, strict=True
    ):
        require_file(
            REPO_ROOT / relative, expected, "Campaign286 infrastructure failure"
        )
    if not SOURCE_PROVIDER_URI.is_dir():
        raise Campaign286Error("source provider directory is missing")
    protocol = load_json(PROTOCOL_PATH)
    manifest = load_json(DESIGN_MANIFEST_PATH)
    audit = load_json(DESIGN_AUDIT_PATH)
    shared = protocol.get("shared_model_parameters") or {}
    expected_protocol_shared = {
        "objective": "regression",
        "metric": "l2",
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 1,
        "verbosity": -1,
        "num_threads": 8,
        "deterministic": True,
        "force_col_wise": True,
        "random_state": 286,
    }
    folds = protocol.get("walkforward_folds") or []
    if not (
        shared == expected_protocol_shared
        and lgb.__version__ == "4.6.0"
        and len(trial_catalog(protocol)) == 3
        and folds
        == [
            {
                "fold": 1,
                "train": ["2019-01-01", "2020-12-31"],
                "validation": ["2021-01-01", "2021-12-31"],
            },
            {
                "fold": 2,
                "train": ["2019-01-01", "2021-12-31"],
                "validation": ["2022-01-01", "2022-12-31"],
            },
            {
                "fold": 3,
                "train": ["2019-01-01", "2022-12-31"],
                "validation": ["2023-01-01", "2023-12-31"],
            },
        ]
        and manifest.get("dataset_sha256") == DESIGN_DATASET_SHA256
        and manifest.get("feature_count") == FEATURE_COUNT
        and manifest.get("minimum_finite_features") == MINIMUM_FINITE_FEATURES
        and manifest.get("historical_label_or_forward_return_values_read") is False
        and manifest.get("lockbox_2024_2025_feature_or_return_values_read") is False
        and audit.get("status") == "passed_ready_for_frozen_model_implementation"
        and (audit.get("coverage") or {}).get(
            "gate_passed_before_historical_label_or_forward_return_read"
        )
        is True
    ):
        raise Campaign286Error("Campaign286 frozen model context changed")
    return protocol, manifest


def validate_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE_PATH.is_file():
        raise Campaign286Error("Campaign286 development implementation freeze absent")
    record = load_json(IMPLEMENTATION_FREEZE_PATH)
    runner = record.get("runner") or {}
    tests = record.get("tests") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign286_development_implementation_freeze"
        and record.get("status")
        == "frozen_before_first_campaign286_training_or_validation_return_read"
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (record.get("design_manifest") or {}).get("sha256")
        == DESIGN_MANIFEST_SHA256
        and runner.get("path") == str(Path(__file__).resolve().relative_to(REPO_ROOT))
        and runner.get("sha256") == file_sha256(Path(__file__).resolve())
        and tests.get("path") == str(TEST_PATH.relative_to(REPO_ROOT))
        and tests.get("sha256") == file_sha256(TEST_PATH)
        and boundary.get("training_or_validation_return_read_before_freeze") is False
        and boundary.get("model_fit_before_freeze") is False
        and boundary.get("lockbox_2024_2025_return_read_before_freeze") is False
        and boundary.get("provider_request_issued_before_freeze") is False
        and boundary.get("candidate49_ledgers_changed_before_freeze") is False
    ):
        raise Campaign286Error("Campaign286 development implementation freeze changed")
    return record


def decode_keys(keys: np.ndarray) -> tuple[pd.DatetimeIndex, np.ndarray]:
    values = np.asarray(keys, dtype=np.int64)
    days = values // 4_000_000
    security = values % 4_000_000
    exchange = security // 1_000_000
    codes = security % 1_000_000
    prefixes = np.empty(len(values), dtype=object)
    for code, prefix in ((1, "SH"), (2, "SZ"), (3, "BJ")):
        prefixes[exchange == code] = prefix
    if np.any(~np.isin(exchange, [1, 2, 3])):
        raise Campaign286Error("compact key exchange changed")
    instruments = np.array(
        [
            f"{prefix}{int(code):06d}"
            for prefix, code in zip(prefixes, codes, strict=True)
        ],
        dtype=object,
    )
    dates = pd.DatetimeIndex(pd.to_datetime(days, unit="D", origin="unix"))
    return dates, instruments


def design_record(year: int, manifest: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    matches = [item for item in manifest["files"] if int(item["year"]) == year]
    if len(matches) != 1:
        raise Campaign286Error(f"design partition year changed: {year}")
    record = matches[0]
    path = (DESIGN_MANIFEST_PATH.parent / str(record["path"])).resolve()
    require_file(path, str(record["sha256"]), f"design partition {year}")
    return path, record


def load_design_years(
    years: Iterable[int],
    manifest: dict[str, Any],
    *,
    allowed_dates: Iterable[Any] | None = None,
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, dict[str, Any]]:
    names = list(manifest["feature_names"])
    allowed_days: np.ndarray | None = None
    if allowed_dates is not None:
        allowed_days = (
            pd.DatetimeIndex(list(allowed_dates))
            .normalize()
            .to_numpy(dtype="datetime64[D]")
            .astype(np.int64)
        )
    keys_parts: list[np.ndarray] = []
    matrix_parts: list[np.ndarray] = []
    eligible_parts: list[np.ndarray] = []
    selected_by_year: dict[str, int] = {}
    columns = [
        "stock_day_key",
        *names,
        "finite_feature_count",
        "feature_support_eligible",
        "model_support_eligible",
    ]
    for year in sorted({int(value) for value in years}):
        path, _ = design_record(year, manifest)
        year_rows = 0
        for batch in pq.ParquetFile(path).iter_batches(
            batch_size=65_536, columns=columns
        ):
            frame = batch.to_pandas()
            keys = frame["stock_day_key"].to_numpy(dtype=np.int64)
            mask = np.ones(len(frame), dtype=bool)
            if allowed_days is not None:
                mask = np.isin(keys // 4_000_000, allowed_days)
            if not mask.any():
                continue
            matrix = frame[names].to_numpy(dtype=np.float32, copy=True)[mask]
            finite = np.isfinite(matrix).sum(axis=1).astype(np.uint8)
            observed_count = frame["finite_feature_count"].to_numpy(dtype=np.uint8)[
                mask
            ]
            support = frame["feature_support_eligible"].to_numpy(dtype=bool)[mask]
            eligible = frame["model_support_eligible"].to_numpy(dtype=bool)[mask]
            if not (
                np.array_equal(finite, observed_count)
                and np.array_equal(support, finite >= MINIMUM_FINITE_FEATURES)
                and np.all(~eligible | support)
            ):
                raise Campaign286Error(f"design support changed in {year}")
            keys_parts.append(keys[mask])
            matrix_parts.append(matrix)
            eligible_parts.append(eligible)
            year_rows += int(mask.sum())
        selected_by_year[str(year)] = year_rows
    if not keys_parts:
        raise Campaign286Error("design selection is empty")
    keys = np.concatenate(keys_parts)
    matrix = np.concatenate(matrix_parts)
    eligible = np.concatenate(eligible_parts)
    if len(np.unique(keys)) != len(keys) or np.any(keys[1:] < keys[:-1]):
        raise Campaign286Error("selected design keys changed")
    dates, instruments = decode_keys(keys)
    identities = pd.DataFrame(
        {"trade_date": dates, "instrument": instruments, "stock_day_key": keys}
    )
    return (
        identities,
        matrix,
        eligible,
        {
            "selected_rows": len(keys),
            "model_support_eligible_rows": int(eligible.sum()),
            "selected_rows_by_year": selected_by_year,
        },
    )


def target_percentiles(signal_dates: pd.Series, returns: pd.Series) -> np.ndarray:
    frame = pd.DataFrame(
        {
            "position": np.arange(len(signal_dates)),
            "signal_date": pd.to_datetime(signal_dates).dt.normalize(),
            "value": pd.to_numeric(returns, errors="coerce"),
        }
    )
    target = np.full(len(frame), np.nan, dtype=np.float64)
    for _, group in frame.groupby("signal_date", sort=True):
        values = group["value"].to_numpy(dtype=np.float64)
        finite = np.isfinite(values)
        if int(finite.sum()) < MIN_SIGNAL_NAMES:
            continue
        positions = group["position"].to_numpy(dtype=np.int64)[finite]
        target[positions] = rankdata(values[finite], method="average") / int(
            finite.sum()
        )
    return target


def training_weights(
    signal_dates: pd.Series, target: np.ndarray, eligible: np.ndarray
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    dates = pd.DatetimeIndex(signal_dates).normalize().to_numpy(dtype="datetime64[D]")
    y = np.asarray(target, dtype=np.float64)
    support = np.asarray(eligible, dtype=bool)
    valid = np.isfinite(y) & support
    unique, inverse, counts = np.unique(
        dates[valid], return_inverse=True, return_counts=True
    )
    if len(unique) == 0 or int(counts.min()) < MIN_SIGNAL_NAMES:
        raise Campaign286Error("training target has insufficient contained sessions")
    weights = np.zeros(len(y), dtype=np.float64)
    weights[valid] = 1.0 / (len(unique) * counts[inverse])
    daily = np.bincount(inverse, weights=weights[valid], minlength=len(unique))
    if not (
        math.isclose(float(weights.sum()), 1.0, rel_tol=0.0, abs_tol=1e-12)
        and np.allclose(daily, np.full(len(unique), 1.0 / len(unique)), atol=1e-12)
    ):
        raise Campaign286Error("training session-equal weights changed")
    return (
        valid,
        weights,
        {
            "training_observations": int(valid.sum()),
            "training_sessions": len(unique),
            "minimum_names_per_training_session": int(counts.min()),
            "maximum_names_per_training_session": int(counts.max()),
            "session_equal_row_weight_sum": float(weights.sum()),
            "weights_sha256": hashlib.sha256(
                weights[valid].astype("<f8", copy=False).tobytes()
            ).hexdigest(),
        },
    )


def model_parameters(trial: dict[str, Any]) -> tuple[dict[str, Any], int]:
    params = dict(SHARED_MODEL_PARAMETERS)
    for name in (
        "learning_rate",
        "max_depth",
        "num_leaves",
        "min_data_in_leaf",
        "lambda_l1",
        "lambda_l2",
    ):
        params[name] = trial[name]
    rounds = int(trial["num_boost_round"])
    if rounds < 1:
        raise Campaign286Error("num_boost_round changed")
    return params, rounds


def model_scores(
    model: lgb.Booster, matrix: np.ndarray, eligible: np.ndarray
) -> np.ndarray:
    x = np.asarray(matrix, dtype=np.float32)
    support = np.asarray(eligible, dtype=bool)
    if x.ndim != 2 or x.shape[1] != FEATURE_COUNT or len(support) != len(x):
        raise Campaign286Error("model score inputs changed")
    score = np.asarray(
        model.predict(x, num_iteration=model.current_iteration()), dtype=np.float64
    )
    score[~support] = np.nan
    if not np.isfinite(score[support]).all():
        raise Campaign286Error("eligible model scores are nonfinite")
    return score


def build_training_panel(
    context: dict[str, Any],
    manifest: dict[str, Any],
    training_end: str,
    batch_size: int,
) -> tuple[
    pd.DataFrame,
    Any,
    pd.DatetimeIndex,
    pd.DataFrame,
    np.ndarray,
    np.ndarray,
    dict[str, Any],
]:
    market, calendar = engine.load_market_context(
        context, training_end, "2019-01-01", batch_size
    )
    schedule = engine.global_signal_schedule(calendar)
    period_schedule = engine.purged_period_schedule(
        schedule, "2019-01-01", training_end, PURGE_SIGNAL_SESSIONS
    )
    identities, matrix, eligible, design_stats = load_design_years(
        range(2019, pd.Timestamp(training_end).year + 1),
        manifest,
        allowed_dates=period_schedule["signal_date"],
    )
    columns = [f"alpha158_{index:03d}" for index in range(FEATURE_COUNT)]
    factors = pd.concat(
        [
            identities[["trade_date", "instrument"]].reset_index(drop=True),
            pd.DataFrame(matrix, columns=columns),
        ],
        axis=1,
    )
    factors["model_support_eligible"] = eligible
    panel = engine.build_signal_panel(market, factors, schedule)
    panel_matrix = panel[columns].to_numpy(dtype=np.float32, copy=True)
    panel_eligible = panel["model_support_eligible"].fillna(False).to_numpy(dtype=bool)
    return (
        panel,
        engine.quote_lookup(market),
        calendar,
        schedule,
        panel_matrix,
        panel_eligible,
        design_stats,
    )


def fit_fold(
    context: dict[str, Any],
    manifest: dict[str, Any],
    protocol: dict[str, Any],
    fold: dict[str, Any],
    batch_size: int,
    output_root: Path,
) -> tuple[dict[str, Any], dict[str, lgb.Booster], dict[str, Any]]:
    training_start, training_end = fold["train"]
    (
        panel,
        quotes,
        calendar,
        schedule,
        matrix,
        eligible,
        design_stats,
    ) = build_training_panel(context, manifest, training_end, batch_size)
    returns = pd.to_numeric(panel["forward_gross_return"], errors="coerce").copy()
    returns.loc[~eligible] = np.nan
    target = target_percentiles(panel["signal_date"], returns)
    valid, weights, weight_stats = training_weights(
        panel["signal_date"], target, eligible
    )
    dataset = lgb.Dataset(
        matrix[valid],
        label=target[valid],
        weight=weights[valid],
        feature_name=list(manifest["feature_names"]),
        free_raw_data=True,
    )
    fits: dict[str, Any] = {}
    models: dict[str, lgb.Booster] = {}
    metrics: dict[str, Any] = {}
    for trial in trial_catalog(protocol):
        trial_id = str(trial["trial_id"])
        params, rounds = model_parameters(trial)
        print(
            f"fold {fold['fold']}: fitting {trial_id} for {rounds} rounds",
            flush=True,
        )
        model = lgb.train(params, dataset, num_boost_round=rounds)
        model_path = output_root / f"fold_{fold['fold']}_models" / f"{trial_id}.txt"
        atomic_bytes(model_path, model.model_to_string().encode("utf-8"))
        score = model_scores(model, matrix, eligible)
        panel[engine.factor_score_column(trial_id)] = score
        metrics[trial_id] = engine.evaluate_trial_period(
            panel,
            quotes,
            calendar,
            schedule,
            {"feature_set": [trial_id], "weights": [1.0]},
            training_start,
            training_end,
            PURGE_SIGNAL_SESSIONS,
            include_sensitivity=False,
        )
        fits[trial_id] = {
            "trial_configuration": trial,
            "resolved_parameters": params,
            "num_boost_round": rounds,
            "current_iteration": int(model.current_iteration()),
            "training": weight_stats,
            "selected_design": design_stats,
            "model_text": {
                "path": str(model_path),
                "sha256": file_sha256(model_path),
                "bytes": model_path.stat().st_size,
            },
            "lightgbm_version": lgb.__version__,
        }
        models[trial_id] = model
    return fits, models, metrics


def write_score_snapshot(
    path: Path, identities: pd.DataFrame, scores: dict[str, np.ndarray]
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.tmp"
    arrays: dict[str, Any] = {
        "stock_day_key": pa.array(
            identities["stock_day_key"].to_numpy(dtype=np.int64), type=pa.int64()
        )
    }
    for trial_id, values in scores.items():
        arrays[trial_id] = pa.array(values, type=pa.float64(), from_pandas=True)
    pq.write_table(
        pa.Table.from_pydict(arrays),
        temporary,
        compression="zstd",
        use_dictionary=False,
        row_group_size=65_536,
    )
    os.replace(temporary, path)
    return {
        "path": str(path),
        "sha256": file_sha256(path),
        "rows": len(identities),
        "trial_score_columns": list(scores),
    }


def validation_prefit_record(
    manifest: dict[str, Any],
    fold: dict[str, Any],
    fits: dict[str, Any],
    models: dict[str, lgb.Booster],
    output_root: Path,
) -> tuple[dict[str, np.ndarray], pd.DataFrame, dict[str, Any]]:
    validation_start, _ = fold["validation"]
    year = pd.Timestamp(validation_start).year
    identities, matrix, eligible, design_stats = load_design_years([year], manifest)
    scores = {
        trial_id: model_scores(model, matrix, eligible)
        for trial_id, model in models.items()
    }
    snapshot = write_score_snapshot(
        output_root / f"fold_{fold['fold']}_validation_scores.parquet",
        identities,
        scores,
    )
    payload = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign286_fold_prefit_scores",
        "status": "frozen_before_fold_validation_return_read",
        "created_at": utc_now(),
        "fold": int(fold["fold"]),
        "training": list(fold["train"]),
        "validation": list(fold["validation"]),
        "fits": fits,
        "validation_design": design_stats,
        "validation_score_snapshot": snapshot,
        "all_three_trials_scored_before_validation_returns": True,
        "validation_daily_price_fields_read_before_record": [],
        "validation_forward_return_fields_read_before_record": False,
        "lockbox_2024_2025_return_fields_read": False,
        "candidate49_ledgers_changed": False,
    }
    path = output_root / f"fold_{fold['fold']}_prefit_scores.json"
    engine.atomic_write_json(path, payload)
    payload["record_binding"] = {"path": str(path), "sha256": file_sha256(path)}
    return scores, identities, payload


def evaluate_validation(
    context: dict[str, Any],
    fold: dict[str, Any],
    scores: dict[str, np.ndarray],
    identities: pd.DataFrame,
    batch_size: int,
) -> dict[str, Any]:
    validation_start, validation_end = fold["validation"]
    market, calendar = engine.load_market_context(
        context, validation_end, validation_start, batch_size
    )
    schedule = engine.global_signal_schedule(calendar)
    factors = identities[["trade_date", "instrument"]].copy()
    for trial_id, values in scores.items():
        factors[engine.factor_score_column(trial_id)] = values
    panel = engine.build_signal_panel(market, factors, schedule)
    quotes = engine.quote_lookup(market)
    return {
        trial_id: engine.evaluate_trial_period(
            panel,
            quotes,
            calendar,
            schedule,
            {"feature_set": [trial_id], "weights": [1.0]},
            validation_start,
            validation_end,
            PURGE_SIGNAL_SESSIONS,
            include_sensitivity=True,
        )
        for trial_id in scores
    }


def compound(values: Iterable[float]) -> float:
    result = 1.0
    for value in values:
        result *= 1.0 + float(value)
    return float(result - 1.0)


def survivor_decision(record: dict[str, Any]) -> dict[str, Any]:
    validations = list(record.get("validation_metrics") or [])
    reasons: list[str] = []
    if len(validations) != 3:
        reasons.append("incomplete_validation_fold_count")
    for index, result in enumerate(validations, start=1):
        association = result.get("association") or {}
        normalized = result.get("normalized_execution") or {}
        pilot = result.get("pilot_execution_primary_10bp") or {}
        if int(association.get("cohorts") or 0) < 60:
            reasons.append(f"fold_{index}_insufficient_association_cohorts")
        if int(normalized.get("terminal_unresolved_position_count") or 0) != 0:
            reasons.append(f"fold_{index}_normalized_unresolved_positions")
        if int(pilot.get("terminal_unresolved_position_count") or 0) != 0:
            reasons.append(f"fold_{index}_pilot_unresolved_positions")
        affordability = pilot.get("board_lot_affordability_rate")
        if affordability is None or float(affordability) < 0.9:
            reasons.append(f"fold_{index}_board_lot_affordability")
        participation = pilot.get("maximum_filled_trade_daily_amount_participation")
        if participation is None or float(participation) > 0.01:
            reasons.append(f"fold_{index}_amount_participation")
    if len(validations) != 3:
        return {
            "passed": False,
            "rejection_reasons": reasons,
            "operationally_admissible": False,
        }
    mean_ics = [float(item["association"]["mean_rank_ic"]) for item in validations]
    spreads = [
        float(item["association"]["mean_top3_minus_bottom3_gross_return"])
        for item in validations
    ]
    normalized_returns = [
        float(item["normalized_execution"]["net_cumulative_return"])
        for item in validations
    ]
    pilot10 = [
        float(item["pilot_execution_primary_10bp"]["net_cumulative_return"])
        for item in validations
    ]
    pilot20 = [
        float(item["pilot_slippage_sensitivity"]["0.0020"]["net_cumulative_return"])
        for item in validations
    ]
    drawdowns = [
        float(item["normalized_execution"]["maximum_drawdown"]) for item in validations
    ]
    positive_ic = sum(value > 0.0 for value in mean_ics)
    positive_normalized = sum(value > 0.0 for value in normalized_returns)
    positive_pilot = sum(value > 0.0 for value in pilot10)
    aggregate = {
        "normalized_return": compound(normalized_returns),
        "pilot_10bp_return": compound(pilot10),
        "pilot_20bp_return": compound(pilot20),
    }
    quality = bool(
        positive_ic >= 2
        and statistics.median(mean_ics) > 0.0
        and statistics.median(spreads) > 0.0
        and positive_normalized >= 2
        and positive_pilot >= 2
        and statistics.median(pilot10) > 0.0
        and min(drawdowns) >= -0.25
        and aggregate["pilot_20bp_return"] > 0.0
    )
    if not quality:
        reasons.append("development_quality_or_aggregate_gate_failed")
    operational = not any(
        reason
        for reason in reasons
        if reason != "development_quality_or_aggregate_gate_failed"
    )
    return {
        "passed": bool(operational and quality),
        "operationally_admissible": operational,
        "validation_quality_and_aggregate_passed": quality,
        "rejection_reasons": reasons,
        "positive_mean_rank_ic_fold_count": positive_ic,
        "positive_normalized_return_fold_count": positive_normalized,
        "positive_pilot_10bp_return_fold_count": positive_pilot,
        "median_validation_mean_rank_ic": float(statistics.median(mean_ics)),
        "median_validation_spread": float(statistics.median(spreads)),
        "median_validation_pilot_10bp_return": float(statistics.median(pilot10)),
        "worst_validation_normalized_drawdown": min(drawdowns),
        "development_aggregate": aggregate,
    }


def rank_survivors(records: list[dict[str, Any]]) -> list[str]:
    passing = [record for record in records if record["decision"]["passed"]]
    passing.sort(
        key=lambda record: (
            -record["decision"]["positive_pilot_10bp_return_fold_count"],
            -record["decision"]["median_validation_pilot_10bp_return"],
            -record["decision"]["median_validation_mean_rank_ic"],
            TRIAL_ORDER[record["trial_id"]],
        )
    )
    return [record["trial_id"] for record in passing[:1]]


def prevalue_entries() -> list[dict[str, Any]]:
    concept = load_json(CONCEPT_PATH)
    entries: list[dict[str, Any]] = []
    for item in concept["finite_prevalue_concept_catalog"]:
        entries.append(
            {
                "attempt_id": item["catalog_id"],
                "phase": "prevalue_concept_scouting",
                "name": item["name"],
                "outcome": item["decision"],
                "reason": item["reason"],
                "evidence": {"path": str(CONCEPT_PATH), "sha256": CONCEPT_SHA256},
                "alpha158_feature_values_read": False,
                "historical_forward_return_fields_read": False,
            }
        )
    for relative, expected in zip(
        INFRASTRUCTURE_FAILURES, INFRASTRUCTURE_FAILURE_SHA256, strict=True
    ):
        record = load_json(REPO_ROOT / relative)
        entries.append(
            {
                "attempt_id": record["attempt_id"],
                "phase": "infrastructure_failure",
                "stage": record["stage"],
                "outcome": record["status"],
                "evidence": {"path": relative, "sha256": expected},
                "scientific_result_changed": False,
                "historical_forward_return_fields_read": False,
            }
        )
    return entries


def build_ledger(trials: list[dict[str, Any]]) -> dict[str, Any]:
    previous = CHAIN_GENESIS
    entries: list[dict[str, Any]] = []
    for record in [*prevalue_entries(), *trials]:
        entry = {**record, "previous_entry_sha256": previous}
        entry["entry_sha256"] = engine.value_sha256(entry)
        previous = entry["entry_sha256"]
        entries.append(entry)
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign286_trial_ledger",
        "append_only": True,
        "campaign": {
            "protocol_sha256": PROTOCOL_SHA256,
            "design_dataset_sha256": DESIGN_DATASET_SHA256,
        },
        "chain_genesis": CHAIN_GENESIS,
        "entries": entries,
        "entry_count": len(entries),
        "prevalue_concept_attempt_count": 6,
        "infrastructure_failure_attempt_count": len(INFRASTRUCTURE_FAILURES),
        "model_trial_attempt_count": len(trials),
        "chain_tip_sha256": previous,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
    }


def run_development(args: argparse.Namespace) -> dict[str, Any]:
    if not args.confirm_run:
        raise Campaign286Error("run-development requires --confirm-run")
    validate_implementation_freeze()
    protocol, manifest = validate_context()
    output_root = Path(args.output_root).expanduser().resolve()
    report_path = output_root / "development_report.json"
    if report_path.exists():
        report = load_json(report_path)
        return {
            "status": "development_already_complete_idempotent",
            "report_path": str(report_path),
            "report_sha256": file_sha256(report_path),
            "survivor_count": report["survivor_count"],
        }
    output_root.mkdir(parents=True, exist_ok=True)
    if list(output_root.iterdir()):
        raise Campaign286Error(
            "incomplete Campaign286 output exists; preserve it and use an explicit recovery revision"
        )
    intent = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign286_development_intent",
        "status": "training_return_open_pending_chronological_completion",
        "opened_at": utc_now(),
        "protocol_sha256": PROTOCOL_SHA256,
        "design_manifest_sha256": DESIGN_MANIFEST_SHA256,
        "design_dataset_sha256": DESIGN_DATASET_SHA256,
        "runner_sha256": file_sha256(Path(__file__).resolve()),
        "all_three_trials_must_complete_all_three_folds": True,
        "validation_scores_frozen_before_each_validation_return_read": True,
        "lockbox_2024_2025_remains_closed": True,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
    }
    engine.atomic_write_json(output_root / "development_intent.json", intent)
    folds = [
        {
            "fold": int(item["fold"]),
            "train": list(item["train"]),
            "validation": list(item["validation"]),
        }
        for item in protocol["walkforward_folds"]
    ]
    trials = trial_catalog(protocol)
    records: dict[str, dict[str, Any]] = {
        str(trial["trial_id"]): {
            "attempt_id": str(trial["trial_id"]),
            "trial_id": str(trial["trial_id"]),
            "phase": "development_walkforward",
            "created_at": intent["opened_at"],
            "formula": "LightGBM regression over the complete frozen raw Alpha158 feature family",
            "direction": "higher predicted within-session gross-return percentile",
            "trial_configuration": trial,
            "shared_parameters": SHARED_MODEL_PARAMETERS,
            "source_feature_count": FEATURE_COUNT,
            "source_feature_library_sha256": design.FEATURE_LIBRARY_SHA256,
            "folds": [],
            "validation_metrics": [],
            "candidate49_historical_return_read": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
        }
        for trial in trials
    }
    context = model_context()
    try:
        for fold in folds:
            print(
                f"fold {fold['fold']}: loading contained training returns",
                flush=True,
            )
            fits, models, training_metrics = fit_fold(
                context,
                manifest,
                protocol,
                fold,
                args.batch_size,
                output_root,
            )
            print(
                f"fold {fold['fold']}: freezing validation scores before returns",
                flush=True,
            )
            scores, identities, prefit = validation_prefit_record(
                manifest, fold, fits, models, output_root
            )
            print(
                f"fold {fold['fold']}: reading contained validation returns",
                flush=True,
            )
            validation = evaluate_validation(
                context, fold, scores, identities, args.batch_size
            )
            metrics_payload = {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign286_fold_validation_metrics",
                "status": "completed_after_bound_prefit_scores",
                "created_at": utc_now(),
                "fold": fold["fold"],
                "prefit_score_record": prefit["record_binding"],
                "validation_metrics": validation,
                "lockbox_2024_2025_return_fields_read": False,
                "candidate49_ledgers_changed": False,
            }
            metrics_path = output_root / f"fold_{fold['fold']}_validation_metrics.json"
            engine.atomic_write_json(metrics_path, metrics_payload)
            metrics_binding = {
                "path": str(metrics_path),
                "sha256": file_sha256(metrics_path),
            }
            for trial in trials:
                trial_id = str(trial["trial_id"])
                records[trial_id]["folds"].append(
                    {
                        "fold": fold["fold"],
                        "fit": fits[trial_id],
                        "training_metrics": training_metrics[trial_id],
                        "prefit_score_record": prefit["record_binding"],
                        "validation_metrics_binding": metrics_binding,
                        "validation_metrics": validation[trial_id],
                    }
                )
                records[trial_id]["validation_metrics"].append(validation[trial_id])
            del fits, models, training_metrics, scores, identities, validation
            gc.collect()
        trial_records: list[dict[str, Any]] = []
        for trial in trials:
            trial_id = str(trial["trial_id"])
            record = records[trial_id]
            record["decision"] = survivor_decision(record)
            record["status"] = (
                "development_survivor_gate_passed"
                if record["decision"]["passed"]
                else "development_rejected"
            )
            trial_records.append(record)
        survivors = rank_survivors(trial_records)
        ledger = build_ledger(trial_records)
        ledger_path = output_root / "trial_ledger.json"
        engine.atomic_write_json(ledger_path, ledger)
        survivor_payload = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign286_development_survivors",
            "status": "frozen_before_2024_2025_return_read",
            "created_at": utc_now(),
            "ledger": {"path": str(ledger_path), "sha256": file_sha256(ledger_path)},
            "trial_decisions": {
                record["trial_id"]: record["decision"] for record in trial_records
            },
            "selected_lockbox_survivor_trial_ids": survivors,
            "selected_survivor_count": len(survivors),
            "maximum_survivors": 1,
            "lockbox_return_fields_read": False,
            "candidate49_ledgers_changed": False,
        }
        survivor_path = output_root / "development_survivors.json"
        engine.atomic_write_json(survivor_path, survivor_payload)
        report = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign286_development_report",
            "status": "development_complete_survivors_frozen",
            "created_at": utc_now(),
            "protocol_sha256": PROTOCOL_SHA256,
            "design_manifest_sha256": DESIGN_MANIFEST_SHA256,
            "design_dataset_sha256": DESIGN_DATASET_SHA256,
            "trial_count": len(trial_records),
            "ledger_entry_count": ledger["entry_count"],
            "validation_return_reading_trial_count": len(trial_records),
            "total_model_fold_validation_return_reads": sum(
                len(record["validation_metrics"]) for record in trial_records
            ),
            "survivor_count": len(survivors),
            "selected_survivor_trial_ids": survivors,
            "ledger": {"path": str(ledger_path), "sha256": file_sha256(ledger_path)},
            "survivors": {
                "path": str(survivor_path),
                "sha256": file_sha256(survivor_path),
            },
            "lockbox_2024_2025_opened": False,
            "candidate49_historical_return_read": False,
            "candidate49_ledgers_changed": False,
            "provider_request_issued": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
            "investment_advice": False,
        }
        engine.atomic_write_json(report_path, report)
        return {
            "status": report["status"],
            "trial_count": report["trial_count"],
            "survivor_count": report["survivor_count"],
            "selected_survivor_trial_ids": survivors,
            "report_path": str(report_path),
            "report_sha256": file_sha256(report_path),
        }
    except BaseException as error:
        engine.atomic_write_json(
            output_root / "development_failure.json",
            {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign286_development_failure",
                "status": "failed_preserved_requires_explicit_recovery_revision",
                "created_at": utc_now(),
                "error_type": type(error).__name__,
                "error": str(error),
                "training_or_validation_returns_may_have_been_read": True,
                "lockbox_2024_2025_return_fields_read": False,
                "candidate49_ledgers_changed": False,
                "provider_request_issued": False,
            },
        )
        raise


def plan(args: argparse.Namespace) -> dict[str, Any]:
    validate_implementation_freeze()
    protocol, manifest = validate_context()
    output_root = Path(args.output_root).expanduser().resolve()
    empty = not output_root.exists() or not list(output_root.iterdir())
    ready = bool(
        empty
        and len(trial_catalog(protocol)) == 3
        and len(protocol.get("walkforward_folds") or []) == 3
        and manifest.get("dataset_sha256") == DESIGN_DATASET_SHA256
    )
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign286_development_plan",
        "status": (
            "ready_to_open_2019_2023_training_and_validation_returns"
            if ready
            else "not_ready_preserve_existing_output"
        ),
        "ready": ready,
        "trial_count": 3,
        "fold_count": 3,
        "output_root": str(output_root),
        "design_dataset_sha256": DESIGN_DATASET_SHA256,
        "historical_return_values_read_by_plan": False,
        "lockbox_2024_2025_return_fields_read_by_plan": False,
        "provider_request_issued": False,
        "credential_loaded": False,
        "candidate49_ledgers_changed": False,
    }


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    subcommands = command.add_subparsers(dest="command", required=True)
    plan_command = subcommands.add_parser("plan")
    plan_command.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    run = subcommands.add_parser("run-development")
    run.add_argument("--confirm-run", action="store_true")
    run.add_argument("--batch-size", type=int, default=512)
    run.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    return command


def main() -> int:
    args = parser().parse_args()
    if args.command == "plan":
        payload = plan(args)
    elif args.command == "run-development":
        payload = run_development(args)
    else:  # pragma: no cover
        raise AssertionError(args.command)
    print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
