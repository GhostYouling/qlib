import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTIER = ROOT / (
    "docs/a_share_three_day_walkforward_campaign_207_digital_advertising_"
    "campaign_inventory_delivery_measurement_invalid_traffic_billing_makegood_"
    "dispute_settlement_lifecycle_source_frontier_20260815.json"
)
LEDGER_V1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_207"
    / "research_attempt_ledger_v1.json"
)
LEDGER_V2 = LEDGER_V1.with_name("research_attempt_ledger_v2.json")
LEDGER_V3 = LEDGER_V1.with_name("research_attempt_ledger_v3.json")
LEDGER_V4 = LEDGER_V1.with_name("research_attempt_ledger_v4.json")
LEDGER_V5 = LEDGER_V1.with_name("research_attempt_ledger_v5.json")
LEDGER_V6 = LEDGER_V1.with_name("research_attempt_ledger_v6.json")
LEDGER_V7 = LEDGER_V1.with_name("research_attempt_ledger_v7.json")
RESULT = ROOT / (
    "docs/a_share_three_day_walkforward_campaign_207_terminal_result_v6_20260815.json"
)
POLICY = ROOT / (
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_"
    "policy_v313_20260815.json"
)


def load(file_path):
    return json.loads(file_path.read_text())


def sha(file_path):
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def rooted(value):
    file_path = Path(value)
    return file_path if file_path.is_absolute() else ROOT / file_path


def validate_references(record):
    references = list(record.get("authoritative_inputs", {}).values())
    if isinstance(record.get("supersedes_without_rewriting"), dict):
        references.append(record["supersedes_without_rewriting"])
    if isinstance(record.get("authoritative_predecessor"), dict):
        references.append(record["authoritative_predecessor"])
    for reference in references:
        if (
            isinstance(reference, dict)
            and "path" in reference
            and "sha256" in reference
        ):
            assert sha(rooted(reference["path"])) == reference["sha256"]


def test_campaign207_bindings_frontier_safety_and_corrected_append_only_chain():
    for record in (
        load(FRONTIER),
        load(LEDGER_V2),
        load(LEDGER_V3),
        load(LEDGER_V4),
        load(LEDGER_V5),
        load(LEDGER_V6),
        load(LEDGER_V7),
        load(RESULT),
        load(POLICY),
    ):
        validate_references(record)

    frontier = load(FRONTIER)
    routes = frontier["finite_prevalue_catalog"]
    assert len(routes) == 7
    assert all(route["formula"] is None for route in routes)
    assert all(route["direction"] is None for route in routes)
    assert all(
        not route["parameters_filters_subsets_combinations_models"] for route in routes
    )
    assert sum(route["new_issuer_state"] for route in routes) == 3
    assert (
        sum(
            route["decision"] == "deferred_source_admission_not_factor_failure"
            for route in routes
        )
        == 3
    )
    assert sum(route["decision"].startswith("rejected_") for route in routes) == 4
    assert (
        len(
            frontier["mandatory_source_admission_gate"][
                "must_freeze_before_any_formula_or_direction"
            ]
        )
        == 11
    )
    assert (
        frontier["repository_evidence"][
            "dedicated_issuer_as_digital_advertising_platform_or_media_operator_lifecycle_frontier_found"
        ]
        is False
    )
    assert (
        frontier["research_boundary"][
            "person_device_precise_location_browsing_sensitive_category_cross_site_identity_or_reidentifiable_ad_event_record_read"
        ]
        is False
    )

    ledger_v1 = load(LEDGER_V1)
    ledger_v2 = load(LEDGER_V2)
    ledger_v3 = load(LEDGER_V3)
    ledger_v4 = load(LEDGER_V4)
    ledger_v5 = load(LEDGER_V5)
    ledger_v6 = load(LEDGER_V6)
    ledger_v7 = load(LEDGER_V7)
    correction = ledger_v2["declared_corrections"]
    assert len(correction) == 1
    assert correction[0]["json_pointer"] == "/delta_entries/1/evidence/sha256"
    assert correction[0]["scientific_result_changed"] is False
    entries = copy.deepcopy(ledger_v1["delta_entries"])
    entries[1]["evidence"]["sha256"] = correction[0]["corrected_value"]
    entries.extend(ledger_v2["appended_entries"])
    entries.extend(ledger_v3["delta_entries"])
    entries.extend(ledger_v4["delta_entries"])
    entries.extend(ledger_v5["delta_entries"])
    entries.extend(ledger_v6["delta_entries"])
    entries.extend(ledger_v7["delta_entries"])

    previous = ledger_v2["authoritative_predecessor"]["chain_tip_sha256"]
    for entry in entries:
        assert sha(rooted(entry["evidence"]["path"])) == entry["evidence"]["sha256"]
        assert entry["previous_entry_sha256"] == previous
        previous = hashlib.sha256(
            "|".join(
                [
                    "campaign207",
                    entry["attempt_id"],
                    previous,
                    entry["phase"],
                    entry["status"],
                ]
            ).encode()
        ).hexdigest()
        assert previous == entry["entry_sha256"]
        assert (
            entry["candidate_comparator_security_price_or_return_value_read"] is False
        )
    assert previous == ledger_v7["chain_tip_sha256"]
    assert len(entries) == ledger_v7["effective_entry_count"] == 19
    assert ledger_v7["effective_prevalue_scientific_attempt_count"] == 7
    assert ledger_v7["effective_infrastructure_failure_attempt_count"] == 12
    assert ledger_v7["cumulative_historical_research_attempt_count"] == 1908
    assert ledger_v7["cumulative_return_reading_development_trial_count"] == 314


