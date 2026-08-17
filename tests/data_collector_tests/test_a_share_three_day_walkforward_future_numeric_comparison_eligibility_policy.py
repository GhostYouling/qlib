from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign064_features as campaign064


POLICY_PATH = (
    campaign064.REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_20260805.json"
)
POLICY_SHA256 = "ab28928886b1f617a7be094e0afad241e24bacad9646360c35a05acd80e853b8"
C63_FACTOR = "intraday_cross_sectional_standardized_return_state_stability_236p"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_policy_bindings_and_scope_are_frozen_before_campaign065() -> None:
    assert _sha256(POLICY_PATH) == POLICY_SHA256
    report = campaign064.bindings.validate_record(
        POLICY_PATH, data_root=campaign064.DEFAULT_DATA_ROOT
    )
    assert report["all_bindings_passed"] is True
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    assert policy["status"] == (
        "frozen_before_campaign065_candidate_definition_source_values_or_search"
    )
    assert policy["scope"]["effective_start_campaign"] == 65
    assert policy["scope"]["campaign064_result_or_gate_decision_changed"] is False


def test_full_and_numeric_orders_are_exact_and_not_candidate_specific() -> None:
    spec = campaign064.load_protocol()
    full = campaign064.reconstruct_comparisons(spec) + [
        {"name": campaign064.FACTOR_NAME, "score_direction": "higher"}
    ]
    numeric = [item for item in full if item["name"] != C63_FACTOR]
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    assert len(full) == 96
    assert campaign064._comparison_order_digest(full) == (
        policy["complete_historical_feature_library"]["order_sha256"]
    )
    assert len(numeric) == 95
    assert campaign064._comparison_order_digest(numeric) == (
        policy["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_order_sha256"
        ]
    )
    assert C63_FACTOR in [item["name"] for item in full]
    assert C63_FACTOR not in [item["name"] for item in numeric]
    assert numeric[-1] == {
        "name": campaign064.FACTOR_NAME,
        "score_direction": "higher",
    }
    assert policy["numerical_comparator_eligibility"][
        "no_candidate_specific_comparator_drop_allowed"
    ] is True


def test_zero_value_terminal_factor_remains_explicit_nonnumeric_challenge() -> None:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    challenges = policy["structurally_nonnumeric_mechanism_challenges"]
    assert len(challenges) == 1
    challenge = challenges[0]
    assert challenge["name"] == C63_FACTOR
    assert challenge["source_snapshot_eligible_rows"] == 0
    assert challenge["numeric_correlation_status"] == "undefined_not_pass_not_fail"
    assert challenge["mechanism_overlap_audit_required"] is True
    assert challenge["may_be_silently_omitted_from_reports"] is False
    assert challenge["may_be_treated_as_numeric_gate_pass"] is False
    assert challenge["may_be_treated_as_numeric_gate_fail_for_future_candidates"] is False
