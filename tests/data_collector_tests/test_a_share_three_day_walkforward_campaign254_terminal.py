import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PARKING = ROOT / (
    "docs/a_share_three_day_walkforward_campaign_254_commercial_parking_access_"
    "revenue_control_equipment_domain_overlap_rejection_v2_20260816.json"
)
FRONTIER = ROOT / (
    "docs/a_share_three_day_walkforward_campaign_254_commercial_audiovisual_"
    "conference_room_equipment_service_lifecycle_source_frontier_20260816.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_254"
    / "research_attempt_ledger_v1.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_254_terminal_result_20260816.json"
)
POLICY = ROOT / (
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_"
    "policy_v386_20260816.json"
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
                "campaign254",
                entry["attempt_id"],
                previous,
                entry["phase"],
                entry["status"],
            ]
        ).encode()
    ).hexdigest()


def test_campaign254_frontier_bindings_and_append_only_chain():
    for path in (PARKING, FRONTIER, LEDGER, RESULT, POLICY):
        validate_references(load(path))

    parking = load(PARKING)
    assert parking["decision"] == "reject_terminal_overlap"
    assert "Campaign232" in parking["overlap_finding"]
    assert not parking["research_boundary"][
        "source_or_candidate_or_comparator_value_read"
    ]

    frontier = load(FRONTIER)
    routes = frontier["finite_prevalue_catalog"]
    assert len(routes) == 7
    assert [route["route_id"] for route in routes] == [
        f"c254_{number:02d}" for number in range(1, 8)
    ]
    assert (
        sum(route["decision"] == "defer_source_not_admitted" for route in routes) == 3
    )
    assert sum(route["decision"].startswith("reject_") for route in routes) == 4
    assert not frontier["mandatory_source_admission_gate"]["admitted_source_present"]
    assert frontier["repository_evidence"]["source_frontier_files_reviewed"] == 113
    assert not frontier["repository_evidence"][
        "dedicated_commercial_audiovisual_conference_room_equipment_service_definition_present"
    ]
    assert (
        frontier["repository_evidence"][
            "commercial_audiovisual_audio_visual_audiovisual_equipment_service_projection_equipment_digital_signage_conference_room_equipment_sound_system_projector_display_panel_or_video_wall_service_exact_phrase_line_match_count_in_prior_source_frontiers"
        ]
        == 0
    )
    assert frontier["repository_evidence"][
        "parking_access_revenue_control_equipment_candidate_rejected_before_catalog_freeze"
    ]
    assert frontier["gate_summary"]["selected_factor_count"] == 0
    assert not frontier["gate_summary"]["formula_or_direction_frozen"]
    assert not frontier["gate_summary"]["candidate_or_comparator_value_read"]
    assert not frontier["gate_summary"]["daily_price_or_forward_return_read"]

    ledger = load(LEDGER)
    previous = ledger["authoritative_predecessor"]["chain_tip_sha256"]
    for ordinal, entry in enumerate(ledger["entries"], 1):
        assert entry["ordinal"] == ordinal
        artifact = entry["artifact"]
        assert sha(rooted(artifact["path"])) == artifact["sha256"]
        assert entry["previous_entry_sha256"] == previous
        previous = entry_hash(entry, previous)
        assert previous == entry["entry_sha256"]
    assert previous == ledger["chain_tip_sha256"]
    assert ledger["effective_entry_count"] == 18
    assert ledger["effective_infrastructure_failure_attempt_count"] == 10
    assert ledger["effective_prevalue_scientific_attempt_count"] == 8
    assert all(not entry["result_consumed"] for entry in ledger["entries"][:10])
    assert ledger["entries"][10]["domain"].startswith("commercial_parking")
    assert ledger["cumulative_historical_research_attempt_count"] == 2431
    assert ledger["cumulative_return_reading_development_trial_count"] == 314


def test_campaign254_reports_candidate49_and_research_boundaries():
    heading = "## Campaign254：商用视听与会议室设备服务生命周期值前终止（2026-08-16）"
    policy = load(POLICY)
    for key, path in {
        "current": ROOT / "data/experiments/short_horizon/current_research_report.md",
        "three_day": ROOT
        / "data/experiments/short_horizon/three_day_research_report.md",
    }.items():
        report = path.read_text()
        assert report.count(heading) == 1
        campaign254_section = report[report.index(heading) :]
        assert "累计历史尝试为 2431" in campaign254_section
        assert "Candidate49 仍是唯一前瞻候选" in campaign254_section
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
    assert (
        result["scientific_result"]["pre_catalog_domain_overlap_rejection_count"] == 1
    )
    assert result["effective_accounting"]["campaign_attempt_count"] == 18
    assert (
        policy["effective_accounting"]["campaign254_infrastructure_failure_count"] == 10
    )
    assert policy["future_campaign_boundary"]["next_campaign"] == 255
    assert policy["future_campaign_boundary"][
        "2024_2025_source_or_returns_remain_closed"
    ]
    assert policy["candidate49"]["only_active_prospective_candidate"]
    carried = policy["cumulative_regression_boundary"][
        "carried_forward_additional_deselected_nodes"
    ]
    assert len(carried) == 47
    assert (
        carried[-1]
        == "data_collector_tests/test_a_share_three_day_walkforward_campaign253_terminal.py::test_campaign253_reports_candidate49_and_research_boundaries"
    )
    assert policy["cumulative_regression_boundary"]["deselection_node_count"] == 69
    assert all(value is False for value in result["research_boundary"].values())
    assert all(value is False for value in policy["research_boundary"].values())
