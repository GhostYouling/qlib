#!/usr/bin/env python3
"""Run Campaign288's frozen session-ordinal Alpha158 RFF ridge trial."""

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
import scipy
from scipy.stats import rankdata

from scripts import a_share_three_day_walkforward_campaign as engine
from scripts import a_share_three_day_walkforward_campaign286 as campaign286


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_288_preregistration_20260825.json"
)
PROTOCOL_SHA256 = "4ec58ecef2bd4da21ee144c33c27402225aa821f5938f20c564ac3c70934ab76"
CONCEPT_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_288_concept_scouting_20260825.json"
)
CONCEPT_SHA256 = "7c785fdc2d8c7a085cba2895a8e4a25df922cf4cc85e2d481bdb50f63f24eb12"
OVERLAP_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_288_model_overlap_audit_20260825.json"
)
OVERLAP_SHA256 = "cd1fd186a37ab27f29f3a0a0954905c25b1b6a9a9b18fc839a37f152f961d895"
CAMPAIGN287_TERMINAL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_287_terminal_result_20260825.json"
)
CAMPAIGN287_TERMINAL_SHA256 = (
    "d3ad876809040fbbbce682ef8bf8f77947aec6244a7bbfd23b1a7d150f90dd58"
)
CAMPAIGN287_STATE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_iteration_status_20260825_campaign287_terminal.json"
)
CAMPAIGN287_STATE_SHA256 = (
    "e00896e50cfd399bc0c442ac67872ede0f62bc1fbf195b69a5ee847b15dabbad"
)
DESIGN_IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_288_design_implementation_freeze_20260825.json"
)
DEVELOPMENT_EXECUTION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_288_development_execution_freeze_20260825.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign288.py"
)
OUTPUT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_288/ordinal_rff_ridge_v1"
)
DESIGN_EVIDENCE_PATH = OUTPUT_ROOT / "design_evidence.json"
FEATURE_COUNT = 158
RFF_DIMENSION = 128
RBF_GAMMA = 6.0 / FEATURE_COUNT
RIDGE_PENALTY = 0.001
RANDOM_STATE = 288
TRIAL_ID = "wf288_alpha158_ordinal_rff128_ridge"
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
    "input_feature_count": FEATURE_COUNT,
    "random_fourier_dimension": RFF_DIMENSION,
    "rbf_gamma": RBF_GAMMA,
    "random_state": RANDOM_STATE,
    "ridge_penalty": RIDGE_PENALTY,
    "output_intercept": False,
    "linear_solver": "numpy.linalg.solve_float64_symmetric_normal_equation",
}


class Campaign288Error(RuntimeError):
    """Fail closed when Campaign288 evidence or execution changes."""


def file_sha256(path: Path) -> str:
    return campaign286.file_sha256(path)


def load_json(path: Path) -> dict[str, Any]:
    return campaign286.load_json(path)


def require_file(path: Path, expected: str, label: str) -> None:
    try:
        campaign286.require_file(path, expected, label)
    except campaign286.Campaign286Error as error:
        raise Campaign288Error(str(error)) from error


def hash_array(values: np.ndarray, dtype: str) -> str:
    array = np.asarray(values).astype(dtype, copy=False)
    return hashlib.sha256(array.tobytes(order="C")).hexdigest()


def protocol_folds(protocol: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "fold": int(record["fold"]),
            "train": tuple(record["training"]),
            "validation": tuple(record["validation"]),
        }
        for record in protocol.get("walkforward_folds") or []
    ]


