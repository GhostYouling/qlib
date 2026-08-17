#!/usr/bin/env python3
"""Run the finite Campaign004 three-session historical walk-forward study.

The exact admissible feature list and every single/pair rank blend are frozen
in the Campaign004 preregistration before this runner may read daily prices or
forward outcomes.  Development uses only 2019-2023.  The historically exposed
2024-2025 stress interval remains closed until development survivors are
frozen.  Candidate49 is never included or historically backfilled.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_three_day_walkforward_campaign as base  # noqa: E402
import a_share_three_day_walkforward_campaign002 as campaign002  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CAMPAIGN = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_004_preregistration.json"
)
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT
    / "data"
    / "experiments"
    / "short_horizon"
    / "historical_walkforward"
    / "campaign_004"
    / "walkforward"
)
LEDGER_FILENAME = "trial_ledger.json"
SURVIVOR_FILENAME = "development_survivors.json"
STRESS_INTENT_FILENAME = "exposed_stress_open_intent.json"
STRESS_RECORD_FILENAME = "exposed_stress_consumption_record.json"
REPORT_FILENAME = "campaign_report.json"
CAMPAIGN_ID = "a_share_three_day_walkforward_campaign_004"
LEDGER_KIND = "a_share_three_day_historical_walkforward_campaign004_trial_ledger"
CHAIN_GENESIS = "0" * 64
DEVELOPMENT_PHASE = "development_walkforward_2019_2023"
STRESS_PHASE = "historically_exposed_stress_replay_2024_2025"
PAIR_WEIGHTS = ([0.25, 0.75], [0.50, 0.50], [0.75, 0.25])


class Campaign004Error(RuntimeError):
    """Fail-closed Campaign004 walk-forward error."""


def _validate_binding(binding: dict[str, Any], label: str) -> Path:
    try:
        return base.validate_file_binding(binding, label)
    except base.WalkForwardError as error:
        raise Campaign004Error(str(error)) from error


def build_trial_catalog(campaign: dict[str, Any]) -> list[dict[str, Any]]:
    factors = sorted(
        str(item.get("name") or "") for item in campaign.get("factor_library") or []
    )
    if (
        not factors
        or len(factors) > 3
        or len(factors) != len(set(factors))
        or any(not factor for factor in factors)
        or "intraday_cumulative_vwap_crossing_rate_240m" in factors
    ):
        raise Campaign004Error("Campaign004 admissible factor library is invalid")
    search = campaign.get("search_space") or {}
    if list(search.get("admissible_factor_names_canonical") or []) != factors:
        raise Campaign004Error("Campaign004 canonical factor order changed")
    if list(search.get("pair_weight_grid_for_canonical_factor_order") or []) != list(
        PAIR_WEIGHTS
    ):
        raise Campaign004Error("Campaign004 pair weight grid changed")
    trials: list[dict[str, Any]] = []
    for factor in factors:
        trials.append(
            {
                "trial_id": f"wf004_single__{factor}",
                "parent_trial_id": None,
                "kind": "single_factor",
                "feature_set": [factor],
                "weights": [1.0],
                "complexity": 1,
            }
        )
    for left_index, left in enumerate(factors):
        for right in factors[left_index + 1 :]:
            for left_weight, right_weight in PAIR_WEIGHTS:
                suffix = (
                    f"w{round(left_weight * 100):02d}_"
                    f"{round(right_weight * 100):02d}"
                )
                trials.append(
                    {
                        "trial_id": (
                            f"wf004_pair__{left}__{right}__{suffix}"
                        ),
                        "parent_trial_id": None,
                        "kind": "pair_rank_blend",
                        "feature_set": [left, right],
                        "weights": [left_weight, right_weight],
                        "complexity": 2,
                    }
                )
    expected = len(factors) + 3 * (len(factors) * (len(factors) - 1) // 2)
    if (
        len(trials) != expected
        or len(trials) != int(search.get("expected_trial_count", -1))
        or len({str(item["trial_id"]) for item in trials}) != len(trials)
    ):
        raise Campaign004Error("Campaign004 finite trial catalog changed")
    return trials


def load_campaign(path: Path) -> tuple[dict[str, Any], str]:
    path = path.expanduser().resolve()
    spec = base.load_json(path)
    if (
        spec.get("version") != 1
        or spec.get("kind")
        != "a_share_three_day_walkforward_campaign004_preregistration"
        or spec.get("campaign_id") != CAMPAIGN_ID
        or spec.get("status")
        != "frozen_before_campaign004_2019_2023_development_return_read"
    ):
        raise Campaign004Error("Campaign004 preregistration header is invalid")
    allowed = {
        "version",
        "kind",
        "campaign_id",
        "status",
        "frozen_at",
        "purpose",
        "evidence_classification",
        "governance_bindings",
        "campaign003_bindings",
        "no_return_bindings",
        "implementation",
        "daily_data_bindings",
        "execution_policy_bindings",
        "factor_library",
        "search_space",
        "walkforward_folds",
        "split_protocol",
        "survivor_rule",
        "exposed_stress_replay",
        "candidate49_boundary",
        "research_output_boundary",
    }
    unexpected = sorted(set(spec) - allowed)
    if unexpected:
        raise Campaign004Error(
            "Campaign004 preregistration has unexpected fields: "
            + ", ".join(unexpected)
        )
    for group_name in (
        "governance_bindings",
        "campaign003_bindings",
        "no_return_bindings",
        "daily_data_bindings",
        "execution_policy_bindings",
    ):
        for name, binding in sorted((spec.get(group_name) or {}).items()):
            if (binding or {}).get("kind") == "directory":
                directory = base.resolve_bound_path(
                    str((binding or {}).get("path") or "")
                )
                if not directory.is_dir():
                    raise Campaign004Error(
                        f"{group_name}.{name} directory is missing: {directory}"
                    )
            else:
                _validate_binding(binding, f"{group_name}.{name}")
    implementation = spec.get("implementation") or {}
    if set(implementation) != {
        "script",
        "development_command",
        "exposed_stress_command",
        "output_root",
    }:
        raise Campaign004Error("Campaign004 implementation binding is incomplete")
    runner = _validate_binding(implementation["script"], "Campaign004 runner")
    if runner != Path(__file__).resolve():
        raise Campaign004Error("Campaign004 runner binding identifies another file")

    no_return_path = _validate_binding(
        (spec.get("no_return_bindings") or {}).get("audit") or {},
        "Campaign004 no-return audit",
    )
    no_return = base.load_json(no_return_path)
    admissible = sorted(str(value) for value in no_return.get("admissible_factor_names") or [])
    if (
        no_return.get("kind")
        != "a_share_three_day_walkforward_campaign004_no_return_audit"
        or no_return.get("status")
        != "completed_with_admissible_factors_pending_walkforward_preregistration"
        or not admissible
        or len(admissible) > 3
        or int(no_return.get("admissible_factor_count") or 0) != len(admissible)
        or no_return.get("historical_forward_return_fields_read") is not False
        or no_return.get("candidate49_historical_return_read") is not False
    ):
        raise Campaign004Error("Campaign004 no-return audit is not admissible")
    factor_library = list(spec.get("factor_library") or [])
    factor_names = sorted(str(item.get("name") or "") for item in factor_library)
    if (
        factor_names != admissible
        or len(factor_library) != len(admissible)
        or any(item.get("direction") != "higher" for item in factor_library)
        or any(
            item.get("dataset_group") != "campaign004_new_factors"
            for item in factor_library
        )
        or any(
            not Path(str(item.get("partition_root") or "")).is_absolute()
            for item in factor_library
        )
    ):
        raise Campaign004Error("Campaign004 factor library changed from no-return audit")
    for factor in factor_library:
        for index, binding in enumerate(factor.get("bindings") or []):
            _validate_binding(
                binding,
                f"factor_library.{factor.get('name')}.bindings[{index}]",
            )

    campaign003_path = _validate_binding(
        (spec.get("campaign003_bindings") or {}).get("preregistration") or {},
        "Campaign003 preregistration",
    )
    campaign003 = base.load_json(campaign003_path)
    for key in (
        "walkforward_folds",
        "split_protocol",
        "survivor_rule",
        "exposed_stress_replay",
    ):
        if spec.get(key) != campaign003.get(key):
            raise Campaign004Error(f"Campaign004 changed frozen {key}")
    boundary = spec.get("candidate49_boundary") or {}
    if (
        boundary.get("included_in_feature_library") is not False
        or boundary.get("historical_return_read_allowed") is not False
        or boundary.get("prospective_ledgers_changed_by_campaign") is not False
    ):
        raise Campaign004Error("Candidate49 boundary is not fail-closed")
    output = spec.get("research_output_boundary") or {}
    if not all(
        output.get(key) is False
        for key in (
            "current_scoring_allowed",
            "selection_allowed",
            "sizing_allowed",
            "orders_allowed",
            "prospective_candidate_activation_allowed",
        )
    ):
        raise Campaign004Error("Campaign004 output boundary is not closed")
    search = spec.get("search_space") or {}
    if (
        search.get("weight_fitting") is not False
        or search.get("threshold_search") is not False
        or search.get("year_subset_search") is not False
        or search.get("filter_search") is not False
        or search.get("triple_or_higher_order_combinations") is not False
        or search.get("record_every_trial_and_infrastructure_failure") is not True
    ):
        raise Campaign004Error("Campaign004 finite search boundary changed")
    build_trial_catalog(spec)
    return spec, base.file_sha256(path)


def _empty_ledger(campaign_path: Path, campaign_sha: str) -> dict[str, Any]:
    return {
        "version": 1,
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


def _entry_payload(entry: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in entry.items() if key != "entry_sha256"}


def _validate_ledger(
    ledger: dict[str, Any],
    campaign_path: Path,
    campaign_sha: str,
) -> dict[str, Any]:
    campaign = ledger.get("campaign") or {}
    if not (
        ledger.get("version") == 1
        and ledger.get("kind") == LEDGER_KIND
        and ledger.get("append_only") is True
        and ledger.get("chain_genesis") == CHAIN_GENESIS
        and campaign.get("path") == str(campaign_path)
        and campaign.get("sha256") == campaign_sha
        and campaign.get("campaign_id") == CAMPAIGN_ID
    ):
        raise Campaign004Error("Campaign004 trial ledger header changed")
    previous = CHAIN_GENESIS
    identifiers: set[str] = set()
    for ordinal, entry in enumerate(ledger.get("entries") or [], start=1):
        identifier = str(entry.get("trial_id") or "")
        digest = base.value_sha256(_entry_payload(entry))
        if (
            entry.get("ordinal") != ordinal
            or entry.get("previous_entry_sha256") != previous
            or not identifier
            or identifier in identifiers
            or entry.get("entry_sha256") != digest
        ):
            raise Campaign004Error("Campaign004 trial ledger chain changed")
        identifiers.add(identifier)
        previous = digest
    if ledger.get("chain_tip_sha256") != previous:
        raise Campaign004Error("Campaign004 trial ledger tip changed")
    return ledger


def _load_or_initialize_ledger(
    path: Path,
    campaign_path: Path,
    campaign_sha: str,
) -> dict[str, Any]:
    if path.exists():
        return _validate_ledger(
            base.load_json(path),
            campaign_path,
            campaign_sha,
        )
    ledger = _empty_ledger(campaign_path, campaign_sha)
    base.atomic_write_json(path, ledger)
    return ledger


def _append_ledger_entry(
    path: Path,
    ledger: dict[str, Any],
    payload: dict[str, Any],
    campaign_path: Path,
    campaign_sha: str,
) -> dict[str, Any]:
    _validate_ledger(ledger, campaign_path, campaign_sha)
    existing = {
        str(item["trial_id"]): item for item in ledger.get("entries") or []
    }
    trial_id = str(payload.get("trial_id") or "")
    if trial_id in existing:
        candidate = dict(payload)
        candidate["ordinal"] = existing[trial_id]["ordinal"]
        candidate["previous_entry_sha256"] = existing[trial_id][
            "previous_entry_sha256"
        ]
        candidate["entry_sha256"] = base.value_sha256(_entry_payload(candidate))
        if candidate != existing[trial_id]:
            raise Campaign004Error(f"existing Campaign004 trial changed: {trial_id}")
        return ledger
    entry = dict(payload)
    entry["ordinal"] = len(ledger["entries"]) + 1
    entry["previous_entry_sha256"] = ledger["chain_tip_sha256"]
    entry["entry_sha256"] = base.value_sha256(_entry_payload(entry))
    updated = dict(ledger)
    updated["entries"] = [*ledger["entries"], entry]
    updated["chain_tip_sha256"] = entry["entry_sha256"]
    base.atomic_write_json(path, updated)
    return _validate_ledger(base.load_json(path), campaign_path, campaign_sha)


def _development_payload(
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
    payload = base.development_trial_payload(
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
    payload["phase"] = DEVELOPMENT_PHASE
    payload["data_and_code_fingerprints"]["runner"] = {
        "path": str(Path(__file__).resolve()),
        "sha256": base.file_sha256(Path(__file__).resolve()),
    }
    return payload


def _failure_payload(
    *,
    campaign: dict[str, Any],
    campaign_path: Path,
    campaign_sha: str,
    trial: dict[str, Any] | None,
    error: Exception,
    ordinal_hint: int,
) -> dict[str, Any]:
    if trial is None:
        trial_id = f"wf004_infrastructure__development_load_{ordinal_hint:03d}"
        phase = "infrastructure_failure"
        feature_set: list[str] = []
        configuration = None
    else:
        trial_id = str(trial["trial_id"])
        phase = DEVELOPMENT_PHASE
        feature_set = list(trial["feature_set"])
        configuration = {
            "kind": trial["kind"],
            "weights": list(trial["weights"]),
            "all_components_required": True,
        }
    return {
        "trial_id": trial_id,
        "parent_trial_id": None,
        "campaign_id": CAMPAIGN_ID,
        "phase": phase,
        "created_at": base.utc_now(),
        "economic_hypothesis": "frozen Campaign004 trial failed before complete metrics",
        "formula": None,
        "direction": None,
        "feature_set": feature_set,
        "window_transform_threshold_filter_and_weight_configuration": configuration,
        "training_and_validation_folds": [],
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
        "fixed_execution_policy_fingerprints": (
            {} if trial is None else campaign["execution_policy_bindings"]
        ),
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


def _development_ledger_prefix(ledger: dict[str, Any]) -> dict[str, Any]:
    entries = list(ledger.get("entries") or [])
    first_stress = next(
        (
            index
            for index, entry in enumerate(entries)
            if entry.get("phase") == STRESS_PHASE
        ),
        len(entries),
    )
    prefix = entries[:first_stress]
    if any(entry.get("phase") != STRESS_PHASE for entry in entries[first_stress:]):
        raise Campaign004Error(
            "non-stress entry appears after Campaign004 stress replay began"
        )
    return {
        "entry_count": len(prefix),
        "chain_tip_sha256": (
            str(prefix[-1]["entry_sha256"]) if prefix else CHAIN_GENESIS
        ),
        "entries_sha256": base.value_sha256(prefix),
    }


def _build_survivor_record(
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
    if set(development) != {str(item["trial_id"]) for item in catalog}:
        raise Campaign004Error("Campaign004 development ledger is incomplete")
    decisions = [
        {
            "trial_id": trial["trial_id"],
            **campaign002.survivor_decision(
                development[str(trial["trial_id"])],
                campaign,
            ),
        }
        for trial in catalog
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
        "kind": "a_share_three_day_walkforward_campaign004_development_survivors",
        "status": "development_complete_survivors_frozen_before_exposed_stress",
        "campaign": {"path": str(campaign_path), "sha256": campaign_sha},
        "ledger_prefix": _development_ledger_prefix(ledger),
        "survivor_rule": campaign["survivor_rule"],
        "trial_decisions": decisions,
        "ranked_gate_passing_trial_ids": [
            str(item["trial_id"]) for item in ranked
        ],
        "selected_exposed_stress_survivor_trial_ids": selected,
        "selected_survivor_count": len(selected),
        "created_at": max(
            str(entry["created_at"]) for entry in development.values()
        ),
        "stress_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "current_scoring_selection_sizing_or_orders_allowed": False,
    }


def _ensure_survivor_record(
    path: Path,
    campaign: dict[str, Any],
    campaign_path: Path,
    campaign_sha: str,
    ledger: dict[str, Any],
) -> dict[str, Any]:
    expected = _build_survivor_record(
        campaign,
        campaign_path,
        campaign_sha,
        ledger,
    )
    if path.exists():
        observed = base.load_json(path)
        if observed != expected:
            raise Campaign004Error("Campaign004 frozen survivor record changed")
        return observed
    base.atomic_write_json(path, expected)
    return base.load_json(path)


def run_development(args: argparse.Namespace) -> dict[str, Any]:
    campaign_path = Path(args.campaign).expanduser().resolve()
    campaign, campaign_sha = load_campaign(campaign_path)
    output_root = Path(args.output_root).expanduser().resolve()
    ledger_path = output_root / LEDGER_FILENAME
    survivor_path = output_root / SURVIVOR_FILENAME
    if (output_root / STRESS_INTENT_FILENAME).exists():
        raise Campaign004Error(
            "development cannot run after exposed stress was opened"
        )
    ledger = _load_or_initialize_ledger(
        ledger_path,
        campaign_path,
        campaign_sha,
    )
    catalog = build_trial_catalog(campaign)
    existing = {
        str(entry["trial_id"])
        for entry in ledger["entries"]
        if entry.get("phase") == DEVELOPMENT_PHASE
    }
    expected = {str(item["trial_id"]) for item in catalog}
    if existing - expected:
        raise Campaign004Error("development ledger contains unexpected trials")
    if existing == expected:
        survivors = _ensure_survivor_record(
            survivor_path,
            campaign,
            campaign_path,
            campaign_sha,
            ledger,
        )
        stress_record = None
        if int(survivors["selected_survivor_count"]) == 0:
            stress_record = _write_or_validate_record(
                output_root / STRESS_RECORD_FILENAME,
                _zero_survivor_stress_record(
                    campaign_path,
                    campaign_sha,
                    ledger,
                    survivors,
                ),
            )
        elif (output_root / STRESS_RECORD_FILENAME).exists():
            stress_record = base.load_json(output_root / STRESS_RECORD_FILENAME)
        _write_report(
            output_root / REPORT_FILENAME,
            campaign,
            campaign_sha,
            ledger,
            survivors,
            stress_record,
        )
        return {
            "status": "development_already_complete_idempotent",
            "trial_count": len(existing),
            "survivor_count": survivors["selected_survivor_count"],
            "exposed_stress_return_fields_read": False,
        }
    print(
        "loading Campaign004 2019-2023 market, quality, and admissible factors",
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
        failure_ordinal = (
            sum(
                entry.get("phase") == "infrastructure_failure"
                for entry in ledger["entries"]
            )
            + 1
        )
        ledger = _append_ledger_entry(
            ledger_path,
            ledger,
            _failure_payload(
                campaign=campaign,
                campaign_path=campaign_path,
                campaign_sha=campaign_sha,
                trial=None,
                error=error,
                ordinal_hint=failure_ordinal,
            ),
            campaign_path,
            campaign_sha,
        )
        raise Campaign004Error(
            f"development data load failed and was recorded: {error}"
        ) from error
    created_at = base.utc_now()
    for index, trial in enumerate(catalog, start=1):
        if str(trial["trial_id"]) in existing:
            continue
        try:
            payload = _development_payload(
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
            payload = _failure_payload(
                campaign=campaign,
                campaign_path=campaign_path,
                campaign_sha=campaign_sha,
                trial=trial,
                error=error,
                ordinal_hint=index,
            )
        ledger = _append_ledger_entry(
            ledger_path,
            ledger,
            payload,
            campaign_path,
            campaign_sha,
        )
        print(
            f"recorded Campaign004 development trial {index}/{len(catalog)}",
            flush=True,
        )
    survivors = _ensure_survivor_record(
        survivor_path,
        campaign,
        campaign_path,
        campaign_sha,
        ledger,
    )
    stress_record = None
    if int(survivors["selected_survivor_count"]) == 0:
        stress_record = _write_or_validate_record(
            output_root / STRESS_RECORD_FILENAME,
            _zero_survivor_stress_record(
                campaign_path,
                campaign_sha,
                ledger,
                survivors,
            ),
        )
    _write_report(
        output_root / REPORT_FILENAME,
        campaign,
        campaign_sha,
        ledger,
        survivors,
        stress_record,
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


def _apply_stress_gate(
    combined: dict[str, Any],
    yearly: dict[str, dict[str, Any]],
    gate: dict[str, Any],
) -> list[str]:
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
    if normalized["net_cumulative_return"] <= float(gate["normalized_return_gt"]):
        failures.append("nonpositive_stress_normalized_return")
    if normalized["maximum_drawdown"] < float(gate["normalized_drawdown_gte"]):
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
    sensitivity_20bp = combined["pilot_slippage_sensitivity"]["0.0020"][
        "net_cumulative_return"
    ]
    if sensitivity_20bp <= float(gate["pilot_20bp_return_gt"]):
        failures.append("nonpositive_stress_pilot_20bp_return")
    if not all(
        yearly[str(year)]["pilot_execution_primary_10bp"][
            "net_cumulative_return"
        ]
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
    return failures


def _stress_payload(
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
    combined = base.evaluate_trial_period(
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
        str(year): base.evaluate_trial_period(
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
    failures = _apply_stress_gate(combined, yearly, gate)
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
        "development_aggregate_metrics": original_entry[
            "development_aggregate_metrics"
        ],
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


def _zero_survivor_stress_record(
    campaign_path: Path,
    campaign_sha: str,
    ledger: dict[str, Any],
    survivors: dict[str, Any],
) -> dict[str, Any]:
    return {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign004_exposed_stress_record",
        "status": "not_opened_zero_development_survivors",
        "campaign": {"path": str(campaign_path), "sha256": campaign_sha},
        "development_ledger": _development_ledger_prefix(ledger),
        "survivor_record_sha256": base.value_sha256(survivors),
        "selected_survivor_count": 0,
        "selected_survivor_trial_ids": [],
        "stress_interval_opened": False,
        "stress_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "current_scoring_selection_sizing_or_orders_allowed": False,
    }


def _write_or_validate_record(path: Path, expected: dict[str, Any]) -> dict[str, Any]:
    if path.exists():
        observed = base.load_json(path)
        if observed != expected:
            raise Campaign004Error(f"frozen Campaign004 record changed: {path}")
        return observed
    base.atomic_write_json(path, expected)
    return base.load_json(path)


def _write_report(
    path: Path,
    campaign: dict[str, Any],
    campaign_sha: str,
    ledger: dict[str, Any],
    survivors: dict[str, Any],
    stress_record: dict[str, Any] | None,
) -> None:
    development = [
        entry
        for entry in ledger["entries"]
        if entry.get("phase") == DEVELOPMENT_PHASE
    ]
    failures = [
        entry
        for entry in development
        if (entry.get("status_and_rejection_reason") or {}).get("status")
        == "infrastructure_failed"
    ]
    base.atomic_write_json(
        path,
        {
            "version": 1,
            "kind": "a_share_three_day_walkforward_campaign004_report",
            "campaign_id": CAMPAIGN_ID,
            "campaign_sha256": campaign_sha,
            "classification": (
                "development_walkforward_plus_historically_exposed_stress_replay"
            ),
            "admissible_factor_names": [
                str(item["name"]) for item in campaign["factor_library"]
            ],
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
                "All 2019-2025 outcomes are historically exposed, not pristine.",
                (
                    "The local holding universe derives from a current listing "
                    "snapshot and may contain survivorship bias."
                ),
                (
                    "Campaign004 is research-only; an exposed stress pass cannot "
                    "create a current score, selection, size, order, or new "
                    "prospective activation."
                ),
            ],
        },
    )


def run_exposed_stress(args: argparse.Namespace) -> dict[str, Any]:
    if not args.confirm_exposed_stress:
        raise Campaign004Error(
            "exposed stress requires --confirm-exposed-stress"
        )
    campaign_path = Path(args.campaign).expanduser().resolve()
    campaign, campaign_sha = load_campaign(campaign_path)
    output_root = Path(args.output_root).expanduser().resolve()
    ledger_path = output_root / LEDGER_FILENAME
    survivor_path = output_root / SURVIVOR_FILENAME
    intent_path = output_root / STRESS_INTENT_FILENAME
    stress_path = output_root / STRESS_RECORD_FILENAME
    ledger = _validate_ledger(
        base.load_json(ledger_path),
        campaign_path,
        campaign_sha,
    )
    survivors = _ensure_survivor_record(
        survivor_path,
        campaign,
        campaign_path,
        campaign_sha,
        ledger,
    )
    selected = list(survivors["selected_exposed_stress_survivor_trial_ids"])
    if not selected:
        if intent_path.exists():
            raise Campaign004Error(
                "zero-survivor Campaign004 must not contain a stress intent"
            )
        record = _write_or_validate_record(
            stress_path,
            _zero_survivor_stress_record(
                campaign_path,
                campaign_sha,
                ledger,
                survivors,
            ),
        )
        _write_report(
            output_root / REPORT_FILENAME,
            campaign,
            campaign_sha,
            ledger,
            survivors,
            record,
        )
        return {
            "status": record["status"],
            "stress_interval_opened": False,
            "stress_return_fields_read": False,
        }
    expected_intent = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign004_exposed_stress_intent",
        "status": "frozen_before_first_2024_2025_return_read",
        "campaign": {"path": str(campaign_path), "sha256": campaign_sha},
        "development_ledger": _development_ledger_prefix(ledger),
        "survivor_record_sha256": base.value_sha256(survivors),
        "selected_survivor_trial_ids": selected,
        "created_at": survivors["created_at"],
        "candidate49_historical_return_read": False,
    }
    _write_or_validate_record(intent_path, expected_intent)
    if stress_path.exists():
        record = base.load_json(stress_path)
        if (
            record.get("status") != "consumed_all_frozen_survivors"
            or record.get("selected_survivor_trial_ids") != selected
        ):
            raise Campaign004Error("Campaign004 stress record changed")
        _write_report(
            output_root / REPORT_FILENAME,
            campaign,
            campaign_sha,
            ledger,
            survivors,
            record,
        )
        return {
            "status": "exposed_stress_already_consumed_idempotent",
            "stress_trial_count": len(selected),
            "stress_return_fields_read": True,
        }
    print(
        "opening historically exposed Campaign004 2024-2025 stress replay",
        flush=True,
    )
    panel, quotes, calendar, schedule = base.prepare_phase_data(
        campaign,
        phase_end="2025-12-31",
        target_start="2024-01-01",
        years=range(2024, 2026),
        batch_size=int(args.batch_size),
    )
    catalog = {
        str(item["trial_id"]): item for item in build_trial_catalog(campaign)
    }
    development = {
        str(entry["trial_id"]): entry
        for entry in ledger["entries"]
        if entry.get("phase") == DEVELOPMENT_PHASE
    }
    created_at = base.utc_now()
    for index, trial_id in enumerate(selected, start=1):
        stress_trial_id = f"{trial_id}::exposed_stress_2024_2025"
        if any(
            str(entry.get("trial_id")) == stress_trial_id
            for entry in ledger["entries"]
        ):
            continue
        payload = _stress_payload(
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
        ledger = _append_ledger_entry(
            ledger_path,
            ledger,
            payload,
            campaign_path,
            campaign_sha,
        )
        print(
            f"recorded Campaign004 exposed stress trial {index}/{len(selected)}",
            flush=True,
        )
    stress_entries = [
        entry
        for entry in ledger["entries"]
        if entry.get("phase") == STRESS_PHASE
    ]
    if {
        str(entry.get("parent_trial_id")) for entry in stress_entries
    } != set(selected):
        raise Campaign004Error("Campaign004 stress ledger is incomplete")
    record = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign004_exposed_stress_record",
        "status": "consumed_all_frozen_survivors",
        "campaign": {"path": str(campaign_path), "sha256": campaign_sha},
        "intent_sha256": base.file_sha256(intent_path),
        "selected_survivor_count": len(selected),
        "selected_survivor_trial_ids": selected,
        "stress_trial_ids": [str(entry["trial_id"]) for entry in stress_entries],
        "ledger": {
            "entry_count": len(ledger["entries"]),
            "chain_tip_sha256": ledger["chain_tip_sha256"],
        },
        "stress_interval_opened": True,
        "stress_return_fields_read": True,
        "candidate49_historical_return_read": False,
        "current_scoring_selection_sizing_or_orders_allowed": False,
    }
    _write_or_validate_record(stress_path, record)
    _write_report(
        output_root / REPORT_FILENAME,
        campaign,
        campaign_sha,
        ledger,
        survivors,
        record,
    )
    return {
        "status": "exposed_stress_consumed",
        "stress_trial_count": len(stress_entries),
        "ledger_sha256": base.file_sha256(ledger_path),
        "stress_record_path": str(stress_path),
        "stress_record_sha256": base.file_sha256(stress_path),
        "stress_return_fields_read": True,
        "candidate49_historical_return_read": False,
    }


def status(args: argparse.Namespace) -> dict[str, Any]:
    campaign_path = Path(args.campaign).expanduser().resolve()
    campaign, campaign_sha = load_campaign(campaign_path)
    output_root = Path(args.output_root).expanduser().resolve()
    result: dict[str, Any] = {
        "campaign_id": CAMPAIGN_ID,
        "campaign_sha256": campaign_sha,
        "expected_trial_count": len(build_trial_catalog(campaign)),
        "candidate49_historical_return_read": False,
        "current_scoring_selection_sizing_or_orders_allowed": False,
    }
    ledger_path = output_root / LEDGER_FILENAME
    if ledger_path.exists():
        ledger = _validate_ledger(
            base.load_json(ledger_path),
            campaign_path,
            campaign_sha,
        )
        result["ledger_entry_count"] = len(ledger["entries"])
        result["ledger_chain_tip_sha256"] = ledger["chain_tip_sha256"]
    else:
        result["ledger_entry_count"] = 0
    survivor_path = output_root / SURVIVOR_FILENAME
    if survivor_path.exists():
        survivors = base.load_json(survivor_path)
        result["selected_survivor_count"] = survivors.get(
            "selected_survivor_count"
        )
    result["stress_intent_exists"] = (
        output_root / STRESS_INTENT_FILENAME
    ).exists()
    stress_path = output_root / STRESS_RECORD_FILENAME
    result["stress_record_exists"] = stress_path.exists()
    if stress_path.exists():
        result["stress_status"] = base.load_json(stress_path).get("status")
    return result


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Run the frozen Campaign004 walk-forward study."
    )
    value.add_argument("--campaign", default=str(DEFAULT_CAMPAIGN))
    value.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    value.add_argument("--batch-size", type=int, default=256)
    subparsers = value.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run-development")
    stress = subparsers.add_parser("run-exposed-stress")
    stress.add_argument("--confirm-exposed-stress", action="store_true")
    subparsers.add_parser("status")
    return value


def main() -> int:
    args = parser().parse_args()
    if args.command == "run-development":
        result = run_development(args)
    elif args.command == "run-exposed-stress":
        result = run_exposed_stress(args)
    else:
        result = status(args)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
