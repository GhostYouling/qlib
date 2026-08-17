import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_196_inventory_production_conversion_aging_obsolescence_consignment_channel_sellthrough_custody_lifecycle_source_frontier_20260815.json"
)
REJECTION = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_196_semiconductor_fabrication_domain_overlap_rejection_20260815.json"
)
LEDGERS = tuple(
    ROOT
    / f"data/experiments/short_horizon/historical_walkforward/campaign_196/research_attempt_ledger_v{version}.json"
    for version in (1, 2, 3, 4, 5, 6)
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_196_terminal_result_v5_20260815.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v289_20260815.json"
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
    for reference in references:
        if (
            isinstance(reference, dict)
            and "path" in reference
            and "sha256" in reference
        ):
            assert sha(rooted(reference["path"])) == reference["sha256"]


def test_campaign196_bindings_frontier_rejection_and_append_only_chain():
    for record in (load(FRONTIER), load(REJECTION), load(RESULT), load(POLICY)):
        validate_references(record)

    rejection = load(REJECTION)
    assert rejection["selected_for_factor_definition"] is False
    assert rejection["formula"] is None
    assert rejection["direction"] is None
    assert rejection["bounded_repository_search"][
        "dedicated_prior_overlap_rejection_found"
    ]
    assert "Campaign167" in rejection["reason"]
    assert "Campaign168" in rejection["reason"]

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
        == 12
    )
    assert (
        frontier["repository_evidence"][
            "dedicated_physical_inventory_lifecycle_frontier_found"
        ]
        is False
    )

    expected_counts = (
        (11, 8, 3, 1760),
        (12, 8, 4, 1761),
        (13, 8, 5, 1762),
        (14, 8, 6, 1763),
        (15, 8, 7, 1764),
        (16, 8, 8, 1765),
    )
    for ledger_path, expected in zip(LEDGERS, expected_counts):
        ledger = load(ledger_path)
        validate_references(ledger)
        previous = ledger["authoritative_predecessor"]["chain_tip_sha256"]
        for entry in ledger["delta_entries"]:
            assert sha(rooted(entry["evidence"]["path"])) == entry["evidence"]["sha256"]
            assert entry["previous_entry_sha256"] == previous
            previous = hashlib.sha256(
                "|".join(
                    [
                        "campaign196",
                        entry["attempt_id"],
                        previous,
                        entry["phase"],
                        entry["status"],
                    ]
                ).encode()
            ).hexdigest()
            assert previous == entry["entry_sha256"]
            assert (
                entry["candidate_comparator_security_price_or_return_value_read"]
                is False
            )
        assert previous == ledger["chain_tip_sha256"]
        assert ledger["effective_entry_count"] == expected[0]
        assert ledger["effective_prevalue_scientific_attempt_count"] == expected[1]
        assert ledger["effective_infrastructure_failure_attempt_count"] == expected[2]
        assert ledger["cumulative_historical_research_attempt_count"] == expected[3]
        assert ledger["cumulative_return_reading_development_trial_count"] == 314

    result = load(RESULT)
    policy = load(POLICY)
    for accounting in (result["effective_accounting"], policy["effective_accounting"]):
        assert accounting["campaign196_attempt_count"] == 16
        assert accounting["campaign196_infrastructure_failure_count"] == 8
        assert accounting["cumulative_historical_research_attempt_count"] == 1765
        assert accounting["cumulative_return_reading_development_trial_count"] == 314


def test_campaign196_reports_candidate49_and_research_boundaries():
    heading = "## Campaign196 库存生产转换、库龄减值、寄售渠道销货与保管生命周期来源前沿值前终止"
    correction_heading = "### Campaign196 初次格式校验失败会计追加"
    cumulative_correction_heading = "### Campaign196 累计回归排除节点前缀失败会计追加"
    patch_correction_heading = "### Campaign196 聚焦测试会计更新补丁失败追加"
    policy = load(POLICY)
    for key, file_path in {
        "current": ROOT / "data/experiments/short_horizon/current_research_report.md",
        "three_day": ROOT
        / "data/experiments/short_horizon/three_day_research_report.md",
    }.items():
        report = file_path.read_text()
        assert report.count(heading) == 1
        assert report.count(correction_heading) == 1
        assert report.count(cumulative_correction_heading) == 1
        assert report.count(patch_correction_heading) == 1
        assert "Campaign196 最终有效会计" not in report
        assert "本轮最终有效会计为 13 次尝试（8 科学、5 基础设施）" in report
        assert (
            "Campaign196 有效会计追加校正为 14 次尝试（8 科学、6 基础设施）" in report
        )
        assert (
            "Campaign196 有效会计追加校正为 15 次尝试（8 科学、7 基础设施）" in report
        )
        assert (
            "Campaign196 有效会计追加校正为 16 次尝试（8 科学、8 基础设施）" in report
        )
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

    assert policy["future_campaign_boundary"]["next_campaign"] == 197
    assert policy["future_campaign_boundary"][
        "2024_2025_source_or_returns_remain_closed"
    ]
    assert policy["candidate49"]["only_active_prospective_candidate"]
    assert all(value is False for value in policy["research_boundary"].values())
