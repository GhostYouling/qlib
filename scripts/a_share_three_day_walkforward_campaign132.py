#!/usr/bin/env python3
"""Run Campaign132's frozen three-model chronological development campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pickle
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import sklearn
from scipy.stats import rankdata
from sklearn.ensemble import HistGradientBoostingRegressor

from scripts import a_share_three_day_walkforward_campaign102 as legacy
from scripts import a_share_three_day_walkforward_campaign132_design as design

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = design.DEFAULT_PROTOCOL
DEFAULT_DESIGN_MANIFEST = (
    design.output_root(design.DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
)
DEFAULT_DESIGN_AUDIT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_132/no_return/"
    "design_structural_audit.json"
)
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_132/walkforward"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_132_development_implementation_freeze_20260814.json"
)
CONCEPT_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_132_concept_scouting_20260814.json"
)
TEMPLATE_PATH = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_004_preregistration.json"
)
ENGINE_PATH = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign.py"
LEGACY_HELPER_PATH = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign102.py"
DESIGN_PATH = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign132_design.py"
INTERPRETATION_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_102_sequential_execution_interpretation_freeze_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign132.py"
)

PROTOCOL_SHA256 = "b4c3f6b3a69506c8a8f5ee71ffe05e487af0f71ae2b104adb3a79b2efc4ac0be"
DESIGN_MANIFEST_SHA256 = (
    "043c17fea89f3b0956d643a7c6e3f4d73a11403b967213d2d57539a6a8316a49"
)
DESIGN_DATASET_SHA256 = (
    "12ce3a64b5e13581392ded9890e2064db4ccca3945da3eb8ad7752c95366a9fc"
)
DESIGN_AUDIT_SHA256 = "86bb53552caf6f6d8f1fad688d2f3a7e39c75827f968bb1ee1510fff2394deec"
CONCEPT_SHA256 = "ad0aa0b674fff6307c8c4f47310becaf1f05e6d4311126c0c004e9c52043a058"
TEMPLATE_SHA256 = "e67811f265b2b744073391fa65698951b132065109f95fa47991b8254a5756e6"
ENGINE_SHA256 = "301f5fe665422b94c9fa110e67995ff0999584a5f323ecdd5f56151a3529f5a7"
LEGACY_HELPER_SHA256 = (
    "ba298ed23d0675f6fea5de85bbf085dcb7b88ef72e730031b90e1e6b350ca6db"
)
DESIGN_RUNNER_SHA256 = (
    "efbb0db0afa6519a6ba9a149ec913c0522c7500f781320b1a5f2a7aa685453de"
)
INTERPRETATION_SHA256 = (
    "07dce156a77e65167f55a04105db9d5d0a167e61db5028bca833f1d8fbfa6bd2"
)

TRIALS = (
    ("wf132_monotone_hgb_no_interactions_140f", "no_interactions"),
    ("wf132_monotone_hgb_pairwise_interactions_140f", "pairwise"),
    ("wf132_monotone_hgb_unrestricted_interactions_140f", None),
)
TRIAL_ORDER = {trial_id: index for index, (trial_id, _) in enumerate(TRIALS)}
MODEL_PARAMETERS = {
    "loss": "squared_error",
    "learning_rate": 0.05,
    "max_iter": 120,
    "max_leaf_nodes": 7,
    "max_depth": None,
    "min_samples_leaf": 500,
    "l2_regularization": 1.0,
    "max_features": 1.0,
    "max_bins": 63,
    "categorical_features": None,
    "early_stopping": False,
    "random_state": 132,
    "warm_start": False,
}
MIN_SIGNAL_NAMES = 50
PURGE_SIGNAL_SESSIONS = 3
NEUTRAL_FILL = 0.5
CHAIN_GENESIS = "0" * 64
INFRASTRUCTURE_FAILURES = (
    (
        "docs/a_share_three_day_walkforward_campaign_132_relative_manifest_partition_path_failure_20260814.json",
        "835c841d7f8abb8ad2a7c627323c049e1d1e3970e40ee0776bff5dbc9eb649ae",
    ),
    (
        "docs/a_share_three_day_walkforward_campaign_132_nonexistent_ordered_uniqueness_path_search_failure_20260814.json",
        "9a7b247141adebec6f03163e7072b76f4baf3257bfc9bf46972ca9209c2dc963",
    ),
    (
        "docs/a_share_three_day_walkforward_campaign_132_runtime_probe_session_id_visibility_failure_20260814.json",
        "d7992ad256a4cd1f7e7dd796137caefef8f071f0b889e9a537984a23c1ca94a0",
    ),
    (
        "docs/a_share_three_day_walkforward_campaign_132_nonexistent_campaign044_key_search_failure_20260814.json",
        "bd30aa047d1831058527f94d02fcac2b5b11c391593afdc614a28715422b4189",
    ),
    (
        "docs/a_share_three_day_walkforward_campaign_132_pytest_repository_import_path_failure_20260814.json",
        "0c2b07987992e053a0b9368ff7c31bef64567f75ecb8c695179a1076b1525454",
    ),
    (
        "docs/a_share_three_day_walkforward_campaign_132_verify_manifest_argument_failure_20260814.json",
        "288664f32f27f73e614745bd3d9fc9e13b902e5a9de87756641c36d96f38ec2e",
    ),
    (
        "docs/a_share_three_day_walkforward_campaign_132_initial_model_runner_synthetic_test_failure_20260814.json",
        "694dcea757b2b6f9f162b947de56412662b8a1f1cdf6ce880883f8d869fac8c2",
    ),
    (
        "docs/a_share_three_day_walkforward_campaign_132_second_model_runner_float_assertion_failure_20260814.json",
        "1d724d1ea1d77bdcf565e802e3d0238bf7d12abc015c8e0c5209f46ed0f07830",
    ),
)


class Campaign132Error(RuntimeError):
    """Fail closed when a Campaign132 invariant or chronological gate changes."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_file(path: Path, expected: str, label: str) -> None:
    if len(expected) != 64 or not path.is_file() or file_sha256(path) != expected:
        raise Campaign132Error(f"{label} changed: {path}")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Campaign132Error(f"JSON object required: {path}")
    return value


