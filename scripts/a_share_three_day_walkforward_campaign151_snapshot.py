#!/usr/bin/env python3
"""Metadata-only plan gate and confirmed snapshot launcher for Campaign151.

``plan`` validates only frozen JSON/text metadata, file fingerprints, output
root exclusivity, a non-blocking process lock, and disk capacity.  It never
opens a Parquet/NPZ payload, a provider credential, or a network connection.
``build`` repeats the same plan in-process and calls the separately frozen
builder only when the plan is ready and ``--confirm-build`` is present.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign151_features as features,
)


DEFAULT_DATA_ROOT = features.DEFAULT_DATA_ROOT
DEFAULT_ACTIVATION_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_151_snapshot_runner_activation_v3_20260815.json"
)
PLAN_LAUNCH_FAILURE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_151_snapshot_plan_launch_failure_20260815.json"
)
PLAN_LAUNCH_FAILURE_SHA256 = (
    "3e1b1958d6584311f1c3e45571cf8d183448a8a406e274e7f36a68dd420076ef"
)
BUILDER_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_151_source_bound_builder_implementation_freeze_v2_20260815.json"
)
BUILDER_IMPLEMENTATION_FREEZE_SHA256 = (
    "1574ee3166597a2af44967b5f14239b8febbffb474e799c3d12d95c481927180"
)
BUILDER_MODULE_PATH = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign151_features.py"
)
BUILDER_MODULE_SHA256 = (
    "c808cfc180855a616237be914ade00c45fc217804406fce947d0391c288defdf"
)
BUILDER_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign151_features.py"
)
BUILDER_TEST_SHA256 = "f51e1971c511f2f44dc9c32f2e4ce0ba88a06692dd4ad689f465205e4688b907"
STATE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_iteration_status_20260815_campaign151_formula_frozen_v2.json"
)
STATE_SHA256 = "b11c239e9559283b6c44912bbc6afb0e64eb9bde02d3d913b25325e47eb44cc9"
POLICY_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v205_20260815.json"
)
POLICY_SHA256 = "e8a45201021392d36cd5af61409719619fbfec8f2c31609490ca231a54974b59"
FORMULA_VALIDATION_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_151_formula_frozen_validation_20260815.json"
)
FORMULA_VALIDATION_SHA256 = (
    "52ab888a7dfbedd68b7b80ea4c031b931709fcd3b15d96a3f049a527b02a19f6"
)
SIGNAL_LEDGER_PATH = (
    REPO_ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
SIGNAL_LEDGER_SHA256 = (
    "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
)
EXECUTION_LEDGER_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
EXECUTION_LEDGER_SHA256 = (
    "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
)
LOCK_NAME = ".a_share_three_day_walkforward_campaign151.lock"
MINIMUM_FREE_BYTES = features.MINIMUM_FREE_BYTES


class Campaign151SnapshotPlanError(RuntimeError):
    """Raised when a frozen plan or launch invariant is not satisfied."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if path.is_symlink() or not path.is_file() or _sha256(path) != expected_sha256:
        raise Campaign151SnapshotPlanError(f"{label} fingerprint changed: {path}")


