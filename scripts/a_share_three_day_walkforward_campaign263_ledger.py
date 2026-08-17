#!/usr/bin/env python3
"""Build Campaign263's append-only research-attempt ledgers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN_ROOT = (
    REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_263"
)
FAILED_PREDEVELOPMENT_LEDGER = CAMPAIGN_ROOT / "research_attempt_ledger_v1.json"
SUPERSEDED_PREDEVELOPMENT_LEDGERS = (
    CAMPAIGN_ROOT / "research_attempt_ledger_v2.json",
    CAMPAIGN_ROOT / "research_attempt_ledger_v3.json",
    CAMPAIGN_ROOT / "research_attempt_ledger_v4.json",
    CAMPAIGN_ROOT / "research_attempt_ledger_v5.json",
    CAMPAIGN_ROOT / "research_attempt_ledger_v6.json",
)
PREDEVELOPMENT_LEDGER = CAMPAIGN_ROOT / "research_attempt_ledger_v7.json"
PREDECESSOR = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_262/research_attempt_ledger_v4.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact(path: str) -> dict[str, Any]:
    target = REPO_ROOT / path
    if not target.is_file():
        raise RuntimeError(f"missing Campaign263 ledger artifact: {path}")
    return {"path": path, "sha256": _sha256(target)}


def _entry_hash(entry: dict[str, Any]) -> str:
    body = {key: value for key, value in entry.items() if key != "entry_sha256"}
    payload = json.dumps(
        body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def _entry(
    ordinal: int,
    attempt_id: str,
    attempt_class: str,
    phase: str,
    status: str,
    scientific_attempt: bool,
    result_consumed: bool,
    artifact_path: str,
    previous: str,
    route_id: str | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "ordinal": ordinal,
        "attempt_id": attempt_id,
        "attempt_class": attempt_class,
        "phase": phase,
        "status": status,
        "scientific_attempt": scientific_attempt,
        "result_consumed": result_consumed,
    }
    if route_id is not None:
        value["route_id"] = route_id
    value["artifact"] = _artifact(artifact_path)
    value["previous_entry_sha256"] = previous
    value["entry_sha256"] = _entry_hash(value)
    return value


def build_predevelopment() -> dict[str, Any]:
    predecessor = json.loads(PREDECESSOR.read_text(encoding="utf-8"))
    previous = str(predecessor["chain_tip_sha256"])
    entries: list[dict[str, Any]] = []

    def append(**kwargs: Any) -> None:
        nonlocal previous
        value = _entry(ordinal=len(entries) + 1, previous=previous, **kwargs)
        entries.append(value)
        previous = str(value["entry_sha256"])

    early = (
        "docs/a_share_three_day_walkforward_campaign_263_"
        "early_infrastructure_failures_20260816.json"
    )
    for number, status in enumerate(
        (
            "failed_skill_lines_241_360_output_truncated",
            "failed_skill_lines_361_480_output_truncated",
            "failed_skill_lines_601_660_output_truncated",
            "failed_skill_lines_1081_1110_output_truncated",
            "first_synthetic_feature_test_run_failed_18_passed_1_failed_due_to_extra_internal_column",
        ),
        1,
    ):
        append(
            attempt_id=f"campaign263_infrastructure_{number:03d}",
            attempt_class="infrastructure_failure",
            phase=(
                "mandatory_skill_read" if number <= 4 else "feature_builder_unit_test"
            ),
            status=status,
            scientific_attempt=False,
            result_consumed=False,
            artifact_path=early,
        )

    concept = (
        "docs/a_share_three_day_walkforward_campaign_263_"
        "concept_scouting_20260816.json"
    )
    scientific = (
        (
            "rejected_symmetric_price_impact_as_terminal_price_impact_and_return_amount_coupling_refresh",
            "prevalue_price_impact_overlap_audit",
            False,
            concept,
        ),
        (
            "rejected_running_drawdown_area_as_frozen_drawdown_frontier_ulcer_refresh",
            "prevalue_drawdown_overlap_audit",
            False,
            concept,
        ),
        (
            "rejected_complete_numeric_library_pairwise_interaction_as_terminal_model_refresh",
            "prevalue_complete_library_model_audit",
            False,
            concept,
        ),
        (
            "coverage_and_all_142_numeric_uniqueness_passed_ready_for_exactly_one_frozen_development_trial",
            "coverage_and_all_142_numeric_uniqueness",
            True,
            "data/experiments/short_horizon/historical_walkforward/campaign_263/uniqueness/campaign263_ordered_uniqueness_audit.json",
        ),
        (
            "rejected_spectral_concentration_as_direction_and_operator_sibling",
            "prevalue_operator_direction_audit",
            False,
            concept,
        ),
        (
            "rejected_half_session_entropy_resolution_as_aggregation_sweep",
            "prevalue_window_aggregation_audit",
            False,
            concept,
        ),
        (
            "rejected_selected_band_power_as_frequency_band_and_threshold_search",
            "prevalue_frequency_band_audit",
            False,
            concept,
        ),
        (
            "rejected_terminal_factor_combination_or_model_as_post_exposure_recombination",
            "prevalue_combination_model_audit",
            False,
            concept,
        ),
    )
    for route, (status, phase, consumed, artifact_path) in enumerate(scientific, 1):
        append(
            attempt_id=f"campaign263_scientific_{route:03d}",
            attempt_class=(
                "complete_factor_attempt"
                if route == 4
                else "prevalue_scientific_attempt"
            ),
            phase=phase,
            status=status,
            scientific_attempt=True,
            result_consumed=consumed,
            artifact_path=artifact_path,
            route_id=f"c263_{route:02d}",
        )

    failures = (
        (
            "candidate_snapshot_build",
            "failed_missing_nonempty_partition_quality_key_positive_amount_bars",
            "docs/a_share_three_day_walkforward_campaign_263_snapshot_build_quality_key_failure_20260816.json",
        ),
        (
            "implementation_freeze_boundary_validation",
            "failed_v2_freeze_bound_old_feature_builder_hash_before_retry",
            "docs/a_share_three_day_walkforward_campaign_263_implementation_freeze_v2_boundary_failure_20260816.json",
        ),
        (
            "candidate_snapshot_build",
            "failed_missing_partition_index_passthrough_key",
            "docs/a_share_three_day_walkforward_campaign_263_snapshot_build_partition_index_failure_20260816.json",
        ),
        (
            "candidate_snapshot_verification_cli",
            "failed_cli_used_data_root_instead_of_required_manifest_argument",
            "docs/a_share_three_day_walkforward_campaign_263_feature_snapshot_verification_cli_failure_20260816.json",
        ),
        (
            "ordered_uniqueness_unit_test",
            "failed_candidate_row_binding_expected_1330170_but_nested_runtime_retained_1330171",
            "docs/a_share_three_day_walkforward_campaign_263_ordered_uniqueness_row_binding_test_failure_20260816.json",
        ),
        (
            "ordered_uniqueness_candidate_loader",
            "failed_missing_nested_candidate_loader_symbol_before_comparators",
            "docs/a_share_three_day_walkforward_campaign_263_ordered_uniqueness_candidate_loader_failure_20260816.json",
        ),
        (
            "ordered_uniqueness_quality_key_loader",
            "failed_missing_nested_quality_listing_key_loader_before_comparators",
            "docs/a_share_three_day_walkforward_campaign_263_ordered_uniqueness_quality_key_loader_failure_20260816.json",
        ),
        (
            "ordered_uniqueness_candidate_eligible_count",
            "failed_inherited_loader_expected_total_rows_instead_of_manifest_bound_eligible_rows_before_comparators",
            "docs/a_share_three_day_walkforward_campaign_263_ordered_uniqueness_candidate_eligible_count_failure_20260816.json",
        ),
        (
            "predevelopment_attempt_ledger_generation",
            "failed_lifecycle_ledger_v1_transcribed_incorrect_complete_definition_order_digest",
            "docs/a_share_three_day_walkforward_campaign_263_predevelopment_ledger_library_digest_failure_20260816.json",
        ),
        (
            "development_runner_pre_activation_validation",
            "failed_black_check_after_eight_tests_passed_and_before_ruff",
            "docs/a_share_three_day_walkforward_campaign_263_development_formatting_failure_20260816.json",
        ),
        (
            "development_runner_recovery",
            "failed_apply_patch_context_for_v2_default_preregistration_path_without_file_change",
            "docs/a_share_three_day_walkforward_campaign_263_recovery_patch_context_failures_20260816.json",
        ),
        (
            "predevelopment_ledger_recovery",
            "failed_apply_patch_context_for_formatted_superseded_checkpoint_block_without_file_change",
            "docs/a_share_three_day_walkforward_campaign_263_recovery_patch_context_failures_20260816.json",
        ),
        (
            "development_preregistration_load",
            "failed_recovery_preregistration_top_level_version_2_rejected_by_frozen_version_1_engine",
            "docs/a_share_three_day_walkforward_campaign_263_preregistration_version_failure_20260816.json",
        ),
        (
            "preregistration_recovery_generator_update",
            "failed_apply_patch_context_for_formatted_hash_condition_without_file_change",
            "docs/a_share_three_day_walkforward_campaign_263_preregistration_recovery_patch_failure_20260816.json",
        ),
        (
            "development_preregistration_load",
            "failed_recovery_preregistration_changed_exact_status_and_top_level_field_set",
            "docs/a_share_three_day_walkforward_campaign_263_preregistration_header_contract_failure_20260816.json",
        ),
    )
    for number, (phase, status, artifact_path) in enumerate(failures, 6):
        append(
            attempt_id=f"campaign263_infrastructure_{number:03d}",
            attempt_class="infrastructure_failure",
            phase=phase,
            status=status,
            scientific_attempt=False,
            result_consumed=False,
            artifact_path=artifact_path,
        )

    if len(entries) != 28:
        raise RuntimeError("Campaign263 predevelopment attempt count changed")
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign263_append_only_research_attempt_ledger",
        "status": "campaign263_predevelopment_recovery_twenty_infrastructure_failures_eight_scientific_routes_one_complete_factor_attempt_all_142_uniqueness_gates_passed_zero_return_trials",
        "recorded_at": "2026-08-16T13:47:00Z",
        "timestamp_semantics": "monotonic logical append time before the first Campaign263 daily-price or forward-return value is read",
        "chain_hash_algorithm": "sha256_of_canonical_json_without_entry_sha256",
        "authoritative_predecessor": {
            "path": str(PREDECESSOR.relative_to(REPO_ROOT)),
            "sha256": _sha256(PREDECESSOR),
            "campaign_effective_entry_count": predecessor["effective_entry_count"],
            "cumulative_historical_research_attempt_count": predecessor[
                "cumulative_historical_research_attempt_count"
            ],
            "cumulative_return_reading_development_trial_count": predecessor[
                "cumulative_return_reading_development_trial_count"
            ],
            "chain_tip_sha256": predecessor["chain_tip_sha256"],
        },
        "effective_entry_count": len(entries),
        "effective_infrastructure_failure_attempt_count": 20,
        "effective_prevalue_scientific_attempt_count": 8,
        "effective_complete_factor_attempt_count": 1,
        "effective_return_reading_development_trial_count": 0,
        "cumulative_historical_research_attempt_count": 2591,
        "cumulative_return_reading_development_trial_count": 314,
        "library_state": {
            "complete_definition_appended_once": True,
            "complete_factor_definition_count": 162,
            "complete_factor_definition_order_sha256": "974f2c1f16a85eb43a0bd1e8db768dbe120cd8826c1754d5f220bf9f1d4a3ea0",
            "numeric_comparator_appended": False,
            "eligible_numeric_comparator_count": 142,
            "eligible_numeric_comparator_order_sha256": "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf",
        },
        "research_boundary": {
            "failed_or_truncated_output_used_as_scientific_or_validation_evidence": False,
            "candidate_snapshot_values_read": True,
            "numeric_comparator_values_read": True,
            "historical_daily_price_or_forward_return_values_read": False,
            "return_reading_development_trial_count": 0,
            "stress_2024_2025_opened": False,
            "provider_or_web_request_issued": False,
            "provider_credential_presence_value_or_digest_read": False,
            "candidate49_plan_or_run_executed": False,
            "candidate49_historical_backfill_performed": False,
            "candidate49_ledgers_changed": False,
            "second_prospective_candidate_created": False,
            "current_scoring_selection_sizing_positions_or_orders_performed": False,
            "investment_advice": False,
        },
        "candidate49": {
            "sole_prospective_candidate": True,
            "signal_entry_count": 0,
            "execution_entry_count": 0,
            "signal_ledger_sha256": "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79",
            "execution_ledger_sha256": "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f",
            "ledgers_changed": False,
        },
        "failed_lifecycle_ledgers_preserved": [
            {
                "path": str(FAILED_PREDEVELOPMENT_LEDGER.relative_to(REPO_ROOT)),
                "sha256": _sha256(FAILED_PREDEVELOPMENT_LEDGER),
                "reason": "incorrect_complete_definition_order_digest",
                "used_as_evidence": False,
            }
        ],
        "superseded_pre_return_checkpoints": [
            {
                "path": str(path.relative_to(REPO_ROOT)),
                "sha256": _sha256(path),
                "reason": "predates_the_latest_recorded_pre_return_infrastructure_failure",
                "used_as_effective_ledger": False,
            }
            for path in SUPERSEDED_PREDEVELOPMENT_LEDGERS
        ],
        "entries": entries,
        "chain_tip_sha256": previous,
    }


def main() -> int:
    CAMPAIGN_ROOT.mkdir(parents=True, exist_ok=True)
    payload = build_predevelopment()
    PREDEVELOPMENT_LEDGER.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "path": str(PREDEVELOPMENT_LEDGER),
                "sha256": _sha256(PREDEVELOPMENT_LEDGER),
                "entries": payload["effective_entry_count"],
                "chain_tip_sha256": payload["chain_tip_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
