#!/usr/bin/env python3
"""Validate and publish Campaign132's corrected append-only terminal evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_132/walkforward_v3"
)
ORIGINAL_LEDGER = RUN_ROOT / "trial_ledger.json"
LEDGER_V2 = RUN_ROOT / "trial_ledger_v2.json"
ORIGINAL_REPORT = RUN_ROOT / "development_report.json"
SURVIVORS = RUN_ROOT / "development_survivors.json"
FAILURE_011 = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_132_validation_return_count_label_failure_20260814.json"
)
TERMINAL_RESULT = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_132_terminal_result_20260814.json"
)
TERMINAL_REPORT = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_132_terminal_report.md"
)
POLICY_V158 = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v158_20260814.json"
)
POLICY_V159 = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v159_20260814.json"
)
PRIOR_STATE = (
    REPO_ROOT
    / "docs/a_share_three_day_iteration_status_20260814_campaign131_prevalue_terminal_v4.json"
)
STATE = (
    REPO_ROOT
    / "docs/a_share_three_day_iteration_status_20260814_campaign132_terminal.json"
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

EXPECTED = {
    ORIGINAL_LEDGER: "7fb54d2e8a66187b2cef48150b7fb4f8ec7a5da98c8f0bdd4e5a635b7cf30a99",
    ORIGINAL_REPORT: "7a06c835eda37199496440a4eb12da87e75b10e81d5d1895dc803803b7798dbe",
    SURVIVORS: "b30981e40be5009cb906435b5e93ecaf36cb852e985679a491d4d65bfc69014b",
    FAILURE_011: "dc63dbd6e0a914549a36820cb17ef017ce7b5d675edcc1857af876a36f0459d6",
    POLICY_V158: "9e5c84c38aca839877a0723e35fcb7c4925127971da0e9d9789c24e55a239baf",
    PRIOR_STATE: "99371746a8ce6a1f2123975f74712808b99c306a3fe208433eefe208213da1e6",
    CANDIDATE49_SIGNAL: "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79",
    CANDIDATE49_EXECUTION: "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f",
}
CHAIN_GENESIS = "0" * 64


class Campaign132FinalizeError(RuntimeError):
    """Fail closed when immutable Campaign132 terminal evidence changes."""


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
        raise Campaign132FinalizeError(f"JSON object required: {path}")
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
            raise Campaign132FinalizeError("Campaign132 ledger predecessor changed")
        body = {key: value for key, value in entry.items() if key != "entry_sha256"}
        observed = str(entry.get("entry_sha256"))
        if observed != canonical_sha256(body):
            raise Campaign132FinalizeError("Campaign132 ledger entry digest changed")
        previous = observed
    if ledger.get("chain_tip_sha256") != previous:
        raise Campaign132FinalizeError("Campaign132 ledger tip changed")
    return previous


def summarize_models(
    ledger: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    models: list[dict[str, Any]] = []
    total_fold_reads = 0
    at_least_one = 0
    all_three = 0
    for entry in ledger["entries"]:
        if entry.get("phase") != "development_walkforward":
            continue
        validation_count = len(entry.get("validation_metrics") or [])
        total_fold_reads += validation_count
        at_least_one += int(validation_count > 0)
        all_three += int(validation_count == 3)
        folds: list[dict[str, Any]] = []
        for fold in entry["folds"]:
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
            metrics = fold.get("validation_metrics")
            folds.append(
                {
                    "fold": fold["fold"],
                    "uniqueness_passed": uniqueness["all_required_comparisons_passed"],
                    "failed_comparison_count": sum(
                        not item["gate_passed"] for item in comparisons
                    ),
                    "nearest_factor": nearest["comparison_factor"],
                    "nearest_absolute_median_daily_rank_correlation": nearest[
                        "absolute_median_daily_rank_correlation"
                    ],
                    "validation_return_read": metrics is not None,
                    "mean_rank_ic": (
                        None
                        if metrics is None
                        else metrics["association"]["mean_rank_ic"]
                    ),
                    "top3_minus_bottom3_gross_return": (
                        None
                        if metrics is None
                        else metrics["association"][
                            "mean_top3_minus_bottom3_gross_return"
                        ]
                    ),
                    "pilot_10bp_net_cumulative_return": (
                        None
                        if metrics is None
                        else metrics["pilot_execution_primary_10bp"][
                            "net_cumulative_return"
                        ]
                    ),
                    "pilot_20bp_net_cumulative_return": (
                        None
                        if metrics is None
                        else metrics["pilot_slippage_sensitivity"]["0.0020"][
                            "net_cumulative_return"
                        ]
                    ),
                    "normalized_net_cumulative_return": (
                        None
                        if metrics is None
                        else metrics["normalized_execution"]["net_cumulative_return"]
                    ),
                    "board_lot_affordability_rate": (
                        None
                        if metrics is None
                        else metrics["pilot_execution_primary_10bp"][
                            "board_lot_affordability_rate"
                        ]
                    ),
                }
            )
            model_binding = fold["fit"]["model_binary"]
            path = Path(model_binding["path"])
            if file_sha256(path) != model_binding["sha256"]:
                raise Campaign132FinalizeError("Campaign132 model binary changed")
            prefit_path = Path(fold["prefit_uniqueness_record"]["path"])
            if file_sha256(prefit_path) != fold["prefit_uniqueness_record"]["sha256"]:
                raise Campaign132FinalizeError("Campaign132 prefit record changed")
        models.append(
            {
                "trial_id": entry["trial_id"],
                "interaction_cst": entry["interaction_cst"],
                "status": entry["status"],
                "terminal_before_validation_return_reason": entry.get(
                    "terminal_before_validation_return_reason"
                ),
                "validation_return_fold_count": validation_count,
                "decision": entry["decision"],
                "folds": folds,
            }
        )
    if len(models) != 3:
        raise Campaign132FinalizeError("Campaign132 model trial count changed")
    return models, {
        "model_trials_with_at_least_one_validation_return_read": at_least_one,
        "total_model_fold_validation_return_reads": total_fold_reads,
        "model_trials_with_all_three_validation_folds_read": all_three,
    }


def append_failure(ledger: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(ledger))
    previous = validate_chain(result)
    entry = {
        "attempt_id": "campaign132_infrastructure_011",
        "phase": "infrastructure_failure",
        "stage": "postdevelopment_terminal_report_semantic_validation",
        "outcome": "failed_ambiguous_validation_return_reading_trial_count_label",
        "evidence": {
            "path": str(FAILURE_011.relative_to(REPO_ROOT)),
            "sha256": EXPECTED[FAILURE_011],
        },
        "scientific_result_changed": False,
        "historical_forward_return_fields_read_by_failure": False,
        "previous_entry_sha256": previous,
    }
    entry["entry_sha256"] = canonical_sha256(entry)
    result["entries"].append(entry)
    result["entry_count"] = len(result["entries"])
    result["infrastructure_failure_attempt_count"] = (
        int(result["infrastructure_failure_attempt_count"]) + 1
    )
    result["chain_tip_sha256"] = entry["entry_sha256"]
    result["supersedes_without_rewriting"] = {
        "path": str(ORIGINAL_LEDGER),
        "sha256": EXPECTED[ORIGINAL_LEDGER],
        "preserved": True,
    }
    validate_chain(result)
    return result


def validate_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    for path, expected in EXPECTED.items():
        if not path.is_file() or file_sha256(path) != expected:
            raise Campaign132FinalizeError(f"bound evidence changed: {path}")
    original = load_json(ORIGINAL_LEDGER)
    report = load_json(ORIGINAL_REPORT)
    survivors = load_json(SURVIVORS)
    validate_chain(original)
    if not (
        report.get("survivor_count") == 0
        and report.get("lockbox_2024_2025_opened") is False
        and survivors.get("selected_survivor_count") == 0
        and survivors.get("lockbox_return_fields_read") is False
        and report.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign132FinalizeError("Campaign132 terminal boundary changed")
    return original, report, survivors


def recorded_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def terminal_markdown(terminal: dict[str, Any]) -> str:
    rows = []
    for model in terminal["models"]:
        last = model["folds"][-1]
        rows.append(
            "| {trial} | {count} | {reason} | {factor} | {corr:.4f} |".format(
                trial=model["trial_id"],
                count=model["validation_return_fold_count"],
                reason=model["terminal_before_validation_return_reason"],
                factor=last["nearest_factor"],
                corr=last["nearest_absolute_median_daily_rank_correlation"],
            )
        )
    return "\n".join(
        [
            "# Campaign132 终止报告",
            "",
            "Campaign132 使用完整 140 个方向归一化数值因子和三种冻结的单调直方图梯度提升配置。开发期没有幸存者；2024–2025 准样本外锁箱未打开。本报告是历史研究证据，不构成投资建议。",
            "",
            "| 模型 | 已读取验证折数 | 终止原因 | 最近分量 | 绝对中位日 Rank 相关 |",
            "| --- | ---: | --- | --- | ---: |",
            *rows,
            "",
            "验证收益暴露的明确计数：3 个模型至少读取过一个验证折，共 5 个模型×折；完成全部三折的模型为 0。原始报告中的歧义字段保留不改写，并由追加台账纠正。",
            "",
            "Candidate49 信号与执行台账均未改变；未生成当前评分、选股、仓位或订单。",
            "",
        ]
    )


def finalize_evidence() -> dict[str, Any]:
    original, report, _ = validate_inputs()
    models, exposure = summarize_models(original)
    if exposure != {
        "model_trials_with_at_least_one_validation_return_read": 3,
        "total_model_fold_validation_return_reads": 5,
        "model_trials_with_all_three_validation_folds_read": 0,
    }:
        raise Campaign132FinalizeError("Campaign132 validation exposure changed")
    ledger_v2 = append_failure(original)
    atomic_json(LEDGER_V2, ledger_v2)
    ledger_binding = {"path": str(LEDGER_V2), "sha256": file_sha256(LEDGER_V2)}
    terminal = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign132_terminal_result",
        "status": "terminal_no_development_survivor_lockbox_closed",
        "recorded_at": recorded_at(),
        "campaign": 132,
        "authoritative_inputs": {
            "original_report": {
                "path": str(ORIGINAL_REPORT),
                "sha256": EXPECTED[ORIGINAL_REPORT],
            },
            "original_ledger": {
                "path": str(ORIGINAL_LEDGER),
                "sha256": EXPECTED[ORIGINAL_LEDGER],
            },
            "corrected_append_only_ledger": ledger_binding,
            "semantic_failure_correction": {
                "path": str(FAILURE_011.relative_to(REPO_ROOT)),
                "sha256": EXPECTED[FAILURE_011],
            },
        },
        "design": report["design_verification"],
        "structural_coverage": {
            "median_coverage": 0.9981273391821838,
            "p05_coverage": 0.992066409032738,
            "eligible_names_p05": 138.0,
            "potential_non_overlapping_three_session_cohorts": 540,
        },
        "accounting": {
            "attempt_count": ledger_v2["entry_count"],
            "prevalue_concept_attempt_count": 6,
            "infrastructure_failure_count": 11,
            "model_trial_count": 3,
            **exposure,
        },
        "models": models,
        "terminal_decision": {
            "development_survivor_count": 0,
            "selected_survivor_trial_ids": [],
            "2023_validation_returns_read_for_any_trial": False,
            "2024_2025_lockbox_opened": False,
            "campaign132_retry_repair_or_threshold_relaxation_allowed": False,
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
            "credential_loaded": False,
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
        "version": 159,
        "kind": "a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy",
        "status": "campaign132_terminal_no_survivor_campaign133_prevalue_scouting_allowed",
        "recorded_at": recorded_at(),
        "authoritative_inputs": {
            "policy_v158": {
                "path": str(POLICY_V158.relative_to(REPO_ROOT)),
                "sha256": EXPECTED[POLICY_V158],
            },
            "campaign132_ledger_v2": ledger_binding,
            "campaign132_terminal_result": terminal_binding,
        },
        "supersedes_without_rewriting": {
            "path": str(POLICY_V158.relative_to(REPO_ROOT)),
            "sha256": EXPECTED[POLICY_V158],
            "preserved": True,
            "library_order_changed": False,
        },
        "effective_accounting": {
            "campaign132_attempt_count": 20,
            "campaign132_infrastructure_failure_count": 11,
            "campaign132_prevalue_concept_attempt_count": 6,
            "campaign132_model_trial_count": 3,
            **exposure,
            "campaign132_development_survivor_count": 0,
            "campaign132_stress_trial_count": 0,
            "cumulative_historical_research_attempt_count": 1092,
            "cumulative_return_reading_development_trial_count": 310,
        },
        "complete_historical_feature_library": {
            "factor_definition_count": 151,
            "order_sha256": "91c2da3018330edbaddbb60b86370dcd9732425590f0565c70790b990002e0b5",
            "unchanged_from_v158": True,
        },
        "numerical_comparator_eligibility": {
            "eligible_numeric_comparator_count": 140,
            "eligible_numeric_comparator_order_sha256": "c71bfe27486c9567afd3aca21e4b04053658c23ac651e7f4df7fd014b0c31efd",
            "unchanged_from_v158": True,
            "campaign132_model_definition_eligible_now_or_later": False,
        },
        "campaign132_terminal_classification": {
            "terminal": True,
            "terminal_phase": "development_prefit_uniqueness_and_operational_gate",
            "selected_candidate_count": 0,
            "2023_validation_returns_read": False,
            "2024_2025_lockbox_opened": False,
            "retry_repair_reparameterization_threshold_relaxation_or_rescue_allowed": False,
        },
        "future_campaign_boundary": {
            "next_campaign": 133,
            "must_begin_from_genuinely_new_prevalue_mechanism_or_separately_accepted_historically_versioned_point_in_time_source": True,
            "campaign132_model_family_retry_or_rescue_allowed": False,
            "complete_library_historical_combinations_remain_allowed_only_when_new_and_prevalue_frozen": True,
        },
        "research_boundary": {
            "historical_2019_2022_price_or_return_values_read": True,
            "2023_validation_returns_read": False,
            "stress_2024_2025_opened": False,
            "provider_request_issued": False,
            "provider_credential_loaded": False,
            "candidate49_historical_backfill_performed": False,
            "candidate49_ledgers_changed": False,
            "second_prospective_candidate_created": False,
            "current_scoring_selection_sizing_positions_or_orders_performed": False,
            "investment_advice": False,
        },
        "next_action": "Continue Campaign133 prevalue scouting offline at any local time; Candidate49 remains the sole prospective ledger and Campaign132 stays terminal.",
    }
    atomic_json(POLICY_V159, policy)
    return {
        "status": terminal["status"],
        "ledger_v2": ledger_binding,
        "terminal_result": terminal_binding,
        "terminal_report": {
            "path": str(TERMINAL_REPORT),
            "sha256": file_sha256(TERMINAL_REPORT),
        },
        "policy_v159": {"path": str(POLICY_V159), "sha256": file_sha256(POLICY_V159)},
    }


def write_state() -> dict[str, Any]:
    validate_inputs()
    for path in (
        LEDGER_V2,
        TERMINAL_RESULT,
        TERMINAL_REPORT,
        POLICY_V159,
        CURRENT_REPORT,
        THREE_DAY_REPORT,
    ):
        if not path.is_file():
            raise Campaign132FinalizeError(f"state input missing: {path}")
    ledger = load_json(LEDGER_V2)
    terminal = load_json(TERMINAL_RESULT)
    policy = load_json(POLICY_V159)
    validate_chain(ledger)
    if not (
        ledger.get("entry_count") == 20
        and terminal.get("status") == "terminal_no_development_survivor_lockbox_closed"
        and policy.get("version") == 159
    ):
        raise Campaign132FinalizeError("corrected terminal state semantics changed")
    state = {
        "schema_version": 1,
        "kind": "a_share_three_day_iteration_status",
        "status": "campaign132_terminal_no_survivor_campaign133_prevalue_scouting_ready",
        "recorded_at": recorded_at(),
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
            "path": str(POLICY_V159.relative_to(REPO_ROOT)),
            "sha256": file_sha256(POLICY_V159),
            "factor_definition_count": 151,
            "factor_definition_order_sha256": "91c2da3018330edbaddbb60b86370dcd9732425590f0565c70790b990002e0b5",
            "numeric_comparator_count": 140,
            "numeric_comparator_order_sha256": "c71bfe27486c9567afd3aca21e4b04053658c23ac651e7f4df7fd014b0c31efd",
        },
        "campaign132": {
            "terminal": True,
            "terminal_result": {
                "path": str(TERMINAL_RESULT.relative_to(REPO_ROOT)),
                "sha256": file_sha256(TERMINAL_RESULT),
            },
            "corrected_append_only_ledger": {
                "path": str(LEDGER_V2.relative_to(REPO_ROOT)),
                "sha256": file_sha256(LEDGER_V2),
                "entry_count": 20,
                "chain_tip_sha256": ledger["chain_tip_sha256"],
            },
            "development_survivor_count": 0,
            "2023_validation_returns_read": False,
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
            "campaign132_terminal_report": {
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
        "next_action": "Continue Campaign133 genuinely new prevalue scouting offline; do not retry or rescue Campaign132 and do not open its lockbox.",
        "research_boundary": policy["research_boundary"],
    }
    atomic_json(STATE, state)
    return {
        "status": state["status"],
        "state": str(STATE),
        "sha256": file_sha256(STATE),
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
            validate_inputs()
            ledger = load_json(LEDGER_V2)
            terminal = load_json(TERMINAL_RESULT)
            state = load_json(STATE)
            validate_chain(ledger)
            payload = {
                "status": "verified",
                "ledger_entry_count": ledger["entry_count"],
                "terminal_status": terminal["status"],
                "state_status": state["status"],
                "candidate49_signal_sha256": file_sha256(CANDIDATE49_SIGNAL),
                "candidate49_execution_sha256": file_sha256(CANDIDATE49_EXECUTION),
            }
    except (Campaign132FinalizeError, FileNotFoundError, ValueError) as error:
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
