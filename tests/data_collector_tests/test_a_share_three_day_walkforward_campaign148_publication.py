from __future__ import annotations

import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings


ROOT = Path(__file__).resolve().parents[2]
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v199_20260814.json"
)
STATUS = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260814_campaign148_prevalue_terminal.json"
)
VALIDATION = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_148_terminal_validation_20260814.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_campaign148_policy_advances_without_changing_library_orders() -> None:
    assert bindings.validate_record(POLICY)["all_bindings_passed"] is True
    policy = _load(POLICY)
    assert policy["version"] == 199
    assert policy["complete_historical_feature_library"] == {
        "factor_definition_count": 155,
        "order_sha256": (
            "2e4114edb26fa3aaebd145ef07fe4e2ac9c5d9dc4586cf70ff61c20e39b954ba"
        ),
        "unchanged_from_v198": True,
        "campaign148_definition_appended": False,
    }
    eligibility = policy["numerical_comparator_eligibility"]
    assert eligibility["eligible_numeric_comparator_count"] == 142
    assert eligibility["eligible_numeric_comparator_order_sha256"] == (
        "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf"
    )
    assert eligibility["campaign148_numeric_series_appended"] is False
    assert policy["future_campaign_boundary"]["next_campaign"] == 149


def test_campaign148_latest_status_keeps_goal_and_candidate49_boundaries() -> None:
    assert bindings.validate_record(VALIDATION)["all_bindings_passed"] is True
    assert bindings.validate_record(STATUS)["all_bindings_passed"] is True
    status = _load(STATUS)
    assert status["goal"]["status"] == "active"
    assert status["goal"]["campaign149_offline_scouting_authorized"] is True
    assert status["campaign148"]["terminal"] is True
    assert status["campaign148"]["selected_candidate_count"] == 0
    assert status["candidate49"]["sole_prospective_candidate"] is True
    assert status["candidate49"]["signal_ledger"]["entries"] == 0
    assert status["candidate49"]["execution_ledger"]["entries"] == 0
    assert status["candidate49_daily_20260814"]["same_day_retry_performed"] is False
    assert status["active_daily_data_root"]["mutated_by_campaign148"] is False
    for report in status["reports"].values():
        if report.get("mutable_append_only_report_not_an_immutable_binding"):
            assert "sha256" not in report
            assert report["sha256_at_publication"]