def _resolve_repository_path(value: str) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def _validate_activation(path: Path) -> dict[str, Any]:
    target = path.expanduser().resolve()
    if target != DEFAULT_ACTIVATION_RECORD.resolve():
        raise Campaign151SnapshotPlanError("Campaign151 activation record path changed")
    if target.is_symlink() or not target.is_file():
        raise Campaign151SnapshotPlanError("Campaign151 activation record is absent")
    activation = json.loads(target.read_text(encoding="utf-8"))
    bindings = activation.get("authoritative_inputs") or {}
    expected = {
        "plan_runner": (Path(__file__).resolve(), None),
        "plan_runner_test": (
            REPO_ROOT
            / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign151_snapshot.py",
            None,
        ),
        "plan_launch_failure": (PLAN_LAUNCH_FAILURE, PLAN_LAUNCH_FAILURE_SHA256),
        "builder_implementation_freeze": (
            BUILDER_IMPLEMENTATION_FREEZE,
            BUILDER_IMPLEMENTATION_FREEZE_SHA256,
        ),
        "source_bound_builder": (BUILDER_MODULE_PATH, BUILDER_MODULE_SHA256),
        "source_bound_builder_test": (BUILDER_TEST_PATH, BUILDER_TEST_SHA256),
        "campaign151_state_v2": (STATE_PATH, STATE_SHA256),
        "numeric_policy_v205": (POLICY_PATH, POLICY_SHA256),
        "formula_frozen_validation": (
            FORMULA_VALIDATION_PATH,
            FORMULA_VALIDATION_SHA256,
        ),
    }
    if not (
        activation.get("kind")
        == "a_share_three_day_walkforward_campaign151_snapshot_runner_activation"
        and activation.get("status")
        == "runner_and_tests_frozen_before_campaign151_historical_values"
        and activation.get("plan_contract", {}).get("metadata_only") is True
        and activation.get("plan_contract", {}).get("parquet_or_npz_opened") is False
        and activation.get("plan_contract", {}).get("ready_true_and_exit_zero_required")
        is True
        and activation.get("build_contract", {}).get("confirmed_build_required") is True
        and activation.get("build_contract", {}).get("rerun_same_plan_in_process")
        is True
        and activation.get("research_boundary", {}).get(
            "historical_minute_source_rows_or_values_read_by_activation_or_plan"
        )
        is False
        and activation.get("research_boundary", {}).get(
            "prior_authorized_build_historical_minute_amount_values_read"
        )
        is True
        and activation.get("research_boundary", {}).get("provider_request_issued")
        is False
        and activation.get("research_boundary", {}).get("credential_loaded") is False
        and set(bindings) == set(expected)
    ):
        raise Campaign151SnapshotPlanError("Campaign151 activation semantics changed")
    for key, (expected_path, frozen_sha) in expected.items():
        binding = bindings[key]
        observed_path = _resolve_repository_path(str(binding.get("path", "")))
        if observed_path != expected_path.resolve():
            raise Campaign151SnapshotPlanError(f"{key} path changed")
        expected_sha = frozen_sha or str(binding.get("sha256", ""))
        if binding.get("sha256") != expected_sha:
            raise Campaign151SnapshotPlanError(f"{key} binding changed")
        _require_file(observed_path, expected_sha, key)
    return activation


def _validate_frozen_authority() -> None:
    _require_file(
        BUILDER_IMPLEMENTATION_FREEZE,
        BUILDER_IMPLEMENTATION_FREEZE_SHA256,
        "builder implementation freeze",
    )
    _require_file(BUILDER_MODULE_PATH, BUILDER_MODULE_SHA256, "source-bound builder")
    _require_file(BUILDER_TEST_PATH, BUILDER_TEST_SHA256, "source-bound builder test")
    _require_file(STATE_PATH, STATE_SHA256, "Campaign151 state v2")
    _require_file(POLICY_PATH, POLICY_SHA256, "numeric policy v205")
    _require_file(
        FORMULA_VALIDATION_PATH,
        FORMULA_VALIDATION_SHA256,
        "formula frozen validation",
    )
    freeze = json.loads(BUILDER_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign151_source_bound_builder_implementation_freeze"
        and freeze.get("status")
        == "corrected_builder_and_tests_frozen_after_failed_amount_only_build_before_resume"
        and freeze.get("implementation", {}).get("separate_plan_runner_still_required")
        is True
        and freeze.get("research_boundary", {}).get(
            "historical_minute_source_rows_or_values_read"
        )
        is True
        and freeze.get("research_boundary", {}).get("historical_price_values_read")
        is False
        and freeze.get("research_boundary", {}).get("peer_benchmark_values_published")
        is False
    ):
        raise Campaign151SnapshotPlanError("builder implementation freeze changed")
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if not (
        state.get("status")
        == "campaign151_formula_frozen_v2_goal_active_source_bound_builder_next"
        and state.get("frozen_library", {}).get("complete_definition_count") == 156
        and state.get("frozen_library", {}).get("eligible_numeric_comparator_count")
        == 142
        and state.get("research_boundary", {}).get(
            "campaign151_candidate_or_comparator_values_read"
        )
        is False
        and policy.get("status")
        == "campaign151_formula_frozen_publication_validation_corrected"
        and policy.get("complete_historical_feature_library", {}).get(
            "factor_definition_count"
        )
        == 156
        and policy.get("numerical_comparator_eligibility", {}).get(
            "eligible_numeric_comparator_count"
        )
        == 142
        and policy.get("numerical_comparator_eligibility", {}).get(
            "campaign151_numeric_series_appended"
        )
        is False
    ):
        raise Campaign151SnapshotPlanError(
            "Campaign151 state or policy semantics changed"
        )
    features.load_builder_protocol()


