import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    REPO_ROOT
    / "scripts/a_share_three_day_walkforward_campaign265_source_acceptance_workflow.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "campaign265_source_acceptance_workflow", MODULE_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.value += seconds


class SyntheticStop(BaseException):
    pass


class SyntheticProvider:
    def __init__(self, clock: FakeClock | None = None) -> None:
        self.clock = clock
        self.calls: list[dict] = []

    def cb_basic(self, *, fields: str) -> pd.DataFrame:
        self.calls.append(
            {
                "api": "cb_basic",
                "fields": fields,
                "entered_at": None if self.clock is None else self.clock.value,
            }
        )
        return pd.DataFrame(
            [
                {
                    "ts_code": "110001.SH",
                    "cb_type": "CB",
                    "stk_code": "600000.SH",
                    "list_date": "20180101",
                    "delist_date": None,
                    "exchange": "SSE",
                }
            ],
            columns=(
                "ts_code",
                "cb_type",
                "stk_code",
                "list_date",
                "delist_date",
                "exchange",
            ),
        )

    def cb_daily(self, *, trade_date: str, fields: str) -> pd.DataFrame:
        self.calls.append(
            {
                "api": "cb_daily",
                "trade_date": trade_date,
                "fields": fields,
                "entered_at": None if self.clock is None else self.clock.value,
            }
        )
        return pd.DataFrame(
            [
                {
                    "ts_code": "110001.SH",
                    "trade_date": trade_date,
                    "amount": 1000.0,
                    "cb_over_rate": 25.0,
                }
            ],
            columns=("ts_code", "trade_date", "amount", "cb_over_rate"),
        )


def prepare_synthetic_bindings(module, tmp_path, monkeypatch, call_count=3) -> None:
    for name in (
        "IMPLEMENTATION_FREEZE_PATH",
        "RUN_AUTHORIZATION_POLICY_PATH",
        "PLAN_RESULT_PATH",
    ):
        target = tmp_path / f"{name.lower()}.json"
        target.write_text('{"synthetic":true}\n', encoding="utf-8")
        target.chmod(0o600)
        monkeypatch.setattr(module, name, target)
    monkeypatch.setattr(module, "WORKFLOW_TEST_PATH", Path(__file__).resolve())
    monkeypatch.setattr(module.PLANNER, "EXACT_PROVIDER_CALL_COUNT", call_count)


def read_json_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_plan_is_ready_and_does_not_inspect_credential_or_provider(
    monkeypatch,
) -> None:
    module = load_module()

    def forbidden_credential_loader(*args, **kwargs):
        raise AssertionError("plan inspected credential")

    def forbidden_provider_factory(*args, **kwargs):
        raise AssertionError("plan created provider")

    monkeypatch.setattr(module, "_safe_dotenv_token", forbidden_credential_loader)
    monkeypatch.setattr(module, "_default_provider_factory", forbidden_provider_factory)
    plan = module.build_plan()
    assert plan["ready"] is True
    assert plan["blockers"] == []
    assert plan["accepted_trade_date_count"] == 1699
    assert plan["exact_provider_call_count"] == 1700
    assert plan["future_run_authorized"] is False
    assert plan["run_interface_exposed"] is False
    assert plan["credential_file_or_environment_inspected"] is False
    assert plan["provider_client_imported_or_created"] is False
    assert plan["provider_request_issued"] is False
    assert plan["filesystem_write_performed"] is False


def test_cli_plan_is_one_json_zero_write_and_run_is_not_exposed() -> None:
    module = load_module()
    paths = module.AttemptPaths.from_root(REPO_ROOT)
    watched = (
        paths.staging_root,
        paths.final_root,
        paths.intent,
        paths.journal,
        paths.terminal_failure,
        paths.repository_manifest,
    )
    before = [path.exists() for path in watched]
    plan_result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "plan"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert plan_result.returncode == 0
    assert plan_result.stderr == ""
    assert json.loads(plan_result.stdout)["ready"] is True
    assert [path.exists() for path in watched] == before

    run_result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "run", "--confirm-run"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 2
    assert "invalid choice" in run_result.stderr
    assert [path.exists() for path in watched] == before


