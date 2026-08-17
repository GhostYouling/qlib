#!/usr/bin/env python3
"""Validate and publish Campaign133's append-only terminal evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_133/walkforward_v3"
)
ORIGINAL_LEDGER = RUN_ROOT / "trial_ledger.json"
LEDGER_V2 = RUN_ROOT / "trial_ledger_v2.json"
ORIGINAL_REPORT = RUN_ROOT / "development_report.json"
SURVIVORS = RUN_ROOT / "development_survivors.json"
PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_133_preregistration_20260814.json"
)
IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_133_development_implementation_freeze_v3_20260814.json"
)
POLICY_V159 = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v159_20260814.json"
)
POLICY_V160 = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v160_20260814.json"
)
PRIOR_STATE = (
    REPO_ROOT
    / "docs/a_share_three_day_iteration_status_20260814_campaign132_terminal.json"
)
STATE = (
    REPO_ROOT
    / "docs/a_share_three_day_iteration_status_20260814_campaign133_terminal.json"
)
TERMINAL_RESULT = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_133_terminal_result_20260814.json"
)
TERMINAL_REPORT = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_133_terminal_report.md"
)
CURRENT_REPORT = REPO_ROOT / "data/experiments/short_horizon/current_research_report.md"
THREE_DAY_REPORT = (
    REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md"
)
CANDIDATE49_SIGNAL = (
    REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
CANDIDATE49_EXECUTION = (
    REPO_ROOT
    / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
POSTRUN_FAILURES = (
    (
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_133_terminalization_jq_input_failure_20260814.json",
        "bb1ac62742692a5edba833d7ce20559bb971e92fe80b40ed548402705c0ef085",
    ),
    (
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_133_terminalization_metric_path_failure_20260814.json",
        "1d99a96a5d805efb3bba13cbcc019da81b4a595dad9908454dfba3e99e073453",
    ),
    (
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_133_terminalization_finalizer_filename_failure_20260814.json",
        "921bcbb7e58def7738487c67f1ff6558e9315755dafcfad739c9d4c74734ff88",
    ),
)

EXPECTED = {
    ORIGINAL_LEDGER: "6c11ffc4b6829fd2bd0bb3a1bf888f66e50731f286e67270ca705ae18433c86c",
    ORIGINAL_REPORT: "263078feb1b3c91bd3faadf9b5d86605d8f90d43a47d71fb1328becd9cab930f",
    SURVIVORS: "dc882c56ee405bb14ca6c0a7c6be02b64374ba848e30d0fecfec3c89cce87af5",
    PROTOCOL: "533cb1cc7738bf91afd0d08bd97757638fc07cc85edf8af35ff57c69031b7371",
    IMPLEMENTATION_FREEZE: "f585582fcdd8e5370bd113542b8a75e5df439902c3fb4afde000576ae2bde9d3",
    POLICY_V159: "e7665a5699cbb41b1f1a2ace542ce0dca2e43a53a99f66b51960c201991bce01",
    PRIOR_STATE: "02ec46710b18e4a66530cc5820444a5dd9a5c29aa03381a62c69a5cf83c31303",
    CANDIDATE49_SIGNAL: "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79",
    CANDIDATE49_EXECUTION: "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f",
    **dict(POSTRUN_FAILURES),
}
CHAIN_GENESIS = "0" * 64
RECORDED_AT = "2026-08-14T02:16:27.612961+00:00"


class Campaign133FinalizeError(RuntimeError):
    """Fail closed when immutable Campaign133 terminal evidence changes."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Campaign133FinalizeError(f"JSON object required: {path}")
    return value


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def validate_chain(ledger: dict[str, Any]) -> str:
    previous = CHAIN_GENESIS
    for entry in ledger.get("entries") or []:
        if entry.get("previous_entry_sha256") != previous:
            raise Campaign133FinalizeError("Campaign133 ledger predecessor changed")
        body = {key: value for key, value in entry.items() if key != "entry_sha256"}
        observed = str(entry.get("entry_sha256"))
        if observed != canonical_sha256(body):
            raise Campaign133FinalizeError("Campaign133 ledger entry digest changed")
        previous = observed
    if ledger.get("chain_tip_sha256") != previous:
        raise Campaign133FinalizeError("Campaign133 ledger tip changed")
    return previous


