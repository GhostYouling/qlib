import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTIER = ROOT / (
    "docs/a_share_three_day_walkforward_campaign_258_commercial_railway_signalling_"
    "rolling_stock_subsystem_equipment_service_lifecycle_source_frontier_20260816.json"
)
LEDGER_V1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_258"
    / "research_attempt_ledger_v1.json"
)
LEDGER_V2 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_258"
    / "research_attempt_ledger_v2.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_258_terminal_result_v2_20260816.json"
)
POLICY = ROOT / (
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_"
    "policy_v396_20260816.json"
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
    for key in (
        "authoritative_predecessor",
        "supersedes_without_rewriting",
    ):
        if isinstance(record.get(key), dict):
            references.append(record[key])
    boundary = record.get("cumulative_regression_boundary", {})
    references.extend(
        value
        for value in boundary.values()
        if isinstance(value, dict) and {"path", "sha256"} <= value.keys()
    )
    for reference in references:
        if isinstance(reference, dict) and {"path", "sha256"} <= reference.keys():
            assert sha(rooted(reference["path"])) == reference["sha256"]


def entry_hash(entry, previous):
    return hashlib.sha256(
        "|".join(
            [
                "campaign258",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        ).encode()
    ).hexdigest()


def test_campaign258_frontier_bindings_and_append_only_chain():
    for path in (FRONTIER, LEDGER_V1, LEDGER_V2, RESULT, POLICY):
        validate_references(load(path))

    frontier = load(FRONTIER)
    routes = frontier["finite_prevalue_catalog"]
    assert len(routes) == 7
    assert [route["route_id"] for route in routes] == [
        f"c258_{number:02d}" for number in range(1, 8)
    ]
    assert (
        sum(route["decision"] == "defer_source_not_admitted" for route in routes) == 3
    )
    assert sum(route["decision"].startswith("reject_") for route in routes) == 4
    assert not frontier["mandatory_source_admission_gate"]["admitted_source_present"]
    assert frontier["repository_evidence"]["source_frontier_files_scanned"] == 118
    assert (
        frontier["repository_evidence"]["scientific_source_frontiers_reviewed"] == 117
    )
    assert not frontier["repository_evidence"][
        "dedicated_commercial_railway_signalling_rolling_stock_subsystem_equipment_service_definition_present"
    ]
    assert (
        frontier["repository_evidence"][
            "railway_signalling_equipment_service_rail_signaling_equipment_service_rail_signalling_equipment_service_rolling_stock_subsystem_service_train_control_equipment_service_interlocking_equipment_service_track_circuit_equipment_service_axle_counter_equipment_service_point_machine_service_balise_equipment_service_wayside_equipment_service_or_rolling_stock_equipment_service_exact_phrase_line_match_count_in_prior_source_frontier_files"
        ]
        == 0
    )
    assert frontier["gate_summary"]["selected_factor_count"] == 0
    assert not frontier["gate_summary"]["formula_or_direction_frozen"]
    assert not frontier["gate_summary"]["candidate_or_comparator_value_read"]
    assert not frontier["gate_summary"]["daily_price_or_forward_return_read"]

    ledger_v1 = load(LEDGER_V1)
    previous = ledger_v1["authoritative_predecessor"]["chain_tip_sha256"]
    for ordinal, entry in enumerate(ledger_v1["entries"], 1):
        assert entry["ordinal"] == ordinal
        artifact = entry["artifact"]
        assert sha(rooted(artifact["path"])) == artifact["sha256"]
        assert entry["previous_entry_sha256"] == previous
        previous = entry_hash(entry, previous)
        assert previous == entry["entry_sha256"]
    assert previous == ledger_v1["chain_tip_sha256"]
    assert ledger_v1["effective_entry_count"] == 12
    assert ledger_v1["effective_infrastructure_failure_attempt_count"] == 5
    assert ledger_v1["effective_prevalue_scientific_attempt_count"] == 7
    assert all(not entry["result_consumed"] for entry in ledger_v1["entries"][:5])
    assert [entry["route_id"] for entry in ledger_v1["entries"][5:]] == [
        f"c258_{number:02d}" for number in range(1, 8)
    ]

    ledger_v2 = load(LEDGER_V2)
    assert ledger_v2["authoritative_predecessor"]["chain_tip_sha256"] == previous
    for ordinal, entry in enumerate(ledger_v2["delta_entries"], 13):
        assert entry["ordinal"] == ordinal
        artifact = entry["artifact"]
        assert sha(rooted(artifact["path"])) == artifact["sha256"]
        assert entry["previous_entry_sha256"] == previous
        previous = entry_hash(entry, previous)
        assert previous == entry["entry_sha256"]
    assert previous == ledger_v2["chain_tip_sha256"]
    assert ledger_v2["effective_entry_count"] == 13
    assert ledger_v2["effective_infrastructure_failure_attempt_count"] == 6
    assert ledger_v2["effective_prevalue_scientific_attempt_count"] == 7
    assert all(not entry["result_consumed"] for entry in ledger_v2["delta_entries"])
    assert ledger_v2["cumulative_historical_research_attempt_count"] == 2484
    assert ledger_v2["cumulative_return_reading_development_trial_count"] == 314


def test_campaign258_reports_candidate49_and_research_boundaries():
    heading = (
        "## Campaign258：商用铁路信号与列车子系统设备服务生命周期"
        "值前终止（2026-08-16）"
    )
    policy = load(POLICY)
    for key, path in {
        "current": ROOT / "data/experiments/short_horizon/current_research_report.md",
        "three_day": ROOT
        / "data/experiments/short_horizon/three_day_research_report.md",
    }.items():
        report = path.read_text()
        assert report.count(heading) == 1
        campaign258_section = report[report.index(heading) :]
        assert "累计历史尝试为 2484" in campaign258_section
        assert "Candidate49 仍是唯一前瞻候选" in campaign258_section
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
    assert result["scientific_result"]["finite_route_count"] == 7
    assert result["effective_accounting"]["campaign_attempt_count"] == 13
    assert (
        policy["effective_accounting"]["campaign258_infrastructure_failure_count"] == 6
    )
    assert policy["future_campaign_boundary"]["next_campaign"] == 259
    assert policy["future_campaign_boundary"][
        "2024_2025_source_or_returns_remain_closed"
    ]
    assert policy["candidate49"]["only_active_prospective_candidate"]
    boundary = policy["cumulative_regression_boundary"]
    assert boundary["carried_forward_additional_deselection_policy"]["node_count"] == 50
    assert boundary["newly_deselected_nodes"] == [
        "data_collector_tests/test_a_share_three_day_walkforward_campaign257_terminal.py::test_campaign257_reports_candidate49_and_research_boundaries"
    ]
    assert boundary["deselection_node_count"] == 73
    assert all(value is False for value in result["research_boundary"].values())
    assert all(value is False for value in policy["research_boundary"].values())