def test_campaign207_reports_candidate49_and_research_boundaries():
    heading = (
        "## Campaign207 数字广告活动订单、库存投放、测量无效流量与账单补量争议结算"
        "生命周期来源前沿值前终止"
    )
    policy = load(POLICY)
    for key, file_path in {
        "current": ROOT / "data/experiments/short_horizon/current_research_report.md",
        "three_day": ROOT
        / "data/experiments/short_horizon/three_day_research_report.md",
    }.items():
        report = file_path.read_text()
        assert report.count(heading) == 1
        assert report.count("### Campaign207 聚焦测试 Black 检查失败会计追加") == 1
        assert (
            report.count("### Campaign207 累计回归剔除节点工作目录不匹配会计追加") == 1
        )
        assert (
            report.count("### Campaign207 聚焦测试最新绑定补丁上下文失败会计追加") == 1
        )
        assert report.count("### Campaign207 累计回归测试工作目录导入失败会计追加") == 1
        assert report.count("### Campaign207 累计回归前缀 node id 不匹配会计追加") == 1
        assert (
            "Campaign207 最终有效会计更正为 19 次尝试（7 科学、12 基础设施）" in report
        )
        assert "累计历史尝试 `1908`" in report
        assert (
            sha(file_path)
            == policy["mutable_unified_reports"][key]["sha256_at_publication"]
        )

    signal = (
        ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    )
    execution = (
        ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert (
        sha(signal)
        == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert (
        sha(execution)
        == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert load(signal)["entries"] == []
    assert load(execution)["entries"] == []

    result = load(RESULT)
    assert result["library_state"]["complete_factor_definition_count"] == 158
    assert result["library_state"]["eligible_numeric_comparator_count"] == 142
    assert result["candidate49"]["completed_future_workflow_record_count"] == 0
    assert policy["future_campaign_boundary"]["next_campaign"] == 208
    assert policy["future_campaign_boundary"][
        "2024_2025_source_or_returns_remain_closed"
    ]
    assert policy["candidate49"]["only_active_prospective_candidate"]
    assert all(value is False for value in policy["research_boundary"].values())
