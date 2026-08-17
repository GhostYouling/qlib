import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTIER = ROOT / (
    "docs/a_share_three_day_walkforward_campaign_211_interactive_entertainment_"
    "game_player_session_match_content_liveops_virtual_item_economy_moderation_"
    "anticheat_refund_lifecycle_source_frontier_20260815.json"
)
LEDGER_V1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_211"
    / "research_attempt_ledger_v1.json"
)
LEDGER_V2 = LEDGER_V1.with_name("research_attempt_ledger_v2.json")
LEDGER = LEDGER_V1.with_name("research_attempt_ledger_v3.json")
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_211_terminal_result_v3_20260815.json"
)
POLICY = ROOT / (
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_"
    "policy_v320_20260815.json"
)


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rooted(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def validate_references(record):
    references = list(record.get("authoritative_inputs", {}).values())
    for key in ("authoritative_predecessor", "supersedes_without_rewriting"):
        if isinstance(record.get(key), dict):
            references.append(record[key])
    for reference in references:
        if isinstance(reference, dict) and {"path", "sha256"} <= reference.keys():
            assert sha(rooted(reference["path"])) == reference["sha256"]


def test_campaign211_frontier_bindings_and_append_only_chain():
    for path in (FRONTIER, LEDGER_V1, LEDGER_V2, LEDGER, RESULT, POLICY):
        validate_references(load(path))

    frontier = load(FRONTIER)
    routes = frontier["finite_prevalue_catalog"]
    assert len(routes) == 7
    assert [route["route_id"] for route in routes] == [
        f"c211_{number:02d}" for number in range(1, 8)
    ]
    assert (
        sum(route["decision"] == "defer_source_not_admitted" for route in routes) == 3
    )
    assert sum(route["decision"].startswith("reject_") for route in routes) == 4
    assert (
        frontier["mandatory_source_admission_gate"]["admitted_source_present"] is False
    )
    assert frontier["gate_summary"]["selected_factor_count"] == 0

    ledgers = [load(path) for path in (LEDGER_V1, LEDGER_V2, LEDGER)]
    previous = ledgers[0]["authoritative_predecessor"]["chain_tip_sha256"]
    observed_entry_count = 0
    for ledger in ledgers:
        assert ledger["authoritative_predecessor"]["chain_tip_sha256"] == previous
        for entry in ledger["delta_entries"]:
            artifact = entry.get("artifact") or entry.get("evidence")
            if artifact:
                assert sha(rooted(artifact["path"])) == artifact["sha256"]
            assert entry["previous_entry_sha256"] == previous
            previous = hashlib.sha256(
                "|".join(
                    [
                        "campaign211",
                        entry["attempt_id"],
                        previous,
                        entry["phase"],
                        entry["status"],
                    ]
                ).encode()
            ).hexdigest()
            assert previous == entry["entry_sha256"]
            observed_entry_count += 1
    ledger = ledgers[-1]
    assert previous == ledger["chain_tip_sha256"]
    assert observed_entry_count == ledger["effective_entry_count"] == 13
    assert ledger["effective_prevalue_scientific_attempt_count"] == 7
    assert ledger["effective_infrastructure_failure_attempt_count"] == 6
    assert ledger["cumulative_historical_research_attempt_count"] == 1956
    assert ledger["cumulative_return_reading_development_trial_count"] == 314


def test_campaign211_reports_candidate49_and_research_boundaries():
    heading = (
        "## Campaign211 互动娱乐玩家接入、会话匹配、内容运营、虚拟经济与"
        "完整性退款生命周期来源前沿值前终止"
    )
    policy = load(POLICY)
    for key, path in {
        "current": ROOT / "data/experiments/short_horizon/current_research_report.md",
        "three_day": ROOT
        / "data/experiments/short_horizon/three_day_research_report.md",
    }.items():
        report = path.read_text()
        assert report.count(heading) == 1
        assert "累计历史尝试 `1956`" in report
        assert "Candidate49 仍是唯一前瞻候选" in report
        assert (
            sha(path) == policy["mutable_unified_reports"][key]["sha256_at_publication"]
        )

    signal = (
        ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    )
    execution = (
        ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert sha(signal) == policy["candidate49"]["signal_ledger_sha256"]
    assert sha(execution) == policy["candidate49"]["execution_ledger_sha256"]
    assert load(signal)["entries"] == []
    assert load(execution)["entries"] == []

    result = load(RESULT)
    assert result["library_state"]["complete_factor_definition_count"] == 158
    assert result["library_state"]["eligible_numeric_comparator_count"] == 142
    assert result["result"]["selected_factor_count"] == 0
    assert policy["future_campaign_boundary"]["next_campaign"] == 212
    assert policy["future_campaign_boundary"][
        "2024_2025_source_or_returns_remain_closed"
    ]
    assert policy["candidate49"]["only_active_prospective_candidate"]
    assert all(value is False for value in policy["research_boundary"].values())
