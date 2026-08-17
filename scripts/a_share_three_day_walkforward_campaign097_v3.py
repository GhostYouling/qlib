#!/usr/bin/env python3
"""Run Campaign097 with the exact active compact-loader namespace repair."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from scripts import a_share_three_day_walkforward_campaign097_v2 as v2


REPO_ROOT = Path(__file__).resolve().parents[1]
V2_RUNNER_SHA256 = "3fa9185b13455e0d9d5cfce1aec3a22b0ef9a4ba2c21fa6846070e8aad322df3"
V2_IMPLEMENTATION_FREEZE_SHA256 = (
    "7ec30b2cf9728102c1adcc4d7064d37a0616e4fcb98a1f49a91157951120b5dd"
)
V2_ACTIVATION_SHA256 = (
    "88a49b0c3781d12f9609286468ccdfdd87961ff12820e3a2ac94a3970d44fdda"
)
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_097_development_v2_outer_namespace_failure_20260807.json"
)
FAILURE_RECORD_SHA256 = (
    "8ce0c30a9d8522bbd4fdda9b6938ca45b50915eec527a1209c3a4c8ccbc3554c"
)
FAILED_LEDGER_SHA256 = (
    "8b22da7d62c831fd03294ab3b3a60ea7a339cf20ce5d824bb3d09c95de7b4fa2"
)
IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_097_development_implementation_freeze_v3_20260807.json"
)
ACTIVATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_097_development_activation_binding_v3_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign097_development_v3.py"
)


class Campaign097DevelopmentV3Error(RuntimeError):
    """Fail-closed Campaign097 development v3 error."""


def _sha256(path: Path) -> str:
    return v2._sha256(path)


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign097DevelopmentV3Error(
            f"Campaign097 development v3 {label} changed: {path}"
        )


def _load_implementation_freeze() -> dict[str, Any]:
    _require(Path(v2.__file__).resolve(), V2_RUNNER_SHA256, "v2 runner")
    _require(
        v2.AUDIT_IMPLEMENTATION_FREEZE,
        V2_IMPLEMENTATION_FREEZE_SHA256,
        "v2 implementation freeze",
    )
    _require(
        v2.AUDIT_ACTIVATION_BINDING,
        V2_ACTIVATION_SHA256,
        "v2 activation binding",
    )
    _require(FAILURE_RECORD, FAILURE_RECORD_SHA256, "v2 failure record")
    if not IMPLEMENTATION_FREEZE.is_file():
        raise Campaign097DevelopmentV3Error("v3 implementation freeze is absent")
    record = json.loads(IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign097_development_implementation_freeze_v3"
        and record.get("status")
        == "active_loader_namespace_repair_frozen_after_two_append_only_failures_before_complete_development_trial"
        and (record.get("v3_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("v3_tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and (record.get("v2_failure_record") or {}).get("sha256")
        == FAILURE_RECORD_SHA256
        and record.get("repair_scope")
        == "patch only the decorated compact contextmanager wrapped-generator globals loader binding"
        and record.get("complete_development_trial_count_before_v3_freeze") == 0
        and record.get("stress_2024_2025_read_before_v3_freeze") is False
    ):
        raise Campaign097DevelopmentV3Error("v3 implementation freeze changed")
    return record


def _load_activation_binding() -> dict[str, Any]:
    _load_implementation_freeze()
    if not ACTIVATION_BINDING.is_file():
        raise Campaign097DevelopmentV3Error("v3 activation binding is absent")
    record = json.loads(ACTIVATION_BINDING.read_text(encoding="utf-8"))
    ledger = REPO_ROOT / str(
        (record.get("append_only_internal_ledger") or {}).get("path")
    )
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign097_development_activation_binding_v3"
        and record.get("status")
        == "active_loader_namespace_repair_frozen_after_two_append_only_failures_before_complete_development_trial"
        and (record.get("implementation_freeze_v3") or {}).get("sha256")
        == _sha256(IMPLEMENTATION_FREEZE)
        and (record.get("v2_failure_record") or {}).get("sha256")
        == FAILURE_RECORD_SHA256
        and ledger.is_file()
        and _sha256(ledger) == FAILED_LEDGER_SHA256
        and record.get("remaining_complete_development_trials_authorized") == 1
        and record.get("stress_2024_2025_authorized") is False
    ):
        raise Campaign097DevelopmentV3Error("v3 activation binding changed")
    return record


def active_loader_namespace() -> dict[str, Any]:
    wrapper = v2.v1._temporary_compact_factor_loader
    wrapped = getattr(wrapper, "__wrapped__", None)
    if wrapped is None or wrapped.__globals__ is not v2.v1.run_development.__globals__:
        raise Campaign097DevelopmentV3Error(
            "active compact loader namespace identity changed"
        )
    return wrapped.__globals__


@contextmanager
def _temporary_active_loader_repair() -> Iterator[None]:
    namespace = active_loader_namespace()
    original = namespace.get("_load_compact_factor_panel")
    if original is None or original is v2._load_compact_factor_panel:
        raise Campaign097DevelopmentV3Error("active loader was already repaired")
    namespace["_load_compact_factor_panel"] = v2._load_compact_factor_panel
    try:
        yield
    finally:
        namespace["_load_compact_factor_panel"] = original


def main() -> int:
    _load_activation_binding()
    with _temporary_active_loader_repair():
        return v2.v1.main()


if __name__ == "__main__":
    raise SystemExit(main())
