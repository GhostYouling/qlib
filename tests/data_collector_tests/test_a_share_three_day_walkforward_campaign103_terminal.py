from __future__ import annotations

import argparse
import hashlib
import json
import stat
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign100_features as inventory
from scripts import a_share_three_day_walkforward_campaign101_features as c101
from scripts import a_share_three_day_walkforward_campaign103 as campaign

ROOT = Path(__file__).resolve().parents[2]
WALKFORWARD = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_103/walkforward"
)
INTERNAL_LEDGER = WALKFORWARD / "trial_ledger.json"
SURVIVORS = WALKFORWARD / "development_survivors.json"
STRESS = WALKFORWARD / "exposed_stress_consumption_record.json"
GENERATED_REPORT = WALKFORWARD / "campaign_report.json"
ATTEMPT_LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_103/research_attempt_ledger_v1.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_103_terminal_result_binding_20260808.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v60_20260808.json"
)
STATE = ROOT / "docs/a_share_three_day_iteration_status_20260808_campaign103_terminal.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _value_sha256(value: dict) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def test_terminal_artifact_hashes_are_exact() -> None:
    assert _sha256(INTERNAL_LEDGER) == (
        "244fd32d508138fbcdfb6a432d528037d3f1548dd70f2f6a01aac8eb2bb810c2"
    )
    assert _sha256(SURVIVORS) == (
        "8a3adecd90aa26031316cd5352f67ae7bbb6f975c36bf4f30d12be7b5cabb749"
    )
    assert _sha256(STRESS) == (
        "c2fc3e0fcf041729365d12116796e539a79483aed0286d57b26bd8e34b0b18d6"
    )
    assert _sha256(GENERATED_REPORT) == (
        "b5a398d6a4a273b330dc731b6d1fe44221a3bccbaa97d695232df205e7302b01"
    )
    assert _sha256(ATTEMPT_LEDGER) == (
        "0ad84fd42d406fd9ab6f288d9a8139cad9af7189f98d7a2fabe929a19af35bdd"
    )
    assert _sha256(RESULT) == (
        "a5131ed43186564a4161cdbb0669a25d65aa501379ba722bfb15a0bc23d950f2"
    )
    assert _sha256(POLICY) == (
        "8342009361e8d45bdff47706917d25c05ddaaa1ced9285a3303da3e9ad38100b"
    )


def test_internal_ledger_has_two_failures_and_one_complete_trial() -> None:
    ledger = _load(INTERNAL_LEDGER)
    assert [entry["ordinal"] for entry in ledger["entries"]] == [1, 2, 3]
    assert [entry["phase"] for entry in ledger["entries"]] == [
        "infrastructure_failure",
        "infrastructure_failure",
        "development_walkforward_2019_2023",
    ]
    trial = ledger["entries"][-1]
    assert trial["trial_id"] == campaign.FROZEN_TRIAL_ID
    assert trial["status_and_rejection_reason"]["status"] == (
        "development_walkforward_completed"
    )
    assert ledger["chain_tip_sha256"] == trial["entry_sha256"]


def test_fold_metrics_and_rejection_are_exact() -> None:
    result = _load(RESULT)
    folds = result["development"]["fold_metrics"]
    assert [item["validation_year"] for item in folds] == [2021, 2022, 2023]
    assert [item["mean_rank_ic"] for item in folds] == [
        -0.008286539580953382,
        0.010427668768461518,
        -0.001280962995261452,
    ]
    assert [item["normalized_return"] for item in folds] == [
        0.24048156092611261,
        0.09453510205939697,
        -0.3933862746246731,
    ]
    assert [item["pilot_10bp_return"] for item in folds] == [
        0.01971233145418294,
        -0.014366433900924402,
        -0.07451937130173014,
    ]
    terminal = result["terminal_result"]
    assert terminal["positive_rank_ic_fold_count"] == 1
    assert terminal["positive_normalized_return_fold_count"] == 2
    assert terminal["positive_pilot_10bp_return_fold_count"] == 1
    assert terminal["development_aggregate_20bp_return"] == (-0.10108890350750255)
    assert terminal["worst_validation_normalized_drawdown"] == (
        -0.40050125692198524
    )
    assert terminal["development_survivor_count"] == 0