def validate_common() -> tuple[dict[str, Any], dict[str, Any]]:
    require_file(PROTOCOL_PATH, PROTOCOL_SHA256, "Campaign288 protocol")
    require_file(CONCEPT_PATH, CONCEPT_SHA256, "Campaign288 concept catalog")
    require_file(OVERLAP_PATH, OVERLAP_SHA256, "Campaign288 overlap audit")
    require_file(
        CAMPAIGN287_TERMINAL_PATH,
        CAMPAIGN287_TERMINAL_SHA256,
        "Campaign287 terminal result",
    )
    require_file(
        CAMPAIGN287_STATE_PATH,
        CAMPAIGN287_STATE_SHA256,
        "Campaign287 terminal state",
    )
    protocol = load_json(PROTOCOL_PATH)
    try:
        _, manifest = campaign286.validate_context()
    except campaign286.Campaign286Error as error:
        raise Campaign288Error(str(error)) from error
    model = protocol.get("model_trial") or {}
    design = protocol.get("zero_return_design_stage") or {}
    parameters = model.get("parameters") or {}
    if not (
        protocol.get("kind")
        == "a_share_three_day_walkforward_campaign288_preregistration"
        and protocol.get("status")
        == "frozen_one_trial_complete_alpha158_session_ordinal_rff_ridge_before_campaign288_feature_or_return_read"
        and protocol_folds(protocol) == list(FOLDS)
        and model.get("trial_id") == TRIAL_ID
        and model.get("configuration_count") == 1
        and parameters.get("random_fourier_dimension") == RFF_DIMENSION
        and math.isclose(parameters.get("rbf_gamma"), RBF_GAMMA)
        and parameters.get("random_state") == RANDOM_STATE
        and math.isclose(parameters.get("ridge_penalty"), RIDGE_PENALTY)
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
        and np.__version__ == "1.26.4"
        and scipy.__version__ == "1.13.1"
        and manifest.get("dataset_sha256") == campaign286.DESIGN_DATASET_SHA256
        and manifest.get("feature_count") == FEATURE_COUNT
        and manifest.get("lockbox_2024_2025_feature_or_return_values_read") is False
    ):
        raise Campaign288Error("Campaign288 frozen protocol context changed")
    return protocol, manifest


def _validate_freeze(path: Path, expected_kind: str, expected_status: str) -> dict[str, Any]:
    if not path.is_file():
        raise Campaign288Error(f"missing Campaign288 freeze: {path}")
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
        raise Campaign288Error("Campaign288 implementation freeze changed")
    return record


def validate_design_freeze() -> dict[str, Any]:
    record = _validate_freeze(
        DESIGN_IMPLEMENTATION_FREEZE_PATH,
        "a_share_three_day_walkforward_campaign288_design_implementation_freeze",
        "frozen_before_campaign288_design_partition_row_or_return_read",
    )
    boundary = record.get("research_boundary") or {}
    if not (
        boundary.get("campaign288_design_partition_row_read_before_freeze") is False
        and boundary.get("campaign288_ordinal_projection_or_center_before_freeze")
        is False
        and boundary.get("training_or_validation_return_read_before_freeze") is False
    ):
        raise Campaign288Error("Campaign288 design freeze boundary changed")
    return record


def validate_development_freeze() -> dict[str, Any]:
    record = _validate_freeze(
        DEVELOPMENT_EXECUTION_FREEZE_PATH,
        "a_share_three_day_walkforward_campaign288_development_execution_freeze",
        "frozen_after_zero_return_design_before_campaign288_training_or_validation_return_read",
    )
    evidence = record.get("design_evidence") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        evidence.get("path") == str(DESIGN_EVIDENCE_PATH.relative_to(REPO_ROOT))
        and evidence.get("sha256") == file_sha256(DESIGN_EVIDENCE_PATH)
        and boundary.get("training_or_validation_return_read_before_freeze") is False
        and boundary.get("model_fit_before_freeze") is False
    ):
        raise Campaign288Error("Campaign288 development freeze changed")
    return record


