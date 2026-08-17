"""Offline tests for the fail-closed Candidate49 future-session workflow."""

from __future__ import annotations

import datetime as dt
import json
import os
import stat
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import Mapping, Sequence

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_tushare_candidate49_future_session_workflow as workflow  # noqa: E402
import a_share_tushare_intraday_cumulative_vwap_crossing_rate as candidate  # noqa: E402


SESSION = dt.date(2026, 7, 27)
AFTER_CLOSE = dt.datetime(2026, 7, 27, 17, 0, tzinfo=workflow.CHINA_TZ)
NEXT_DAY = dt.datetime(2026, 7, 28, 17, 0, tzinfo=workflow.CHINA_TZ)


def _json_out(value: Mapping) -> str:
    return json.dumps(value, ensure_ascii=False)


class FakeWorkflowExecutor:
    def __init__(
        self,
        tmp_path: Path,
        *,
        active_source: str = "baostock",
        active_calendar_end: str = "2026-07-13",
        fail_step: str | None = None,
        extra_probe_failure: str | None = None,
    ) -> None:
        self.active_root = tmp_path / "active"
        self.active_root.mkdir()
        self.staging_root = tmp_path / "daily-staging"
        self.minute_root = tmp_path / "minute-root"
        self.minute_root.mkdir()
        self.reference_manifest = tmp_path / "tushare-daily-reference.json"
        self.reference_manifest.write_text(
            '{"provider":"tushare","range":"2019-2025"}\n',
            encoding="utf-8",
        )
        self.reference_sha256 = workflow.file_digest(self.reference_manifest)
        self.signal_ledger = tmp_path / "signal-ledger.json"
        self.execution_ledger = tmp_path / "execution-ledger.json"
        candidate.initialize_future_ledgers(
            signal_path=self.signal_ledger,
            execution_path=self.execution_ledger,
        )
        self.active_source = active_source
        self.active_calendar_end = active_calendar_end
        self.fail_step = fail_step
        self.extra_probe_failure = extra_probe_failure
        self.calls: list[dict] = []
        self.source_ready = False
        self.seed_ready = False
        self.acceptance_ready = False
        self.activated = False
        self.quality_ready = False
        self.migration_latest_failure: dict | None = None
        self.reference_daily_requests = 0
        self.candidate_provider_calls_this_invocation = 50
        self.candidate_eligible_names = 50

    def _candidate_artifact_summary(
        self,
        config: workflow.WorkflowConfig,
    ) -> dict:
        raw_manifest = self.minute_root / "raw-manifest.json"
        factor_manifest = self.minute_root / "factor-manifest.json"
        ledger = candidate.validate_future_ledger(
            self.signal_ledger,
            candidate.FUTURE_SIGNAL_LEDGER_KIND,
        )
        matching = [
            entry
            for entry in ledger["entries"]
            if entry["session_date"] == config.session.isoformat()
        ]
        return {
            "active_data_root": str(self.staging_root),
            "raw_manifest_path": str(raw_manifest),
            "raw_manifest_sha256": workflow.file_digest(raw_manifest),
            "factor_manifest_path": str(factor_manifest),
            "factor_manifest_sha256": workflow.file_digest(factor_manifest),
            "eligible_names": self.candidate_eligible_names,
            "signal_entry_sha256": (
                None if not matching else matching[0]["entry_sha256"]
            ),
            "raw_provider_calls": 50,
        }

    def _outcome(
        self,
        value: Mapping | None = None,
        *,
        returncode: int = 0,
        stdout: str | None = None,
        stderr: str = "",
    ) -> workflow.CommandOutcome:
        return workflow.CommandOutcome(
            returncode=returncode,
            stdout=stdout if stdout is not None else _json_out(value or {}),
            stderr=stderr,
        )

    def _pipeline_status(self) -> dict:
        if self.activated:
            root = self.staging_root
            source = "tushare"
            calendar_end = SESSION.isoformat()
        else:
            root = self.active_root
            source = self.active_source
            calendar_end = self.active_calendar_end
        return {
            "data_root": str(root),
            "qlib_calendar_end": calendar_end,
            "price_basis": {
                "status": "passed",
                "daily_sources": [source],
                "failures": {},
            },
        }

    def _migration_status(self) -> dict:
        return {
            "kind": "a_share_tushare_daily_provider_migration_status",
            "staging_root": str(self.staging_root),
            "active_data_root": str(
                self.staging_root if self.activated else self.active_root
            ),
            "reference_manifest_valid": True,
            "reference_manifest_sha256": self.reference_sha256,
            "reference_snapshot": {
                "path": str(self.reference_manifest),
                "sha256": self.reference_sha256,
                "provider": "tushare",
                "requested_start": workflow.DAILY_REFERENCE_START,
                "requested_end": workflow.DAILY_REFERENCE_END,
                "rows": workflow.DAILY_REFERENCE_ROWS,
                "annual_partitions": 7,
                "sessions": 1699,
                "valid": True,
            },
            "reference_error": None,
            "refresh_seed_intent": (
                {"status": "prepared"} if self.seed_ready else None
            ),
            "refresh_seed": (
                {"status": "source_checkpoints_seeded"} if self.seed_ready else None
            ),
            "source_snapshot": (
                {"through_date": SESSION.isoformat()} if self.source_ready else None
            ),
            "canonical_build": (
                {"status": "completed"} if self.acceptance_ready else None
            ),
            "acceptance": (
                {
                    "status": (
                        "accepted_staging_pending_explicit_crash_safe_activation"
                    ),
                    "through_date": SESSION.isoformat(),
                    "daily_source": "tushare",
                    "protocol_sha256": workflow.DAILY_MIGRATION_PROTOCOL_SHA256,
                }
                if self.acceptance_ready
                else None
            ),
            "activation": None,
            "latest_failure": self.migration_latest_failure,
            "provider_request_issued": False,
        }

    def _source_manifest_path(self) -> Path:
        return (
            self.staging_root
            / "raw"
            / "a_share"
            / "rich"
            / "tushare"
            / "daily_provider_migration_v1"
            / "source_manifest.json"
        )

    def _write_source_manifest(self) -> None:
        path = self._source_manifest_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "kind": (
                        "a_share_tushare_daily_provider_migration_source_snapshot"
                    ),
                    "status": (
                        "complete_pending_canonical_build_and_acceptance"
                    ),
                    "protocol_sha256": (
                        workflow.DAILY_MIGRATION_PROTOCOL_SHA256
                    ),
                    "through_date": SESSION.isoformat(),
                    "accepted_reference_manifest_path": str(
                        self.reference_manifest
                    ),
                    "accepted_reference_manifest_sha256": (
                        self.reference_sha256
                    ),
                    "accepted_reference_rows": workflow.DAILY_REFERENCE_ROWS,
                    "reference_daily_sessions_reused": 1699,
                    "reference_daily_sessions_requested_this_invocation": (
                        self.reference_daily_requests
                    ),
                    "requested_daily_sessions_this_invocation": 1200,
                    "requested_daily_basic_sessions_this_invocation": 2800,
                    "provider_calls_this_invocation": 4004,
                    "active_root_mutated": False,
                    "forward_return_fields_read": False,
                    "factor_values_read": False,
                }
            ),
            encoding="utf-8",
        )

    def _write_acceptance(self) -> None:
        metadata = self.staging_root / "metadata"
        metadata.mkdir(parents=True, exist_ok=True)
        source_manifest = self._source_manifest_path()
        (metadata / "tushare_daily_provider_acceptance.json").write_text(
            json.dumps(
                {
                    "status": (
                        "accepted_staging_pending_explicit_crash_safe_activation"
                    ),
                    "protocol_sha256": workflow.DAILY_MIGRATION_PROTOCOL_SHA256,
                    "through_date": SESSION.isoformat(),
                    "daily_source": "tushare",
                    "source_manifest_path": str(source_manifest),
                    "source_manifest_sha256": workflow.file_digest(
                        source_manifest
                    ),
                }
            ),
            encoding="utf-8",
        )

    def _write_activation(self) -> None:
        metadata = self.staging_root / "metadata"
        metadata.mkdir(parents=True, exist_ok=True)
        acceptance = metadata / "tushare_daily_provider_acceptance.json"
        (metadata / "tushare_daily_activation.json").write_text(
            json.dumps(
                {
                    "status": "active_via_atomic_repository_pointer",
                    "protocol_sha256": workflow.DAILY_MIGRATION_PROTOCOL_SHA256,
                    "staging_root": str(self.staging_root),
                    "acceptance_manifest_path": str(acceptance),
                    "acceptance_manifest_sha256": workflow.file_digest(
                        acceptance
                    ),
                }
            ),
            encoding="utf-8",
        )

    def _quality_paths(self) -> tuple[Path, Path]:
        return (
            self.staging_root
            / "raw"
            / "a_share"
            / "fundamentals"
            / "quarterly_quality_future.parquet",
            self.staging_root
            / "metadata"
            / "quarterly_quality_future_manifest.json",
        )

    def _write_quality(self) -> None:
        quality_path, quality_manifest = self._quality_paths()
        quality_path.parent.mkdir(parents=True, exist_ok=True)
        quality_manifest.parent.mkdir(parents=True, exist_ok=True)
        quality_path.write_bytes(b"future-quality")
        quality_manifest.write_text(
            '{"status":"completed"}\n',
            encoding="utf-8",
        )

    def _preflight(self, ready: bool) -> dict:
        quality_path, quality_manifest = self._quality_paths()
        failures = [] if ready else ["future_quarterly_quality_not_accepted"]
        if not ready and self.extra_probe_failure:
            failures.append(self.extra_probe_failure)
        return {
            "status": (
                "ready_for_explicit_future_source_to_signal_collection"
                if ready
                else "not_ready_no_provider_request"
            ),
            "ready": ready,
            "recommended_cli_exit_code": 0 if ready else 2,
            "failures": failures,
            "future_quarterly_quality_ready": ready,
            "future_quarterly_quality_path": str(quality_path),
            "future_quarterly_quality_sha256": (
                workflow.file_digest(quality_path) if ready else None
            ),
            "future_quarterly_quality_manifest_path": str(quality_manifest),
            "future_quarterly_quality_manifest_sha256": (
                workflow.file_digest(quality_manifest) if ready else None
            ),
            "provider_request_issued": False,
            "minute_rows_read": False,
            "signal_or_execution_entry_written": False,
            "filesystem_write_performed": False,
        }

    def __call__(
        self,
        step: str,
        argv: Sequence[str],
        environment: Mapping[str, str],
    ) -> workflow.CommandOutcome:
        self.calls.append(
            {
                "step": step,
                "argv": list(argv),
                "token_present": bool(environment.get(workflow.TOKEN_ENV)),
                "data_root_override_present": bool(
                    environment.get(workflow.DATA_ROOT_ENV)
                ),
            }
        )
        if step == self.fail_step:
            return self._outcome(
                returncode=1,
                stderr="synthetic child failure",
            )
        if step in {"active-daily-status", "post-activation-daily-status"}:
            return self._outcome(self._pipeline_status())
        if step == "daily-migration-status":
            return self._outcome(self._migration_status())
        if step == "daily-seed-refresh":
            self.seed_ready = True
            return self._outcome(
                {
                    "status": "source_checkpoints_seeded_pending_incremental_sync",
                    "provider_request_issued": False,
                    "hardlinks_used": False,
                    "active_root_mutated": False,
                }
            )
        if step == "daily-migration-preflight":
            return self._outcome(
                {
                    "status": "ready_for_explicit_tushare_source_sync",
                    "ready": True,
                    "recommended_cli_exit_code": 0,
                    "provider_request_issued": False,
                    "filesystem_write_performed": False,
                }
            )
        if step == "daily-source-sync":
            self.source_ready = True
            self._write_source_manifest()
            return self._outcome(
                {
                    "status": "source_snapshot_complete",
                    "active_root_mutated": False,
                }
            )
        if step == "daily-build-and-accept":
            self.acceptance_ready = True
            self._write_acceptance()
            return self._outcome(
                {
                    "status": (
                        "accepted_staging_pending_explicit_crash_safe_activation"
                    ),
                    "active_root_mutated": False,
                }
            )
        if step == "daily-activation-preflight":
            return self._outcome(
                {
                    "status": "ready_for_explicit_atomic_pointer_activation",
                    "ready": True,
                    "recommended_cli_exit_code": 0,
                    "accepted_through_date": SESSION.isoformat(),
                    "environment_override_present": False,
                    "provider_request_issued": False,
                }
            )
        if step == "daily-atomic-activation":
            self.activated = True
            self._write_activation()
            return self._outcome(
                {
                    "status": "active_via_atomic_repository_pointer",
                    "active_data_root": str(self.staging_root),
                    "old_daily_or_qlib_file_mutated": False,
                }
            )
        if step == "post-activation-price-basis-audit":
            return self._outcome(
                {
                    "status": "passed",
                    "daily_sources": ["tushare"],
                    "failures": {},
                }
            )
        if step == "resolve-active-data-root":
            return self._outcome(stdout=str(self.staging_root) + "\n")
        if step == "candidate49-quality-readiness-probe":
            ready = self.quality_ready
            return self._outcome(
                self._preflight(ready),
                returncode=0 if ready else 2,
            )
        if step == "future-quarterly-quality-refresh":
            self._write_quality()
            quality_path, _ = self._quality_paths()
            self.quality_ready = True
            return self._outcome(
                {
                    "status": "completed",
                    "report_frequency": "quarterly",
                    "through_report_date": "2026-06-30",
                    "latest_completed_quarter_end_at_sync": "2026-06-30",
                    "output": str(quality_path),
                }
            )
        if step == "candidate49-final-combined-preflight":
            return self._outcome(self._preflight(True))
        if step == "candidate49-source-to-signal-collection":
            raw_manifest = self.minute_root / "raw-manifest.json"
            factor_manifest = self.minute_root / "factor-manifest.json"
            raw_manifest.write_text('{"status":"completed"}\n', encoding="utf-8")
            factor_manifest.write_text(
                '{"status":"completed"}\n',
                encoding="utf-8",
            )
            signal_ledger = candidate.validate_future_ledger(
                self.signal_ledger,
                candidate.FUTURE_SIGNAL_LEDGER_KIND,
            )
            matching = [
                entry
                for entry in signal_ledger["entries"]
                if entry["session_date"] == SESSION.isoformat()
            ]
            if self.candidate_eligible_names < 50:
                signal_entry = None
                status = (
                    "future_session_frozen_without_signal_fewer_than_50_names"
                )
            elif matching:
                signal_entry = matching[0]
                status = "future_signal_already_present_idempotent"
            else:
                signal_entry = candidate.append_future_ledger_entry(
                    path=self.signal_ledger,
                    kind=candidate.FUTURE_SIGNAL_LEDGER_KIND,
                    payload={
                        "entry_id": (
                            f"{candidate.FUTURE_REGISTRATION_ID}:"
                            f"signal:{SESSION.isoformat()}"
                        ),
                        "session_date": SESSION.isoformat(),
                    },
                )
                status = "future_signal_appended"
            return self._outcome(
                {
                    "status": status,
                    "session_date": SESSION.isoformat(),
                    "raw_manifest": str(raw_manifest),
                    "raw_manifest_sha256": workflow.file_digest(raw_manifest),
                    "factor_manifest": str(factor_manifest),
                    "factor_manifest_sha256": workflow.file_digest(factor_manifest),
                    "eligible_names": self.candidate_eligible_names,
                    "signal_entry_sha256": (
                        None
                        if signal_entry is None
                        else signal_entry["entry_sha256"]
                    ),
                    "provider_calls_this_invocation": (
                        self.candidate_provider_calls_this_invocation
                    ),
                    "forward_return_fields_read": False,
                    "execution_or_order_performed": False,
                    "historical_backfill_allowed": False,
                }
            )
        raise AssertionError(f"unexpected workflow step: {step}")


