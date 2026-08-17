import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTIER = ROOT / (
    "docs/a_share_three_day_walkforward_campaign_226_physical_records_management_"
    "intake_custody_storage_retrieval_retention_hold_destruction_certificate_"
    "billing_lifecycle_source_frontier_20260816.json"
)
LEDGER_V1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_226"
    / "research_attempt_ledger_v1.json"
)
LEDGER_V2 = LEDGER_V1.with_name("research_attempt_ledger_v2.json")
LEDGER_V3 = LEDGER_V1.with_name("research_attempt_ledger_v3.json")
LEDGER_V4 = LEDGER_V1.with_name("research_attempt_ledger_v4.json")
LEDGER_V5 = LEDGER_V1.with_name("research_attempt_ledger_v5.json")
RESULT = ROOT / (
    "docs/a_share_three_day_walkforward_campaign_226_terminal_result_v5_20260816.json"
)
POLICY = ROOT / (
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_"
    "policy_v343_20260816.json"
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
                    "campaign226",
                    entry["attempt_id"],
                    previous,
                    entry["phase"],
                    entry["status"],
                ]
            ).encode()
        ).hexdigest()
        assert previous == entry["entry_sha256"]
    assert previous == ledger["chain_tip_sha256"]


def test_campaign226_frontier_bindings_and_append_only_chain():
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
        f"c226_{number:02d}" for number in range(1, 8)
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

    ledger_v1 = load(LEDGER_V1)
    validate_chain_segment(
        ledger_v1, ledger_v1["authoritative_predecessor"]["chain_tip_sha256"]
    )
    assert len(ledger_v1["delta_entries"]) == 9

    ledger_v2 = load(LEDGER_V2)
    validate_chain_segment(
        ledger_v2, ledger_v2["authoritative_predecessor"]["chain_tip_sha256"]
    )
    assert len(ledger_v2["delta_entries"]) == 1

    ledger_v3 = load(LEDGER_V3)
    validate_chain_segment(
        ledger_v3, ledger_v3["authoritative_predecessor"]["chain_tip_sha256"]
    )
    assert len(ledger_v3["delta_entries"]) == 1

    ledger_v4 = load(LEDGER_V4)
    validate_chain_segment(
        ledger_v4, ledger_v4["authoritative_predecessor"]["chain_tip_sha256"]
    )
    assert len(ledger_v4["delta_entries"]) == 1

    ledger_v5 = load(LEDGER_V5)
    validate_chain_segment(
        ledger_v5, ledger_v5["authoritative_predecessor"]["chain_tip_sha256"]
    )
    assert len(ledger_v5["delta_entries"]) == 1
    assert ledger_v5["effective_entry_count"] == 13
    assert ledger_v5["effective_prevalue_scientific_attempt_count"] == 7
    assert ledger_v5["effective_infrastructure_failure_attempt_count"] == 6
    assert ledger_v5["cumulative_historical_research_attempt_count"] == 2122
    assert ledger_v5["cumulative_return_reading_development_trial_count"] == 314


def test_campaign226_reports_candidate49_and_research_boundaries():
    heading = (
        "## Campaign226 实体档案接收保管、检索归还、留存冻结、销毁证明与计费"
        "生命周期来源前沿值前终止"
    )
    correction_heading = "### Campaign226 累计撤选目录检查失败会计追加"
    selection_correction_heading = "### Campaign226 累计测试文件选择失败会计追加"
    test_patch_correction_heading = "### Campaign226 终结测试策略更新补丁失败会计追加"
    policy = load(POLICY)
    for key, path in {
        "current": ROOT / "data/experiments/short_horizon/current_research_report.md",
        "three_day": ROOT
        / "data/experiments/short_horizon/three_day_research_report.md",
    }.items():
        report = path.read_text()
        assert report.count(heading) == 1
        assert report.count(correction_heading) == 1
        assert report.count(selection_correction_heading) == 1
        assert report.count(test_patch_correction_heading) == 1
        campaign226_section = report[report.index(heading) :]
        assert "累计历史尝试更正为 `2122`" in campaign226_section
        assert "Candidate49 仍是唯一前瞻候选" in campaign226_section
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
    assert result["effective_accounting"]["campaign_attempt_count"] == 13
    assert (
        policy["effective_accounting"]["campaign226_infrastructure_failure_count"] == 6
    )
    assert policy["future_campaign_boundary"]["next_campaign"] == 227
    assert policy["future_campaign_boundary"][
        "2024_2025_source_or_returns_remain_closed"
    ]
    assert policy["candidate49"]["only_active_prospective_candidate"]
    assert all(value is False for value in result["research_boundary"].values())
    assert all(value is False for value in policy["research_boundary"].values())
