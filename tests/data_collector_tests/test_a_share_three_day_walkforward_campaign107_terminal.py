from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign107_features as campaign107


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_107_terminal_result_binding_20260808.json"
)
LEDGER_V1 = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_107/research_attempt_ledger_v1.json"
)
LEDGER_V2 = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_107/research_attempt_ledger_v2.json"
)
LEDGER_V3 = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_107/research_attempt_ledger_v3.json"
)
POLICY = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v67_20260808.json"
)
STATE = (
    REPO_ROOT
    / "docs/a_share_three_day_iteration_status_20260808_campaign107_terminal.json"
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
        path = REPO_ROOT / binding["path"]
        assert _sha256(path) == binding["sha256"]
    scientific = result["scientific_terminal_semantics"]
    assert scientific["coverage_gate_passed"] is True
    assert scientific["numeric_comparisons_completed"] == 132
    assert scientific["failed_numeric_comparisons"] == 5
    assert (
        scientific["maximum_absolute_median_daily_rank_correlation"]
        == 0.9315530906961503
    )
    assert scientific["maximum_comparison_factor"] == "intraday_price_update_share_238m"
    assert scientific["scientific_result"] == "rejected_as_numerically_redundant"
    assert scientific["development_trial_count"] == 0
    assert scientific["stress_2024_2025_opened"] is False
    assert result["boundaries"]["historical_daily_price_fields_read"] == []
    assert result["boundaries"]["historical_forward_returns_read"] is False


def test_append_only_ledger_chain_and_accounting_are_reconciled() -> None:
    v1, v2, v3 = _load(LEDGER_V1), _load(LEDGER_V2), _load(LEDGER_V3)
    assert _sha256(LEDGER_V1) == v2["supersedes_without_rewriting"]["sha256"]
    assert _sha256(LEDGER_V2) == v3["supersedes_without_rewriting"]["sha256"]
    entries = [*v1["entries"], *v2["appended_entries"], *v3["appended_entries"]]
    previous = v1["chain_genesis"]
    for entry in entries:
        assert entry["previous_entry_sha256"] == previous
        payload = "|".join(
            [
                "campaign107",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        )
        expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        assert entry["entry_sha256"] == expected
        previous = expected
    assert v3["chain_tip_sha256"] == previous
    assert len(entries) == v3["ledger_entry_count"] == 4
    assert v3["attempt_count"] == 3
    assert v3["infrastructure_failure_count"] == 2
    assert v3["complete_factor_attempt_count"] == 1
    assert v3["scientifically_decided_factor_attempt_count"] == 1
    assert v3["cumulative_historical_research_attempt_count"] == 791 + 3 == 794
    assert v3["cumulative_return_reading_development_trial_count"] == 300


def test_audit_completed_all_comparisons_and_failed_exact_five() -> None:
    result = _load(RESULT)
    audit_binding = _load(REPO_ROOT / result["no_return_result"]["path"])[
        "audit_record"
    ]
    audit = _load(REPO_ROOT / audit_binding["path"])
    factor = campaign107.FACTOR_NAME
    coverage = audit["coverage_and_capacity"][factor]
    uniqueness = audit["uniqueness"][factor]
    assert coverage["gate_passed_before_comparison_values"] is True
    assert coverage["median_coverage"] == 0.9994517542211769
    assert coverage["p05_coverage"] == 0.9956886515772271
    assert uniqueness["comparison_factor_count"] == 132
    assert uniqueness["comparison_order_matches_preregistration"] is True
    failed = [
        item for item in uniqueness["comparisons"] if item["gate_passed"] is not True
    ]
    assert {item["comparison_factor"] for item in failed} == {
        "intraday_price_update_share_238m",
        "intraday_unchanged_close_range_absorption_share_238p",
        "intraday_terminal_nominal_share_price_affordability_rank_240m",
        "intraday_return_weak_order_entropy_234t",
        "intraday_price_update_clock_entropy_10b_238m",
    }
    assert audit["admissible_factor_count"] == 0
    assert audit["historical_daily_price_fields_read"] == []
    assert audit["historical_forward_return_fields_read"] is False


def test_v67_appends_only_semantic_definition_and_preserves_numeric_order() -> None:
    policy = _load(POLICY)
    complete = campaign107.reconstruct_complete_definitions() + [
        {"name": campaign107.FACTOR_NAME, "score_direction": "higher"}
    ]
    numeric = campaign107.reconstruct_comparisons()
    assert (
        len(complete)
        == policy["complete_historical_feature_library"]["factor_definition_count"]
        == 137
    )
    assert (
        campaign107._order_digest(complete)
        == policy["complete_historical_feature_library"]["order_sha256"]
    )
    assert (
        len(numeric)
        == policy["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_count"
        ]
        == 132
    )
    assert (
        campaign107._order_digest(numeric)
        == policy["numerical_comparator_eligibility"][
            "eligible_numeric_comparator_order_sha256"
        ]
    )
    assert (
        policy["campaign107_terminal_classification"]["numeric_comparator_eligible"]
        is False
    )
    assert (
        policy["final_accounting"]["cumulative_historical_research_attempt_count"]
        == 794
    )


def test_current_state_bindings_candidate49_and_weekend_boundary() -> None:
    state = _load(STATE)
    bindings = [
        state["supersedes_without_rewriting"],
        state["campaign107_terminal"]["terminal_result"],
        state["campaign107_terminal"]["research_attempt_ledger"],
        state["campaign107_terminal"]["no_return_audit"],
        state["effective_future_numeric_policy"],
        state["candidate49"]["signal_ledger"],
        state["candidate49"]["execution_ledger"],
        state["candidate49"]["latest_preserved_source_failure"],
        *state["reports"].values(),
    ]
    for binding in bindings:
        path = REPO_ROOT / binding["path"]
        assert _sha256(path) == binding["sha256"]
    assert (
        state["campaign107_terminal"]["cumulative_historical_research_attempt_count"]
        == 794
    )
    assert state["candidate49"]["signal_ledger"]["entry_count"] == 0
    assert state["candidate49"]["execution_ledger"]["entry_count"] == 0
    assert state["provider_credential"]["repository_dotenv_mode"] == "0600"
    assert state["provider_credential"]["tushare_token_nonempty"] is True
    assert (
        state["provider_credential"]["secret_printed_hashed_logged_or_persisted"]
        is False
    )
    assert state["weekend_boundary"]["candidate49_plan_or_run_executed"] is False
    assert (
        state["research_boundary"][
            "historical_daily_price_or_forward_return_values_read_by_campaign107"
        ]
        is False
    )
