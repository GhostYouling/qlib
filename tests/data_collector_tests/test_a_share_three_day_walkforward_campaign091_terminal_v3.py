from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign091_features as campaign091


REPO_ROOT = campaign091.REPO_ROOT
STATUS_PATH = REPO_ROOT / (
    "docs/a_share_three_day_iteration_status_20260807_campaign091_corrected_v4.json"
)
STATUS_SHA256 = "544f4af7506040e8705a31be082a4280c19f89347bae904def1deb98e8cb4767"
POLICY_PATH = REPO_ROOT / (
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_"
    "policy_v35_20260807.json"
)
POLICY_SHA256 = "734949300e95958b968ce8a9280bbac764ec3be5752d2c3d0f810320574b10c5"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_corrected_state_and_final_accounting_are_exact() -> None:
    assert _sha256(STATUS_PATH) == STATUS_SHA256
    assert bindings.validate_record(STATUS_PATH)["all_bindings_passed"] is True
    state = _load(STATUS_PATH)
    assert datetime.fromisoformat(state["recorded_at"].replace("Z", "+00:00")) <= (
        datetime.now(timezone.utc)
    )
    assert state["campaign091_result"]["development_survivor_count"] == 0
    assert state["campaign091_result"]["stress_2024_2025_opened"] is False
    assert state["final_accounting"]["campaign091_attempt_count"] == 8
    assert state["final_accounting"]["campaign091_ledger_entry_count"] == 11
    assert (
        state["final_accounting"]["cumulative_historical_research_attempt_count"] == 640
    )
    assert (
        state["final_accounting"]["cumulative_return_reading_development_trial_count"]
        == 289
    )


def test_corrected_terminal_chain_and_reporting_bindings_pass() -> None:
    state = _load(STATUS_PATH)
    chain = state["authoritative_campaign091_chain"]
    for binding in chain.values():
        path = REPO_ROOT / binding["path"]
        assert _sha256(path) == binding["sha256"]
        assert bindings.validate_record(path)["all_bindings_passed"] is True
    record = _load(REPO_ROOT / chain["research_record_v3"]["path"])
    for binding in record["reporting_bindings"].values():
        if isinstance(binding, dict):
            path = REPO_ROOT / binding["path"]
            assert _sha256(path) == binding["sha256"]
            assert "Campaign091" in path.read_text(encoding="utf-8")


def test_timestamp_correction_is_append_only_and_bound() -> None:
    state = _load(STATUS_PATH)
    binding = state["timestamp_correction"]
    path = REPO_ROOT / binding["path"]
    assert _sha256(path) == binding["sha256"]
    correction = _load(path)
    assert correction["governance"]["affected_files_rewritten"] is False
    assert (
        correction["governance"][
            "count_as_one_infrastructure_failure_for_common_root_cause"
        ]
        is True
    )
    assert correction["corrected_semantics"]["scientific_result_changed"] is False


def test_v35_policy_preserves_terminal_definition_and_comparator_order() -> None:
    assert _sha256(POLICY_PATH) == POLICY_SHA256
    assert bindings.validate_record(POLICY_PATH)["all_bindings_passed"] is True
    policy = _load(POLICY_PATH)
    factor = {"name": campaign091.FACTOR_NAME, "score_direction": "higher"}
    complete = campaign091.reconstruct_complete_definitions() + [factor]
    numeric = campaign091.reconstruct_comparisons() + [factor]
    assert len(complete) == 123
    assert campaign091._comparison_order_digest(complete) == (
        policy["complete_historical_feature_library"]["order_sha256"]
    )
    assert len(numeric) == 121
    assert campaign091._comparison_order_digest(numeric) == (
        policy["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_order_sha256"
        ]
    )
    assert complete[-1] == numeric[-1] == factor


def test_candidate49_and_next_campaign_boundaries_remain_closed() -> None:
    state = _load(STATUS_PATH)
    candidate49 = state["candidate49"]
    assert candidate49["signal_ledger_entry_count"] == 0
    assert candidate49["execution_ledger_entry_count"] == 0
    assert candidate49["provider_request_issued_this_iteration"] is False
    assert candidate49["same_day_plan_or_run_executed_this_iteration"] is False
    assert state["next_campaign_boundary"]["must_bind_v35_policy"] is True
    assert "Candidate49 historical backfill" in state["prohibited_actions"]