def value_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=legacy.engine.research._json_default,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def atomic_binary(path: Path, payload: bytes) -> None:
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


def _implementation_freeze() -> dict[str, Any]:
    record = load_json(DEFAULT_IMPLEMENTATION_FREEZE)
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign132_development_implementation_freeze"
        and record.get("status")
        == "frozen_before_first_campaign132_training_return_read"
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (record.get("design_manifest") or {}).get("sha256")
        == DESIGN_MANIFEST_SHA256
        and (record.get("design_audit") or {}).get("sha256") == DESIGN_AUDIT_SHA256
        and (record.get("runner") or {}).get("sha256")
        == file_sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == file_sha256(TEST_PATH)
        and record.get("model_fit_before_freeze") is False
        and record.get("training_or_validation_return_read_before_freeze") is False
        and record.get("lockbox_2024_2025_return_read_before_freeze") is False
        and record.get("candidate49_ledgers_changed_before_freeze") is False
    ):
        raise Campaign132Error("Campaign132 development implementation freeze changed")
    return record


def load_frozen_context() -> tuple[dict[str, Any], dict[str, Any]]:
    bindings = (
        (Path(DEFAULT_PROTOCOL), PROTOCOL_SHA256, "Campaign132 protocol"),
        (DEFAULT_DESIGN_MANIFEST, DESIGN_MANIFEST_SHA256, "Campaign132 design"),
        (DEFAULT_DESIGN_AUDIT, DESIGN_AUDIT_SHA256, "Campaign132 design audit"),
        (CONCEPT_PATH, CONCEPT_SHA256, "Campaign132 concept catalog"),
        (TEMPLATE_PATH, TEMPLATE_SHA256, "execution template"),
        (ENGINE_PATH, ENGINE_SHA256, "execution engine"),
        (LEGACY_HELPER_PATH, LEGACY_HELPER_SHA256, "bound evaluation helper"),
        (DESIGN_PATH, DESIGN_RUNNER_SHA256, "Campaign132 design runner"),
        (INTERPRETATION_PATH, INTERPRETATION_SHA256, "execution interpretation"),
    )
    for path, expected, label in bindings:
        require_file(path, expected, label)
    for relative, expected in INFRASTRUCTURE_FAILURES:
        require_file(
            REPO_ROOT / relative, expected, "Campaign132 infrastructure failure"
        )
    protocol = load_json(Path(DEFAULT_PROTOCOL))
    audit = load_json(DEFAULT_DESIGN_AUDIT)
    template = load_json(TEMPLATE_PATH)
    observed_trials = [
        (item.get("trial_id"), item.get("interaction_cst"))
        for item in protocol.get("trial_catalog") or []
    ]
    shared = protocol.get("shared_model_configuration") or {}
    if not (
        observed_trials == list(TRIALS)
        and shared.get("runtime") == "scikit-learn==1.5.1"
        and sklearn.__version__ == "1.5.1"
        and shared.get("class") == "sklearn.ensemble.HistGradientBoostingRegressor"
        and shared.get("monotonic_cst") == "array_of_140_positive_ones"
        and all(shared.get(name) == value for name, value in MODEL_PARAMETERS.items())
        and (protocol.get("complete_feature_library") or {}).get(
            "numeric_feature_order_sha256"
        )
        == design.FEATURE_ORDER_SHA256
        and (protocol.get("training_target_and_weights") or {}).get(
            "feature_missing_fill"
        )
        == NEUTRAL_FILL
        and audit.get("status") == "passed_ready_for_frozen_model_implementation"
        and (audit.get("coverage") or {}).get("gate_passed_before_model_fit_or_returns")
        is True
        and (audit.get("snapshot") or {}).get("dataset_sha256") == DESIGN_DATASET_SHA256
        and audit.get("historical_forward_return_fields_read") is False
        and audit.get("model_fitting_performed") is False
    ):
        raise Campaign132Error("Campaign132 frozen context semantics changed")
    for group_name in ("daily_data_bindings", "execution_policy_bindings"):
        for name, binding in (template.get(group_name) or {}).items():
            if binding.get("kind") == "directory":
                path = legacy.engine.resolve_bound_path(str(binding["path"]))
                if not path.is_dir():
                    raise Campaign132Error(f"{group_name}.{name} directory is missing")
            else:
                legacy.engine.validate_file_binding(binding, f"{group_name}.{name}")
    return protocol, template