def _patch_fake_semantics(
    monkeypatch,
    value: FakeWorkflowExecutor,
) -> None:
    monkeypatch.setattr(
        workflow,
        "_candidate49_artifact_summary",
        value._candidate_artifact_summary,
    )
    monkeypatch.setattr(
        workflow,
        "_validate_candidate49_ledgers_semantically",
        lambda: None,
    )


@pytest.fixture
def fake(tmp_path, monkeypatch) -> FakeWorkflowExecutor:
    value = FakeWorkflowExecutor(tmp_path)
    monkeypatch.setattr(workflow, "FIXED_MINUTE_DATA_ROOT", value.minute_root)
    monkeypatch.setattr(workflow, "SIGNAL_LEDGER_PATH", value.signal_ledger)
    monkeypatch.setattr(
        workflow,
        "EXECUTION_LEDGER_PATH",
        value.execution_ledger,
    )
    _patch_fake_semantics(monkeypatch, value)
    return value


def _config(value: FakeWorkflowExecutor) -> workflow.WorkflowConfig:
    return workflow.WorkflowConfig(
        session=SESSION,
        staging_root=value.staging_root,
        minute_data_root=value.minute_root,
    )


def _run(value: FakeWorkflowExecutor, **kwargs) -> dict:
    return workflow.run_workflow(
        _config(value),
        confirm_run=True,
        executor=value,
        token_loader=lambda: "secret-token",
        now=AFTER_CLOSE,
        lock_factory=lambda path: nullcontext(),
        reference_manifest_path=value.reference_manifest,
        reference_manifest_sha256=value.reference_sha256,
        **kwargs,
    )


