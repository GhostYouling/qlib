#!/usr/bin/env python3
"""Run Campaign134's frozen positive-redundancy balanced consensus."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import a_share_three_day_walkforward_campaign133 as shared  # noqa: E402

base = shared.base
legacy = shared.legacy
design = shared.design

REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_134_preregistration_20260814.json"
)
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_134_development_implementation_freeze_20260814.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign134.py"
)
CONCEPT_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_134_concept_scouting_20260814.json"
)
OVERLAP_AUDIT_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_134_mechanism_overlap_audit_20260814.json"
)
TRANSITION_FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_134_post_campaign133_missing_test_path_failure_20260814.json"
)
SYNTHETIC_FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_134_initial_synthetic_test_failure_20260814.json"
)
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_134/walkforward_v1"
)

PROTOCOL_SHA256 = "9193053035f1961d22db0c214cb5d55c29570a0f93dac12a084bde50bcecd435"
CONCEPT_SHA256 = "3815a871a097ff8e42b64611056043539b6e859a710c0ce5ab15d1d1bc45c894"
OVERLAP_AUDIT_SHA256 = (
    "9c7301140468b44ca827366d0b911452de170cfae2e9770cc1f47fd38f2b092d"
)
TRANSITION_FAILURE_SHA256 = (
    "5443c236d5c23bbaf2c78531052f8c2f7c46ad184cd29cf51378586a98a4abd9"
)
SYNTHETIC_FAILURE_SHA256 = (
    "5b388e18e75c92176e8c8a8a1e07d5f2cbdb9b37ee9f56db744d71fb59f86d50"
)
FROZEN_SHARED_RUNNER_SHA256 = (
    "aaebd401c017ef94a4d41322dc27fb87a9b7926b0c08e758f26dfd71042b5aae"
)
DESIGN_MANIFEST_SHA256 = base.DESIGN_MANIFEST_SHA256
DESIGN_DATASET_SHA256 = base.DESIGN_DATASET_SHA256
DESIGN_AUDIT_SHA256 = base.DESIGN_AUDIT_SHA256
TRIAL_ID = "wf134_complete140_corr80_component_balanced_consensus"
CORRELATION_THRESHOLD = 0.8
MINIMUM_JOINT_NAMES = 50
MINIMUM_PAIR_SESSIONS = 100
NEUTRAL_FILL = 0.5
CHAIN_GENESIS = "0" * 64


class Campaign134Error(RuntimeError):
    """Fail closed when a Campaign134 invariant or chronological gate changes."""


def require_file(path: Path, expected: str, label: str) -> None:
    if len(expected) != 64 or not path.is_file() or base.file_sha256(path) != expected:
        raise Campaign134Error(f"{label} changed: {path}")


def implementation_freeze() -> dict[str, Any]:
    record = base.load_json(IMPLEMENTATION_FREEZE_PATH)
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign134_development_implementation_freeze"
        and record.get("status")
        == "frozen_before_first_campaign134_component_value_graph_fit_or_return_read"
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (record.get("design_manifest") or {}).get("sha256")
        == DESIGN_MANIFEST_SHA256
        and (record.get("design_audit") or {}).get("sha256") == DESIGN_AUDIT_SHA256
        and (record.get("frozen_shared_runner") or {}).get("sha256")
        == FROZEN_SHARED_RUNNER_SHA256
        and (record.get("runner") or {}).get("sha256")
        == base.file_sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == base.file_sha256(TEST_PATH)
        and record.get("campaign134_component_values_read_before_freeze") is False
        and record.get("campaign134_graph_fit_or_score_before_freeze") is False
        and record.get("campaign134_training_or_validation_return_read_before_freeze")
        is False
        and record.get("lockbox_2024_2025_return_read_before_freeze") is False
        and record.get("candidate49_ledgers_changed_before_freeze") is False
    ):
        raise Campaign134Error("Campaign134 development implementation freeze changed")
    return record


def load_frozen_context() -> tuple[dict[str, Any], dict[str, Any]]:
    shared.ensure_base_runtime()
    bindings = (
        (PROTOCOL_PATH, PROTOCOL_SHA256, "Campaign134 protocol"),
        (CONCEPT_PATH, CONCEPT_SHA256, "Campaign134 concept catalog"),
        (OVERLAP_AUDIT_PATH, OVERLAP_AUDIT_SHA256, "Campaign134 overlap audit"),
        (
            TRANSITION_FAILURE_PATH,
            TRANSITION_FAILURE_SHA256,
            "Campaign134 transition failure",
        ),
        (
            SYNTHETIC_FAILURE_PATH,
            SYNTHETIC_FAILURE_SHA256,
            "Campaign134 synthetic failure",
        ),
        (
            Path(shared.__file__).resolve(),
            FROZEN_SHARED_RUNNER_SHA256,
            "frozen shared runner",
        ),
    )
    for path, expected, label in bindings:
        require_file(path, expected, label)
    protocol = base.load_json(PROTOCOL_PATH)
    _, template = base.load_frozen_context()
    search = protocol.get("search_multiplicity") or {}
    graph = protocol.get("frozen_graph_fit") or {}
    score = protocol.get("frozen_score_algorithm") or {}
    library = protocol.get("complete_feature_library") or {}
    if not (
        protocol.get("kind")
        == "a_share_three_day_walkforward_campaign134_preregistration"
        and [item.get("trial_id") for item in protocol.get("trial_catalog") or []]
        == [TRIAL_ID]
        and search.get("trial_count") == 1
        and search.get("positive_correlation_threshold") == CORRELATION_THRESHOLD
        and search.get("minimum_joint_names_per_daily_pair") == MINIMUM_JOINT_NAMES
        and search.get("minimum_daily_pair_correlations") == MINIMUM_PAIR_SESSIONS
        and search.get("graph_rule") == "undirected_connected_components"
        and graph.get("return_or_target_fields_used") is False
        and score.get("target_fitted_weights") is False
        and score.get("negative_or_zero_source_weights") is False
        and library.get("numeric_feature_count") == design.FEATURE_COUNT
        and library.get("numeric_feature_order_sha256") == design.FEATURE_ORDER_SHA256
        and (library.get("design_support") or {}).get("minimum_finite_components")
        == design.MINIMUM_FINITE_COMPONENTS
        and (library.get("design_support") or {}).get("model_input_missing_fill")
        == NEUTRAL_FILL
        and len(protocol.get("walkforward_folds") or []) == 3
    ):
        raise Campaign134Error("Campaign134 frozen protocol semantics changed")
    return protocol, template


def connected_components(
    median_correlations: np.ndarray,
    pair_session_counts: np.ndarray,
    *,
    threshold: float = CORRELATION_THRESHOLD,
    minimum_sessions: int = MINIMUM_PAIR_SESSIONS,
) -> tuple[list[list[int]], list[tuple[int, int]]]:
    correlations = np.asarray(median_correlations, dtype=np.float64)
    counts = np.asarray(pair_session_counts, dtype=np.int64)
    expected = (design.FEATURE_COUNT, design.FEATURE_COUNT)
    if correlations.shape != expected or counts.shape != expected:
        raise Campaign134Error("graph matrix shape changed")
    parents = np.arange(design.FEATURE_COUNT, dtype=np.int64)

    def find(value: int) -> int:
        while parents[value] != value:
            parents[value] = parents[int(parents[value])]
            value = int(parents[value])
        return value

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root:
            return
        lower = min(left_root, right_root)
        upper = max(left_root, right_root)
        parents[upper] = lower

    edges: list[tuple[int, int]] = []
    for left in range(design.FEATURE_COUNT):
        for right in range(left + 1, design.FEATURE_COUNT):
            if (
                counts[left, right] >= minimum_sessions
                and np.isfinite(correlations[left, right])
                and correlations[left, right] >= threshold
            ):
                edges.append((left, right))
                union(left, right)
    groups: dict[int, list[int]] = {}
    for feature in range(design.FEATURE_COUNT):
        groups.setdefault(find(feature), []).append(feature)
    components = sorted(
        (sorted(members) for members in groups.values()), key=lambda item: item[0]
    )
    if sorted(feature for group in components for feature in group) != list(
        range(design.FEATURE_COUNT)
    ):
        raise Campaign134Error("graph components do not partition all features")
    return components, edges


def fit_graph(
    signal_dates: pd.Series | pd.Index | np.ndarray,
    matrix: np.ndarray,
    *,
    minimum_names: int = MINIMUM_JOINT_NAMES,
    minimum_sessions: int = MINIMUM_PAIR_SESSIONS,
    threshold: float = CORRELATION_THRESHOLD,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    shared.ensure_base_runtime()
    dates = pd.DatetimeIndex(signal_dates).normalize().to_numpy(dtype="datetime64[D]")
    values = np.asarray(matrix, dtype=np.float64)
    if values.shape != (len(dates), design.FEATURE_COUNT):
        raise Campaign134Error("graph fit inputs changed")
    if len(dates) > 1 and np.any(dates[1:] < dates[:-1]):
        raise Campaign134Error("graph fit rows are not session sorted")
    boundaries = np.flatnonzero(np.r_[True, dates[1:] != dates[:-1], True])
    daily: list[np.ndarray] = []
    for index in range(len(boundaries) - 1):
        positions = slice(int(boundaries[index]), int(boundaries[index + 1]))
        frame = pd.DataFrame(values[positions], copy=False)
        daily.append(
            frame.corr(method="spearman", min_periods=minimum_names).to_numpy(
                dtype=np.float64
            )
        )
    if len(daily) < minimum_sessions:
        raise Campaign134Error("insufficient training sessions for frozen graph")
    cube = np.stack(daily, axis=0)
    counts = np.isfinite(cube).sum(axis=0).astype(np.uint16)
    medians = np.full((design.FEATURE_COUNT, design.FEATURE_COUNT), np.nan)
    eligible_pairs = counts >= minimum_sessions
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        observed_medians = np.nanmedian(cube, axis=0)
    medians[eligible_pairs] = observed_medians[eligible_pairs]
    components, edges = connected_components(
        medians,
        counts,
        threshold=threshold,
        minimum_sessions=minimum_sessions,
    )
    names = list(design.component_columns())
    component_names = [[names[index] for index in group] for group in components]
    size_values = [len(group) for group in components]
    graph = {
        "training_sessions": len(daily),
        "minimum_joint_names_per_daily_pair": minimum_names,
        "minimum_daily_pair_correlations": minimum_sessions,
        "positive_correlation_edge_threshold": threshold,
        "feature_count": design.FEATURE_COUNT,
        "component_count": len(components),
        "edge_count": len(edges),
        "minimum_component_size": min(size_values),
        "maximum_component_size": max(size_values),
        "singleton_component_count": sum(size == 1 for size in size_values),
        "components": components,
        "component_names": component_names,
        "edges": [list(edge) for edge in edges],
        "median_correlations_sha256": hashlib.sha256(
            medians.astype("<f8").tobytes()
        ).hexdigest(),
        "pair_session_counts_sha256": hashlib.sha256(
            counts.astype("<u2").tobytes()
        ).hexdigest(),
        "return_or_target_fields_used": False,
    }
    return graph, medians, counts


def component_weights(components: list[list[int]]) -> np.ndarray:
    if not components:
        raise Campaign134Error("graph has no components")
    weights = np.zeros(design.FEATURE_COUNT, dtype=np.float64)
    seen: list[int] = []
    for component in components:
        if not component:
            raise Campaign134Error("graph has an empty component")
        value = 1.0 / (len(components) * len(component))
        weights[np.asarray(component, dtype=np.int64)] = value
        seen.extend(component)
    if sorted(seen) != list(range(design.FEATURE_COUNT)) or not math.isclose(
        float(weights.sum()), 1.0, rel_tol=0.0, abs_tol=1e-12
    ):
        raise Campaign134Error("component weights do not preserve all features")
    if np.any(weights <= 0.0):
        raise Campaign134Error("component weight is not strictly positive")
    return weights


def graph_scores(
    components: list[list[int]], matrix: np.ndarray, eligible: np.ndarray
) -> np.ndarray:
    values = np.asarray(matrix, dtype=np.float64)
    support = np.asarray(eligible, dtype=bool)
    if values.shape != (len(support), design.FEATURE_COUNT):
        raise Campaign134Error("graph score inputs changed")
    finite = np.isfinite(values)
    if np.any((values[finite] < 0.0) | (values[finite] > 1.0)):
        raise Campaign134Error("favorable percentile outside [0,1]")
    filled = np.where(finite, values, NEUTRAL_FILL)
    scores = filled @ component_weights(components)
    scores[~support] = np.nan
    if not np.isfinite(scores[support]).all():
        raise Campaign134Error("eligible graph score is nonfinite")
    return scores


def fit_fold(
    template: dict[str, Any],
    fold: dict[str, Any],
    batch_size: int,
    output_root: Path,
) -> tuple[dict[str, Any], list[list[int]], dict[str, Any]]:
    training_start, training_end = fold["training"]
    panel, quotes, calendar, schedule, matrix, eligible = base.build_training_panel(
        template, training_end, batch_size
    )
    graph, medians, counts = fit_graph(panel["signal_date"], matrix)
    model_root = output_root / f"fold_{fold['fold']}_models"
    median_path = model_root / f"{TRIAL_ID}_median_correlations.f64"
    counts_path = model_root / f"{TRIAL_ID}_pair_session_counts.u16"
    graph_path = model_root / f"{TRIAL_ID}_graph.json"
    base.atomic_binary(median_path, medians.astype("<f8").tobytes())
    base.atomic_binary(counts_path, counts.astype("<u2").tobytes())
    graph_payload = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign134_fold_training_graph",
        "status": "fit_without_return_or_target_fields",
        "created_at": base.utc_now(),
        "fold": fold["fold"],
        "training": list(fold["training"]),
        "graph": graph,
        "median_correlations": {
            "path": str(median_path),
            "sha256": base.file_sha256(median_path),
            "dtype": "little_endian_float64",
            "shape": [design.FEATURE_COUNT, design.FEATURE_COUNT],
        },
        "pair_session_counts": {
            "path": str(counts_path),
            "sha256": base.file_sha256(counts_path),
            "dtype": "little_endian_uint16",
            "shape": [design.FEATURE_COUNT, design.FEATURE_COUNT],
        },
        "historical_forward_return_fields_used_for_fit": False,
        "validation_component_or_return_values_read_before_record": False,
    }
    legacy.atomic_json(graph_path, graph_payload)
    scores = graph_scores(graph["components"], matrix, eligible)
    panel[legacy._score_column(TRIAL_ID)] = scores
    trial = {"feature_set": [TRIAL_ID], "weights": [1.0]}
    training_metrics = legacy.engine.evaluate_trial_period(
        panel,
        quotes,
        calendar,
        schedule,
        trial,
        training_start,
        training_end,
        base.PURGE_SIGNAL_SESSIONS,
        include_sensitivity=False,
    )
    fit = {
        "family": "complete_140_numeric_library_positive_correlation_component_balanced_consensus",
        "graph": graph,
        "graph_record": {
            "path": str(graph_path),
            "sha256": base.file_sha256(graph_path),
        },
        "source_weights_sha256": hashlib.sha256(
            component_weights(graph["components"]).astype("<f8").tobytes()
        ).hexdigest(),
        "minimum_source_weight": float(component_weights(graph["components"]).min()),
        "maximum_source_weight": float(component_weights(graph["components"]).max()),
        "target_or_return_used_for_graph_fit": False,
    }
    return fit, graph["components"], training_metrics


def validation_prefit_audit(
    fold: dict[str, Any],
    fit: dict[str, Any],
    components: list[list[int]],
    output_root: Path,
) -> tuple[dict[str, Any], np.ndarray, pd.DataFrame]:
    validation_start, validation_end = fold["validation"]
    identities, matrix, _, eligible = base.load_design_years(
        [pd.Timestamp(validation_start).year]
    )
    scores = graph_scores(components, matrix, eligible)
    uniqueness = base.uniqueness_audit(
        identities["stock_day_key"].to_numpy(dtype=np.int64),
        matrix,
        scores,
        design.component_columns(),
    )
    score_binding = legacy.write_score_snapshot(
        output_root / f"fold_{fold['fold']}_validation_scores.parquet",
        identities,
        {TRIAL_ID: scores},
    )
    payload = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign134_fold_prefit_uniqueness",
        "status": "frozen_before_fold_validation_return_read",
        "created_at": base.utc_now(),
        "fold": int(fold["fold"]),
        "training": list(fold["training"]),
        "validation": [validation_start, validation_end],
        "fit": fit,
        "validation_score_snapshot": score_binding,
        "uniqueness": uniqueness,
        "all_140_comparisons_audited_before_validation_returns": True,
        "validation_daily_price_fields_read_before_record": [],
        "validation_forward_return_fields_read_before_record": False,
        "lockbox_2024_2025_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
    }
    path = output_root / f"fold_{fold['fold']}_prefit_uniqueness.json"
    legacy.atomic_json(path, payload)
    payload["record_binding"] = {"path": str(path), "sha256": base.file_sha256(path)}
    return payload, scores, identities


def concept_and_failure_entries() -> list[dict[str, Any]]:
    concept = base.load_json(CONCEPT_PATH)
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
    for failure_path, failure_sha256 in (
        (TRANSITION_FAILURE_PATH, TRANSITION_FAILURE_SHA256),
        (SYNTHETIC_FAILURE_PATH, SYNTHETIC_FAILURE_SHA256),
    ):
        failure = base.load_json(failure_path)
        entries.append(
            {
                "attempt_id": failure["attempt_id"],
                "phase": "infrastructure_failure",
                "stage": failure["stage"],
                "outcome": failure["status"],
                "evidence": {
                    "path": str(failure_path),
                    "sha256": failure_sha256,
                },
                "scientific_result_changed": False,
                "historical_forward_return_fields_read": False,
            }
        )
    return entries


def build_ledger(trial_record: dict[str, Any]) -> dict[str, Any]:
    previous = CHAIN_GENESIS
    entries: list[dict[str, Any]] = []
    for record in [*concept_and_failure_entries(), trial_record]:
        entry = {**record, "previous_entry_sha256": previous}
        entry["entry_sha256"] = base.value_sha256(entry)
        previous = entry["entry_sha256"]
        entries.append(entry)
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign134_trial_ledger",
        "append_only": True,
        "campaign": {"protocol_sha256": PROTOCOL_SHA256},
        "chain_genesis": CHAIN_GENESIS,
        "entries": entries,
        "entry_count": len(entries),
        "prevalue_concept_attempt_count": 6,
        "infrastructure_failure_attempt_count": 2,
        "model_trial_attempt_count": 1,
        "chain_tip_sha256": previous,
        "candidate49_historical_return_read": False,
        "candidate49_ledgers_changed": False,
    }


def run_development(args: argparse.Namespace) -> dict[str, Any]:
    if not args.confirm_run:
        raise Campaign134Error("run-development requires --confirm-run")
    implementation_freeze()
    protocol, template = load_frozen_context()
    verification = design.verify_snapshot(base.DEFAULT_DESIGN_MANIFEST)
    output_root = Path(args.output_root).expanduser().resolve()
    report_path = output_root / "development_report.json"
    if report_path.exists():
        report = base.load_json(report_path)
        return {
            "status": "development_already_complete_idempotent",
            "report_path": str(report_path),
            "report_sha256": base.file_sha256(report_path),
            "survivor_count": report["survivor_count"],
        }
    output_root.mkdir(parents=True, exist_ok=True)
    if list(output_root.iterdir()):
        raise Campaign134Error(
            "incomplete Campaign134 output exists; preserve it and use an explicit recovery revision"
        )
    intent = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign134_development_intent",
        "status": "training_factor_graph_and_returns_open_pending_chronological_completion",
        "opened_at": base.utc_now(),
        "protocol_sha256": PROTOCOL_SHA256,
        "design_manifest_sha256": DESIGN_MANIFEST_SHA256,
        "design_audit_sha256": DESIGN_AUDIT_SHA256,
        "runner_sha256": base.file_sha256(Path(__file__).resolve()),
        "graph_fit_never_uses_return_or_target_fields": True,
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
    record: dict[str, Any] = {
        "attempt_id": TRIAL_ID,
        "trial_id": TRIAL_ID,
        "phase": "development_walkforward",
        "created_at": intent["opened_at"],
        "formula": "equal mean of training-only +0.8 Spearman connected-component means over all 140 favorable percentiles",
        "direction": "higher",
        "source_feature_count": design.FEATURE_COUNT,
        "source_feature_order_sha256": design.FEATURE_ORDER_SHA256,
        "positive_correlation_threshold": CORRELATION_THRESHOLD,
        "folds": [],
        "validation_metrics": [],
        "candidate49_historical_return_read": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }
    live = True
    try:
        for fold in folds:
            if not live:
                break
            print(
                f"fold {fold['fold']}: fitting training-only redundancy graph and computing training evidence",
                flush=True,
            )
            fit, components, training_metrics = fit_fold(
                template, fold, args.batch_size, output_root
            )
            print(
                f"fold {fold['fold']}: auditing validation score against all 140 components before returns",
                flush=True,
            )
            prefit, scores, identities = validation_prefit_audit(
                fold, fit, components, output_root
            )
            fold_record = {
                "fold": fold["fold"],
                "fit": fit,
                "training_metrics": training_metrics,
                "prefit_uniqueness_record": prefit["record_binding"],
                "uniqueness": prefit["uniqueness"],
                "validation_metrics": None,
            }
            record["folds"].append(fold_record)
            if not prefit["uniqueness"]["all_required_comparisons_passed"]:
                record["terminal_before_validation_return_reason"] = (
                    f"fold_{fold['fold']}_uniqueness_failed"
                )
                live = False
                continue
            print(
                f"fold {fold['fold']}: uniqueness passed; reading contained validation returns",
                flush=True,
            )
            validation = legacy.evaluate_validation(
                template,
                fold,
                {TRIAL_ID: scores},
                identities,
                args.batch_size,
            )
            metrics_payload = {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign134_fold_validation_metrics",
                "status": "completed_after_bound_prefit_uniqueness",
                "created_at": base.utc_now(),
                "fold": fold["fold"],
                "prefit_uniqueness_record": prefit["record_binding"],
                "validation_metrics": validation,
                "lockbox_2024_2025_return_fields_read": False,
                "candidate49_historical_return_read": False,
                "candidate49_ledgers_changed": False,
            }
            metrics_path = output_root / f"fold_{fold['fold']}_validation_metrics.json"
            legacy.atomic_json(metrics_path, metrics_payload)
            fold_record["validation_metrics"] = validation[TRIAL_ID]
            fold_record["validation_metrics_binding"] = {
                "path": str(metrics_path),
                "sha256": base.file_sha256(metrics_path),
            }
            record["validation_metrics"].append(validation[TRIAL_ID])
        record["decision"] = legacy.survivor_decision(record)
        record["status"] = (
            "development_survivor_gate_passed"
            if record["decision"]["passed"]
            else "development_rejected"
        )
        survivors = [TRIAL_ID] if record["decision"]["passed"] else []
        ledger = build_ledger(record)
        ledger_path = output_root / "trial_ledger.json"
        legacy.atomic_json(ledger_path, ledger)
        survivor_record = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign134_development_survivors",
            "status": "frozen_before_2024_2025_return_read",
            "created_at": base.utc_now(),
            "ledger": {
                "path": str(ledger_path),
                "sha256": base.file_sha256(ledger_path),
            },
            "trial_decisions": {TRIAL_ID: record["decision"]},
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
            "kind": "a_share_three_day_walkforward_campaign134_development_report",
            "status": "development_complete_survivors_frozen",
            "created_at": base.utc_now(),
            "protocol_sha256": PROTOCOL_SHA256,
            "design_verification": verification,
            "trial_count": 1,
            "ledger_entry_count": ledger["entry_count"],
            "validation_return_reading_trial_count": int(
                len(record["validation_metrics"]) == 3
            ),
            "validation_return_fold_count": len(record["validation_metrics"]),
            "survivor_count": len(survivors),
            "selected_survivor_trial_ids": survivors,
            "ledger": {
                "path": str(ledger_path),
                "sha256": base.file_sha256(ledger_path),
            },
            "survivors": {
                "path": str(survivor_path),
                "sha256": base.file_sha256(survivor_path),
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
            "trial_count": 1,
            "validation_return_fold_count": report["validation_return_fold_count"],
            "survivor_count": len(survivors),
            "selected_survivor_trial_ids": survivors,
            "report_path": str(report_path),
            "report_sha256": base.file_sha256(report_path),
        }
    except BaseException as error:
        failure = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign134_development_failure",
            "status": "failed_preserved_requires_explicit_recovery_revision",
            "created_at": base.utc_now(),
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
    implementation_freeze()
    protocol, _ = load_frozen_context()
    verification = design.verify_snapshot(base.DEFAULT_DESIGN_MANIFEST)
    output_root = Path(args.output_root).expanduser().resolve()
    empty_or_absent = not output_root.exists() or not list(output_root.iterdir())
    ready = bool(
        empty_or_absent
        and verification.get("dataset_sha256") == DESIGN_DATASET_SHA256
        and len(protocol.get("walkforward_folds") or []) == 3
    )
    return {
        "status": (
            "ready_to_open_2019_2023_training_factor_values_and_returns"
            if ready
            else "not_ready_preserve_existing_output"
        ),
        "ready": ready,
        "trial_count": 1,
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
        "implementation_freeze_exists": IMPLEMENTATION_FREEZE_PATH.is_file(),
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
        report = base.load_json(output_root / "development_report.json")
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
            raise Campaign134Error(f"unsupported command: {args.command}")
    except (
        Campaign134Error,
        shared.Campaign133Error,
        base.Campaign132Error,
        ValueError,
        FileNotFoundError,
    ) as error:
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
