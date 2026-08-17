#!/usr/bin/env python3
"""Resume Campaign063 with the exact frozen manifest namespace bindings.

The launcher first installs the frozen zero-row compatibility boundary, then
injects only six already-frozen constants/modules required by the inner atomic
publication function. No extractor, candidate computation, manifest validator,
file byte, formula, direction, or gate is changed.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign063_empty_partition_repair as empty_repair


core = empty_repair.core
REPO_ROOT = Path(__file__).resolve().parents[1]
EMPTY_REPAIR_RUNNER = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign063_empty_partition_repair.py"
)
EMPTY_REPAIR_RUNNER_SHA256 = "a158a4b1f7dd4531a7da17b16cf1f9ea77e10f973a5a94155c9ea8fd4ddf81f7"
EMPTY_REPAIR_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_063_empty_partition_repair_freeze_20260805.json"
)
EMPTY_REPAIR_FREEZE_SHA256 = "030397749f6a4fd44bd814430fd4f7afb3304762103bd0893b4b0e78f6444e51"
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_063_manifest_namespace_failure_20260805.json"
)
FAILURE_RECORD_SHA256 = "6e555d9c9856fbda1f890051c0f97ddc6ae24bfda09c8a8910dd163de4a12a0a"

FROZEN_NAMESPACE_BINDINGS: dict[str, Any] = {
    "campaign004": core.campaign031,
    "MARKET_BENCHMARK_MANIFEST_SHA256": core.MOMENT_MANIFEST_SHA256,
    "MARKET_BENCHMARK_BYTE_SHA256": core.MOMENT_BYTE_SHA256,
    "MARKET_BENCHMARK_FRAME_SHA256": core.MOMENT_FRAME_SHA256,
    "MINIMUM_LEAVE_ONE_OUT_PEERS": core.MINIMUM_LEAVE_ONE_OUT_PEERS,
    "MINIMUM_INFORMATIVE_POSITIONS": core.ADJACENT_STATE_PAIR_COUNT,
}


class Campaign063ManifestNamespaceRepairError(RuntimeError):
    """Fail-closed Campaign063 publication-namespace repair error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected_sha256:
        raise Campaign063ManifestNamespaceRepairError(f"{label} changed: {path}")


def verify_repair_bindings() -> dict[str, Any]:
    _require_file(
        EMPTY_REPAIR_RUNNER,
        EMPTY_REPAIR_RUNNER_SHA256,
        "empty-partition repair runner",
    )
    _require_file(
        EMPTY_REPAIR_FREEZE,
        EMPTY_REPAIR_FREEZE_SHA256,
        "empty-partition repair freeze",
    )
    _require_file(FAILURE_RECORD, FAILURE_RECORD_SHA256, "immutable failure record")
    empty_result = empty_repair.verify_repair_bindings()
    expected_names = {
        "campaign004",
        "MARKET_BENCHMARK_MANIFEST_SHA256",
        "MARKET_BENCHMARK_BYTE_SHA256",
        "MARKET_BENCHMARK_FRAME_SHA256",
        "MINIMUM_LEAVE_ONE_OUT_PEERS",
        "MINIMUM_INFORMATIVE_POSITIONS",
    }
    if set(FROZEN_NAMESPACE_BINDINGS) != expected_names:
        raise Campaign063ManifestNamespaceRepairError(
            "Campaign063 publication namespace set changed"
        )
    return {
        **empty_result,
        "empty_repair_runner_sha256": EMPTY_REPAIR_RUNNER_SHA256,
        "empty_repair_freeze_sha256": EMPTY_REPAIR_FREEZE_SHA256,
        "manifest_namespace_failure_sha256": FAILURE_RECORD_SHA256,
        "injected_names": sorted(expected_names),
    }


def install_repair() -> dict[str, Any]:
    result = verify_repair_bindings()
    empty_repair.install_repair()
    original_extract = core._engine["extract_amount_profiles"]
    original_compute = core._engine["compute_output_frame"]
    original_validate = core._engine["_validate_manifest"]
    for name, value in FROZEN_NAMESPACE_BINDINGS.items():
        current = core._engine.get(name)
        if current is not None and current is not value and current != value:
            raise Campaign063ManifestNamespaceRepairError(
                f"Campaign063 generated namespace already has a conflicting {name}"
            )
        core._engine[name] = value
    if (
        core._engine["extract_amount_profiles"] is not original_extract
        or core._engine["compute_output_frame"] is not original_compute
        or core._engine["_validate_manifest"] is not original_validate
    ):
        raise Campaign063ManifestNamespaceRepairError(
            "Campaign063 computation boundary changed during namespace repair"
        )
    return result


def main() -> int:
    install_repair()
    return core.main()


if __name__ == "__main__":
    raise SystemExit(main())
