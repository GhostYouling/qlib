from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign152_features as features

ROOT = Path(__file__).resolve().parents[2]
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_189_insurer_underwriting_claims_reserve_source_frontier_20260815.json"
)
CHECKPOINT = (
    ROOT
    / "docs/a_share_three_day_iteration_status_20260815_campaign189_prevalue_in_progress.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_189/research_attempt_ledger_v1.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_189_terminal_result_20260815.json"
)
REPORT = (
    ROOT / "docs/a_share_three_day_walkforward_campaign_189_terminal_report_20260815.md"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v278_20260815.json"
)
SIGNAL = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION = (
    ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def test_campaign189_bindings_and_finite_frontier() -> None:
    for path in (FRONTIER, CHECKPOINT, TERMINAL, POLICY):
        record = load(path)
        refs = list(record.get("authoritative_inputs", {}).values())
        if isinstance(record.get("supersedes_without_rewriting"), dict):
            refs.append(record["supersedes_without_rewriting"])
        for ref in refs:
            if isinstance(ref, dict) and "path" in ref and "sha256" in ref:
                assert sha(resolve(ref["path"])) == ref["sha256"]
    routes = load(FRONTIER)["finite_prevalue_catalog"]
    assert [x["catalog_id"] for x in routes] == [f"c189_0{i}" for i in range(1, 8)]
    assert all(x["formula"] is None and x["direction"] is None for x in routes)
    assert sum(x["new_issuer_state"] for x in routes) == 4
    assert load(FRONTIER)["gate_summary"]["selected_candidate_count"] == 0


def test_campaign189_gate_and_attempt_chain() -> None:
    frontier = load(FRONTIER)
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
    ledger = load(LEDGER)
    predecessor = ledger["authoritative_predecessor"]
    assert sha(ROOT / predecessor["path"]) == predecessor["sha256"]
    previous = predecessor["chain_tip_sha256"]
    for entry in ledger["delta_entries"]:
        assert entry["previous_entry_sha256"] == previous
        previous = hashlib.sha256(
            "|".join(
                [
                    "campaign189",
                    entry["attempt_id"],
                    previous,
                    entry["phase"],
                    entry["status"],
                ]
            ).encode()
        ).hexdigest()
        assert previous == entry["entry_sha256"]
        assert sha(ROOT / entry["evidence"]["path"]) == entry["evidence"]["sha256"]
    assert previous == ledger["chain_tip_sha256"]
    assert ledger["effective_entry_count"] == 7
    assert ledger["effective_infrastructure_failure_attempt_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 1670


def test_campaign189_library_policy_and_candidate49() -> None:
    definitions = features.reconstruct_complete_definitions()
    definitions.append(
        {"name": "eastmoney_debt_maturity_resilience", "score_direction": "higher"}
    )
    comparisons = features.reconstruct_comparisons()
    policy = load(POLICY)
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
    assert policy["future_campaign_boundary"]["next_campaign"] == 190
    assert policy["future_campaign_boundary"][
        "2024_2025_source_or_returns_remain_closed"
    ]
    assert (
        sha(SIGNAL)
        == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert (
        sha(EXECUTION)
        == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )


def test_campaign189_reports_are_appended_once() -> None:
    heading = "## Campaign189 保险承保与赔款准备金来源前沿值前终止"
    assert "7 次科学尝试、0 次基础设施失败" in REPORT.read_text(encoding="utf-8")
    for path in (
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        assert "Campaign189 最终有效会计为 7 次科学尝试、0 次基础设施失败" in text


def test_campaign189_timestamps() -> None:
    for path in (FRONTIER, CHECKPOINT, LEDGER, TERMINAL, POLICY):
        recorded = datetime.fromisoformat(load(path)["recorded_at"])
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=recorded.tzinfo)
        assert recorded <= modified
