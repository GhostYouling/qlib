from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TERMINAL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_261_terminal_result_v3_20260816.json"
)
POLICY = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v404_20260816.json"
)
LEDGER_V1 = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_261/research_attempt_ledger_v1.json"
)
LEDGER_V2 = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_261/research_attempt_ledger_v2.json"
)
LEDGER_V3 = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_261/research_attempt_ledger_v3.json"
)
COVERAGE = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_261/coverage/campaign261_coverage_audit.json"
)
UNIQUENESS = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_261/uniqueness/campaign261_ordered_uniqueness_audit.json"
)
SIGNAL = (
    REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION = (
    REPO_ROOT
    / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
REPORTS = (
    REPO_ROOT / "data/experiments/short_horizon/current_research_report.md",
    REPO_ROOT / "data/experiments/short_horizon/three_day_research_report.md",
)


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _entry_hash(entry: dict) -> str:
    body = {key: value for key, value in entry.items() if key != "entry_sha256"}
    payload = json.dumps(
        body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def test_terminal_and_policy_bind_current_artifacts() -> None:
    terminal = _load(TERMINAL)
    policy = _load(POLICY)
    assert (
        _sha256(TERMINAL)
        == "0612b8fee0e71864460ba7977253276853096355d08d5ef417edadd8087c0112"
    )
    assert (
        _sha256(POLICY)
        == "fb2a95214db33763c6b14fe132c0c29eafad9a15ee4ea8fdafb58de3e2eb9fed"
    )
    assert policy["version"] == 404
    assert policy["authoritative_inputs"]["campaign261_terminal_result_v3"][
        "sha256"
    ] == _sha256(TERMINAL)
    assert terminal["authoritative_inputs"]["attempt_ledger_v3"]["sha256"] == _sha256(
        LEDGER_V3
    )


def test_terminal_science_stops_before_returns() -> None:
    terminal = _load(TERMINAL)
    science = terminal["scientific_result"]
    assert science["factor"] == "intraday_amount_lorenz_gini_240m"
    assert science["coverage_gate_passed"] is True
    assert science["numeric_comparison_count"] == 142
    assert science["numeric_uniqueness_passed"] is False
    assert [item["name"] for item in science["failing_comparators"]] == [
        "intraday_amount_participation_entropy_240m",
        "intraday_morning_afternoon_amount_profile_similarity_120b",
    ]
    assert science["other_comparators_passed"] == 140
    assert science["development_trial_count"] == 0
    assert science["stress_trial_count_2024_2025"] == 0
    assert (
        terminal["research_boundary"][
            "historical_daily_price_or_forward_return_values_read"
        ]
        is False
    )


def test_coverage_and_all_uniqueness_results_are_exact() -> None:
    coverage = _load(COVERAGE)
    uniqueness = _load(UNIQUENESS)
    gate = coverage["coverage_and_variation"]
    assert gate["gate_passed_before_comparator_values"] is True
    assert gate["candidate_eligible_rows"] == 1_330_171
    assert gate["median_daily_coverage"] == 0.9994517542211769
    assert gate["p05_daily_coverage"] == 0.9956886515772271
    assert len(uniqueness["comparisons"]) == 142
    assert uniqueness["all_142_results_recorded_without_early_stop"] is True
    failed = [item for item in uniqueness["comparisons"] if not item["gate_passed"]]
    assert len(failed) == 2
    assert uniqueness["historical_daily_price_or_forward_return_values_read"] is False
    assert uniqueness["stress_2024_2025_return_values_opened"] is False


def test_append_only_ledger_v1_and_delta_v2_chain() -> None:
    v1 = _load(LEDGER_V1)
    previous = v1["authoritative_predecessor"]["chain_tip_sha256"]
    for ordinal, entry in enumerate(v1["entries"], 1):
        assert entry["ordinal"] == ordinal
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        previous = entry["entry_sha256"]
    assert previous == v1["chain_tip_sha256"]
    v2 = _load(LEDGER_V2)
    assert _sha256(LEDGER_V1) == v2["authoritative_predecessor"]["sha256"]
    entry = v2["delta_entries"][0]
    assert entry["ordinal"] == 23
    assert entry["previous_entry_sha256"] == v1["chain_tip_sha256"]
    assert entry["entry_sha256"] == _entry_hash(entry) == v2["chain_tip_sha256"]
    assert v2["effective_infrastructure_failure_attempt_count"] == 17
    assert v2["effective_prevalue_scientific_attempt_count"] == 6
    assert v2["cumulative_historical_research_attempt_count"] == 2533
    v3 = _load(LEDGER_V3)
    assert _sha256(LEDGER_V2) == v3["authoritative_predecessor"]["sha256"]
    previous = v2["chain_tip_sha256"]
    for ordinal, entry in enumerate(v3["delta_entries"], 24):
        assert entry["ordinal"] == ordinal
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        previous = entry["entry_sha256"]
    assert previous == v3["chain_tip_sha256"]
    assert v3["effective_entry_count"] == 28
    assert v3["effective_infrastructure_failure_attempt_count"] == 22
    assert v3["effective_prevalue_scientific_attempt_count"] == 6
    assert v3["cumulative_historical_research_attempt_count"] == 2538


def test_library_and_candidate49_semantics_remain_frozen() -> None:
    policy = _load(POLICY)
    assert (
        policy["complete_historical_feature_library"]["factor_definition_count"] == 160
    )
    assert (
        policy["complete_historical_feature_library"]["order_sha256"]
        == "2c431b3c9f9e772f7fdccab2625d671f8a836809710e78af8cb43d6d4e66cc0c"
    )
    assert (
        policy["numerical_comparator_eligibility"]["eligible_numeric_comparator_count"]
        == 142
    )
    assert (
        policy["numerical_comparator_eligibility"][
            "campaign261_numeric_comparator_appended"
        ]
        is False
    )
    assert (
        _sha256(SIGNAL)
        == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert (
        _sha256(EXECUTION)
        == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert _load(SIGNAL)["entries"] == []
    assert _load(EXECUTION)["entries"] == []


def test_unified_reports_have_one_matching_campaign261_section() -> None:
    for path in REPORTS:
        text = path.read_text(encoding="utf-8")
        assert text.count("## Campaign261：成交额 Lorenz-Gini 数值唯一性终止") == 1
        assert "−0.989313" in text
        assert "−0.892397" in text
        assert "累计历史尝试为 2,538" in text
        assert "Campaign262" in text


def test_campaign262_offline_boundary_is_authorized_without_current_use() -> None:
    policy = _load(POLICY)
    assert policy["future_campaign_boundary"]["next_campaign"] == 262
    assert (
        policy["future_campaign_boundary"][
            "historical_offline_prevalue_work_may_continue_at_any_local_time"
        ]
        is True
    )
    boundary = policy["research_boundary"]
    assert boundary["provider_or_web_request_issued"] is False
    assert boundary["candidate49_plan_or_run_executed"] is False
    assert (
        boundary["current_scoring_selection_sizing_positions_or_orders_performed"]
        is False
    )
    assert boundary["investment_advice"] is False
