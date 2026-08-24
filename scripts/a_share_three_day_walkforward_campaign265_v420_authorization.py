#!/usr/bin/env python3
"""Plan or explicitly publish Campaign265's exact v420 run authorization.

``plan`` is the default-safe boundary: it reads only frozen metadata and the
existing workflow's zero-network plan.  ``publish`` requires an explicit
confirmation flag and only creates the v420 policy; it never loads a
credential, imports a provider client, issues a request, or runs Campaign265.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_three_day_walkforward_campaign265_source_acceptance_workflow as WORKFLOW  # noqa: E402


TARGET_POLICY_RELATIVE = Path(
    "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v420_20260824.json"
)
PROTOCOL_RELATIVE = Path(
    "docs/a_share_three_day_walkforward_campaign_265_v420_authorization_publisher_protocol_20260824.json"
)
REQUEST_SEQUENCE_SHA256 = (
    "3f9cccb3134b7e9e22f5d34fd8bc07f89e1d8047dd775d07c3257443a97b4c58"
)
EXACT_PROVIDER_CALL_COUNT = 1700
ACCEPTED_TRADE_DATE_COUNT = 1699

AUTHORITATIVE_BINDINGS: dict[str, tuple[str, str]] = {
    "latest_state": (
        "docs/a_share_three_day_iteration_status_20260824_campaign265_execution_workflow_plan_ready_v2.json",
        "1cf226d8d64520cf1801baa6f0bf1ac96a3adb19f85e3d950e7d19d674a79753",
    ),
    "plan_authorization_policy_v419_revision_2": (
        "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v419_20260824_execution_path_hardening_v2.json",
        "c331d3931893ea183a7d0a750be8f5b136b1e95e5a0e1fc65683e6cf64d5cc2a",
    ),
    "workflow": (
        "scripts/a_share_three_day_walkforward_campaign265_source_acceptance_workflow.py",
        "796322ab186c837dc02a5657572a3f936792dc33ffd4c817cfc430c1d7639020",
    ),
    "workflow_tests": (
        "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign265_source_acceptance_workflow.py",
        "b160f11d19e5ab85d2b6f3a523ac450a0be8214014165837591c68de0d1faac9",
    ),
    "execution_protocol": (
        "docs/a_share_three_day_walkforward_campaign_265_source_acceptance_execution_protocol_20260824.json",
        "766172caa77a9ffa90867e7299e1ac77816934469b8cafd5f63fd27281d9c04c",
    ),
    "implementation_freeze_v2": (
        "docs/a_share_three_day_walkforward_campaign_265_source_acceptance_execution_workflow_implementation_freeze_v2_20260824.json",
        "27bcadf74f6dcd0abe47e22f7d62eacf7f2e788bb4b4d0286d0b7e63337a267f",
    ),
    "workflow_plan_result_v2": (
        "docs/a_share_three_day_walkforward_campaign_265_source_acceptance_execution_workflow_plan_result_v2_20260824.json",
        "9006c35b51912e48cf3ae03a6c581c87da6249119b3ceaeb54b0a8ba998bcd03",
    ),
    "workflow_plan_validation_v2": (
        "docs/a_share_three_day_walkforward_campaign_265_source_acceptance_execution_workflow_plan_validation_v2_20260824.json",
        "1ac037d922474364d3d39ad2c1592e013a288b7f5fb75d51db792be6257882ee",
    ),
    "publisher_protocol": (
        str(PROTOCOL_RELATIVE),
        "ea524208edb471e7a98343640f631f6e3e99c97576ea3004f9861fd2cb738a7a",
    ),
}

ATTEMPT_ARTIFACTS = (
    "data/raw/a_share/rich/tushare/convertible_premium/campaign265_2019_2025_v1.staging",
    "data/raw/a_share/rich/tushare/convertible_premium/campaign265_2019_2025_v1",
    "data/metadata/rich_data/runs/campaign265_convertible_premium_acceptance_intent_v1.json",
    "data/metadata/rich_data/runs/campaign265_convertible_premium_acceptance_attempt_v1.jsonl",
    "data/metadata/rich_data/runs/campaign265_convertible_premium_acceptance_failure_v1.json",
    "data/metadata/rich_data/runs/campaign265_convertible_premium_acceptance_v1.json",
)


class Campaign265AuthorizationError(RuntimeError):
    """Raised when the v420 publication boundary fails closed."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _is_real_directory(path: Path) -> bool:
    try:
        mode = path.lstat().st_mode
    except OSError:
        return False
    return stat.S_ISDIR(mode) and not stat.S_ISLNK(mode)


