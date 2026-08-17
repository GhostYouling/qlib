#!/usr/bin/env python3
"""Resume Campaign059 with the exact frozen manifest namespace bindings.

The launcher first installs the frozen zero-row compatibility boundary, then
injects only six already-frozen constants/modules required by the inner atomic
publication function.  No partition extractor, candidate computation, manifest
validator, file byte, formula, direction, or gate is changed.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign059_empty_partition_repair as empty_repair


core = empty_repair.core
REPO_ROOT = Path(__file__).resolve().parents[1]
EMPTY_REPAIR_RUNNER = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign059_empty_partition_repair.py"
)
EMPTY_REPAIR_RUNNER_SHA256 = "62fdaa5811a5952f4d0aceb3f114093c224e1d387f9bb8f66e48d4af9d8918cf"
EMPTY_REPAIR_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_059_empty_partition_repair_freeze_20260804.json"
)
EMPTY_REPAIR_FREEZE_SHA256 = "33cc38507b15f14bfa145b461b9aba9b2556451a53db13df8aa4115a3445cb42"
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_059_manifest_namespace_failure_20260804.json"
)
FAILURE_RECORD_SHA256 = "16eba8a741b53ab578aefcf0b01db568f9d6278303fe53c7d87f05af80033a46"

FROZEN_NAMESPACE_BINDINGS: dict[str, Any] = {
    "campaign004": core.campaign004,
    "MARKET_BENCHMARK_MANIFEST_SHA256": core.MARKET_BENCHMARK_MANIFEST_SHA256,
    "MARKET_BENCHMARK_BYTE_SHA256": core.MARKET_BENCHMARK_BYTE_SHA256,
    "MARKET_BENCHMARK_FRAME_SHA256": core.MARKET_BENCHMARK_FRAME_SHA256,
    "MINIMUM_LEAVE_ONE_OUT_PEERS": core.MINIMUM_LEAVE_ONE_OUT_PEERS,
    "MINIMUM_INFORMATIVE_POSITIONS": core.MINIMUM_INFORMATIVE_POSITIONS,
}


class Campaign059ManifestNamespaceRepairError(RuntimeError):
    """Fail-closed Campaign059 publication-namespace repair error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected_sha256:
        raise Campaign059ManifestNamespaceRepairError(f"{label} changed: {path}")


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
        raise Campaign059ManifestNamespaceRepairError(
            "Campaign059 publication namespace set changed"
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
            raise Campaign059ManifestNamespaceRepairError(
                f"Campaign059 generated namespace already has a conflicting {name}"
            )
        core._engine[name] = value
    if (
        core._engine["extract_amount_profiles"] is not original_extract
        or core._engine["compute_output_frame"] is not original_compute
        or core._engine["_validate_manifest"] is not original_validate
    ):
        raise Campaign059ManifestNamespaceRepairError(
            "Campaign059 computation boundary changed during namespace repair"
        )
    return result


def main() -> int:
    install_repair()
    return core.main()


if __name__ == "__main__":
    raise SystemExit(main())