def local_calendar() -> pd.DatetimeIndex:
    values = [
        line.strip()
        for line in campaign286.SOURCE_CALENDAR_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    calendar = pd.DatetimeIndex(pd.to_datetime(values, errors="raise")).normalize()
    if not calendar.is_monotonic_increasing or calendar.has_duplicates:
        raise Campaign288Error("source calendar identity changed")
    return calendar


def deterministic_sample_positions(
    identities: pd.DataFrame,
    eligible: np.ndarray,
    sample_size: int = SAMPLE_SIZE_PER_SESSION,
) -> tuple[np.ndarray, dict[str, Any]]:
    support = np.asarray(eligible, dtype=bool)
    if len(identities) != len(support) or identities["stock_day_key"].duplicated().any():
        raise Campaign288Error("sampling identity changed")
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
                    f"288|{date_text}|{instrument}".encode("utf-8")
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
        raise Campaign288Error("deterministic training sample gate failed")
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


def session_ordinal_transform_inplace(
    matrix: np.ndarray, dates: Iterable[Any], eligible: np.ndarray
) -> dict[str, Any]:
    values = np.asarray(matrix)
    support = np.asarray(eligible, dtype=bool)
    sessions = pd.DatetimeIndex(dates).normalize().to_numpy(dtype="datetime64[D]")
    if not (
        values.ndim == 2
        and values.shape[1] == FEATURE_COUNT
        and len(values) == len(support) == len(sessions)
        and values.dtype == np.float32
    ):
        raise Campaign288Error("session ordinal input changed")
    unique, starts, counts = np.unique(sessions, return_index=True, return_counts=True)
    if not (
        len(unique) > 0
        and np.array_equal(starts, np.sort(starts))
        and int(counts.sum()) == len(values)
    ):
        raise Campaign288Error("session ordinal date ordering changed")
    finite_totals = np.zeros(FEATURE_COUNT, dtype=np.int64)
    minimum_session_finite = FEATURE_COUNT * [None]
    maximum_session_finite = np.zeros(FEATURE_COUNT, dtype=np.int64)
    for start, count in zip(starts, counts, strict=True):
        positions = np.arange(int(start), int(start + count), dtype=np.int64)
        positions = positions[support[positions]]
        if len(positions) == 0:
            continue
        for column in range(FEATURE_COUNT):
            observed = values[positions, column].astype(np.float64, copy=True)
            finite = np.isfinite(observed)
            finite_count = int(finite.sum())
            values[positions, column] = 0.0
            if finite_count:
                ranks = rankdata(observed[finite], method="average") / finite_count - 0.5
                values[positions[finite], column] = ranks.astype(np.float32)
            finite_totals[column] += finite_count
            maximum_session_finite[column] = max(
                maximum_session_finite[column], finite_count
            )
            prior = minimum_session_finite[column]
            minimum_session_finite[column] = (
                finite_count if prior is None else min(int(prior), finite_count)
            )
    values[~support] = 0.0
    if not (
        np.isfinite(values).all()
        and float(values.min()) >= -0.5
        and float(values.max()) <= 0.5
        and int(finite_totals.min()) >= 512
    ):
        raise Campaign288Error("session ordinal transform gate failed")
    minima = np.asarray(
        [0 if value is None else int(value) for value in minimum_session_finite],
        dtype=np.int64,
    )
    return {
        "session_count": len(unique),
        "feature_count": FEATURE_COUNT,
        "minimum_total_finite_observations_per_feature": int(finite_totals.min()),
        "maximum_total_finite_observations_per_feature": int(finite_totals.max()),
        "minimum_session_finite_observations_across_features": int(minima.min()),
        "maximum_session_finite_observations_across_features": int(
            maximum_session_finite.max()
        ),
        "finite_totals_sha256": hash_array(finite_totals, "<i8"),
        "minimum_session_finite_sha256": hash_array(minima, "<i8"),
        "maximum_session_finite_sha256": hash_array(maximum_session_finite, "<i8"),
        "nonfinite_fill": 0.0,
        "range": [-0.5, 0.5],
    }


def random_fourier_basis() -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    rng = np.random.default_rng(RANDOM_STATE)
    weights = rng.normal(
        0.0,
        math.sqrt(2.0 * RBF_GAMMA),
        size=(FEATURE_COUNT, RFF_DIMENSION),
    ).astype(np.float64)
    phases = rng.uniform(0.0, 2.0 * math.pi, size=RFF_DIMENSION).astype(np.float64)
    return weights, phases, {
        "random_state": RANDOM_STATE,
        "rbf_gamma": RBF_GAMMA,
        "dimension": RFF_DIMENSION,
        "weights_sha256": hash_array(weights, "<f8"),
        "phases_sha256": hash_array(phases, "<f8"),
    }


def random_fourier_features(
    ordinal_matrix: np.ndarray, weights: np.ndarray, phases: np.ndarray
) -> np.ndarray:
    values = np.asarray(ordinal_matrix, dtype=np.float64)
    if not (
        values.ndim == 2
        and values.shape[1] == FEATURE_COUNT
        and weights.shape == (FEATURE_COUNT, RFF_DIMENSION)
        and phases.shape == (RFF_DIMENSION,)
        and np.isfinite(values).all()
    ):
        raise Campaign288Error("random Fourier input changed")
    return math.sqrt(2.0 / RFF_DIMENSION) * np.cos(values @ weights + phases)


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
    ordinal_stats = session_ordinal_transform_inplace(
        matrix, identities["trade_date"], eligible
    )
    weights, phases, basis_stats = random_fourier_basis()
    sampled_ordinal = matrix[positions].astype(np.float64)
    projection = random_fourier_features(sampled_ordinal, weights, phases)
    projection_center = projection.mean(axis=0)
    if not np.isfinite(projection_center).all():
        raise Campaign288Error("random Fourier center changed")
    representation = {
        "sampled_ordinal_matrix_sha256": hash_array(sampled_ordinal, "<f8"),
        "sampled_projection_sha256": hash_array(projection, "<f8"),
        "projection_center_sha256": hash_array(projection_center, "<f8"),
        "projection_center_minimum": float(projection_center.min()),
        "projection_center_maximum": float(projection_center.max()),
        "basis": basis_stats,
    }
    record = {
        "fold": int(fold["fold"]),
        "training": list(fold["train"]),
        "scheduled_signal_count_after_containment_and_purge": len(period),
        "selected_design": design_stats,
        "sample": sample_stats,
        "session_ordinal_transform": ordinal_stats,
        "random_fourier_representation": representation,
        "historical_label_or_forward_return_values_read": False,
    }
    record["fold_design_sha256"] = engine.value_sha256(record)
    return {
        "record": record,
        "sample_keys": identities.iloc[positions]["stock_day_key"].to_numpy(
            dtype=np.int64
        ),
        "projection_center": projection_center,
    }


def plan_design() -> dict[str, Any]:
    validate_design_freeze()
    validate_common()
    ready = not OUTPUT_ROOT.exists() or not list(OUTPUT_ROOT.iterdir())
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign288_design_plan",
        "status": "ready_for_zero_return_design" if ready else "not_ready_preserve_existing_output",
        "ready": ready,
        "fold_count": 3,
        "output_root": str(OUTPUT_ROOT),
        "campaign288_design_partition_rows_read_by_plan": False,
        "historical_return_values_read_by_plan": False,
        "lockbox_2024_2025_return_fields_read_by_plan": False,
        "provider_request_issued": False,
        "candidate49_ledgers_changed": False,
    }


