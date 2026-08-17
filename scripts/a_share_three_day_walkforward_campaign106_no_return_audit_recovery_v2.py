#!/usr/bin/env python3
"""Recover Campaign106's no-return audit by registering comparator 132's range."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import a_share_three_day_walkforward_campaign105_features as c105
from scripts import a_share_three_day_walkforward_campaign106_no_return_audit as base


REPO_ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_RUNNER = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign106_no_return_audit.py"
)
ORIGINAL_RUNNER_SHA256 = (
    "4326a206cf1f67e7d4bf8375ea190404918d744650d794df6b48acf09a2f801a"
)
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_106_no_return_audit_failure_20260808.json"
)
FAILURE_RECORD_SHA256 = (
    "e07e26303427f6f9eaa90b8fb77553685f99aee8ec5b9f1f9dfc9db00a9f03ee"
)
RECOVERY_ACTIVATION = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_106_no_return_audit_recovery_v2_activation_20260808.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign106_no_return_audit_recovery_v2.py"
)


class Campaign106NoReturnAuditRecoveryError(RuntimeError):
    """Fail closed when the additive recovery contract changes."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign106NoReturnAuditRecoveryError(f"{label} changed: {path}")


def _register_campaign105_range(engine: Any) -> None:
    """Add only the already frozen Campaign105 [0,1] value-domain metadata."""

    ranges = dict(getattr(engine, "FACTOR_RANGES", {}))
    observed = ranges.get(c105.FACTOR_NAME)
    if observed is not None and tuple(observed) != (0.0, 1.0):
        raise Campaign106NoReturnAuditRecoveryError(
            "Campaign105 factor range conflicts with frozen [0,1]"
        )
    ranges[c105.FACTOR_NAME] = (0.0, 1.0)
    engine.FACTOR_RANGES = ranges


def _load_recovery_activation() -> dict[str, Any]:
    _require(ORIGINAL_RUNNER, ORIGINAL_RUNNER_SHA256, "original audit runner")
    _require(FAILURE_RECORD, FAILURE_RECORD_SHA256, "failure record")
    if not RECOVERY_ACTIVATION.is_file():
        raise Campaign106NoReturnAuditRecoveryError("recovery activation is absent")
    record = json.loads(RECOVERY_ACTIVATION.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign106_no_return_audit_recovery_v2_activation"
        and record.get("status")
        == "frozen_after_infrastructure_failure_before_recovery_value_reread"
        and (record.get("failed_attempt") or {}).get("sha256")
        == FAILURE_RECORD_SHA256
        and (record.get("original_runner") or {}).get("sha256")
        == ORIGINAL_RUNNER_SHA256
        and (record.get("recovery_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("synthetic_test") or {}).get("sha256") == _sha256(TEST_PATH)
        and (record.get("semantic_diff") or {}).get("only_change")
        == "register frozen Campaign105 comparator range [0,1] before load_factor_frame"
        and (record.get("semantic_diff") or {}).get("candidate_formula_changed")
        is False
        and (record.get("semantic_diff") or {}).get("candidate_direction_changed")
        is False
        and (record.get("semantic_diff") or {}).get("coverage_gate_changed") is False
        and (record.get("semantic_diff") or {}).get("comparator_order_changed") is False
        and (record.get("semantic_diff") or {}).get("uniqueness_threshold_changed")
        is False
        and (record.get("semantic_diff") or {}).get("daily_price_or_return_access_added")
        is False
        and record.get("provider_request_issued_before_recovery") is False
        and record.get("single_recovery_attempt") is True
    ):
        raise Campaign106NoReturnAuditRecoveryError(
            "recovery activation semantics changed"
        )
    return record


def _recovery_comparison_loader(**kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if (kwargs.get("coverage") or {}).get("gate_passed_before_comparison_values") is not True:
        raise Campaign106NoReturnAuditRecoveryError(
            "recovery comparison loader called before coverage pass"
        )
    context = (
        base._generated["cache_v4"].v1.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    )
    _register_campaign105_range(context[2])
    return base._load_comparisons_after_coverage(**kwargs)


def run_recovery(
    *, data_root: Path, experiment_root: Path, workers: int, confirm_run: bool = False
) -> Path:
    if not confirm_run:
        raise Campaign106NoReturnAuditRecoveryError(
            "Campaign106 recovery requires --confirm-run"
        )
    _load_recovery_activation()
    base._generated["_load_comparisons_after_coverage"] = _recovery_comparison_loader
    return base.run_no_return_audit(
        data_root=data_root,
        experiment_root=experiment_root,
        workers=workers,
        confirm_run=True,
    )


def status(experiment_root: Path = base.DEFAULT_EXPERIMENT_ROOT) -> dict[str, Any]:
    original = base.status(experiment_root)
    return {
        **original,
        "failed_attempt_record_exists": FAILURE_RECORD.is_file(),
        "recovery_activation_exists": RECOVERY_ACTIVATION.is_file(),
        "range_registration_performed_by_status": False,
        "comparator_values_reread_by_status": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "run"))
    parser.add_argument("--data-root", type=Path, default=base.DEFAULT_DATA_ROOT)
    parser.add_argument(
        "--experiment-root", type=Path, default=base.DEFAULT_EXPERIMENT_ROOT
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--confirm-run", action="store_true")
    args = parser.parse_args()
    if args.command == "status":
        print(json.dumps(status(args.experiment_root), ensure_ascii=False, sort_keys=True))
        return 0
    print(
        run_recovery(
            data_root=args.data_root,
            experiment_root=args.experiment_root,
            workers=args.workers,
            confirm_run=args.confirm_run,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