def test_load_token_reads_repository_dotenv_without_shell_evaluation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "# local credential\n"
        "UNRELATED=$(touch should-not-exist)\n"
        'TUSHARE_TOKEN="dotenv-secret-token"\n',
        encoding="utf-8",
    )
    monkeypatch.delenv(workflow.TOKEN_ENV, raising=False)

    assert workflow._load_token(dotenv_path) == "dotenv-secret-token"
    assert not (tmp_path / "should-not-exist").exists()


def test_load_token_prefers_process_environment_over_repository_dotenv(
    tmp_path: Path,
    monkeypatch,
) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "TUSHARE_TOKEN=dotenv-secret-token\n",
        encoding="utf-8",
    )
    monkeypatch.setenv(workflow.TOKEN_ENV, "process-secret-token")

    assert workflow._load_token(dotenv_path) == "process-secret-token"


def test_repository_dotenv_rejects_duplicate_token_declarations(
    tmp_path: Path,
) -> None:
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "TUSHARE_TOKEN=first-secret-token\n"
        "TUSHARE_TOKEN=second-secret-token\n",
        encoding="utf-8",
    )

    with pytest.raises(
        workflow.Candidate49FutureSessionWorkflowError,
        match="declares TUSHARE_TOKEN more than once",
    ):
        workflow._parse_dotenv_token(dotenv_path)


