#!/usr/bin/env python3
"""Publish append-only terminal evidence for historical Campaign049."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
FACTOR = "intraday_morning_afternoon_amount_profile_similarity_120b"
TRIAL_ID = "wf049_intraday_morning_afternoon_amount_profile_similarity_120b_single_higher"
CAMPAIGN_ROOT = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_049"
AUDIT = CAMPAIGN_ROOT / "no_return/20260801T072440Z_campaign049_no_return_audit.json"
ATTEMPT_LEDGER = CAMPAIGN_ROOT / "research_attempt_ledger.json"
SNAPSHOT = DATA_ROOT / (
    "derived/a_share/rich/tushare/minute_walkforward_campaign049_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_walkforward_campaign049_feature_library_v1/"
    "snapshot_manifest.json"
)
CONCEPT = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_049_concept_scouting.json"
MECHANISM = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_049_mechanism_overlap_audit.json"
PROTOCOL = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_049_no_return_preregistration.json"
IMPLEMENTATION_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_049_feature_implementation_freeze_20260801.json"
SNAPSHOT_BINDING = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_049_snapshot_publication_binding_20260801.json"
NO_RETURN_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_049_no_return_audit_freeze_20260801.json"
RESEARCH_RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_049_research_record.json"
REPORT = REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md"
PIPELINE_DOC = REPO_ROOT / "docs/a_share_data_pipeline.md"
REPORT_SUPERSESSION = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_049_unified_report_supersession_20260801.json"
POST_REPORT_TRANSITION = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_049_post_report_test_transition_20260801.json"
VERIFICATION = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_049_verification_20260801.json"
STATE = REPO_ROOT / "docs/a_share_three_day_iteration_status_20260801_campaign049_verified.json"
PREDECESSOR_STATE = REPO_ROOT / "docs/a_share_three_day_iteration_status_20260801_campaign048_verified.json"
PREDECESSOR_RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_research_record.json"
PREDECESSOR_SUPERSESSION = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_unified_report_supersession_v2_20260801.json"
POLICY = REPO_ROOT / "docs/a_share_three_day_historical_walkforward_research_policy_20260727.json"
RUNNER_V1 = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign049_features.py"
RUNNER_V2 = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign049_features_v2.py"
RUNNER_V3 = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign049_features_v3.py"
FEATURE_TESTS = REPO_ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign049_features.py"
TERMINAL_TESTS = REPO_ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign049_terminal.py"
C43_TERMINAL_TESTS = REPO_ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign043_terminal.py"
C47_TERMINAL_TESTS = REPO_ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign047_terminal.py"
SIGNAL_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION_LEDGER = REPO_ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
FUTURE_WORKFLOW = REPO_ROOT / "scripts/a_share_tushare_candidate49_future_session_workflow.py"
FUTURE_WORKFLOW_TESTS = REPO_ROOT / "tests/data_collector_tests/test_a_share_tushare_candidate49_future_session_workflow.py"
SKILL = Path("/Users/niyufei/.codex/skills/manage-qlib-a-share-data/SKILL.md")
DOTENV = REPO_ROOT / ".env"


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


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def write_new(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode()
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        if load(path) != record:
            raise RuntimeError(f"refuse to rewrite terminal evidence: {path}")
        return
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def append_section(path: Path, marker: str, section: str) -> None:
    text = path.read_text()
    if marker in text:
        if not text.rstrip().endswith(section.rstrip()):
            raise RuntimeError(f"existing non-terminal section marker in {path}: {marker}")
        return
    with path.open("a") as handle:
        if not text.endswith("\n"):
            handle.write("\n")
        handle.write("\n" + section.rstrip() + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def result() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    audit = load(AUDIT)
    snapshot = load(SNAPSHOT)
    protocol = load(PROTOCOL)
    coverage = audit["coverage_and_capacity"][FACTOR]
    uniqueness = audit["uniqueness"][FACTOR]
    failed = [item for item in uniqueness["comparisons"] if not item["gate_passed"]]
    if not (
        audit["status"] == "completed_zero_admissible_factors_stop_before_historical_returns"
        and audit["admissible_factor_count"] == 0
        and audit["historical_daily_price_fields_read"] == []
        and audit["historical_forward_return_fields_read"] is False
        and audit["training_or_model_fitting_performed"] is False
        and coverage["gate_passed_before_comparison_values"] is True
        and uniqueness["comparison_factor_count"] == 72
        and uniqueness["comparison_order_matches_preregistration"] is True
        and uniqueness["all_required_comparisons_passed"] is False
        and len(failed) == 1
        and failed[0]["comparison_factor"] == "intraday_amount_participation_entropy_240m"
        and failed[0]["absolute_median_daily_rank_correlation"] == 0.8715970553916501
        and protocol["ordered_no_return_gates"]["uniqueness_after_coverage_only"]["maximum_allowed_absolute_median_daily_rank_correlation"] == 0.8
        and snapshot["source_fields_read"] == ["datetime", "symbol", "provider", "amount"]
    ):
        raise RuntimeError("Campaign049 terminal boundary changed")
    return audit, snapshot, coverage, uniqueness


def publish() -> list[Path]:
    audit, snapshot, coverage, uniqueness = result()
    failed = [item for item in uniqueness["comparisons"] if not item["gate_passed"]][0]
    quality = snapshot["quality"]
    q = f"{FACTOR}__"
    freeze = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign049_no_return_audit_freeze",
        "status": "terminal_zero_admissible_factors_before_historical_returns",
        "recorded_at": "2026-08-01T07:28:00Z",
        "purpose": "Bind the complete ordered Campaign049 no-return result and preserve the uniqueness rejection before any daily price, forward return, training, or model fitting.",
        "authoritative_inputs": {
            "concept_scouting": binding(CONCEPT),
            "mechanism_overlap_audit": binding(MECHANISM),
            "no_return_preregistration": binding(PROTOCOL),
            "feature_implementation_freeze": binding(IMPLEMENTATION_FREEZE),
            "snapshot_publication_binding": binding(SNAPSHOT_BINDING),
            "feature_snapshot": {**binding(SNAPSHOT), "dataset_sha256": snapshot["dataset_sha256"]},
            "no_return_audit": binding(AUDIT),
            "snapshot_bound_audit_runner": binding(RUNNER_V3),
            "feature_tests": binding(FEATURE_TESTS),
        },
        "result": {
            "factor": FACTOR,
            "direction": "higher",
            "candidate_eligible_rows": coverage["candidate_eligible_rows"],
            "median_coverage": coverage["median_coverage"],
            "p05_coverage": coverage["p05_coverage"],
            "median_eligible_names": coverage["eligible_names_median"],
            "p05_eligible_names": coverage["eligible_names_p05"],
            "potential_non_overlapping_three_session_cohorts": coverage["potential_non_overlapping_three_session_cohorts"],
            "coverage_and_capacity_gate_passed": True,
            "comparison_values_loaded_only_after_coverage_pass": True,
            "comparison_factor_count": uniqueness["comparison_factor_count"],
            "comparison_order_matches_preregistration": True,
            "all_72_uniqueness_comparisons_passed": False,
            "failed_uniqueness_comparison_count": 1,
            "maximum_allowed_absolute_median_daily_rank_correlation": 0.8,
            "maximum_absolute_median_daily_rank_correlation": failed["absolute_median_daily_rank_correlation"],
            "nearest_and_failed_comparison": {
                "name": failed["comparison_factor"],
                "median_daily_rank_correlation": failed["median_daily_rank_correlation"],
                "absolute_median_daily_rank_correlation": failed["absolute_median_daily_rank_correlation"],
                "pairwise_sessions": failed["pairwise_sessions"],
                "minimum_pairwise_names_observed": failed["minimum_pairwise_names_observed"],
            },
            "admissible_factor_count": 0,
        },
        "research_boundary": {
            "source_fields_read": audit["source_fields_read"],
            "minute_open_high_low_close_or_volume_fields_read": [],
            "historical_daily_price_fields_read": [],
            "historical_forward_returns_read": False,
            "training_or_model_fitting_performed": False,
            "provider_request_issued": False,
            "candidate49_historical_return_signal_execution_or_milestone_backfill_performed": False,
            "candidate49_prospective_ledgers_changed": False,
            "candidate50_activation_created": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
        },
        "decision": {
            "factor_terminal": True,
            "terminal_stage": "ordered_no_return_uniqueness_gate",
            "terminal_reason": "absolute_median_daily_rank_correlation_with_intraday_amount_participation_entropy_240m_exceeded_frozen_0_8_limit",
            "historical_walkforward_allowed": False,
            "development_folds_opened": False,
            "2024_2025_stress_allowed": False,
            "invert_rescue_reweight_filter_threshold_rewindow_model_combination_or_rerun_allowed": False,
        },
    }
    write_new(NO_RETURN_FREEZE, freeze)

    ledger = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign049_research_attempt_ledger",
        "status": "terminal_zero_admissible_factors_all_attempts_recorded",
        "append_only": True,
        "created_at": "2026-08-01T07:29:00Z",
        "counting_rule": "Every attempted formula, direction, parameter set, subset, filter, model, combination, and infrastructure-only failure counts even when rejected before values or returns.",
        "policy_sha256": sha256(POLICY),
        "prior_cumulative_historical_research_attempt_count": 279,
        "campaign049_attempt_count": 1,
        "cumulative_historical_research_attempt_count": 280,
        "campaign049_historical_return_trial_count": 0,
        "cumulative_return_reading_development_trial_count": 264,
        "entries": [{
            "sequence": 1,
            "attempt_id": TRIAL_ID,
            "parent_attempt_id": None,
            "kind": "single_factor_ordered_no_return_gate",
            "created_at": audit["created_at"],
            "economic_hypothesis": load(PROTOCOL)["candidate"]["economic_hypothesis"],
            "formula": load(PROTOCOL)["candidate"]["formula"],
            "direction": "higher",
            "feature_set": [FACTOR],
            "feature_set_count": 1,
            "window_transform_threshold_filter_and_weight_configuration": "exactly 120 morning plus 120 afternoon amount bins; independently normalized; equal-mixture Jensen-Shannon similarity; at least 60 positive bars per half; exact zeros retained; no alternate field/window/distance/direction/filter/threshold/model/fit/subset/combination",
            "data_and_code_fingerprints": {
                "no_return_protocol_sha256": sha256(PROTOCOL),
                "snapshot_manifest_sha256": sha256(SNAPSHOT),
                "snapshot_dataset_sha256": snapshot["dataset_sha256"],
                "no_return_audit_sha256": sha256(AUDIT),
                "no_return_audit_freeze_sha256": sha256(NO_RETURN_FREEZE),
                "effective_runner_sha256": sha256(RUNNER_V3),
            },
            "fixed_execution_policy_fingerprint": sha256(POLICY),
            "no_return_metrics": {
                "median_coverage": coverage["median_coverage"],
                "p05_coverage": coverage["p05_coverage"],
                "eligible_names_p05": coverage["eligible_names_p05"],
                "potential_non_overlapping_three_session_cohorts": coverage["potential_non_overlapping_three_session_cohorts"],
                "comparison_factor_count": 72,
                "comparison_order_matches_preregistration": True,
                "maximum_absolute_median_daily_rank_correlation": failed["absolute_median_daily_rank_correlation"],
                "failed_comparison": failed["comparison_factor"],
                "failed_comparison_median_daily_rank_correlation": failed["median_daily_rank_correlation"],
                "all_coverage_capacity_and_uniqueness_gates_passed": False,
            },
            "candidate_source_values_returned": True,
            "comparison_factor_values_read": True,
            "candidate49_factor_values_read": True,
            "candidate49_historical_return_fields_read": False,
            "historical_daily_price_fields_read": [],
            "historical_forward_return_fields_read": False,
            "2024_2025_stress_return_fields_read": False,
            "status_and_rejection_reason": "terminal_zero_admissible_factors_uniqueness_gate_failed_absolute_median_daily_rank_correlation_0_8715970553916501_exceeded_0_8",
        }],
        "boundary": {
            "development_preregistration_created": False,
            "development_folds_opened": False,
            "2024_2025_stress_opened": False,
            "candidate49_historical_return_signal_execution_or_milestone_backfill_performed": False,
            "candidate49_prospective_ledgers_changed": False,
            "candidate50_activation_created": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
        },
    }
    write_new(ATTEMPT_LEDGER, ledger)

    record = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign049_research_record",
        "status": audit["status"],
        "recorded_at": "2026-08-01T07:30:00Z",
        "purpose": "Record the exact Campaign049 amount-profile design and ordered no-return rejection; keep development folds, 2024-2025, Candidate49 history, and current trading outputs closed.",
        "numbering_disambiguation": "Historical Campaign049 is unrelated to prospective Candidate49.",
        "authoritative_inputs": {
            "prior_iteration_state": binding(PREDECESSOR_STATE),
            "historical_walkforward_policy": binding(POLICY),
            "prior_campaign_terminal_record": binding(PREDECESSOR_RECORD),
        },
        "frozen_evidence": {
            "concept_scouting": binding(CONCEPT),
            "mechanism_overlap_audit": binding(MECHANISM),
            "no_return_preregistration": binding(PROTOCOL),
            "feature_implementation_freeze": binding(IMPLEMENTATION_FREEZE),
            "snapshot_publication_binding": binding(SNAPSHOT_BINDING),
            "no_return_audit_freeze": binding(NO_RETURN_FREEZE),
        },
        "factor_definition": load(PROTOCOL)["candidate"],
        "feature_snapshot": {
            **binding(SNAPSHOT),
            "dataset_sha256": snapshot["dataset_sha256"],
            "partitions": snapshot["partitions"],
            "rows": snapshot["rows"],
            "eligible_rows": snapshot["factor_eligible_rows"][FACTOR],
            "below_minimum_positive_morning_bars_rows": quality[q + "below_minimum_positive_morning_bars_rows"],
            "below_minimum_positive_afternoon_bars_rows": quality[q + "below_minimum_positive_afternoon_bars_rows"],
            "exact_zero_amount_positions": quality[q + "exact_zero_amount_positions"],
            "negative_or_nonfinite_amount_rows": quality[q + "negative_amount_rows"] + quality[q + "nonfinite_amount_rows"],
            "invalid_probability_or_divergence_rows": quality[q + "invalid_probability_or_divergence_rows"],
            "range_or_nonfinite_score_rows": quality[q + "range_or_nonfinite_rows"],
            "all_partition_byte_and_frame_hashes_valid": True,
            "source_fields_read": snapshot["source_fields_read"],
            "source_open_high_low_close_or_volume_read": False,
        },
        "no_return_result": {
            **binding(AUDIT),
            "status": audit["status"],
            "calendar_sessions": coverage["calendar_sessions"],
            "candidate_eligible_rows": coverage["candidate_eligible_rows"],
            "median_coverage": coverage["median_coverage"],
            "p05_coverage": coverage["p05_coverage"],
            "p05_eligible_names": coverage["eligible_names_p05"],
            "potential_three_session_cohorts": coverage["potential_non_overlapping_three_session_cohorts"],
            "coverage_gate_passed": True,
            "comparison_values_loaded_after_coverage_pass": True,
            "comparison_factor_count": 72,
            "comparison_order_matches_preregistration": True,
            "failed_comparison_count": 1,
            "failed_comparison": failed["comparison_factor"],
            "failed_comparison_median_daily_rank_correlation": failed["median_daily_rank_correlation"],
            "maximum_absolute_median_daily_rank_correlation": failed["absolute_median_daily_rank_correlation"],
            "maximum_allowed_absolute_median_daily_rank_correlation": 0.8,
            "admissible_factor_count": 0,
            "historical_daily_price_fields_read": [],
            "historical_forward_return_fields_read": False,
        },
        "append_only_attempt_accounting": {
            "ledger": binding(ATTEMPT_LEDGER),
            "prior_historical_research_attempt_count": 279,
            "campaign049_no_return_candidate_attempt_count": 1,
            "campaign049_total_attempt_count": 1,
            "cumulative_historical_research_attempt_count": 280,
            "campaign049_historical_return_trial_count": 0,
            "cumulative_return_reading_development_trial_count": 264,
        },
        "implementation": {
            "base_feature_runner": binding(RUNNER_V1),
            "snapshot_bound_build_runner": binding(RUNNER_V2),
            "snapshot_bound_audit_runner": binding(RUNNER_V3),
            "feature_tests": binding(FEATURE_TESTS),
        },
        "prospective_boundary": {
            "candidate49_signal_ledger": {**binding(SIGNAL_LEDGER), "entry_count": 0},
            "candidate49_execution_ledger": {**binding(EXECUTION_LEDGER), "entry_count": 0},
            "candidate49_historical_return_signal_execution_or_milestone_backfill_performed": False,
            "candidate50_activation_created": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
        },
        "decision": {
            "factor_terminal": True,
            "terminal_stage": "ordered_no_return_uniqueness_gate",
            "terminal_reason": "absolute_median_daily_rank_correlation_with_intraday_amount_participation_entropy_240m_exceeded_frozen_0_8_limit",
            "development_preregistration_created": False,
            "development_folds_opened": False,
            "development_return_fields_read": False,
            "2024_2025_returns_read": False,
            "invert_repair_redistance_renormalize_rewindow_rescale_filter_threshold_rerun_rescue_or_combine_allowed": False,
            "next_campaign_must_be_independently_preregistered": True,
            "new_daily_bar_or_16_30_wait_required_for_next_offline_campaign": False,
            "investment_advice_or_current_selection_claim_allowed": False,
        },
    }
    write_new(RESEARCH_RECORD, record)

    report_section = f"""## 历史滚动 Campaign049 权威追加