def test_synthetic_success_persists_intent_before_token_and_exact_checkpoints(
    tmp_path, monkeypatch
) -> None:
    module = load_module()
    prepare_synthetic_bindings(module, tmp_path, monkeypatch)
    dates = ("2019-01-02", "2019-01-03")
    clock = FakeClock()
    provider = SyntheticProvider(clock)
    paths = module.AttemptPaths.from_root(tmp_path)
    secret = "SYNTHETIC_SECRET_MUST_NOT_PERSIST"

    def token_loader() -> str:
        assert paths.intent.is_file()
        assert paths.journal.is_file()
        assert paths.intent.stat().st_mode & 0o777 == 0o600
        header = read_json_lines(paths.journal)
        assert [event["status"] for event in header] == ["attempt_created"]
        return secret

    def provider_factory(token: str):
        assert token == secret
        assert paths.intent.is_file() and paths.journal.is_file()
        return provider

    result = module.execute_authorized_workflow(
        confirm_run=True,
        token_loader=token_loader,
        provider_factory=provider_factory,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        repo_root=tmp_path,
        accepted_dates=dates,
        require_v420_authorization=False,
    )
    assert result == 0
    assert [call["api"] for call in provider.calls] == [
        "cb_basic",
        "cb_daily",
        "cb_daily",
    ]
    assert [call.get("trade_date") for call in provider.calls[1:]] == [
        "20190102",
        "20190103",
    ]
    assert all(
        later["entered_at"] - earlier["entered_at"] >= 1.05
        for earlier, later in zip(provider.calls, provider.calls[1:])
    )
    assert len(clock.sleeps) == 2
    assert paths.final_root.is_dir()
    assert not paths.staging_root.exists()
    assert paths.repository_manifest.is_file()
    manifest = json.loads(paths.repository_manifest.read_text(encoding="utf-8"))
    assert manifest["committed_request_count"] == 3
    assert manifest["candidate_or_comparator_value_read"] is False
    events = read_json_lines(paths.journal)
    assert [event["status"] for event in events] == [
        "attempt_created",
        "request_authorized",
        "response_received",
        "checkpoint_committed",
        "request_authorized",
        "response_received",
        "checkpoint_committed",
        "request_authorized",
        "response_received",
        "checkpoint_committed",
        "success_committed",
    ]
    persisted = b"".join(
        path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()
    )
    assert secret.encode("utf-8") not in persisted


def test_exact_committed_prefix_resumes_without_reissuing_checkpoint(
    tmp_path, monkeypatch
) -> None:
    module = load_module()
    prepare_synthetic_bindings(module, tmp_path, monkeypatch)
    dates = ("2019-01-02", "2019-01-03")
    first_clock = FakeClock()
    first_provider = SyntheticProvider(first_clock)

    def stop_before_second_authorization(seconds: float) -> None:
        raise SyntheticStop

    with pytest.raises(SyntheticStop):
        module.execute_authorized_workflow(
            confirm_run=True,
            token_loader=lambda: "secret",
            provider_factory=lambda token: first_provider,
            monotonic=first_clock.monotonic,
            sleep=stop_before_second_authorization,
            repo_root=tmp_path,
            accepted_dates=dates,
            require_v420_authorization=False,
        )
    assert [call["api"] for call in first_provider.calls] == ["cb_basic"]
    paths = module.AttemptPaths.from_root(tmp_path)
    assert not paths.terminal_failure.exists()

    second_clock = FakeClock()
    second_provider = SyntheticProvider(second_clock)
    result = module.execute_authorized_workflow(
        confirm_run=True,
        token_loader=lambda: "secret",
        provider_factory=lambda token: second_provider,
        monotonic=second_clock.monotonic,
        sleep=second_clock.sleep,
        repo_root=tmp_path,
        accepted_dates=dates,
        require_v420_authorization=False,
    )
    assert result == 0
    assert [call["api"] for call in second_provider.calls] == [
        "cb_daily",
        "cb_daily",
    ]
    assert paths.repository_manifest.is_file()


