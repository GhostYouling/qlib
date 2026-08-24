import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    REPO_ROOT
    / "scripts/a_share_three_day_walkforward_campaign265_source_acceptance_plan.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "a_share_three_day_walkforward_campaign265_source_acceptance_plan",
        MODULE_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_plan_is_ready_and_freezes_exact_schedule() -> None:
    module = load_module()
    plan = module.build_plan()
    assert plan["ready"] is True
    assert plan["exit_code_if_executed"] == 0
    assert plan["accepted_trade_date_count"] == 1699
    assert plan["accepted_trade_dates"][0] == "2019-01-02"
    assert plan["accepted_trade_dates"][-1] == "2025-12-31"
    assert len(set(plan["accepted_trade_dates"])) == 1699
    assert plan["exact_provider_call_count"] == 1700
    assert plan["cb_basic_fields"] == list(module.CB_BASIC_FIELDS)
    assert plan["cb_daily_fields"] == list(module.CB_DAILY_FIELDS)
    assert plan["blockers"] == []


def test_plan_binds_date_and_request_sequence_digests() -> None:
    module = load_module()
    plan = module.build_plan()
    assert (
        plan["accepted_trade_dates_canonical_newline_sha256"]
        == module.ACCEPTED_DATE_LIST_SHA256
    )
    assert (
        plan["request_sequence_canonical_json_sha256"] == module.REQUEST_SEQUENCE_SHA256
    )
    assert all(plan["checks"].values())


def test_plan_contains_only_private_repo_data_destinations() -> None:
    module = load_module()
    plan = module.build_plan()
    destinations = plan["destinations"]
    assert set(destinations) == set(module.DESTINATIONS)
    assert all(value.startswith("data/") for value in destinations.values())
    assert destinations["staging_root"].endswith(".staging")
    assert "{trade_date}" in destinations["cb_daily_checkpoint_template"]


def test_plan_has_no_credential_provider_or_write_interface() -> None:
    module = load_module()
    plan = module.build_plan()
    assert plan["credential_file_or_environment_inspected"] is False
    assert plan["credential_value_or_digest_read"] is False
    assert plan["provider_client_imported_or_created"] is False
    assert plan["provider_request_issued"] is False
    assert plan["source_candidate_comparator_price_or_return_value_read"] is False
    assert plan["filesystem_write_performed"] is False
    assert plan["run_or_confirmation_interface_exposed"] is False
    assert plan["ready_does_not_authorize_credential_load_or_provider_request"] is True


def test_source_has_no_secret_or_transport_loader() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "TUSHARE_TOKEN" not in source
    assert '".env"' not in source
    assert "import requests" not in source
    assert "import tushare" not in source
    assert "pro_api" not in source
    assert "run_acceptance" not in source
    assert "confirm-provider" not in source


def test_calendar_mutation_fails_closed_even_if_file_binding_is_updated(
    tmp_path, monkeypatch
) -> None:
    module = load_module()
    calendar = tmp_path / "calendar.txt"
    original = (REPO_ROOT / module.BASELINE_BINDINGS["calendar"][0]).read_text(
        encoding="utf-8"
    )
    calendar.write_text(original.replace("2019-01-03\n", "", 1), encoding="utf-8")
    digest = hashlib.sha256(calendar.read_bytes()).hexdigest()
    monkeypatch.setitem(module.BASELINE_BINDINGS, "calendar", (str(calendar), digest))
    plan = module.build_plan()
    assert plan["ready"] is False
    assert plan["checks"]["binding_calendar"] is True
    assert plan["checks"]["accepted_date_count_exact"] is False
    assert plan["checks"]["accepted_date_list_digest_exact"] is False


def test_any_existing_attempt_evidence_blocks_new_plan(tmp_path, monkeypatch) -> None:
    module = load_module()
    failure = tmp_path / "terminal_failure.json"
    failure.write_text("{}\n", encoding="utf-8")
    monkeypatch.setitem(module.DESTINATIONS, "terminal_failure", str(failure))
    plan = module.build_plan()
    assert plan["ready"] is False
    assert plan["checks"]["terminal_failure_absent"] is False
    assert "terminal_failure_absent" in plan["blockers"]


def test_candidate49_ledger_binding_fails_closed(tmp_path, monkeypatch) -> None:
    module = load_module()
    ledger = tmp_path / "candidate49.json"
    ledger.write_text('{"entries":[{"forbidden":true}]}\n', encoding="utf-8")
    monkeypatch.setitem(
        module.BASELINE_BINDINGS,
        "candidate49_signal_ledger",
        (str(ledger), module.BASELINE_BINDINGS["candidate49_signal_ledger"][1]),
    )
    plan = module.build_plan()
    assert plan["ready"] is False
    assert plan["checks"]["binding_candidate49_signal_ledger"] is False


def test_policy_authorizes_plan_only_and_binds_current_bytes() -> None:
    module = load_module()
    policy = json.loads(module.AUTHORIZATION_POLICY_PATH.read_text(encoding="utf-8"))
    authorization = policy["campaign265_source_acceptance_plan_authorization"]
    assert authorization["authorized"] is True
    assert authorization["plan_only"] is True
    assert authorization["credential_load_allowed"] is False
    assert authorization["provider_request_allowed"] is False
    assert authorization["run_interface_allowed"] is False
    assert authorization["planner"]["sha256"] == module.file_sha256(MODULE_PATH)
    assert authorization["planner_tests"]["sha256"] == module.file_sha256(
        Path(__file__)
    )


def test_cli_plan_exits_zero_outputs_one_json_and_writes_nothing() -> None:
    module = load_module()
    watched = [
        REPO_ROOT / module.DESTINATIONS[name]
        for name in (
            "staging_root",
            "final_root",
            "intent",
            "attempt_journal",
            "terminal_failure",
            "repository_acceptance_manifest",
        )
    ]
    before = [path.exists() for path in watched]
    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "plan"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stderr == ""
    output = json.loads(result.stdout)
    assert output["ready"] is True
    assert output["accepted_trade_date_count"] == 1699
    assert [path.exists() for path in watched] == before


def test_cli_exposes_no_run_command() -> None:
    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "run"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "invalid choice" in result.stderr


def test_preregistration_freezes_terminal_no_retry_semantics() -> None:
    preregistration = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_265_source_acceptance_preregistration_20260824.json"
        ).read_text(encoding="utf-8")
    )
    state_machine = preregistration["durable_one_shot_state_machine"]
    assert (
        state_machine[
            "intent_and_journal_created_exclusively_and_fsynced_before_credential_load"
        ]
        is True
    )
    assert (
        state_machine[
            "authorized_request_without_matching_committed_checkpoint_is_terminal_no_retry_evidence"
        ]
        is True
    )
    assert (
        state_machine["failed_response_must_not_be_requested_again_for_diagnostics"]
        is True
    )
    planner = preregistration["planner_contract"]
    assert planner["only_cli_command"] == "plan"
    assert planner["credential_file_or_environment_inspection"] is False
    assert planner["provider_client_or_transport_interface"] is False
