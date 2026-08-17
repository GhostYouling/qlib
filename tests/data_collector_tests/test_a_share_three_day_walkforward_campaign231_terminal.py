import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTIER = ROOT / (
    "docs/a_share_three_day_walkforward_campaign_231_elevator_escalator_"
    "installation_commissioning_registration_inspection_maintenance_fault_"
    "entrapment_rescue_modernization_decommissioning_lifecycle_source_"
    "frontier_20260816.json"
)
LEDGER_V1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_231"
    / "research_attempt_ledger_v1.json"
)
LEDGER_V2 = LEDGER_V1.with_name("research_attempt_ledger_v2.json")
LEDGER_V3 = LEDGER_V1.with_name("research_attempt_ledger_v3.json")
LEDGER_V4 = LEDGER_V1.with_name("research_attempt_ledger_v4.json")
LEDGER_V5 = LEDGER_V1.with_name("research_attempt_ledger_v5.json")
LEDGER_V6 = LEDGER_V1.with_name("research_attempt_ledger_v6.json")
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_231_terminal_result_v2_20260816.json"
)
POLICY = ROOT / (
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_"
    "policy_v352_20260816.json"
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


def validate_chain_segment(ledger, initial_previous):
    previous = initial_previous
    for entry in ledger["delta_entries"]:
        artifact = entry.get("artifact") or entry.get("evidence")
        assert sha(rooted(artifact["path"])) == artifact["sha256"]
        assert entry["previous_entry_sha256"] == previous
        previous = hashlib.sha256(
            "|".join(
                [
                    "campaign231",
                    entry["attempt_id"],
                    previous,
                    entry["phase"],
                    entry["status"],
                ]
            ).encode()
        ).hexdigest()
        assert previous == entry["entry_sha256"]
    assert previous == ledger["chain_tip_sha256"]


def test_campaign231_frontier_bindings_and_append_only_chain():
    for path in (
        FRONTIER,
        LEDGER_V1,
        LEDGER_V2,
        LEDGER_V3,
        LEDGER_V4,
        LEDGER_V5,
        LEDGER_V6,
        RESULT,
        POLICY,
    ):
        validate_references(load(path))

    frontier = load(FRONTIER)
    routes = frontier["finite_prevalue_catalog"]
    assert len(routes) == 7
    assert [route["route_id"] for route in routes] == [
        f"c231_{number:02d}" for number in range(1, 8)
    ]
    assert (
        sum(route["decision"] == "defer_source_not_admitted" for route in routes) == 3
    )
    assert sum(route["decision"].startswith("reject_") for route in routes) == 4
    assert (
        frontier["mandatory_source_admission_gate"]["admitted_source_present"] is False
    )
    assert frontier["gate_summary"]["selected_factor_count"] == 0
    assert frontier["gate_summary"]["formula_or_direction_frozen"] is False
    assert frontier["gate_summary"]["candidate_or_comparator_value_read"] is False
    assert frontier["gate_summary"]["daily_price_or_forward_return_read"] is False

    expected = [
        (LEDGER_V1, 1, 1, 0),
        (LEDGER_V2, 1, 2, 0),
        (LEDGER_V3, 1, 3, 0),
        (LEDGER_V4, 7, 10, 7),
        (LEDGER_V5, 1, 11, 7),
        (LEDGER_V6, 1, 12, 7),
    ]
    for path, delta_count, effective_count, scientific_count in expected:
        ledger = load(path)
        validate_chain_segment(
            ledger, ledger["authoritative_predecessor"]["chain_tip_sha256"]
        )
        assert len(ledger["delta_entries"]) == delta_count
        assert ledger["effective_entry_count"] == effective_count
        assert ledger["effective_prevalue_scientific_attempt_count"] == scientific_count

    ledger_v6 = load(LEDGER_V6)
    assert ledger_v6["effective_infrastructure_failure_attempt_count"] == 5
    assert ledger_v6["cumulative_historical_research_attempt_count"] == 2177
    assert ledger_v6["cumulative_return_reading_development_trial_count"] == 314


def test_campaign231_reports_candidate49_and_research_boundaries():
    heading = "## Campaign231 电梯扶梯安装、验收登记、检修维保、故障救援与更新退役生命周期来源前沿值前终止"
    policy = load(POLICY)
    for key, path in {
        "current": ROOT / "data/experiments/short_horizon/current_research_report.md",
        "three_day": ROOT
        / "data/experiments/short_horizon/three_day_research_report.md",
    }.items():
        report = path.read_text()
        assert report.count(heading) == 1
        campaign231_section = report[report.index(heading) :]
        assert "累计历史尝试更正为 `2177`" in campaign231_section
        assert "Candidate49 仍是唯一前瞻候选" in campaign231_section
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
    assert result["scientific_result"]["selected_factor_count"] == 0
    assert result["effective_accounting"]["campaign_attempt_count"] == 12
    assert (
        policy["effective_accounting"]["campaign231_infrastructure_failure_count"] == 5
    )
    assert policy["future_campaign_boundary"]["next_campaign"] == 232
    assert policy["future_campaign_boundary"][
        "2024_2025_source_or_returns_remain_closed"
    ]
    assert policy["candidate49"]["only_active_prospective_candidate"]
    assert all(value is False for value in result["research_boundary"].values())
    assert all(value is False for value in policy["research_boundary"].values())