def test_authorized_request_without_checkpoint_terminalizes_without_retry(
    tmp_path, monkeypatch
) -> None:
    module = load_module()
    prepare_synthetic_bindings(module, tmp_path, monkeypatch)
    dates = ("2019-01-02", "2019-01-03")

    class StopAfterProviderEntry(SyntheticProvider):
        def cb_basic(self, *, fields: str) -> pd.DataFrame:
            self.calls.append({"api": "cb_basic", "fields": fields})
            raise SyntheticStop

    provider = StopAfterProviderEntry()
    with pytest.raises(SyntheticStop):
        module.execute_authorized_workflow(
            confirm_run=True,
            token_loader=lambda: "secret",
            provider_factory=lambda token: provider,
            repo_root=tmp_path,
            accepted_dates=dates,
            require_v420_authorization=False,
        )
    assert len(provider.calls) == 1

    retry_provider = SyntheticProvider()
    result = module.execute_authorized_workflow(
        confirm_run=True,
        token_loader=lambda: "secret",
        provider_factory=lambda token: retry_provider,
        repo_root=tmp_path,
        accepted_dates=dates,
        require_v420_authorization=False,
    )
    paths = module.AttemptPaths.from_root(tmp_path)
    assert result == 1
    assert retry_provider.calls == []
    assert (
        json.loads(paths.terminal_failure.read_text(encoding="utf-8"))["stage_code"]
        == "existing_attempt_evidence_invalid_or_inflight"
    )


@pytest.mark.parametrize("failure_kind", ["empty", "truncated", "schema"])
def test_response_gates_terminalize_once_without_plaintext_or_raw_values(
    tmp_path, monkeypatch, failure_kind
) -> None:
    module = load_module()
    prepare_synthetic_bindings(module, tmp_path, monkeypatch, call_count=2)
    dates = ("2019-01-02",)
    secret = "NEVER_PERSIST_THIS_SECRET"

    class FailingProvider(SyntheticProvider):
        def cb_basic(self, *, fields: str) -> pd.DataFrame:
            self.calls.append({"api": "cb_basic", "fields": fields})
            if failure_kind == "empty":
                return pd.DataFrame(columns=module.ADAPTER.CB_BASIC_FIELDS)
            if failure_kind == "truncated":
                return pd.DataFrame(
                    [["RAW_VALUE"] * 6] * 2000,
                    columns=module.ADAPTER.CB_BASIC_FIELDS,
                )
            return pd.DataFrame([{"forbidden": "RAW_VALUE"}])

    provider = FailingProvider()
    result = module.execute_authorized_workflow(
        confirm_run=True,
        token_loader=lambda: secret,
        provider_factory=lambda token: provider,
        repo_root=tmp_path,
        accepted_dates=dates,
        require_v420_authorization=False,
    )
    paths = module.AttemptPaths.from_root(tmp_path)
    assert result == 1
    assert len(provider.calls) == 1
    failure = paths.terminal_failure.read_text(encoding="utf-8")
    assert secret not in failure
    assert "RAW_VALUE" not in failure
    assert "2000" not in failure
    assert 'provider_response_row_count_persisted": false' in failure

    with pytest.raises(module.Campaign265WorkflowError):
        module.execute_authorized_workflow(
            confirm_run=True,
            token_loader=lambda: secret,
            provider_factory=lambda token: SyntheticProvider(),
            repo_root=tmp_path,
            accepted_dates=dates,
            require_v420_authorization=False,
        )


def test_persistence_failure_after_response_is_terminal_no_retry(
    tmp_path, monkeypatch
) -> None:
    module = load_module()
    prepare_synthetic_bindings(module, tmp_path, monkeypatch, call_count=2)
    dates = ("2019-01-02",)
    provider = SyntheticProvider()

    def fail_commit(*args, **kwargs):
        raise OSError("synthetic persistence failure with private detail")

    monkeypatch.setattr(module, "_commit_checkpoint", fail_commit)
    result = module.execute_authorized_workflow(
        confirm_run=True,
        token_loader=lambda: "secret",
        provider_factory=lambda token: provider,
        repo_root=tmp_path,
        accepted_dates=dates,
        require_v420_authorization=False,
    )
    paths = module.AttemptPaths.from_root(tmp_path)
    assert result == 1
    events = read_json_lines(paths.journal)
    assert [event["status"] for event in events] == [
        "attempt_created",
        "request_authorized",
        "response_received",
    ]
    failure = paths.terminal_failure.read_text(encoding="utf-8")
    assert "private detail" not in failure
    assert "request_response_schema_or_persistence_failed" in failure


