#!/usr/bin/env python3
"""Run Campaign002: nonlinear consensus combinations for the three-day study.

This campaign deliberately reuses the complete eight-factor Campaign001
research library while preserving every prior terminal conclusion.  It runs
only a finite, preregistered family of nonlinear pair consensus operators:
geometric mean, harmonic mean, and minimum of same-day directional percentile
ranks.

The two return-reading phases remain separate:

* ``run-development`` reads only 2019-2023 expanding walk-forward partitions.
* ``run-exposed-stress --confirm-exposed-stress`` reads 2024-2025 only for the
  frozen development survivors.  This interval is explicitly historically
  exposed and is never described as an unseen lockbox.

Candidate49 is excluded.  This script never reads or writes its prospective
signal, execution, or evaluation ledgers and creates no current stock score,
selection, sizing, or order artifact.
"""

from __future__ import annotations

import argparse
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_three_day_walkforward_campaign as base  # noqa: E402
import a_share_short_horizon_factor_research as research  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CAMPAIGN = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_002_preregistration.json"
)
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT
    / "data"
    / "experiments"
    / "short_horizon"
    / "historical_walkforward"
    / "campaign_002"
)
LEDGER_FILENAME = "trial_ledger.json"
SURVIVOR_FILENAME = "development_survivors.json"
STRESS_INTENT_FILENAME = "exposed_stress_open_intent.json"
STRESS_RECORD_FILENAME = "exposed_stress_consumption_record.json"
REPORT_FILENAME = "campaign_report.json"
LEDGER_KIND = "a_share_three_day_historical_walkforward_campaign002_trial_ledger"
LEDGER_VERSION = 1
CHAIN_GENESIS = "0" * 64
CAMPAIGN_ID = "a_share_three_day_walkforward_campaign_002"
DEVELOPMENT_PHASE = "development_walkforward_2019_2023"
STRESS_PHASE = "historically_exposed_stress_replay_2024_2025"


class Campaign002Error(RuntimeError):
    """Fail-closed Campaign002 error."""


def validate_binding(binding: dict[str, Any], label: str) -> Path:
    try:
        return base.validate_file_binding(binding, label)
    except base.WalkForwardError as error:
        raise Campaign002Error(str(error)) from error