def _validate_source_metadata(data_root: Path) -> dict[str, int]:
    _raw, _joint, by_symbol = features._validate_external_manifests(data_root)
    return {
        "raw_partitions": features.EXPECTED_PARTITIONS,
        "joint_partitions": features.EXPECTED_PARTITIONS,
        "joint_rows": features.EXPECTED_ROWS,
        "symbols": len(by_symbol),
    }


def _validate_candidate49_ledgers() -> dict[str, int]:
    _require_file(SIGNAL_LEDGER_PATH, SIGNAL_LEDGER_SHA256, "Candidate49 signal ledger")
    _require_file(
        EXECUTION_LEDGER_PATH,
        EXECUTION_LEDGER_SHA256,
        "Candidate49 execution ledger",
    )
    signal = json.loads(SIGNAL_LEDGER_PATH.read_text(encoding="utf-8"))
    execution = json.loads(EXECUTION_LEDGER_PATH.read_text(encoding="utf-8"))
    if not (
        isinstance(signal.get("entries"), list)
        and len(signal["entries"]) == 0
        and isinstance(execution.get("entries"), list)
        and len(execution["entries"]) == 0
    ):
        raise Campaign151SnapshotPlanError("Candidate49 ledger entries changed")
    return {"signal_entries": 0, "execution_entries": 0}


def _partial_layout_is_metadata_safe(partial: Path) -> bool:
    if partial.is_symlink() or not partial.is_dir():
        return False
    for item in partial.rglob("*"):
        if item.is_symlink():
            return False
        if item.is_dir():
            continue
        relative = item.relative_to(partial)
        parts = relative.parts
        allowed = (
            relative == Path(".metadata/raw_amount_accumulator.npz")
            or relative == Path(features.BENCHMARK_FILENAME)
            or relative == Path("snapshot_manifest.json")
            or (
                len(parts) == 3
                and parts[0] == "partitions"
                and parts[2].endswith(".parquet")
            )
            or (
                len(parts) == 4
                and parts[:2] == (".metadata", "partitions")
                and parts[3].endswith(".json")
            )
        )
        if not allowed:
            return False
    return True


