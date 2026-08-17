#!/usr/bin/env python3
"""Run Campaign061 audit with its frozen [0,1] compatibility attributes."""

from __future__ import annotations

import hashlib
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign061_no_return_audit as audit


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign061_no_return_audit.py"
AUDIT_RUNNER_SHA256 = "afea274393bef9fd2fe59747f0437fad2fbfef604cfe2a4f689822d83d6d6d43"
AUDIT_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_061_no_return_audit_implementation_freeze_20260805.json"
AUDIT_FREEZE_SHA256 = "5a12d622509f6a681d17b8da1987b1b894a00cd278d2452c77370f49bc6cde2a"
FAILURE_RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_061_no_return_audit_range_binding_failure_20260805.json"
FAILURE_RECORD_SHA256 = "17832406a794559835cb1950c70afec58b6f6d97461f3c97fe45df38bdad73bf"
SNAPSHOT_BINDING = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_061_feature_snapshot_binding_20260805.json"
SNAPSHOT_BINDING_SHA256 = "232117b95fe4ff426c8ca6a4742f647d53a0697f9a4497479ef557fe59d919ce"
ATTEMPT_LEDGER = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_061/research_attempt_ledger_v2.json"
ATTEMPT_LEDGER_SHA256 = "32a68ce593c366274dccb2797aae77ecda9689b35f0f242653230647a4496672"


class Campaign061NoReturnAuditRangeRepairError(RuntimeError):
    """Fail-closed range-attribute adapter error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected_sha256:
        raise Campaign061NoReturnAuditRangeRepairError(f"{label} changed: {path}")


def verify_repair_bindings() -> dict[str, str]:
    _require_file(AUDIT_RUNNER, AUDIT_RUNNER_SHA256, "frozen audit runner")
    _require_file(AUDIT_FREEZE, AUDIT_FREEZE_SHA256, "frozen audit record")
    _require_file(FAILURE_RECORD, FAILURE_RECORD_SHA256, "immutable failure record")
    _require_file(SNAPSHOT_BINDING, SNAPSHOT_BINDING_SHA256, "snapshot binding")
    _require_file(ATTEMPT_LEDGER, ATTEMPT_LEDGER_SHA256, "append-only ledger")
    if audit.FACTOR_NAME != "intraday_day_over_day_realized_variance_stability_238b":
        raise Campaign061NoReturnAuditRangeRepairError("Campaign061 factor changed")
    frozen_range = audit.candidate.FACTOR_RANGES.get(audit.FACTOR_NAME)
    if tuple(frozen_range or ()) != (0.0, 1.0):
        raise Campaign061NoReturnAuditRangeRepairError(
            "Campaign061 frozen candidate range changed"
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
            raise Campaign061NoReturnAuditRangeRepairError(
                f"Campaign061 {name} was already changed"
            )
        setattr(audit.candidate, name, expected)
    return result


def main() -> int:
    install_repair()
    return audit.main()


if __name__ == "__main__":
    raise SystemExit(main())