def _directory_tree_is_safe(repo_root: Path, target_parent: Path) -> bool:
    try:
        root = repo_root.absolute()
        parent = target_parent.absolute()
        parent.relative_to(root)
    except (OSError, ValueError):
        return False
    if not _is_real_directory(root):
        return False
    current = root
    for part in parent.relative_to(root).parts:
        current = current / part
        if not _is_real_directory(current):
            return False
    return True


def _workflow_plan_checks(plan: Mapping[str, Any]) -> dict[str, bool]:
    plan_checks = plan.get("checks")
    return {
        "workflow_plan_ready": plan.get("ready") is True,
        "workflow_plan_exit_code_zero": plan.get("exit_code_if_executed") == 0,
        "workflow_plan_check_count_34": isinstance(plan_checks, Mapping)
        and len(plan_checks) == 34,
        "workflow_plan_all_checks_passed": isinstance(plan_checks, Mapping)
        and all(value is True for value in plan_checks.values()),
        "accepted_trade_date_count_1699": plan.get("accepted_trade_date_count")
        == ACCEPTED_TRADE_DATE_COUNT,
        "exact_provider_call_count_1700": plan.get("exact_provider_call_count")
        == EXACT_PROVIDER_CALL_COUNT,
        "request_sequence_digest_exact": plan.get(
            "request_sequence_canonical_json_sha256"
        )
        == REQUEST_SEQUENCE_SHA256,
        "future_run_not_yet_authorized": plan.get("future_run_authorized") is False,
        "run_interface_not_yet_exposed": plan.get("run_interface_exposed") is False,
        "workflow_plan_no_credential_inspection": plan.get(
            "credential_file_or_environment_inspected"
        )
        is False,
        "workflow_plan_no_provider_client": plan.get(
            "provider_client_imported_or_created"
        )
        is False,
        "workflow_plan_no_provider_request": plan.get("provider_request_issued")
        is False,
        "workflow_plan_no_values": plan.get(
            "source_candidate_comparator_price_or_return_value_read"
        )
        is False,
        "workflow_plan_no_write": plan.get("filesystem_write_performed") is False,
    }


def build_plan(
    *,
    repo_root: Path = REPO_ROOT,
    bindings: Mapping[str, tuple[str, str]] = AUTHORITATIVE_BINDINGS,
    workflow_plan_builder: Callable[[], Mapping[str, Any]] = WORKFLOW.build_plan,
) -> dict[str, Any]:
    """Return a zero-write, zero-credential publication-readiness plan."""

    root = repo_root.absolute()
    target = root / TARGET_POLICY_RELATIVE
    checks: dict[str, bool] = {}
    for name, (relative, expected_sha256) in bindings.items():
        path = root / relative
        checks[f"binding_{name}"] = (
            path.is_file()
            and not path.is_symlink()
            and file_sha256(path) == expected_sha256
        )
    checks["target_parent_real_directory_tree"] = _directory_tree_is_safe(
        root, target.parent
    )
    checks["v420_target_absent"] = not os.path.lexists(target)
    for relative in ATTEMPT_ARTIFACTS:
        checks[f"attempt_artifact_absent_{Path(relative).name}"] = not os.path.lexists(
            root / relative
        )

    workflow_plan = dict(workflow_plan_builder())
    checks.update(_workflow_plan_checks(workflow_plan))
    ready = bool(checks and all(checks.values()))
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign265_v420_authorization_publication_plan",
        "status": (
            "ready_for_explicit_v420_publication_zero_network"
            if ready
            else "blocked_fail_closed"
        ),
        "ready": ready,
        "exit_code_if_executed": 0 if ready else 2,
        "campaign": 265,
        "target_policy": str(TARGET_POLICY_RELATIVE),
        "checks": checks,
        "blockers": [name for name, passed in checks.items() if not passed],
        "accepted_trade_date_count": workflow_plan.get("accepted_trade_date_count"),
        "exact_provider_call_count": workflow_plan.get("exact_provider_call_count"),
        "request_sequence_canonical_json_sha256": workflow_plan.get(
            "request_sequence_canonical_json_sha256"
        ),
        "publication_command": (
            "scripts/a_share_three_day_walkforward_campaign265_v420_authorization.py "
            "publish --confirm-v420-publication"
        ),
        "post_publication_plan_command": (
            "scripts/a_share_three_day_walkforward_campaign265_source_acceptance_workflow.py plan"
        ),
        "real_run_command_requires_separate_operator_confirmation": (
            "scripts/a_share_three_day_walkforward_campaign265_source_acceptance_workflow.py "
            "run --confirm-run"
        ),
        "v420_policy_published": False,
        "credential_file_or_environment_inspected": False,
        "credential_value_or_digest_read": False,
        "provider_module_imported_or_client_created": False,
        "provider_request_issued": False,
        "candidate_comparator_price_or_return_value_read": False,
        "filesystem_write_performed": False,
        "ready_does_not_publish_v420_or_authorize_the_real_run": True,
    }


