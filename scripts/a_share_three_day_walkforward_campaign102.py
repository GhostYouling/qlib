#!/usr/bin/env python3
"""Run Campaign102's chronological bounded-simplex development campaign.

The runner enforces, in code and on disk, the frozen sequence for each fold:
training returns -> fit -> validation-score snapshot -> all-130 uniqueness audit
-> validation returns.  It never touches Candidate49 or any current-action path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.optimize import minimize
from scipy.stats import rankdata

from scripts import a_share_three_day_walkforward_campaign as engine
from scripts import a_share_three_day_walkforward_campaign102_design as design

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = design.DEFAULT_PROTOCOL
DEFAULT_DESIGN_MANIFEST = design.output_root(design.DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
DEFAULT_DESIGN_AUDIT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_102/no_return/"
    "design_structural_audit.json"
)
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_102/walkforward"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_102_development_implementation_freeze_20260807.json"
)
INTERPRETATION_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_102_sequential_execution_interpretation_freeze_20260807.json"
)
DESIGN_BINDING_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_102_design_snapshot_binding_20260807.json"
)
TEMPLATE_PATH = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_004_preregistration.json"
ENGINE_PATH = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign.py"
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign102.py"
)

PROTOCOL_SHA256 = design.PROTOCOL_SHA256
DESIGN_MANIFEST_SHA256 = "fc9ab498462439731785a0eabbde370c1fd883c8d771eba312c85aa912d3cebe"
DESIGN_DATASET_SHA256 = "cceec2b790d134a89914e83e0697c1e6abff605a85fd85be74de68067faddb92"
DESIGN_AUDIT_SHA256 = "87001a379815e027787bf51763451f5235ae619b9d2ade12a5790cc753f77b90"
DESIGN_BINDING_SHA256 = "706eccfb3104e50a627e92ff0e740bfaea8cd71c99c079595a193c1c7bdade34"
TEMPLATE_SHA256 = "e67811f265b2b744073391fa65698951b132065109f95fa47991b8254a5756e6"
ENGINE_SHA256 = "301f5fe665422b94c9fa110e67995ff0999584a5f323ecdd5f56151a3529f5a7"
INTERPRETATION_SHA256 = "07dce156a77e65167f55a04105db9d5d0a167e61db5028bca833f1d8fbfa6bd2"
FACTOR_NAME = "full_numeric_library_bounded_simplex_ridge_130f"
TRIALS = (
    ("wf102_full_numeric_library_bounded_simplex_ridge_130f_lambda_0", 0.0),
    ("wf102_full_numeric_library_bounded_simplex_ridge_130f_lambda_0p1", 0.1),
    ("wf102_full_numeric_library_bounded_simplex_ridge_130f_lambda_1", 1.0),
)
LOWER_WEIGHT = 0.25 / design.NUMERIC_COUNT
UPPER_WEIGHT = 4.0 / design.NUMERIC_COUNT
MIN_SIGNAL_NAMES = 50
PURGE_SIGNAL_SESSIONS = 3
CHAIN_GENESIS = "0" * 64


class Campaign102Error(RuntimeError):
    """Fail closed when a Campaign102 invariant or chronological gate changes."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def value_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=engine.research._json_default,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def require_file(path: Path, expected: str, label: str) -> None:
    if len(expected) != 64 or not path.is_file() or file_sha256(path) != expected:
        raise Campaign102Error(f"{label} changed: {path}")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Campaign102Error(f"JSON object required: {path}")
    return value


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                payload,
                handle,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=False,
                default=engine.research._json_default,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _implementation_freeze() -> dict[str, Any]:
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign102Error("Campaign102 development implementation freeze is absent")
    record = load_json(DEFAULT_IMPLEMENTATION_FREEZE)
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign102_development_implementation_freeze"
        and record.get("status") == "frozen_before_first_campaign102_training_return_read"
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (record.get("design_manifest") or {}).get("sha256")
        == DESIGN_MANIFEST_SHA256
        and (record.get("design_audit") or {}).get("sha256") == DESIGN_AUDIT_SHA256
        and (record.get("runner") or {}).get("sha256")
        == file_sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == file_sha256(TEST_PATH)
        and record.get("campaign102_model_fit_before_freeze") is False
        and record.get("campaign102_training_or_validation_return_read_before_freeze")
        is False
        and record.get("provider_request_issued_before_freeze") is False
        and record.get("candidate49_ledgers_changed_before_freeze") is False
    ):
        raise Campaign102Error("Campaign102 development implementation freeze changed")
    return record