def require_binding(binding: dict[str, Any], label: str) -> Path:
    path = Path(str(binding.get("path")))
    if not path.is_absolute():
        path = REPO_ROOT / path
    if not path.is_file() or file_sha256(path) != binding.get("sha256"):
        raise Campaign133FinalizeError(f"{label} binding changed: {path}")
    return path


def validate_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    for path, expected in EXPECTED.items():
        if not path.is_file() or file_sha256(path) != expected:
            raise Campaign133FinalizeError(f"bound evidence changed: {path}")
    ledger = load_json(ORIGINAL_LEDGER)
    report = load_json(ORIGINAL_REPORT)
    survivors = load_json(SURVIVORS)
    validate_chain(ledger)
    if not (
        ledger.get("entry_count") == 10
        and ledger.get("prevalue_concept_attempt_count") == 6
        and ledger.get("infrastructure_failure_attempt_count") == 3
        and ledger.get("model_trial_attempt_count") == 1
        and report.get("trial_count") == 1
        and report.get("survivor_count") == 0
        and report.get("validation_return_reading_trial_count") == 1
        and report.get("lockbox_2024_2025_opened") is False
        and survivors.get("selected_survivor_count") == 0
        and survivors.get("lockbox_return_fields_read") is False
        and report.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign133FinalizeError("Campaign133 terminal boundary changed")
    return ledger, report, survivors


def summarize_trial(ledger: dict[str, Any]) -> dict[str, Any]:
    trials = [
        entry
        for entry in ledger["entries"]
        if entry.get("phase") == "development_walkforward"
    ]
    if len(trials) != 1:
        raise Campaign133FinalizeError("Campaign133 model trial count changed")
    trial = trials[0]
    folds: list[dict[str, Any]] = []
    for fold in trial["folds"]:
        uniqueness = fold["uniqueness"]
        comparisons = uniqueness["comparisons"]
        nearest = max(
            comparisons,
            key=lambda item: (
                item["absolute_median_daily_rank_correlation"]
                if item["absolute_median_daily_rank_correlation"] is not None
                else -1.0
            ),
        )
        if not (
            uniqueness.get("all_required_comparisons_passed") is True
            and uniqueness.get("comparison_count") == 140
            and len(comparisons) == 140
            and all(item.get("gate_passed") is True for item in comparisons)
            and float(nearest["absolute_median_daily_rank_correlation"]) < 0.8
            and fold.get("validation_metrics") is not None
        ):
            raise Campaign133FinalizeError("Campaign133 fold chronology gate changed")
        model_path = require_binding(fold["fit"]["model_binary"], "PAVA model")
        prefit_path = require_binding(
            fold["prefit_uniqueness_record"], "prefit uniqueness"
        )
        metrics_path = require_binding(
            fold["validation_metrics_binding"], "validation metrics"
        )
        prefit = load_json(prefit_path)
        metrics_record = load_json(metrics_path)
        score_path = require_binding(
            prefit["validation_score_snapshot"], "validation score snapshot"
        )
        if not (
            prefit.get("status") == "frozen_before_fold_validation_return_read"
            and prefit.get("validation_forward_return_fields_read_before_record")
            is False
            and metrics_record.get("status")
            == "completed_after_bound_prefit_uniqueness"
            and metrics_record.get("prefit_uniqueness_record")
            == fold["prefit_uniqueness_record"]
            and datetime.fromisoformat(prefit["created_at"])
            < datetime.fromisoformat(metrics_record["created_at"])
        ):
            raise Campaign133FinalizeError(
                "Campaign133 prefit-before-return evidence changed"
            )
        metrics = fold["validation_metrics"]
        folds.append(
            {
                "fold": fold["fold"],
                "model_binary_sha256": file_sha256(model_path),
                "validation_score_snapshot_sha256": file_sha256(score_path),
                "prefit_uniqueness_sha256": file_sha256(prefit_path),
                "validation_metrics_sha256": file_sha256(metrics_path),
                "uniqueness_passed": True,
                "comparison_count": 140,
                "nearest_factor": nearest["comparison_factor"],
                "nearest_absolute_median_daily_rank_correlation": nearest[
                    "absolute_median_daily_rank_correlation"
                ],
                "association_cohorts": metrics["association"]["cohorts"],
                "mean_rank_ic": metrics["association"]["mean_rank_ic"],
                "top3_minus_bottom3_gross_return": metrics["association"][
                    "mean_top3_minus_bottom3_gross_return"
                ],
                "normalized_net_cumulative_return": metrics["normalized_execution"][
                    "net_cumulative_return"
                ],
                "normalized_maximum_drawdown": metrics["normalized_execution"][
                    "maximum_drawdown"
                ],
                "pilot_10bp_net_cumulative_return": metrics[
                    "pilot_execution_primary_10bp"
                ]["net_cumulative_return"],
                "pilot_20bp_net_cumulative_return": metrics[
                    "pilot_slippage_sensitivity"
                ]["0.0020"]["net_cumulative_return"],
                "board_lot_affordability_rate": metrics["pilot_execution_primary_10bp"][
                    "board_lot_affordability_rate"
                ],
                "maximum_amount_participation": metrics["pilot_execution_primary_10bp"][
                    "maximum_filled_trade_daily_amount_participation"
                ],
                "terminal_unresolved_position_count": metrics[
                    "pilot_execution_primary_10bp"
                ]["terminal_unresolved_position_count"],
            }
        )
    if not (
        len(folds) == 3
        and len(trial.get("validation_metrics") or []) == 3
        and trial.get("status") == "development_rejected"
        and trial["decision"].get("passed") is False
        and trial["decision"].get("operationally_admissible") is True
        and trial["decision"].get("positive_mean_rank_ic_fold_count") == 0
        and trial["decision"].get("positive_normalized_return_fold_count") == 0
        and trial["decision"].get("positive_pilot_10bp_return_fold_count") == 0
    ):
        raise Campaign133FinalizeError("Campaign133 terminal trial decision changed")
    return {
        "trial_id": trial["trial_id"],
        "formula": trial["formula"],
        "status": trial["status"],
        "validation_return_fold_count": 3,
        "decision": trial["decision"],
        "folds": folds,
    }


def append_postrun_failures(ledger: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(ledger))
    previous = validate_chain(result)
    for path, expected in POSTRUN_FAILURES:
        failure = load_json(path)
        entry = {
            "attempt_id": failure["attempt_id"],
            "phase": "postrun_infrastructure_failure",
            "stage": failure["stage"],
            "outcome": failure["status"],
            "evidence": {
                "path": str(path.relative_to(REPO_ROOT)),
                "sha256": expected,
            },
            "scientific_result_changed": False,
            "campaign133_development_rerun_performed": False,
            "historical_forward_return_fields_read_by_failure": False,
            "previous_entry_sha256": previous,
        }
        entry["entry_sha256"] = canonical_sha256(entry)
        result["entries"].append(entry)
        previous = entry["entry_sha256"]
    result["entry_count"] = len(result["entries"])
    result["infrastructure_failure_attempt_count"] = int(
        result["infrastructure_failure_attempt_count"]
    ) + len(POSTRUN_FAILURES)
    result["chain_tip_sha256"] = previous
    result["supersedes_without_rewriting"] = {
        "path": str(ORIGINAL_LEDGER),
        "sha256": EXPECTED[ORIGINAL_LEDGER],
        "preserved": True,
    }
    validate_chain(result)
    return result


def terminal_markdown(terminal: dict[str, Any]) -> str:
    rows = []
    for fold in terminal["trial"]["folds"]:
        rows.append(
            "| {fold} | {corr:.4f} | {ic:.4f} | {spread:.4f} | {pilot:.2%} | {drawdown:.2%} |".format(
                fold=fold["fold"],
                corr=fold["nearest_absolute_median_daily_rank_correlation"],
                ic=fold["mean_rank_ic"],
                spread=fold["top3_minus_bottom3_gross_return"],
                pilot=fold["pilot_10bp_net_cumulative_return"],
                drawdown=fold["normalized_maximum_drawdown"],
            )
        )
    return "\n".join(
        [
            "# Campaign133 终止报告",
            "",
            "Campaign133 用完整 140 个方向统一因子测试了唯一一个 50% 原始分位锚定、10 档单调 PAVA 边际校准的等权组合。三个折都通过了对全部 140 个旧数值因子的预收益唯一性门槛，但三个验证折的 Rank IC、归一化收益和 10bp 资金试运行收益均为负，因此没有开发期幸存者。2024–2025 准样本外锁箱未打开。",
            "",
            "| 折 | 最近旧因子绝对相关 | Rank IC | Top3-Bottom3 | 10bp 资金收益 | 归一化最大回撤 |",
            "| ---: | ---: | ---: | ---: | ---: | ---: |",
            *rows,
            "",
            "该机制在可执行性约束上通过，但质量与收益聚合门槛失败；Campaign133 及其 PAVA 锚定组合家族终止，不允许重试、改参数、放松门槛或堆叠救援。",
            "",
            "Candidate49 信号与执行台账均未改变；未生成当前评分、选股、仓位或订单。本报告是历史研究证据，不构成投资建议。",
            "",
        ]
    )


def finalize_evidence() -> dict[str, Any]:
    ledger, report, _ = validate_inputs()
    trial = summarize_trial(ledger)
    ledger_v2 = append_postrun_failures(ledger)
    atomic_json(LEDGER_V2, ledger_v2)
    ledger_binding = {"path": str(LEDGER_V2), "sha256": file_sha256(LEDGER_V2)}
    terminal = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign133_terminal_result",
        "status": "terminal_no_development_survivor_lockbox_closed",
        "recorded_at": RECORDED_AT,
        "campaign": 133,
        "authoritative_inputs": {
            "protocol": {
                "path": str(PROTOCOL.relative_to(REPO_ROOT)),
                "sha256": EXPECTED[PROTOCOL],
            },
            "implementation_freeze_v3": {
                "path": str(IMPLEMENTATION_FREEZE.relative_to(REPO_ROOT)),
                "sha256": EXPECTED[IMPLEMENTATION_FREEZE],
            },
            "original_report": {
                "path": str(ORIGINAL_REPORT),
                "sha256": EXPECTED[ORIGINAL_REPORT],
            },
            "original_ledger": {
                "path": str(ORIGINAL_LEDGER),
                "sha256": EXPECTED[ORIGINAL_LEDGER],
            },
            "corrected_append_only_ledger": ledger_binding,
        },
        "design": report["design_verification"],
        "accounting": {
            "attempt_count": ledger_v2["entry_count"],
            "prevalue_concept_attempt_count": 6,
            "infrastructure_failure_count": 6,
            "model_trial_count": 1,
            "model_trials_with_at_least_one_validation_return_read": 1,
            "total_model_fold_validation_return_reads": 3,
            "model_trials_with_all_three_validation_folds_read": 1,
        },
        "trial": trial,
        "terminal_decision": {
            "development_survivor_count": 0,
            "selected_survivor_trial_ids": [],
            "all_three_validation_folds_read": True,
            "2024_2025_lockbox_opened": False,
            "campaign133_retry_repair_reparameterization_stack_or_threshold_relaxation_allowed": False,
        },
        "candidate49": {
            "only_active_prospective_candidate": True,
            "signal_ledger_sha256": EXPECTED[CANDIDATE49_SIGNAL],
            "signal_entry_count": 0,
            "execution_ledger_sha256": EXPECTED[CANDIDATE49_EXECUTION],
            "execution_entry_count": 0,
            "historical_backfill_performed": False,
            "ledgers_changed": False,
        },
        "research_boundary": {
            "provider_request_issued": False,
            "credential_value_or_digest_read": False,
            "current_scoring_selection_sizing_positions_or_orders_performed": False,
            "investment_advice": False,
        },
    }
    atomic_json(TERMINAL_RESULT, terminal)
    atomic_text(TERMINAL_REPORT, terminal_markdown(terminal))
    terminal_binding = {
        "path": str(TERMINAL_RESULT),
        "sha256": file_sha256(TERMINAL_RESULT),
    }
    policy = {
        "version": 160,
        "kind": "a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy",
        "status": "campaign133_terminal_no_survivor_campaign134_prevalue_scouting_allowed",
        "recorded_at": RECORDED_AT,
        "authoritative_inputs": {
            "policy_v159": {
                "path": str(POLICY_V159.relative_to(REPO_ROOT)),
                "sha256": EXPECTED[POLICY_V159],
            },
            "campaign133_ledger_v2": ledger_binding,
            "campaign133_terminal_result": terminal_binding,
        },
        "supersedes_without_rewriting": {
            "path": str(POLICY_V159.relative_to(REPO_ROOT)),
            "sha256": EXPECTED[POLICY_V159],
            "preserved": True,
            "library_order_changed": False,
        },
        "effective_accounting": {
            "campaign133_attempt_count": 13,
            "campaign133_infrastructure_failure_count": 6,
            "campaign133_prevalue_concept_attempt_count": 6,
            "campaign133_model_trial_count": 1,
            "campaign133_model_trials_with_at_least_one_validation_return_read": 1,
            "campaign133_total_model_fold_validation_return_reads": 3,
            "campaign133_model_trials_with_all_three_validation_folds_read": 1,
            "campaign133_development_survivor_count": 0,
            "campaign133_stress_trial_count": 0,
            "cumulative_historical_research_attempt_count": 1105,
            "cumulative_return_reading_development_trial_count": 311,
        },
        "complete_historical_feature_library": {
            "factor_definition_count": 151,
            "order_sha256": "91c2da3018330edbaddbb60b86370dcd9732425590f0565c70790b990002e0b5",
            "unchanged_from_v159": True,
        },
        "numerical_comparator_eligibility": {
            "eligible_numeric_comparator_count": 140,
            "eligible_numeric_comparator_order_sha256": "c71bfe27486c9567afd3aca21e4b04053658c23ac651e7f4df7fd014b0c31efd",
            "unchanged_from_v159": True,
            "campaign133_model_definition_eligible_now_or_later": False,
        },
        "campaign133_terminal_classification": {
            "terminal": True,
            "terminal_phase": "development_all_three_folds_quality_and_aggregate_gate",
            "selected_candidate_count": 0,
            "all_three_validation_folds_read": True,
            "2024_2025_lockbox_opened": False,
            "retry_repair_reparameterization_stack_threshold_relaxation_or_rescue_allowed": False,
        },
        "future_campaign_boundary": {
            "next_campaign": 134,
            "must_begin_from_genuinely_new_prevalue_mechanism_or_separately_accepted_historically_versioned_point_in_time_source": True,
            "campaign133_pava_anchor_family_retry_reparameterization_stack_or_rescue_allowed": False,
            "complete_library_historical_combinations_remain_allowed_only_when_new_and_prevalue_frozen": True,
        },
        "research_boundary": {
            "historical_2019_2023_price_or_return_values_read": True,
            "stress_2024_2025_opened": False,
            "provider_request_issued": False,
            "provider_credential_value_or_digest_read": False,
            "candidate49_historical_backfill_performed": False,
            "candidate49_ledgers_changed": False,
            "second_prospective_candidate_created": False,
            "current_scoring_selection_sizing_positions_or_orders_performed": False,
            "investment_advice": False,
        },
        "next_action": "Continue Campaign134 genuinely new prevalue scouting offline at any local time; Candidate49 remains the sole prospective ledger and Campaign133 stays terminal.",
    }
    atomic_json(POLICY_V160, policy)
    return {
        "status": terminal["status"],
        "ledger_v2": ledger_binding,
        "terminal_result": terminal_binding,
        "terminal_report": {
            "path": str(TERMINAL_REPORT),
            "sha256": file_sha256(TERMINAL_REPORT),
        },
        "policy_v160": {"path": str(POLICY_V160), "sha256": file_sha256(POLICY_V160)},
    }


