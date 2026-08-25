#!/usr/bin/env python3
"""Run Campaign287's frozen session-balanced Alpha158 weighted MLP trial."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign as engine
from scripts import a_share_three_day_walkforward_campaign286 as campaign286


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_287_preregistration_20260825.json"
)
PROTOCOL_SHA256 = "135e9ff2dad4e9f006dd4cd21d1d37e7f20b165b913b5fc7220d2586847b4d8f"
CONCEPT_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_287_concept_scouting_20260825.json"
)
CONCEPT_SHA256 = "78c635116df5c5dc381e1357929bdda05bce48e69344da7dd25661b93d94d05e"
OVERLAP_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_287_model_overlap_audit_20260825.json"
)
OVERLAP_SHA256 = "2b43bbadfa59b1dd2b0550b7e345cacbf8f2a6b8e9175ee68c943cd6a5fed280"
CAMPAIGN286_TERMINAL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_286_terminal_result_20260825.json"
)
CAMPAIGN286_TERMINAL_SHA256 = (
    "f06b1e98e96a29a5cbc703ea87b8035d4f4e7086dcefaff0d09535b3a7a073d9"
)
DESIGN_IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_287_design_implementation_freeze_20260825.json"
)
DEVELOPMENT_EXECUTION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_287_development_execution_freeze_20260825.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign287.py"
)
OUTPUT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_287/balanced_mlp_v1"
)
DESIGN_EVIDENCE_PATH = OUTPUT_ROOT / "design_evidence.json"
FEATURE_COUNT = 158
TRIAL_ID = "wf287_alpha158_balanced_mlp_32"
SAMPLE_SIZE_PER_SESSION = 96
MINIMUM_RETAINED_TRAINING_SESSIONS = 60
MINIMUM_FINITE_TARGETS_PER_SESSION = 80
PURGE_SIGNAL_SESSIONS = 3
CHAIN_GENESIS = "0" * 64
FOLDS = (
    {
        "fold": 1,
        "train": ("2019-01-01", "2020-12-31"),
        "validation": ("2021-01-01", "2021-12-31"),
    },
    {
        "fold": 2,
        "train": ("2019-01-01", "2021-12-31"),
        "validation": ("2022-01-01", "2022-12-31"),
    },
    {
        "fold": 3,
        "train": ("2019-01-01", "2022-12-31"),
        "validation": ("2023-01-01", "2023-12-31"),
    },
)
MODEL_PARAMETERS = {
    "input_feature_count": 158,
    "hidden_width": 32,
    "activation": "relu",
    "optimizer": "adam",
    "l2": 0.0001,
    "batch_size": 2048,
    "learning_rate": 0.001,
    "epochs": 20,
    "shuffle": True,
    "random_state": 287,
    "beta_1": 0.9,
    "beta_2": 0.999,
    "epsilon": 1e-8,
    "gradient_clip_l2_norm": 5.0,
}


class Campaign287Error(RuntimeError):
    """Fail closed when Campaign287 evidence or execution changes."""


def file_sha256(path: Path) -> str:
    return campaign286.file_sha256(path)


def load_json(path: Path) -> dict[str, Any]:
    return campaign286.load_json(path)


def require_file(path: Path, expected: str, label: str) -> None:
    try:
        campaign286.require_file(path, expected, label)
    except campaign286.Campaign286Error as error:
        raise Campaign287Error(str(error)) from error


def hash_array(values: np.ndarray, dtype: str) -> str:
    array = np.asarray(values).astype(dtype, copy=False)
    return hashlib.sha256(array.tobytes(order="C")).hexdigest()


def protocol_folds(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for record in protocol.get("walkforward_folds") or []:
        result.append(
            {
                "fold": int(record["fold"]),
                "train": tuple(record["training"]),
                "validation": tuple(record["validation"]),
            }
        )
    return result


def validate_common() -> tuple[dict[str, Any], dict[str, Any]]:
    require_file(PROTOCOL_PATH, PROTOCOL_SHA256, "Campaign287 protocol")
    require_file(CONCEPT_PATH, CONCEPT_SHA256, "Campaign287 concept catalog")
    require_file(OVERLAP_PATH, OVERLAP_SHA256, "Campaign287 overlap audit")
    require_file(
        CAMPAIGN286_TERMINAL_PATH,
        CAMPAIGN286_TERMINAL_SHA256,
        "Campaign286 terminal result",
    )
    protocol = load_json(PROTOCOL_PATH)
    try:
        _, manifest = campaign286.validate_context()
    except campaign286.Campaign286Error as error:
        raise Campaign287Error(str(error)) from error
    model = protocol.get("model_trial") or {}
    design = protocol.get("zero_return_design_stage") or {}
    if not (
        protocol.get("kind") == "a_share_three_day_walkforward_campaign287_preregistration"
        and protocol.get("status")
        == "frozen_one_trial_complete_alpha158_balanced_mlp_before_campaign287_feature_sample_preprocessing_or_returns"
        and protocol_folds(protocol) == list(FOLDS)
        and model.get("trial_id") == TRIAL_ID
        and model.get("configuration_count") == 1
        and design.get("training_sample_size_per_contained_signal_session")
        == SAMPLE_SIZE_PER_SESSION
        and design.get("minimum_retained_training_sessions_per_fold")
        == MINIMUM_RETAINED_TRAINING_SESSIONS
        and (protocol.get("complete_feature_library") or {}).get("feature_count")
        == FEATURE_COUNT
        and (protocol.get("complete_feature_library") or {}).get(
            "feature_subset_search_allowed"
        )
        is False
        and manifest.get("dataset_sha256") == campaign286.DESIGN_DATASET_SHA256
        and manifest.get("feature_count") == FEATURE_COUNT
        and manifest.get("lockbox_2024_2025_feature_or_return_values_read") is False
    ):
        raise Campaign287Error("Campaign287 frozen protocol context changed")
    return protocol, manifest


def _validate_freeze(path: Path, expected_kind: str, expected_status: str) -> dict[str, Any]:
    if not path.is_file():
        raise Campaign287Error(f"missing Campaign287 freeze: {path}")
    record = load_json(path)
    runner = record.get("runner") or {}
    tests = record.get("tests") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind") == expected_kind
        and record.get("status") == expected_status
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and runner.get("path") == str(Path(__file__).resolve().relative_to(REPO_ROOT))
        and runner.get("sha256") == file_sha256(Path(__file__).resolve())
        and tests.get("path") == str(TEST_PATH.relative_to(REPO_ROOT))
        and tests.get("sha256") == file_sha256(TEST_PATH)
        and boundary.get("provider_request_issued_before_freeze") is False
        and boundary.get("candidate49_ledgers_changed_before_freeze") is False
        and boundary.get("lockbox_2024_2025_return_read_before_freeze") is False
    ):
        raise Campaign287Error("Campaign287 implementation freeze changed")
    return record


def validate_design_freeze() -> dict[str, Any]:
    record = _validate_freeze(
        DESIGN_IMPLEMENTATION_FREEZE_PATH,
        "a_share_three_day_walkforward_campaign287_design_implementation_freeze",
        "frozen_before_campaign287_design_partition_row_or_return_read",
    )
    boundary = record.get("research_boundary") or {}
    if not (
        boundary.get("campaign287_design_partition_row_read_before_freeze") is False
        and boundary.get("campaign287_sample_or_preprocessing_computed_before_freeze")
        is False
        and boundary.get("training_or_validation_return_read_before_freeze") is False
    ):
        raise Campaign287Error("Campaign287 design freeze boundary changed")
    return record


def validate_development_freeze() -> dict[str, Any]:
    record = _validate_freeze(
        DEVELOPMENT_EXECUTION_FREEZE_PATH,
        "a_share_three_day_walkforward_campaign287_development_execution_freeze",
        "frozen_after_zero_return_design_before_campaign287_training_or_validation_return_read",
    )
    evidence = record.get("design_evidence") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        evidence.get("path") == str(DESIGN_EVIDENCE_PATH.relative_to(REPO_ROOT))
        and evidence.get("sha256") == file_sha256(DESIGN_EVIDENCE_PATH)
        and boundary.get("training_or_validation_return_read_before_freeze") is False
        and boundary.get("model_fit_before_freeze") is False
    ):
        raise Campaign287Error("Campaign287 development freeze changed")
    return record


def local_calendar() -> pd.DatetimeIndex:
    values = [
        line.strip()
        for line in campaign286.SOURCE_CALENDAR_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    calendar = pd.DatetimeIndex(pd.to_datetime(values, errors="raise")).normalize()
    if not calendar.is_monotonic_increasing or calendar.has_duplicates:
        raise Campaign287Error("source calendar identity changed")
    return calendar


def deterministic_sample_positions(
    identities: pd.DataFrame,
    eligible: np.ndarray,
    sample_size: int = SAMPLE_SIZE_PER_SESSION,
) -> tuple[np.ndarray, dict[str, Any]]:
    support = np.asarray(eligible, dtype=bool)
    if len(identities) != len(support) or identities["stock_day_key"].duplicated().any():
        raise Campaign287Error("sampling identity changed")
    frame = identities[["trade_date", "instrument", "stock_day_key"]].copy()
    frame["position"] = np.arange(len(frame), dtype=np.int64)
    frame = frame.loc[support]
    selected: list[int] = []
    retained_names: list[int] = []
    excluded_sessions = 0
    for session, group in frame.groupby("trade_date", sort=True):
        if len(group) < sample_size:
            excluded_sessions += 1
            continue
        date_text = pd.Timestamp(session).strftime("%Y-%m-%d")
        ordered = sorted(
            (
                hashlib.sha256(
                    f"287|{date_text}|{instrument}".encode("utf-8")
                ).digest(),
                str(instrument),
                int(position),
            )
            for instrument, position in zip(
                group["instrument"], group["position"], strict=True
            )
        )
        selected.extend(item[2] for item in ordered[:sample_size])
        retained_names.append(len(group))
    positions = np.asarray(selected, dtype=np.int64)
    if (
        len(retained_names) < MINIMUM_RETAINED_TRAINING_SESSIONS
        or len(positions) != len(retained_names) * sample_size
        or len(np.unique(positions)) != len(positions)
    ):
        raise Campaign287Error("deterministic training sample gate failed")
    keys = identities.iloc[positions]["stock_day_key"].to_numpy(dtype=np.int64)
    return positions, {
        "retained_training_sessions": len(retained_names),
        "excluded_small_training_sessions": excluded_sessions,
        "sampled_rows": len(positions),
        "sample_size_per_session": sample_size,
        "minimum_eligible_names_in_retained_session": int(min(retained_names)),
        "maximum_eligible_names_in_retained_session": int(max(retained_names)),
        "sample_stock_day_keys_sha256": hash_array(keys, "<i8"),
    }


def preprocessing_statistics(
    sample_matrix: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    values = np.asarray(sample_matrix, dtype=np.float64).copy()
    if values.ndim != 2 or values.shape[1] != FEATURE_COUNT:
        raise Campaign287Error("preprocessing matrix shape changed")
    values[~np.isfinite(values)] = np.nan
    finite_counts = np.isfinite(values).sum(axis=0).astype(np.int64)
    if int(finite_counts.min()) < 512:
        raise Campaign287Error("preprocessing feature finite-count gate failed")
    centers = np.nanmedian(values, axis=0)
    q25 = np.nanpercentile(values, 25.0, axis=0)
    q75 = np.nanpercentile(values, 75.0, axis=0)
    scales = np.maximum(q75 - q25, 1e-6)
    if not (np.isfinite(centers).all() and np.isfinite(scales).all() and (scales > 0).all()):
        raise Campaign287Error("preprocessing statistics are invalid")
    return centers, scales, {
        "feature_count": FEATURE_COUNT,
        "minimum_finite_observations_per_feature": int(finite_counts.min()),
        "maximum_finite_observations_per_feature": int(finite_counts.max()),
        "finite_counts_sha256": hash_array(finite_counts, "<i8"),
        "centers_sha256": hash_array(centers, "<f8"),
        "scales_sha256": hash_array(scales, "<f8"),
        "minimum_scale": float(scales.min()),
        "maximum_scale": float(scales.max()),
        "missing_fill_after_scaling": 0.0,
        "clip": [-8.0, 8.0],
    }


def transform_features(
    matrix: np.ndarray, centers: np.ndarray, scales: np.ndarray
) -> np.ndarray:
    values = np.asarray(matrix, dtype=np.float32).copy()
    values[~np.isfinite(values)] = np.nan
    values = (values - centers.astype(np.float32)) / scales.astype(np.float32)
    values[~np.isfinite(values)] = 0.0
    return np.clip(values, -8.0, 8.0).astype(np.float32, copy=False)


def fold_design_bundle(
    fold: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    calendar = local_calendar()
    schedule = engine.global_signal_schedule(calendar)
    period = engine.purged_period_schedule(
        schedule, fold["train"][0], fold["train"][1], PURGE_SIGNAL_SESSIONS
    )
    years = range(2019, pd.Timestamp(fold["train"][1]).year + 1)
    identities, matrix, eligible, design_stats = campaign286.load_design_years(
        years, manifest, allowed_dates=period["signal_date"]
    )
    positions, sample_stats = deterministic_sample_positions(identities, eligible)
    centers, scales, preprocessing = preprocessing_statistics(matrix[positions])
    fold_record = {
        "fold": int(fold["fold"]),
        "training": list(fold["train"]),
        "scheduled_signal_count_after_containment_and_purge": len(period),
        "selected_design": design_stats,
        "sample": sample_stats,
        "preprocessing": preprocessing,
        "historical_label_or_forward_return_values_read": False,
    }
    fold_record["fold_design_sha256"] = engine.value_sha256(fold_record)
    return {
        "record": fold_record,
        "identities": identities,
        "matrix": matrix,
        "eligible": eligible,
        "sample_positions": positions,
        "sample_keys": identities.iloc[positions]["stock_day_key"].to_numpy(
            dtype=np.int64
        ),
        "centers": centers,
        "scales": scales,
    }


def plan_design() -> dict[str, Any]:
    validate_design_freeze()
    validate_common()
    ready = not OUTPUT_ROOT.exists() or not list(OUTPUT_ROOT.iterdir())
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign287_design_plan",
        "status": "ready_for_zero_return_design" if ready else "not_ready_preserve_existing_output",
        "ready": ready,
        "fold_count": 3,
        "output_root": str(OUTPUT_ROOT),
        "campaign287_design_partition_rows_read_by_plan": False,
        "historical_return_values_read_by_plan": False,
        "lockbox_2024_2025_return_fields_read_by_plan": False,
        "provider_request_issued": False,
        "candidate49_ledgers_changed": False,
    }


def build_design(confirm: bool) -> dict[str, Any]:
    if not confirm:
        raise Campaign287Error("build-design requires --confirm-build")
    payload = plan_design()
    if payload["ready"] is not True:
        raise Campaign287Error("Campaign287 design plan is not ready")
    _, manifest = validate_common()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=False)
    try:
        records = []
        for fold in FOLDS:
            bundle = fold_design_bundle(fold, manifest)
            records.append(bundle["record"])
            del bundle
            gc.collect()
        evidence = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign287_zero_return_design_evidence",
            "status": "passed_ready_for_frozen_development_execution",
            "created_at": campaign286.utc_now(),
            "protocol_sha256": PROTOCOL_SHA256,
            "source_design_manifest_sha256": campaign286.DESIGN_MANIFEST_SHA256,
            "source_design_dataset_sha256": campaign286.DESIGN_DATASET_SHA256,
            "source_feature_library_sha256": campaign286.design.FEATURE_LIBRARY_SHA256,
            "feature_count": FEATURE_COUNT,
            "folds": records,
            "all_fold_design_gates_passed": True,
            "campaign287_design_partition_rows_read": True,
            "campaign287_sample_and_preprocessing_computed": True,
            "historical_label_or_forward_return_values_read": False,
            "lockbox_2024_2025_feature_or_return_values_read": False,
            "provider_request_issued": False,
            "credential_loaded": False,
            "candidate49_ledgers_changed": False,
        }
        engine.atomic_write_json(DESIGN_EVIDENCE_PATH, evidence)
        return {
            "status": evidence["status"],
            "design_evidence_path": str(DESIGN_EVIDENCE_PATH),
            "design_evidence_sha256": file_sha256(DESIGN_EVIDENCE_PATH),
            "fold_count": len(records),
            "historical_return_values_read": False,
        }
    except BaseException as error:
        if OUTPUT_ROOT.exists():
            engine.atomic_write_json(
                OUTPUT_ROOT / "design_failure.json",
                {
                    "schema_version": 1,
                    "kind": "a_share_three_day_walkforward_campaign287_design_failure",
                    "status": "failed_preserved_requires_explicit_recovery_revision",
                    "created_at": campaign286.utc_now(),
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "historical_return_values_read": False,
                    "lockbox_2024_2025_return_fields_read": False,
                    "provider_request_issued": False,
                    "candidate49_ledgers_changed": False,
                },
            )
        raise


@dataclass
class WeightedMLPRegressor:
    """Small deterministic weighted MLP with a fixed Adam training loop."""

    parameters: dict[str, Any]
    weights_: dict[str, np.ndarray] | None = None
    loss_curve_: list[float] | None = None

    def fit(
        self, matrix: np.ndarray, target: np.ndarray, sample_weight: np.ndarray
    ) -> "WeightedMLPRegressor":
        x = np.asarray(matrix, dtype=np.float32)
        y = np.asarray(target, dtype=np.float32).reshape(-1)
        weight = np.asarray(sample_weight, dtype=np.float32).reshape(-1)
        if not (
            x.ndim == 2
            and x.shape[1] == int(self.parameters["input_feature_count"])
            and len(x) == len(y) == len(weight)
            and len(x) > 0
            and np.isfinite(x).all()
            and np.isfinite(y).all()
            and np.isfinite(weight).all()
            and (weight > 0).all()
        ):
            raise Campaign287Error("weighted MLP fit inputs changed")
        weight = weight / weight.sum()
        seed = int(self.parameters["random_state"])
        hidden = int(self.parameters["hidden_width"])
        rng = np.random.default_rng(seed)
        w1 = rng.normal(0.0, math.sqrt(2.0 / x.shape[1]), (x.shape[1], hidden)).astype(
            np.float32
        )
        b1 = np.zeros(hidden, dtype=np.float32)
        w2 = rng.normal(0.0, 1.0 / math.sqrt(hidden), hidden).astype(np.float32)
        b2 = np.zeros(1, dtype=np.float32)
        arrays = [w1, b1, w2, b2]
        first = [np.zeros_like(value) for value in arrays]
        second = [np.zeros_like(value) for value in arrays]
        beta1 = float(self.parameters["beta_1"])
        beta2 = float(self.parameters["beta_2"])
        epsilon = float(self.parameters["epsilon"])
        learning_rate = float(self.parameters["learning_rate"])
        l2 = float(self.parameters["l2"])
        clip = float(self.parameters["gradient_clip_l2_norm"])
        batch_size = int(self.parameters["batch_size"])
        step = 0
        losses: list[float] = []
        for _ in range(int(self.parameters["epochs"])):
            order = rng.permutation(len(x)) if self.parameters["shuffle"] else np.arange(len(x))
            for start in range(0, len(order), batch_size):
                index = order[start : start + batch_size]
                xb, yb, wb = x[index], y[index], weight[index]
                hidden_pre = xb @ w1 + b1
                hidden_value = np.maximum(hidden_pre, 0.0)
                prediction = hidden_value @ w2 + b2[0]
                normalizer = float(wb.sum())
                output_gradient = (2.0 * wb * (prediction - yb) / normalizer).astype(
                    np.float32
                )
                gradients = [
                    xb.T @ ((output_gradient[:, None] * w2[None, :]) * (hidden_pre > 0))
                    + 2.0 * l2 * w1,
                    (((output_gradient[:, None] * w2[None, :]) * (hidden_pre > 0))).sum(
                        axis=0
                    ),
                    hidden_value.T @ output_gradient + 2.0 * l2 * w2,
                    np.asarray([output_gradient.sum()], dtype=np.float32),
                ]
                norm = math.sqrt(sum(float(np.square(value).sum()) for value in gradients))
                if norm > clip:
                    gradients = [value * (clip / norm) for value in gradients]
                step += 1
                for position, (parameter, gradient) in enumerate(zip(arrays, gradients, strict=True)):
                    first[position] = beta1 * first[position] + (1.0 - beta1) * gradient
                    second[position] = beta2 * second[position] + (1.0 - beta2) * np.square(
                        gradient
                    )
                    corrected_first = first[position] / (1.0 - beta1**step)
                    corrected_second = second[position] / (1.0 - beta2**step)
                    parameter -= learning_rate * corrected_first / (
                        np.sqrt(corrected_second) + epsilon
                    )
            prediction = np.maximum(x @ w1 + b1, 0.0) @ w2 + b2[0]
            loss = float(
                np.sum(weight * np.square(prediction - y))
                + l2 * (np.square(w1).sum() + np.square(w2).sum())
            )
            if not math.isfinite(loss):
                raise Campaign287Error("weighted MLP loss became nonfinite")
            losses.append(loss)
        self.weights_ = {"w1": w1, "b1": b1, "w2": w2, "b2": b2}
        self.loss_curve_ = losses
        return self

    def predict(self, matrix: np.ndarray) -> np.ndarray:
        if self.weights_ is None:
            raise Campaign287Error("weighted MLP is not fitted")
        x = np.asarray(matrix, dtype=np.float32)
        value = (
            np.maximum(x @ self.weights_["w1"] + self.weights_["b1"], 0.0)
            @ self.weights_["w2"]
            + self.weights_["b2"][0]
        )
        return np.asarray(value, dtype=np.float64)

    def save(self, path: Path) -> None:
        if self.weights_ is None or self.loss_curve_ is None:
            raise Campaign287Error("weighted MLP is not fitted")
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                np.savez_compressed(
                    handle,
                    **self.weights_,
                    loss_curve=np.asarray(self.loss_curve_, dtype=np.float64),
                    parameters_json=np.asarray(
                        json.dumps(self.parameters, sort_keys=True, separators=(",", ":"))
                    ),
                )
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def session_equal_target_weights(
    dates: Iterable[Any], target: np.ndarray, sampled: np.ndarray
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    sessions = pd.DatetimeIndex(dates).normalize().to_numpy(dtype="datetime64[D]")
    y = np.asarray(target, dtype=np.float64)
    sample = np.asarray(sampled, dtype=bool)
    initial = sample & np.isfinite(y)
    unique, inverse, counts = np.unique(
        sessions[initial], return_inverse=True, return_counts=True
    )
    if len(unique) < MINIMUM_RETAINED_TRAINING_SESSIONS or int(counts.min()) < MINIMUM_FINITE_TARGETS_PER_SESSION:
        raise Campaign287Error("finite sampled training target gate failed")
    valid = initial.copy()
    weights = np.zeros(len(y), dtype=np.float64)
    weights[valid] = 1.0 / (len(unique) * counts[inverse])
    daily = np.bincount(inverse, weights=weights[valid], minlength=len(unique))
    if not (
        math.isclose(float(weights.sum()), 1.0, rel_tol=0.0, abs_tol=1e-12)
        and np.allclose(daily, np.full(len(unique), 1.0 / len(unique)), atol=1e-12)
    ):
        raise Campaign287Error("sampled target session weights changed")
    return valid, weights, {
        "training_observations": int(valid.sum()),
        "training_sessions": len(unique),
        "minimum_finite_sampled_targets_per_session": int(counts.min()),
        "maximum_finite_sampled_targets_per_session": int(counts.max()),
        "session_equal_row_weight_sum": float(weights.sum()),
        "weights_sha256": hash_array(weights[valid], "<f8"),
    }


def model_scores(
    model: WeightedMLPRegressor,
    matrix: np.ndarray,
    eligible: np.ndarray,
    centers: np.ndarray,
    scales: np.ndarray,
    batch_size: int = 65_536,
) -> np.ndarray:
    support = np.asarray(eligible, dtype=bool)
    result = np.full(len(matrix), np.nan, dtype=np.float64)
    positions = np.flatnonzero(support)
    for start in range(0, len(positions), batch_size):
        index = positions[start : start + batch_size]
        transformed = transform_features(matrix[index], centers, scales)
        result[index] = model.predict(transformed)
    if not np.isfinite(result[support]).all():
        raise Campaign287Error("eligible weighted MLP score is nonfinite")
    return result


def compare_fold_design(bundle: dict[str, Any], evidence: dict[str, Any]) -> None:
    matches = [
        record
        for record in evidence.get("folds") or []
        if int(record.get("fold", -1)) == int(bundle["record"]["fold"])
    ]
    if len(matches) != 1 or matches[0] != bundle["record"]:
        raise Campaign287Error("Campaign287 fold design evidence changed")


def fit_training_fold(
    fold: dict[str, Any],
    manifest: dict[str, Any],
    evidence: dict[str, Any],
    batch_size: int,
) -> tuple[dict[str, Any], WeightedMLPRegressor, dict[str, Any]]:
    bundle = fold_design_bundle(fold, manifest)
    compare_fold_design(bundle, evidence)
    context = campaign286.model_context()
    panel, quotes, calendar, schedule, matrix, eligible, selected_design = (
        campaign286.build_training_panel(
            context, manifest, fold["train"][1], batch_size
        )
    )
    panel_keys = campaign286.design.compact_stock_day_keys(
        panel["signal_date"], panel["instrument"]
    )
    sampled = np.isin(panel_keys, bundle["sample_keys"], assume_unique=False) & eligible
    returns = pd.to_numeric(panel["forward_gross_return"], errors="coerce").copy()
    returns.loc[~eligible] = np.nan
    target = campaign286.target_percentiles(panel["signal_date"], returns)
    valid, weights, weight_stats = session_equal_target_weights(
        panel["signal_date"], target, sampled
    )
    x = transform_features(matrix[valid], bundle["centers"], bundle["scales"])
    model = WeightedMLPRegressor(dict(MODEL_PARAMETERS)).fit(
        x, target[valid], weights[valid]
    )
    model_path = OUTPUT_ROOT / f"fold_{fold['fold']}_model" / f"{TRIAL_ID}.npz"
    model.save(model_path)
    score = model_scores(
        model, matrix, eligible, bundle["centers"], bundle["scales"]
    )
    panel[engine.factor_score_column(TRIAL_ID)] = score
    training_metrics = engine.evaluate_trial_period(
        panel,
        quotes,
        calendar,
        schedule,
        {"feature_set": [TRIAL_ID], "weights": [1.0]},
        fold["train"][0],
        fold["train"][1],
        PURGE_SIGNAL_SESSIONS,
        include_sensitivity=False,
    )
    fit = {
        "trial_id": TRIAL_ID,
        "resolved_parameters": MODEL_PARAMETERS,
        "training": weight_stats,
        "selected_design": selected_design,
        "zero_return_fold_design_sha256": bundle["record"]["fold_design_sha256"],
        "preprocessing": bundle["record"]["preprocessing"],
        "loss_curve": model.loss_curve_,
        "initial_loss": model.loss_curve_[0],
        "final_loss": model.loss_curve_[-1],
        "model_artifact": {
            "path": str(model_path),
            "sha256": file_sha256(model_path),
            "bytes": model_path.stat().st_size,
        },
        "numpy_version": np.__version__,
    }
    return fit, model, training_metrics


def validation_prefit(
    fold: dict[str, Any],
    manifest: dict[str, Any],
    evidence: dict[str, Any],
    model: WeightedMLPRegressor,
    fit: dict[str, Any],
) -> tuple[dict[str, np.ndarray], pd.DataFrame, dict[str, Any]]:
    bundle = fold_design_bundle(fold, manifest)
    compare_fold_design(bundle, evidence)
    year = pd.Timestamp(fold["validation"][0]).year
    identities, matrix, eligible, design_stats = campaign286.load_design_years(
        [year], manifest
    )
    score = model_scores(
        model, matrix, eligible, bundle["centers"], bundle["scales"]
    )
    calendar = local_calendar()
    schedule = engine.purged_period_schedule(
        engine.global_signal_schedule(calendar),
        fold["validation"][0],
        fold["validation"][1],
        PURGE_SIGNAL_SESSIONS,
    )
    dates = pd.DatetimeIndex(identities["trade_date"]).normalize()
    good_sessions = 0
    minimum_finite = None
    minimum_unique = None
    for session in schedule["signal_date"]:
        mask = dates.eq(pd.Timestamp(session)) & eligible & np.isfinite(score)
        count = int(mask.sum())
        unique = int(np.unique(score[mask]).size)
        minimum_finite = count if minimum_finite is None else min(minimum_finite, count)
        minimum_unique = unique if minimum_unique is None else min(minimum_unique, unique)
        if count >= 50 and unique >= 2:
            good_sessions += 1
    gate_passed = bool(
        good_sessions >= 60
        and minimum_finite is not None
        and minimum_finite >= 50
        and minimum_unique is not None
        and minimum_unique >= 2
    )
    snapshot = campaign286.write_score_snapshot(
        OUTPUT_ROOT / f"fold_{fold['fold']}_validation_scores.parquet",
        identities,
        {TRIAL_ID: score},
    )
    payload = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign287_fold_prefit_scores",
        "status": (
            "frozen_score_gate_passed_before_validation_return_read"
            if gate_passed
            else "frozen_score_gate_failed_validation_returns_remain_unread"
        ),
        "created_at": campaign286.utc_now(),
        "fold": int(fold["fold"]),
        "training": list(fold["train"]),
        "validation": list(fold["validation"]),
        "fit": fit,
        "validation_design": design_stats,
        "validation_score_snapshot": snapshot,
        "score_gate": {
            "passed": gate_passed,
            "scheduled_validation_signals": len(schedule),
            "good_nonconstant_score_sessions": good_sessions,
            "minimum_finite_scores_per_scheduled_signal": minimum_finite,
            "minimum_unique_scores_per_scheduled_signal": minimum_unique,
        },
        "validation_daily_price_fields_read_before_record": [],
        "validation_forward_return_fields_read_before_record": False,
        "lockbox_2024_2025_return_fields_read": False,
        "candidate49_ledgers_changed": False,
    }
    path = OUTPUT_ROOT / f"fold_{fold['fold']}_prefit_scores.json"
    engine.atomic_write_json(path, payload)
    payload["record_binding"] = {"path": str(path), "sha256": file_sha256(path)}
    return {TRIAL_ID: score}, identities, payload


def prevalue_entries() -> list[dict[str, Any]]:
    concept = load_json(CONCEPT_PATH)
    return [
        {
            "attempt_id": item["catalog_id"],
            "phase": "prevalue_concept_scouting",
            "name": item["name"],
            "outcome": item["decision"],
            "reason": item["reason"],
            "evidence": {
                "path": str(CONCEPT_PATH.relative_to(REPO_ROOT)),
                "sha256": CONCEPT_SHA256,
            },
            "alpha158_feature_values_previously_read_by_campaign286": True,
            "campaign287_training_or_validation_return_fields_read": False,
        }
        for item in concept["finite_prevalue_concept_catalog"]
    ]


def build_ledger(trial: dict[str, Any]) -> dict[str, Any]:
    entries = []
    previous = CHAIN_GENESIS
    for record in [*prevalue_entries(), trial]:
        entry = {**record, "previous_entry_sha256": previous}
        entry["entry_sha256"] = engine.value_sha256(entry)
        previous = entry["entry_sha256"]
        entries.append(entry)
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign287_trial_ledger",
        "append_only": True,
        "campaign": {
            "protocol_sha256": PROTOCOL_SHA256,
            "design_dataset_sha256": campaign286.DESIGN_DATASET_SHA256,
            "design_evidence_sha256": file_sha256(DESIGN_EVIDENCE_PATH),
        },
        "chain_genesis": CHAIN_GENESIS,
        "entries": entries,
        "entry_count": len(entries),
        "prevalue_concept_attempt_count": 7,
        "infrastructure_failure_attempt_count": 0,
        "model_trial_attempt_count": 1,
        "validation_return_fold_count": len(trial.get("validation_metrics") or []),
        "chain_tip_sha256": previous,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
    }


def plan_development() -> dict[str, Any]:
    validate_development_freeze()
    validate_common()
    evidence = load_json(DESIGN_EVIDENCE_PATH)
    existing = [
        path.name
        for path in OUTPUT_ROOT.iterdir()
        if path.name not in {"design_evidence.json"}
    ]
    ready = bool(
        not existing
        and evidence.get("status") == "passed_ready_for_frozen_development_execution"
        and len(evidence.get("folds") or []) == 3
    )
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign287_development_plan",
        "status": (
            "ready_to_open_2019_2023_training_and_validation_returns"
            if ready
            else "not_ready_preserve_existing_output"
        ),
        "ready": ready,
        "trial_count": 1,
        "fold_count": 3,
        "existing_non_design_outputs": existing,
        "historical_return_values_read_by_plan": False,
        "lockbox_2024_2025_return_fields_read_by_plan": False,
        "provider_request_issued": False,
        "candidate49_ledgers_changed": False,
    }


def run_development(confirm: bool, batch_size: int) -> dict[str, Any]:
    if not confirm:
        raise Campaign287Error("run-development requires --confirm-run")
    payload = plan_development()
    if payload["ready"] is not True:
        raise Campaign287Error("Campaign287 development plan is not ready")
    _, manifest = validate_common()
    evidence = load_json(DESIGN_EVIDENCE_PATH)
    intent = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign287_development_intent",
        "status": "training_return_open_pending_chronological_completion",
        "opened_at": campaign286.utc_now(),
        "protocol_sha256": PROTOCOL_SHA256,
        "design_evidence_sha256": file_sha256(DESIGN_EVIDENCE_PATH),
        "runner_sha256": file_sha256(Path(__file__).resolve()),
        "validation_scores_frozen_before_each_validation_return_read": True,
        "lockbox_2024_2025_remains_closed": True,
        "candidate49_ledgers_changed": False,
    }
    engine.atomic_write_json(OUTPUT_ROOT / "development_intent.json", intent)
    trial: dict[str, Any] = {
        "attempt_id": TRIAL_ID,
        "trial_id": TRIAL_ID,
        "parent_trial_id": None,
        "campaign_id": "campaign_287",
        "created_at": intent["opened_at"],
        "phase": "development_walkforward",
        "economic_hypothesis": "Smooth distributed nonlinear interactions across the complete raw Alpha158 library may generalize differently from Campaign286's boosted decision trees.",
        "formula": "fixed weighted one-hidden-layer ReLU MLP over all 158 training-fold median/IQR standardized Alpha158 features",
        "direction": "higher predicted within-session gross-return percentile",
        "feature_set": "complete Alpha158 in frozen order",
        "window_transform_threshold_filter_and_weight_configuration": {
            "sample_size_per_session": SAMPLE_SIZE_PER_SESSION,
            "preprocessing": "training-sample median/IQR, missing zero after scaling, clip [-8,8]",
            "model_parameters": MODEL_PARAMETERS,
        },
        "training_and_validation_folds": [
            {"fold": f["fold"], "train": list(f["train"]), "validation": list(f["validation"])}
            for f in FOLDS
        ],
        "data_and_code_fingerprints": {
            "protocol_sha256": PROTOCOL_SHA256,
            "design_dataset_sha256": campaign286.DESIGN_DATASET_SHA256,
            "design_evidence_sha256": file_sha256(DESIGN_EVIDENCE_PATH),
            "runner_sha256": file_sha256(Path(__file__).resolve()),
        },
        "fixed_execution_policy_fingerprints": {
            "prospective_execution_policy_sha256": "72c3c3871e153372ed9e7691c9d89ba1aeb2f6d02cc839761fefa5fee085e1bc",
            "pilot_execution_policy_sha256": "72235cd29fc14d43538238150bb2823dae1dd05b027b2c86a9872de89cc0d3f9",
        },
        "folds": [],
        "training_metrics": [],
        "validation_metrics": [],
        "locked_backtest_metrics_when_opened": None,
        "candidate49_historical_return_read": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }
    try:
        for fold in FOLDS:
            print(f"fold {fold['fold']}: fitting frozen weighted MLP", flush=True)
            fit, model, training_metrics = fit_training_fold(
                fold, manifest, evidence, batch_size
            )
            print(
                f"fold {fold['fold']}: freezing validation scores before returns",
                flush=True,
            )
            scores, identities, prefit = validation_prefit(
                fold, manifest, evidence, model, fit
            )
            fold_record: dict[str, Any] = {
                "fold": fold["fold"],
                "fit": fit,
                "training_metrics": training_metrics,
                "prefit_score_record": prefit["record_binding"],
                "score_gate": prefit["score_gate"],
            }
            trial["training_metrics"].append(training_metrics)
            if prefit["score_gate"]["passed"] is not True:
                fold_record["validation_metrics"] = None
                trial["folds"].append(fold_record)
                trial["status"] = "development_rejected_prefit_score_gate"
                trial["decision"] = {
                    "passed": False,
                    "operationally_admissible": False,
                    "rejection_reasons": [
                        f"fold_{fold['fold']}_prefit_score_gate_failed"
                    ],
                }
                break
            print(
                f"fold {fold['fold']}: reading contained validation returns", flush=True
            )
            validation = campaign286.evaluate_validation(
                campaign286.model_context(),
                fold,
                scores,
                identities,
                batch_size,
            )[TRIAL_ID]
            metrics_payload = {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign287_fold_validation_metrics",
                "status": "completed_after_bound_prefit_scores",
                "created_at": campaign286.utc_now(),
                "fold": fold["fold"],
                "prefit_score_record": prefit["record_binding"],
                "validation_metrics": {TRIAL_ID: validation},
                "lockbox_2024_2025_return_fields_read": False,
                "candidate49_ledgers_changed": False,
            }
            metrics_path = OUTPUT_ROOT / f"fold_{fold['fold']}_validation_metrics.json"
            engine.atomic_write_json(metrics_path, metrics_payload)
            fold_record["validation_metrics_binding"] = {
                "path": str(metrics_path),
                "sha256": file_sha256(metrics_path),
            }
            fold_record["validation_metrics"] = validation
            trial["folds"].append(fold_record)
            trial["validation_metrics"].append(validation)
            del fit, model, training_metrics, scores, identities, validation
            gc.collect()
        if "decision" not in trial:
            trial["decision"] = campaign286.survivor_decision(trial)
            trial["status"] = (
                "development_survivor_gate_passed"
                if trial["decision"]["passed"]
                else "development_rejected"
            )
        survivors = [TRIAL_ID] if trial["decision"]["passed"] else []
        ledger = build_ledger(trial)
        ledger_path = OUTPUT_ROOT / "trial_ledger.json"
        engine.atomic_write_json(ledger_path, ledger)
        survivor_payload = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign287_development_survivors",
            "status": "frozen_before_2024_2025_return_read",
            "created_at": campaign286.utc_now(),
            "ledger": {"path": str(ledger_path), "sha256": file_sha256(ledger_path)},
            "trial_decisions": {TRIAL_ID: trial["decision"]},
            "selected_lockbox_survivor_trial_ids": survivors,
            "selected_survivor_count": len(survivors),
            "maximum_survivors": 1,
            "lockbox_return_fields_read": False,
            "candidate49_ledgers_changed": False,
        }
        survivor_path = OUTPUT_ROOT / "development_survivors.json"
        engine.atomic_write_json(survivor_path, survivor_payload)
        report = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign287_development_report",
            "status": "development_complete_survivors_frozen",
            "created_at": campaign286.utc_now(),
            "protocol_sha256": PROTOCOL_SHA256,
            "design_evidence_sha256": file_sha256(DESIGN_EVIDENCE_PATH),
            "trial_count": 1,
            "ledger_entry_count": ledger["entry_count"],
            "validation_return_reading_trial_count": (
                1 if trial["validation_metrics"] else 0
            ),
            "model_fold_validation_return_reads": len(trial["validation_metrics"]),
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
        report_path = OUTPUT_ROOT / "development_report.json"
        engine.atomic_write_json(report_path, report)
        return {
            "status": report["status"],
            "trial_count": 1,
            "survivor_count": len(survivors),
            "selected_survivor_trial_ids": survivors,
            "model_fold_validation_return_reads": len(trial["validation_metrics"]),
            "report_path": str(report_path),
            "report_sha256": file_sha256(report_path),
        }
    except BaseException as error:
        engine.atomic_write_json(
            OUTPUT_ROOT / "development_failure.json",
            {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign287_development_failure",
                "status": "failed_preserved_requires_explicit_recovery_revision",
                "created_at": campaign286.utc_now(),
                "error_type": type(error).__name__,
                "error": str(error),
                "training_or_validation_returns_may_have_been_read": True,
                "lockbox_2024_2025_return_fields_read": False,
                "candidate49_ledgers_changed": False,
                "provider_request_issued": False,
            },
        )
        raise


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    subcommands = command.add_subparsers(dest="command", required=True)
    subcommands.add_parser("plan-design")
    build = subcommands.add_parser("build-design")
    build.add_argument("--confirm-build", action="store_true")
    subcommands.add_parser("plan-development")
    run = subcommands.add_parser("run-development")
    run.add_argument("--confirm-run", action="store_true")
    run.add_argument("--batch-size", type=int, default=512)
    return command


def main() -> int:
    args = parser().parse_args()
    if args.command == "plan-design":
        payload = plan_design()
    elif args.command == "build-design":
        payload = build_design(args.confirm_build)
    elif args.command == "plan-development":
        payload = plan_development()
    elif args.command == "run-development":
        payload = run_development(args.confirm_run, args.batch_size)
    else:
        raise Campaign287Error(f"unsupported command: {args.command}")
    print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