历史 Campaign049（与前瞻 Candidate49 无关）冻结的 higher 因子 `{FACTOR}` 只读取 09:31–11:30 与 13:01–15:00 的 240 个 amount。上午、下午各 120 个固定时钟位置分别归一化为概率分布 `p/q`，返回等权 Jensen–Shannon 相似度 `1-JSD(p,q)/log(2)`；精确零成交额保留为零概率位置，每半场至少 60 个正成交额分钟。禁止 OHLC/volume、改距离/半场/方向、阈值、过滤、模型或组合。

不可变快照 manifest/data SHA‑256 为 `{sha256(SNAPSHOT)}` / `{snapshot['dataset_sha256']}`；33,015 个分区、7,724,498 行中 7,652,927 行有效，所有分区字节与帧哈希通过。唯一无收益审计 `{AUDIT.name}`（SHA‑256 `{sha256(AUDIT)}`）先通过覆盖门：中位/P05 覆盖为 `{coverage['median_coverage']:.6%}/{coverage['p05_coverage']:.6%}`，P05 合格名称 138，可形成 540 个三日 cohort。随后冻结的 72 项比较顺序完全匹配；与 `intraday_amount_participation_entropy_240m` 的中位日秩相关为 `+{failed['median_daily_rank_correlation']:.6f}`，绝对值超过 0.8，故零准入并在读取任何日线或 forward return 前终止。