def load_frozen_context() -> tuple[dict[str, Any], dict[str, Any]]:
    require_file(DEFAULT_PROTOCOL, PROTOCOL_SHA256, "Campaign102 protocol")
    require_file(DEFAULT_DESIGN_MANIFEST, DESIGN_MANIFEST_SHA256, "Campaign102 design")
    require_file(DEFAULT_DESIGN_AUDIT, DESIGN_AUDIT_SHA256, "Campaign102 design audit")
    require_file(DESIGN_BINDING_PATH, DESIGN_BINDING_SHA256, "Campaign102 design binding")
    require_file(TEMPLATE_PATH, TEMPLATE_SHA256, "execution template")
    require_file(ENGINE_PATH, ENGINE_SHA256, "execution engine")
    require_file(INTERPRETATION_PATH, INTERPRETATION_SHA256, "execution interpretation")
    protocol = load_json(DEFAULT_PROTOCOL)
    audit = load_json(DEFAULT_DESIGN_AUDIT)
    template = load_json(TEMPLATE_PATH)
    if not (
        audit.get("status") == "passed_ready_for_sequential_training_fit"
        and (audit.get("coverage") or {}).get("gate_passed_before_model_fit_or_returns")
        is True
        and (audit.get("snapshot") or {}).get("dataset_sha256")
        == DESIGN_DATASET_SHA256
        and audit.get("historical_forward_return_fields_read") is False
        and audit.get("model_fitting_performed") is False
        and protocol.get("model_family", {}).get("regularization_grid")
        == [item[1] for item in TRIALS]
        and int(protocol.get("design_matrix", {}).get("source_factor_count", -1))
        == design.NUMERIC_COUNT
    ):
        raise Campaign102Error("Campaign102 frozen context semantics changed")
    for group_name in ("daily_data_bindings", "execution_policy_bindings"):
        for name, binding in (template.get(group_name) or {}).items():
            if binding.get("kind") == "directory":
                path = engine.resolve_bound_path(str(binding["path"]))
                if not path.is_dir():
                    raise Campaign102Error(f"{group_name}.{name} directory is missing")
            else:
                engine.validate_file_binding(binding, f"{group_name}.{name}")
    return protocol, template


def decode_keys(keys: np.ndarray) -> tuple[pd.DatetimeIndex, np.ndarray]:
    compact = np.asarray(keys, dtype=np.int64)
    days = compact // 4_000_000
    security = compact % 4_000_000
    exchanges = security // 1_000_000
    codes = security % 1_000_000
    if not np.isin(exchanges, np.array([1, 2, 3], dtype=np.int64)).all():
        raise Campaign102Error("compact exchange code changed")
    dates = pd.to_datetime(days, unit="D", origin="unix").normalize()
    prefixes = pd.Series(exchanges).map({1: "SH", 2: "SZ", 3: "BJ"})
    instruments = (prefixes + pd.Series(codes).astype("string").str.zfill(6)).to_numpy(
        dtype=str
    )
    return pd.DatetimeIndex(dates), instruments


def design_record(year: int) -> tuple[Path, dict[str, Any]]:
    manifest = load_json(DEFAULT_DESIGN_MANIFEST)
    records = [item for item in manifest["files"] if int(item["year"]) == int(year)]
    if len(records) != 1:
        raise Campaign102Error(f"Campaign102 design year changed: {year}")
    record = records[0]
    path = (DEFAULT_DESIGN_MANIFEST.parent / str(record["path"])).resolve()
    require_file(path, str(record["sha256"]), f"Campaign102 design partition {year}")
    return path, record