def load_campaign(
    path: Path,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    path = path.expanduser().resolve()
    spec = base.load_json(path)
    if (
        spec.get("version") != 1
        or spec.get("kind")
        != "a_share_three_day_walkforward_campaign_preregistration"
        or spec.get("campaign_id") != CAMPAIGN_ID
        or spec.get("status")
        != "frozen_before_campaign002_development_or_exposed_stress_return_read"
    ):
        raise Campaign002Error("Campaign002 preregistration header is invalid")
    allowed_keys = {
        "version",
        "kind",
        "campaign_id",
        "status",
        "frozen_at",
        "purpose",
        "evidence_classification",
        "governance_bindings",
        "campaign001_bindings",
        "implementation",
        "reused_complete_feature_library",
        "search_space",
        "walkforward_folds",
        "split_protocol",
        "survivor_rule",
        "exposed_stress_replay",
        "candidate49_boundary",
        "research_output_boundary",
    }
    unexpected = sorted(set(spec) - allowed_keys)
    if unexpected:
        raise Campaign002Error(
            "Campaign002 preregistration has unexpected fields: "
            + ", ".join(unexpected)
        )
    for group_name in ("governance_bindings", "campaign001_bindings"):
        for name, binding in sorted((spec.get(group_name) or {}).items()):
            validate_binding(binding, f"{group_name}.{name}")
    implementation = spec.get("implementation") or {}
    if set(implementation) != {
        "script",
        "development_command",
        "exposed_stress_command",
        "output_root",
    }:
        raise Campaign002Error("Campaign002 implementation binding is incomplete")
    script_path = validate_binding(implementation["script"], "Campaign002 runner")
    if script_path != Path(__file__).resolve():
        raise Campaign002Error("Campaign002 runner binding identifies another file")

    base_binding = (spec.get("campaign001_bindings") or {}).get(
        "repaired_preregistration"
    ) or {}
    base_path = validate_binding(base_binding, "Campaign001 repaired preregistration")
    try:
        campaign001, observed_base_sha = base.load_campaign(base_path)
    except base.WalkForwardError as error:
        raise Campaign002Error(str(error)) from error
    if observed_base_sha != str(base_binding.get("sha256")):
        raise Campaign002Error("Campaign001 preregistration digest changed")

    completion = base.load_json(
        validate_binding(
            (spec.get("campaign001_bindings") or {}).get("completion_audit") or {},
            "Campaign001 completion audit",
        )
    )
    if (
        completion.get("kind")
        != "a_share_three_day_walkforward_campaign_completion_audit_record"
        or completion.get("status") != "passed_all_goal_requirements"
        or int(completion.get("requirement_check_count") or 0) != 15
        or completion.get("failed_requirement_checks") != []
    ):
        raise Campaign002Error("Campaign001 completion audit is not accepted")

    factors = list(campaign001.get("factor_library") or [])
    names = sorted(str(item.get("name") or "") for item in factors)
    reused = spec.get("reused_complete_feature_library") or {}
    expected_names = sorted(str(value) for value in reused.get("factor_names") or [])
    if (
        len(factors) != 8
        or names != expected_names
        or len(names) != len(set(names))
        or reused.get("factor_count") != 8
        or reused.get("all_prior_terminal_conclusions_unchanged") is not True
        or "intraday_cumulative_vwap_crossing_rate_240m" in names
        or any(item.get("prior_terminal_conclusion_unchanged") is not True for item in factors)
    ):
        raise Campaign002Error("complete reused feature library is not accepted")

    campaign = dict(campaign001)
    campaign.update(
        {
            "campaign_id": CAMPAIGN_ID,
            "implementation": implementation,
            "walkforward_folds": spec.get("walkforward_folds"),
            "split_protocol": spec.get("split_protocol"),
            "survivor_rule": spec.get("survivor_rule"),
            "search_space": spec.get("search_space"),
            "exposed_stress_replay": spec.get("exposed_stress_replay"),
            "candidate49_boundary": spec.get("candidate49_boundary"),
            "research_output_boundary": spec.get("research_output_boundary"),
        }
    )
    if campaign["walkforward_folds"] != campaign001["walkforward_folds"]:
        raise Campaign002Error("Campaign002 walk-forward folds changed from policy")
    if campaign["split_protocol"] != campaign001["split_protocol"]:
        raise Campaign002Error("Campaign002 split or holding protocol changed")
    boundary = campaign["candidate49_boundary"] or {}
    if (
        boundary.get("included_in_feature_library") is not False
        or boundary.get("historical_return_read_allowed") is not False
        or boundary.get("prospective_ledgers_changed_by_campaign") is not False
    ):
        raise Campaign002Error("Candidate49 boundary is not fail-closed")
    output_boundary = campaign["research_output_boundary"] or {}
    if not all(
        output_boundary.get(key) is False
        for key in (
            "current_scoring_allowed",
            "selection_allowed",
            "sizing_allowed",
            "orders_allowed",
            "prospective_candidate_activation_allowed",
        )
    ):
        raise Campaign002Error("Campaign002 research output boundary is not closed")
    catalog = build_trial_catalog(campaign)
    if len(catalog) != int(campaign["search_space"]["expected_trial_count"]):
        raise Campaign002Error("Campaign002 trial catalog count changed")
    return campaign, spec, base.file_sha256(path)


def build_trial_catalog(campaign: dict[str, Any]) -> list[dict[str, Any]]:
    names = sorted(str(item.get("name") or "") for item in campaign["factor_library"])
    if (
        len(names) != 8
        or len(names) != len(set(names))
        or "intraday_cumulative_vwap_crossing_rate_240m" in names
    ):
        raise Campaign002Error("Campaign002 requires the complete eight-factor library")
    search = campaign.get("search_space") or {}
    operators = list(search.get("nonlinear_consensus_operators") or [])
    operator_ids = [str(item.get("id") or "") for item in operators]
    if operator_ids != ["geometric_mean", "harmonic_mean", "minimum"]:
        raise Campaign002Error("Campaign002 nonlinear operator grid changed")
    trials: list[dict[str, Any]] = []
    for left_index, left in enumerate(names):
        for right in names[left_index + 1 :]:
            parent = f"wf001_pair__{left}__{right}__w50_50"
            for operator in operators:
                operator_id = str(operator["id"])
                trials.append(
                    {
                        "trial_id": (
                            f"wf002_pair__{left}__{right}__{operator_id}"
                        ),
                        "parent_trial_id": parent,
                        "kind": "nonlinear_pair_consensus",
                        "feature_set": [left, right],
                        "operator": operator_id,
                        "operator_formula": str(operator["formula"]),
                        "complexity": 2,
                    }
                )
    identifiers = [str(item["trial_id"]) for item in trials]
    if len(identifiers) != 84 or len(identifiers) != len(set(identifiers)):
        raise Campaign002Error("Campaign002 must contain exactly 84 unique trials")
    return trials


def trial_score(panel: pd.DataFrame, trial: dict[str, Any]) -> pd.Series:
    left_name, right_name = [str(value) for value in trial["feature_set"]]
    left = pd.to_numeric(
        panel[base.factor_score_column(left_name)], errors="coerce"
    )
    right = pd.to_numeric(
        panel[base.factor_score_column(right_name)], errors="coerce"
    )
    available = (
        left.notna()
        & right.notna()
        & np.isfinite(left)
        & np.isfinite(right)
        & left.gt(0.0)
        & right.gt(0.0)
    )
    operator = str(trial["operator"])
    if operator == "geometric_mean":
        score = np.sqrt(left * right)
    elif operator == "harmonic_mean":
        score = 2.0 / ((1.0 / left) + (1.0 / right))
    elif operator == "minimum":
        score = pd.concat([left, right], axis=1).min(axis=1)
    else:
        raise Campaign002Error(f"unsupported nonlinear operator: {operator}")
    return pd.Series(score, index=panel.index).where(available)


def empty_ledger(campaign_path: Path, campaign_sha: str) -> dict[str, Any]:
    return {
        "version": LEDGER_VERSION,
        "kind": LEDGER_KIND,
        "campaign": {
            "path": str(campaign_path),
            "sha256": campaign_sha,
            "campaign_id": CAMPAIGN_ID,
        },
        "append_only": True,
        "chain_genesis": CHAIN_GENESIS,
        "entries": [],
        "chain_tip_sha256": CHAIN_GENESIS,
    }


def validate_ledger(
    ledger: dict[str, Any], campaign_path: Path, campaign_sha: str
) -> dict[str, Any]:
    campaign = ledger.get("campaign") or {}
    if (
        ledger.get("version") != LEDGER_VERSION
        or ledger.get("kind") != LEDGER_KIND
        or ledger.get("append_only") is not True
        or ledger.get("chain_genesis") != CHAIN_GENESIS
        or campaign.get("path") != str(campaign_path)
        or campaign.get("sha256") != campaign_sha
        or campaign.get("campaign_id") != CAMPAIGN_ID
    ):
        raise Campaign002Error("Campaign002 trial ledger header is invalid")
    previous = CHAIN_GENESIS
    identifiers: set[str] = set()
    entries = list(ledger.get("entries") or [])
    for ordinal, entry in enumerate(entries, start=1):
        trial_id = str(entry.get("trial_id") or "")
        if (
            entry.get("ordinal") != ordinal
            or entry.get("previous_entry_sha256") != previous
            or not trial_id
            or trial_id in identifiers
        ):
            raise Campaign002Error("Campaign002 trial ledger ordering changed")
        expected = base.value_sha256(base.entry_payload_for_hash(entry))
        if entry.get("entry_sha256") != expected:
            raise Campaign002Error("Campaign002 trial ledger entry hash changed")
        identifiers.add(trial_id)
        previous = expected
    if ledger.get("chain_tip_sha256") != previous:
        raise Campaign002Error("Campaign002 trial ledger chain tip changed")
    return ledger


def load_or_initialize_ledger(
    path: Path, campaign_path: Path, campaign_sha: str
) -> dict[str, Any]:
    if path.exists():
        return validate_ledger(base.load_json(path), campaign_path, campaign_sha)
    ledger = empty_ledger(campaign_path, campaign_sha)
    base.atomic_write_json(path, ledger)
    return validate_ledger(base.load_json(path), campaign_path, campaign_sha)


def append_ledger_entry(
    path: Path,
    ledger: dict[str, Any],
    payload: dict[str, Any],
    campaign_path: Path,
    campaign_sha: str,
) -> dict[str, Any]:
    ledger = validate_ledger(ledger, campaign_path, campaign_sha)
    if any(entry["trial_id"] == payload["trial_id"] for entry in ledger["entries"]):
        raise Campaign002Error(f"duplicate trial id: {payload['trial_id']}")
    entry = {
        **payload,
        "ordinal": len(ledger["entries"]) + 1,
        "previous_entry_sha256": ledger["chain_tip_sha256"],
    }
    entry["entry_sha256"] = base.value_sha256(entry)
    updated = dict(ledger)
    updated["entries"] = [*ledger["entries"], entry]
    updated["chain_tip_sha256"] = entry["entry_sha256"]
    base.atomic_write_json(path, updated)
    return validate_ledger(base.load_json(path), campaign_path, campaign_sha)


def evaluate_trial_period(
    panel: pd.DataFrame,
    quotes: Any,
    calendar: pd.DatetimeIndex,
    schedule: pd.DataFrame,
    trial: dict[str, Any],
    start: str,
    end: str,
    purge_signal_count: int,
    *,
    include_sensitivity: bool,
) -> dict[str, Any]:
    period_schedule = base.purged_period_schedule(
        schedule, start, end, purge_signal_count
    )
    score = trial_score(panel, trial)
    association = base.association_metrics(panel, period_schedule, score, topk=3)
    baskets = base.selected_signal_baskets(
        panel, period_schedule, score, topk=3
    )
    period_calendar = calendar[
        (calendar >= pd.Timestamp(start)) & (calendar <= pd.Timestamp(end))
    ]
    normalized = base.simulate_portfolio(
        quotes, period_calendar, period_schedule, baskets, pilot=False, slippage=0.0
    )
    pilot = base.simulate_portfolio(
        quotes, period_calendar, period_schedule, baskets, pilot=True, slippage=0.001
    )
    sensitivity: dict[str, Any] = {}
    if include_sensitivity:
        for rate in (0.0, 0.0005, 0.001, 0.002):
            result = base.simulate_portfolio(
                quotes,
                period_calendar,
                period_schedule,
                baskets,
                pilot=True,
                slippage=rate,
            )
            sensitivity[f"{rate:.4f}"] = {
                "net_cumulative_return": result["net_cumulative_return"],
                "maximum_drawdown": result["maximum_drawdown"],
            }
    return {
        "start": start,
        "end": end,
        "purge_signal_count_each_boundary": purge_signal_count,
        "scheduled_signal_count_after_containment_and_purge": int(
            len(period_schedule)
        ),
        "association": association,
        "normalized_execution": normalized,
        "pilot_execution_primary_10bp": pilot,
        "pilot_slippage_sensitivity": sensitivity,
    }


def development_trial_payload(
    campaign: dict[str, Any],
    campaign_path: Path,
    campaign_sha: str,
    trial: dict[str, Any],
    panel: pd.DataFrame,
    quotes: Any,
    calendar: pd.DatetimeIndex,
    schedule: pd.DataFrame,
    created_at: str,
) -> dict[str, Any]:
    purge = int(campaign["split_protocol"]["purge_signal_sessions_each_boundary"])
    folds: list[dict[str, Any]] = []
    for fold in campaign["walkforward_folds"]:
        training = fold["training"]
        validation = fold["validation"]
        folds.append(
            {
                "fold": int(fold["fold"]),
                "training_metrics": evaluate_trial_period(
                    panel,
                    quotes,
                    calendar,
                    schedule,
                    trial,
                    training["start"],
                    training["end"],
                    purge,
                    include_sensitivity=False,
                ),
                "validation_metrics": evaluate_trial_period(
                    panel,
                    quotes,
                    calendar,
                    schedule,
                    trial,
                    validation["start"],
                    validation["end"],
                    purge,
                    include_sensitivity=False,
                ),
            }
        )
    aggregate = evaluate_trial_period(
        panel,
        quotes,
        calendar,
        schedule,
        trial,
        "2019-01-01",
        "2023-12-31",
        purge,
        include_sensitivity=True,
    )
    factor_lookup = {
        str(item["name"]): item for item in campaign["factor_library"]
    }
    hypotheses = [
        str(factor_lookup[name]["economic_hypothesis"])
        for name in trial["feature_set"]
    ]
    return {
        "trial_id": trial["trial_id"],
        "parent_trial_id": trial["parent_trial_id"],
        "campaign_id": CAMPAIGN_ID,
        "phase": DEVELOPMENT_PHASE,
        "created_at": created_at,
        "economic_hypothesis": (
            "Require nonlinear same-day rank agreement between two distinct "
            "mechanisms to reduce single-mechanism tail exposure: "
            + "; ".join(hypotheses)
        ),
        "formula": trial["operator_formula"],
        "direction": "higher_nonlinear_consensus_score_is_better",
        "feature_set": list(trial["feature_set"]),
        "window_transform_threshold_filter_and_weight_configuration": {
            "kind": trial["kind"],
            "operator": trial["operator"],
            "all_components_required": True,
            "daily_cross_sectional_rank_method": "average_percentile",
            "minimum_signal_names": base.MIN_SIGNAL_NAMES,
            "quality_maximum_age_days": 550,
            "minimum_listing_sessions": 20,
            "weight_fitting": False,
            "threshold_or_year_subset_search": False,
        },
        "training_and_validation_folds": folds,
        "data_and_code_fingerprints": {
            "campaign_preregistration": {
                "path": str(campaign_path),
                "sha256": campaign_sha,
            },
            "runner": {
                "path": str(Path(__file__).resolve()),
                "sha256": base.file_sha256(Path(__file__).resolve()),
            },
        },
        "fixed_execution_policy_fingerprints": campaign[
            "execution_policy_bindings"
        ],
        "training_metrics": [item["training_metrics"] for item in folds],
        "validation_metrics": [item["validation_metrics"] for item in folds],
        "development_aggregate_metrics": aggregate,
        "locked_backtest_metrics_when_opened": None,
        "status_and_rejection_reason": {
            "status": "development_walkforward_completed",
            "rejection_reason": None,
        },
        "candidate49_historical_return_read": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }


def _median(values: Iterable[float]) -> float:
    return float(statistics.median(float(value) for value in values))


def survivor_decision(
    entry: dict[str, Any], campaign: dict[str, Any]
) -> dict[str, Any]:
    rule = campaign["survivor_rule"]
    validations = list(entry.get("validation_metrics") or [])
    reasons: list[str] = []
    if len(validations) != len(campaign["walkforward_folds"]):
        reasons.append("incomplete_validation_fold_count")
    minimum_cohorts = int(rule["minimum_validation_association_cohorts_per_fold"])
    mean_ics: list[float] = []
    spreads: list[float] = []
    normalized_returns: list[float] = []
    pilot_returns: list[float] = []
    drawdowns: list[float] = []
    for index, result in enumerate(validations, start=1):
        association = result.get("association") or {}
        normalized = result.get("normalized_execution") or {}
        pilot = result.get("pilot_execution_primary_10bp") or {}
        if int(association.get("cohorts") or 0) < minimum_cohorts:
            reasons.append(f"fold_{index}_insufficient_association_cohorts")
        if int(normalized.get("terminal_unresolved_position_count") or 0) != 0:
            reasons.append(f"fold_{index}_normalized_unresolved_positions")
        if int(pilot.get("terminal_unresolved_position_count") or 0) != 0:
            reasons.append(f"fold_{index}_pilot_unresolved_positions")
        affordability = pilot.get("board_lot_affordability_rate")
        if (
            affordability is None
            or float(affordability)
            < float(rule["minimum_board_lot_affordability_rate_each_fold"])
        ):
            reasons.append(f"fold_{index}_board_lot_affordability")
        participation = pilot.get(
            "maximum_filled_trade_daily_amount_participation"
        )
        if (
            participation is None
            or float(participation)
            > float(rule["maximum_daily_amount_participation_each_fold"])
            or int(pilot.get("filled_trade_amount_missing_count") or 0) != 0
        ):
            reasons.append(f"fold_{index}_amount_participation")
        if association.get("mean_rank_ic") is not None:
            mean_ics.append(float(association["mean_rank_ic"]))
        if association.get("mean_top3_minus_bottom3_gross_return") is not None:
            spreads.append(
                float(association["mean_top3_minus_bottom3_gross_return"])
            )
        normalized_returns.append(float(normalized["net_cumulative_return"]))
        pilot_returns.append(float(pilot["net_cumulative_return"]))
        drawdowns.append(float(normalized["maximum_drawdown"]))
    positive_ic_folds = sum(value > 0.0 for value in mean_ics)
    positive_normalized_folds = sum(value > 0.0 for value in normalized_returns)
    positive_pilot_folds = sum(value > 0.0 for value in pilot_returns)
    quality_reasons: list[str] = []
    if len(mean_ics) != 3 or len(spreads) != 3:
        quality_reasons.append("incomplete_validation_association_metrics")
    else:
        if positive_ic_folds < int(rule["positive_ic_fold_count_gte"]):
            quality_reasons.append("insufficient_positive_ic_folds")
        if _median(mean_ics) <= float(rule["median_validation_mean_rank_ic_gt"]):
            quality_reasons.append("median_validation_mean_rank_ic")
        if _median(spreads) <= float(rule["median_validation_spread_gt"]):
            quality_reasons.append("median_validation_spread")
    if positive_normalized_folds < int(
        rule["positive_normalized_return_fold_count_gte"]
    ):
        quality_reasons.append("insufficient_positive_normalized_return_folds")
    if positive_pilot_folds < int(rule["positive_pilot_return_fold_count_gte"]):
        quality_reasons.append("insufficient_positive_pilot_return_folds")
    if pilot_returns and _median(pilot_returns) <= float(
        rule["median_validation_pilot_return_gt"]
    ):
        quality_reasons.append("median_validation_pilot_return")
    if drawdowns and min(drawdowns) < float(rule["worst_normalized_drawdown_gte"]):
        quality_reasons.append("worst_validation_normalized_drawdown")
    aggregate = entry.get("development_aggregate_metrics") or {}
    cost_20bp = (
        (aggregate.get("pilot_slippage_sensitivity") or {}).get("0.0020") or {}
    ).get("net_cumulative_return")
    if cost_20bp is None or float(cost_20bp) <= float(
        rule["development_aggregate_20bp_return_gt"]
    ):
        quality_reasons.append("nonpositive_development_aggregate_20bp_return")
    passed = not reasons and not quality_reasons
    return {
        "operationally_admissible": not reasons,
        "operational_rejection_reasons": reasons,
        "validation_quality_gate_passed": not quality_reasons,
        "validation_quality_rejection_reasons": quality_reasons,
        "development_survivor_gate_passed": passed,
        "positive_mean_rank_ic_fold_count": int(positive_ic_folds),
        "positive_normalized_return_fold_count": int(positive_normalized_folds),
        "positive_pilot_return_fold_count": int(positive_pilot_folds),
        "median_validation_mean_rank_ic": (
            _median(mean_ics) if mean_ics else -math.inf
        ),
        "median_validation_spread": (
            _median(spreads) if spreads else -math.inf
        ),
        "median_validation_normalized_return": (
            _median(normalized_returns) if normalized_returns else -math.inf
        ),
        "median_validation_pilot_return": (
            _median(pilot_returns) if pilot_returns else -math.inf
        ),
        "worst_validation_normalized_drawdown": (
            min(drawdowns) if drawdowns else -math.inf
        ),
        "development_aggregate_20bp_return": (
            float(cost_20bp) if cost_20bp is not None else -math.inf
        ),
        "complexity": 2,
    }


def build_survivor_record(
    campaign: dict[str, Any],
    campaign_path: Path,
    campaign_sha: str,
    ledger: dict[str, Any],
) -> dict[str, Any]:
    catalog = build_trial_catalog(campaign)
    development = {
        str(entry["trial_id"]): entry
        for entry in ledger["entries"]
        if entry.get("phase") == DEVELOPMENT_PHASE
    }
    if set(development) != {item["trial_id"] for item in catalog}:
        raise Campaign002Error("Campaign002 development ledger is incomplete")
    decisions = [
        {
            "trial_id": item["trial_id"],
            **survivor_decision(development[item["trial_id"]], campaign),
        }
        for item in catalog
    ]
    passing = [
        item for item in decisions if item["development_survivor_gate_passed"]
    ]
    ranked = sorted(
        passing,
        key=lambda item: (
            -int(item["positive_mean_rank_ic_fold_count"]),
            -int(item["positive_pilot_return_fold_count"]),
            -int(item["positive_normalized_return_fold_count"]),
            -float(item["median_validation_mean_rank_ic"]),
            -float(item["median_validation_pilot_return"]),
            -float(item["development_aggregate_20bp_return"]),
            -float(item["worst_validation_normalized_drawdown"]),
            str(item["trial_id"]),
        ),
    )
    maximum = int(campaign["survivor_rule"]["maximum_exposed_stress_survivors"])
    selected = [str(item["trial_id"]) for item in ranked[:maximum]]
    return {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign002_development_survivors",
        "status": "development_complete_survivors_frozen_before_exposed_stress",
        "campaign": {"path": str(campaign_path), "sha256": campaign_sha},
        "ledger_prefix": {
            "entry_count": len(ledger["entries"]),
            "chain_tip_sha256": ledger["chain_tip_sha256"],
            "entries_sha256": base.value_sha256(ledger["entries"]),
        },
        "survivor_rule": campaign["survivor_rule"],
        "trial_decisions": decisions,
        "ranked_gate_passing_trial_ids": [
            str(item["trial_id"]) for item in ranked
        ],
        "selected_exposed_stress_survivor_trial_ids": selected,
        "selected_survivor_count": len(selected),
        "created_at": max(str(entry["created_at"]) for entry in development.values()),
        "stress_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "current_scoring_selection_sizing_or_orders_allowed": False,
    }


def ensure_survivor_record(
    path: Path,
    campaign: dict[str, Any],
    campaign_path: Path,
    campaign_sha: str,
    ledger: dict[str, Any],
) -> dict[str, Any]:
    expected = build_survivor_record(
        campaign, campaign_path, campaign_sha, ledger
    )
    if path.exists():
        observed = base.load_json(path)
        if observed != expected:
            raise Campaign002Error("Campaign002 frozen survivor record changed")
        return observed
    base.atomic_write_json(path, expected)
    return base.load_json(path)


def _record_common_load_failure(
    ledger_path: Path,
    ledger: dict[str, Any],
    campaign_path: Path,
    campaign_sha: str,
    error: Exception,
) -> dict[str, Any]:
    existing = [
        entry
        for entry in ledger["entries"]
        if entry.get("phase") == "infrastructure_failure"
    ]
    trial_id = f"wf002_infrastructure__development_phase_load_{len(existing) + 1:03d}"
    return append_ledger_entry(
        ledger_path,
        ledger,
        {
            "trial_id": trial_id,
            "parent_trial_id": None,
            "campaign_id": CAMPAIGN_ID,
            "phase": "infrastructure_failure",
            "created_at": base.utc_now(),
            "economic_hypothesis": "infrastructure-only failure before trial evaluation",
            "formula": None,
            "direction": None,
            "feature_set": [],
            "window_transform_threshold_filter_and_weight_configuration": None,
            "training_and_validation_folds": [],
            "data_and_code_fingerprints": {
                "campaign_preregistration": {
                    "path": str(campaign_path),
                    "sha256": campaign_sha,
                }
            },
            "fixed_execution_policy_fingerprints": {},
            "training_metrics": [],
            "validation_metrics": [],
            "locked_backtest_metrics_when_opened": None,
            "status_and_rejection_reason": {
                "status": "infrastructure_failed",
                "rejection_reason": f"{type(error).__name__}: {error}",
            },
            "candidate49_historical_return_read": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
        },
        campaign_path,
        campaign_sha,
    )


def run_development(args: argparse.Namespace) -> dict[str, Any]:
    campaign_path = Path(args.campaign).expanduser().resolve()
    campaign, _spec, campaign_sha = load_campaign(campaign_path)
    output_root = Path(args.output_root).expanduser().resolve()
    ledger_path = output_root / LEDGER_FILENAME
    survivor_path = output_root / SURVIVOR_FILENAME
    if (output_root / STRESS_INTENT_FILENAME).exists():
        raise Campaign002Error(
            "development cannot run after exposed stress replay was opened"
        )
    ledger = load_or_initialize_ledger(
        ledger_path, campaign_path, campaign_sha
    )
    catalog = build_trial_catalog(campaign)
    existing = {
        str(entry["trial_id"])
        for entry in ledger["entries"]
        if entry.get("phase") == DEVELOPMENT_PHASE
    }
    expected = {str(item["trial_id"]) for item in catalog}
    if existing - expected:
        raise Campaign002Error("development ledger contains unexpected trials")
    if existing == expected:
        survivors = ensure_survivor_record(
            survivor_path, campaign, campaign_path, campaign_sha, ledger
        )
        return {
            "status": "development_already_complete_idempotent",
            "trial_count": len(existing),
            "survivor_count": survivors["selected_survivor_count"],
            "ledger_path": str(ledger_path),
            "survivor_path": str(survivor_path),
            "exposed_stress_return_fields_read": False,
        }
    print(
        "loading 2019-2023 market, quality, and complete frozen factor panels",
        flush=True,
    )
    try:
        panel, quotes, calendar, schedule = base.prepare_phase_data(
            campaign,
            phase_end="2023-12-31",
            target_start="2019-01-01",
            years=range(2019, 2024),
            batch_size=int(args.batch_size),
        )
    except Exception as error:
        _record_common_load_failure(
            ledger_path,
            ledger,
            campaign_path,
            campaign_sha,
            error,
        )
        raise Campaign002Error(
            f"development phase data load failed and was recorded: {error}"
        ) from error
    created_at = base.utc_now()
    for index, trial in enumerate(catalog, start=1):
        if trial["trial_id"] in existing:
            continue
        try:
            payload = development_trial_payload(
                campaign,
                campaign_path,
                campaign_sha,
                trial,
                panel,
                quotes,
                calendar,
                schedule,
                created_at,
            )
        except Exception as error:
            payload = {
                "trial_id": trial["trial_id"],
                "parent_trial_id": trial["parent_trial_id"],
                "campaign_id": CAMPAIGN_ID,
                "phase": DEVELOPMENT_PHASE,
                "created_at": created_at,
                "economic_hypothesis": "frozen trial failed before complete metrics",
                "formula": trial["operator_formula"],
                "direction": "higher_nonlinear_consensus_score_is_better",
                "feature_set": list(trial["feature_set"]),
                "window_transform_threshold_filter_and_weight_configuration": {
                    "kind": trial["kind"],
                    "operator": trial["operator"],
                },
                "training_and_validation_folds": [],
                "data_and_code_fingerprints": {
                    "campaign_preregistration": {
                        "path": str(campaign_path),
                        "sha256": campaign_sha,
                    }
                },
                "fixed_execution_policy_fingerprints": campaign[
                    "execution_policy_bindings"
                ],
                "training_metrics": [],
                "validation_metrics": [],
                "development_aggregate_metrics": {},
                "locked_backtest_metrics_when_opened": None,
                "status_and_rejection_reason": {
                    "status": "infrastructure_failed",
                    "rejection_reason": f"{type(error).__name__}: {error}",
                },
                "candidate49_historical_return_read": False,
                "current_scoring_selection_sizing_or_orders_performed": False,
            }
        ledger = append_ledger_entry(
            ledger_path,
            ledger,
            payload,
            campaign_path,
            campaign_sha,
        )
        print(f"recorded Campaign002 development trial {index}/84", flush=True)
    survivors = ensure_survivor_record(
        survivor_path, campaign, campaign_path, campaign_sha, ledger
    )
    return {
        "status": "development_completed",
        "trial_count": len(catalog),
        "survivor_count": survivors["selected_survivor_count"],
        "ledger_path": str(ledger_path),
        "ledger_sha256": base.file_sha256(ledger_path),
        "survivor_path": str(survivor_path),
        "survivor_sha256": base.file_sha256(survivor_path),
        "exposed_stress_return_fields_read": False,
        "candidate49_historical_return_read": False,
    }


def exposed_stress_trial_payload(
    campaign: dict[str, Any],
    campaign_path: Path,
    campaign_sha: str,
    survivor_record: dict[str, Any],
    original_entry: dict[str, Any],
    trial: dict[str, Any],
    panel: pd.DataFrame,
    quotes: Any,
    calendar: pd.DatetimeIndex,
    schedule: pd.DataFrame,
    created_at: str,
) -> dict[str, Any]:
    purge = int(campaign["split_protocol"]["purge_signal_sessions_each_boundary"])
    combined = evaluate_trial_period(
        panel,
        quotes,
        calendar,
        schedule,
        trial,
        "2024-01-01",
        "2025-12-31",
        purge,
        include_sensitivity=True,
    )
    yearly = {
        str(year): evaluate_trial_period(
            panel,
            quotes,
            calendar,
            schedule,
            trial,
            f"{year}-01-01",
            f"{year}-12-31",
            purge,
            include_sensitivity=False,
        )
        for year in (2024, 2025)
    }
    gate = campaign["exposed_stress_replay"]["frozen_comparison_gates"]
    association = combined["association"]
    normalized = combined["normalized_execution"]
    pilot = combined["pilot_execution_primary_10bp"]
    failures: list[str] = []
    if (association.get("mean_rank_ic") or -math.inf) <= float(
        gate["mean_rank_ic_gt"]
    ):
        failures.append("nonpositive_stress_mean_rank_ic")
    if (association.get("positive_rank_ic_rate") or -math.inf) <= float(
        gate["positive_rank_ic_rate_gt"]
    ):
        failures.append("stress_positive_rank_ic_rate_not_above_half")
    if (
        association.get("mean_top3_minus_bottom3_gross_return") or -math.inf
    ) <= float(gate["mean_top3_minus_bottom3_spread_gt"]):
        failures.append("nonpositive_stress_top3_minus_bottom3_spread")
    if not all(
        (yearly[str(year)]["association"]["mean_rank_ic"] or -math.inf)
        > float(gate["each_year_mean_rank_ic_gt"])
        for year in (2024, 2025)
    ):
        failures.append("nonpositive_stress_annual_mean_rank_ic")
    if normalized["net_cumulative_return"] <= float(
        gate["normalized_return_gt"]
    ):
        failures.append("nonpositive_stress_normalized_return")
    if normalized["maximum_drawdown"] < float(
        gate["normalized_drawdown_gte"]
    ):
        failures.append("stress_normalized_drawdown_below_limit")
    if not all(
        yearly[str(year)]["normalized_execution"]["net_cumulative_return"]
        > float(gate["each_year_normalized_return_gt"])
        for year in (2024, 2025)
    ):
        failures.append("nonpositive_stress_annual_normalized_return")
    if normalized["terminal_unresolved_position_count"] != 0:
        failures.append("stress_normalized_terminal_unresolved")
    if pilot["net_cumulative_return"] <= float(gate["pilot_10bp_return_gt"]):
        failures.append("nonpositive_stress_pilot_10bp_return")
    sensitivity_20bp = (
        combined["pilot_slippage_sensitivity"]["0.0020"]["net_cumulative_return"]
    )
    if sensitivity_20bp <= float(gate["pilot_20bp_return_gt"]):
        failures.append("nonpositive_stress_pilot_20bp_return")
    if not all(
        yearly[str(year)]["pilot_execution_primary_10bp"]["net_cumulative_return"]
        > float(gate["each_year_pilot_10bp_return_gt"])
        for year in (2024, 2025)
    ):
        failures.append("nonpositive_stress_annual_pilot_return")
    if (pilot["board_lot_affordability_rate"] or 0.0) < float(
        gate["board_lot_affordability_gte"]
    ):
        failures.append("stress_board_lot_affordability_below_limit")
    if (
        pilot["maximum_filled_trade_daily_amount_participation"]
        > float(gate["maximum_daily_amount_participation_lte"])
        or pilot["filled_trade_amount_missing_count"] != 0
    ):
        failures.append("stress_amount_participation_or_missing_amount")
    if pilot["terminal_unresolved_position_count"] != 0:
        failures.append("stress_pilot_terminal_unresolved")
    return {
        "trial_id": f"{trial['trial_id']}::exposed_stress_2024_2025",
        "parent_trial_id": trial["trial_id"],
        "campaign_id": CAMPAIGN_ID,
        "phase": STRESS_PHASE,
        "created_at": created_at,
        "economic_hypothesis": original_entry["economic_hypothesis"],
        "formula": original_entry["formula"],
        "direction": original_entry["direction"],
        "feature_set": list(trial["feature_set"]),
        "window_transform_threshold_filter_and_weight_configuration": original_entry[
            "window_transform_threshold_filter_and_weight_configuration"
        ],
        "training_and_validation_folds": original_entry[
            "training_and_validation_folds"
        ],
        "data_and_code_fingerprints": {
            "campaign_preregistration": {
                "path": str(campaign_path),
                "sha256": campaign_sha,
            },
            "survivor_record_sha256": base.value_sha256(survivor_record),
            "runner": {
                "path": str(Path(__file__).resolve()),
                "sha256": base.file_sha256(Path(__file__).resolve()),
            },
        },
        "fixed_execution_policy_fingerprints": campaign[
            "execution_policy_bindings"
        ],
        "training_metrics": original_entry["training_metrics"],
        "validation_metrics": original_entry["validation_metrics"],
        "locked_backtest_metrics_when_opened": {
            "classification": "historically_exposed_stress_replay_not_unseen",
            "combined_2024_2025": combined,
            "standalone_year_replays": yearly,
            "frozen_comparison_gate": {
                "passed": not failures,
                "failures": failures,
                "historical_pass_can_directly_promote_or_select": False,
            },
        },
        "status_and_rejection_reason": {
            "status": (
                "exposed_stress_gate_passed_research_only"
                if not failures
                else "exposed_stress_gate_rejected"
            ),
            "rejection_reason": failures or None,
        },
        "candidate49_historical_return_read": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }


def write_report(
    path: Path,
    campaign: dict[str, Any],
    campaign_sha: str,
    ledger: dict[str, Any],
    survivors: dict[str, Any],
    stress_record: dict[str, Any] | None,
) -> None:
    development = [
        entry for entry in ledger["entries"] if entry.get("phase") == DEVELOPMENT_PHASE
    ]
    failures = [
        entry
        for entry in ledger["entries"]
        if (entry.get("status_and_rejection_reason") or {}).get("status")
        == "infrastructure_failed"
    ]
    base.atomic_write_json(
        path,
        {
            "version": 1,
            "kind": "a_share_three_day_walkforward_campaign002_report",
            "campaign_id": CAMPAIGN_ID,
            "campaign_sha256": campaign_sha,
            "classification": (
                "development_walkforward_plus_historically_exposed_stress_replay"
            ),
            "development_trial_count": len(development),
            "infrastructure_failure_count": len(failures),
            "development_gate_passer_count": len(
                survivors["ranked_gate_passing_trial_ids"]
            ),
            "selected_exposed_stress_survivor_count": survivors[
                "selected_survivor_count"
            ],
            "selected_exposed_stress_survivor_trial_ids": survivors[
                "selected_exposed_stress_survivor_trial_ids"
            ],
            "exposed_stress": stress_record,
            "ledger": {
                "path": str(path.parent / LEDGER_FILENAME),
                "entry_count": len(ledger["entries"]),
                "chain_tip_sha256": ledger["chain_tip_sha256"],
            },
            "prior_terminal_factor_conclusions_changed": False,
            "candidate49": {
                "historical_return_read": False,
                "prospective_registration_or_ledgers_changed": False,
            },
            "candidate50_prospective_activation_created": False,
            "current_scoring_selection_sizing_or_orders_allowed": False,
            "limitations": [
                "2019-2025 outcomes are historically exposed, not pristine.",
                (
                    "The local holding universe derives from a current listing "
                    "snapshot and may contain survivorship bias."
                ),
                (
                    "This campaign is exploratory because it follows prior use "
                    "of the same market interval and factor definitions."
                ),
            ],
        },
    )


def run_exposed_stress(args: argparse.Namespace) -> dict[str, Any]:
    if not args.confirm_exposed_stress:
        raise Campaign002Error(
            "run-exposed-stress requires --confirm-exposed-stress"
        )
    campaign_path = Path(args.campaign).expanduser().resolve()
    campaign, _spec, campaign_sha = load_campaign(campaign_path)
    output_root = Path(args.output_root).expanduser().resolve()
    ledger_path = output_root / LEDGER_FILENAME
    survivor_path = output_root / SURVIVOR_FILENAME
    intent_path = output_root / STRESS_INTENT_FILENAME
    record_path = output_root / STRESS_RECORD_FILENAME
    ledger = validate_ledger(
        base.load_json(ledger_path), campaign_path, campaign_sha
    )
    survivors = ensure_survivor_record(
        survivor_path, campaign, campaign_path, campaign_sha, ledger
    )
    if record_path.exists():
        record = base.load_json(record_path)
        if (
            record.get("campaign_sha256") != campaign_sha
            or record.get("survivor_record_sha256")
            != base.file_sha256(survivor_path)
            or record.get("status") != "exposed_stress_replay_consumed_once_complete"
        ):
            raise Campaign002Error("existing exposed stress record changed")
        return {
            "status": "exposed_stress_already_consumed_idempotent",
            "record_path": str(record_path),
            "record_sha256": base.file_sha256(record_path),
        }
    selected_ids = list(
        survivors["selected_exposed_stress_survivor_trial_ids"]
    )
    if not selected_ids:
        record = {
            "version": 1,
            "kind": "a_share_three_day_walkforward_campaign002_exposed_stress_record",
            "status": "exposed_stress_replay_consumed_once_complete",
            "campaign_sha256": campaign_sha,
            "survivor_record_sha256": base.file_sha256(survivor_path),
            "stress_interval_opened": False,
            "reason": "zero_development_survivors",
            "selected_survivor_trial_ids": [],
            "completed_stress_trial_ids": [],
            "frozen_gate_passer_trial_ids": [],
            "research_only_lead_trial_id": None,
            "candidate49_historical_return_read": False,
            "current_scoring_selection_sizing_or_orders_allowed": False,
        }
        base.atomic_write_json(record_path, record)
        write_report(
            output_root / REPORT_FILENAME,
            campaign,
            campaign_sha,
            ledger,
            survivors,
            record,
        )
        return {
            "status": "exposed_stress_not_opened_zero_development_survivors",
            "record_path": str(record_path),
            "record_sha256": base.file_sha256(record_path),
        }
    expected_intent_core = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign002_exposed_stress_intent",
        "status": "opened_once_pending_completion",
        "campaign_sha256": campaign_sha,
        "survivor_record_sha256": base.file_sha256(survivor_path),
        "runner_sha256": base.file_sha256(Path(__file__).resolve()),
        "stress_start": "2024-01-01",
        "stress_end": "2025-12-31",
        "classification": "historically_exposed_stress_replay_not_unseen",
        "candidate49_historical_return_read": False,
    }
    if intent_path.exists():
        intent = base.load_json(intent_path)
        for key, value in expected_intent_core.items():
            if intent.get(key) != value:
                raise Campaign002Error("exposed stress intent changed")
    else:
        intent = {**expected_intent_core, "opened_at": base.utc_now()}
        base.atomic_write_json(intent_path, intent)
    print(
        "exposed stress intent frozen; loading historically exposed 2024-2025",
        flush=True,
    )
    panel, quotes, calendar, schedule = base.prepare_phase_data(
        campaign,
        phase_end="2025-12-31",
        target_start="2024-01-01",
        years=(2024, 2025),
        batch_size=int(args.batch_size),
    )
    catalog = {item["trial_id"]: item for item in build_trial_catalog(campaign)}
    development = {
        str(entry["trial_id"]): entry
        for entry in ledger["entries"]
        if entry.get("phase") == DEVELOPMENT_PHASE
    }
    created_at = str(intent["opened_at"])
    for index, trial_id in enumerate(selected_ids, start=1):
        stress_id = f"{trial_id}::exposed_stress_2024_2025"
        if any(entry["trial_id"] == stress_id for entry in ledger["entries"]):
            continue
        payload = exposed_stress_trial_payload(
            campaign,
            campaign_path,
            campaign_sha,
            survivors,
            development[trial_id],
            catalog[trial_id],
            panel,
            quotes,
            calendar,
            schedule,
            created_at,
        )
        ledger = append_ledger_entry(
            ledger_path,
            ledger,
            payload,
            campaign_path,
            campaign_sha,
        )
        print(
            f"recorded Campaign002 exposed stress survivor "
            f"{index}/{len(selected_ids)}",
            flush=True,
        )
    stress_entries = [
        entry
        for entry in ledger["entries"]
        if entry.get("phase") == STRESS_PHASE
        and entry.get("parent_trial_id") in selected_ids
    ]
    if len(stress_entries) != len(selected_ids):
        raise Campaign002Error("exposed stress ledger is incomplete")
    passers = [
        entry
        for entry in stress_entries
        if (
            (entry.get("locked_backtest_metrics_when_opened") or {})
            .get("frozen_comparison_gate", {})
            .get("passed")
        )
    ]
    ranked_entries = sorted(
        stress_entries,
        key=lambda entry: (
            len(
                (
                    entry["locked_backtest_metrics_when_opened"][
                        "frozen_comparison_gate"
                    ]["failures"]
                    or []
                )
            ),
            -float(
                entry["locked_backtest_metrics_when_opened"][
                    "combined_2024_2025"
                ]["association"]["mean_rank_ic"]
                or -math.inf
            ),
            -float(
                entry["locked_backtest_metrics_when_opened"][
                    "combined_2024_2025"
                ]["pilot_execution_primary_10bp"]["net_cumulative_return"]
            ),
            str(entry["parent_trial_id"]),
        ),
    )
    lead = str(ranked_entries[0]["parent_trial_id"]) if ranked_entries else None
    record = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign002_exposed_stress_record",
        "status": "exposed_stress_replay_consumed_once_complete",
        "campaign_sha256": campaign_sha,
        "survivor_record_sha256": base.file_sha256(survivor_path),
        "stress_intent_sha256": base.file_sha256(intent_path),
        "stress_interval_opened": True,
        "classification": "historically_exposed_stress_replay_not_unseen",
        "ledger": {
            "path": str(ledger_path),
            "entry_count": len(ledger["entries"]),
            "chain_tip_sha256": ledger["chain_tip_sha256"],
            "file_sha256": base.file_sha256(ledger_path),
        },
        "selected_survivor_trial_ids": selected_ids,
        "completed_stress_trial_ids": [
            str(entry["parent_trial_id"]) for entry in stress_entries
        ],
        "frozen_gate_passer_trial_ids": [
            str(entry["parent_trial_id"]) for entry in passers
        ],
        "research_only_lead_trial_id": lead,
        "opened_at": intent["opened_at"],
        "completed_at": base.utc_now(),
        "candidate49_historical_return_read": False,
        "candidate50_prospective_activation_created": False,
        "current_scoring_selection_sizing_or_orders_allowed": False,
    }
    base.atomic_write_json(record_path, record)
    write_report(
        output_root / REPORT_FILENAME,
        campaign,
        campaign_sha,
        ledger,
        survivors,
        record,
    )
    return {
        "status": "exposed_stress_replay_consumed_once_complete",
        "survivor_count": len(selected_ids),
        "frozen_gate_passer_count": len(passers),
        "research_only_lead_trial_id": lead,
        "record_path": str(record_path),
        "record_sha256": base.file_sha256(record_path),
        "report_path": str(output_root / REPORT_FILENAME),
    }