def _lock_is_available(path: Path) -> bool:
    if not path.exists():
        return True
    if path.is_symlink() or not path.is_file():
        return False
    with path.open("r", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        finally:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
    return True


def _validate_output_gate(data_root: Path) -> dict[str, Any]:
    root = data_root.expanduser().resolve()
    final = features.output_root(root)
    partial = features.partial_root(root)
    lock = root / LOCK_NAME
    if final.exists():
        raise Campaign151SnapshotPlanError(
            "Campaign151 final snapshot already exists and is never overwritten"
        )
    resume = partial.exists()
    if resume and not _partial_layout_is_metadata_safe(partial):
        raise Campaign151SnapshotPlanError(
            "Campaign151 partial root is not a recognized resumable layout"
        )
    if not _lock_is_available(lock):
        raise Campaign151SnapshotPlanError("Campaign151 build lock is held or invalid")
    free = shutil.disk_usage(root).free
    if free < MINIMUM_FREE_BYTES:
        raise Campaign151SnapshotPlanError(
            "Campaign151 data root has less than 10 GiB free"
        )
    return {
        "final_root": str(final),
        "final_root_exists": False,
        "partial_root": str(partial),
        "resume_partial": resume,
        "lock_path": str(lock),
        "lock_available": True,
        "free_bytes": free,
        "minimum_free_bytes": MINIMUM_FREE_BYTES,
    }


def plan_status(
    *,
    workers: int,
    data_root: Path = DEFAULT_DATA_ROOT,
    activation_record: Path = DEFAULT_ACTIVATION_RECORD,
) -> dict[str, Any]:
    """Return a fail-closed, zero-market-value plan record."""

    gates: dict[str, Any] = {}
    failures: list[str] = []

    def check(name: str, callable_: Any) -> None:
        try:
            evidence = callable_()
        except Exception as exc:  # Fail closed while preserving one JSON plan object.
            gates[name] = {"ready": False, "error": f"{type(exc).__name__}: {exc}"}
            failures.append(name)
        else:
            gates[name] = {"ready": True, "evidence": evidence}

    if workers < 1 or workers > 8:
        gates["workers"] = {"ready": False, "error": "workers must be between 1 and 8"}
        failures.append("workers")
    else:
        gates["workers"] = {"ready": True, "evidence": {"workers": workers}}
    check("activation", lambda: _validate_activation(activation_record))
    check(
        "frozen_authority", lambda: (_validate_frozen_authority(), {"valid": True})[1]
    )
    check("source_metadata", lambda: _validate_source_metadata(data_root))
    check("candidate49_ledgers", _validate_candidate49_ledgers)
    check("output", lambda: _validate_output_gate(data_root))
    ready = not failures
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign151_snapshot_plan",
        "status": "ready_for_confirmed_build" if ready else "not_ready",
        "ready": ready,
        "workers": workers,
        "data_root": str(data_root.expanduser().resolve()),
        "output_run_id": features.OUTPUT_RUN_ID,
        "factor_name": features.FACTOR_NAME,
        "gates": gates,
        "failed_gates": failures,
        "historical_parquet_or_npz_payload_opened_by_plan": False,
        "historical_minute_source_rows_or_values_read_by_plan": False,
        "prior_authorized_build_historical_minute_amount_values_read": True,
        "peer_benchmark_values_read_by_plan": False,
        "candidate_or_comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "credential_loaded": False,
        "provider_request_issued": False,
        "candidate49_ledgers_changed": False,
        "current_scoring_selection_sizing_positions_or_orders_performed": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan = subparsers.add_parser("plan", help="validate metadata-only build gates")
    plan.add_argument("--workers", type=int, default=4)
    build = subparsers.add_parser("build", help="run one frozen historical build")
    build.add_argument("--workers", type=int, default=4)
    build.add_argument("--confirm-build", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    plan = plan_status(workers=args.workers)
    if args.command == "plan":
        print(json.dumps(plan, ensure_ascii=False, sort_keys=True))
        return 0 if plan["ready"] else 2
    if not plan["ready"]:
        print(json.dumps(plan, ensure_ascii=False, sort_keys=True))
        return 2
    if not args.confirm_build:
        plan["ready"] = False
        plan["status"] = "not_ready"
        plan["failed_gates"] = ["confirm_build"]
        plan["gates"]["confirm_build"] = {
            "ready": False,
            "error": "--confirm-build is required",
        }
        print(json.dumps(plan, ensure_ascii=False, sort_keys=True))
        return 2
    manifest = features.build_snapshot(
        data_root=DEFAULT_DATA_ROOT,
        workers=args.workers,
        confirm_build=True,
    )
    result = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign151_snapshot_build_result",
        "status": "snapshot_published_pending_independent_validation",
        "ready_plan_repeated_in_process": True,
        "manifest_path": str(manifest),
        "manifest_sha256": _sha256(manifest),
        "provider_request_issued": False,
        "credential_loaded": False,
        "candidate49_ledgers_changed": False,
        "promotion_allowed": False,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "Campaign151SnapshotPlanError",
    "DEFAULT_ACTIVATION_RECORD",
    "DEFAULT_DATA_ROOT",
    "main",
    "plan_status",
]