def write_state() -> dict[str, Any]:
    validate_inputs()
    for path in (
        LEDGER_V2,
        TERMINAL_RESULT,
        TERMINAL_REPORT,
        POLICY_V160,
        CURRENT_REPORT,
        THREE_DAY_REPORT,
    ):
        if not path.is_file():
            raise Campaign133FinalizeError(f"state input missing: {path}")
    ledger = load_json(LEDGER_V2)
    terminal = load_json(TERMINAL_RESULT)
    policy = load_json(POLICY_V160)
    validate_chain(ledger)
    if not (
        ledger.get("entry_count") == 13
        and terminal.get("status") == "terminal_no_development_survivor_lockbox_closed"
        and policy.get("version") == 160
    ):
        raise Campaign133FinalizeError("Campaign133 terminal state semantics changed")
    state = {
        "schema_version": 1,
        "kind": "a_share_three_day_iteration_status",
        "status": "campaign133_terminal_no_survivor_campaign134_prevalue_scouting_ready",
        "recorded_at": RECORDED_AT,
        "authoritative_predecessor": {
            "path": str(PRIOR_STATE.relative_to(REPO_ROOT)),
            "sha256": EXPECTED[PRIOR_STATE],
        },
        "historical_research_policy": {
            "path": "docs/a_share_three_day_historical_walkforward_research_policy_20260727.json",
            "sha256": "38426d6161b9bfed323c58caba18feca668b8c9d53e294951a8ba90c01a798bb",
            "offline_historical_walkforward_is_primary_engine": True,
            "does_not_wait_for_16_30_or_new_daily_bar": True,
        },
        "numeric_policy": {
            "path": str(POLICY_V160.relative_to(REPO_ROOT)),
            "sha256": file_sha256(POLICY_V160),
            "factor_definition_count": 151,
            "factor_definition_order_sha256": "91c2da3018330edbaddbb60b86370dcd9732425590f0565c70790b990002e0b5",
            "numeric_comparator_count": 140,
            "numeric_comparator_order_sha256": "c71bfe27486c9567afd3aca21e4b04053658c23ac651e7f4df7fd014b0c31efd",
        },
        "campaign133": {
            "terminal": True,
            "terminal_result": {
                "path": str(TERMINAL_RESULT.relative_to(REPO_ROOT)),
                "sha256": file_sha256(TERMINAL_RESULT),
            },
            "corrected_append_only_ledger": {
                "path": str(LEDGER_V2.relative_to(REPO_ROOT)),
                "sha256": file_sha256(LEDGER_V2),
                "entry_count": 13,
                "chain_tip_sha256": ledger["chain_tip_sha256"],
            },
            "development_survivor_count": 0,
            "all_three_validation_folds_read": True,
            "2024_2025_lockbox_opened": False,
            "retry_or_rescue_allowed": False,
        },
        "effective_accounting": policy["effective_accounting"],
        "candidate49": {
            "only_active_prospective_candidate": True,
            "signal_ledger_sha256": file_sha256(CANDIDATE49_SIGNAL),
            "signal_entry_count": 0,
            "execution_ledger_sha256": file_sha256(CANDIDATE49_EXECUTION),
            "execution_entry_count": 0,
            "historical_backfill_performed": False,
            "prospective_registration_changed": False,
        },
        "candidate49_daily_20260814": {
            "local_day": "Friday",
            "before_same_day_16_30_gate_during_this_iteration": True,
            "plan_executed": False,
            "run_executed": False,
            "staging_root_created_or_reused": False,
        },
        "reports": {
            "campaign133_terminal_report": {
                "path": str(TERMINAL_REPORT.relative_to(REPO_ROOT)),
                "sha256": file_sha256(TERMINAL_REPORT),
            },
            "current_research_report": {
                "path": str(CURRENT_REPORT.relative_to(REPO_ROOT)),
                "sha256": file_sha256(CURRENT_REPORT),
            },
            "three_day_research_report": {
                "path": str(THREE_DAY_REPORT.relative_to(REPO_ROOT)),
                "sha256": file_sha256(THREE_DAY_REPORT),
            },
        },
        "next_action": "Continue Campaign134 genuinely new prevalue scouting offline; do not retry, restack or rescue Campaign133 and do not open its lockbox.",
        "research_boundary": policy["research_boundary"],
    }
    atomic_json(STATE, state)
    return {
        "status": state["status"],
        "state": str(STATE),
        "sha256": file_sha256(STATE),
    }


