from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v417_20260824.json"
)
FREEZE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_265_adapter_implementation_freeze_20260824.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_265_adapter_result_20260824.json"
)
REPORT = ROOT / "docs/a_share_three_day_walkforward_campaign_265_adapter_report.md"
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_265/research_attempt_ledger_v3.json"
)
ADAPTER = (
    ROOT / "scripts/a_share_three_day_walkforward_campaign265_convertible_premium.py"
)
SYNTHETIC_TEST = (
    ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_convertible_premium.py"
)
SIGNAL = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION = (
    ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
UNIFIED = (
    ROOT / "data/experiments/short_horizon/current_research_report.md",
    ROOT / "data/experiments/short_horizon/three_day_research_report.md",
)
VALIDATION = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_265_adapter_validation_20260824.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260824_campaign265_adapter_ready.json"
)


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve(path: str) -> Path:
    target = Path(path)
    return target if target.is_absolute() else ROOT / target


def _assert_bindings(bindings: dict) -> None:
    for binding in bindings.values():
        target = _resolve(binding["path"])
        assert target.is_file()
        assert _sha(target) == binding["sha256"]


def _entry_hash(entry: dict) -> str:
    payload = "|".join(
        (
            "campaign265",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def test_adapter_artifacts_and_policy_bind_exact_bytes() -> None:
    expected = {
        FREEZE: "2429588261bf35e46c3a68daeab85b23405c247a6fd98195e081c2b43c1f638e",
        RESULT: "4a109a2e7e23091da33246654e391d41af0a57515b23d91dfb28f4718c26da48",
        REPORT: "2411e54360d3fa8e7b0a92bf014824c12af3d08afec5a1f2aa200170807b8e2f",
        LEDGER: "7edd5202c77ed575f84efc6e8ecbc51bb2367f631783b1f3810e2378d094bdf0",
        POLICY: "62805389b141904fe6b519bb7ff345410802fb5475f3804615e6f12ff81da39f",
        ADAPTER: "58b9fddbbeef97955d4961f9f708028aa63d90fc56f2656db68098de7d3543e8",
        SYNTHETIC_TEST: "b681af4d0d6f3d7081adac6207dab438c7166945bfea27c72ac4ea61ea481f4a",
    }
    for path, digest in expected.items():
        assert _sha(path) == digest
    policy = _load(POLICY)
    _assert_bindings(policy["authoritative_inputs"])


def test_additive_failure_chain_and_accounting_are_exact() -> None:
    ledger = _load(LEDGER)
    previous = ledger["authoritative_predecessor"]["chain_tip_sha256"]
    assert len(ledger["appended_entries"]) == 1
    entry = ledger["appended_entries"][0]
    assert entry["ordinal"] == 10
    assert entry["previous_entry_sha256"] == previous
    assert entry["entry_sha256"] == _entry_hash(entry)
    assert ledger["chain_tip_sha256"] == entry["entry_sha256"]
    assert ledger["effective_entry_count"] == 10
    assert ledger["effective_prevalue_scientific_attempt_count"] == 7
    assert ledger["effective_infrastructure_failure_attempt_count"] == 3
    assert ledger["cumulative_historical_research_attempt_count"] == 2614
    assert ledger["cumulative_return_reading_development_trial_count"] == 315


def test_adapter_stage_is_synthetic_only_and_values_remain_closed() -> None:
    policy = _load(POLICY)
    stage = policy["campaign265_adapter_stage"]
    assert stage["source_adapter_created"] is True
    assert stage["source_adapter_zero_network"] is True
    assert stage["synthetic_tests_passed"] == 16
    for key in (
        "source_acceptance_planner_created",
        "source_acceptance_authorized",
        "provider_credential_loaded",
        "provider_request_issued",
        "provider_response_or_row_value_read",
        "candidate_or_comparator_value_read",
        "historical_daily_price_or_forward_return_read",
    ):
        assert stage[key] is False
    boundary = policy["campaign265_next_stage_boundary"]
    assert boundary["provider_request_allowed_by_v417"] is False
    assert boundary["credential_load_allowed_by_v417"] is False
    assert boundary["source_candidate_or_comparator_value_allowed_by_v417"] is False
    assert boundary["daily_price_or_return_value_allowed_by_v417"] is False


def test_library_and_return_gates_remain_closed() -> None:
    policy = _load(POLICY)
    library = policy["complete_historical_feature_library"]
    numeric = policy["numerical_comparator_eligibility"]
    assert library["factor_definition_count"] == 162
    assert library["campaign265_definition_appended"] is False
    assert numeric["eligible_numeric_comparator_count"] == 143
    assert numeric["campaign265_numeric_comparator_appended"] is False
    assert numeric["campaign265_comparator_values_may_open_now"] is False
    assert (
        policy["effective_accounting"]["campaign265_complete_factor_attempt_count"] == 0
    )
    assert (
        policy["effective_accounting"][
            "campaign265_return_reading_development_trial_count"
        ]
        == 0
    )


def test_candidate49_remains_sole_empty_prospective_ledger() -> None:
    policy = _load(POLICY)
    assert _sha(SIGNAL) == policy["candidate49"]["signal_ledger_sha256"]
    assert _sha(EXECUTION) == policy["candidate49"]["execution_ledger_sha256"]
    assert _load(SIGNAL)["entries"] == []
    assert _load(EXECUTION)["entries"] == []
    assert policy["candidate49"]["sole_prospective_candidate"] is True
    assert policy["candidate49"]["historical_backfill_allowed"] is False
    assert policy["candidate49"]["second_prospective_candidate_allowed"] is False


def test_unified_reports_have_one_adapter_stage_and_publication_hashes() -> None:
    policy = _load(POLICY)
    heading = "## Campaign265：零网络可转债溢价适配器完成（2026-08-24）"
    report_bindings = (
        policy["mutable_unified_reports"]["current"],
        policy["mutable_unified_reports"]["three_day"],
    )
    for path, binding in zip(UNIFIED, report_bindings, strict=True):
        text = path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        assert "2,614" in text
        assert "16 项纯合成测试全部通过" in text
        assert _sha(path) == binding["sha256_at_publication"]
    pipeline = policy["mutable_unified_reports"]["data_pipeline"]
    assert _sha(_resolve(pipeline["path"])) == pipeline["sha256_at_publication"]


def test_latest_state_binds_validation_and_keeps_goal_active() -> None:
    state = _load(STATE)
    _assert_bindings({"policy": state["authoritative_policy"]})
    _assert_bindings(state["campaign265_adapter_stage"]["artifacts"])
    validation = state["campaign265_adapter_stage"]["validation"]
    assert _resolve(validation["path"]) == VALIDATION
    assert _sha(VALIDATION) == validation["sha256"]
    assert validation["focused_pytest_passed"] == 30
    assert state["goal"]["status"] == "active"
    assert state["goal"]["current_campaign"] == 265
    assert state["goal"]["terminal_condition_reached"] is False
    assert state["dual_track"]["candidate49"]["signal_entry_count"] == 0
    assert state["dual_track"]["candidate49"]["execution_entry_count"] == 0
    assert state["session_boundary"]["observed_before_16_30"] is True
    assert state["next_action"].startswith("Continue Campaign265")