def load_design_years(
    years: Iterable[int], *, allowed_dates: Iterable[pd.Timestamp] | None = None
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray]:
    names = list(design.component_columns())
    allowed_days: np.ndarray | None = None
    if allowed_dates is not None:
        allowed_days = (
            pd.DatetimeIndex(list(allowed_dates))
            .normalize()
            .to_numpy(dtype="datetime64[D]")
        )
    id_frames: list[pd.DataFrame] = []
    matrices: list[np.ndarray] = []
    finite_counts: list[np.ndarray] = []
    eligible_parts: list[np.ndarray] = []
    for year in sorted({int(value) for value in years}):
        path, _ = design_record(year)
        frame = pd.read_parquet(
            path,
            columns=["stock_day_key", *names, design.FINITE_COUNT_NAME, design.ELIGIBLE_NAME],
        )
        keys = frame.pop("stock_day_key").to_numpy(dtype=np.int64)
        dates, instruments = decode_keys(keys)
        mask = np.ones(len(keys), dtype=bool)
        if allowed_days is not None:
            mask = np.isin(dates.to_numpy(dtype="datetime64[D]"), allowed_days)
        id_frames.append(
            pd.DataFrame(
                {
                    "trade_date": dates[mask],
                    "instrument": instruments[mask],
                    "stock_day_key": keys[mask],
                }
            )
        )
        finite_counts.append(
            frame.pop(design.FINITE_COUNT_NAME).to_numpy(dtype=np.uint8)[mask]
        )
        eligible_parts.append(frame.pop(design.ELIGIBLE_NAME).to_numpy(dtype=bool)[mask])
        matrices.append(frame[names].to_numpy(dtype=np.float32, copy=True)[mask])
    identities = pd.concat(id_frames, ignore_index=True)
    matrix = np.concatenate(matrices, axis=0)
    finite_count = np.concatenate(finite_counts)
    eligible = np.concatenate(eligible_parts)
    if identities.duplicated(["trade_date", "instrument"]).any():
        raise Campaign102Error("Campaign102 decoded design identities are not unique")
    observed_count, observed_eligible = design.support_state(matrix)
    if not (
        np.array_equal(finite_count, observed_count)
        and np.array_equal(eligible, observed_eligible)
    ):
        raise Campaign102Error("Campaign102 design support semantics changed")
    return identities, matrix, finite_count, eligible


def target_percentiles(
    signal_dates: pd.Series, returns: pd.Series, minimum_names: int = MIN_SIGNAL_NAMES
) -> np.ndarray:
    frame = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(signal_dates).dt.normalize(),
            "value": pd.to_numeric(returns, errors="coerce"),
        }
    )
    result = np.full(len(frame), np.nan, dtype=np.float64)
    for _, group in frame.groupby("signal_date", sort=True):
        finite = np.isfinite(group["value"].to_numpy(dtype=np.float64))
        if int(finite.sum()) < minimum_names:
            continue
        positions = group.index.to_numpy()[finite]
        result[positions] = rankdata(
            group.loc[positions, "value"].to_numpy(dtype=np.float64), method="average"
        ) / len(positions)
    return result