def design_record(year: int) -> tuple[Path, dict[str, Any]]:
    manifest = load_json(DEFAULT_DESIGN_MANIFEST)
    records = [item for item in manifest["files"] if int(item["year"]) == int(year)]
    if len(records) != 1:
        raise Campaign132Error(f"Campaign132 design year changed: {year}")
    record = records[0]
    path = (DEFAULT_DESIGN_MANIFEST.parent / str(record["path"])).resolve()
    require_file(path, str(record["sha256"]), f"Campaign132 design partition {year}")
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
    identity_parts: list[pd.DataFrame] = []
    matrix_parts: list[np.ndarray] = []
    count_parts: list[np.ndarray] = []
    eligible_parts: list[np.ndarray] = []
    for year in sorted({int(value) for value in years}):
        path, _ = design_record(year)
        frame = pd.read_parquet(
            path,
            columns=[
                "stock_day_key",
                *names,
                design.FINITE_COUNT_NAME,
                design.ELIGIBLE_NAME,
            ],
        )
        keys = frame.pop("stock_day_key").to_numpy(dtype=np.int64)
        dates, instruments = legacy.decode_keys(keys)
        mask = np.ones(len(keys), dtype=bool)
        if allowed_days is not None:
            mask = np.isin(dates.to_numpy(dtype="datetime64[D]"), allowed_days)
        identity_parts.append(
            pd.DataFrame(
                {
                    "trade_date": dates[mask],
                    "instrument": instruments[mask],
                    "stock_day_key": keys[mask],
                }
            )
        )
        count_parts.append(
            frame.pop(design.FINITE_COUNT_NAME).to_numpy(dtype=np.uint8)[mask]
        )
        eligible_parts.append(
            frame.pop(design.ELIGIBLE_NAME).to_numpy(dtype=bool)[mask]
        )
        matrix_parts.append(frame[names].to_numpy(dtype=np.float32, copy=True)[mask])
    identities = pd.concat(identity_parts, ignore_index=True)
    matrix = np.concatenate(matrix_parts, axis=0)
    finite_count = np.concatenate(count_parts)
    eligible = np.concatenate(eligible_parts)
    if identities.duplicated(["trade_date", "instrument"]).any():
        raise Campaign132Error("Campaign132 decoded design identities are not unique")
    observed_count, observed_eligible = design.support_state(matrix)
    if not (
        np.array_equal(finite_count, observed_count)
        and np.array_equal(eligible, observed_eligible)
    ):
        raise Campaign132Error("Campaign132 design support semantics changed")
    return identities, matrix, finite_count, eligible


