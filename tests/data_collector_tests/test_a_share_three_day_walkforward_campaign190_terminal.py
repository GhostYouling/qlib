import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_190_clinical_trial_evidence_lifecycle_source_frontier_20260815.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_190/research_attempt_ledger_v1.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_190_terminal_result_20260815.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v279_20260815.json"
)


def load(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def path(v):
    p = Path(v)
    return p if p.is_absolute() else ROOT / p


def test_campaign190_bindings_frontier_and_chain():
    for record in (load(FRONTIER), load(RESULT), load(POLICY)):
        refs = list(record.get("authoritative_inputs", {}).values())
        if isinstance(record.get("supersedes_without_rewriting"), dict):
            refs.append(record["supersedes_without_rewriting"])
        for x in refs:
            if isinstance(x, dict) and "path" in x and "sha256" in x:
                assert sha(path(x["path"])) == x["sha256"]
    routes = load(FRONTIER)["finite_prevalue_catalog"]
    assert len(routes) == 7
    assert all(x["formula"] is None and x["direction"] is None for x in routes)
    assert (
        len(
            load(FRONTIER)["mandatory_source_admission_gate"][
                "must_freeze_before_any_formula_or_direction"
            ]
        )
        == 12
    )
    d = load(LEDGER)
    prev = d["authoritative_predecessor"]["chain_tip_sha256"]
    for e in d["delta_entries"]:
        assert sha(path(e["evidence"]["path"])) == e["evidence"]["sha256"]
        assert e["previous_entry_sha256"] == prev
        prev = hashlib.sha256(
            "|".join(
                ["campaign190", e["attempt_id"], prev, e["phase"], e["status"]]
            ).encode()
        ).hexdigest()
        assert prev == e["entry_sha256"]
    assert (
        prev == d["chain_tip_sha256"]
        and len(d["delta_entries"]) == d["effective_entry_count"] == 15
        and d["effective_prevalue_scientific_attempt_count"] == 7
        and d["effective_infrastructure_failure_attempt_count"] == 8
        and d["cumulative_historical_research_attempt_count"] == 1685
        and d["cumulative_return_reading_development_trial_count"] == 314
    )
    result = load(RESULT)
    policy = load(POLICY)
    for accounting in (result["effective_accounting"], policy["effective_accounting"]):
        assert accounting["campaign190_attempt_count"] == 15
        assert accounting["campaign190_infrastructure_failure_count"] == 8
        assert accounting["cumulative_historical_research_attempt_count"] == 1685


def test_campaign190_reports_candidate49_and_boundaries():
    heading = "## Campaign190 临床试验证据生命周期来源前沿值前终止"
    policy = load(POLICY)
    for key, p in {
        "current": ROOT / "data/experiments/short_horizon/current_research_report.md",
        "three_day": ROOT
        / "data/experiments/short_horizon/three_day_research_report.md",
    }.items():
        assert p.read_text().count(heading) == 1
        assert sha(p) == policy["mutable_unified_reports"][key]["sha256_at_publication"]
    assert (
        sha(
            ROOT
            / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
        )
        == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert (
        sha(
            ROOT
            / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
        )
        == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert (
        policy["future_campaign_boundary"]["next_campaign"] == 191
        and policy["future_campaign_boundary"][
            "2024_2025_source_or_returns_remain_closed"
        ]
    )
