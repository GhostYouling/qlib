import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_195_payment_processing_merchant_acquiring_authorization_clearing_settlement_dispute_reserve_lifecycle_source_frontier_20260815.json"
)
LEDGER_V1 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_195/research_attempt_ledger_v1.json"
)
LEDGER_V2 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_195/research_attempt_ledger_v2.json"
)
LEDGER_V3 = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_195/research_attempt_ledger_v3.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_195_terminal_result_v3_20260815.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v285_20260815.json"
)


def load(file_path):
    return json.loads(file_path.read_text())


def sha(file_path):
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def rooted(value):
    file_path = Path(value)
    return file_path if file_path.is_absolute() else ROOT / file_path


def test_campaign195_bindings_frontier_and_append_only_chain():
    for record in (load(FRONTIER), load(RESULT), load(POLICY)):
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
        len(
            frontier["mandatory_source_admission_gate"][
                "must_freeze_before_any_formula_or_direction"
            ]
        )
        == 12
    )
    evidence = frontier["repository_evidence"]
    assert (
        evidence[
            "dedicated_payment_processing_merchant_acquiring_lifecycle_frontier_found"
        ]
        is False
    )
    assert "Merchant counts" in evidence["campaign168_boundary"]
    assert "Merchant discount rates" in evidence["campaign169_boundary"]
    assert "payment-network reversal" in evidence["campaign170_boundary"]

    ledger = load(LEDGER_V1)
    previous = ledger["authoritative_predecessor"]["chain_tip_sha256"]
    for entry in ledger["delta_entries"]:
        assert sha(rooted(entry["evidence"]["path"])) == entry["evidence"]["sha256"]
        assert entry["previous_entry_sha256"] == previous
        previous = hashlib.sha256(
            "|".join(
                [
                    "campaign195",
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

    assert previous == ledger["chain_tip_sha256"]
    assert len(ledger["delta_entries"]) == ledger["effective_entry_count"] == 15
    assert ledger["effective_prevalue_scientific_attempt_count"] == 7
    assert ledger["effective_infrastructure_failure_attempt_count"] == 8
    assert ledger["cumulative_historical_research_attempt_count"] == 1747
    assert ledger["cumulative_return_reading_development_trial_count"] == 314

    for additive_path in (LEDGER_V2, LEDGER_V3):
        additive = load(additive_path)
        predecessor = additive["authoritative_predecessor"]
        assert sha(rooted(predecessor["path"])) == predecessor["sha256"]
        previous = predecessor["chain_tip_sha256"]
        for entry in additive["delta_entries"]:
            assert sha(rooted(entry["evidence"]["path"])) == entry["evidence"]["sha256"]
            assert entry["previous_entry_sha256"] == previous
            previous = hashlib.sha256(
                "|".join(
                    [
                        "campaign195",
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
        assert previous == additive["chain_tip_sha256"]

    ledger_v3 = load(LEDGER_V3)
    assert ledger_v3["effective_entry_count"] == 17
    assert ledger_v3["effective_prevalue_scientific_attempt_count"] == 7
    assert ledger_v3["effective_infrastructure_failure_attempt_count"] == 10
    assert ledger_v3["cumulative_historical_research_attempt_count"] == 1749
    assert ledger_v3["cumulative_return_reading_development_trial_count"] == 314

    result = load(RESULT)
    policy = load(POLICY)
    for accounting in (result["effective_accounting"], policy["effective_accounting"]):
        assert accounting["campaign195_attempt_count"] == 17
        assert accounting["campaign195_infrastructure_failure_count"] == 10
        assert accounting["cumulative_historical_research_attempt_count"] == 1749


def test_campaign195_reports_candidate49_and_research_boundaries():
    heading = "## Campaign195 支付处理、商户收单、授权清算结算与拒付准备金生命周期来源前沿值前终止"
    correction_heading = "### Campaign195 聚焦验证与报告追加失败会计"
    policy = load(POLICY)
    for key, file_path in {
        "current": ROOT / "data/experiments/short_horizon/current_research_report.md",
        "three_day": ROOT
        / "data/experiments/short_horizon/three_day_research_report.md",
    }.items():
        assert file_path.read_text().count(heading) == 1
        assert file_path.read_text().count(correction_heading) == 1
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

    assert policy["future_campaign_boundary"]["next_campaign"] == 196
    assert policy["future_campaign_boundary"][
        "2024_2025_source_or_returns_remain_closed"
    ]
    assert policy["candidate49"]["only_active_prospective_candidate"]
    assert all(value is False for value in policy["research_boundary"].values())