def test_plan_is_zero_write_and_reports_expected_weekend_blocker(
    fake: FakeWorkflowExecutor,
) -> None:
    before = sorted(path.relative_to(fake.minute_root) for path in fake.minute_root.rglob("*"))
    result = workflow.inspect_plan(
        _config(fake),
        executor=fake,
        token_loader=lambda: None,
        now=dt.datetime(2026, 7, 26, 17, 0, tzinfo=workflow.CHINA_TZ),
        reference_manifest_path=fake.reference_manifest,
        reference_manifest_sha256=fake.reference_sha256,
    )
    after = sorted(path.relative_to(fake.minute_root) for path in fake.minute_root.rglob("*"))

    assert result["ready"] is False
    assert result["recommended_cli_exit_code"] == 2
    assert result["failures"] == [
        "signal_session_has_not_arrived",
        "TUSHARE_TOKEN_not_available_to_workflow",
    ]
    assert result["existing_tushare_daily_reference"] == {
        "path": str(fake.reference_manifest),
        "sha256": fake.reference_sha256,
        "requested_start": workflow.DAILY_REFERENCE_START,
        "requested_end": workflow.DAILY_REFERENCE_END,
        "rows": workflow.DAILY_REFERENCE_ROWS,
        "annual_partitions": 7,
        "sessions": 1699,
        "valid": True,
        "covered_daily_sessions_will_be_requested_again": False,
    }
    assert result["provider_request_issued"] is False
    assert result["filesystem_write_performed"] is False
    assert before == after


def test_plan_rejects_same_session_stock_basic_failure_without_provider_retry(
    fake: FakeWorkflowExecutor,
) -> None:
    fake.migration_latest_failure = {
        "status": "failed_preserving_active_root_and_completed_checkpoints",
        "through_date": SESSION.isoformat(),
        "failure_stage": "stock_basic",
    }

    result = workflow.inspect_plan(
        _config(fake),
        executor=fake,
        token_loader=lambda: "secret-token",
        now=AFTER_CLOSE,
        reference_manifest_path=fake.reference_manifest,
        reference_manifest_sha256=fake.reference_sha256,
    )

    assert result["ready"] is False
    assert result["recommended_cli_exit_code"] == 2
    assert result["failures"] == [
        "daily_migration_stock_basic_failure_for_session_forbids_provider_retry"
    ]
    assert result["provider_request_issued"] is False
    assert result["filesystem_write_performed"] is False


def test_run_rejects_same_session_stock_basic_failure_before_provider_child(
    fake: FakeWorkflowExecutor,
) -> None:
    fake.migration_latest_failure = {
        "status": "failed_preserving_active_root_and_completed_checkpoints",
        "through_date": SESSION.isoformat(),
        "failure_stage": "stock_basic",
    }

    with pytest.raises(
        workflow.Candidate49FutureSessionWorkflowError,
        match="provider continuation is forbidden",
    ):
        _run(fake)

    assert [call["step"] for call in fake.calls] == [
        "active-daily-status",
        "daily-migration-status",
    ]
    assert all(not call["token_present"] for call in fake.calls)


def test_run_stops_before_any_child_when_time_or_token_is_not_ready(
    fake: FakeWorkflowExecutor,
) -> None:
    with pytest.raises(
        workflow.Candidate49FutureSessionWorkflowError,
        match="signal_session_has_not_arrived",
    ):
        workflow.run_workflow(
            _config(fake),
            confirm_run=True,
            executor=fake,
            token_loader=lambda: "secret-token",
            now=dt.datetime(2026, 7, 26, 17, 0, tzinfo=workflow.CHINA_TZ),
            lock_factory=lambda path: nullcontext(),
        )
    assert fake.calls == []

    with pytest.raises(
        workflow.Candidate49FutureSessionWorkflowError,
        match="TUSHARE_TOKEN is unavailable",
    ):
        workflow.run_workflow(
            _config(fake),
            confirm_run=True,
            executor=fake,
            token_loader=lambda: None,
            now=AFTER_CLOSE,
            lock_factory=lambda path: nullcontext(),
        )
    assert fake.calls == []


