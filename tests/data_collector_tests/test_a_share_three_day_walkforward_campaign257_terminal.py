import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTIER = ROOT / (
    "docs/a_share_three_day_walkforward_campaign_257_commercial_semiconductor_"
    "fabrication_advanced_packaging_equipment_service_lifecycle_source_frontier_"
    "20260816.json"
)
LEDGER_V1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_257"
    / "research_attempt_ledger_v1.json"
)
LEDGER_V2 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_257"
    / "research_attempt_ledger_v2.json"
)
LEDGER_V3 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_257"
    / "research_attempt_ledger_v3.json"
)
LEDGER_V4 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_257"
    / "research_attempt_ledger_v4.json"
)
LEDGER_V5 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_257"
    / "research_attempt_ledger_v5.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_257_terminal_result_v5_20260816.json"
)
POLICY = ROOT / (
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_"
    "policy_v394_20260816.json"
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
        "supersedes_invalid_draft_without_rewriting",
    ):
        if isinstance(record.get(key), dict):
            references.append(record[key])
    for reference in references:
        if isinstance(reference, dict) and {"path", "sha256"} <= reference.keys():
            assert sha(rooted(reference["path"])) == reference["sha256"]


def entry_hash(entry, previous):
    return hashlib.sha256(
        "|".join(
            [
                "campaign257",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        ).encode()
    ).hexdigest()


def test_campaign257_frontier_bindings_and_append_only_chain():
    for path in (
        FRONTIER,
        LEDGER_V1,
        LEDGER_V2,
        LEDGER_V3,
        LEDGER_V4,
        LEDGER_V5,
        RESULT,
        POLICY,
    ):
        validate_references(load(path))

    frontier = load(FRONTIER)
    routes = frontier["finite_prevalue_catalog"]
    assert len(routes) == 7
    assert [route["route_id"] for route in routes] == [
        f"c257_{number:02d}" for number in range(1, 8)
    ]
    assert (
        sum(route["decision"] == "defer_source_not_admitted" for route in routes) == 3
    )
    assert sum(route["decision"].startswith("reject_") for route in routes) == 4
    assert not frontier["mandatory_source_admission_gate"]["admitted_source_present"]
    assert frontier["repository_evidence"]["source_frontier_files_scanned"] == 117
    assert (
        frontier["repository_evidence"]["scientific_source_frontiers_reviewed"] == 116
    )
    assert not frontier["repository_evidence"][
        "dedicated_commercial_semiconductor_fabrication_advanced_packaging_equipment_service_definition_present"
    ]
    assert (
        frontier["repository_evidence"][
            "commercial_semiconductor_fabrication_equipment_commercial_semiconductor_fabrication_and_advanced_packaging_equipment_service_lifecycle_semiconductor_fabrication_equipment_service_semiconductor_equipment_service_wafer_fabrication_equipment_service_wafer_fab_equipment_service_lithography_equipment_service_etch_equipment_service_deposition_equipment_service_ion_implantation_equipment_service_wafer_inspection_equipment_service_semiconductor_metrology_equipment_service_wafer_dicing_equipment_service_die_bonding_equipment_service_wire_bonding_equipment_service_or_advanced_packaging_equipment_service_exact_phrase_line_match_count_in_prior_source_frontier_files"
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
    assert ledger_v1["effective_entry_count"] == 11
    assert ledger_v1["effective_infrastructure_failure_attempt_count"] == 4
    assert ledger_v1["effective_prevalue_scientific_attempt_count"] == 7
    assert all(not entry["result_consumed"] for entry in ledger_v1["entries"][:4])
    assert [entry["route_id"] for entry in ledger_v1["entries"][4:]] == [
        f"c257_{number:02d}" for number in range(1, 8)
    ]

    ledger_v2 = load(LEDGER_V2)
    assert ledger_v2["authoritative_predecessor"]["chain_tip_sha256"] == previous
    for ordinal, entry in enumerate(ledger_v2["delta_entries"], 12):
        assert entry["ordinal"] == ordinal
        artifact = entry["artifact"]
        assert sha(rooted(artifact["path"])) == artifact["sha256"]
        assert entry["previous_entry_sha256"] == previous
        previous = entry_hash(entry, previous)
        assert previous == entry["entry_sha256"]
    assert previous == ledger_v2["chain_tip_sha256"]
    assert ledger_v2["effective_entry_count"] == 12
    assert ledger_v2["effective_infrastructure_failure_attempt_count"] == 5
    assert ledger_v2["effective_prevalue_scientific_attempt_count"] == 7
    assert all(not entry["result_consumed"] for entry in ledger_v2["delta_entries"])
    assert ledger_v2["cumulative_historical_research_attempt_count"] == 2468
    assert ledger_v2["cumulative_return_reading_development_trial_count"] == 314

    ledger_v3 = load(LEDGER_V3)
    assert ledger_v3["authoritative_predecessor"]["chain_tip_sha256"] == previous
    for ordinal, entry in enumerate(ledger_v3["delta_entries"], 13):
        assert entry["ordinal"] == ordinal
        artifact = entry["artifact"]
        assert sha(rooted(artifact["path"])) == artifact["sha256"]
        assert entry["previous_entry_sha256"] == previous
        previous = entry_hash(entry, previous)
        assert previous == entry["entry_sha256"]
    assert previous == ledger_v3["chain_tip_sha256"]
    assert ledger_v3["effective_entry_count"] == 13
    assert ledger_v3["effective_infrastructure_failure_attempt_count"] == 6
    assert ledger_v3["effective_prevalue_scientific_attempt_count"] == 7
    assert all(not entry["result_consumed"] for entry in ledger_v3["delta_entries"])
    assert ledger_v3["cumulative_historical_research_attempt_count"] == 2469
    assert ledger_v3["cumulative_return_reading_development_trial_count"] == 314

    ledger_v4 = load(LEDGER_V4)
    assert ledger_v4["authoritative_predecessor"]["chain_tip_sha256"] == previous
    for ordinal, entry in enumerate(ledger_v4["delta_entries"], 14):
        assert entry["ordinal"] == ordinal
        artifact = entry["artifact"]
        assert sha(rooted(artifact["path"])) == artifact["sha256"]
        assert entry["previous_entry_sha256"] == previous
        previous = entry_hash(entry, previous)
        assert previous == entry["entry_sha256"]
    assert previous == ledger_v4["chain_tip_sha256"]
    assert ledger_v4["effective_entry_count"] == 14
    assert ledger_v4["effective_infrastructure_failure_attempt_count"] == 7
    assert ledger_v4["effective_prevalue_scientific_attempt_count"] == 7
    assert all(not entry["result_consumed"] for entry in ledger_v4["delta_entries"])
    assert ledger_v4["cumulative_historical_research_attempt_count"] == 2470
    assert ledger_v4["cumulative_return_reading_development_trial_count"] == 314

    ledger_v5 = load(LEDGER_V5)
    assert ledger_v5["authoritative_predecessor"]["chain_tip_sha256"] == previous
    for ordinal, entry in enumerate(ledger_v5["delta_entries"], 15):
        assert entry["ordinal"] == ordinal
        artifact = entry["artifact"]
        assert sha(rooted(artifact["path"])) == artifact["sha256"]
        assert entry["previous_entry_sha256"] == previous
        previous = entry_hash(entry, previous)
        assert previous == entry["entry_sha256"]
    assert previous == ledger_v5["chain_tip_sha256"]
    assert ledger_v5["effective_entry_count"] == 15
    assert ledger_v5["effective_infrastructure_failure_attempt_count"] == 8
    assert ledger_v5["effective_prevalue_scientific_attempt_count"] == 7
    assert all(not entry["result_consumed"] for entry in ledger_v5["delta_entries"])
    assert ledger_v5["cumulative_historical_research_attempt_count"] == 2471
    assert ledger_v5["cumulative_return_reading_development_trial_count"] == 314


def test_campaign257_reports_candidate49_and_research_boundaries():
    heading = (
        "## Campaign257：商用半导体晶圆制造与先进封装设备服务生命周期"
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
        campaign257_section = report[report.index(heading) :]
        assert "累计历史尝试为 2471" in campaign257_section
        assert "Candidate49 仍是唯一前瞻候选" in campaign257_section
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
    assert result["effective_accounting"]["campaign_attempt_count"] == 15
    assert (
        policy["effective_accounting"]["campaign257_infrastructure_failure_count"] == 8
    )
    assert policy["future_campaign_boundary"]["next_campaign"] == 258
    assert policy["future_campaign_boundary"][
        "2024_2025_source_or_returns_remain_closed"
    ]
    assert policy["candidate49"]["only_active_prospective_candidate"]
    carried = policy["cumulative_regression_boundary"][
        "carried_forward_additional_deselected_nodes"
    ]
    assert len(carried) == 50
    assert (
        carried[-1]
        == "data_collector_tests/test_a_share_three_day_walkforward_campaign256_terminal.py::test_campaign256_reports_candidate49_and_research_boundaries"
    )
    assert policy["cumulative_regression_boundary"]["deselection_node_count"] == 72
    assert all(value is False for value in result["research_boundary"].values())
    assert all(value is False for value in policy["research_boundary"].values())