def build_model(interaction_cst: str | None) -> HistGradientBoostingRegressor:
    if interaction_cst not in ("no_interactions", "pairwise", None):
        raise Campaign132Error("unfrozen interaction constraint")
    return HistGradientBoostingRegressor(
        **MODEL_PARAMETERS,
        monotonic_cst=np.ones(design.FEATURE_COUNT, dtype=np.int8),
        interaction_cst=interaction_cst,
    )


def training_weights(
    signal_dates: Iterable[Any], target: np.ndarray, eligible: np.ndarray
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    dates = pd.DatetimeIndex(signal_dates).normalize().to_numpy(dtype="datetime64[D]")
    y = np.asarray(target, dtype=np.float64)
    support = np.asarray(eligible, dtype=bool)
    valid = np.isfinite(y) & support
    unique, inverse, counts = np.unique(
        dates[valid], return_inverse=True, return_counts=True
    )
    if len(unique) == 0 or int(counts.min()) < MIN_SIGNAL_NAMES:
        raise Campaign132Error("training target has insufficient contained sessions")
    weights = np.zeros(len(y), dtype=np.float64)
    weights[valid] = 1.0 / (len(unique) * counts[inverse])
    daily_sums = np.bincount(inverse, weights=weights[valid], minlength=len(unique))
    if not (
        math.isclose(float(weights.sum()), 1.0, rel_tol=0.0, abs_tol=1e-12)
        and np.allclose(daily_sums, np.full(len(unique), 1.0 / len(unique)), atol=1e-12)
    ):
        raise Campaign132Error("training session-equal weights changed")
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
                np.asarray(weights[valid], dtype="<f8").tobytes()
            ).hexdigest(),
        },
    )


def model_scores(
    model: HistGradientBoostingRegressor, matrix: np.ndarray, eligible: np.ndarray
) -> np.ndarray:
    x = np.asarray(matrix, dtype=np.float64)
    support = np.asarray(eligible, dtype=bool)
    if x.ndim != 2 or x.shape[1] != design.FEATURE_COUNT or len(support) != len(x):
        raise Campaign132Error("model score inputs changed")
    filled = np.where(np.isfinite(x), x, NEUTRAL_FILL)
    scores = np.asarray(model.predict(filled), dtype=np.float64)
    scores[~support] = np.nan
    if not np.isfinite(scores[support]).all():
        raise Campaign132Error("eligible model scores are nonfinite")
    return scores


