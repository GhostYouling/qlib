#!/usr/bin/env python3
"""Freeze Campaign048 concept, mechanism audit, and no-return protocol.

This command is deliberately pre-value: it reads only tracked control records and
never opens minute partitions, comparison values, daily prices, or returns.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any

try:
    import scripts.a_share_three_day_preregistration_binding_validator as bindings
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
RECORDED_AT = "2026-08-01T03:42:00Z"
FACTOR_NAME = "intraday_two_sided_wick_absorption_balance_240m"
FACTOR_FORMULA = (
    "Across exactly 240 bars at 09:31-11:30 and 13:01-15:00, define "
    "lower wick l_i=log(min(open_i,close_i)/low_i) and upper wick "
    "u_i=log(high_i/max(open_i,close_i)). Pool L=sum(l_i) and U=sum(u_i) "
    "and return 2*min(L,U)/(L+U)."
)
STATE_PATH = REPO_ROOT / "docs/a_share_three_day_iteration_status_20260801_campaign047_verified.json"
POLICY_PATH = REPO_ROOT / "docs/a_share_three_day_historical_walkforward_research_policy_20260727.json"
VALIDATOR_PATH = REPO_ROOT / "scripts/a_share_three_day_preregistration_binding_validator.py"
PREVIOUS_PROTOCOL_PATH = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_047_no_return_preregistration.json"
PREVIOUS_RECORD_PATH = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_047_research_record.json"
PREVIOUS_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign047_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign047_feature_library_v1/snapshot_manifest.json"
)
CONCEPT_PATH = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_concept_scouting.json"
MECHANISM_PATH = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_mechanism_overlap_audit.json"
PROTOCOL_PATH = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_no_return_preregistration.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def order_digest(comparisons: list[dict[str, str]]) -> str:
    payload = json.dumps(
        [(item["name"], item["score_direction"]) for item in comparisons],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_new(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        observed = json.loads(path.read_text(encoding="utf-8"))
        if observed != record:
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


def require_bindings(path: Path) -> None:
    report = bindings.validate_record(path, data_root=DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise RuntimeError(json.dumps(report, ensure_ascii=False, sort_keys=True))


def main() -> int:
    previous = json.loads(PREVIOUS_PROTOCOL_PATH.read_text(encoding="utf-8"))
    previous_manifest = json.loads(PREVIOUS_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    state_sha = sha256(STATE_PATH)
    policy_sha = sha256(POLICY_PATH)
    validator_sha = sha256(VALIDATOR_PATH)

    concept = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign048_concept_scouting",
        "status": "completed_before_campaign048_candidate_comparison_daily_price_or_return_values",
        "recorded_at": RECORDED_AT,
        "purpose": "Select one genuinely new historical-only minute mechanism after Campaign047 without using any candidate, comparison, price, or return value.",
        "authoritative_inputs": {
            "campaign047_verified_state": {"path": str(STATE_PATH.relative_to(REPO_ROOT)), "sha256": state_sha},
            "historical_walkforward_policy": {"path": str(POLICY_PATH.relative_to(REPO_ROOT)), "sha256": policy_sha},
            "campaign047_terminal_record": {"path": str(PREVIOUS_RECORD_PATH.relative_to(REPO_ROOT)), "sha256": sha256(PREVIOUS_RECORD_PATH)},
        },
        "candidate_design_catalog": [
            {
                "design": "two_sided_wick_absorption_balance",
                "decision": "selected",
                "reason": "It measures whether completed one-minute bars reject both upper and lower extremes in balance. No frozen factor pools only upper and lower wick distances and scores their two-sided balance."
            },
            {
                "design": "lower_wick_share_or_upper_wick_share",
                "decision": "rejected_before_values",
                "reason": "Choosing one side would create a direction search and reopen terminal close-location and body-direction pressure families."
            },
            {
                "design": "total_wick_share",
                "decision": "rejected_before_values",
                "reason": "Total wick share is the algebraic complement of terminal intrabar body-range efficiency and is not a new mechanism."
            },
            {
                "design": "wick_serial_persistence_entropy_or_subwindow_variants",
                "decision": "rejected_before_values",
                "reason": "Those variants create a family search around terminal range entropy, reversal, profile, and persistence definitions."
            },
            {
                "design": "range_frontier_overlap_or_revisit_variants",
                "decision": "rejected_before_values",
                "reason": "Record-frontier balance, adjacent overlap, and global revisit are already terminal mechanisms and use different range geometry."
            },
            {
                "design": "terminal_factor_combination_filter_threshold_or_model",
                "decision": "rejected_before_values",
                "reason": "Campaign048 contains one raw OHLC statistic and no historical terminal value, fitted weight, filter, threshold, regime, subset, combination, or model."
            },
        ],
        "selected_candidate": {
            "name": FACTOR_NAME,
            "direction": "higher",
            "economic_hypothesis": "Balanced rejection of both intraminute extremes is consistent with continuous two-sided liquidity absorption rather than one-sided pressure, potentially leaving a more resilient completed-session state for the next-open-to-third-close horizon.",
            "formula": FACTOR_FORMULA,
            "source_projection": ["datetime", "symbol", "provider", "open", "high", "low", "close"],
            "selected_grid": ["09:31-11:30", "13:01-15:00"],
            "selected_bar_count": 240,
            "include_0930": False,
            "include_lunch_transition": False,
            "support_rule": "All 240 bars must be finite, positive, and exactly ordered low<=min(open,close)<=max(open,close)<=high; require at least 120 bars with high>low.",
            "zero_semantics": "Retain exact-zero upper and lower wicks; require finite L+U>0.",
            "valid_range": [0.0, 1.0],
            "endpoint_canonicalization_tolerance": 1e-12,
            "transform_threshold_filter_combination_or_model": "none",
        },
        "research_boundary": {
            "external_minute_partitions_read": False,
            "candidate_or_comparison_values_read": False,
            "historical_daily_price_or_forward_return_read": False,
            "provider_request_issued": False,
            "candidate49_ledgers_changed": False,
            "candidate50_activation_created": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
        },
        "decision": {
            "selected_candidate_count": 1,
            "predictive_value_established": False,
            "next_action": "Complete a separate pre-value overlap audit against all 70 inherited comparisons plus terminal Campaign047, then freeze the exact 71-comparison no-return protocol.",
        },
    }
    write_new(CONCEPT_PATH, concept)
    require_bindings(CONCEPT_PATH)
    concept_sha = sha256(CONCEPT_PATH)

    mechanism = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign048_mechanism_overlap_audit",
        "status": "passed_conceptual_independence_before_campaign048_candidate_comparison_daily_price_or_return_values",
        "recorded_at": RECORDED_AT,
        "purpose": "Challenge the selected wick-balance mechanism against every nearby frozen family before any Campaign048 value is computed.",
        "authoritative_boundary": {"path": str(STATE_PATH.relative_to(REPO_ROOT)), "sha256": state_sha},
        "historical_walkforward_policy": {"path": str(POLICY_PATH.relative_to(REPO_ROOT)), "sha256": policy_sha},
        "concept_scouting": {"path": str(CONCEPT_PATH.relative_to(REPO_ROOT)), "sha256": concept_sha},
        "selected_mechanism": concept["selected_candidate"],
        "design_choices_frozen_before_values": {
            "formula_family": "own_bar_two_sided_upper_lower_wick_absorption_balance",
            "direction": "higher",
            "selected_bar_count": 240,
            "minimum_positive_range_bars": 120,
            "include_0930": False,
            "include_lunch_transition": False,
            "source_open_high_low_close_read": True,
            "source_volume_amount_read": False,
            "score": "2*min(sum_lower_wick,sum_upper_wick)/(sum_lower_wick+sum_upper_wick)",
            "exact_zero_wicks_retained": True,
            "parameter_filter_subset_model_or_combination_count": 0,
        },
        "overlap_challenges": [
            {"family": "intraday_intrabar_body_range_efficiency_240m", "result": "distinct_pending_statistical_uniqueness_gate", "reason": "Body efficiency allocates range to absolute open-close body. Campaign048 uses only residual upper/lower wick distances and scores their balance; total wick share is explicitly excluded."},
            {"family": "intraday_intrabar_close_location_pressure_240m", "result": "distinct_pending_statistical_uniqueness_gate", "reason": "Close-location pressure is directional around close and ignores open. Campaign048 is sign-symmetric, uses both open and close to define body boundaries, and rewards two-sided balance."},
            {"family": "intraday_two_sided_range_frontier_balance_238m", "result": "distinct_pending_statistical_uniqueness_gate", "reason": "Range-frontier balance measures fresh running-session extremes across time. Campaign048 is own-bar geometry and contains no running frontier or record event."},
            {"family": "intraday_adjacent_range_overlap_continuity_and_global_revisit", "result": "distinct_pending_statistical_uniqueness_gate", "reason": "Those factors compare or merge high-low intervals across bars. Campaign048 never compares price intervals across time."},
            {"family": "intraday_range_participation_entropy_reversal_and_profile_similarity", "result": "distinct_pending_statistical_uniqueness_gate", "reason": "Those mechanisms use total range magnitudes, their distribution, or serial/profile relation. Campaign048 aggregates only upper/lower wick components into one balance statistic."},
            {"family": "intraday_prior_range_breakout_pressure_and_microgap_absorption", "result": "distinct_pending_statistical_uniqueness_gate", "reason": "Those mechanisms use prior-bar boundaries or interbar gaps. Campaign048 uses no transition, gap, breakout, containment, or lag."},
            {"family": "campaign047_body_next_microgap_reversal", "result": "distinct_pending_statistical_uniqueness_gate", "reason": "Campaign047 uses open/close sequential body-to-next-gap correlation and reads no high/low. Campaign048 uses contemporaneous OHLC wick geometry and no lag or correlation."},
            {"family": "activity_market_quarterly_candidate49_and_terminal_combinations", "result": "distinct", "reason": "Campaign048 uses no volume, amount, VWAP, peer benchmark, disclosure, Candidate49 value, terminal value, fit, filter, or combination."},
        ],
        "research_boundary": concept["research_boundary"],
        "decision": {
            "conceptual_independence_passed": True,
            "statistical_independence_pending_all_71_comparisons": True,
            "predictive_value_established": False,
            "next_action": "Bind this record, append terminal Campaign047 to the inherited 70-factor order, freeze one exact post-admission trial, and run the binding validator before implementation.",
        },
    }
    write_new(MECHANISM_PATH, mechanism)
    require_bindings(MECHANISM_PATH)
    mechanism_sha = sha256(MECHANISM_PATH)

    gates = copy.deepcopy(previous["ordered_no_return_gates"])
    uniqueness = gates["uniqueness_after_coverage_only"]
    comparisons = copy.deepcopy(uniqueness["comparison_factors"])
    comparisons.append({"name": "intraday_body_next_microgap_reversal_238p", "score_direction": "higher"})
    uniqueness.update({
        "comparison_factor_count": 71,
        "comparison_factor_order_sha256": order_digest(comparisons),
        "comparison_factors": comparisons,
        "inherited_campaign047_comparison_factor_count": 70,
        "inherited_campaign047_comparison_factor_order_sha256": previous["ordered_no_return_gates"]["uniqueness_after_coverage_only"]["comparison_factor_order_sha256"],
        "campaign047_terminal_factor_is_final_comparison": True,
        "all_71_must_pass": True,
    })
    for stale in ("inherited_campaign046_comparison_factor_count", "inherited_campaign046_comparison_factor_order_sha256", "campaign046_terminal_factor_is_final_comparison", "all_70_must_pass"):
        uniqueness.pop(stale, None)

    source_chain = {
        "authoritative_state": {"path": str(STATE_PATH.relative_to(REPO_ROOT)), "sha256": state_sha},
        "historical_walkforward_policy": {"path": str(POLICY_PATH.relative_to(REPO_ROOT)), "sha256": policy_sha},
        "binding_validator": {"path": str(VALIDATOR_PATH.relative_to(REPO_ROOT)), "sha256": validator_sha},
        "concept_scouting": {"path": str(CONCEPT_PATH.relative_to(REPO_ROOT)), "sha256": concept_sha},
        "mechanism_overlap_audit": {"path": str(MECHANISM_PATH.relative_to(REPO_ROOT)), "sha256": mechanism_sha},
        "raw_minute_manifest": {
            "path_below_data_root": "raw/a_share/rich/tushare/minutes/1m/snapshots/tushare_stk_mins_1m_2019_2025_ea0cbb8f/snapshot_manifest.json",
            "sha256": "9b3d959563c9d182f38981c6a36bdb3bc9b415de08487a9e1f9e850825c0839f",
            "projected_columns": ["datetime", "symbol", "provider", "open", "high", "low", "close"],
            "forbidden_columns": ["volume", "amount"],
        },
        "joint_clean_manifest": copy.deepcopy(previous["source_chain"]["joint_clean_manifest"]),
        "campaign047_no_return_protocol": {
            "path": str(PREVIOUS_PROTOCOL_PATH.relative_to(REPO_ROOT)),
            "sha256": sha256(PREVIOUS_PROTOCOL_PATH),
            "factor_count": 70,
            "factor_order_sha256": previous["ordered_no_return_gates"]["uniqueness_after_coverage_only"]["comparison_factor_order_sha256"],
        },
        "campaign047_terminal_snapshot": {
            "path": str(PREVIOUS_SNAPSHOT_PATH),
            "sha256": sha256(PREVIOUS_SNAPSHOT_PATH),
            "dataset_sha256": previous_manifest["dataset_sha256"],
            "factor": "intraday_body_next_microgap_reversal_238p",
            "score_direction": "higher",
        },
        "campaign047_terminal_record": {"path": str(PREVIOUS_RECORD_PATH.relative_to(REPO_ROOT)), "sha256": sha256(PREVIOUS_RECORD_PATH)},
        "candidate49_signal_ledger": copy.deepcopy(previous["source_chain"]["candidate49_signal_ledger"]),
        "candidate49_execution_ledger": copy.deepcopy(previous["source_chain"]["candidate49_execution_ledger"]),
    }
    protocol = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign048_no_return_preregistration",
        "status": "frozen_before_campaign048_minute_candidate_comparison_daily_price_or_return_values",
        "frozen_at": RECORDED_AT,
        "purpose": "Freeze one finite Campaign048 candidate, all 71 no-return comparisons, and one conditional development trial before candidate values.",
        "source_chain": source_chain,
        "candidate": {
            "name": FACTOR_NAME,
            "direction": "higher",
            "formula": FACTOR_FORMULA,
            "economic_hypothesis": concept["selected_candidate"]["economic_hypothesis"],
            "source_projection": ["datetime", "symbol", "provider", "open", "high", "low", "close"],
            "forbidden_source_columns": ["volume", "amount"],
            "selected_bar_count": 240,
            "selected_grid": ["09:31-11:30", "13:01-15:00"],
            "include_0930": False,
            "include_lunch_transition": False,
            "lower_wick_definition": "natural log of min(open,close) divided by low",
            "upper_wick_definition": "natural log of high divided by max(open,close)",
            "aggregation": "pool all 240 upper and lower wick distances into L and U, then compute their two-sided balance",
            "minimum_positive_range_bars": 120,
            "zero_semantics": "Retain exact-zero upper/lower wicks and exact-zero ranges; require finite L+U>0.",
            "bar_ordering_rule": "every selected bar must satisfy finite positive low<=min(open,close)<=max(open,close)<=high exactly",
            "endpoint_canonicalization_tolerance": 1e-12,
            "valid_range": {"lower": 0.0, "lower_inclusive": True, "upper": 1.0, "upper_inclusive": True},
            "missing_rule": "Any duplicate, missing, or off-grid row; invalid or nonpositive OHLC; fewer than 120 positive-range bars; nonfinite wick, sum, denominator, or score; nonpositive L+U; or score outside [0,1] beyond 1e-12 makes the stock-day missing. Never fill, clip, winsorize, repair, or substitute.",
            "transform_scale_clip_threshold_filter": "none",
            "alternate_field_window_transform_direction_scale_board_year_cost_regime_fit_combination_or_model_search": False,
        },
        "ordered_no_return_gates": gates,
        "finite_development_catalog_if_admitted": {
            "trial_id": "wf048_intraday_two_sided_wick_absorption_balance_240m_single_higher",
            "kind": "single_factor",
            "feature_set": [FACTOR_NAME],
            "weights": [1.0],
            "complexity": 1,
            "expected_trial_count": 1,
            "weight_threshold_filter_window_year_cost_regime_or_model_search": False,
            "development_interval": ["2019-01-01", "2023-12-31"],
            "fold_count": 3,
            "purge_local_signal_sessions": 3,
            "t_plus_1_and_t_plus_3_must_remain_inside_partition": True,
            "stress_opening_rule": "2024-2025 may open exactly once only for the frozen development survivor",
        },
        "point_in_time_and_execution_semantics": copy.deepcopy(previous["point_in_time_and_execution_semantics"]),
        "research_boundary": {
            "external_campaign048_minute_partitions_read": False,
            "candidate_values_read": False,
            "comparison_values_read": False,
            "historical_daily_price_fields_read": False,
            "historical_forward_returns_read": False,
            "candidate49_historical_return_signal_execution_or_milestone_backfill_performed": False,
            "candidate49_ledgers_changed": False,
            "candidate50_activation_created": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
            "provider_request_issued": False,
            "investment_advice": False,
        },
        "decision": {
            "protocol_frozen": True,
            "binding_validator_must_pass_before_candidate_values": True,
            "candidate_values_may_open_only_after_implementation_freeze": True,
            "comparison_values_may_open_only_after_coverage_capacity_pass": True,
            "daily_price_and_returns_may_open_only_after_all_71_uniqueness_comparisons_pass": True,
        },
    }
    write_new(PROTOCOL_PATH, protocol)
    require_bindings(PROTOCOL_PATH)
    print(json.dumps({
        "status": "campaign048_pre_value_records_frozen_and_bindings_valid",
        "concept": {"path": str(CONCEPT_PATH), "sha256": sha256(CONCEPT_PATH)},
        "mechanism": {"path": str(MECHANISM_PATH), "sha256": sha256(MECHANISM_PATH)},
        "protocol": {"path": str(PROTOCOL_PATH), "sha256": sha256(PROTOCOL_PATH)},
        "comparison_factor_count": len(comparisons),
        "comparison_order_sha256": order_digest(comparisons),
        "candidate_or_return_values_read": False,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