def status(args: argparse.Namespace) -> dict[str, Any]:
    campaign_path = Path(args.campaign).expanduser().resolve()
    campaign, _spec, campaign_sha = load_campaign(campaign_path)
    output_root = Path(args.output_root).expanduser().resolve()
    result: dict[str, Any] = {
        "status": "campaign002_frozen_pending_development",
        "campaign_path": str(campaign_path),
        "campaign_sha256": campaign_sha,
        "expected_trial_count": len(build_trial_catalog(campaign)),
        "candidate49_historical_return_read": False,
        "evidence_classification": "historically_exposed_exploratory",
    }
    ledger_path = output_root / LEDGER_FILENAME
    if ledger_path.exists():
        ledger = validate_ledger(
            base.load_json(ledger_path), campaign_path, campaign_sha
        )
        result.update(
            {
                "ledger_entry_count": len(ledger["entries"]),
                "ledger_chain_tip_sha256": ledger["chain_tip_sha256"],
                "development_trial_count": sum(
                    entry.get("phase") == DEVELOPMENT_PHASE
                    for entry in ledger["entries"]
                ),
                "exposed_stress_trial_count": sum(
                    entry.get("phase") == STRESS_PHASE
                    for entry in ledger["entries"]
                ),
                "infrastructure_failure_count": sum(
                    entry.get("phase") == "infrastructure_failure"
                    for entry in ledger["entries"]
                ),
                "status": "development_in_progress_or_complete",
            }
        )
    survivor_path = output_root / SURVIVOR_FILENAME
    if survivor_path.exists():
        survivors = base.load_json(survivor_path)
        result["survivor_count"] = survivors["selected_survivor_count"]
        result["status"] = "survivors_frozen_exposed_stress_unopened"
    if (output_root / STRESS_INTENT_FILENAME).exists():
        result["status"] = "exposed_stress_opened_pending_completion"
    record_path = output_root / STRESS_RECORD_FILENAME
    if record_path.exists():
        record = base.load_json(record_path)
        result["status"] = record["status"]
        result["frozen_gate_passer_trial_ids"] = record[
            "frozen_gate_passer_trial_ids"
        ]
        result["research_only_lead_trial_id"] = record[
            "research_only_lead_trial_id"
        ]
    return result


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--campaign", default=str(DEFAULT_CAMPAIGN))
    value.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    subcommands = value.add_subparsers(dest="command", required=True)
    subcommands.add_parser("status")
    development = subcommands.add_parser("run-development")
    development.add_argument("--batch-size", type=int, default=100)
    stress = subcommands.add_parser("run-exposed-stress")
    stress.add_argument("--batch-size", type=int, default=100)
    stress.add_argument("--confirm-exposed-stress", action="store_true")
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "status":
            result = status(args)
        elif args.command == "run-development":
            result = run_development(args)
        elif args.command == "run-exposed-stress":
            result = run_exposed_stress(args)
        else:
            raise Campaign002Error(f"unsupported command: {args.command}")
    except (
        Campaign002Error,
        base.WalkForwardError,
        ValueError,
        FileNotFoundError,
    ) as error:
        print(
            base.json.dumps(
                {"status": "failed", "error": str(error)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    print(
        base.json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            default=research._json_default,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