def uniqueness_audit(
    keys: np.ndarray,
    matrix: np.ndarray,
    scores: np.ndarray,
    component_names: Iterable[str],
    *,
    minimum_names: int = 50,
    minimum_sessions: int = 100,
    strict_maximum_absolute_median: float = 0.8,
) -> dict[str, Any]:
    keys = np.asarray(keys, dtype=np.int64)
    x = np.asarray(matrix, dtype=np.float64)
    candidate = np.asarray(scores, dtype=np.float64)
    names = list(component_names)
    sessions = keys // 4_000_000
    if x.shape != (len(keys), len(names)) or len(candidate) != len(keys):
        raise Campaign132Error("uniqueness inputs changed")
    if len(sessions) > 1 and np.any(sessions[1:] < sessions[:-1]):
        raise Campaign132Error("uniqueness stock-day keys are not session sorted")
    boundaries = np.flatnonzero(np.r_[True, sessions[1:] != sessions[:-1], True])
    session_slices = [
        slice(int(boundaries[index]), int(boundaries[index + 1]))
        for index in range(len(boundaries) - 1)
    ]
    comparisons: list[dict[str, Any]] = []
    for index, name in enumerate(names):
        daily: list[float] = []
        comparator = x[:, index]
        for positions in session_slices:
            valid = np.isfinite(candidate[positions]) & np.isfinite(
                comparator[positions]
            )
            if int(valid.sum()) < minimum_names:
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
            len(daily) >= minimum_sessions
            and median is not None
            and abs(median) < strict_maximum_absolute_median
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
    return {
        "comparison_count": len(comparisons),
        "comparison_order_sha256": design.FEATURE_ORDER_SHA256,
        "minimum_pairwise_names_per_session": minimum_names,
        "minimum_pairwise_sessions_per_comparison": minimum_sessions,
        "strict_maximum_absolute_median_daily_rank_correlation": (
            strict_maximum_absolute_median
        ),
        "all_required_comparisons_passed": bool(
            len(comparisons) == len(names)
            and all(item["gate_passed"] for item in comparisons)
        ),
        "maximum_observed_absolute_median_daily_rank_correlation": (
            max(observed) if observed else None
        ),
        "comparisons": comparisons,
    }


def build_training_panel(
    template: dict[str, Any], training_end: str, batch_size: int
) -> tuple[pd.DataFrame, Any, pd.DatetimeIndex, pd.DataFrame, np.ndarray, np.ndarray]:
    market, calendar = legacy.engine.load_market_context(
        template, training_end, "2019-01-01", batch_size
    )
    schedule = legacy.engine.global_signal_schedule(calendar)
    period_schedule = legacy.engine.purged_period_schedule(
        schedule, "2019-01-01", training_end, PURGE_SIGNAL_SESSIONS
    )
    signal_dates = pd.DatetimeIndex(period_schedule["signal_date"])
    identities, matrix, _, eligible = load_design_years(
        range(2019, pd.Timestamp(training_end).year + 1), allowed_dates=signal_dates
    )
    columns = [f"component_{index:03d}" for index in range(design.FEATURE_COUNT)]
    factor_frame = pd.concat(
        [
            identities[["trade_date", "instrument"]].reset_index(drop=True),
            pd.DataFrame(matrix, columns=columns),
        ],
        axis=1,
    )
    factor_frame[design.ELIGIBLE_NAME] = eligible
    panel = legacy.engine.build_signal_panel(market, factor_frame, schedule)
    panel_matrix = panel[columns].to_numpy(dtype=np.float64, copy=True)
    panel_eligible = panel[design.ELIGIBLE_NAME].fillna(False).to_numpy(dtype=bool)
    return (
        panel,
        legacy.engine.quote_lookup(market),
        calendar,
        schedule,
        panel_matrix,
        panel_eligible,
    )


