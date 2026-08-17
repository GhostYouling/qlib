from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_116/research_attempt_ledger_v4.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_116_feature_snapshot_verification_result_20260812.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v100_20260812.json"
)
STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260812_campaign116_snapshot_verified.json"
)
LATEST_LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_116/research_attempt_ledger_v5.json"
)
LATEST_POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v101_20260812.json"
)
LATEST_STATE = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260812_campaign116_snapshot_verified_v2.json"
)
MANIFEST = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign116_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign116_feature_library_v1/snapshot_manifest.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_campaign116_snapshot_authority_hashes_are_exact() -> None:
    assert _sha256(LEDGER) == (
        "d48e4bc015aecea29cfc91559fa1e60d7d683b28e203f513f886b1b86cff8ab1"
    )
    assert _sha256(RESULT) == (
        "27bf2126460e0f89dea5d50030d06ffe4ae9372e2d6f7bb75d5f901d0a2fb85a"
    )
    assert _sha256(POLICY) == (
        "de014cdffe6da1e366c81d87958be40052fab2d659b9734e6b0592f21a347a01"
    )
    assert _sha256(STATE) == (
        "1c0c7e9f11f2faa4674e77b0afec3cbe160ed949318c71ab8645443e7eb01973"
    )
    assert _sha256(MANIFEST) == (
        "d1036a44495206b2329910d71915a7cd861fdc3baf8344a466d66f1cb1787163"
    )


def test_campaign116_v4_extension_chain_and_accounting_are_exact() -> None:
    ledger = _load(LEDGER)
    extension = ledger["extends_without_rewriting"]
    assert extension["sha256"] == (
        "779b14d36b656b1c158db3f160df6c807a08ea8dc0c1e7c3e1a0d65fdf378434"
    )
    previous = extension["prior_chain_tip_sha256"]
    for entry in ledger["entries"]:
        assert entry["previous_entry_sha256"] == previous
        payload = (
            "campaign116|"
            + entry["attempt_id"]
            + "|"
            + previous
            + "|"
            + entry["phase"]
            + "|"
            + entry["status"]
        ).encode()
        assert hashlib.sha256(payload).hexdigest() == entry["entry_sha256"]
        previous = entry["entry_sha256"]
    assert previous == ledger["current_chain_tip_sha256"]
    assert ledger["attempt_count"] == 4
    assert ledger["infrastructure_failure_count"] == 3
    assert ledger["cumulative_historical_research_attempt_count"] == 882
    assert ledger["cumulative_return_reading_development_trial_count"] == 302


def test_campaign116_snapshot_verified_before_coverage_and_comparators() -> None:
    result = _load(RESULT)
    verification = result["verification"]
    scientific = result["scientific_classification"]
    assert verification["partitions_verified"] == 33015
    assert verification["rows_verified"] == 7724498
    assert verification["eligible_rows_verified"] == 5177430
    assert verification["dataset_sha256"] == (
        "28e9b79514fe905749a3a182d0b3651331c4afb5330e03276c117d58f3b1082a"
    )
    assert scientific["coverage_gate_computed"] is False
    assert scientific["numeric_comparator_values_read"] is False
    assert scientific["historical_daily_price_or_forward_return_values_read"] is False
    assert scientific["stress_2024_2025_opened"] is False


def test_v100_appends_definition_but_not_numeric_comparator() -> None:
    policy = _load(POLICY)
    complete = policy["complete_historical_feature_library"]
    numeric = policy["numerical_comparator_eligibility"]
    assert complete["factor_definition_count"] == 142
    assert complete["order_sha256"] == (
        "ed61b10f3acb939c10ae5759f33aafde377cc921dd99c642300603b50a4851c5"
    )
    assert numeric["eligible_numeric_comparator_count"] == 134
    assert numeric["campaign116_numeric_comparator_appended"] is False


def test_candidate49_and_current_use_boundaries_remain_closed() -> None:
    state = _load(STATE)
    candidate49 = state["candidate49"]
    boundary = state["research_boundary"]
    assert candidate49["only_active_prospective_candidate"] is True
    assert candidate49["signal_entry_count"] == 0
    assert candidate49["execution_entry_count"] == 0
    assert candidate49["historical_backfill_performed"] is False
    assert boundary["provider_request_issued"] is False
    assert boundary["campaign116_comparator_values_read"] is False
    assert boundary["historical_daily_price_or_forward_return_values_read"] is False
    assert boundary["second_prospective_candidate_created"] is False
    assert boundary["current_scoring_selection_sizing_positions_or_orders_performed"] is False


def test_campaign116_unified_reports_record_verified_snapshot_and_no_advice() -> None:
    for path in (
        ROOT / "docs/a_share_three_day_walkforward_campaign_116_snapshot_report_v2.md",
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "Campaign116" in text
        assert "33,015" in text
        assert "5,177,430" in text
        assert "882" in text
        assert "302" in text
        assert "Candidate49" in text
        assert "投资建议" in text


def test_campaign116_latest_validation_accounting_preserves_scientific_stage() -> None:
    assert _sha256(LATEST_LEDGER) == (
        "8600a8754701f4a0bb9c37e32daba07dd1ad8b92c659f6641f2439f510fbb251"
    )
    assert _sha256(LATEST_POLICY) == (
        "27a52a24fd9db6b945fee49a0e55d73dd48a54a62d2a01652ea01d194d05cd46"
    )
    assert _sha256(LATEST_STATE) == (
        "3ed3fb0f02d1d4f009743598a6d18ded9cf1a0df4b776f79e4638cab2d9f69f3"
    )
    ledger = _load(LATEST_LEDGER)
    policy = _load(LATEST_POLICY)
    state = _load(LATEST_STATE)
    assert ledger["attempt_count"] == 5
    assert ledger["infrastructure_failure_count"] == 4
    assert ledger["cumulative_historical_research_attempt_count"] == 883
    assert policy["complete_historical_feature_library"]["factor_definition_count"] == 142
    assert policy["numerical_comparator_eligibility"][
        "eligible_numeric_comparator_count"
    ] == 134
    assert state["campaign116"]["coverage_gate_computed"] is False
    assert state["campaign116"]["numeric_comparator_values_read"] is False
    assert state["validation"]["campaign116_regression_passed"] == 19
    assert state["validation"]["frozen_files_modified_to_satisfy_black"] is False
