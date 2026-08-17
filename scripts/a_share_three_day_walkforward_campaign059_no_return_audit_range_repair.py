#!/usr/bin/env python3
"""Run Campaign059 no-return audit with exact frozen [0,1] range aliases."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign059_no_return_audit as audit


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign059_no_return_audit.py"
AUDIT_RUNNER_SHA256 = "8c24d2e973b00d9a13f98435795703d79be1eb8279565976a57d540d6ee6953b"
AUDIT_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_059_no_return_audit_implementation_freeze_20260804.json"
)
AUDIT_FREEZE_SHA256 = "7c7f696f02e5c0ca8a3aebefaa6a5b8f6d59535e9aee318d253e94127238b11b"
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_059_no_return_audit_candidate_range_binding_failure_20260804.json"
)
FAILURE_RECORD_SHA256 = "2bacf172ffdd7414db6de5c9be274f9db23bd54b9480fc542fdba32cfa75f932"
SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_059_feature_snapshot_binding_20260804.json"
)
SNAPSHOT_BINDING_SHA256 = "9d8c277c68531ea2b2155e983c633d36c197ecb47109bb9043f3e162ad445d9a"
FROZEN_RANGE_ALIASES = {"LOWER_BOUND": 0.0, "UPPER_BOUND": 1.0}


class Campaign059NoReturnAuditRangeRepairError(RuntimeError):
    """Fail-closed additive candidate-range alias repair error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected_sha256:
        raise Campaign059NoReturnAuditRangeRepairError(f"{label} changed: {path}")


def verify_repair_bindings() -> dict[str, Any]:
    _require_file(AUDIT_RUNNER, AUDIT_RUNNER_SHA256, "frozen audit runner")
    _require_file(AUDIT_FREEZE, AUDIT_FREEZE_SHA256, "frozen audit record")
    _require_file(FAILURE_RECORD, FAILURE_RECORD_SHA256, "immutable failure record")
    _require_file(SNAPSHOT_BINDING, SNAPSHOT_BINDING_SHA256, "snapshot binding")
    if (
        audit.FACTOR_NAME != "intraday_market_directional_sign_agreement_238m"
        or audit.candidate.FACTOR_RANGES.get(audit.FACTOR_NAME) != (0.0, 1.0)
        or set(FROZEN_RANGE_ALIASES) != {"LOWER_BOUND", "UPPER_BOUND"}
    ):
        raise Campaign059NoReturnAuditRangeRepairError(
            "Campaign059 frozen range or factor changed"
        )
    return {
        "audit_runner_sha256": AUDIT_RUNNER_SHA256,
        "audit_freeze_sha256": AUDIT_FREEZE_SHA256,
        "failure_record_sha256": FAILURE_RECORD_SHA256,
        "snapshot_binding_sha256": SNAPSHOT_BINDING_SHA256,
        "range_aliases": dict(FROZEN_RANGE_ALIASES),
    }


def install_repair() -> dict[str, Any]:
    result = verify_repair_bindings()
    original_load = audit._audit_engine["load_candidate_frame"]
    original_append = audit._audit_engine["_append_all_prior_comparisons"]
    original_run = audit._audit_engine["run_no_return_audit"]
    for name, value in FROZEN_RANGE_ALIASES.items():
        current = getattr(audit.candidate, name, None)
        if current is not None and current != value:
            raise Campaign059NoReturnAuditRangeRepairError(
                f"Campaign059 candidate already has conflicting {name}"
            )
        setattr(audit.candidate, name, value)
    if (
        audit._audit_engine["load_candidate_frame"] is not original_load
        or audit._audit_engine["_append_all_prior_comparisons"] is not original_append
        or audit._audit_engine["run_no_return_audit"] is not original_run
    ):
        raise Campaign059NoReturnAuditRangeRepairError(
            "Campaign059 audit computation changed during range repair"
        )
    return result


def main() -> int:
    install_repair()
    return audit.main()


if __name__ == "__main__":
    raise SystemExit(main())