def fit_fold(
    template: dict[str, Any],
    fold: dict[str, Any],
    live: dict[str, str | None],
    batch_size: int,
    output_root: Path,
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, HistGradientBoostingRegressor],
    dict[str, dict[str, Any]],
]:
    training_start, training_end = fold["training"]
    panel, quotes, calendar, schedule, panel_matrix, panel_eligible = (
        build_training_panel(template, training_end, batch_size)
    )
    training_returns = pd.to_numeric(
        panel["forward_gross_return"], errors="coerce"
    ).copy()
    training_returns.loc[~panel_eligible] = np.nan
    target = legacy.target_percentiles(panel["signal_date"], training_returns)
    valid, weights, statistics_payload = training_weights(
        panel["signal_date"], target, panel_eligible
    )
    filled = np.where(np.isfinite(panel_matrix), panel_matrix, NEUTRAL_FILL)
    fits: dict[str, dict[str, Any]] = {}
    models: dict[str, HistGradientBoostingRegressor] = {}
    training_metrics: dict[str, dict[str, Any]] = {}
    for trial_id, interaction_cst in live.items():
        model = build_model(interaction_cst)
        model.fit(
            filled[valid],
            np.asarray(target, dtype=np.float64)[valid],
            sample_weight=weights[valid],
        )
        binary = pickle.dumps(model, protocol=5)
        model_path = output_root / f"fold_{fold['fold']}_models" / f"{trial_id}.pickle"
        atomic_binary(model_path, binary)
        score = model_scores(model, panel_matrix, panel_eligible)
        panel[legacy._score_column(trial_id)] = score
        trial = {"feature_set": [trial_id], "weights": [1.0]}
        training_metrics[trial_id] = legacy.engine.evaluate_trial_period(
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
        fits[trial_id] = {
            "interaction_cst": interaction_cst,
            "shared_parameters": MODEL_PARAMETERS,
            "monotonic_cst": "positive_one_for_all_140_features",
            "training": statistics_payload,
            "n_iter": int(model.n_iter_),
            "model_binary": {
                "path": str(model_path),
                "sha256": file_sha256(model_path),
                "bytes": model_path.stat().st_size,
                "pickle_protocol": 5,
            },
            "sklearn_version": sklearn.__version__,
        }
        models[trial_id] = model
    return fits, models, training_metrics


def validation_prefit_audit(
    fold: dict[str, Any],
    fits: dict[str, dict[str, Any]],
    models: dict[str, HistGradientBoostingRegressor],
    output_root: Path,
) -> tuple[dict[str, Any], dict[str, np.ndarray], pd.DataFrame]:
    validation_start, validation_end = fold["validation"]
    identities, matrix, _, eligible = load_design_years(
        [pd.Timestamp(validation_start).year]
    )
    trial_scores: dict[str, np.ndarray] = {}
    audits: dict[str, Any] = {}
    for trial_id, model in models.items():
        scores = model_scores(model, matrix, eligible)
        trial_scores[trial_id] = scores
        audits[trial_id] = uniqueness_audit(
            identities["stock_day_key"].to_numpy(dtype=np.int64),
            matrix,
            scores,
            design.component_columns(),
        )
    score_binding = legacy.write_score_snapshot(
        output_root / f"fold_{fold['fold']}_validation_scores.parquet",
        identities,
        trial_scores,
    )
    payload = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign132_fold_prefit_uniqueness",
        "status": "frozen_before_fold_validation_return_read",
        "created_at": utc_now(),
        "fold": int(fold["fold"]),
        "training": list(fold["training"]),
        "validation": [validation_start, validation_end],
        "fits": fits,
        "validation_score_snapshot": score_binding,
        "uniqueness": audits,
        "all_live_trials_audited_before_validation_returns": True,
        "validation_daily_price_fields_read_before_record": [],
        "validation_forward_return_fields_read_before_record": False,
        "lockbox_2024_2025_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
    }
    path = output_root / f"fold_{fold['fold']}_prefit_uniqueness.json"
    legacy.atomic_json(path, payload)
    payload["record_binding"] = {"path": str(path), "sha256": file_sha256(path)}
    return payload, trial_scores, identities


def concept_and_failure_entries() -> list[dict[str, Any]]:
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
                "component_values_read": False,
                "historical_forward_return_fields_read": False,
            }
        )
    for relative, expected in INFRASTRUCTURE_FAILURES:
        path = REPO_ROOT / relative
        record = load_json(path)
        entries.append(
            {
                "attempt_id": record.get("attempt_id"),
                "phase": "infrastructure_failure",
                "stage": record.get("stage"),
                "outcome": record.get("status"),
                "evidence": {"path": relative, "sha256": expected},
                "scientific_result_changed": False,
                "historical_forward_return_fields_read": False,
            }
        )
    return entries


def build_ledger(trial_records: list[dict[str, Any]]) -> dict[str, Any]:
    previous = CHAIN_GENESIS
    entries: list[dict[str, Any]] = []
    for record in [*concept_and_failure_entries(), *trial_records]:
        entry = {**record, "previous_entry_sha256": previous}
        entry["entry_sha256"] = value_sha256(entry)
        previous = entry["entry_sha256"]
        entries.append(entry)
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign132_trial_ledger",
        "append_only": True,
        "campaign": {"protocol_sha256": PROTOCOL_SHA256},
        "chain_genesis": CHAIN_GENESIS,
        "entries": entries,
        "entry_count": len(entries),
        "prevalue_concept_attempt_count": 6,
        "infrastructure_failure_attempt_count": len(INFRASTRUCTURE_FAILURES),
        "model_trial_attempt_count": len(trial_records),
        "chain_tip_sha256": previous,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
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


