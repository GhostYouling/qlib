#!/usr/bin/env python3
"""Publish immutable Campaign048 development preregistration and freeze."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
FACTOR = "intraday_two_sided_wick_absorption_balance_240m"
TRIAL_ID = "wf048_intraday_two_sided_wick_absorption_balance_240m_single_higher"
PARENT_PREREG = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_047_preregistration.json"
AUTHORITATIVE_STATE = REPO_ROOT / "docs/a_share_three_day_iteration_status_20260801_campaign047_verified.json"
POLICY = REPO_ROOT / "docs/a_share_three_day_historical_walkforward_research_policy_20260727.json"
FUTURE_ONLY = REPO_ROOT / "docs/a_share_three_day_iteration_status_20260725_future_only.json"
CONCEPT = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_concept_scouting.json"
MECHANISM = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_mechanism_overlap_audit.json"
PROTOCOL = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_no_return_preregistration.json"
AUDIT = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_048/no_return/20260801T050642Z_campaign048_no_return_audit.json"
AUDIT_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_no_return_audit_freeze_20260801.json"
SNAPSHOT = DATA_ROOT / "derived/a_share/rich/tushare/minute_walkforward_campaign048_feature_library/tushare_stk_mins_1m_2019_2025_ea0cbb8f_walkforward_campaign048_feature_library_v1/snapshot_manifest.json"
FEATURE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign048_features_v3.py"
RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign048_v2.py"
TESTS = REPO_ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign048.py"
PREREG = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_preregistration_v2.json"
FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_development_implementation_freeze_20260801.json"
SEMANTIC_FAILURE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_development_namespace_semantic_failure_20260801.json"
OUTPUT_ROOT = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_048/walkforward"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def binding(path: Path) -> dict[str, str]:
    return {"path": display(path), "sha256": sha256(path)}


def write_new(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode()
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        if json.loads(path.read_text()) != record:
            raise RuntimeError(f"refuse to rewrite frozen record: {path}")
        return
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def preregister() -> Path:
    parent = json.loads(PARENT_PREREG.read_text())
    snapshot = json.loads(SNAPSHOT.read_text())
    audit = json.loads(AUDIT.read_text())
    protocol = json.loads(PROTOCOL.read_text())
    if (
        audit.get("admissible_factor_names") != [FACTOR]
        or audit.get("admissible_factor_count") != 1
        or audit.get("historical_forward_return_fields_read") is not False
        or protocol.get("finite_development_catalog_if_admitted", {}).get("trial_id") != TRIAL_ID
    ):
        raise RuntimeError("Campaign048 no-return admission boundary changed")

    record = copy.deepcopy(parent)
    record.update(
        {
            "kind": "a_share_three_day_walkforward_campaign048_preregistration",
            "campaign_id": "a_share_three_day_walkforward_campaign_048",
            "status": "frozen_before_campaign048_2019_2023_development_return_read",
            "frozen_at": "2026-08-01T05:12:00Z",
            "purpose": "Freeze the only Campaign048 factor admitted by the ordered no-return gates and the exact pre-value trial identifier before any 2019-2023 daily price or forward-return field is opened.",
        }
    )
    record["evidence_classification"] = copy.deepcopy(parent["evidence_classification"])
    record["governance_bindings"] = {
        "authoritative_iteration_state": binding(AUTHORITATIVE_STATE),
        "historical_walkforward_policy": binding(POLICY),
        "future_only_policy": binding(FUTURE_ONLY),
        "concept_scouting": binding(CONCEPT),
        "mechanism_overlap_audit": binding(MECHANISM),
        "campaign047_terminal_record": binding(
            REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_047_research_record.json"
        ),
        "pre_return_namespace_semantic_failure": binding(SEMANTIC_FAILURE),
    }
    record["no_return_bindings"] = {
        "protocol": binding(PROTOCOL),
        "audit": binding(AUDIT),
        "audit_freeze": binding(AUDIT_FREEZE),
        "feature_snapshot": {
            **binding(SNAPSHOT),
            "dataset_sha256": snapshot["dataset_sha256"],
        },
        "feature_and_no_return_runner": binding(FEATURE_RUNNER),
    }
    record["implementation"] = {
        "script": binding(RUNNER),
        "development_command": "PYTHONPATH=. python scripts/a_share_three_day_walkforward_campaign048_v2.py run-development",
        "exposed_stress_command": "PYTHONPATH=. python scripts/a_share_three_day_walkforward_campaign048_v2.py run-exposed-stress --confirm-exposed-stress",
        "output_root": str(OUTPUT_ROOT),
    }
    record["factor_library"] = [
        {
            "feature_id": "wf048_f01",
            "name": FACTOR,
            "direction": "higher",
            "formula": protocol["candidate"]["formula"],
            "economic_hypothesis": protocol["candidate"]["economic_hypothesis"],
            "dataset_group": "campaign048_new_factors",
            "partition_root": str(SNAPSHOT.parent / "partitions"),
            "bindings": [binding(SNAPSHOT), binding(PROTOCOL), binding(AUDIT), binding(AUDIT_FREEZE)],
        }
    ]
    search = copy.deepcopy(parent["search_space"])
    search.update(
        {
            "admissible_factor_names_canonical": [FACTOR],
            "single_factor_rule": f"Evaluate the only admissible factor exactly once at weight 1.0 using trial_id {TRIAL_ID}.",
            "pair_rule": "No pair exists because exactly one factor passed both no-return gates.",
            "expected_single_trial_count": 1,
            "expected_pair_trial_count": 0,
            "expected_trial_count": 1,
        }
    )
    record["search_space"] = search
    output = copy.deepcopy(parent["research_output_boundary"])
    output.pop("campaign004_through_campaign046_rescue_or_reweight_allowed", None)
    output["campaign004_through_campaign047_rescue_or_reweight_allowed"] = False
    record["research_output_boundary"] = output
    write_new(PREREG, record)
    return PREREG


def record_semantic_failure() -> Path:
    record = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign048_development_namespace_semantic_failure",
        "status": "failed_closed_before_historical_daily_price_or_return_read",
        "recorded_at": "2026-08-01T05:15:00Z",
        "purpose": "Preserve the first Campaign048 development-boundary implementation failure before a corrected version is created.",
        "bindings": {
            "development_preregistration_v1": binding(PREREG),
            "development_runner_v1": binding(RUNNER),
            "no_return_audit_freeze": binding(AUDIT_FREEZE),
        },
        "observed_test_command": "PYTHONPATH=. pytest -q tests/data_collector_tests/test_a_share_three_day_walkforward_campaign048.py",
        "observed_test_file_sha256": sha256(TESTS),
        "observed_test_result": {"passed": 0, "failed": 4},
        "failure": {
            "class": "pre_return_development_namespace_binding_error",
            "detail": "The exact trial-id override was installed in the outer generated namespace while the inherited execution functions resolve build_trial_catalog in the inner engine namespace. Boundary tests also referenced DEFAULT_CAMPAIGN from the wrong namespace and a factor constant not exported by v3.",
            "development_preregistration_binding_count": 17,
            "development_preregistration_bindings_passed": 17,
            "runner_status_ledger_entry_count": 0,
            "runner_status_stress_intent_exists": False,
            "runner_status_stress_record_exists": False,
        },
        "immutability_and_repair": {
            "v1_preregistration_rewritten": False,
            "v1_runner_rewritten": False,
            "repair_requires_new_runner_and_preregistration_version": True,
        },
        "research_boundary": {
            "historical_daily_price_fields_read": [],
            "historical_forward_returns_read": False,
            "provider_request_issued": False,
            "candidate49_historical_return_signal_execution_or_milestone_backfill_performed": False,
            "candidate49_prospective_ledgers_changed": False,
            "candidate50_activation_created": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
        },
    }
    write_new(SEMANTIC_FAILURE, record)
    return SEMANTIC_FAILURE


def freeze() -> Path:
    import scripts.a_share_three_day_walkforward_campaign048_v2 as campaign
    import scripts.a_share_three_day_preregistration_binding_validator as validator

    validation = validator.validate_record(PREREG, data_root=DATA_ROOT)
    spec, observed = campaign.load_campaign(PREREG)
    catalog = campaign.build_trial_catalog(spec)
    before = campaign.status(
        argparse.Namespace(campaign=str(PREREG), output_root=str(OUTPUT_ROOT))
    )
    if (
        not validation["all_bindings_passed"]
        or observed != sha256(PREREG)
        or [item["trial_id"] for item in catalog] != [TRIAL_ID]
        or before.get("ledger_entry_count") != 0
        or before.get("stress_intent_exists") is not False
        or before.get("stress_record_exists") is not False
    ):
        raise RuntimeError("Campaign048 development pre-return boundary is not frozen")
    record = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign048_development_implementation_freeze",
        "status": "single_exact_trial_runner_and_all_bindings_frozen_before_2019_2023_return_read",
        "frozen_at": "2026-08-01T05:18:00Z",
        "purpose": "Bind the admitted factor, exact pre-value trial identifier, development runner, inherited three-fold protocol, closed search space, and conditional stress rule before historical daily prices or returns are read.",
        "bindings": {
            "development_preregistration": binding(PREREG),
            "development_runner": binding(RUNNER),
            "byte_bound_parent_runner": binding(
                REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign047.py"
            ),
            "pre_return_namespace_semantic_failure": binding(SEMANTIC_FAILURE),
            "no_return_audit_freeze": binding(AUDIT_FREEZE),
            "feature_runner": binding(FEATURE_RUNNER),
            "development_boundary_tests": binding(TESTS),
        },
        "frozen_trial_catalog": [
            {
                **catalog[0],
                "direction": "higher",
            }
        ],
        "walkforward_protocol": {
            "fold_count": 3,
            "folds": [
                {"fold": 1, "training": "2019-01-01..2020-12-31", "validation": "2021-01-01..2021-12-31"},
                {"fold": 2, "training": "2019-01-01..2021-12-31", "validation": "2022-01-01..2022-12-31"},
                {"fold": 3, "training": "2019-01-01..2022-12-31", "validation": "2023-01-01..2023-12-31"},
            ],
            "purge_signal_sessions_each_boundary": 3,
            "label_containment_required": True,
            "entry": "next accepted local session open t+1",
            "exit": "third accepted local session close t+3",
            "topk": 3,
        },
        "search_and_stress_boundary": {
            "expected_development_trial_count": 1,
            "alternate_direction_horizon_weight_filter_threshold_model_combination_or_year_subset_search": False,
            "every_trial_and_infrastructure_failure_must_be_retained": True,
            "stress_2024_2025_open_before_frozen_nonzero_development_survivor": False,
            "stress_pass_can_activate_candidate50_or_current_output": False,
        },
        "validation": {
            "preregistration_binding_count": validation["binding_count"],
            "preregistration_bindings_passed": validation["passed_binding_count"],
            "preregistration_bindings_failed": validation["failed_binding_count"],
            "trial_identifier_matches_no_return_preregistration": True,
            "trial_catalog_assertion_passed": True,
            "runner_status_before_execution": before,
            "development_boundary_tests_passed": 4,
            "development_boundary_tests_failed": 0,
        },
        "research_boundary_at_freeze": {
            "historical_daily_price_fields_read": [],
            "historical_forward_returns_read": False,
            "training_or_model_fitting_performed": False,
            "provider_request_issued": False,
            "candidate49_historical_return_signal_execution_or_milestone_backfill_performed": False,
            "candidate49_prospective_ledgers_changed": False,
            "candidate50_activation_created": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
        },
        "next_action": "Execute PYTHONPATH=. python scripts/a_share_three_day_walkforward_campaign048_v2.py run-development exactly once; retain every result and stop before 2024-2025 unless a frozen survivor exists.",
    }
    write_new(FREEZE, record)
    return FREEZE


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("preregister", "record-failure", "freeze"))
    args = parser.parse_args()
    if args.stage == "preregister":
        path = preregister()
    elif args.stage == "record-failure":
        path = record_semantic_failure()
    else:
        path = freeze()
    print(json.dumps({"path": str(path), "sha256": sha256(path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
