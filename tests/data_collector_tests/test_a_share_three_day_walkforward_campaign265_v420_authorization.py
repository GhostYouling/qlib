from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import stat
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    REPO_ROOT
    / "scripts/a_share_three_day_walkforward_campaign265_v420_authorization.py"
)


def load_module():
    module_name = "campaign265_v420_authorization_under_test"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def fake_workflow_plan() -> dict[str, object]:
    return {
        "ready": True,
        "exit_code_if_executed": 0,
        "checks": {f"check_{index:02d}": True for index in range(34)},
        "accepted_trade_date_count": 1699,
        "exact_provider_call_count": 1700,
        "request_sequence_canonical_json_sha256": (
            "3f9cccb3134b7e9e22f5d34fd8bc07f89e1d8047dd775d07c3257443a97b4c58"
        ),
        "future_run_authorized": False,
        "run_interface_exposed": False,
        "credential_file_or_environment_inspected": False,
        "provider_client_imported_or_created": False,
        "provider_request_issued": False,
        "source_candidate_comparator_price_or_return_value_read": False,
        "filesystem_write_performed": False,
    }


def prepare_synthetic_bindings(module, root: Path) -> dict[str, tuple[str, str]]:
    bindings: dict[str, tuple[str, str]] = {}
    for index, (name, (relative, _)) in enumerate(
        module.AUTHORITATIVE_BINDINGS.items()
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = f"{name}:{index}\n".encode()
        path.write_bytes(payload)
        bindings[name] = (relative, sha256_bytes(payload))
    return bindings


def test_real_plan_is_ready_and_zero_write() -> None:
    module = load_module()
    target = REPO_ROOT / module.TARGET_POLICY_RELATIVE
    before = os.path.lexists(target)
    plan = module.build_plan()
    after = os.path.lexists(target)

    assert before is False and after is False
    assert plan["ready"] is True
    assert plan["exit_code_if_executed"] == 0
    assert plan["blockers"] == []
    assert len(plan["checks"]) == 31
    assert all(plan["checks"].values())
    assert plan["v420_policy_published"] is False
    assert plan["credential_file_or_environment_inspected"] is False
    assert plan["provider_request_issued"] is False
    assert plan["candidate_comparator_price_or_return_value_read"] is False
    assert plan["filesystem_write_performed"] is False


def test_attempt_artifacts_match_the_frozen_workflow_destinations() -> None:
    module = load_module()
    destinations = module.WORKFLOW.DESTINATIONS
    assert module.ATTEMPT_ARTIFACTS == (
        destinations["staging_root"],
        destinations["final_root"],
        destinations["intent"],
        destinations["attempt_journal"],
        destinations["terminal_failure"],
        destinations["repository_acceptance_manifest"],
    )


def test_publish_requires_explicit_confirmation_before_plan_or_write(
    tmp_path: Path,
) -> None:
    module = load_module()
    called = False

    def workflow_plan_builder():
        nonlocal called
        called = True
        return fake_workflow_plan()

    with pytest.raises(
        module.Campaign265AuthorizationError,
        match="explicit_v420_publication_required",
    ):
        module.publish_policy(
            confirm_v420_publication=False,
            repo_root=tmp_path,
            bindings={},
            workflow_plan_builder=workflow_plan_builder,
        )
    assert called is False
    assert not os.path.lexists(tmp_path / module.TARGET_POLICY_RELATIVE)


def test_synthetic_explicit_publication_is_exclusive_and_exact(
    tmp_path: Path,
) -> None:
    module = load_module()
    bindings = prepare_synthetic_bindings(module, tmp_path)
    target = tmp_path / module.TARGET_POLICY_RELATIVE

    result = module.publish_policy(
        confirm_v420_publication=True,
        repo_root=tmp_path,
        bindings=bindings,
        workflow_plan_builder=fake_workflow_plan,
        recorded_at="2026-08-24T06:00:00Z",
        post_publish_validator=lambda: True,
    )

    payload = json.loads(target.read_text(encoding="utf-8"))
    authorization = payload["campaign265_source_acceptance_run_authorization"]
    target_stat = target.lstat()
    assert result["status"].endswith("separate_explicit_confirm_run")
    assert result["real_run_executed"] is False
    assert stat.S_ISREG(target_stat.st_mode)
    assert target_stat.st_nlink == 1
    assert target_stat.st_mode & 0o777 == 0o644
    assert payload["version"] == 420
    assert authorization["authorized"] is True
    assert authorization["one_shot"] is True
    assert authorization["explicit_confirm_run_required"] is True
    assert authorization["retry_allowed"] is False
    assert authorization["exact_provider_call_count"] == 1700
    assert authorization["workflow"] == {
        "path": bindings["workflow"][0],
        "sha256": bindings["workflow"][1],
    }
    assert (
        payload["unchanged_execution_boundary"][
            "real_run_requires_separate_explicit_confirm_run"
        ]
        is True
    )

    with pytest.raises(
        module.Campaign265AuthorizationError,
        match="v420_publication_plan_not_ready",
    ):
        module.publish_policy(
            confirm_v420_publication=True,
            repo_root=tmp_path,
            bindings=bindings,
            workflow_plan_builder=fake_workflow_plan,
        )


def test_synthetic_policy_is_accepted_by_frozen_workflow_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    bindings = prepare_synthetic_bindings(module, tmp_path)
    target = tmp_path / module.TARGET_POLICY_RELATIVE
    module.publish_policy(
        confirm_v420_publication=True,
        repo_root=tmp_path,
        bindings=bindings,
        workflow_plan_builder=fake_workflow_plan,
        recorded_at="2026-08-24T06:00:00Z",
        post_publish_validator=lambda: True,
    )

    workflow = module.WORKFLOW
    monkeypatch.setattr(workflow, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(workflow, "RUN_AUTHORIZATION_POLICY_PATH", target)
    monkeypatch.setattr(workflow, "WORKFLOW_PATH", tmp_path / bindings["workflow"][0])
    monkeypatch.setattr(
        workflow,
        "WORKFLOW_TEST_PATH",
        tmp_path / bindings["workflow_tests"][0],
    )
    monkeypatch.setattr(
        workflow,
        "EXECUTION_PROTOCOL_PATH",
        tmp_path / bindings["execution_protocol"][0],
    )
    monkeypatch.setattr(
        workflow,
        "EXECUTION_PROTOCOL_SHA256",
        bindings["execution_protocol"][1],
    )
    monkeypatch.setattr(
        workflow,
        "IMPLEMENTATION_FREEZE_PATH",
        tmp_path / bindings["implementation_freeze_v2"][0],
    )
    monkeypatch.setattr(
        workflow,
        "PLAN_RESULT_PATH",
        tmp_path / bindings["workflow_plan_result_v2"][0],
    )

    checks = workflow._run_authorization_checks()
    assert checks
    assert all(checks.values())
    assert workflow._run_authorized() is True


def test_symlinked_target_parent_fails_closed(tmp_path: Path) -> None:
    module = load_module()
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "docs").symlink_to(outside, target_is_directory=True)

    plan = module.build_plan(
        repo_root=tmp_path,
        bindings={},
        workflow_plan_builder=fake_workflow_plan,
    )

    assert plan["ready"] is False
    assert plan["checks"]["target_parent_real_directory_tree"] is False
    assert not os.path.lexists(outside / module.TARGET_POLICY_RELATIVE.name)


def test_public_cli_publish_without_flag_leaves_v420_absent(capsys) -> None:
    module = load_module()
    target = REPO_ROOT / module.TARGET_POLICY_RELATIVE
    assert not os.path.lexists(target)

    exit_code = module.main(["publish"])
    result = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert result["error_code"] == "explicit_v420_publication_required"
    assert result["provider_request_issued"] is False
    assert result["filesystem_write_performed"] is False
    assert not os.path.lexists(target)