def run_development(args: argparse.Namespace) -> dict[str, Any]:
    if not args.confirm_run:
        raise Campaign132Error("run-development requires --confirm-run")
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
    if list(output_root.iterdir()):
        raise Campaign132Error(
            "incomplete Campaign132 development output exists; preserve it and use an explicit recovery revision"
        )
    intent = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign132_development_intent",
        "status": "training_return_open_pending_chronological_completion",
        "opened_at": utc_now(),
        "protocol_sha256": PROTOCOL_SHA256,
        "design_manifest_sha256": DESIGN_MANIFEST_SHA256,
        "design_audit_sha256": DESIGN_AUDIT_SHA256,
        "runner_sha256": file_sha256(Path(__file__).resolve()),
        "validation_returns_may_be_read_only_after_each_fold_prefit_uniqueness_record": True,
        "lockbox_2024_2025_remains_closed": True,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
    }
    legacy.atomic_json(output_root / "development_intent.json", intent)
    folds = [
        {
            "fold": int(item["fold"]),
            "training": list(item["training"]),
            "validation": list(item["validation"]),
        }
        for item in protocol["walkforward_folds"]
    ]
    live = dict(TRIALS)
    records: dict[str, dict[str, Any]] = {
        trial_id: {
            "attempt_id": trial_id,
            "trial_id": trial_id,
            "interaction_cst": interaction,
            "phase": "development_walkforward",
            "created_at": intent["opened_at"],
            "formula": "monotone HistGradientBoostingRegressor over all 140 favorable percentiles",
            "direction": "higher",
            "shared_parameters": MODEL_PARAMETERS,
            "source_feature_count": design.FEATURE_COUNT,
            "source_feature_order_sha256": design.FEATURE_ORDER_SHA256,
            "folds": [],
            "validation_metrics": [],
            "candidate49_historical_return_read": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
        }
        for trial_id, interaction in TRIALS
    }
    try:
        for fold in folds:
            if not live:
                break
            print(
                f"fold {fold['fold']}: loading training returns and fitting", flush=True
            )
            fits, models, training_metrics = fit_fold(
                template, fold, live, args.batch_size, output_root
            )
            print(
                f"fold {fold['fold']}: auditing validation scores before returns",
                flush=True,
            )
            prefit, trial_scores, identities = validation_prefit_audit(
                fold, fits, models, output_root
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
                        "fit": fits[trial_id],
                        "training_metrics": training_metrics[trial_id],
                        "prefit_uniqueness_record": prefit["record_binding"],
                        "uniqueness": prefit["uniqueness"][trial_id],
                        "validation_metrics": None,
                    }
                )
            for trial_id in rejected:
                records[trial_id][
                    "terminal_before_validation_return_reason"
                ] = f"fold_{fold['fold']}_uniqueness_failed"
            live = {trial_id: live[trial_id] for trial_id in passed}
            if not live:
                continue
            print(
                f"fold {fold['fold']}: uniqueness passed; reading validation returns",
                flush=True,
            )
            validation = legacy.evaluate_validation(
                template, fold, passed, identities, args.batch_size
            )
            metrics_payload = {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign132_fold_validation_metrics",
                "status": "completed_after_bound_prefit_uniqueness",
                "created_at": utc_now(),
                "fold": fold["fold"],
                "prefit_uniqueness_record": prefit["record_binding"],
                "validation_metrics": validation,
                "lockbox_2024_2025_return_fields_read": False,
                "candidate49_historical_return_read": False,
                "candidate49_ledgers_changed": False,
            }
            metrics_path = output_root / f"fold_{fold['fold']}_validation_metrics.json"
            legacy.atomic_json(metrics_path, metrics_payload)
            metrics_binding = {
                "path": str(metrics_path),
                "sha256": file_sha256(metrics_path),
            }
            for trial_id in live:
                records[trial_id]["folds"][-1]["validation_metrics"] = validation[
                    trial_id
                ]
                records[trial_id]["folds"][-1][
                    "validation_metrics_binding"
                ] = metrics_binding
                records[trial_id]["validation_metrics"].append(validation[trial_id])
        trial_records: list[dict[str, Any]] = []
        for trial_id, _ in TRIALS:
            record = records[trial_id]
            record["decision"] = legacy.survivor_decision(record)
            record["status"] = (
                "development_survivor_gate_passed"
                if record["decision"]["passed"]
                else "development_rejected"
            )
            trial_records.append(record)
        survivors = rank_survivors(trial_records)
        ledger = build_ledger(trial_records)
        ledger_path = output_root / "trial_ledger.json"
        legacy.atomic_json(ledger_path, ledger)
        survivor_record = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign132_development_survivors",
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
        legacy.atomic_json(survivor_path, survivor_record)
        report = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign132_development_report",
            "status": "development_complete_survivors_frozen",
            "created_at": utc_now(),
            "protocol_sha256": PROTOCOL_SHA256,
            "design_verification": verification,
            "trial_count": len(trial_records),
            "ledger_entry_count": ledger["entry_count"],
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
        legacy.atomic_json(report_path, report)
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
            "kind": "a_share_three_day_walkforward_campaign132_development_failure",
            "status": "failed_preserved_requires_explicit_recovery_revision",
            "created_at": utc_now(),
            "error_type": type(error).__name__,
            "error": str(error),
            "training_or_validation_returns_may_have_been_read": True,
            "lockbox_2024_2025_return_fields_read": False,
            "candidate49_historical_return_read": False,
            "candidate49_ledgers_changed": False,
            "provider_request_issued": False,
        }
        legacy.atomic_json(output_root / "development_failure.json", failure)
        raise


