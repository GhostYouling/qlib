from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign152_features as features


ROOT = Path(__file__).resolve().parents[2]
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_188_mineral_resource_reserve_conversion_source_frontier_20260815.json"
)
FAILURES = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_188_skill_full_read_output_truncation_failure_20260815.json",
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_188_skill_chunk_read_output_truncation_failure_20260815.json",
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_188/research_attempt_ledger_v1.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_188_terminal_result_20260815.json"
)
REPORT = (
    ROOT / "docs/a_share_three_day_walkforward_campaign_188_terminal_report_20260815.md"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v277_20260815.json"
)
SIGNAL_LEDGER = (
    ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER = (
    ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def test_campaign188_bindings_and_finite_frontier() -> None:
    for path in (FRONTIER, *FAILURES, TERMINAL, POLICY):
        record = _load(path)
        superseded = record.get("supersedes_without_rewriting")
        refs = [superseded] if isinstance(superseded, dict) else []
        refs += list(record.get("authoritative_inputs", {}).values())
        for binding in refs:
            if isinstance(binding, dict) and "path" in binding and "sha256" in binding:
                bound = _resolve(binding["path"])
                assert bound.is_file() and _sha(bound) == binding["sha256"]
    routes = _load(FRONTIER)["finite_prevalue_catalog"]
    assert [item["catalog_id"] for item in routes] == [
        f"c188_0{i}" for i in range(1, 8)
    ]
    assert all(item["formula"] is None and item["direction"] is None for item in routes)
    assert all(
        not item["parameters_filters_subsets_combinations_models"] for item in routes
    )
    assert sum(item["new_issuer_state"] for item in routes) == 4
    assert sum(item["complete_local_source_contract"] for item in routes) == 0
    assert _load(FRONTIER)["gate_summary"]["selected_candidate_count"] == 0


def test_campaign188_source_gate_failures_and_attempt_chain() -> None:
    frontier = _load(FRONTIER)
    assert (
        len(
            frontier["mandatory_source_admission_gate"][
                "must_freeze_before_any_formula_or_direction"
            ]
        )
        == 12
    )
    assert (
        frontier["mandatory_source_admission_gate"][
            "formula_direction_parameter_filter_subset_combination_or_model_choice_allowed_before_gate"
        ]
        is False
    )
    for path in FAILURES:
        failure = _load(path)
        assert failure["status"].startswith("recorded_recovered")
        assert failure["recovery"]["fingerprint_unchanged"] is True
        assert failure["research_boundary"]["scientific_attempt"] is False
    ledger = _load(LEDGER)
    predecessor = ledger["authoritative_predecessor"]
    assert _sha(ROOT / predecessor["path"]) == predecessor["sha256"]
    previous = predecessor["chain_tip_sha256"]
    for entry in ledger["delta_entries"]:
        assert entry["previous_entry_sha256"] == previous
        previous = hashlib.sha256(
            "|".join(
                [
                    "campaign188",
                    entry["attempt_id"],
                    previous,
                    entry["phase"],
                    entry["status"],
                ]
            ).encode()
        ).hexdigest()
        assert entry["entry_sha256"] == previous
        assert _sha(ROOT / entry["evidence"]["path"]) == entry["evidence"]["sha256"]
        assert (
            entry["candidate_comparator_security_price_or_return_value_read"] is False
        )
    assert previous == ledger["chain_tip_sha256"]
    assert ledger["effective_entry_count"] == 9
    assert ledger["effective_prevalue_scientific_attempt_count"] == 7
    assert ledger["effective_infrastructure_failure_attempt_count"] == 2
    assert ledger["cumulative_historical_research_attempt_count"] == 1663
    assert ledger["cumulative_return_reading_development_trial_count"] == 314


def test_campaign188_library_policy_and_candidate49_boundaries() -> None:
    definitions = features.reconstruct_complete_definitions()
    definitions.append(
        {"name": "eastmoney_debt_maturity_resilience", "score_direction": "higher"}
    )
    comparisons = features.reconstruct_comparisons()
    policy = _load(POLICY)
    assert len(definitions) == 158
    assert (
        features._order_digest(definitions)
        == "4819c7fd7c0795d7598a52f3c615e3f117d5f4ecd9332974bc8e3dfa57c96667"
    )
    assert len(comparisons) == 142
    assert (
        features._order_digest(comparisons)
        == "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf"
    )
    assert policy["complete_historical_feature_library"]["unchanged_from_v276"]
    assert policy["numerical_comparator_eligibility"]["unchanged_from_v276"]
    assert policy["future_campaign_boundary"]["next_campaign"] == 189
    assert policy["future_campaign_boundary"][
        "2024_2025_source_or_returns_remain_closed"
    ]
    assert (
        policy["deferred_source_boundary"][
            "current_technical_report_or_latest_reserve_table_may_be_historically_backfilled"
        ]
        is False
    )
    assert (
        _sha(SIGNAL_LEDGER)
        == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert (
        _sha(EXECUTION_LEDGER)
        == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )


def test_campaign188_reports_are_appended_exactly_once() -> None:
    heading = "## Campaign188 矿产资源与储量转换来源前沿值前终止"
    assert "9 次尝试（7 科学、2 基础设施）" in REPORT.read_text(encoding="utf-8")
    for path in (
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        assert "Campaign188 最终有效会计为 9 次尝试（7 科学、2 基础设施）" in text


def test_campaign188_records_use_reached_wall_clock_timestamps() -> None:
    for path in (FRONTIER, *FAILURES, LEDGER, TERMINAL, POLICY):
        recorded_at = datetime.fromisoformat(_load(path)["recorded_at"])
        modified_at = datetime.fromtimestamp(
            path.stat().st_mtime, tz=recorded_at.tzinfo
        )
        assert recorded_at <= modified_at
