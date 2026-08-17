#!/usr/bin/env python3
"""Run Campaign097's additive total-denominator alignment repair."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from scripts import (
    a_share_three_day_walkforward_campaign097_no_return_audit_v3 as v3,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = v3.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = v3.DEFAULT_EXPERIMENT_ROOT
V3_RUNNER_SHA256 = "0e22daebbab70fc9aaa5cd1dcc1fb051a30f011e5a35e6f054c18ecfe9f804b4"
V3_IMPLEMENTATION_FREEZE_SHA256 = (
    "8171fb7e6fa43b7fba7b675867e5be5800f070c378dd6f45da717beb53a73ba5"
)
V3_ACTIVATION_SHA256 = (
    "d25f59a838726bc8aa0824e76be1b55ae4ca93e99a4529a8ecc6fde4fdbcc11c"
)
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_097_no_return_audit_total_denominator_alignment_failure_20260807.json"
)
FAILURE_RECORD_SHA256 = (
    "3c7bb1611eff37ccb8602e3b0a9515c0e4e24eeb8c0a4f2e0865acb2981c7d95"
)
AUDIT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_097_no_return_audit_implementation_freeze_v4_20260807.json"
)
AUDIT_ACTIVATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_097_no_return_audit_activation_binding_v4_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign097_no_return_audit_v4.py"
)


class Campaign097NoReturnAuditV4Error(RuntimeError):
    """Fail-closed Campaign097 v4 no-return audit error."""


def _sha256(path: Path) -> str:
    return v3._sha256(path)


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign097NoReturnAuditV4Error(f"Campaign097 v4 {label} changed: {path}")


def _load_implementation_freeze() -> dict[str, Any]:
    _require(Path(v3.__file__).resolve(), V3_RUNNER_SHA256, "v3 runner")
    _require(
        v3.AUDIT_IMPLEMENTATION_FREEZE,
        V3_IMPLEMENTATION_FREEZE_SHA256,
        "v3 implementation freeze",
    )
    _require(v3.AUDIT_ACTIVATION_BINDING, V3_ACTIVATION_SHA256, "v3 activation")
    _require(FAILURE_RECORD, FAILURE_RECORD_SHA256, "v3 failure record")
    if not AUDIT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign097NoReturnAuditV4Error("v4 implementation freeze is absent")
    record = json.loads(AUDIT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign097_no_return_audit_implementation_freeze_v4"
        and record.get("status")
        == "total_denominator_alignment_repair_frozen_before_campaign097_coverage_comparison_or_return_values"
        and (record.get("v4_audit_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("v4_tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and (record.get("v3_failure_record") or {}).get("sha256")
        == FAILURE_RECORD_SHA256
        and record.get("repair_scope")
        == "left-align candidate observations onto every frozen quality-listing denominator key and retain unmatched rows as NaN"
        and record.get("identity_missing_count_computed_before_v4_freeze") is False
        and record.get("coverage_or_capacity_metrics_computed_before_v4_freeze")
        is False
        and record.get("comparison_values_read_before_v4_freeze") is False
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_v4_freeze"
        )
        is False
        and record.get("provider_request_issued_before_v4_freeze") is False
    ):
        raise Campaign097NoReturnAuditV4Error("v4 implementation freeze changed")
    return record


def _load_activation_binding() -> dict[str, Any]:
    _load_implementation_freeze()
    if not AUDIT_ACTIVATION_BINDING.is_file():
        raise Campaign097NoReturnAuditV4Error("v4 activation binding is absent")
    record = json.loads(AUDIT_ACTIVATION_BINDING.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign097_no_return_audit_activation_binding_v4"
        and record.get("status")
        == "total_denominator_alignment_repair_frozen_before_campaign097_coverage_comparison_or_return_values"
        and (record.get("implementation_freeze_v4") or {}).get("sha256")
        == _sha256(AUDIT_IMPLEMENTATION_FREEZE)
        and (record.get("v3_failure_record") or {}).get("sha256")
        == FAILURE_RECORD_SHA256
        and record.get("identity_missing_count_computed_before_activation") is False
        and record.get("coverage_or_capacity_metrics_computed_before_activation")
        is False
        and record.get("comparison_values_read_before_activation") is False
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_activation"
        )
        is False
        and record.get("provider_request_issued_before_activation") is False
    ):
        raise Campaign097NoReturnAuditV4Error("v4 activation binding changed")
    return record


def align_candidate_year(
    *,
    eligible_keys: np.ndarray,
    candidate_keys: np.ndarray,
    candidate_values: np.ndarray,
    year: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Left-align candidate observations to the complete frozen denominator."""

    frozen_keys = np.asarray(eligible_keys, dtype=np.int64)
    observed_keys = np.asarray(candidate_keys, dtype=np.int64)
    observed_values = np.asarray(candidate_values, dtype=np.float64)
    if not (
        year in range(2019, 2026)
        and frozen_keys.ndim == 1
        and observed_keys.ndim == 1
        and observed_values.shape == observed_keys.shape
        and len(frozen_keys) > 0
        and len(observed_keys) > 0
        and np.all(frozen_keys[1:] > frozen_keys[:-1])
        and len(np.unique(observed_keys)) == len(observed_keys)
    ):
        raise Campaign097NoReturnAuditV4Error("candidate alignment inputs changed")
    order = np.argsort(observed_keys, kind="stable")
    sorted_keys = observed_keys[order]
    positions = np.searchsorted(sorted_keys, frozen_keys, side="left")
    matched = positions < len(sorted_keys)
    matched[matched] = sorted_keys[positions[matched]] == frozen_keys[matched]
    aligned_values = np.full(len(frozen_keys), np.nan, dtype=np.float64)
    aligned_values[matched] = observed_values[order][positions[matched]]
    finite = np.isfinite(aligned_values)
    if np.any((aligned_values[finite] < -1.0) | (aligned_values[finite] > 1.0)):
        raise Campaign097NoReturnAuditV4Error("candidate values left frozen range")
    return (
        frozen_keys,
        aligned_values,
        np.full(len(frozen_keys), year, dtype=np.int64),
    )