def _binding_payload(
    bindings: Mapping[str, tuple[str, str]], name: str
) -> dict[str, str]:
    path, sha256 = bindings[name]
    return {"path": path, "sha256": sha256}


def build_policy_payload(
    *,
    recorded_at: str,
    bindings: Mapping[str, tuple[str, str]] = AUTHORITATIVE_BINDINGS,
) -> dict[str, Any]:
    """Build the exact policy consumed by the frozen workflow."""

    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy",
        "version": 420,
        "status": "campaign265_one_shot_source_acceptance_run_authorized_only_with_separate_explicit_confirm_run",
        "recorded_at": recorded_at,
        "timestamp_semantics": (
            "measured host UTC at exclusive atomic v420 publication; before credential "
            "load, provider entry, request intent, source values or run --confirm-run"
        ),
        "supersedes_without_rewriting": _binding_payload(
            bindings, "plan_authorization_policy_v419_revision_2"
        ),
        "publication_protocol": _binding_payload(bindings, "publisher_protocol"),
        "campaign265_source_acceptance_run_authorization": {
            "authorized": True,
            "one_shot": True,
            "explicit_confirm_run_required": True,
            "retry_allowed": False,
            "exact_provider_call_count": EXACT_PROVIDER_CALL_COUNT,
            "request_sequence_canonical_json_sha256": REQUEST_SEQUENCE_SHA256,
            "workflow": _binding_payload(bindings, "workflow"),
            "workflow_tests": _binding_payload(bindings, "workflow_tests"),
            "execution_protocol": _binding_payload(bindings, "execution_protocol"),
            "implementation_freeze": _binding_payload(
                bindings, "implementation_freeze_v2"
            ),
            "workflow_plan_result": _binding_payload(
                bindings, "workflow_plan_result_v2"
            ),
            "latest_prepublication_state": _binding_payload(bindings, "latest_state"),
            "workflow_plan_validation": _binding_payload(
                bindings, "workflow_plan_validation_v2"
            ),
        },
        "unchanged_execution_boundary": {
            "accepted_trade_date_count": ACCEPTED_TRADE_DATE_COUNT,
            "minimum_seconds_between_provider_entries": 1.05,
            "schedule_formula_fields_paths_row_limits_interval_retry_and_failure_semantics_changed": False,
            "v420_publication_itself_loads_credential_or_provider": False,
            "v420_publication_itself_creates_attempt_intent_or_journal": False,
            "v420_publication_itself_reads_source_candidate_comparator_price_or_return_values": False,
            "workflow_plan_must_be_rerun_after_publication": True,
            "real_run_requires_separate_explicit_confirm_run": True,
        },
        "research_boundary": {
            "candidate49_historical_backfill_allowed": False,
            "second_prospective_candidate_allowed": False,
            "historical_daily_price_or_forward_return_allowed_before_no_return_admission": False,
            "stress_2024_2025_allowed_before_nonzero_development_survivor": False,
            "current_scoring_selection_sizing_positions_or_orders_allowed": False,
            "investment_advice": False,
        },
    }


def _publish_exclusive(target: Path, payload: bytes) -> None:
    parent_stat = target.parent.lstat()
    directory_flags = (
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    )
    directory = os.open(target.parent, directory_flags)
    directory_stat = os.fstat(directory)
    if not stat.S_ISDIR(directory_stat.st_mode) or (
        directory_stat.st_dev,
        directory_stat.st_ino,
    ) != (parent_stat.st_dev, parent_stat.st_ino):
        os.close(directory)
        raise Campaign265AuthorizationError("publication_parent_identity_changed")
    temporary_name = f".{target.name}.{os.getpid()}.partial"
    if os.path.lexists(target.parent / temporary_name):
        os.close(directory)
        raise Campaign265AuthorizationError("publication_temporary_path_already_exists")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(temporary_name, flags, 0o644, dir_fd=directory)
    linked = False
    try:
        os.fchmod(descriptor, 0o644)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(
            temporary_name,
            target.name,
            src_dir_fd=directory,
            dst_dir_fd=directory,
            follow_symlinks=False,
        )
        linked = True
        os.unlink(temporary_name, dir_fd=directory)
        os.fsync(directory)
        final_parent_stat = target.parent.lstat()
        if (final_parent_stat.st_dev, final_parent_stat.st_ino) != (
            directory_stat.st_dev,
            directory_stat.st_ino,
        ):
            raise Campaign265AuthorizationError("publication_parent_replaced")
    except Exception:
        try:
            os.unlink(temporary_name, dir_fd=directory)
        except FileNotFoundError:
            pass
        if linked:
            raise Campaign265AuthorizationError(
                "v420_publication_post_link_failure_target_preserved"
            )
        raise
    finally:
        os.close(directory)