def sufficient_statistics(
    matrix: np.ndarray, target: np.ndarray, sessions: np.ndarray
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    x = np.asarray(matrix, dtype=np.float64)
    y = np.asarray(target, dtype=np.float64)
    session_values = np.asarray(sessions)
    valid = np.isfinite(y) & np.isfinite(x).all(axis=1)
    x = x[valid]
    y = y[valid]
    session_values = session_values[valid]
    unique, counts = np.unique(session_values, return_counts=True)
    if len(unique) == 0 or len(x) < MIN_SIGNAL_NAMES:
        raise Campaign102Error("training target has insufficient observations")
    count_map = dict(zip(unique.tolist(), counts.tolist()))
    row_weight = np.array(
        [1.0 / (len(unique) * count_map[value]) for value in session_values],
        dtype=np.float64,
    )
    weighted = x * np.sqrt(row_weight)[:, None]
    a = weighted.T @ weighted
    b = x.T @ (row_weight * y)
    if not (np.isfinite(a).all() and np.isfinite(b).all()):
        raise Campaign102Error("training sufficient statistics are nonfinite")
    return a, b, {
        "training_observations": len(x),
        "training_sessions": len(unique),
        "minimum_names_per_training_session": int(counts.min()),
        "maximum_names_per_training_session": int(counts.max()),
        "session_equal_row_weight_sum": float(row_weight.sum()),
        "a_sha256": hashlib.sha256(np.asarray(a, dtype="<f8").tobytes()).hexdigest(),
        "b_sha256": hashlib.sha256(np.asarray(b, dtype="<f8").tobytes()).hexdigest(),
    }


def fit_weights(a: np.ndarray, b: np.ndarray, regularization: float) -> dict[str, Any]:
    n = design.NUMERIC_COUNT
    uniform = np.full(n, 1.0 / n, dtype=np.float64)

    def objective(weights: np.ndarray) -> float:
        delta = weights - uniform
        return float(weights @ a @ weights - 2.0 * b @ weights + regularization * (delta @ delta))

    def gradient(weights: np.ndarray) -> np.ndarray:
        return 2.0 * (a @ weights - b) + 2.0 * regularization * (weights - uniform)

    result = minimize(
        objective,
        uniform,
        jac=gradient,
        method="SLSQP",
        bounds=[(LOWER_WEIGHT, UPPER_WEIGHT)] * n,
        constraints=[{"type": "eq", "fun": lambda w: float(w.sum() - 1.0), "jac": lambda w: np.ones(n)}],
        options={"ftol": 1e-12, "maxiter": 2000, "disp": False},
    )
    weights = np.asarray(result.x, dtype=np.float64)
    tolerance = 1e-8
    if not (
        result.success
        and np.isfinite(weights).all()
        and abs(float(weights.sum()) - 1.0) <= tolerance
        and float(weights.min()) >= LOWER_WEIGHT - tolerance
        and float(weights.max()) <= UPPER_WEIGHT + tolerance
    ):
        raise Campaign102Error(
            f"bounded simplex fit failed: success={result.success}, message={result.message}"
        )
    return {
        "regularization": float(regularization),
        "weights": weights.tolist(),
        "weight_sum": float(weights.sum()),
        "minimum_weight": float(weights.min()),
        "maximum_weight": float(weights.max()),
        "objective_without_target_constant": objective(weights),
        "optimizer_success": bool(result.success),
        "optimizer_status": int(result.status),
        "optimizer_message": str(result.message),
        "optimizer_iterations": int(result.nit),
        "weights_sha256": hashlib.sha256(np.asarray(weights, dtype="<f8").tobytes()).hexdigest(),
    }


def model_scores(matrix: np.ndarray, eligible: np.ndarray, weights: np.ndarray) -> np.ndarray:
    x = np.asarray(matrix, dtype=np.float64)
    support = np.asarray(eligible, dtype=bool)
    w = np.asarray(weights, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] != design.NUMERIC_COUNT or w.shape != (design.NUMERIC_COUNT,):
        raise Campaign102Error("model score inputs changed")
    scores = np.where(np.isfinite(x), x, 0.0) @ w
    scores[~support] = np.nan
    finite = np.isfinite(scores)
    if np.any((scores[finite] < -1e-12) | (scores[finite] > 1.0 + 1e-12)):
        raise Campaign102Error("model score escaped [0,1]")
    return scores


def uniqueness_audit(
    keys: np.ndarray,
    matrix: np.ndarray,
    scores: np.ndarray,
    component_names: Iterable[str],
) -> dict[str, Any]:
    keys = np.asarray(keys, dtype=np.int64)
    x = np.asarray(matrix, dtype=np.float64)
    candidate = np.asarray(scores, dtype=np.float64)
    sessions = keys // 4_000_000
    if len(sessions) > 1 and np.any(sessions[1:] < sessions[:-1]):
        raise Campaign102Error("uniqueness stock-day keys are not session sorted")
    boundaries = np.flatnonzero(np.r_[True, sessions[1:] != sessions[:-1], True])
    session_slices = [
        slice(int(boundaries[index]), int(boundaries[index + 1]))
        for index in range(len(boundaries) - 1)
    ]
    names = list(component_names)
    if x.shape != (len(keys), design.NUMERIC_COUNT) or len(names) != design.NUMERIC_COUNT:
        raise Campaign102Error("uniqueness inputs changed")
    comparisons: list[dict[str, Any]] = []
    for index, name in enumerate(names):
        daily: list[float] = []
        comparator = x[:, index]
        for positions in session_slices:
            valid = np.isfinite(candidate[positions]) & np.isfinite(comparator[positions])
            if int(valid.sum()) < 50:
                continue
            left = rankdata(candidate[positions][valid], method="average")
            right = rankdata(comparator[positions][valid], method="average")
            if np.ptp(left) == 0.0 or np.ptp(right) == 0.0:
                continue
            correlation = float(np.corrcoef(left, right)[0, 1])
            if math.isfinite(correlation):
                daily.append(correlation)
        median = float(np.median(daily)) if daily else None
        passed = bool(
            len(daily) >= 100
            and median is not None
            and abs(median) < 0.8
        )
        comparisons.append(
            {
                "comparison_factor": name,
                "pairwise_sessions": len(daily),
                "median_daily_rank_correlation": median,
                "absolute_median_daily_rank_correlation": (
                    abs(median) if median is not None else None
                ),
                "gate_passed": passed,
            }
        )
    observed = [
        float(item["absolute_median_daily_rank_correlation"])
        for item in comparisons
        if item["absolute_median_daily_rank_correlation"] is not None
    ]
    all_passed = len(comparisons) == design.NUMERIC_COUNT and all(
        item["gate_passed"] for item in comparisons
    )
    return {
        "comparison_count": len(comparisons),
        "comparison_order_sha256": design.NUMERIC_ORDER_SHA256,
        "minimum_pairwise_names_per_session": 50,
        "minimum_pairwise_sessions_per_comparison": 100,
        "strict_maximum_absolute_median_daily_rank_correlation": 0.8,
        "all_required_comparisons_passed": all_passed,
        "maximum_observed_absolute_median_daily_rank_correlation": (
            max(observed) if observed else None
        ),
        "comparisons": comparisons,
    }


def write_score_snapshot(
    path: Path, identities: pd.DataFrame, trial_scores: dict[str, np.ndarray]
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.tmp"
    arrays: dict[str, Any] = {
        "stock_day_key": pa.array(identities["stock_day_key"].to_numpy(dtype=np.int64), type=pa.int64())
    }
    for trial_id, scores in trial_scores.items():
        arrays[trial_id] = pa.array(scores, type=pa.float64(), from_pandas=True)
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
        "trial_score_columns": list(trial_scores),
    }


def _score_column(trial_id: str) -> str:
    return engine.factor_score_column(trial_id)


def build_training_panel(
    template: dict[str, Any], training_end: str, batch_size: int
) -> tuple[pd.DataFrame, Any, pd.DatetimeIndex, pd.DataFrame, np.ndarray, np.ndarray]:
    market, calendar = engine.load_market_context(
        template, training_end, "2019-01-01", batch_size
    )
    schedule = engine.global_signal_schedule(calendar)
    period_schedule = engine.purged_period_schedule(
        schedule, "2019-01-01", training_end, PURGE_SIGNAL_SESSIONS
    )
    signal_dates = pd.DatetimeIndex(period_schedule["signal_date"])
    identities, matrix, _, eligible = load_design_years(
        range(2019, pd.Timestamp(training_end).year + 1), allowed_dates=signal_dates
    )
    component_frame = pd.DataFrame(
        matrix,
        columns=[f"component_{index:03d}" for index in range(design.NUMERIC_COUNT)],
    )
    factor_frame = pd.concat(
        [identities[["trade_date", "instrument"]].reset_index(drop=True), component_frame],
        axis=1,
    )
    factor_frame[design.ELIGIBLE_NAME] = eligible
    panel = engine.build_signal_panel(market, factor_frame, schedule)
    columns = [f"component_{index:03d}" for index in range(design.NUMERIC_COUNT)]
    panel_matrix = panel[columns].to_numpy(dtype=np.float64, copy=True)
    panel_eligible = panel[design.ELIGIBLE_NAME].fillna(False).to_numpy(dtype=bool)
    return panel, engine.quote_lookup(market), calendar, schedule, panel_matrix, panel_eligible


def fit_fold(
    template: dict[str, Any], fold: dict[str, Any], live: dict[str, float], batch_size: int
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    training_start, training_end = fold["training"]
    panel, quotes, calendar, schedule, panel_matrix, panel_eligible = build_training_panel(
        template, training_end, batch_size
    )
    training_returns = pd.to_numeric(panel["forward_gross_return"], errors="coerce").copy()
    training_returns.loc[~panel_eligible] = np.nan
    target = target_percentiles(panel["signal_date"], training_returns)
    x = np.where(np.isfinite(panel_matrix), panel_matrix, 0.0)
    x[~panel_eligible, :] = np.nan
    a, b, stats = sufficient_statistics(
        x, target, panel["signal_date"].to_numpy(dtype="datetime64[D]")
    )
    fits: dict[str, Any] = {}
    training_metrics: dict[str, dict[str, Any]] = {}
    for trial_id, regularization in live.items():
        fit = fit_weights(a, b, regularization)
        weights = np.asarray(fit["weights"], dtype=np.float64)
        score = model_scores(panel_matrix, panel_eligible, weights)
        panel[_score_column(trial_id)] = score
        trial = {
            "feature_set": [trial_id],
            "weights": [1.0],
        }
        training_metrics[trial_id] = engine.evaluate_trial_period(
            panel,
            quotes,
            calendar,
            schedule,
            trial,
            training_start,
            training_end,
            PURGE_SIGNAL_SESSIONS,
            include_sensitivity=False,
        )
        fits[trial_id] = fit
    return {"sufficient_statistics": stats, "fits": fits}, training_metrics


def validation_prefit_audit(
    fold: dict[str, Any], fit_payload: dict[str, Any], output_root: Path
) -> tuple[dict[str, Any], dict[str, np.ndarray], pd.DataFrame]:
    validation_start, validation_end = fold["validation"]
    year = pd.Timestamp(validation_start).year
    identities, matrix, _, eligible = load_design_years([year])
    trial_scores: dict[str, np.ndarray] = {}
    audits: dict[str, Any] = {}
    for trial_id, fit in fit_payload["fits"].items():
        scores = model_scores(matrix, eligible, np.asarray(fit["weights"], dtype=np.float64))
        trial_scores[trial_id] = scores
        audits[trial_id] = uniqueness_audit(
            identities["stock_day_key"].to_numpy(dtype=np.int64),
            matrix,
            scores,
            design.component_columns(),
        )
    score_binding = write_score_snapshot(
        output_root / f"fold_{fold['fold']}_validation_scores.parquet",
        identities,
        trial_scores,
    )
    payload = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign102_fold_prefit_uniqueness",
        "status": "frozen_before_fold_validation_return_read",
        "created_at": utc_now(),
        "fold": int(fold["fold"]),
        "training": [fold["training"][0], fold["training"][1]],
        "validation": [validation_start, validation_end],
        "fit": fit_payload,
        "validation_score_snapshot": score_binding,
        "uniqueness": audits,
        "all_live_trials_audited_before_validation_returns": True,
        "validation_daily_price_fields_read_before_record": [],
        "validation_forward_return_fields_read_before_record": False,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
    }
    path = output_root / f"fold_{fold['fold']}_prefit_uniqueness.json"
    atomic_json(path, payload)
    payload["record_binding"] = {"path": str(path), "sha256": file_sha256(path)}
    return payload, trial_scores, identities


def evaluate_validation(
    template: dict[str, Any],
    fold: dict[str, Any],
    trial_scores: dict[str, np.ndarray],
    identities: pd.DataFrame,
    batch_size: int,
) -> dict[str, Any]:
    validation_start, validation_end = fold["validation"]
    market, calendar = engine.load_market_context(
        template, validation_end, validation_start, batch_size
    )
    schedule = engine.global_signal_schedule(calendar)
    factor_frame = identities[["trade_date", "instrument"]].copy()
    for trial_id, values in trial_scores.items():
        factor_frame[_score_column(trial_id)] = values
    panel = engine.build_signal_panel(market, factor_frame, schedule)
    quotes = engine.quote_lookup(market)
    results: dict[str, Any] = {}
    for trial_id in trial_scores:
        trial = {"feature_set": [trial_id], "weights": [1.0]}
        results[trial_id] = engine.evaluate_trial_period(
            panel,
            quotes,
            calendar,
            schedule,
            trial,
            validation_start,
            validation_end,
            PURGE_SIGNAL_SESSIONS,
            include_sensitivity=True,
        )
    return results


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
    normalized = [
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
        float(item["normalized_execution"]["maximum_drawdown"])
        for item in validations
    ]
    positive_ic = sum(value > 0.0 for value in mean_ics)
    positive_normalized = sum(value > 0.0 for value in normalized)
    positive_pilot = sum(value > 0.0 for value in pilot10)
    aggregate = {
        "normalized_return": compound(normalized),
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
    operational = not any(reason for reason in reasons if reason != "development_quality_or_aggregate_gate_failed")
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


def build_ledger(trial_records: list[dict[str, Any]]) -> dict[str, Any]:
    previous = CHAIN_GENESIS
    entries: list[dict[str, Any]] = []
    for record in trial_records:
        entry = {**record, "previous_entry_sha256": previous}
        entry["entry_sha256"] = value_sha256(entry)
        previous = entry["entry_sha256"]
        entries.append(entry)
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign102_trial_ledger",
        "append_only": True,
        "campaign": {"protocol_sha256": PROTOCOL_SHA256},
        "chain_genesis": CHAIN_GENESIS,
        "entries": entries,
        "chain_tip_sha256": previous,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
    }


def _rank_survivors(records: list[dict[str, Any]]) -> list[str]:
    passing = [record for record in records if record["decision"]["passed"]]
    passing.sort(
        key=lambda record: (
            -record["decision"]["positive_mean_rank_ic_fold_count"],
            -record["decision"]["positive_pilot_10bp_return_fold_count"],
            -record["decision"]["positive_normalized_return_fold_count"],
            -record["decision"]["median_validation_mean_rank_ic"],
            -record["decision"]["median_validation_pilot_10bp_return"],
            -record["decision"]["development_aggregate"]["pilot_20bp_return"],
            -record["decision"]["worst_validation_normalized_drawdown"],
            record["trial_id"],
        )
    )
    return [record["trial_id"] for record in passing[:1]]


def run_development(args: argparse.Namespace) -> dict[str, Any]:
    _implementation_freeze()
    protocol, template = load_frozen_context()
    verification = design.verify_snapshot(DEFAULT_DESIGN_MANIFEST)
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
    preexisting = list(output_root.iterdir())
    if preexisting:
        raise Campaign102Error(
            "incomplete Campaign102 development output exists; preserve it and use an explicit recovery revision"
        )
    intent = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign102_development_intent",
        "status": "training_return_open_pending_chronological_completion",
        "opened_at": utc_now(),
        "protocol_sha256": PROTOCOL_SHA256,
        "design_manifest_sha256": DESIGN_MANIFEST_SHA256,
        "design_audit_sha256": DESIGN_AUDIT_SHA256,
        "runner_sha256": file_sha256(Path(__file__).resolve()),
        "validation_returns_may_be_read_only_after_each_fold_prefit_uniqueness_record": True,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
    }
    atomic_json(output_root / "development_intent.json", intent)
    folds = [
        {
            "fold": int(item["fold"]),
            "training": list(item["training"]),
            "validation": list(item["validation"]),
        }
        for item in protocol["walkforward_folds"]
    ]
    live = {trial_id: regularization for trial_id, regularization in TRIALS}
    records: dict[str, dict[str, Any]] = {
        trial_id: {
            "trial_id": trial_id,
            "regularization": regularization,
            "phase": "development_walkforward",
            "created_at": intent["opened_at"],
            "formula": protocol["model_family"]["objective"],
            "direction": "higher",
            "source_feature_count": design.NUMERIC_COUNT,
            "source_feature_order_sha256": design.NUMERIC_ORDER_SHA256,
            "folds": [],
            "validation_metrics": [],
            "candidate49_historical_return_read": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
        }
        for trial_id, regularization in TRIALS
    }
    try:
        for fold in folds:
            if not live:
                break
            print(f"fold {fold['fold']}: loading training returns and fitting", flush=True)
            fit_payload, training_metrics = fit_fold(template, fold, live, args.batch_size)
            print(f"fold {fold['fold']}: auditing validation scores before returns", flush=True)
            prefit, trial_scores, identities = validation_prefit_audit(
                fold, fit_payload, output_root
            )
            passed = {
                trial_id: score
                for trial_id, score in trial_scores.items()
                if prefit["uniqueness"][trial_id]["all_required_comparisons_passed"]
            }
            rejected = sorted(set(live) - set(passed))
            for trial_id in live:
                records[trial_id]["folds"].append(
                    {
                        "fold": fold["fold"],
                        "fit": fit_payload["fits"][trial_id],
                        "training_metrics": training_metrics[trial_id],
                        "prefit_uniqueness_record": prefit["record_binding"],
                        "uniqueness": prefit["uniqueness"][trial_id],
                        "validation_metrics": None,
                    }
                )
            for trial_id in rejected:
                records[trial_id]["terminal_before_validation_return_reason"] = (
                    f"fold_{fold['fold']}_uniqueness_failed"
                )
            live = {trial_id: live[trial_id] for trial_id in passed}
            if not live:
                continue
            print(f"fold {fold['fold']}: uniqueness passed; reading validation returns", flush=True)
            validation = evaluate_validation(
                template, fold, passed, identities, args.batch_size
            )
            metrics_payload = {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign102_fold_validation_metrics",
                "status": "completed_after_bound_prefit_uniqueness",
                "created_at": utc_now(),
                "fold": fold["fold"],
                "prefit_uniqueness_record": prefit["record_binding"],
                "validation_metrics": validation,
                "candidate49_historical_return_read": False,
                "candidate49_ledgers_changed": False,
            }
            metrics_path = output_root / f"fold_{fold['fold']}_validation_metrics.json"
            atomic_json(metrics_path, metrics_payload)
            metrics_binding = {"path": str(metrics_path), "sha256": file_sha256(metrics_path)}
            for trial_id in live:
                records[trial_id]["folds"][-1]["validation_metrics"] = validation[trial_id]
                records[trial_id]["folds"][-1]["validation_metrics_binding"] = metrics_binding
                records[trial_id]["validation_metrics"].append(validation[trial_id])
        trial_records = []
        for trial_id, _ in TRIALS:
            record = records[trial_id]
            record["decision"] = survivor_decision(record)
            record["status"] = (
                "development_survivor_gate_passed"
                if record["decision"]["passed"]
                else "development_rejected"
            )
            trial_records.append(record)
        survivors = _rank_survivors(trial_records)
        ledger = build_ledger(trial_records)
        ledger_path = output_root / "trial_ledger.json"
        atomic_json(ledger_path, ledger)
        survivor_record = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign102_development_survivors",
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
            "candidate49_historical_return_read": False,
            "candidate49_ledgers_changed": False,
        }
        survivor_path = output_root / "development_survivors.json"
        atomic_json(survivor_path, survivor_record)
        report = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign102_development_report",
            "status": "development_complete_survivors_frozen",
            "created_at": utc_now(),
            "protocol_sha256": PROTOCOL_SHA256,
            "design_verification": verification,
            "trial_count": len(trial_records),
            "validation_return_reading_trial_count": sum(
                len(record["validation_metrics"]) == 3 for record in trial_records
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
        atomic_json(report_path, report)
        return {
            "status": report["status"],
            "trial_count": report["trial_count"],
            "survivor_count": report["survivor_count"],
            "selected_survivor_trial_ids": survivors,
            "report_path": str(report_path),
            "report_sha256": file_sha256(report_path),
        }
    except BaseException as error:
        failure = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign102_development_failure",
            "status": "failed_preserved_requires_explicit_recovery_revision",
            "created_at": utc_now(),
            "error_type": type(error).__name__,
            "error": str(error),
            "training_or_validation_returns_may_have_been_read": True,
            "candidate49_historical_return_read": False,
            "candidate49_ledgers_changed": False,
            "provider_request_issued": False,
        }
        atomic_json(output_root / "development_failure.json", failure)
        raise


