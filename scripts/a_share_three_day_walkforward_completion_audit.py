#!/usr/bin/env python3
"""Read-only completion audit for historical walk-forward campaign 001r1."""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_three_day_walkforward_campaign as campaign_runner  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
PREREGISTRATION_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_001r1_preregistration.json"
)
RESEARCH_RECORD_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_001r1_research_record.json"
)
OUTPUT_ROOT = (
    REPO_ROOT
    / "data"
    / "experiments"
    / "short_horizon"
    / "historical_walkforward"
    / "campaign_001r1"
)
EXPECTED_OUTPUT_FILENAMES = {
    "campaign_report.json",
    "development_survivors.json",
    "lockbox_consumption_record.json",
    "lockbox_open_intent.json",
    "trial_ledger.json",
}
EXPECTED_FOLDS = [
    {
        "fold": 1,
        "training": {"start": "2019-01-01", "end": "2020-12-31"},
        "validation": {"start": "2021-01-01", "end": "2021-12-31"},
    },
    {
        "fold": 2,
        "training": {"start": "2019-01-01", "end": "2021-12-31"},
        "validation": {"start": "2022-01-01", "end": "2022-12-31"},
    },
    {
        "fold": 3,
        "training": {"start": "2019-01-01", "end": "2022-12-31"},
        "validation": {"start": "2023-01-01", "end": "2023-12-31"},
    },
]


class CompletionAuditError(RuntimeError):
    """Raised when a required campaign invariant is not proven."""


def parse_timestamp(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise CompletionAuditError(f"timestamp is not timezone-aware: {value}")
    return parsed


def resolved_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def binding_matches(binding: dict[str, Any], hash_key: str = "sha256") -> bool:
    path = resolved_path(str(binding.get("path") or ""))
    expected = str(binding.get(hash_key) or "")
    return (
        path.is_file()
        and len(expected) == 64
        and campaign_runner.file_sha256(path) == expected
    )


def metric_windows(entry: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "fold": int(fold["fold"]),
            "training": {
                "start": fold["training_metrics"]["start"],
                "end": fold["training_metrics"]["end"],
            },
            "validation": {
                "start": fold["validation_metrics"]["start"],
                "end": fold["validation_metrics"]["end"],
            },
        }
        for fold in entry["training_and_validation_folds"]
    ]


