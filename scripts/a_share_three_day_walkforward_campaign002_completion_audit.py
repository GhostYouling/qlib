#!/usr/bin/env python3
"""Read-only completion audit for three-day walk-forward Campaign002."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_three_day_walkforward_campaign002 as runner  # noqa: E402
import a_share_three_day_walkforward_completion_audit as campaign001_audit  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
PREREGISTRATION_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_002_preregistration.json"
)
RESEARCH_RECORD_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_002_research_record.json"
)
OUTPUT_ROOT = (
    REPO_ROOT
    / "data"
    / "experiments"
    / "short_horizon"
    / "historical_walkforward"
    / "campaign_002"
)
EXPECTED_OUTPUT_FILENAMES = {
    "campaign_report.json",
    "development_survivors.json",
    "exposed_stress_consumption_record.json",
    "trial_ledger.json",
}


class CompletionAuditError(RuntimeError):
    """Raised when Campaign002 evidence cannot prove a frozen invariant."""


def resolved_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def binding_matches(binding: dict[str, Any]) -> bool:
    path = resolved_path(str(binding.get("path") or ""))
    expected = str(binding.get("sha256") or "")
    return (
        path.is_file()
        and len(expected) == 64
        and runner.base.file_sha256(path) == expected
    )


def audit() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, evidence: Any) -> None:
        checks.append({"name": name, "passed": bool(condition), "evidence": evidence})

    campaign, preregistration, campaign_sha = runner.load_campaign(
        PREREGISTRATION_PATH
    )
    record = runner.base.load_json(RESEARCH_RECORD_PATH)
    catalog = runner.build_trial_catalog(campaign)
    catalog_by_id = {str(item["trial_id"]): item for item in catalog}
    ledger_path = OUTPUT_ROOT / runner.LEDGER_FILENAME
    ledger = runner.validate_ledger(
        runner.base.load_json(ledger_path),
        PREREGISTRATION_PATH.resolve(),
        campaign_sha,
    )
    survivors_path = OUTPUT_ROOT / runner.SURVIVOR_FILENAME
    survivors = runner.base.load_json(survivors_path)
    expected_survivors = runner.build_survivor_record(
        campaign,
        PREREGISTRATION_PATH.resolve(),
        campaign_sha,
        ledger,
    )
    stress_path = OUTPUT_ROOT / runner.STRESS_RECORD_FILENAME
    stress = runner.base.load_json(stress_path)
    report_path = OUTPUT_ROOT / runner.REPORT_FILENAME
    report = runner.base.load_json(report_path)

    check(
        "complete_finite_library_and_search_frozen",
        len(campaign["factor_library"]) == 8
        and len(catalog) == 84
        and len(catalog_by_id) == 84
        and all(item["kind"] == "nonlinear_pair_consensus" for item in catalog)
        and {
            str(item["operator"]) for item in catalog
        }
        == {"geometric_mean", "harmonic_mean", "minimum"},
        {
            "factor_count": len(campaign["factor_library"]),
            "trial_count": len(catalog),
            "operator_counts": {
                operator: sum(item["operator"] == operator for item in catalog)
                for operator in ("geometric_mean", "harmonic_mean", "minimum")
            },
        },
    )
    factor_names = {
        str(item["name"]) for item in campaign["factor_library"]
    }
    check(
        "prior_terminal_conclusions_preserved_and_candidate49_excluded",
        all(
            item.get("prior_terminal_conclusion_unchanged") is True
            for item in campaign["factor_library"]
        )
        and "intraday_cumulative_vwap_crossing_rate_240m" not in factor_names
        and preregistration["reused_complete_feature_library"][
            "all_prior_terminal_conclusions_unchanged"
        ]
        is True,
        {
            "factor_names": sorted(factor_names),
            "candidate49_factor_present": (
                "intraday_cumulative_vwap_crossing_rate_240m" in factor_names
            ),
        },
    )
    development = [
        entry
        for entry in ledger["entries"]
        if entry.get("phase") == runner.DEVELOPMENT_PHASE
    ]
    infrastructure = [
        entry
        for entry in ledger["entries"]
        if (entry.get("status_and_rejection_reason") or {}).get("status")
        == "infrastructure_failed"
    ]
    check(
        "all_84_development_trials_retained_once_without_infrastructure_failure",
        len(ledger["entries"]) == 84
        and len(development) == 84
        and len(infrastructure) == 0
        and {str(entry["trial_id"]) for entry in development}
        == set(catalog_by_id),
        {
            "ledger_entry_count": len(ledger["entries"]),
            "development_entry_count": len(development),
            "infrastructure_failure_count": len(infrastructure),
        },
    )
    expected_windows = campaign["walkforward_folds"]
    semantic_matches = True
    for entry in development:
        trial = catalog_by_id[str(entry["trial_id"])]
        folds = list(entry.get("training_and_validation_folds") or [])
        observed_windows = [
            {
                "fold": int(item["fold"]),
                "training": {
                    "start": item["training_metrics"]["start"],
                    "end": item["training_metrics"]["end"],
                },
                "validation": {
                    "start": item["validation_metrics"]["start"],
                    "end": item["validation_metrics"]["end"],
                },
            }
            for item in folds
        ]
        config = (
            entry.get(
                "window_transform_threshold_filter_and_weight_configuration"
            )
            or {}
        )
        if not (
            entry.get("parent_trial_id") == trial["parent_trial_id"]
            and entry.get("formula") == trial["operator_formula"]
            and entry.get("feature_set") == trial["feature_set"]
            and config.get("operator") == trial["operator"]
            and observed_windows == expected_windows
            and entry.get("locked_backtest_metrics_when_opened") is None
            and entry.get("candidate49_historical_return_read") is False
            and entry.get(
                "current_scoring_selection_sizing_or_orders_performed"
            )
            is False
        ):
            semantic_matches = False
            break
    check(
        "development_entries_match_catalog_folds_and_research_boundaries",
        semantic_matches,
        {"checked_development_entries": len(development)},
    )
    check(
        "survivor_record_replays_exactly",
        survivors == expected_survivors,
        {
            "trial_decision_count": len(survivors["trial_decisions"]),
            "selected_survivor_count": survivors["selected_survivor_count"],
            "ledger_prefix_entry_count": survivors["ledger_prefix"][
                "entry_count"
            ],
        },
    )
    decisions = list(survivors["trial_decisions"])
    operational_count = sum(
        item["operationally_admissible"] for item in decisions
    )
    quality_count = sum(
        item["validation_quality_gate_passed"] for item in decisions
    )
    gate_count = sum(
        item["development_survivor_gate_passed"] for item in decisions
    )
    check(
        "zero_survivors_is_frozen_gate_result_not_post_result_relaxation",
        len(decisions) == 84
        and operational_count == 43
        and quality_count == 0
        and gate_count == 0
        and survivors["selected_survivor_count"] == 0,
        {
            "decision_count": len(decisions),
            "operationally_admissible_count": operational_count,
            "validation_quality_gate_passed_count": quality_count,
            "development_survivor_gate_passed_count": gate_count,
        },
    )
    check(
        "historically_exposed_2024_2025_interval_was_not_opened",
        not (OUTPUT_ROOT / runner.STRESS_INTENT_FILENAME).exists()
        and stress.get("status") == "exposed_stress_replay_consumed_once_complete"
        and stress.get("stress_interval_opened") is False
        and stress.get("reason") == "zero_development_survivors"
        and stress.get("completed_stress_trial_ids") == []
        and stress.get("frozen_gate_passer_trial_ids") == []
        and not any(
            entry.get("phase") == runner.STRESS_PHASE
            for entry in ledger["entries"]
        ),
        {
            "stress_intent_exists": (
                OUTPUT_ROOT / runner.STRESS_INTENT_FILENAME
            ).exists(),
            "stress_interval_opened": stress.get("stress_interval_opened"),
            "stress_ledger_entry_count": sum(
                entry.get("phase") == runner.STRESS_PHASE
                for entry in ledger["entries"]
            ),
        },
    )
    check(
        "campaign_report_matches_closed_zero_survivor_state",
        report.get("campaign_id") == runner.CAMPAIGN_ID
        and report.get("campaign_sha256") == campaign_sha
        and report.get("development_trial_count") == 84
        and report.get("infrastructure_failure_count") == 0
        and report.get("development_gate_passer_count") == 0
        and report.get("selected_exposed_stress_survivor_count") == 0
        and report.get("exposed_stress") == stress
        and report.get("prior_terminal_factor_conclusions_changed") is False
        and report.get(
            "current_scoring_selection_sizing_or_orders_allowed"
        )
        is False,
        {
            "development_trial_count": report.get("development_trial_count"),
            "development_gate_passer_count": report.get(
                "development_gate_passer_count"
            ),
            "stress_interval_opened": stress.get("stress_interval_opened"),
        },
    )
    actual_outputs = {
        path.name for path in OUTPUT_ROOT.iterdir() if path.is_file()
    }
    check(
        "campaign_created_only_declared_research_artifacts",
        actual_outputs == EXPECTED_OUTPUT_FILENAMES,
        {
            "actual_output_filenames": sorted(actual_outputs),
            "expected_output_filenames": sorted(EXPECTED_OUTPUT_FILENAMES),
        },
    )
    campaign001 = campaign001_audit.audit()
    check(
        "campaign001_and_candidate49_independent_state_still_validate",
        campaign001.get("status") == "passed"
        and not campaign001.get("failed_requirement_checks")
        and next(
            item
            for item in campaign001["checks"]
            if item["name"]
            == "candidate49_remains_independent_and_candidate50_not_started"
        )["passed"],
        {
            "campaign001_audit_status": campaign001.get("status"),
            "campaign001_requirement_check_count": campaign001.get(
                "requirement_check_count"
            ),
        },
    )
    completed = record.get("completed_artifacts") or {}
    artifact_bindings_ok = all(
        binding_matches(completed.get(name) or {})
        for name in (
            "trial_ledger",
            "development_survivors",
            "exposed_stress_consumption_record",
            "campaign_report",
            "fresh_price_basis_audit",
        )
    )
    check(
        "research_record_binds_completed_artifacts_and_fresh_price_audit",
        record.get("kind")
        == "a_share_three_day_walkforward_campaign002_research_record"
        and record.get("status")
        == "completed_zero_development_survivors_stress_interval_not_opened"
        and record.get("campaign", {}).get("sha256") == campaign_sha
        and artifact_bindings_ok,
        {
            "artifact_binding_names": sorted(completed),
            "all_required_bindings_match": artifact_bindings_ok,
        },
    )
    safety = record.get("research_boundary") or {}
    check(
        "research_record_preserves_candidate_and_action_boundaries",
        safety.get("candidate49_historical_return_read") is False
        and safety.get("candidate49_ledgers_changed") is False
        and safety.get("candidate50_prospective_activation_created") is False
        and safety.get("current_scoring_performed") is False
        and safety.get("selection_sizing_or_orders_performed") is False
        and safety.get("stress_2024_2025_return_fields_read") is False,
        safety,
    )

    failed = [item["name"] for item in checks if not item["passed"]]
    return {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign002_completion_audit",
        "status": "passed" if not failed else "failed",
        "campaign_sha256": campaign_sha,
        "research_record_sha256": runner.base.file_sha256(RESEARCH_RECORD_PATH),
        "ledger_sha256": runner.base.file_sha256(ledger_path),
        "ledger_chain_tip_sha256": ledger["chain_tip_sha256"],
        "requirement_check_count": len(checks),
        "failed_requirement_checks": failed,
        "checks": checks,
        "limitations": [
            "All historical evidence remains exposed rather than pristine.",
            (
                "The holding universe derives from a current listing snapshot "
                "and may contain survivorship bias."
            ),
            (
                "The audit proves repository artifacts and boundaries, not "
                "actions outside the declared workspace."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    try:
        result = audit()
    except (
        CompletionAuditError,
        runner.Campaign002Error,
        runner.base.WalkForwardError,
        KeyError,
        ValueError,
        FileNotFoundError,
    ) as error:
        result = {
            "version": 1,
            "kind": "a_share_three_day_walkforward_campaign002_completion_audit",
            "status": "failed",
            "error": f"{type(error).__name__}: {error}",
        }
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=None if args.compact else 2,
            sort_keys=args.compact,
            allow_nan=False,
        )
    )
    return 0 if result.get("status") == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
