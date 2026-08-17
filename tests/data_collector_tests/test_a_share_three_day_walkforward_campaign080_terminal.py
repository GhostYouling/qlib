from __future__ import annotations

import hashlib
import json
import stat
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign080_features as features
from scripts import a_share_tushare_candidate49_future_session_workflow as future_workflow


ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "docs/a_share_three_day_iteration_status_20260806_campaign080_verified.json"
RECORD = ROOT / "docs/a_share_three_day_walkforward_campaign_080_research_record.json"
POLICY = ROOT / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v16_20260806.json"
FREEZE = ROOT / "docs/a_share_three_day_walkforward_campaign_080_terminal_completion_freeze_20260806.json"
TRIAL = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_080/walkforward/trial_ledger.json"
SURVIVORS = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_080/walkforward/development_survivors.json"
STRESS = ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_080/walkforward/exposed_stress_consumption_record.json"
REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_080_report.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_state_and_terminal_freeze_bindings_are_live() -> None:
    assert bindings.validate_record(STATE)["all_bindings_passed"] is True
    assert bindings.validate_record(FREEZE)["all_bindings_passed"] is True
    state = _load(STATE)
    assert state["status"].startswith("campaign080_terminal_verified_zero_survivors")
    assert state["campaign080_result"]["development_survivor_count"] == 0
    assert state["campaign080_result"]["stress_2024_2025_opened"] is False


def test_research_record_matches_the_frozen_no_return_and_development_results() -> None:
    assert bindings.validate_record(RECORD)["all_bindings_passed"] is True
    record = _load(RECORD)
    assert record["no_return_admission"]["uniqueness"]["comparisons_passed"] == 109
    assert record["no_return_admission"]["uniqueness"][
        "maximum_absolute_median_daily_rank_correlation"
    ] == 0.5120572125572724
    folds = record["development_trial"]["training_and_validation_folds"]
    assert [item["validation_mean_rank_ic"] for item in folds] == [
        -0.03407568185766916,
        -0.03777943451170531,
        -0.04791119048113904,
    ]
    assert record["development_trial"]["development_aggregate"][
        "pilot_20bp_return"
    ] == -0.17584418246214684


def test_trial_survivor_and_stress_records_are_terminal_and_closed() -> None:
    trial = _load(TRIAL)
    survivors = _load(SURVIVORS)
    stress = _load(STRESS)
    assert len(trial["entries"]) == 1
    assert trial["entries"][0]["trial_id"] == (
        "wf080_intraday_above_median_amount_longest_run_240m_single_higher"
    )
    assert survivors["selected_survivor_count"] == 0
    assert survivors["trial_decisions"][0]["positive_mean_rank_ic_fold_count"] == 0
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False


def test_v16_complete_and_numeric_orders_reconstruct_exactly() -> None:
    assert bindings.validate_record(POLICY)["all_bindings_passed"] is True
    policy = _load(POLICY)
    numeric = features.reconstruct_comparisons() + [
        {"name": features.FACTOR_NAME, "score_direction": "higher"}
    ]
    complete = features.reconstruct_complete_definitions() + [
        {"name": features.FACTOR_NAME, "score_direction": "higher"}
    ]
    assert len(numeric) == 110
    assert features._comparison_order_digest(numeric) == (
        "dc6319ac2f7c9d5811a8bee3f8fd9dbd174d2451739ef201aad31c36a9f25ce3"
    )
    assert len(complete) == 112
    assert features._comparison_order_digest(complete) == (
        "a31457db36af9a8ddac4e08890c87f50ef6554bb46918f022749bd9cccbc1c55"
    )
    assert policy["numerical_comparator_eligibility"][
        "eligible_numeric_comparator_count"
    ] == 110


def test_candidate49_ledgers_and_repository_dotenv_remain_safe() -> None:
    signal = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    execution = ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    assert _sha(signal) == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    assert _sha(execution) == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    assert _load(signal)["entries"] == []
    assert _load(execution)["entries"] == []
    dotenv = ROOT / ".env"
    assert dotenv.is_file() and not dotenv.is_symlink()
    assert stat.S_IMODE(dotenv.stat().st_mode) == 0o600
    assert bool(future_workflow._load_token(dotenv)) is True


def test_report_states_terminal_result_without_current_action() -> None:
    report = REPORT.read_text(encoding="utf-8")
    assert "109/109" in report
    assert "−9.90%" in report
    assert "−17.58%" in report
    assert "2024–2025 压力收益未打开" in report
    assert "不能生成当前评分、选股、仓位、订单或投资建议" in report
