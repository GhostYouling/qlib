import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTIER = ROOT / (
    "docs/a_share_three_day_walkforward_campaign_201_healthcare_provider_patient_"
    "referral_appointment_admission_care_episode_discharge_readmission_payer_"
    "claim_reimbursement_lifecycle_source_frontier_20260815.json"
)
LEDGERS = tuple(
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_201"
    / f"research_attempt_ledger_v{version}.json"
    for version in range(1, 6)
)
LEDGER = LEDGERS[-1]
RESULT = ROOT / (
    "docs/a_share_three_day_walkforward_campaign_201_terminal_result_v5_20260815.json"
)
POLICY = ROOT / (
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_"
    "policy_v299_20260815.json"
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


def test_campaign201_bindings_frontier_privacy_and_append_only_chain():
    for record in (load(FRONTIER), load(RESULT), load(POLICY)):
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
        == 12
    )
    assert (
        frontier["repository_evidence"][
            "dedicated_issuer_as_healthcare_provider_care_episode_and_"
            "reimbursement_lifecycle_frontier_found"
        ]
        is False
    )
    assert (
        frontier["research_boundary"][
            "protected_health_information_or_directly_identifiable_patient_data_read"
        ]
        is False
    )

    ledgers = [load(file_path) for file_path in LEDGERS]
    ledger = ledgers[-1]
    previous = None
    for current_ledger in ledgers:
        predecessor = current_ledger["authoritative_predecessor"]
        assert sha(rooted(predecessor["path"])) == predecessor["sha256"]
        assert previous in (None, predecessor["chain_tip_sha256"])
        previous = predecessor["chain_tip_sha256"]
        for entry in current_ledger["delta_entries"]:
            assert sha(rooted(entry["evidence"]["path"])) == entry["evidence"]["sha256"]
            assert entry["previous_entry_sha256"] == previous
            previous = hashlib.sha256(
                "|".join(
                    [
                        "campaign201",
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
        assert previous == current_ledger["chain_tip_sha256"]
    assert ledger["effective_entry_count"] == 14
    assert ledger["effective_prevalue_scientific_attempt_count"] == 7
    assert ledger["effective_infrastructure_failure_attempt_count"] == 7
    assert ledger["cumulative_historical_research_attempt_count"] == 1833
    assert ledger["cumulative_return_reading_development_trial_count"] == 314


def test_campaign201_reports_candidate49_and_research_boundaries():
    heading = (
        "## Campaign201 医疗服务提供者患者准入、诊疗、出院再入院与医保结算"
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
        assert "Campaign201 最终有效会计为 14 次尝试（7 科学、7 基础设施）" in report
        assert "累计历史尝试 `1833`" in report
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
    assert policy["future_campaign_boundary"]["next_campaign"] == 202
    assert policy["future_campaign_boundary"][
        "2024_2025_source_or_returns_remain_closed"
    ]
    assert policy["candidate49"]["only_active_prospective_candidate"]
    assert all(value is False for value in policy["research_boundary"].values())
