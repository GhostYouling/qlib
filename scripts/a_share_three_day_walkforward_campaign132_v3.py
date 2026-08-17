#!/usr/bin/env python3
"""Campaign132 v3 recovery with a complete audited design-interface shim."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from scripts import a_share_three_day_walkforward_campaign132_v2 as frozen_v2

frozen_v1 = frozen_v2.frozen_v1
REPO_ROOT = Path(__file__).resolve().parents[1]
FROZEN_V2_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign132_v2.py"
FROZEN_V2_RUNNER_SHA256 = (
    "58743be5f89226939c7fa79fe7fa30cf953d01b4c5ed924e2dd35e805002559f"
)
V3_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_132_development_implementation_freeze_v3_20260814.json"
)
V3_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign132_v3.py"
)
V3_OUTPUT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_132/walkforward_v3"
)
V2_FAILURE = (
    "docs/a_share_three_day_walkforward_campaign_132_v2_development_support_state_failure_20260814.json",
    "1ac48281f2bcafb44799349b5cef45f807b695532bb85ffcbd3ee886c1186e93",
)


def support_state(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Reproduce the frozen design builder's exact row-support calculation."""
    values = np.asarray(matrix)
    if values.ndim != 2 or values.shape[1] != frozen_v1.design.FEATURE_COUNT:
        raise frozen_v1.Campaign132Error("Campaign132 v3 support input shape changed")
    finite_count = np.isfinite(values).sum(axis=1).astype(np.uint8)
    eligible = finite_count >= frozen_v1.design.MINIMUM_FINITE_COMPONENTS
    return finite_count, eligible


def validate_v3_implementation_freeze() -> dict[str, object]:
    record = frozen_v1.load_json(V3_IMPLEMENTATION_FREEZE)
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign132_development_implementation_freeze_v3"
        and record.get("status")
        == "frozen_before_first_campaign132_v3_model_fit_and_return_open"
        and record.get("revision") == 3
        and (record.get("protocol") or {}).get("sha256") == frozen_v1.PROTOCOL_SHA256
        and (record.get("design_manifest") or {}).get("sha256")
        == frozen_v1.DESIGN_MANIFEST_SHA256
        and (record.get("design_audit") or {}).get("sha256")
        == frozen_v1.DESIGN_AUDIT_SHA256
        and (record.get("frozen_v1_runner") or {}).get("sha256")
        == frozen_v2.FROZEN_V1_RUNNER_SHA256
        and (record.get("frozen_v2_runner") or {}).get("sha256")
        == FROZEN_V2_RUNNER_SHA256
        and (record.get("runner") or {}).get("sha256")
        == frozen_v1.file_sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256")
        == frozen_v1.file_sha256(V3_TEST_PATH)
        and record.get("v1_and_v2_training_or_validation_returns_may_have_been_read")
        is True
        and record.get("v1_and_v2_model_fit_performed") is False
        and record.get("v3_model_fit_before_freeze") is False
        and record.get("v3_training_or_validation_return_read_before_freeze") is False
        and record.get("lockbox_2024_2025_return_read_before_freeze") is False
        and record.get("candidate49_ledgers_changed_before_freeze") is False
    ):
        raise frozen_v1.Campaign132Error(
            "Campaign132 v3 development implementation freeze changed"
        )
    return record


def configure_runtime() -> None:
    """Apply the complete audited shim and redirect all mutable run artifacts."""
    frozen_v1.require_file(
        FROZEN_V2_RUNNER,
        FROZEN_V2_RUNNER_SHA256,
        "Campaign132 frozen v2 runner",
    )
    frozen_v2.configure_runtime()
    frozen_v1.design.support_state = support_state
    frozen_v1.DEFAULT_IMPLEMENTATION_FREEZE = V3_IMPLEMENTATION_FREEZE
    frozen_v1.DEFAULT_OUTPUT_ROOT = V3_OUTPUT_ROOT
    frozen_v1.TEST_PATH = V3_TEST_PATH
    frozen_v1._implementation_freeze = validate_v3_implementation_freeze
    if V2_FAILURE not in frozen_v1.INFRASTRUCTURE_FAILURES:
        frozen_v1.INFRASTRUCTURE_FAILURES = (
            *frozen_v1.INFRASTRUCTURE_FAILURES,
            V2_FAILURE,
        )
    frozen_v1.__file__ = str(Path(__file__).resolve())


def main() -> int:
    configure_runtime()
    return frozen_v1.main()


if __name__ == "__main__":
    raise SystemExit(main())
