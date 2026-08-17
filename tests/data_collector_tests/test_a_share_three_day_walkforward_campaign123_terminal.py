import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TERMINAL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_123_namechange_source_acceptance_terminal_20260814.json"
)
POLICY_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v124_20260814.json"
)
LEDGER_V3_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_123/research_attempt_ledger_v3.json"
)
LEDGER_V4_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_123/research_attempt_ledger_v4.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_terminal_record_binds_one_shot_failure_and_no_accepted_outputs() -> None:
    terminal = load_json(TERMINAL_PATH)
    assert terminal["plan_evidence"]["ready"] is True
    assert terminal["plan_evidence"]["exit_code"] == 0
    run = terminal["run_evidence"]
    assert run["exit_code"] == 2
    assert run["provider_calls_issued"] == 7
    assert run["failure_code"] == "source_schema_or_canonicalization_contract_failure"
    assert run["retry_performed"] is False
    assert run["raw_provider_rows_persisted"] is False
    for key in ("intent", "failure_record"):
        binding = terminal["authoritative_inputs"][key]
        assert sha256(REPO_ROOT / binding["path"]) == binding["sha256"]
        assert binding["mode"] == "0600"
    assert terminal["publication_evidence"]["accepted_snapshot_exists"] is False
    assert terminal["publication_evidence"]["accepted_manifest_exists"] is False
    assert not (
        REPO_ROOT
        / "data/raw/a_share/rich/tushare/namechange/snapshots/campaign123_2019_2025_v1.json"
    ).exists()
    assert not (
        REPO_ROOT
        / "data/metadata/rich_data/runs/campaign123_namechange_acceptance_v1.json"
    ).exists()


def test_v124_terminalizes_candidate_without_changing_148_139_orders() -> None:
    policy = load_json(POLICY_PATH)
    complete = policy["complete_historical_feature_library"]
    numeric = policy["numerical_comparator_eligibility"]
    terminal = policy["campaign123_terminal_classification"]
    assert (
        complete["factor_definition_count"],
        numeric["eligible_numeric_comparator_count"],
    ) == (148, 139)
    assert (
        complete["order_sha256"]
        == "fa9f0254b17d1a2b568e056b2696f24087f3f0668d7842a1bcbfdde1a87192e8"
    )
    assert (
        numeric["eligible_numeric_comparator_order_sha256"]
        == "9c4de054ca1b83eced67eece256b024ebec3a6e1925de17a4cedfa7d36265161"
    )
    assert terminal["terminal"] is True
    assert terminal["source_acceptance_authorization_remaining"] is False
    assert (
        terminal[
            "retry_relabel_field_reason_window_direction_threshold_source_substitution_or_rescue_allowed"
        ]
        is False
    )


def test_v4_ledger_appends_two_hash_chained_entries_and_final_accounting() -> None:
    prior = load_json(LEDGER_V3_PATH)
    ledger = load_json(LEDGER_V4_PATH)
    assert ledger["supersedes_without_rewriting"]["sha256"] == sha256(LEDGER_V3_PATH)
    assert (
        ledger["supersedes_without_rewriting"]["preserved_chain_tip_sha256"]
        == prior["chain_tip_sha256"]
    )
    previous = prior["chain_tip_sha256"]
    for entry in ledger["appended_entries"]:
        assert entry["previous_entry_sha256"] == previous
        material = (
            "campaign123|"
            + entry["attempt_id"]
            + "|"
            + previous
            + "|"
            + entry["phase"]
            + "|"
            + entry["status"]
        )
        assert hashlib.sha256(material.encode()).hexdigest() == entry["entry_sha256"]
        previous = entry["entry_sha256"]
    assert ledger["chain_tip_sha256"] == previous
    assert ledger["attempt_count"] == ledger["ledger_entry_count"] == 15
    assert ledger["infrastructure_failure_count"] == 11
    assert ledger["source_acceptance_attempt_count"] == 1
    assert ledger["cumulative_historical_research_attempt_count"] == 1014
    assert ledger["cumulative_return_reading_development_trial_count"] == 306


def test_candidate49_remains_the_only_empty_prospective_ledger() -> None:
    signal = (
        REPO_ROOT
        / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
    )
    execution = (
        REPO_ROOT
        / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
    )
    assert (
        sha256(signal)
        == "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert (
        sha256(execution)
        == "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert load_json(signal)["entries"] == []
    assert load_json(execution)["entries"] == []
