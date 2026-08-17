#!/usr/bin/env python3
"""Verify Campaign087's v3 snapshot with scoped runner identities."""

from __future__ import annotations

import argparse
import contextlib
import json
from pathlib import Path
from typing import Any, Iterator

from scripts import a_share_three_day_walkforward_campaign087_features as v1
from scripts import a_share_three_day_walkforward_campaign087_features_v3 as v3

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = v1.DEFAULT_DATA_ROOT
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_087_feature_verifier_implementation_freeze_v4_20260807.json"
)
REPAIR_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_087_v4_verifier_identity_repair_protocol_20260807.json"
)
REPAIR_PROTOCOL_SHA256 = (
    "f70e058871cf13233a9467db8ed3501ae48a7a45ae50452910f6db94db0d46eb"
)
V1_RUNNER_PATH = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign087_features.py"
)
V1_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_087_feature_implementation_freeze_20260807.json"
)
V1_RUNNER_SHA256 = v3.V1_RUNNER_SHA256
V3_RUNNER_SHA256 = (
    "be6f174ef880ab562424f457328b33539372a9426c850b032915cac62b995964"
)
V3_FREEZE_SHA256 = (
    "1fff6cb9dd04ef65641be5f000102da3e48fa73e3445620c9a675a044145d774"
)
SNAPSHOT_MANIFEST_PATH = (
    v1.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "6abe71a2402dc7b34124c1cc2abee8c54730ce978e6057b7b02beb4a4bcce5bd"
)
SNAPSHOT_DATASET_SHA256 = (
    "acc712042d582fbcbb87d23e7e7e47e71c6cbeb9b8a33678c75bb0ea58070777"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign087_features_v4.py"
)


class Campaign087FeatureV4Error(RuntimeError):
    """Fail-closed Campaign087 v4 verifier error."""


def _sha256(path: Path) -> str:
    return v1._sha256(path)


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign087FeatureV4Error(f"Campaign087 v4 {label} changed: {path}")


def _load_v3_freeze_with_v1_identity() -> dict[str, Any]:
    current_file = v1.__file__
    current_freeze = v1.DEFAULT_IMPLEMENTATION_FREEZE
    v1.__file__ = str(V1_RUNNER_PATH.resolve())
    v1.DEFAULT_IMPLEMENTATION_FREEZE = V1_FREEZE_PATH
    try:
        return v3._load_implementation_freeze()
    finally:
        v1.__file__ = current_file
        v1.DEFAULT_IMPLEMENTATION_FREEZE = current_freeze


@contextlib.contextmanager
def _patched_v1_verifier() -> Iterator[None]:
    replacements = {
        "__file__": str(Path(v3.__file__).resolve()),
        "DEFAULT_IMPLEMENTATION_FREEZE": v3.DEFAULT_IMPLEMENTATION_FREEZE,
        "_load_implementation_freeze": _load_v3_freeze_with_v1_identity,
    }
    original = {name: getattr(v1, name) for name in replacements}
    try:
        for name, value in replacements.items():
            setattr(v1, name, value)
        yield
    finally:
        for name, value in original.items():
            setattr(v1, name, value)


