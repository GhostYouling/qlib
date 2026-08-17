import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTIER = ROOT / (
    "docs/a_share_three_day_walkforward_campaign_213_retail_merchandising_"
    "assortment_planogram_shelf_availability_replenishment_promotion_coupon_"
    "markdown_omnichannel_order_return_exchange_restock_lifecycle_source_"
    "frontier_20260815.json"
)
LEDGER_V1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_213"
    / "research_attempt_ledger_v1.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_213"
    / "research_attempt_ledger_v2.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_213_terminal_result_20260815.json"
)
POLICY = ROOT / (
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_"
    "policy_v323_20260815.json"
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


def test_campaign213_frontier_bindings_and_append_only_chain():
    for path in (FRONTIER, LEDGER_V1, LEDGER, RESULT, POLICY):
        validate_references(load(path))

    frontier = load(FRONTIER)
    routes = frontier["finite_prevalue_catalog"]
    assert len(routes) == 7
    assert [route["route_id"] for route in routes] == [
        f"c213_{number:02d}" for number in range(1, 8)
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

    previous = None
    observed_entries = 0
    for ledger_path in (LEDGER_V1, LEDGER):
        ledger = load(ledger_path)
        predecessor_tip = ledger["authoritative_predecessor"]["chain_tip_sha256"]
        if previous is None:
            previous = predecessor_tip
        else:
            assert predecessor_tip == previous
        for entry in ledger["delta_entries"]:
            artifact = entry.get("artifact") or entry.get("evidence")
            assert sha(rooted(artifact["path"])) == artifact["sha256"]
            assert entry["previous_entry_sha256"] == previous
            previous = hashlib.sha256(
                "|".join(
                    [
                        "campaign213",
                        entry["attempt_id"],
                        previous,
                        entry["phase"],
                        entry["status"],
                    ]
                ).encode()
            ).hexdigest()
            assert previous == entry["entry_sha256"]
            observed_entries += 1

    assert previous == ledger["chain_tip_sha256"]
    assert observed_entries == ledger["effective_entry_count"] == 9
    assert ledger["effective_prevalue_scientific_attempt_count"] == 7
    assert ledger["effective_infrastructure_failure_attempt_count"] == 2
    assert ledger["cumulative_historical_research_attempt_count"] == 1978
    assert ledger["cumulative_return_reading_development_trial_count"] == 314


def test_campaign213_reports_candidate49_and_research_boundaries():
    heading = (
        "## Campaign213 零售商品陈列补货、促销优惠与全渠道订单退换生命周期"
        "来源前沿值前终止"
    )
    policy = load(POLICY)
    for key, path in {
        "current": ROOT / "data/experiments/short_horizon/current_research_report.md",
        "three_day": ROOT
        / "data/experiments/short_horizon/three_day_research_report.md",
    }.items():
        report = path.read_text()
        assert report.count(heading) == 1
        assert "累计历史尝试为 `1978`" in report
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
    assert result["effective_accounting"]["campaign_attempt_count"] == 9
    assert (
        policy["effective_accounting"]["campaign213_infrastructure_failure_count"] == 2
    )
    assert policy["future_campaign_boundary"]["next_campaign"] == 214
    assert policy["future_campaign_boundary"][
        "2024_2025_source_or_returns_remain_closed"
    ]
    assert policy["candidate49"]["only_active_prospective_candidate"]
    assert all(value is False for value in policy["research_boundary"].values())