def test_stress_is_closed_and_direct_status_is_read_only() -> None:
    before = INTERNAL_LEDGER.read_bytes()
    stress = _load(STRESS)
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    args = argparse.Namespace(
        campaign=str(campaign.DEFAULT_PREREGISTRATION),
        output_root=str(WALKFORWARD),
    )
    status_payload = campaign.status(args)
    assert status_payload["ledger_entry_count"] == 3
    assert status_payload["selected_survivor_count"] == 0
    assert status_payload["stress_status"] == stress["status"]
    assert INTERNAL_LEDGER.read_bytes() == before


def test_attempt_ledger_chain_and_accounting_are_append_only() -> None:
    ledger = _load(ATTEMPT_LEDGER)
    previous = ledger["chain_genesis"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = {key: value for key, value in entry.items() if key != "entry_sha256"}
        assert entry["entry_sha256"] == _value_sha256(payload)
        previous = entry["entry_sha256"]
    assert previous == ledger["chain_tip_sha256"]
    assert ledger["attempt_count"] == 14
    assert ledger["infrastructure_failure_count"] == 13
    assert ledger["complete_factor_attempt_count"] == 1
    assert ledger["return_reading_complete_development_trial_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 767
    assert ledger["cumulative_return_reading_development_trial_count"] == 299


def test_v60_appends_campaign103_to_both_exact_orders() -> None:
    policy = _load(POLICY)
    c100_item = {"name": inventory.FACTOR_NAME, "score_direction": "higher"}
    c101_item = {"name": c101.FACTOR_NAME, "score_direction": "higher"}
    c103_item = {"name": campaign.ADMITTED_FACTOR, "score_direction": "higher"}
    complete = inventory.reconstruct_complete_definitions() + [
        c100_item,
        c101_item,
        c103_item,
    ]
    numeric = inventory.reconstruct_comparisons() + [
        c100_item,
        c101_item,
        c103_item,
    ]
    complete_policy = policy["complete_historical_feature_library"]
    numeric_policy = policy["numerical_comparator_eligibility"]
    assert len(complete) == complete_policy["factor_definition_count"] == 134
    assert inventory._order_digest(complete) == complete_policy["order_sha256"]
    assert len(numeric) == numeric_policy["eligible_numeric_comparator_count"] == 131
    assert inventory._order_digest(numeric) == (
        numeric_policy["eligible_numeric_comparator_order_sha256"]
    )


def test_state_reports_candidate49_and_credential_boundaries() -> None:
    state = _load(STATE)
    assert state["campaign103_terminal"]["development_survivor_count"] == 0
    assert state["effective_future_numeric_policy"]["complete_definition_count"] == 134
    assert state["effective_future_numeric_policy"]["numeric_comparator_count"] == 131
    assert state["candidate49"]["signal_entry_count"] == 0
    assert state["candidate49"]["execution_entry_count"] == 0
    assert state["candidate49"]["historical_backfill_performed"] is False
    assert state["candidate49_20260807_source_failure"]["same_day_retry_allowed"] is False
    dotenv = ROOT / ".env"
    assert dotenv.is_file() and not dotenv.is_symlink()
    assert stat.S_IMODE(dotenv.stat().st_mode) == 0o600
    assert state["provider_credential"]["secret_printed_hashed_logged_or_persisted"] is False


def test_unified_reports_expose_terminal_result() -> None:
    for path in (
        ROOT / "docs/a_share_three_day_walkforward_campaign_103_report.md",
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "Campaign103" in text
        assert "-10.108890%" in text
        assert "134" in text and "131" in text
        assert "2024–2025" in text
