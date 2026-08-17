#!/usr/bin/env python3
"""Run Campaign063 no-return audit with its exact frozen factor range registered."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign063_no_return_audit as core


REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign063_no_return_audit.py"
CORE_RUNNER_SHA256 = "86e1b87fe72ff4ffc54da36a40cb573a3c0ee51b143799bdd063020a749f7f4c"
CORE_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_063_no_return_audit_implementation_freeze_20260805.json"
)
CORE_FREEZE_SHA256 = "39eccb5ebefa40129de2496573452edc2b23a4d8cf6f9c3a1b31aaa31efd7192"
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_063_no_return_factor_range_namespace_failure_20260805.json"
)
FAILURE_RECORD_SHA256 = "b1d79a204c583dc11daa11f967642c8f9e7a63814d3d031199fa917bcc4fa2a9"
FROZEN_FACTOR_RANGE = (0.0, 1.0)


class Campaign063NoReturnFactorRangeRepairError(RuntimeError):
    """Fail-closed Campaign063 no-return factor-range registration error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected_sha256:
        raise Campaign063NoReturnFactorRangeRepairError(f"{label} changed: {path}")


def _generic_engine() -> Any:
    return core.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()[2]


def verify_repair_bindings() -> dict[str, Any]:
    _require(CORE_RUNNER, CORE_RUNNER_SHA256, "frozen no-return runner")
    _require(CORE_FREEZE, CORE_FREEZE_SHA256, "frozen no-return implementation")
    _require(FAILURE_RECORD, FAILURE_RECORD_SHA256, "immutable range failure")
    static = core.verify_static_bindings()
    if core.candidate.FACTOR_RANGES.get(core.FACTOR_NAME) != FROZEN_FACTOR_RANGE:
        raise Campaign063NoReturnFactorRangeRepairError(
            "Campaign063 module factor range changed"
        )
    return {
        "core_runner_sha256": CORE_RUNNER_SHA256,
        "core_freeze_sha256": CORE_FREEZE_SHA256,
        "failure_record_sha256": FAILURE_RECORD_SHA256,
        "candidate_manifest_sha256": static["candidate_manifest_sha256"],
        "factor": core.FACTOR_NAME,
        "frozen_factor_range": list(FROZEN_FACTOR_RANGE),
    }


def install_repair() -> dict[str, Any]:
    result = verify_repair_bindings()
    engine = _generic_engine()
    original_loader = engine.load_factor_frame
    original_coverage = engine.coverage_and_capacity
    current = engine.FACTOR_RANGES.get(core.FACTOR_NAME)
    if current is not None and tuple(current) != FROZEN_FACTOR_RANGE:
        raise Campaign063NoReturnFactorRangeRepairError(
            "Campaign063 generic factor range already conflicts"
        )
    engine.FACTOR_RANGES[core.FACTOR_NAME] = FROZEN_FACTOR_RANGE
    if (
        engine.load_factor_frame is not original_loader
        or engine.coverage_and_capacity is not original_coverage
    ):
        raise Campaign063NoReturnFactorRangeRepairError(
            "Campaign063 generic audit functions changed during range repair"
        )
    return result


def main() -> int:
    install_repair()
    return core.main()


if __name__ == "__main__":
    raise SystemExit(main())