def plan(args: argparse.Namespace) -> dict[str, Any]:
    _implementation_freeze()
    protocol, _ = load_frozen_context()
    verification = design.verify_snapshot(DEFAULT_DESIGN_MANIFEST)
    output_root = Path(args.output_root).expanduser().resolve()
    empty_or_absent = not output_root.exists() or not list(output_root.iterdir())
    ready = bool(
        empty_or_absent
        and verification.get("dataset_sha256") == DESIGN_DATASET_SHA256
        and len(protocol.get("walkforward_folds") or []) == 3
    )
    return {
        "status": (
            "ready_to_open_2019_2023_training_returns"
            if ready
            else "not_ready_preserve_existing_output"
        ),
        "ready": ready,
        "trial_count": len(TRIALS),
        "fold_count": 3,
        "output_root": str(output_root),
        "design_verification": verification,
        "historical_daily_price_or_forward_return_values_read_by_plan": False,
        "lockbox_2024_2025_return_fields_read_by_plan": False,
        "provider_request_issued": False,
        "candidate49_ledgers_changed": False,
    }


def status(args: argparse.Namespace) -> dict[str, Any]:
    output_root = Path(args.output_root).expanduser().resolve()
    result: dict[str, Any] = {
        "status": "frozen_pending_development",
        "output_root": str(output_root),
        "implementation_freeze_exists": DEFAULT_IMPLEMENTATION_FREEZE.is_file(),
        "historical_daily_price_or_return_values_read_by_status": False,
        "lockbox_2024_2025_return_fields_read_by_status": False,
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
    subcommands.add_parser("plan")
    development = subcommands.add_parser("run-development")
    development.add_argument("--batch-size", type=int, default=100)
    development.add_argument("--confirm-run", action="store_true")
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "status":
            payload = status(args)
        elif args.command == "plan":
            payload = plan(args)
        elif args.command == "run-development":
            payload = run_development(args)
        else:
            raise Campaign132Error(f"unsupported command: {args.command}")
    except (Campaign132Error, ValueError, FileNotFoundError) as error:
        print(
            json.dumps(
                {"status": "failed", "error": str(error)}, ensure_ascii=False, indent=2
            )
        )
        return 2
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
            default=legacy.engine.research._json_default,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
