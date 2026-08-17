from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign106_features as campaign106


REPO_ROOT = Path(__file__).resolve().parents[2]
TERMINAL = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_106_terminal_result_binding_20260808.json"
POLICY = REPO_ROOT / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v64_20260808.json"
LEDGER = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_106/research_attempt_ledger_v3.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _order_digest(items: list[dict[str, str]]) -> str:
    payload = json.dumps(
        [[item["name"], item["score_direction"]] for item in items],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def test_terminal_bindings_and_infrastructure_classification_are_exact() -> None:
    terminal = _load(TERMINAL)
    report = bindings.validate_record(TERMINAL, data_root=campaign106.DEFAULT_DATA_ROOT)
    assert report["all_bindings_passed"] is True
    assert terminal["status"] == "campaign106_terminal_infrastructure_inconclusive_no_development_or_stress"
    assert terminal["candidate_definition"]["complete_definition_eligible_for_future_inventory"] is True
    assert terminal["candidate_definition"]["numeric_comparator_eligible_for_future_uniqueness"] is False
    assert terminal["no_return_evidence"]["coverage"]["gate_passed_before_comparison_values"] is True
    assert terminal["no_return_evidence"]["all_numeric_comparisons_passed"] is None
    assert terminal["development"]["development_trial_started"] is False
    assert terminal["exposed_stress"]["interval_2024_2025_opened"] is False
    assert terminal["boundaries"]["provider_request_issued"] is False


def test_v64_appends_definition_but_preserves_exact_v63_numeric_order() -> None:
    policy = _load(POLICY)
    report = bindings.validate_record(POLICY, data_root=campaign106.DEFAULT_DATA_ROOT)
    assert report["all_bindings_passed"] is True
    complete = [
        *campaign106.reconstruct_complete_definitions(),
        {"name": campaign106.FACTOR_NAME, "score_direction": "higher"},
    ]
    numeric = campaign106.reconstruct_comparisons()
    assert len(complete) == 136
    assert _order_digest(complete) == policy["complete_historical_feature_library"]["order_sha256"]
    assert len(numeric) == 132
    assert _order_digest(numeric) == policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_order_sha256"]
    assert policy["numerical_comparator_eligibility"]["campaign106_numeric_comparator_appended"] is False
    adapter = policy["mandatory_prevalue_support_and_adapter_gates_for_campaign107_and_later"]
    assert adapter["synthetic_comparator_fixture_must_include_finite_and_missing_values"] is True
    assert adapter["candidate_only_finite_sorter_may_not_be_used_for_raw_comparators"] is True


def test_attempt_ledger_preserves_both_failures_and_chain() -> None:
    ledger = _load(LEDGER)
    assert ledger["attempt_count"] == len(ledger["entries"]) == 3
    assert ledger["infrastructure_failure_count"] == 2
    assert ledger["scientifically_decided_factor_attempt_count"] == 0
    previous = ledger["chain_genesis"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        material = "|".join(
            [
                "campaign106",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        previous = hashlib.sha256(material.encode()).hexdigest()
        assert entry["entry_sha256"] == previous
    assert ledger["chain_tip_sha256"] == previous
    assert ledger["research_boundary"]["historical_daily_price_or_forward_return_values_read"] is False
    assert ledger["research_boundary"]["stress_2024_2025_opened"] is False


def test_no_audit_result_was_published_after_either_failed_process() -> None:
    root = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_106/no_return"
    assert list(root.glob("*_campaign106_no_return_audit.json")) == []