def test_initial_workflow_runs_in_order_and_scopes_token_to_required_children(
    fake: FakeWorkflowExecutor,
) -> None:
    result = _run(fake)
    names = [call["step"] for call in fake.calls]

    assert names == [
        "active-daily-status",
        "daily-migration-status",
        "daily-migration-preflight",
        "daily-source-sync",
        "daily-migration-status",
        "daily-build-and-accept",
        "daily-migration-status",
        "daily-activation-preflight",
        "daily-atomic-activation",
        "post-activation-daily-status",
        "post-activation-price-basis-audit",
        "resolve-active-data-root",
        "candidate49-quality-readiness-probe",
        "future-quarterly-quality-refresh",
        "candidate49-final-combined-preflight",
        "candidate49-source-to-signal-collection",
    ]
    token_steps = {
        call["step"] for call in fake.calls if call["token_present"]
    }
    assert token_steps == {
        "daily-migration-preflight",
        "daily-source-sync",
        "candidate49-quality-readiness-probe",
        "candidate49-final-combined-preflight",
        "candidate49-source-to-signal-collection",
    }
    assert all(not call["data_root_override_present"] for call in fake.calls)
    assert result["status"] == workflow.FINAL_RECORD_STATUS
    assert result["candidate49_status"] == "future_signal_appended"
    record_path = Path(result["record_path"])
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["daily_reference_reuse"] == {
        "accepted_reference_range": [
            workflow.DAILY_REFERENCE_START,
            workflow.DAILY_REFERENCE_END,
        ],
        "accepted_reference_rows": workflow.DAILY_REFERENCE_ROWS,
        "reference_daily_sessions_reused": 1699,
        "reference_daily_sessions_requested_this_invocation": 0,
        "requested_daily_sessions_this_invocation": 1200,
        "requested_daily_basic_sessions_this_invocation": 2800,
        "daily_provider_calls_this_invocation": 4004,
    }
    assert record["evidence"]["accepted_tushare_daily_reference"] == {
        "path": str(fake.reference_manifest),
        "sha256": fake.reference_sha256,
    }
    assert record["credential_value_logged_hashed_or_persisted"] is False
    assert record["forward_return_fields_read"] is False
    assert record["paper_execution_or_order_performed"] is False
    assert record["candidate49_raw_provider_calls_total"] == 50
    assert "candidate49_provider_calls_this_invocation" not in record
    assert "steps" not in record
    assert record["candidate49_outcome"] == "future_signal_present"
    assert record["phase_receipts"][-1] == {
        "ordinal": 4,
        "phase": "candidate49_source_to_signal",
        "status": "future_signal_present",
        "raw_manifest_sha256": workflow.file_digest(
            fake.minute_root / "raw-manifest.json"
        ),
        "factor_manifest_sha256": workflow.file_digest(
            fake.minute_root / "factor-manifest.json"
        ),
        "eligible_names": 50,
        "signal_entry_sha256": record[
            "candidate49_signal_entry_sha256"
        ],
        "raw_provider_calls_total": 50,
    }
    assert "secret-token" not in record_path.read_text(encoding="utf-8")


def test_completed_daily_source_resumes_at_build_without_provider_sync(
    fake: FakeWorkflowExecutor,
) -> None:
    fake.source_ready = True
    fake._write_source_manifest()

    _run(fake)
    names = [call["step"] for call in fake.calls]

    assert "daily-migration-preflight" not in names
    assert "daily-source-sync" not in names
    assert "daily-build-and-accept" in names
    assert "daily-atomic-activation" in names
    assert "candidate49-source-to-signal-collection" in names


def test_completed_incremental_source_reuses_seed_and_skips_provider_sync(
    tmp_path,
    monkeypatch,
) -> None:
    value = FakeWorkflowExecutor(
        tmp_path,
        active_source="tushare",
        active_calendar_end="2026-07-24",
    )
    monkeypatch.setattr(workflow, "FIXED_MINUTE_DATA_ROOT", value.minute_root)
    monkeypatch.setattr(workflow, "SIGNAL_LEDGER_PATH", value.signal_ledger)
    monkeypatch.setattr(
        workflow,
        "EXECUTION_LEDGER_PATH",
        value.execution_ledger,
    )
    _patch_fake_semantics(monkeypatch, value)
    value.source_ready = True
    value.seed_ready = True
    value._write_source_manifest()

    _run(value)
    names = [call["step"] for call in value.calls]

    assert "daily-seed-refresh" not in names
    assert "daily-migration-preflight" not in names
    assert "daily-source-sync" not in names
    assert "daily-build-and-accept" in names
    assert "candidate49-source-to-signal-collection" in names


def test_completed_daily_acceptance_resumes_at_activation_without_rebuild(
    fake: FakeWorkflowExecutor,
) -> None:
    fake.source_ready = True
    fake._write_source_manifest()
    fake.acceptance_ready = True
    fake._write_acceptance()

    _run(fake)
    names = [call["step"] for call in fake.calls]

    assert "daily-migration-preflight" not in names
    assert "daily-source-sync" not in names
    assert "daily-build-and-accept" not in names
    assert "daily-activation-preflight" in names
    assert "daily-atomic-activation" in names
    assert "candidate49-source-to-signal-collection" in names


def test_accepted_active_daily_root_skips_migration_entirely(
    fake: FakeWorkflowExecutor,
) -> None:
    fake.source_ready = True
    fake._write_source_manifest()
    fake.acceptance_ready = True
    fake._write_acceptance()
    fake.activated = True
    fake._write_activation()

    _run(fake)
    names = [call["step"] for call in fake.calls]

    assert names[:3] == [
        "active-daily-status",
        "post-activation-price-basis-audit",
        "resolve-active-data-root",
    ]
    assert not any(name.startswith("daily-migration") for name in names)
    assert "daily-source-sync" not in names
    assert "daily-build-and-accept" not in names
    assert "daily-atomic-activation" not in names
    assert "candidate49-source-to-signal-collection" in names


def test_ready_same_session_quality_skips_refresh(
    fake: FakeWorkflowExecutor,
) -> None:
    fake.source_ready = True
    fake._write_source_manifest()
    fake.acceptance_ready = True
    fake._write_acceptance()
    fake.activated = True
    fake._write_activation()
    fake.quality_ready = True
    fake._write_quality()

    _run(fake)
    names = [call["step"] for call in fake.calls]

    assert "candidate49-quality-readiness-probe" in names
    assert "future-quarterly-quality-refresh" not in names
    assert "candidate49-final-combined-preflight" not in names
    assert names[-1] == "candidate49-source-to-signal-collection"