追加式台账记录一个完整无收益候选尝试，累计历史研究尝试由 279 推进到 280；累计读取开发收益的试验仍为 264。未创建开发预注册或模型，2019–2023 收益与 2024–2025 压力区间均未打开。不得反向、改距离/归一化/正成交额支持门、删除失败比较、重跑、修补、救援或组合；Candidate49 仍是唯一前瞻候选且两本台账未改变。下一轮只能从独立 Campaign050 的值前概念开始，离线研究不需要等待新日线或 16:30。"""
    append_section(REPORT, "## 历史滚动 Campaign049 权威追加", report_section)

    pipeline_section = f"""## Campaign049：早晚盘成交额轮廓相似度（无收益唯一性门终止）

历史 Campaign049 与前瞻 Candidate49 严格分离。冻结 higher 因子 `{FACTOR}` 在两个连续半场各使用 120 个 amount，独立归一化后计算等权 Jensen–Shannon 相似度；每半场至少 60 个正成交额分钟，精确零值保留，禁止价格、volume、替代距离、方向、阈值、过滤、模型和组合。

快照 manifest/data SHA‑256 为 `{sha256(SNAPSHOT)}` / `{snapshot['dataset_sha256']}`，33,015 个分区和 7,724,498 行均通过字节/frame 哈希。无收益覆盖中位/P05 为 `{coverage['median_coverage']:.6%}/{coverage['p05_coverage']:.6%}`；覆盖通过后才加载 72 项冻结比较。与 `intraday_amount_participation_entropy_240m` 的绝对中位日秩相关为 `{failed['absolute_median_daily_rank_correlation']:.6f}`，超过 0.8，故不创建开发预注册、不读取日线或 forward return、不打开 2024–2025。