def test_tampered_committed_sidecar_fails_closed_before_provider(
    tmp_path, monkeypatch
) -> None:
    module = load_module()
    prepare_synthetic_bindings(module, tmp_path, monkeypatch)
    dates = ("2019-01-02", "2019-01-03")
    clock = FakeClock()
    provider = SyntheticProvider(clock)

    def stop_before_second_authorization(seconds: float) -> None:
        raise SyntheticStop

    with pytest.raises(SyntheticStop):
        module.execute_authorized_workflow(
            confirm_run=True,
            token_loader=lambda: "secret",
            provider_factory=lambda token: provider,
            monotonic=clock.monotonic,
            sleep=stop_before_second_authorization,
            repo_root=tmp_path,
            accepted_dates=dates,
            require_v420_authorization=False,
        )
    paths = module.AttemptPaths.from_root(tmp_path)
    sidecar_path = paths.staging_root / "cb_basic.parquet.meta.json"
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    sidecar["checkpoint_sha256"] = "0" * 64
    sidecar_path.write_text(json.dumps(sidecar) + "\n", encoding="utf-8")
    sidecar_path.chmod(0o600)

    retry_provider = SyntheticProvider()
    result = module.execute_authorized_workflow(
        confirm_run=True,
        token_loader=lambda: "secret",
        provider_factory=lambda token: retry_provider,
        repo_root=tmp_path,
        accepted_dates=dates,
        require_v420_authorization=False,
    )
    assert result == 1
    assert retry_provider.calls == []
    assert paths.terminal_failure.is_file()


def test_confirmation_and_future_v420_authorization_fail_closed() -> None:
    module = load_module()
    with pytest.raises(module.Campaign265WorkflowError, match="explicit_confirm"):
        module.execute_authorized_workflow(confirm_run=False)
    with pytest.raises(module.Campaign265WorkflowError, match="v420"):
        module.execute_authorized_workflow(confirm_run=True)


def test_destination_parent_symlink_fails_before_credential_or_provider(
    tmp_path, monkeypatch
) -> None:
    module = load_module()
    prepare_synthetic_bindings(module, tmp_path, monkeypatch, call_count=2)
    outside = tmp_path / "outside"
    outside.mkdir()
    parent = tmp_path / "data/raw/a_share/rich/tushare"
    parent.mkdir(parents=True)
    (parent / "convertible_premium").symlink_to(outside, target_is_directory=True)
    credential_loaded = False

    def token_loader() -> str:
        nonlocal credential_loaded
        credential_loaded = True
        return "secret"

    with pytest.raises(
        module.Campaign265WorkflowError,
        match="destination_parent_not_real_directory",
    ):
        module.execute_authorized_workflow(
            confirm_run=True,
            token_loader=token_loader,
            provider_factory=lambda token: SyntheticProvider(),
            repo_root=tmp_path,
            accepted_dates=("2019-01-02",),
            require_v420_authorization=False,
        )
    assert credential_loaded is False
    assert list(outside.iterdir()) == []


def test_protocol_freezes_no_retry_and_current_plan_only_boundary() -> None:
    protocol = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_265_source_acceptance_execution_protocol_20260824.json"
        ).read_text(encoding="utf-8")
    )
    state_machine = protocol["durable_state_machine"]
    boundary = protocol["workflow_cli_and_authorization_boundary"]
    assert (
        state_machine[
            "intent_and_journal_created_exclusively_mode_0600_and_fsynced_before_credential_load"
        ]
        is True
    )
    assert (
        state_machine[
            "authorized_request_without_matching_committed_checkpoint_is_terminal_no_retry_evidence"
        ]
        is True
    )
    assert boundary["current_cli_commands"] == ["plan"]
    assert boundary["real_run_policy_required"] == 420
    assert boundary["explicit_confirm_run_required_under_v420"] is True