def publish_policy(
    *,
    confirm_v420_publication: bool,
    repo_root: Path = REPO_ROOT,
    bindings: Mapping[str, tuple[str, str]] = AUTHORITATIVE_BINDINGS,
    workflow_plan_builder: Callable[[], Mapping[str, Any]] = WORKFLOW.build_plan,
    recorded_at: str | None = None,
    post_publish_validator: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Publish v420 only after explicit confirmation and a fresh ready plan."""

    if not confirm_v420_publication:
        raise Campaign265AuthorizationError("explicit_v420_publication_required")
    plan = build_plan(
        repo_root=repo_root,
        bindings=bindings,
        workflow_plan_builder=workflow_plan_builder,
    )
    if plan["ready"] is not True or plan["exit_code_if_executed"] != 0:
        raise Campaign265AuthorizationError("v420_publication_plan_not_ready")

    timestamp = recorded_at or datetime.now(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
    payload = build_policy_payload(recorded_at=timestamp, bindings=bindings)
    payload_bytes = _canonical_json_bytes(payload)
    root = repo_root.absolute()
    target = root / TARGET_POLICY_RELATIVE
    if not _directory_tree_is_safe(root, target.parent):
        raise Campaign265AuthorizationError("target_parent_not_real_directory")
    if os.path.lexists(target):
        raise Campaign265AuthorizationError("v420_target_already_exists")
    _publish_exclusive(target, payload_bytes)

    target_stat = target.lstat()
    if (
        not stat.S_ISREG(target_stat.st_mode)
        or stat.S_ISLNK(target_stat.st_mode)
        or target_stat.st_nlink != 1
        or target.read_bytes() != payload_bytes
    ):
        raise Campaign265AuthorizationError("published_v420_identity_or_bytes_invalid")
    if post_publish_validator is not None and post_publish_validator() is not True:
        raise Campaign265AuthorizationError("published_v420_not_accepted_by_workflow")
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign265_v420_authorization_publication_result",
        "status": "v420_published_real_run_still_requires_separate_explicit_confirm_run",
        "target_policy": str(TARGET_POLICY_RELATIVE),
        "target_policy_sha256": file_sha256(target),
        "recorded_at": timestamp,
        "credential_file_or_environment_inspected": False,
        "credential_value_or_digest_read": False,
        "provider_module_imported_or_client_created": False,
        "provider_request_issued": False,
        "candidate_comparator_price_or_return_value_read": False,
        "attempt_intent_or_journal_created": False,
        "real_run_executed": False,
        "next_required_command": (
            "scripts/a_share_three_day_walkforward_campaign265_source_acceptance_workflow.py plan"
        ),
        "later_real_run_requires_separate_operator_command": (
            "scripts/a_share_three_day_walkforward_campaign265_source_acceptance_workflow.py "
            "run --confirm-run"
        ),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    publish = subparsers.add_parser("publish")
    publish.add_argument("--confirm-v420-publication", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    confirmed_publication_attempted = bool(
        arguments.command == "publish"
        and getattr(arguments, "confirm_v420_publication", False)
    )
    try:
        if arguments.command == "plan":
            result = build_plan()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return int(result["exit_code_if_executed"])
        if arguments.command == "publish":
            result = publish_policy(
                confirm_v420_publication=bool(arguments.confirm_v420_publication),
                post_publish_validator=WORKFLOW._run_authorized,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
    except (Campaign265AuthorizationError, OSError, ValueError) as error:
        print(
            json.dumps(
                {
                    "status": "blocked_fail_closed",
                    "error_code": str(error),
                    "credential_file_or_environment_inspected": False,
                    "provider_request_issued": False,
                    "filesystem_write_performed": (
                        None if confirmed_publication_attempted else False
                    ),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    raise Campaign265AuthorizationError("unsupported_command")


if __name__ == "__main__":
    raise SystemExit(main())