def _load_implementation_freeze() -> dict[str, Any]:
    _require(REPAIR_PROTOCOL, REPAIR_PROTOCOL_SHA256, "repair protocol")
    _require(V1_RUNNER_PATH, V1_RUNNER_SHA256, "v1 runner")
    _require(Path(v3.__file__).resolve(), V3_RUNNER_SHA256, "v3 runner")
    _require(v3.DEFAULT_IMPLEMENTATION_FREEZE, V3_FREEZE_SHA256, "v3 freeze")
    _require(SNAPSHOT_MANIFEST_PATH, SNAPSHOT_MANIFEST_SHA256, "snapshot manifest")
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign087FeatureV4Error("Campaign087 v4 freeze is absent")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign087_feature_verifier_implementation_freeze_v4"
        and record.get("status")
        == "scoped_identity_verifier_frozen_before_repaired_snapshot_verification_or_coverage"
        and (record.get("repair_protocol") or {}).get("sha256")
        == REPAIR_PROTOCOL_SHA256
        and (record.get("v3_implementation_freeze") or {}).get("sha256")
        == V3_FREEZE_SHA256
        and (record.get("snapshot_manifest") or {}).get("sha256")
        == SNAPSHOT_MANIFEST_SHA256
        and (record.get("v4_verifier") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("v4_tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("snapshot_verified_before_v4_freeze") is False
        and record.get("coverage_or_capacity_metrics_computed_before_v4_freeze")
        is False
        and record.get("comparison_values_read_before_v4_freeze") is False
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_v4_freeze"
        )
        is False
        and record.get("provider_request_issued_before_v4_freeze") is False
    ):
        raise Campaign087FeatureV4Error("Campaign087 v4 freeze changed")
    return record


def verify_snapshot_files(
    manifest_path: Path = SNAPSHOT_MANIFEST_PATH,
) -> dict[str, Any]:
    _load_implementation_freeze()
    path = manifest_path.expanduser().resolve()
    if path != SNAPSHOT_MANIFEST_PATH.resolve():
        raise Campaign087FeatureV4Error("Campaign087 v4 manifest path changed")
    before = _sha256(path)
    with _patched_v1_verifier():
        result = v1.verify_snapshot_files(path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    repair = manifest.get("runtime_repair") or {}
    if not (
        before == SNAPSHOT_MANIFEST_SHA256
        and _sha256(path) == before
        and result.get("status") == "verified"
        and result.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and result.get("rows") == v1.EXPECTED_ROWS
        and result.get("partitions") == v1.EXPECTED_PARTITIONS
        and result.get("eligible_rows") == 1_328_449
        and repair.get("v3_repair_protocol_sha256") == v3.REPAIR_PROTOCOL_SHA256
        and repair.get("v2_repair_protocol_sha256") == v3.v2.REPAIR_PROTOCOL_SHA256
        and repair.get("v1_runner_sha256") == v3.V1_RUNNER_SHA256
        and repair.get("v2_runner_sha256") == v3.V2_RUNNER_SHA256
        and repair.get("campaign086_v3_runner_sha256")
        == v3.C86_V3_RUNNER_SHA256
        and repair.get("formula_or_gate_changed") is False
        and manifest.get("comparison_values_read") is False
        and manifest.get("historical_daily_price_fields_read") == []
        and manifest.get("historical_forward_returns_read") is False
        and manifest.get("provider_request_issued") is False
    ):
        raise Campaign087FeatureV4Error("Campaign087 v4 verification semantics changed")
    return {
        **result,
        "manifest_sha256": before,
        "verifier_repair_protocol_sha256": REPAIR_PROTOCOL_SHA256,
        "snapshot_rewritten": False,
    }


def status() -> dict[str, Any]:
    return {
        "status": "snapshot_present_pending_v4_verification"
        if SNAPSHOT_MANIFEST_PATH.is_file()
        else "snapshot_absent",
        "snapshot_manifest_path": str(SNAPSHOT_MANIFEST_PATH),
        "snapshot_manifest_sha256_matches": SNAPSHOT_MANIFEST_PATH.is_file()
        and _sha256(SNAPSHOT_MANIFEST_PATH) == SNAPSHOT_MANIFEST_SHA256,
        "coverage_or_capacity_metrics_computed_by_status": False,
        "comparison_values_read_by_status": False,
        "historical_daily_price_or_forward_return_values_read_by_status": False,
        "provider_request_issued_by_status": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    verify = sub.add_parser("verify")
    verify.add_argument("--manifest", type=Path, default=SNAPSHOT_MANIFEST_PATH)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "status":
        print(json.dumps(status(), sort_keys=True))
        return 0
    print(json.dumps(verify_snapshot_files(args.manifest), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
