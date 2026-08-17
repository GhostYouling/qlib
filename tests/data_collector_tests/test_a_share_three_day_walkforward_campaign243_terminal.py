import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTIER = ROOT / (
    "docs/a_share_three_day_walkforward_campaign_243_commercial_electrical_"
    "power_system_service_lifecycle_source_frontier_20260816.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_243"
    / "research_attempt_ledger_v1.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_243_terminal_result_20260816.json"
)
POLICY = ROOT / (
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_"
    "policy_v374_20260816.json"
)
FAILURES = [
    ROOT / "docs/a_share_three_day_walkforward_campaign_243_skill_lines_621_660_"
    "combined_truncated_failure_20260816.json",
    ROOT / "docs/a_share_three_day_walkforward_campaign_243_authority_status_combined_"
    "output_truncated_failure_20260816.json",
]


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


def validate_chain(ledger):
    previous = ledger["authoritative_predecessor"]["chain_tip_sha256"]
    for entry in ledger["entries"]:
        artifact = entry["artifact"]
        assert sha(rooted(artifact["path"])) == artifact["sha256"]
        assert entry["previous_entry_sha256"] == previous
        previous = hashlib.sha256(
            "|".join(
                [
                    "campaign243",
                    entry["attempt_id"],
                    previous,
                    entry["phase"],
                    entry["status"],
                ]
            ).encode()
        ).hexdigest()
        assert previous == entry["entry_sha256"]
    assert previous == ledger["chain_tip_sha256"]


def test_campaign243_frontier_bindings_and_append_only_chain():
    for path in (FRONTIER, LEDGER, RESULT, POLICY, *FAILURES):
        validate_references(load(path))

    frontier = load(FRONTIER)
    routes = frontier["finite_prevalue_catalog"]
    assert len(routes) == 7
    assert [route["route_id"] for route in routes] == [
        f"c243_{number:02d}" for number in range(1, 8)
    ]
    assert (
        sum(route["decision"] == "defer_source_not_admitted" for route in routes) == 3
    )
    assert sum(route["decision"].startswith("reject_") for route in routes) == 4
    assert (
        frontier["mandatory_source_admission_gate"]["admitted_source_present"] is False
    )
    assert frontier["repository_evidence"]["source_frontier_files_reviewed"] == 102
    assert (
        frontier["repository_evidence"][
            "dedicated_commercial_electrical_power_system_service_definition_present"
        ]
        is False
    )
    assert (
        frontier["repository_evidence"][
            "switchgear_automatic_transfer_switch_load_bank_power_quality_or_electrical_preventive_maintenance_exact_keyword_line_match_count_in_prior_source_frontiers"
        ]
        == 0
    )
    assert frontier["gate_summary"]["selected_factor_count"] == 0
    assert frontier["gate_summary"]["formula_or_direction_frozen"] is False
    assert frontier["gate_summary"]["candidate_or_comparator_value_read"] is False
    assert frontier["gate_summary"]["daily_price_or_forward_return_read"] is False

    ledger = load(LEDGER)
    validate_chain(ledger)
    assert ledger["effective_entry_count"] == 9
    assert ledger["effective_infrastructure_failure_attempt_count"] == 2
    assert ledger["effective_prevalue_scientific_attempt_count"] == 7
    assert ledger["cumulative_historical_research_attempt_count"] == 2316
    assert ledger["cumulative_return_reading_development_trial_count"] == 314
    assert [entry["ordinal"] for entry in ledger["entries"]] == list(range(1, 10))
    for failure in FAILURES:
        record = load(failure)
        assert record["evidence_treatment"]["output_discarded"]
        assert not record["evidence_treatment"]["used_as_scientific_evidence"]
        assert not record["evidence_treatment"]["used_as_validation_evidence"]


def test_campaign243_reports_candidate49_and_research_boundaries():
    heading = "## Campaign243 商业电力系统服务合同、设备台账、预防维保、电能质量与负载测试、故障修复、配件合规与计费生命周期来源前沿值前终止"
    policy = load(POLICY)
    for key, path in {
        "current": ROOT / "data/experiments/short_horizon/current_research_report.md",
        "three_day": ROOT
        / "data/experiments/short_horizon/three_day_research_report.md",
    }.items():
        report = path.read_text()
        assert report.count(heading) == 1
        campaign243_section = report[report.index(heading) :]
        assert "累计历史尝试为 `2316`" in campaign243_section
        assert "Candidate49 仍是唯一前瞻候选" in campaign243_section
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
    assert result["effective_accounting"]["campaign_attempt_count"] == 9
    assert (
        policy["effective_accounting"]["campaign243_infrastructure_failure_count"] == 2
    )
    assert policy["future_campaign_boundary"]["next_campaign"] == 244
    assert policy["future_campaign_boundary"][
        "2024_2025_source_or_returns_remain_closed"
    ]
    assert policy["candidate49"]["only_active_prospective_candidate"]
    assert (
        policy["cumulative_regression_boundary"][
            "carried_forward_additional_deselected_nodes"
        ][-1]
        == "data_collector_tests/test_a_share_three_day_walkforward_campaign242_terminal.py::test_campaign242_reports_candidate49_and_research_boundaries"
    )
    assert all(value is False for value in result["research_boundary"].values())
    assert all(value is False for value in policy["research_boundary"].values())
