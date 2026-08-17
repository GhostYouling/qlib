#!/usr/bin/env python3
"""Campaign132 v2 recovery: bind the frozen v1 runner and repair one helper alias."""

from __future__ import annotations

from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign132 as frozen_v1

REPO_ROOT = Path(__file__).resolve().parents[1]
FROZEN_V1_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign132.py"
FROZEN_V1_RUNNER_SHA256 = (
    "ba181f6c154cfde2066e501e7a67bc68f327ecc6ecc146dd8747cbcfa78e1a93"
)
V2_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_132_development_implementation_freeze_v2_20260814.json"
)
V2_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign132_v2.py"
)
V2_OUTPUT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_132/walkforward_v2"
)
V1_FAILURE = (
    "docs/a_share_three_day_walkforward_campaign_132_v1_development_component_columns_failure_20260814.json",
    "deda1ea8d0db7b194f4c2cdec46670a1a72299a7c40aa454a84fdff6aa0cd684",
)


def validate_v2_implementation_freeze() -> dict[str, object]:
    """Validate a truthful v2 freeze after the preserved v1 return-open failure."""
    record = frozen_v1.load_json(V2_IMPLEMENTATION_FREEZE)
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign132_development_implementation_freeze_v2"
        and record.get("status")
        == "frozen_before_first_campaign132_v2_model_fit_and_return_open"
        and record.get("revision") == 2
        and (record.get("protocol") or {}).get("sha256") == frozen_v1.PROTOCOL_SHA256
        and (record.get("design_manifest") or {}).get("sha256")
        == frozen_v1.DESIGN_MANIFEST_SHA256
        and (record.get("design_audit") or {}).get("sha256")
        == frozen_v1.DESIGN_AUDIT_SHA256
        and (record.get("frozen_v1_runner") or {}).get("sha256")
        == FROZEN_V1_RUNNER_SHA256
        and (record.get("runner") or {}).get("sha256")
        == frozen_v1.file_sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256")
        == frozen_v1.file_sha256(V2_TEST_PATH)
        and record.get("v1_training_or_validation_returns_may_have_been_read") is True
        and record.get("v1_model_fit_performed") is False
        and record.get("v2_model_fit_before_freeze") is False
        and record.get("v2_training_or_validation_return_read_before_freeze") is False
        and record.get("lockbox_2024_2025_return_read_before_freeze") is False
        and record.get("candidate49_ledgers_changed_before_freeze") is False
    ):
        raise frozen_v1.Campaign132Error(
            "Campaign132 v2 development implementation freeze changed"
        )
    return record


def configure_runtime() -> None:
    """Apply the sole frozen v2 repair before delegating to the v1 runner."""
    frozen_v1.require_file(
        FROZEN_V1_RUNNER,
        FROZEN_V1_RUNNER_SHA256,
        "Campaign132 frozen v1 runner",
    )
    if not hasattr(frozen_v1.design, "feature_names"):
        raise frozen_v1.Campaign132Error(
            "Campaign132 design feature_names helper changed"
        )
    frozen_v1.design.component_columns = frozen_v1.design.feature_names
    frozen_v1.DEFAULT_IMPLEMENTATION_FREEZE = V2_IMPLEMENTATION_FREEZE
    frozen_v1.DEFAULT_OUTPUT_ROOT = V2_OUTPUT_ROOT
    frozen_v1.TEST_PATH = V2_TEST_PATH
    frozen_v1._implementation_freeze = validate_v2_implementation_freeze
    if V1_FAILURE not in frozen_v1.INFRASTRUCTURE_FAILURES:
        frozen_v1.INFRASTRUCTURE_FAILURES = (
            *frozen_v1.INFRASTRUCTURE_FAILURES,
            V1_FAILURE,
        )
    frozen_v1.__file__ = str(Path(__file__).resolve())


def main() -> int:
    configure_runtime()
    return frozen_v1.main()


if __name__ == "__main__":
    raise SystemExit(main())