def build_design(confirm: bool) -> dict[str, Any]:
    if not confirm:
        raise Campaign288Error("build-design requires --confirm-build")
    payload = plan_design()
    if payload["ready"] is not True:
        raise Campaign288Error("Campaign288 design plan is not ready")
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
            "kind": "a_share_three_day_walkforward_campaign288_zero_return_design_evidence",
            "status": "passed_ready_for_frozen_development_execution",
            "created_at": campaign286.utc_now(),
            "protocol_sha256": PROTOCOL_SHA256,
            "source_design_manifest_sha256": campaign286.DESIGN_MANIFEST_SHA256,
            "source_design_dataset_sha256": campaign286.DESIGN_DATASET_SHA256,
            "source_feature_library_sha256": campaign286.design.FEATURE_LIBRARY_SHA256,
            "feature_count": FEATURE_COUNT,
            "folds": records,
            "all_fold_design_gates_passed": True,
            "campaign288_design_partition_rows_read": True,
            "campaign288_ordinal_projection_and_center_computed": True,
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
                    "kind": "a_share_three_day_walkforward_campaign288_design_failure",
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
class RandomFourierRidgeRegressor:
    """One deterministic weighted ridge output over a fixed RFF representation."""

    parameters: dict[str, Any]
    projection_center: np.ndarray
    coefficients_: np.ndarray | None = None
    target_center_: float | None = None
    fit_statistics_: dict[str, Any] | None = None

    def fit(
        self, ordinal_matrix: np.ndarray, target: np.ndarray, sample_weight: np.ndarray
    ) -> "RandomFourierRidgeRegressor":
        x = np.asarray(ordinal_matrix, dtype=np.float64)
        y = np.asarray(target, dtype=np.float64).reshape(-1)
        weight = np.asarray(sample_weight, dtype=np.float64).reshape(-1)
        center = np.asarray(self.projection_center, dtype=np.float64).reshape(-1)
        if not (
            x.ndim == 2
            and x.shape[1] == FEATURE_COUNT
            and len(x) == len(y) == len(weight) > 0
            and center.shape == (RFF_DIMENSION,)
            and np.isfinite(x).all()
            and np.isfinite(y).all()
            and np.isfinite(weight).all()
            and (weight > 0).all()
        ):
            raise Campaign288Error("random Fourier ridge fit inputs changed")
        weight = weight / weight.sum()
        basis_weights, phases, _ = random_fourier_basis()
        projection = random_fourier_features(x, basis_weights, phases) - center
        target_center = float(np.sum(weight * y))
        centered_target = y - target_center
        normal = projection.T @ (weight[:, None] * projection)
        penalty = float(self.parameters["ridge_penalty"])
        system = normal + penalty * np.eye(RFF_DIMENSION, dtype=np.float64)
        right = projection.T @ (weight * centered_target)
        coefficients = np.linalg.solve(system, right)
        prediction = projection @ coefficients
        residual_mse = float(np.sum(weight * np.square(prediction - centered_target)))
        objective = residual_mse + penalty * float(np.square(coefficients).sum())
        condition = float(np.linalg.cond(system))
        if not (
            np.isfinite(coefficients).all()
            and math.isfinite(target_center)
            and math.isfinite(residual_mse)
            and math.isfinite(objective)
            and math.isfinite(condition)
            and condition < 1e12
        ):
            raise Campaign288Error("random Fourier ridge solution changed")
        self.coefficients_ = coefficients
        self.target_center_ = target_center
        self.fit_statistics_ = {
            "target_center": target_center,
            "weighted_residual_mse": residual_mse,
            "penalized_objective": objective,
            "normal_equation_condition_number": condition,
            "coefficient_l2_norm": float(np.linalg.norm(coefficients)),
            "coefficient_sha256": hash_array(coefficients, "<f8"),
        }
        return self

    def predict(self, ordinal_matrix: np.ndarray) -> np.ndarray:
        if self.coefficients_ is None or self.target_center_ is None:
            raise Campaign288Error("random Fourier ridge is not fitted")
        weights, phases, _ = random_fourier_basis()
        projection = random_fourier_features(ordinal_matrix, weights, phases)
        return (
            (projection - self.projection_center) @ self.coefficients_
            + self.target_center_
        )

    def save(self, path: Path) -> None:
        if (
            self.coefficients_ is None
            or self.target_center_ is None
            or self.fit_statistics_ is None
        ):
            raise Campaign288Error("random Fourier ridge is not fitted")
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                np.savez_compressed(
                    handle,
                    coefficients=self.coefficients_,
                    projection_center=self.projection_center,
                    target_center=np.asarray([self.target_center_], dtype=np.float64),
                    parameters_json=np.asarray(
                        json.dumps(self.parameters, sort_keys=True, separators=(",", ":"))
                    ),
                    fit_statistics_json=np.asarray(
                        json.dumps(self.fit_statistics_, sort_keys=True, separators=(",", ":"))
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
    valid = sample & np.isfinite(y)
    unique, inverse, counts = np.unique(
        sessions[valid], return_inverse=True, return_counts=True
    )
    if (
        len(unique) < MINIMUM_RETAINED_TRAINING_SESSIONS
        or int(counts.min()) < MINIMUM_FINITE_TARGETS_PER_SESSION
    ):
        raise Campaign288Error("finite sampled training target gate failed")
    weights = np.zeros(len(y), dtype=np.float64)
    weights[valid] = 1.0 / (len(unique) * counts[inverse])
    daily = np.bincount(inverse, weights=weights[valid], minlength=len(unique))
    if not (
        math.isclose(float(weights.sum()), 1.0, rel_tol=0.0, abs_tol=1e-12)
        and np.allclose(daily, np.full(len(unique), 1.0 / len(unique)), atol=1e-12)
    ):
        raise Campaign288Error("sampled target session weights changed")
    return valid, weights, {
        "training_observations": int(valid.sum()),
        "training_sessions": len(unique),
        "minimum_finite_sampled_targets_per_session": int(counts.min()),
        "maximum_finite_sampled_targets_per_session": int(counts.max()),
        "session_equal_row_weight_sum": float(weights.sum()),
        "weights_sha256": hash_array(weights[valid], "<f8"),
    }


def model_scores(
    model: RandomFourierRidgeRegressor,
    ordinal_matrix: np.ndarray,
    eligible: np.ndarray,
    batch_size: int = 65_536,
) -> np.ndarray:
    support = np.asarray(eligible, dtype=bool)
    result = np.full(len(ordinal_matrix), np.nan, dtype=np.float64)
    positions = np.flatnonzero(support)
    for start in range(0, len(positions), batch_size):
        index = positions[start : start + batch_size]
        result[index] = model.predict(ordinal_matrix[index])
    if not np.isfinite(result[support]).all():
        raise Campaign288Error("eligible random Fourier ridge score is nonfinite")
    return result


def compare_fold_design(bundle: dict[str, Any], evidence: dict[str, Any]) -> None:
    matches = [
        record
        for record in evidence.get("folds") or []
        if int(record.get("fold", -1)) == int(bundle["record"]["fold"])
    ]
    if len(matches) != 1 or matches[0] != bundle["record"]:
        raise Campaign288Error("Campaign288 fold design evidence changed")


def fit_training_fold(
    fold: dict[str, Any],
    manifest: dict[str, Any],
    evidence: dict[str, Any],
    batch_size: int,
) -> tuple[dict[str, Any], RandomFourierRidgeRegressor, dict[str, Any]]:
    bundle = fold_design_bundle(fold, manifest)
    compare_fold_design(bundle, evidence)
    context = campaign286.model_context()
    panel, quotes, calendar, schedule, matrix, eligible, selected_design = (
        campaign286.build_training_panel(context, manifest, fold["train"][1], batch_size)
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
    ordinal_stats = session_ordinal_transform_inplace(
        matrix, panel["signal_date"], eligible
    )
    basis_weights, phases, _ = random_fourier_basis()
    observed_center = random_fourier_features(
        matrix[sampled], basis_weights, phases
    ).mean(axis=0)
    if hash_array(observed_center, "<f8") != hash_array(
        bundle["projection_center"], "<f8"
    ):
        raise Campaign288Error("training projection center differs from zero-return design")
    model = RandomFourierRidgeRegressor(
        dict(MODEL_PARAMETERS), bundle["projection_center"]
    ).fit(matrix[valid], target[valid], weights[valid])
    model_path = OUTPUT_ROOT / f"fold_{fold['fold']}_model" / f"{TRIAL_ID}.npz"
    model.save(model_path)
    score = model_scores(model, matrix, eligible)
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
        "session_ordinal_transform": ordinal_stats,
        "random_fourier_representation": bundle["record"][
            "random_fourier_representation"
        ],
        "fit_statistics": model.fit_statistics_,
        "model_artifact": {
            "path": str(model_path),
            "sha256": file_sha256(model_path),
            "bytes": model_path.stat().st_size,
        },
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
    }
    return fit, model, training_metrics


def validation_prefit(
    fold: dict[str, Any],
    manifest: dict[str, Any],
    evidence: dict[str, Any],
    model: RandomFourierRidgeRegressor,
    fit: dict[str, Any],
) -> tuple[dict[str, np.ndarray], pd.DataFrame, dict[str, Any]]:
    bundle = fold_design_bundle(fold, manifest)
    compare_fold_design(bundle, evidence)
    year = pd.Timestamp(fold["validation"][0]).year
    identities, matrix, eligible, design_stats = campaign286.load_design_years(
        [year], manifest
    )
    ordinal_stats = session_ordinal_transform_inplace(
        matrix, identities["trade_date"], eligible
    )
    score = model_scores(model, matrix, eligible)
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
        mask = (dates == pd.Timestamp(session)) & eligible & np.isfinite(score)
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
        "kind": "a_share_three_day_walkforward_campaign288_fold_prefit_scores",
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
        "validation_session_ordinal_transform": ordinal_stats,
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
            "alpha158_feature_values_previously_read_by_prior_campaigns": True,
            "campaign288_training_or_validation_return_fields_read": False,
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
        "kind": "a_share_three_day_walkforward_campaign288_trial_ledger",
        "append_only": True,
        "campaign": {
            "protocol_sha256": PROTOCOL_SHA256,
            "design_dataset_sha256": campaign286.DESIGN_DATASET_SHA256,
            "design_evidence_sha256": file_sha256(DESIGN_EVIDENCE_PATH),
        },
        "chain_genesis": CHAIN_GENESIS,
        "entries": entries,
        "entry_count": len(entries),
        "prevalue_concept_attempt_count": 8,
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
        path.name for path in OUTPUT_ROOT.iterdir() if path.name != "design_evidence.json"
    ]
    ready = bool(
        not existing
        and evidence.get("status") == "passed_ready_for_frozen_development_execution"
        and len(evidence.get("folds") or []) == 3
    )
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign288_development_plan",
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
        raise Campaign288Error("run-development requires --confirm-run")
    payload = plan_development()
    if payload["ready"] is not True:
        raise Campaign288Error("Campaign288 development plan is not ready")
    _, manifest = validate_common()
    evidence = load_json(DESIGN_EVIDENCE_PATH)
    intent = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign288_development_intent",
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
        "campaign_id": "campaign_288",
        "created_at": intent["opened_at"],
        "phase": "development_walkforward",
        "economic_hypothesis": "Local nonlinear similarity among scale-free cross-sectional Alpha158 states may preserve three-session ranking structure while reducing raw-scale and outlier sensitivity relative to the terminal tree and MLP estimators.",
        "formula": "one fixed RBF random Fourier ridge score over all 158 within-session ordinal Alpha158 coordinates",
        "direction": "higher predicted within-session gross-return percentile",
        "feature_set": "complete Alpha158 in frozen order",
        "window_transform_threshold_filter_and_weight_configuration": {
            "sample_size_per_session": SAMPLE_SIZE_PER_SESSION,
            "session_ordinal_transform": "average-tie percentile minus 0.5; missing zero",
            "model_parameters": MODEL_PARAMETERS,
        },
        "training_and_validation_folds": [
            {
                "fold": f["fold"],
                "train": list(f["train"]),
                "validation": list(f["validation"]),
            }
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
            print(f"fold {fold['fold']}: fitting frozen ordinal RFF ridge", flush=True)
            fit, model, training_metrics = fit_training_fold(
                fold, manifest, evidence, batch_size
            )
            print(f"fold {fold['fold']}: freezing validation scores before returns", flush=True)
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
                    "rejection_reasons": [f"fold_{fold['fold']}_prefit_score_gate_failed"],
                }
                break
            print(f"fold {fold['fold']}: reading contained validation returns", flush=True)
            validation = campaign286.evaluate_validation(
                campaign286.model_context(), fold, scores, identities, batch_size
            )[TRIAL_ID]
            metrics_payload = {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign288_fold_validation_metrics",
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
            "kind": "a_share_three_day_walkforward_campaign288_development_survivors",
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
            "kind": "a_share_three_day_walkforward_campaign288_development_report",
            "status": "development_complete_survivors_frozen",
            "created_at": campaign286.utc_now(),
            "protocol_sha256": PROTOCOL_SHA256,
            "design_evidence_sha256": file_sha256(DESIGN_EVIDENCE_PATH),
            "trial_count": 1,
            "ledger_entry_count": ledger["entry_count"],
            "validation_return_reading_trial_count": 1 if trial["validation_metrics"] else 0,
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
                "kind": "a_share_three_day_walkforward_campaign288_development_failure",
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
        raise Campaign288Error(f"unsupported command: {args.command}")
    print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
