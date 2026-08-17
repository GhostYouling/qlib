from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign108_features_v2 as campaign108


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_108_terminal_result_binding_v2_20260808.json"
)
LEDGERS = [
    REPO_ROOT
    / f"data/experiments/short_horizon/historical_walkforward/campaign_108/research_attempt_ledger_v{version}.json"
    for version in range(1, 9)
]
POLICY = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v69_20260808.json"
)
STATE = (
    REPO_ROOT
    / "docs/a_share_three_day_iteration_status_20260808_campaign108_terminal_v2.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_terminal_result_bindings_and_scientific_stop_are_exact() -> None:
    result = _load(RESULT)
    bindings = [
        result["no_return_result"],
        result["research_attempt_ledger"],
        *result["preserved_failures"],
    ]
    for binding in bindings:
        assert _sha256(REPO_ROOT / binding["path"]) == binding["sha256"]
    scientific = result["scientific_terminal_semantics"]
    assert scientific["coverage_gate_passed"] is True
    assert scientific["numeric_comparisons_completed"] == 132
    assert scientific["failed_numeric_comparisons"] == 1
    assert (
        scientific["maximum_absolute_median_daily_rank_correlation"]
        == 0.9734820997581389
    )
    assert scientific["maximum_comparison_factor"] == (
        "intraday_signed_path_efficiency_239m"
    )
    assert scientific["scientific_result"] == "rejected_as_numerically_redundant"
    assert scientific["development_trial_count"] == 0
    assert scientific["stress_2024_2025_opened"] is False
    assert result["boundaries"]["historical_daily_price_fields_read"] == []
    assert result["boundaries"]["historical_forward_returns_read"] is False


def test_append_only_ledger_chain_and_accounting_are_reconciled() -> None:
    ledgers = [_load(path) for path in LEDGERS]
    for previous_path, current in zip(LEDGERS[:-1], ledgers[1:], strict=True):
        assert _sha256(previous_path) == current["supersedes_without_rewriting"][
            "sha256"
        ]
    entries = [*ledgers[0]["entries"]]
    for ledger in ledgers[1:]:
        entries.extend(ledger["appended_entries"])
    previous = ledgers[0]["chain_genesis"]
    for entry in entries:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign108",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        previous = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        assert entry["entry_sha256"] == previous
    final = ledgers[-1]
    assert final["chain_tip_sha256"] == previous
    assert len(entries) == final["ledger_entry_count"] == 8
    assert final["attempt_count"] == 7
    assert final["infrastructure_failure_count"] == 6
    assert final["complete_factor_attempt_count"] == 1
    assert final["scientifically_decided_factor_attempt_count"] == 1
    assert final["cumulative_historical_research_attempt_count"] == 794 + 7 == 801
    assert final["cumulative_return_reading_development_trial_count"] == 300


def test_audit_completed_all_comparisons_and_failed_exactly_one() -> None:
    no_return = _load(REPO_ROOT / _load(RESULT)["no_return_result"]["path"])
    audit = _load(REPO_ROOT / no_return["audit_record"]["path"])
    factor = campaign108.FACTOR_NAME
    coverage = audit["coverage_and_capacity"][factor]
    uniqueness = audit["uniqueness"][factor]
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["median_coverage"] == 0.9994517542211769
    assert coverage["p05_coverage"] == 0.9956886515772271
    assert uniqueness["comparison_factor_count"] == 132
    assert uniqueness["comparison_order_matches_preregistration"] is True
    failed = [item for item in uniqueness["comparisons"] if not item["gate_passed"]]
    assert len(failed) == 1
    assert failed[0]["comparison_factor"] == "intraday_signed_path_efficiency_239m"
    assert failed[0]["absolute_median_daily_rank_correlation"] == (
        0.9734820997581389
    )
    assert audit["admissible_factor_count"] == 0
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False


def test_v69_preserves_v68_semantic_definition_and_numeric_order() -> None:
    policy = _load(POLICY)
    complete = campaign108.reconstruct_complete_definitions() + [
        {"name": campaign108.FACTOR_NAME, "score_direction": "higher"}
    ]
    numeric = campaign108.reconstruct_comparisons()
    assert len(complete) == 138
    assert campaign108._order_digest(complete) == policy[
        "complete_historical_feature_library"
    ]["order_sha256"]
    assert len(numeric) == 132
    assert campaign108._order_digest(numeric) == policy[
        "numerical_comparator_eligibility"
    ]["eligible_numeric_comparator_order_sha256"]
    assert policy["campaign108_terminal_classification"][
        "numeric_comparator_eligible"
    ] is False
    assert policy["final_accounting"][
        "cumulative_historical_research_attempt_count"
    ] == 801


def test_current_state_bindings_candidate49_and_weekend_boundary() -> None:
    state = _load(STATE)
    bindings = [
        state["supersedes_without_rewriting"],
        state["campaign108_terminal"]["terminal_result"],
        state["campaign108_terminal"]["research_attempt_ledger"],
        state["campaign108_terminal"]["no_return_audit"],
        state["effective_future_numeric_policy"],
        state["candidate49"]["signal_ledger"],
        state["candidate49"]["execution_ledger"],
        state["candidate49"]["latest_preserved_source_failure"],
        *state["reports"].values(),
    ]
    for binding in bindings:
        assert _sha256(REPO_ROOT / binding["path"]) == binding["sha256"]
    assert state["campaign108_terminal"][
        "cumulative_historical_research_attempt_count"
    ] == 801
    assert state["candidate49"]["signal_ledger"]["entry_count"] == 0
    assert state["candidate49"]["execution_ledger"]["entry_count"] == 0
    assert state["provider_credential"]["repository_dotenv_mode"] == "0600"
    assert state["provider_credential"]["tushare_token_nonempty"] is True
    assert state["provider_credential"][
        "secret_printed_hashed_logged_or_persisted"
    ] is False
    assert state["weekend_boundary"]["candidate49_plan_or_run_executed"] is False
    assert state["research_boundary"][
        "historical_daily_price_or_forward_return_values_read_by_campaign108"
    ] is False
