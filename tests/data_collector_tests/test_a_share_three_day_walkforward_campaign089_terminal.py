from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign089_features as campaign089


REPO_ROOT = campaign089.REPO_ROOT
STATUS_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_iteration_status_20260807_campaign089_verified_v2.json"
)
STATUS_SHA256 = "9ee27e671a56307be59ac70dd4e127ee9369b27c24c54ab9ec45512345d0d478"
POLICY_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v30_20260807.json"
)
POLICY_SHA256 = "dad79c5ed34158aa3b044875782ab6e96e622d4df737a5361aa0966081eb183c"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_terminal_state_and_attempt_accounting_are_bound() -> None:
    assert _sha256(STATUS_PATH) == STATUS_SHA256
    state = _load(STATUS_PATH)
    campaign = state["campaign089"]
    assert campaign["terminal_status"] == (
        "development_quality_gate_rejection_zero_survivors"
    )
    assert campaign["numeric_comparisons_passed"] == 118
    assert campaign["development_survivor_count"] == 0
    assert campaign["stress_2024_2025_opened"] is False
    assert campaign["stress_return_fields_read"] is False
    assert state["accounting"] == {
        "cumulative_historical_research_attempt_count": 622,
        "cumulative_return_reading_development_trial_count": 287,
        "campaign089_attempt_count": 10,
        "campaign089_ledger_entry_count": 12,
        "campaign089_complete_factor_attempt_count": 1,
        "campaign089_return_reading_development_trial_count": 1,
    }


def test_final_ledger_and_reporting_bindings_are_exact() -> None:
    state = _load(STATUS_PATH)
    campaign = state["campaign089"]
    ledger_binding = campaign["final_attempt_ledger"]
    ledger_path = REPO_ROOT / ledger_binding["path"]
    assert _sha256(ledger_path) == ledger_binding["sha256"]
    ledger = _load(ledger_path)
    assert ledger["campaign089_attempt_count"] == 10
    assert ledger["campaign089_ledger_entry_count"] == 12
    assert ledger["appended_entries"][0]["kind"] == "reporting_implementation_failure"

    record_binding = campaign["research_record_v2"]
    record_path = REPO_ROOT / record_binding["path"]
    assert _sha256(record_path) == record_binding["sha256"]
    record = _load(record_path)
    for binding in record["reporting_bindings"].values():
        if not isinstance(binding, dict):
            continue
        path = REPO_ROOT / binding["path"]
        assert _sha256(path) == binding["sha256"]
        assert "Campaign089" in path.read_text(encoding="utf-8")


def test_future_numeric_policy_v30_appends_campaign089_exactly_once() -> None:
    assert _sha256(POLICY_PATH) == POLICY_SHA256
    policy = _load(POLICY_PATH)
    factor = {"name": campaign089.FACTOR_NAME, "score_direction": "higher"}
    complete = campaign089.reconstruct_complete_definitions() + [factor]
    numeric = campaign089.reconstruct_comparisons() + [factor]
    assert len(complete) == 121
    assert campaign089._comparison_order_digest(complete) == (
        policy["complete_historical_feature_library"]["order_sha256"]
    )
    assert len(numeric) == 119
    assert campaign089._comparison_order_digest(numeric) == (
        policy["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_order_sha256"
        ]
    )
    assert complete[-1] == numeric[-1] == factor


def test_candidate49_and_stress_boundaries_remain_closed() -> None:
    state = _load(STATUS_PATH)
    candidate49 = state["candidate49"]
    assert candidate49["signal_ledger_entry_count"] == 0
    assert candidate49["execution_ledger_entry_count"] == 0
    assert candidate49["provider_request_issued_this_iteration"] is False
    assert candidate49["same_day_plan_or_run_executed_this_iteration"] is False
    assert state["next_campaign_boundary"]["must_bind_v30_policy"] is True
    assert "Candidate49 historical backfill" in state["prohibited_actions"]
