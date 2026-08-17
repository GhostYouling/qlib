import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_192_bank_deposit_funding_franchise_lifecycle_source_frontier_20260815.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_192/research_attempt_ledger_v1.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_192_terminal_result_20260815.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v281_20260815.json"
)


def load(file_path):
    return json.loads(file_path.read_text())


def sha(file_path):
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def rooted(value):
    file_path = Path(value)
    return file_path if file_path.is_absolute() else ROOT / file_path


def test_campaign192_bindings_frontier_and_append_only_chain():
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

    ledger = load(LEDGER)
    previous = ledger["authoritative_predecessor"]["chain_tip_sha256"]
    for entry in ledger["delta_entries"]:
        assert sha(rooted(entry["evidence"]["path"])) == entry["evidence"]["sha256"]
        assert entry["previous_entry_sha256"] == previous
        previous = hashlib.sha256(
            "|".join(
                [
                    "campaign192",
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
    assert len(ledger["delta_entries"]) == ledger["effective_entry_count"] == 13
    assert ledger["effective_prevalue_scientific_attempt_count"] == 7
    assert ledger["effective_infrastructure_failure_attempt_count"] == 6
    assert ledger["cumulative_historical_research_attempt_count"] == 1711
    assert ledger["cumulative_return_reading_development_trial_count"] == 314

    result = load(RESULT)
    policy = load(POLICY)
    for accounting in (result["effective_accounting"], policy["effective_accounting"]):
        assert accounting["campaign192_attempt_count"] == 13
        assert accounting["campaign192_infrastructure_failure_count"] == 6
        assert accounting["cumulative_historical_research_attempt_count"] == 1711


def test_campaign192_reports_candidate49_and_research_boundaries():
    heading = "## Campaign192 银行存款资金来源与负债特许生命周期来源前沿值前终止"
    policy = load(POLICY)
    for key, file_path in {
        "current": ROOT / "data/experiments/short_horizon/current_research_report.md",
        "three_day": ROOT
        / "data/experiments/short_horizon/three_day_research_report.md",
    }.items():
        assert file_path.read_text().count(heading) == 1
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

    assert policy["future_campaign_boundary"]["next_campaign"] == 193
    assert policy["future_campaign_boundary"][
        "2024_2025_source_or_returns_remain_closed"
    ]
    assert policy["candidate49"]["only_active_prospective_candidate"]
    assert all(value is False for value in policy["research_boundary"].values())