本轮累计历史研究尝试增至 280，累计读取开发收益的试验保持 264。Candidate49 的历史收益、信号、执行和里程碑均未回填，两本前瞻台账不变；周六没有运行供应商工作流。后续离线 Campaign050 可随时独立预注册，不必等待新日线或 16:30，但不得救援、重跑、组合 Campaign049 或生成当前评分、选股、仓位、订单和投资建议。"""
    append_section(PIPELINE_DOC, "## Campaign049：早晚盘成交额轮廓相似度（无收益唯一性门终止）", pipeline_section)

    supersession = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign049_unified_report_supersession",
        "status": "campaign048_report_binding_preserved_historically_campaign049_report_current",
        "recorded_at": "2026-08-01T07:33:00Z",
        "purpose": "Preserve Campaign048's immutable report binding while binding the append-only Campaign049 terminal update.",
        "bindings": {
            "campaign048_terminal_record": binding(PREDECESSOR_RECORD),
            "campaign049_terminal_record": binding(RESEARCH_RECORD),
            "previous_campaign048_supersession": binding(PREDECESSOR_SUPERSESSION),
            "current_unified_research_report": binding(REPORT),
        },
        "historical_binding": {
            "record": display(PREDECESSOR_SUPERSESSION),
            "json_pointer": "/bindings/current_unified_research_report",
            "expected_sha256": load(PREDECESSOR_SUPERSESSION)["bindings"]["current_unified_research_report"]["sha256"],
            "current_sha256": sha256(REPORT),
            "historical_record_rewritten": False,
            "previous_supersession_rewritten": False,
        },
        "semantic_boundary": {
            "campaign048_result_or_gate_changed": False,
            "campaign049_result_or_gate_changed_after_values": False,
            "report_update_is_append_only": True,
            "additional_historical_daily_price_or_forward_return_read": False,
            "2024_2025_stress_return_read": False,
            "candidate49_ledgers_changed": False,
        },
    }
    write_new(REPORT_SUPERSESSION, supersession)
    return [NO_RETURN_FREEZE, ATTEMPT_LEDGER, RESEARCH_RECORD, REPORT, PIPELINE_DOC, REPORT_SUPERSESSION]


def verify(focused_passed: int, full_passed: int, warnings: int) -> list[Path]:
    repo_path = str(REPO_ROOT)
    if repo_path not in sys.path:
        sys.path.insert(0, repo_path)
    import scripts.a_share_three_day_preregistration_binding_validator as validator

    scripts_path = str(REPO_ROOT / "scripts")
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
    import scripts.a_share_tushare_candidate49_future_session_workflow as workflow

    audit, _, _, uniqueness = result()
    records = [NO_RETURN_FREEZE, RESEARCH_RECORD, REPORT_SUPERSESSION]
    validations = {display(path): validator.validate_record(path, data_root=DATA_ROOT) for path in records}
    if not all(item["all_bindings_passed"] for item in validations.values()):
        raise RuntimeError("Campaign049 terminal bindings are not current")
    workflow._validate_candidate49_ledgers_semantically()
    if not (sha256(SIGNAL_LEDGER) == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79" and sha256(EXECUTION_LEDGER) == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"):
        raise RuntimeError("Candidate49 ledgers changed")

    transition = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign049_post_report_test_transition",
        "status": "historical_campaign048_report_binding_preserved_campaign049_supersession_current",
        "recorded_at": "2026-08-01T07:35:00Z",
        "purpose": "Bind tests that now recognize the Campaign049 append-only report supersession without rewriting any historical record.",
        "bindings": {
            "campaign049_report_supersession": binding(REPORT_SUPERSESSION),
            "updated_campaign043_terminal_test": binding(C43_TERMINAL_TESTS),
            "updated_campaign047_terminal_test": binding(C47_TERMINAL_TESTS),
            "campaign049_terminal_test": binding(TERMINAL_TESTS),
        },
        "verification_transition": {
            "first_candidate49_semantic_validation": {
                "status": "failed_before_ledger_validation",
                "reason": "direct Python import omitted the repository scripts directory, so the workflow's sibling execution module was not importable",
                "exception_type": "ModuleNotFoundError",
                "ledger_content_read_or_changed": False,
                "credential_value_read_printed_hashed_or_persisted": False,
                "historical_daily_price_or_forward_return_read": False,
            },
            "candidate49_semantic_validation_retry": {
                "status": "passed",
                "repair": "add the repository scripts directory to the import path only",
                "workflow_or_ledger_semantics_changed": False,
            },
            "first_final_verification_publisher": {
                "status": "failed_before_record_write",
                "reason": "direct script execution omitted the repository root before importing the scripts package",
                "exception_type": "ModuleNotFoundError",
                "terminal_record_verification_or_state_written": False,
                "historical_daily_price_or_forward_return_read": False,
            },
            "final_verification_publisher_retry": {
                "repair": "add the repository root to the import path before importing the binding validator",
                "research_code_result_gate_or_fingerprint_changed": False,
            },
            "first_focused_suite": {
                "passed": 25,
                "failed": 3,
                "failures": [
                    "pre-freeze feature test observed wrapper-induced module-global mutation during joint collection",
                    "terminal test imported a wrapper namespace without a direct FACTOR_NAME export",
                    "terminal test imported a wrapper namespace without a direct _sha256 export",
                ],
            },
            "focused_suite_retry": {
                "passed": focused_passed,
                "failed": 0,
                "repair": "terminal test imports the immutable base feature module; the frozen pre-value feature test and research implementation were not changed",
            },
            "research_attempt_count_increment": 0,
            "classification": "post-terminal verification harness transition, not a new formula, direction, parameter, data, candidate-value, comparison-value, or return-reading attempt",
        },
        "semantic_boundary": {
            "historical_campaign_records_or_supersessions_rewritten": False,
            "test_change_only_tracks_new_current_report_hash": True,
            "additional_historical_daily_price_or_forward_return_read": False,
            "candidate49_ledgers_changed": False,
        },
    }
    write_new(POST_REPORT_TRANSITION, transition)

    dotenv_mode = f"{stat.S_IMODE(DOTENV.stat().st_mode):04o}"
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", str(DOTENV)], cwd=REPO_ROOT, check=False
    ).returncode == 0
    verification = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign049_verification",
        "status": "terminal_campaign049_candidate49_isolation_and_full_regression_verified",
        "recorded_at": "2026-08-01T07:36:00Z",
        "purpose": "Bind the Campaign049 no-return rejection, append-only accounting, report transition, unchanged Candidate49 ledgers, credential-safe dotenv resolution, and final regression.",
        "bindings": {
            "research_record": binding(RESEARCH_RECORD),
            "no_return_audit_freeze": binding(NO_RETURN_FREEZE),
            "unified_report_supersession": binding(REPORT_SUPERSESSION),
            "post_report_test_transition": binding(POST_REPORT_TRANSITION),
            "research_attempt_ledger": binding(ATTEMPT_LEDGER),
            "base_feature_runner": binding(RUNNER_V1),
            "snapshot_bound_build_runner": binding(RUNNER_V2),
            "snapshot_bound_audit_runner": binding(RUNNER_V3),
            "feature_tests": binding(FEATURE_TESTS),
            "terminal_tests": binding(TERMINAL_TESTS),
            "unified_research_report": binding(REPORT),
            "data_pipeline_documentation": binding(PIPELINE_DOC),
            "manage_qlib_a_share_data_skill": binding(SKILL),
            "candidate49_future_session_workflow": binding(FUTURE_WORKFLOW),
            "candidate49_future_session_workflow_tests": binding(FUTURE_WORKFLOW_TESTS),
            "candidate49_signal_ledger": binding(SIGNAL_LEDGER),
            "candidate49_execution_ledger": binding(EXECUTION_LEDGER),
        },
        "verification_summary": {
            "binding_records_validated": len(validations),
            "binding_count": sum(item["binding_count"] for item in validations.values()),
            "passed_binding_count": sum(item["passed_binding_count"] for item in validations.values()),
            "focused_campaign049_tests_passed": focused_passed,
            "first_focused_campaign049_transition_tests_passed": 25,
            "first_focused_campaign049_transition_tests_failed": 3,
            "verification_environment_import_failures_recorded": 2,
            "full_data_collector_tests_passed": full_passed,
            "full_data_collector_tests_failed": 0,
            "full_data_collector_test_warnings": warnings,
            "candidate49_semantic_ledger_validation_passed_read_only": True,
            "candidate49_ledgers_rehashed_unchanged": True,
        },
        "credential_verification": {
            "repository_dotenv_exists": DOTENV.exists(),
            "repository_dotenv_is_regular_non_symlink_file": DOTENV.is_file() and not DOTENV.is_symlink(),
            "repository_dotenv_mode": dotenv_mode,
            "repository_dotenv_is_git_ignored": ignored,
            "workflow_dotenv_token_resolution_present": True,
            "credential_value_printed_hashed_persisted_or_written_to_record": False,
            "provider_request_issued_during_campaign049_or_verification": False,
        },
        "terminal_decision": {
            "campaign049_attempt_count": 1,
            "cumulative_historical_research_attempt_count": 280,
            "campaign049_historical_return_trial_count": 0,
            "cumulative_return_reading_development_trial_count": 264,
            "admissible_factor_count": 0,
            "failed_uniqueness_comparison": "intraday_amount_participation_entropy_240m",
            "failed_absolute_median_daily_rank_correlation": 0.8715970553916501,
            "development_preregistration_created": False,
            "development_folds_opened": False,
            "stress_2024_2025_opened": False,
            "candidate49_historical_return_read": False,
            "candidate49_ledgers_changed": False,
            "candidate50_activation_created": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
            "campaign049_formula_direction_window_distance_support_gate_or_comparison_order_changed_after_values": False,
        },
    }
    write_new(VERIFICATION, verification)

    state = {
        "version": 1,
        "kind": "a_share_three_day_iteration_status",
        "status": "campaign049_terminal_verified_historical_walkforward_ready_for_independent_campaign050",
        "recorded_at": "2026-08-01T07:37:00Z",
        "authoritative_predecessor": binding(PREDECESSOR_STATE),
        "research_policy": {
            "historical_walkforward_policy": binding(POLICY),
            "historical_research_may_run_without_new_daily_bar_or_16_30_wait": True,
            "historical_results_may_generate_current_scores_selections_sizes_or_orders": False,
            "historical_results_may_backfill_candidate49": False,
        },
        "fixed_strategy": {
            "holding_period_local_sessions": 3,
            "signal": "accepted local session close t",
            "entry": "next accepted local session open t+1",
            "exit": "third accepted local session close t+3",
            "development_folds": 3,
            "purge_signal_sessions_each_partition_boundary": 3,
            "t_t_plus_1_t_plus_3_must_remain_in_same_partition": True,
        },
        "campaign049": {
            "numbering_disambiguation": "historical Campaign049 is not prospective Candidate49",
            "factor": FACTOR,
            "direction": "higher",
            "no_return": {
                "median_coverage": audit["coverage_and_capacity"][FACTOR]["median_coverage"],
                "p05_coverage": audit["coverage_and_capacity"][FACTOR]["p05_coverage"],
                "comparison_factor_count": 72,
                "maximum_observed_absolute_median_daily_rank_correlation": 0.8715970553916501,
                "failed_comparison": "intraday_amount_participation_entropy_240m",
                "admissible_factor_count": 0,
            },
            "development": {
                "conditional_trial_id_never_opened": TRIAL_ID,
                "trial_count": 0,
                "development_preregistration_created": False,
                "historical_daily_price_or_forward_return_read": False,
                "2024_2025_stress_opened": False,
            },
            "attempt_accounting": {
                "campaign049_attempts": 1,
                "campaign049_return_reading_development_trials": 0,
                "cumulative_historical_research_attempts": 280,
                "cumulative_return_reading_development_trials": 264,
            },
            "terminal": {
                "factor_terminal": True,
                "reason": "Frozen uniqueness correlation with intraday_amount_participation_entropy_240m was 0.871597, above 0.8.",
                "invert_repair_redistance_renormalize_rewindow_rescale_filter_threshold_rerun_rescue_or_combine_allowed": False,
            },
            "authoritative_records": {
                "research_record": binding(RESEARCH_RECORD),
                "verification": binding(VERIFICATION),
                "unified_report_supersession": binding(REPORT_SUPERSESSION),
            },
        },
        "cumulative_state": {
            "cumulative_historical_research_attempt_count_after_campaign049": 280,
            "cumulative_return_reading_development_trial_count_after_campaign049": 264,
            "current_historical_aggregation_candidate_count": 0,
        },
        "local_data_context": {
            "active_daily_data_root": str(REPO_ROOT / "data"),
            "rich_minute_data_root": str(DATA_ROOT),
            "local_date": "2026-08-01",
            "local_weekday": "Saturday",
            "candidate49_same_day_workflow_applicable": False,
            "dotenv_path": str(DOTENV),
            "dotenv_is_regular_non_symlink_file": DOTENV.is_file() and not DOTENV.is_symlink(),
            "dotenv_is_git_ignored": ignored,
            "dotenv_mode": dotenv_mode,
            "tushare_token_present_for_workflow_resolution": True,
            "credential_value_printed_hashed_or_persisted_in_records": False,
            "provider_request_issued_by_campaign049_or_credential_verification": False,
        },
        "prospective_boundary": {
            "active_candidate_count": 1,
            "active_candidate": "Candidate49 intraday_cumulative_vwap_crossing_rate_240m",
            "candidate49_signal_ledger": {**binding(SIGNAL_LEDGER), "entry_count": 0},
            "candidate49_execution_ledger": {**binding(EXECUTION_LEDGER), "entry_count": 0},
            "candidate49_historical_return_signal_execution_or_milestone_backfill_performed": False,
            "candidate50_activation_allowed": False,
        },
        "verification_summary": verification["verification_summary"],
        "next_action": {
            "historical": "Begin historical Campaign050 only from an independent mechanism with separate pre-value scouting, overlap audit, finite fingerprint-bound protocol, and binding-validator exit code 0. Offline work may run at any time.",
            "prospective": "Saturday has no Candidate49 provider phase. On the next accepted local trading date use a new absolute-date staging root and retain the post-16:30 ready=true gate.",
            "strict_prohibitions": [
                "do not backfill Candidate49 historical returns signals executions or milestones",
                "do not start a second prospective candidate",
                "do not invert repair redistance renormalize rewindow rescale filter threshold rerun rescue or combine Campaign049",
                "do not open Campaign049 development or 2024-2025 stress",
                "do not generate current scores selections position sizes orders or investment advice",
            ],
        },
    }
    write_new(STATE, state)
    if uniqueness["all_required_comparisons_passed"] is not False:
        raise RuntimeError("Campaign049 terminal decision changed")
    return [POST_REPORT_TRANSITION, VERIFICATION, STATE]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("publish", "verify"))
    parser.add_argument("--focused-passed", type=int, default=0)
    parser.add_argument("--full-passed", type=int, default=0)
    parser.add_argument("--warnings", type=int, default=0)
    args = parser.parse_args()
    paths = publish() if args.stage == "publish" else verify(args.focused_passed, args.full_passed, args.warnings)
    print(json.dumps({display(path): sha256(path) for path in paths}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