def verify() -> dict[str, Any]:
    validate_inputs()
    ledger = load_json(LEDGER_V2)
    terminal = load_json(TERMINAL_RESULT)
    policy = load_json(POLICY_V160)
    state = load_json(STATE)
    validate_chain(ledger)
    if not (
        terminal.get("terminal_decision", {}).get("2024_2025_lockbox_opened") is False
        and policy.get("version") == 160
        and state.get("campaign133", {}).get("development_survivor_count") == 0
        and file_sha256(CANDIDATE49_SIGNAL) == EXPECTED[CANDIDATE49_SIGNAL]
        and file_sha256(CANDIDATE49_EXECUTION) == EXPECTED[CANDIDATE49_EXECUTION]
    ):
        raise Campaign133FinalizeError(
            "Campaign133 published terminal evidence changed"
        )
    return {
        "status": "verified",
        "ledger_entry_count": ledger["entry_count"],
        "terminal_status": terminal["status"],
        "state_status": state["status"],
        "campaign133_survivor_count": 0,
        "lockbox_2024_2025_opened": False,
        "candidate49_signal_sha256": file_sha256(CANDIDATE49_SIGNAL),
        "candidate49_execution_sha256": file_sha256(CANDIDATE49_EXECUTION),
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument(
        "command", choices=("finalize-evidence", "write-state", "verify")
    )
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "finalize-evidence":
            payload = finalize_evidence()
        elif args.command == "write-state":
            payload = write_state()
        else:
            payload = verify()
    except (Campaign133FinalizeError, FileNotFoundError, ValueError) as error:
        print(
            json.dumps(
                {"status": "failed", "error": str(error)}, ensure_ascii=False, indent=2
            )
        )
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