def test_collection_failure_rerun_reuses_daily_and_quality_boundaries(
    fake: FakeWorkflowExecutor,
) -> None:
    fake.fail_step = "candidate49-source-to-signal-collection"
    with pytest.raises(
        workflow.Candidate49FutureSessionWorkflowError,
        match="candidate49-source-to-signal-collection failed",
    ):
        _run(fake)

    first_names = [call["step"] for call in fake.calls]
    assert "daily-source-sync" in first_names
    assert "future-quarterly-quality-refresh" in first_names
    assert not workflow._final_record_path(_config(fake)).exists()

    fake.calls.clear()
    fake.fail_step = None
    _run(fake)
    resumed_names = [call["step"] for call in fake.calls]

    assert resumed_names == [
        "active-daily-status",
        "post-activation-price-basis-audit",
        "resolve-active-data-root",
        "candidate49-quality-readiness-probe",
        "candidate49-source-to-signal-collection",
    ]


def test_any_child_failure_stops_all_later_phases(
    fake: FakeWorkflowExecutor,
) -> None:
    fake.fail_step = "daily-source-sync"
    with pytest.raises(
        workflow.Candidate49FutureSessionWorkflowError,
        match="daily-source-sync failed",
    ):
        _run(fake)
    names = [call["step"] for call in fake.calls]
    assert names[-1] == "daily-source-sync"
    assert "daily-build-and-accept" not in names
    assert "candidate49-source-to-signal-collection" not in names


def test_reference_covered_daily_request_stops_before_quality_or_signal(
    fake: FakeWorkflowExecutor,
) -> None:
    fake.reference_daily_requests = 1
    with pytest.raises(
        workflow.Candidate49FutureSessionWorkflowError,
        match="does not prove accepted historical reuse",
    ):
        _run(fake)
    names = [call["step"] for call in fake.calls]
    assert names[-1] == "post-activation-daily-status"
    assert "post-activation-price-basis-audit" not in names
    assert "candidate49-source-to-signal-collection" not in names


def test_non_quality_candidate_blocker_stops_before_quality_network(
    fake: FakeWorkflowExecutor,
) -> None:
    fake.extra_probe_failure = "candidate49_signal_ledger_not_accepted"
    with pytest.raises(
        workflow.Candidate49FutureSessionWorkflowError,
        match="non-quality blocker",
    ):
        _run(fake)
    names = [call["step"] for call in fake.calls]
    assert names[-1] == "candidate49-quality-readiness-probe"
    assert "future-quarterly-quality-refresh" not in names
    assert "candidate49-source-to-signal-collection" not in names


def test_later_tushare_refresh_seeds_before_provider_sync(
    tmp_path,
    monkeypatch,
) -> None:
    value = FakeWorkflowExecutor(
        tmp_path,
        active_source="tushare",
        active_calendar_end="2026-07-24",
    )
    monkeypatch.setattr(workflow, "FIXED_MINUTE_DATA_ROOT", value.minute_root)
    monkeypatch.setattr(workflow, "SIGNAL_LEDGER_PATH", value.signal_ledger)
    monkeypatch.setattr(
        workflow,
        "EXECUTION_LEDGER_PATH",
        value.execution_ledger,
    )
    _patch_fake_semantics(monkeypatch, value)
    # A later refresh parent must itself be an accepted active Tushare root.
    metadata = value.active_root / "metadata"
    metadata.mkdir()
    (metadata / "tushare_daily_provider_acceptance.json").write_text(
        "{}\n",
        encoding="utf-8",
    )

    _run(value)
    names = [call["step"] for call in value.calls]
    assert names.index("daily-seed-refresh") < names.index(
        "daily-migration-preflight"
    )
    seed_call = next(
        call for call in value.calls if call["step"] == "daily-seed-refresh"
    )
    assert seed_call["token_present"] is False


def test_completed_record_revalidates_later_without_token_or_child_calls(
    fake: FakeWorkflowExecutor,
) -> None:
    first = _run(fake)
    fake.calls.clear()

    result = workflow.run_workflow(
        _config(fake),
        confirm_run=True,
        executor=lambda *args: pytest.fail("child command must not run"),
        token_loader=lambda: pytest.fail("Token must not be loaded"),
        now=NEXT_DAY,
        lock_factory=lambda path: nullcontext(),
        reference_manifest_path=fake.reference_manifest,
        reference_manifest_sha256=fake.reference_sha256,
    )

    assert result["status"] == (
        "completed_workflow_record_validated_no_provider_request"
    )
    assert result["record_sha256"] == first["record_sha256"]
    assert result["provider_request_issued"] is False
    assert fake.calls == []


def test_completed_record_rejects_symbolic_link_identity(
    fake: FakeWorkflowExecutor,
) -> None:
    first = _run(fake)
    record_path = Path(first["record_path"])
    target = fake.minute_root / "workflow-record-symlink-target.json"
    record_path.replace(target)
    record_path.symlink_to(target)

    with pytest.raises(
        workflow.Candidate49FutureSessionWorkflowError,
        match="workflow record file identity",
    ):
        workflow.run_workflow(
            _config(fake),
            confirm_run=True,
            executor=lambda *args: pytest.fail("child command must not run"),
            token_loader=lambda: pytest.fail("Token must not be loaded"),
            now=NEXT_DAY,
            lock_factory=lambda path: nullcontext(),
            reference_manifest_path=fake.reference_manifest,
            reference_manifest_sha256=fake.reference_sha256,
        )