def _run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int, confirm_run: bool
) -> Path:
    if not confirm_run:
        raise Campaign097NoReturnAuditV4Error(
            "Campaign097 v4 audit requires --confirm-run"
        )
    _load_activation_binding()
    original_alignment = v3.v2.v1.align_candidate_year
    v3.v2.v1.align_candidate_year = align_candidate_year
    try:
        path = v3._run_no_return_audit(
            data_root=data_root,
            experiment_root=experiment_root,
            workers=workers,
            confirm_run=True,
        )
    finally:
        v3.v2.v1.align_candidate_year = original_alignment
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["audit_total_denominator_alignment_repair"] = {
        "scope": "quality-listing denominator left alignment only",
        "unmatched_candidate_observation_semantics": "NaN retained in denominator before coverage",
        "v3_runner_sha256": V3_RUNNER_SHA256,
        "v3_implementation_freeze_sha256": V3_IMPLEMENTATION_FREEZE_SHA256,
        "v3_activation_binding_sha256": V3_ACTIVATION_SHA256,
        "v3_failure_record_sha256": FAILURE_RECORD_SHA256,
        "v4_implementation_freeze_sha256": _sha256(AUDIT_IMPLEMENTATION_FREEZE),
        "v4_activation_binding_sha256": _sha256(AUDIT_ACTIVATION_BINDING),
        "coverage_gate_comparator_order_or_threshold_changed": False,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def status(experiment_root: Path = DEFAULT_EXPERIMENT_ROOT) -> dict[str, Any]:
    base = v3.status(experiment_root)
    return {
        **base,
        "status": (
            "ready_for_single_v4_audit"
            if AUDIT_ACTIVATION_BINDING.is_file()
            else "v4_activation_binding_absent"
        ),
        "repair_scope": "total_denominator_left_alignment_only",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "run"))
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--confirm-run", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "status":
        print(json.dumps(status(args.experiment_root), sort_keys=True))
        return 0
    print(
        _run_no_return_audit(
            data_root=args.data_root,
            experiment_root=args.experiment_root,
            workers=args.workers,
            confirm_run=args.confirm_run,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