def status(args: argparse.Namespace) -> dict[str, Any]:
    output_root = Path(args.output_root).expanduser().resolve()
    result: dict[str, Any] = {
        "status": "frozen_pending_development",
        "output_root": str(output_root),
        "implementation_freeze_exists": DEFAULT_IMPLEMENTATION_FREEZE.is_file(),
        "historical_daily_price_or_return_values_read_by_status": False,
        "candidate49_ledgers_changed_by_status": False,
        "provider_request_issued_by_status": False,
    }
    if (output_root / "development_intent.json").exists():
        result["status"] = "development_opened_or_incomplete"
    if (output_root / "development_failure.json").exists():
        result["status"] = "development_failed_preserved"
    if (output_root / "development_report.json").exists():
        report = load_json(output_root / "development_report.json")
        result["status"] = report["status"]
        result["survivor_count"] = report["survivor_count"]
        result["selected_survivor_trial_ids"] = report["selected_survivor_trial_ids"]
    return result


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    subcommands = value.add_subparsers(dest="command", required=True)
    subcommands.add_parser("status")
    development = subcommands.add_parser("run-development")
    development.add_argument("--batch-size", type=int, default=100)
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "status":
            payload = status(args)
        elif args.command == "run-development":
            payload = run_development(args)
        else:
            raise Campaign102Error(f"unsupported command: {args.command}")
    except (Campaign102Error, ValueError, FileNotFoundError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False, indent=2))
        return 2
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
            default=engine.research._json_default,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