def audit() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, evidence: Any) -> None:
        checks.append({"name": name, "passed": bool(condition), "evidence": evidence})

    preregistration_source = campaign_runner.load_json(PREREGISTRATION_PATH)
    frozen, campaign_sha = campaign_runner.load_campaign(PREREGISTRATION_PATH)
    research_record = campaign_runner.load_json(RESEARCH_RECORD_PATH)
    catalog = campaign_runner.build_trial_catalog(frozen)
    catalog_by_id = {str(item["trial_id"]): item for item in catalog}

    check(
        "finite_factor_library_and_search_frozen",
        len(frozen["factor_library"]) == 8
        and len(catalog) == 92
        and sum(item["kind"] == "single_factor" for item in catalog) == 8
        and sum(item["kind"] == "pair_rank_blend" for item in catalog) == 84,
        {
            "factor_count": len(frozen["factor_library"]),
            "single_trial_count": sum(
                item["kind"] == "single_factor" for item in catalog
            ),
            "pair_trial_count": sum(
                item["kind"] == "pair_rank_blend" for item in catalog
            ),
        },
    )
    factor_names = {str(item["name"]) for item in frozen["factor_library"]}
    check(
        "old_terminal_factor_conclusions_preserved",
        all(
            item.get("prior_terminal_conclusion_unchanged") is True
            for item in frozen["factor_library"]
        ),
        {"factor_names": sorted(factor_names)},
    )
    check(
        "candidate49_excluded_from_historical_library",
        "intraday_cumulative_vwap_crossing_rate_240m" not in factor_names
        and frozen["candidate49_boundary"]["historical_return_read_allowed"] is False,
        {"candidate49_factor_present": False},
    )
    check(
        "expanding_2019_2023_folds_and_three_session_purge_frozen",
        frozen["walkforward_folds"] == EXPECTED_FOLDS
        and frozen["split_protocol"]["purge_signal_sessions_each_boundary"] == 3
        and frozen["split_protocol"]["label_containment_required"] is True,
        {
            "folds": frozen["walkforward_folds"],
            "purge_signal_sessions_each_boundary": frozen["split_protocol"][
                "purge_signal_sessions_each_boundary"
            ],
        },
    )

    frozen_at = parse_timestamp(str(preregistration_source["frozen_at"]))
    ledger_path = OUTPUT_ROOT / campaign_runner.LEDGER_FILENAME
    ledger = campaign_runner.validate_ledger(
        campaign_runner.load_json(ledger_path),
        PREREGISTRATION_PATH,
        campaign_sha,
    )
    entries = list(ledger["entries"])
    development = [
        entry for entry in entries if entry["phase"] == "development_walkforward"
    ]
    lockbox = [
        entry for entry in entries if entry["phase"] == "locked_2024_2025_backtest"
    ]
    first_development_at = min(
        parse_timestamp(str(entry["created_at"])) for entry in development
    )
    check(
        "repaired_preregistration_precedes_successful_development_results",
        frozen_at < first_development_at,
        {
            "repaired_preregistration_frozen_at": preregistration_source["frozen_at"],
            "first_development_entry_created_at": min(
                str(entry["created_at"]) for entry in development
            ),
            "base_campaign_sha256": preregistration_source["base_campaign"]["sha256"],
            "repair_record_sha256": preregistration_source[
                "infrastructure_repair"
            ]["sha256"],
        },
    )

    development_ids = [str(entry["trial_id"]) for entry in development]
    check(
        "all_92_frozen_development_trials_retained_once",
        len(development) == 92
        and len(set(development_ids)) == 92
        and set(development_ids) == set(catalog_by_id),
        {
            "development_entry_count": len(development),
            "unique_development_trial_count": len(set(development_ids)),
            "missing_trial_ids": sorted(set(catalog_by_id) - set(development_ids)),
            "extra_trial_ids": sorted(set(development_ids) - set(catalog_by_id)),
        },
    )
    development_semantics_valid = True
    for ordinal, entry in enumerate(development, start=1):
        trial = catalog_by_id[str(entry["trial_id"])]
        configuration = entry[
            "window_transform_threshold_filter_and_weight_configuration"
        ]
        development_semantics_valid &= (
            int(entry["ordinal"]) == ordinal
            and entry["feature_set"] == trial["feature_set"]
            and configuration["kind"] == trial["kind"]
            and configuration["weights"] == trial["weights"]
            and metric_windows(entry) == EXPECTED_FOLDS
            and entry["training_metrics"]
            == [
                fold["training_metrics"]
                for fold in entry["training_and_validation_folds"]
            ]
            and entry["validation_metrics"]
            == [
                fold["validation_metrics"]
                for fold in entry["training_and_validation_folds"]
            ]
            and all(
                int(result["association"]["cohorts"]) > 0
                and "normalized_execution" in result
                and "pilot_execution_primary_10bp" in result
                for result in entry["training_metrics"] + entry["validation_metrics"]
            )
            and entry["locked_backtest_metrics_when_opened"] is None
            and entry["status_and_rejection_reason"]["status"]
            == "development_walkforward_completed"
            and entry["candidate49_historical_return_read"] is False
            and entry[
                "current_scoring_selection_sizing_or_orders_performed"
            ]
            is False
        )
    check(
        "development_entries_match_catalog_folds_and_execution_views",
        development_semantics_valid,
        {"checked_development_entries": len(development)},
    )

    survivor_path = OUTPUT_ROOT / campaign_runner.SURVIVOR_FILENAME
    survivor = campaign_runner.load_json(survivor_path)
    development_prefix = {
        **{key: value for key, value in ledger.items() if key != "entries"},
        "entries": development,
        "chain_tip_sha256": development[-1]["entry_sha256"],
    }
    expected_survivor = campaign_runner.build_survivor_record(
        frozen,
        PREREGISTRATION_PATH,
        campaign_sha,
        development_prefix,
    )
    selected = list(survivor["selected_lockbox_survivor_trial_ids"])
    check(
        "survivor_rule_replay_matches_frozen_record",
        survivor == expected_survivor
        and survivor["selected_survivor_count"] == 8
        and survivor["lockbox_return_fields_read"] is False,
        {
            "selected_survivor_count": survivor["selected_survivor_count"],
            "selected_trial_ids": selected,
        },
    )

    intent_path = OUTPUT_ROOT / campaign_runner.LOCKBOX_INTENT_FILENAME
    intent = campaign_runner.load_json(intent_path)
    intent_at = parse_timestamp(str(intent["opened_at"]))
    check(
        "lockbox_intent_frozen_after_survivors_and_before_lockbox_entries",
        parse_timestamp(str(survivor["created_at"])) < intent_at
        and all(parse_timestamp(str(entry["created_at"])) == intent_at for entry in lockbox)
        and intent["lockbox_start"] == "2024-01-01"
        and intent["lockbox_end"] == "2025-12-31"
        and intent["survivor_record_sha256"]
        == campaign_runner.file_sha256(survivor_path),
        {
            "survivors_frozen_at": survivor["created_at"],
            "lockbox_opened_at": intent["opened_at"],
            "lockbox_entry_count": len(lockbox),
        },
    )
    lockbox_parents = [str(entry["parent_trial_id"]) for entry in lockbox]
    lockbox_semantics_valid = (
        len(lockbox) == len(selected) == 8
        and lockbox_parents == selected
        and len(set(lockbox_parents)) == 8
    )
    for entry in lockbox:
        opened = entry["locked_backtest_metrics_when_opened"]
        final_gate = opened["final_gate"]
        combined = opened["combined_2024_2025"]
        yearly = opened["standalone_year_replays"]
        expected_status = (
            "lockbox_passed_research_only"
            if final_gate["passed"]
            else "lockbox_rejected"
        )
        lockbox_semantics_valid &= (
            combined["start"] == "2024-01-01"
            and combined["end"] == "2025-12-31"
            and set(yearly) == {"2024", "2025"}
            and yearly["2024"]["start"] == "2024-01-01"
            and yearly["2024"]["end"] == "2024-12-31"
            and yearly["2025"]["start"] == "2025-01-01"
            and yearly["2025"]["end"] == "2025-12-31"
            and entry["status_and_rejection_reason"]["status"] == expected_status
            and entry["candidate49_historical_return_read"] is False
            and entry[
                "current_scoring_selection_sizing_or_orders_performed"
            ]
            is False
        )
    check(
        "all_selected_survivors_opened_once_and_all_outcomes_retained",
        lockbox_semantics_valid,
        {
            "selected_survivor_count": len(selected),
            "completed_lockbox_entry_count": len(lockbox),
            "unique_lockbox_parent_count": len(set(lockbox_parents)),
        },
    )

    passers = [
        str(entry["parent_trial_id"])
        for entry in lockbox
        if entry["locked_backtest_metrics_when_opened"]["final_gate"]["passed"]
    ]
    consumption_path = OUTPUT_ROOT / campaign_runner.LOCKBOX_RECORD_FILENAME
    consumption = campaign_runner.load_json(consumption_path)
    report_path = OUTPUT_ROOT / campaign_runner.REPORT_FILENAME
    report = campaign_runner.load_json(report_path)
    check(
        "one_time_lockbox_consumption_and_report_are_closed",
        consumption["status"] == "lockbox_consumed_once_complete"
        and consumption["selected_survivor_trial_ids"] == selected
        and consumption["completed_lockbox_trial_ids"] == selected
        and consumption["final_gate_passer_trial_ids"] == passers
        and consumption["ledger"]["entry_count"] == 100
        and consumption["ledger"]["chain_tip_sha256"]
        == ledger["chain_tip_sha256"]
        and consumption["ledger"]["file_sha256"]
        == campaign_runner.file_sha256(ledger_path)
        and consumption["lockbox_intent_sha256"]
        == campaign_runner.file_sha256(intent_path)
        and report["lockbox"] == consumption
        and report["ledger"]["entry_count"] == 100,
        {
            "ledger_entry_count": len(entries),
            "development_entry_count": len(development),
            "lockbox_entry_count": len(lockbox),
            "final_gate_passer_count": len(passers),
        },
    )

    old_failure = research_record["first_attempt_infrastructure_failure"]
    old_ledger_binding = old_failure["failed_campaign_ledger"]
    old_ledger_path = resolved_path(old_ledger_binding["path"])
    base_path = resolved_path(preregistration_source["base_campaign"]["path"])
    old_ledger = campaign_runner.validate_ledger(
        campaign_runner.load_json(old_ledger_path),
        base_path,
        preregistration_source["base_campaign"]["sha256"],
    )
    old_entry = old_ledger["entries"][0]
    check(
        "first_infrastructure_failure_retained_before_return_read",
        binding_matches(old_ledger_binding)
        and len(old_ledger["entries"]) == 1
        and old_entry["phase"] == "development_infrastructure"
        and old_entry["forward_return_fields_read"] is False
        and old_entry["lockbox_return_fields_read"] is False
        and old_entry["status_and_rejection_reason"]["status"]
        == "infrastructure_failed_before_forward_return_construction",
        {
            "failure_entry_count": len(old_ledger["entries"]),
            "failure_trial_id": old_entry["trial_id"],
        },
    )

    frozen_binding_results = {
        name: binding_matches(binding)
        for name, binding in research_record["frozen_inputs"].items()
    }
    artifact_binding_results = {
        name: binding_matches(binding)
        for name, binding in research_record["completed_artifacts"].items()
    }
    check(
        "research_record_binds_all_frozen_inputs_and_completed_artifacts",
        all(frozen_binding_results.values())
        and all(artifact_binding_results.values())
        and research_record["development_outcome"]["omitted_trial_count"] == 0
        and research_record["lockbox_outcome"]["final_gate_passer_count"]
        == len(passers),
        {
            "frozen_inputs": frozen_binding_results,
            "completed_artifacts": artifact_binding_results,
        },
    )

    actual_outputs = {
        path.name for path in OUTPUT_ROOT.iterdir() if path.is_file()
    }
    current_action_flags = [
        consumption["current_scoring_allowed"],
        consumption["selection_allowed"],
        consumption["sizing_allowed"],
        consumption["orders_allowed"],
        report["current_scoring_selection_sizing_or_orders_allowed"],
    ]
    check(
        "campaign_created_no_current_score_selection_size_or_order_artifact",
        actual_outputs == EXPECTED_OUTPUT_FILENAMES
        and not any(current_action_flags),
        {
            "output_filenames": sorted(actual_outputs),
            "all_current_action_flags_false": not any(current_action_flags),
        },
    )

    candidate49_results: dict[str, Any] = {}
    candidate49_valid = True
    for name in ("signal_ledger", "execution_ledger"):
        binding = research_record["candidate49_boundary"][name]
        path = resolved_path(binding["path"])
        value = campaign_runner.load_json(path)
        result = {
            "sha256_matches": binding_matches(binding, "sha256_after_campaign"),
            "entry_count": len(value.get("entries") or []),
        }
        candidate49_results[name] = result
        candidate49_valid &= result["sha256_matches"] and result["entry_count"] == 0
    candidate50_paths = sorted(
        str(path.relative_to(REPO_ROOT))
        for path in (REPO_ROOT / "data" / "experiments" / "short_horizon").rglob(
            "*candidate50*"
        )
    )
    check(
        "candidate49_remains_independent_and_candidate50_not_started",
        candidate49_valid
        and not candidate50_paths
        and all(entry["candidate49_historical_return_read"] is False for entry in entries)
        and intent["candidate49_historical_return_read"] is False
        and consumption["candidate49_historical_return_read"] is False,
        {
            "candidate49_ledgers": candidate49_results,
            "candidate50_artifact_paths": candidate50_paths,
        },
    )

    failures = [item["name"] for item in checks if not item["passed"]]
    return {
        "version": 1,
        "kind": "a_share_three_day_walkforward_completion_audit",
        "status": "passed" if not failures else "failed",
        "campaign_sha256": campaign_sha,
        "research_record_sha256": campaign_runner.file_sha256(RESEARCH_RECORD_PATH),
        "ledger_sha256": campaign_runner.file_sha256(ledger_path),
        "ledger_chain_tip_sha256": ledger["chain_tip_sha256"],
        "requirement_check_count": len(checks),
        "failed_requirement_checks": failures,
        "checks": checks,
        "limitations": [
            "The evidence remains historically exposed quasi-out-of-sample, not pristine.",
            "The holding universe derives from a current listing snapshot and may contain survivorship bias.",
            "Repository evidence proves no campaign-generated score, selection, sizing, or order artifact; it cannot prove the absence of actions outside the declared workspace.",
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
        campaign_runner.WalkForwardError,
        KeyError,
        TypeError,
        ValueError,
        FileNotFoundError,
    ) as error:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error": f"{type(error).__name__}: {error}",
                },
                ensure_ascii=False,
                indent=None if args.compact else 2,
                sort_keys=True,
            )
        )
        return 1
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=None if args.compact else 2,
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