def test_completed_record_rejects_shared_hardlink_identity(
    fake: FakeWorkflowExecutor,
) -> None:
    first = _run(fake)
    record_path = Path(first["record_path"])
    alias = fake.minute_root / "workflow-record-hardlink-alias.json"
    os.link(record_path, alias)

    with pytest.raises(
        workflow.Candidate49FutureSessionWorkflowError,
        match="workflow record file identity",
    ):
        workflow.run_workflow(
            _config(fake),
            confirm_run=True,
            executor=lambda *args: pytest.fail("child command must not run"),
            token_loader=lambda: pytest.fail("Token must not be loaded"),
            now=NEXT_DAY,
            lock_factory=lambda path: nullcontext(),
            reference_manifest_path=fake.reference_manifest,
            reference_manifest_sha256=fake.reference_sha256,
        )


def test_completed_record_rejects_inode_replacement_between_check_and_read(
    fake: FakeWorkflowExecutor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = _run(fake)
    record_path = Path(first["record_path"])
    replacement = fake.minute_root / "workflow-record-replacement.json"
    replacement.write_bytes(record_path.read_bytes())
    original_require = workflow._require_unique_regular_file
    swapped = False

    def swap_after_identity_check(
        path: Path,
        *,
        label: str,
    ) -> os.stat_result:
        nonlocal swapped
        identity = original_require(path, label=label)
        if path == record_path and not swapped:
            os.replace(replacement, record_path)
            swapped = True
        return identity

    monkeypatch.setattr(
        workflow,
        "_require_unique_regular_file",
        swap_after_identity_check,
    )

    with pytest.raises(
        workflow.Candidate49FutureSessionWorkflowError,
        match="workflow record file identity changed during read",
    ):
        workflow.run_workflow(
            _config(fake),
            confirm_run=True,
            executor=lambda *args: pytest.fail("child command must not run"),
            token_loader=lambda: pytest.fail("Token must not be loaded"),
            now=NEXT_DAY,
            lock_factory=lambda path: nullcontext(),
            reference_manifest_path=fake.reference_manifest,
            reference_manifest_sha256=fake.reference_sha256,
        )
    assert swapped is True


def test_missing_record_rejects_symbolic_link_parent_before_token_or_child(
    fake: FakeWorkflowExecutor,
) -> None:
    record_parent = (
        fake.minute_root
        / "metadata"
        / "rich_data"
        / "candidate49_future_workflows"
    )
    record_parent.parent.mkdir(parents=True)
    target = fake.minute_root / "workflow-record-parent-target"
    target.mkdir()
    record_parent.symlink_to(target, target_is_directory=True)

    with pytest.raises(
        workflow.Candidate49FutureSessionWorkflowError,
        match="workflow record parent directory identity",
    ):
        workflow.run_workflow(
            _config(fake),
            confirm_run=True,
            executor=lambda *args: pytest.fail("child command must not run"),
            token_loader=lambda: pytest.fail("Token must not be loaded"),
            now=AFTER_CLOSE,
            lock_factory=lambda path: nullcontext(),
            reference_manifest_path=fake.reference_manifest,
            reference_manifest_sha256=fake.reference_sha256,
        )


def test_atomic_workflow_record_write_fsyncs_file_and_parent_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "nested" / "workflow.json"
    modes: list[int] = []
    real_fsync = os.fsync

    def tracked_fsync(file_descriptor: int) -> None:
        modes.append(os.fstat(file_descriptor).st_mode)
        real_fsync(file_descriptor)

    monkeypatch.setattr(workflow.os, "fsync", tracked_fsync)
    workflow._atomic_write_json(target, {"status": "complete"})

    assert json.loads(target.read_text(encoding="utf-8")) == {
        "status": "complete"
    }
    assert len(modes) == 2
    assert stat.S_ISREG(modes[0])
    assert stat.S_ISDIR(modes[1])
    assert list(target.parent.glob(".*.partial")) == []


def test_completed_record_revalidates_after_both_ledgers_grow(
    fake: FakeWorkflowExecutor,
) -> None:
    first = _run(fake)
    candidate.append_future_ledger_entry(
        path=fake.signal_ledger,
        kind=candidate.FUTURE_SIGNAL_LEDGER_KIND,
        payload={
            "entry_id": (
                f"{candidate.FUTURE_REGISTRATION_ID}:signal:2026-07-28"
            ),
            "session_date": "2026-07-28",
        },
    )
    candidate.append_future_ledger_entry(
        path=fake.execution_ledger,
        kind=candidate.FUTURE_EXECUTION_LEDGER_KIND,
        payload={
            "entry_id": (
                f"{candidate.FUTURE_REGISTRATION_ID}:execution:2026-07-28"
            ),
            "session_date": "2026-07-28",
        },
    )

    result = workflow.run_workflow(
        _config(fake),
        confirm_run=True,
        executor=lambda *args: pytest.fail("child command must not run"),
        token_loader=lambda: pytest.fail("Token must not be loaded"),
        now=NEXT_DAY,
        lock_factory=lambda path: nullcontext(),
        reference_manifest_path=fake.reference_manifest,
        reference_manifest_sha256=fake.reference_sha256,
    )

    assert result["status"] == (
        "completed_workflow_record_validated_no_provider_request"
    )
    assert result["record_sha256"] == first["record_sha256"]


def test_fewer_than_50_names_freezes_replayable_no_signal_record(
    fake: FakeWorkflowExecutor,
) -> None:
    fake.candidate_eligible_names = 49
    first = _run(fake)
    record_path = Path(first["record_path"])
    record = json.loads(record_path.read_text(encoding="utf-8"))

    assert first["candidate49_status"] == (
        "future_session_frozen_without_signal_fewer_than_50_names"
    )
    assert first["candidate49_outcome"] == (
        "future_session_frozen_without_signal_fewer_than_50_names"
    )
    assert record["candidate49_outcome"] == (
        "future_session_frozen_without_signal_fewer_than_50_names"
    )
    assert record["candidate49_eligible_names"] == 49
    assert record["candidate49_signal_entry_sha256"] is None
    assert record["phase_receipts"][-1]["status"] == (
        "future_session_frozen_without_signal_fewer_than_50_names"
    )
    assert record["phase_receipts"][-1]["eligible_names"] == 49
    assert record["phase_receipts"][-1]["signal_entry_sha256"] is None
    assert (
        candidate.validate_future_ledger(
            fake.signal_ledger,
            candidate.FUTURE_SIGNAL_LEDGER_KIND,
        )["entries"]
        == []
    )

    repeated = workflow.run_workflow(
        _config(fake),
        confirm_run=True,
        executor=lambda *args: pytest.fail("child command must not run"),
        token_loader=lambda: pytest.fail("Token must not be loaded"),
        now=NEXT_DAY,
        lock_factory=lambda path: nullcontext(),
        reference_manifest_path=fake.reference_manifest,
        reference_manifest_sha256=fake.reference_sha256,
    )

    assert repeated["status"] == (
        "completed_workflow_record_validated_no_provider_request"
    )
    assert repeated["candidate49_outcome"] == (
        "future_session_frozen_without_signal_fewer_than_50_names"
    )
    assert repeated["record_sha256"] == first["record_sha256"]


def test_completed_record_rejects_rewritten_signal_summary(
    fake: FakeWorkflowExecutor,
) -> None:
    first = _run(fake)
    record_path = Path(first["record_path"])
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["candidate49_eligible_names"] = 1
    record["candidate49_signal_entry_sha256"] = "f" * 64
    workflow._atomic_write_json(record_path, record)
    fake.calls.clear()

    with pytest.raises(
        workflow.Candidate49FutureSessionWorkflowError,
        match="Candidate49 summary",
    ):
        workflow.run_workflow(
            _config(fake),
            confirm_run=True,
            executor=lambda *args: pytest.fail("child command must not run"),
            token_loader=lambda: pytest.fail("Token must not be loaded"),
            now=NEXT_DAY,
            lock_factory=lambda path: nullcontext(),
            reference_manifest_path=fake.reference_manifest,
            reference_manifest_sha256=fake.reference_sha256,
        )
    assert fake.calls == []


def test_completed_record_rejects_rewritten_candidate_provider_call_count(
    fake: FakeWorkflowExecutor,
) -> None:
    first = _run(fake)
    record_path = Path(first["record_path"])
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["candidate49_raw_provider_calls_total"] = 0
    record["phase_receipts"][-1]["raw_provider_calls_total"] = 0
    workflow._atomic_write_json(record_path, record)
    fake.calls.clear()

    with pytest.raises(
        workflow.Candidate49FutureSessionWorkflowError,
        match="Candidate49 provider-call evidence",
    ):
        workflow.run_workflow(
            _config(fake),
            confirm_run=True,
            executor=lambda *args: pytest.fail("child command must not run"),
            token_loader=lambda: pytest.fail("Token must not be loaded"),
            now=NEXT_DAY,
            lock_factory=lambda path: nullcontext(),
            reference_manifest_path=fake.reference_manifest,
            reference_manifest_sha256=fake.reference_sha256,
        )
    assert fake.calls == []


def test_completed_record_uses_raw_total_after_zero_call_resume(
    fake: FakeWorkflowExecutor,
) -> None:
    fake.candidate_provider_calls_this_invocation = 0
    result = _run(fake)
    record = json.loads(
        Path(result["record_path"]).read_text(encoding="utf-8")
    )

    assert record["candidate49_raw_provider_calls_total"] == 50
    assert record["phase_receipts"][-1]["raw_provider_calls_total"] == 50
    assert "candidate49_provider_calls_this_invocation" not in record
    assert "steps" not in record


def test_completed_record_rejects_rewritten_intermediate_step(
    fake: FakeWorkflowExecutor,
) -> None:
    first = _run(fake)
    record_path = Path(first["record_path"])
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["phase_receipts"][1]["phase"] = "synthetic-provider-bypass"
    workflow._atomic_write_json(record_path, record)

    with pytest.raises(
        workflow.Candidate49FutureSessionWorkflowError,
        match="phase receipts",
    ):
        workflow.run_workflow(
            _config(fake),
            confirm_run=True,
            executor=lambda *args: pytest.fail("child command must not run"),
            token_loader=lambda: pytest.fail("Token must not be loaded"),
            now=NEXT_DAY,
            lock_factory=lambda path: nullcontext(),
            reference_manifest_path=fake.reference_manifest,
            reference_manifest_sha256=fake.reference_sha256,
        )


def test_completed_record_rejects_rewritten_append_vs_reuse_claim(
    fake: FakeWorkflowExecutor,
) -> None:
    first = _run(fake)
    record_path = Path(first["record_path"])
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["candidate49_outcome"] = (
        "future_session_frozen_without_signal_fewer_than_50_names"
    )
    record["phase_receipts"][-1]["status"] = (
        "future_session_frozen_without_signal_fewer_than_50_names"
    )
    workflow._atomic_write_json(record_path, record)

    with pytest.raises(
        workflow.Candidate49FutureSessionWorkflowError,
        match="Candidate49 outcome",
    ):
        workflow.run_workflow(
            _config(fake),
            confirm_run=True,
            executor=lambda *args: pytest.fail("child command must not run"),
            token_loader=lambda: pytest.fail("Token must not be loaded"),
            now=NEXT_DAY,
            lock_factory=lambda path: nullcontext(),
            reference_manifest_path=fake.reference_manifest,
            reference_manifest_sha256=fake.reference_sha256,
        )


def test_latest_completed_quarter_end_is_deterministic() -> None:
    assert workflow.latest_completed_quarter_end(SESSION) == dt.date(2026, 6, 30)
    assert workflow.latest_completed_quarter_end(
        dt.date(2026, 3, 30)
    ) == dt.date(2025, 12, 31)
    assert workflow.latest_completed_quarter_end(
        dt.date(2026, 3, 31)
    ) == dt.date(2026, 3, 31)
