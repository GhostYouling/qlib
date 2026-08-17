#!/usr/bin/env python3
"""Run Campaign060 audit with its frozen [0,1] compatibility attributes."""

from __future__ import annotations

import hashlib
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign060_no_return_audit as audit


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign060_no_return_audit.py"
AUDIT_RUNNER_SHA256 = "ecedad2aec0cf823c603001e2733411879c87d9b2522c4d09d5b6a212fa19977"
AUDIT_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_060_no_return_audit_implementation_freeze_20260805.json"
AUDIT_FREEZE_SHA256 = "864eb417bf3473f722a973eb9579fa4fb3db26caa67149950b35d10ad58b18df"
FAILURE_RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_060_no_return_audit_range_binding_failure_20260805.json"
FAILURE_RECORD_SHA256 = "03eaa09c2dfe28aa5ce3dbd539f72640903d5e8580ef5294cb11bb4534897fd3"
SNAPSHOT_BINDING = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_060_feature_snapshot_binding_20260804.json"
SNAPSHOT_BINDING_SHA256 = "6226c6381bd5b11eec41061c99e906fb736acbb70c922831bf81d9ed974682bd"
ATTEMPT_LEDGER = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_060/research_attempt_ledger_v4.json"
ATTEMPT_LEDGER_SHA256 = "1310d053b0d9c8f82454370921e5cba2b384d8093bc67c51304225f368bf42d2"


class Campaign060NoReturnAuditRangeRepairError(RuntimeError):
    """Fail-closed range-attribute adapter error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected_sha256:
        raise Campaign060NoReturnAuditRangeRepairError(f"{label} changed: {path}")


def verify_repair_bindings() -> dict[str, str]:
    _require_file(AUDIT_RUNNER, AUDIT_RUNNER_SHA256, "frozen audit runner")
    _require_file(AUDIT_FREEZE, AUDIT_FREEZE_SHA256, "frozen audit record")
    _require_file(FAILURE_RECORD, FAILURE_RECORD_SHA256, "immutable failure record")
    _require_file(SNAPSHOT_BINDING, SNAPSHOT_BINDING_SHA256, "snapshot binding")
    _require_file(ATTEMPT_LEDGER, ATTEMPT_LEDGER_SHA256, "append-only ledger")
    if audit.FACTOR_NAME != "intraday_day_over_day_directional_return_agreement_238b":
        raise Campaign060NoReturnAuditRangeRepairError("Campaign060 factor changed")
    frozen_range = audit.candidate.FACTOR_RANGES.get(audit.FACTOR_NAME)
    if tuple(frozen_range or ()) != (0.0, 1.0):
        raise Campaign060NoReturnAuditRangeRepairError(
            "Campaign060 frozen candidate range changed"
        )
    return {
        "audit_runner_sha256": AUDIT_RUNNER_SHA256,
        "audit_freeze_sha256": AUDIT_FREEZE_SHA256,
        "failure_record_sha256": FAILURE_RECORD_SHA256,
        "snapshot_binding_sha256": SNAPSHOT_BINDING_SHA256,
        "attempt_ledger_sha256": ATTEMPT_LEDGER_SHA256,
    }


def install_repair() -> dict[str, str]:
    result = verify_repair_bindings()
    for name, expected in (("LOWER_BOUND", 0.0), ("UPPER_BOUND", 1.0)):
        current = getattr(audit.candidate, name, expected)
        if current != expected:
            raise Campaign060NoReturnAuditRangeRepairError(
                f"Campaign060 {name} was already changed"
            )
        setattr(audit.candidate, name, expected)
    return result


def main() -> int:
    install_repair()
    return audit.main()


if __name__ == "__main__":
    raise SystemExit(main())
