from __future__ import annotations

import argparse
import hashlib
import json
import stat
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign100_features as inventory
from scripts import a_share_three_day_walkforward_campaign101_features as c101
from scripts import a_share_three_day_walkforward_campaign103 as c103
from scripts import a_share_three_day_walkforward_campaign105 as campaign
from scripts import (
    a_share_tushare_candidate49_future_session_workflow as future_workflow,
)


ROOT = Path(__file__).resolve().parents[2]
WALKFORWARD = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_105/walkforward"
)
TRIAL = WALKFORWARD / "trial_ledger.json"
SURVIVORS = WALKFORWARD / "development_survivors.json"
STRESS = WALKFORWARD / "exposed_stress_consumption_record.json"
GENERATED_REPORT = WALKFORWARD / "campaign_report.json"
ATTEMPT_LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_105/research_attempt_ledger_v7.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_105_terminal_result_binding_20260808.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v63_20260808.json"
)
STATE = (
    ROOT / "docs/a_share_three_day_iteration_status_20260808_campaign105_terminal.json"
)
FREEZE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_105_terminal_completion_freeze_20260808.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_terminal_artifact_hashes_are_exact() -> None:
    assert _sha(TRIAL) == (
        "035cda5d098347154603448e5cc4013ac7a0e88fc3743a1bfd2df3b14be16214"
    )
    assert _sha(SURVIVORS) == (
        "4b49942d4cc190154d8af6f5011197b25cbc85f19b53906ad7c585b1f4b27b01"
    )
    assert _sha(STRESS) == (
        "e9be4bbf4b514340c53c059233c1e713ea4ba2d3cd6f303ccbb02afad3f6df98"
    )
    assert _sha(GENERATED_REPORT) == (
        "4612304d45b1a09c7fc4d0901532ebcceaa6fc7551153a1676bfbc60d2c1570c"
    )
    assert _sha(ATTEMPT_LEDGER) == (
        "1a912bbc0c9cb3df436d23c199ce48fee09e51a78936385e636544e30d05eac5"
    )
    assert _sha(RESULT) == (
        "118820900341dc3a3d540abfab5676dabee439280469a33475a1953bbe6cecf9"
    )
    assert _sha(POLICY) == (
        "2ec29422ce2938c22307095879acfd60397f03c0c70355d68466fd4179ec4ce8"
    )


def test_terminal_result_replays_exact_fold_metrics_and_rejection() -> None:
    result = _load(RESULT)
    folds = result["development"]["fold_metrics"]
    assert [item["validation_year"] for item in folds] == [2021, 2022, 2023]
    assert [item["mean_rank_ic"] for item in folds] == [
        -0.030564640073120403,
        -0.01661724943333402,
        -0.043633808183873725,
    ]
    assert [item["normalized_return"] for item in folds] == [
        -0.2121512200636131,
        0.05246353641286916,
        -0.10210325806668785,
    ]
    assert [item["pilot_10bp_return"] for item in folds] == [
        -0.04864958425054067,
        -0.009515686649625987,
        -0.026594204342089034,
    ]
    decision = result["development"]["survivor_decision"]
    assert decision["operationally_admissible"] is True
    assert decision["positive_mean_rank_ic_fold_count"] == 0
    assert decision["positive_normalized_return_fold_count"] == 1
    assert decision["positive_pilot_return_fold_count"] == 0
    assert decision["development_aggregate_20bp_return"] == (-0.17951246869786153)
    assert decision["worst_validation_normalized_drawdown"] == (-0.32349362546556204)
    assert result["development"]["development_survivor_count"] == 0


def test_stress_is_closed_and_status_is_read_only() -> None:
    before = TRIAL.read_bytes()
    stress = _load(STRESS)
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    payload = campaign.status(
        argparse.Namespace(
            campaign=str(campaign.DEFAULT_PREREGISTRATION),
            output_root=str(WALKFORWARD),
        )
    )
    assert payload["ledger_entry_count"] == 1
    assert payload["selected_survivor_count"] == 0
    assert payload["stress_status"] == stress["status"]
    assert TRIAL.read_bytes() == before


def test_v63_appends_campaign105_to_both_exact_orders() -> None:
    assert bindings.validate_record(POLICY)["all_bindings_passed"] is True
    policy = _load(POLICY)
    additions = [
        {"name": inventory.FACTOR_NAME, "score_direction": "higher"},
        {"name": c101.FACTOR_NAME, "score_direction": "higher"},
        {"name": c103.ADMITTED_FACTOR, "score_direction": "higher"},
        {"name": campaign.ADMITTED_FACTOR, "score_direction": "higher"},
    ]
    complete = inventory.reconstruct_complete_definitions() + additions
    numeric = inventory.reconstruct_comparisons() + additions
    complete_policy = policy["complete_historical_feature_library"]
    numeric_policy = policy["numerical_comparator_eligibility"]
    assert len(complete) == complete_policy["factor_definition_count"] == 135
    assert inventory._order_digest(complete) == complete_policy["order_sha256"]
    assert len(numeric) == numeric_policy["eligible_numeric_comparator_count"] == 132
    assert inventory._order_digest(numeric) == (
        numeric_policy["eligible_numeric_comparator_order_sha256"]
    )


def test_candidate49_ledgers_and_dotenv_remain_safe() -> None:
    signal = (
        ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    )
    execution = (
        ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert _sha(signal) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha(execution) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert _load(signal)["entries"] == []
    assert _load(execution)["entries"] == []
    dotenv = ROOT / ".env"
    assert dotenv.is_file() and not dotenv.is_symlink()
    assert stat.S_IMODE(dotenv.stat().st_mode) == 0o600
    assert bool(future_workflow._load_token(dotenv)) is True


def test_unified_reports_expose_terminal_result_and_no_current_action() -> None:
    for path in (
        ROOT / "docs/a_share_three_day_walkforward_campaign_105_report.md",
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
        ROOT / "docs/a_share_data_pipeline.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "Campaign105" in text
        assert "-17.951247%" in text
        assert "2024–2025" in text
        assert "Candidate49" in text
        assert "投资建议" in text


def test_state_and_completion_freeze_are_absent_or_live() -> None:
    if not STATE.exists() or not FREEZE.exists():
        assert not STATE.exists() and not FREEZE.exists()
        return
    assert bindings.validate_record(STATE)["all_bindings_passed"] is True
    assert bindings.validate_record(FREEZE)["all_bindings_passed"] is True
    state = _load(STATE)
    assert state["campaign105_terminal"]["development_survivor_count"] == 0
    assert state["campaign105_terminal"]["stress_2024_2025_opened"] is False
    assert state["effective_future_numeric_policy"]["complete_definition_count"] == 135
    assert state["effective_future_numeric_policy"]["numeric_comparator_count"] == 132
