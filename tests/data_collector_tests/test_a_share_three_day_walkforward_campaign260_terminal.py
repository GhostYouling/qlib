from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign260_features as features


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v401_20260816.json"
)
RESULT = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_260_terminal_result_v5_20260816.json"
)
LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_260/research_attempt_ledger_v5.json"
)
UNIQUENESS = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_260/uniqueness/campaign260_ordered_uniqueness_audit.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_campaign260_terminal_scientific_and_library_semantics() -> None:
    policy = _load(POLICY)
    result = _load(RESULT)
    uniqueness = _load(UNIQUENESS)
    assert policy["version"] == 401
    assert result["scientific_result"]["selected_factor_count"] == 0
    assert result["scientific_result"]["development_trial_count"] == 0
    assert uniqueness["summary"]["comparison_factor_count"] == 142
    assert uniqueness["summary"]["all_required_numeric_comparisons_passed"] is False
    assert uniqueness["summary"]["maximum_observed_absolute_median_daily_rank_correlation"] == 0.934495698830269
    definitions = features.reconstruct_complete_definitions()
    assert len(definitions) == 159
    assert features._order_digest(definitions) == policy["complete_historical_feature_library"]["order_sha256"]
    assert len(features.reconstruct_comparisons()) == 142


def test_campaign260_accounting_reference_chain_and_boundaries() -> None:
    policy = _load(POLICY)
    ledger = _load(LEDGER)
    assert ledger["effective_entry_count"] == 16
    assert ledger["effective_infrastructure_failure_attempt_count"] == 10
    assert ledger["effective_prevalue_scientific_attempt_count"] == 6
    assert ledger["cumulative_historical_research_attempt_count"] == 2510
    assert ledger["cumulative_return_reading_development_trial_count"] == 314
    assert policy["authoritative_inputs"]["campaign260_attempt_ledger_v5"]["sha256"] == _sha256(LEDGER)
    assert policy["authoritative_inputs"]["campaign260_terminal_result_v5"]["sha256"] == _sha256(RESULT)
    assert policy["candidate49"]["signal_entry_count"] == 0
    assert policy["candidate49"]["execution_entry_count"] == 0
    assert policy["research_boundary"]["historical_daily_price_or_forward_return_values_read"] is False
    assert policy["research_boundary"]["provider_or_web_request_issued"] is False
    assert policy["future_campaign_boundary"]["next_campaign"] == 261
