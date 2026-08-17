#!/usr/bin/env python3
"""Run Campaign087's additive empty-identity attachment repair."""

from __future__ import annotations

import argparse
import contextlib
import json
from pathlib import Path
from typing import Any, Iterator

from scripts import a_share_three_day_walkforward_campaign086_features as c86
from scripts import a_share_three_day_walkforward_campaign086_features_v3 as c86_v3
from scripts import a_share_three_day_walkforward_campaign087_features as v1
from scripts import a_share_three_day_walkforward_campaign087_features_v2 as v2

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = v1.DEFAULT_DATA_ROOT
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_087_feature_implementation_freeze_v3_20260807.json"
)
REPAIR_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_087_v3_empty_identity_repair_protocol_20260807.json"
)
REPAIR_PROTOCOL_SHA256 = (
    "c71e1d9454bbf053e282f4674cacd4bb4fa2efe000d1fd6f13e4abd3abcb293c"
)
V1_RUNNER_SHA256 = v2.V1_RUNNER_SHA256
V1_FREEZE_SHA256 = v2.V1_FREEZE_SHA256
V2_RUNNER_SHA256 = (
    "8ae28bcf6f8b4eb45388df9a2588e22531481a59c0b5f5776d7a907d1460bc2f"
)
V2_FREEZE_SHA256 = (
    "e60ff2b1a2f8d5a2c6e79bc5edc81984f9746d29a9b59e369bb95e856e480163"
)
C86_V3_RUNNER_SHA256 = (
    "17c92d5d0512f0e02bc5997ade732730ba91addb98732af2518563a336ebe6b2"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign087_features_v3.py"
)


class Campaign087FeatureV3Error(RuntimeError):
    """Fail-closed Campaign087 v3 empty-identity repair error."""


def _sha256(path: Path) -> str:
    return v1._sha256(path)


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign087FeatureV3Error(f"Campaign087 v3 {label} changed: {path}")


@contextlib.contextmanager
def _corrected_campaign086_builder() -> Iterator[None]:
    with v2._corrected_campaign086_builder():
        original = c86.attach_values
        c86.attach_values = c86_v3.attach_values
        try:
            yield
        finally:
            c86.attach_values = original


def _load_implementation_freeze() -> dict[str, Any]:
    _require(REPAIR_PROTOCOL, REPAIR_PROTOCOL_SHA256, "repair protocol")
    _require(Path(v1.__file__).resolve(), V1_RUNNER_SHA256, "v1 runner")
    _require(v1.DEFAULT_IMPLEMENTATION_FREEZE, V1_FREEZE_SHA256, "v1 freeze")
    _require(Path(v2.__file__).resolve(), V2_RUNNER_SHA256, "v2 runner")
    _require(v2.DEFAULT_IMPLEMENTATION_FREEZE, V2_FREEZE_SHA256, "v2 freeze")
    _require(Path(c86_v3.__file__).resolve(), C86_V3_RUNNER_SHA256, "Campaign086 v3 runner")
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign087FeatureV3Error("Campaign087 v3 freeze is absent")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign087_feature_implementation_freeze_v3"
        and record.get("status")
        == "empty_identity_repair_frozen_before_campaign087_feature_build_retry"
        and (record.get("protocol") or {}).get("sha256") == v1.PROTOCOL_SHA256
        and (record.get("repair_protocol") or {}).get("sha256")
        == REPAIR_PROTOCOL_SHA256
        and (record.get("v1_implementation_freeze") or {}).get("sha256")
        == V1_FREEZE_SHA256
        and (record.get("v2_implementation_freeze") or {}).get("sha256")
        == V2_FREEZE_SHA256
        and (record.get("v3_feature_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("v3_tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("candidate_snapshot_published_before_v3_freeze") is False
        and record.get("comparison_values_read_before_v3_freeze") is False
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_v3_freeze"
        )
        is False
        and record.get("provider_request_issued_before_v3_freeze") is False
    ):
        raise Campaign087FeatureV3Error("Campaign087 v3 freeze changed")
    return record


def _dataset_material(manifest: dict[str, Any]) -> dict[str, Any]:
    return v1._dataset_material(manifest)


def build_snapshot(
    *, data_root: Path, workers: int = 8, confirm_build: bool = False
) -> Path:
    if not confirm_build:
        raise Campaign087FeatureV3Error("Campaign087 v3 build requires --confirm-build")
    _load_implementation_freeze()
    if v1.output_root(data_root.expanduser().resolve()).exists():
        raise Campaign087FeatureV3Error("Campaign087 output already exists")
    original_context = v1._patched_campaign086_builder
    v1._patched_campaign086_builder = _corrected_campaign086_builder
    try:
        manifest_path = v1.build_snapshot(
            data_root=data_root,
            workers=workers,
            confirm_build=True,
        )
    finally:
        v1._patched_campaign086_builder = original_context
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["implementation_freeze"] = {
        "path": str(DEFAULT_IMPLEMENTATION_FREEZE.resolve()),
        "sha256": _sha256(DEFAULT_IMPLEMENTATION_FREEZE),
    }
    manifest["feature_runner"] = {
        "path": str(Path(__file__).resolve()),
        "sha256": _sha256(Path(__file__).resolve()),
    }
    manifest["runtime_repair"] = {
        "scope": "v2 predecessor identity plus frozen Campaign086 v3 empty-identity attachment dispatch",
        "v3_repair_protocol_sha256": REPAIR_PROTOCOL_SHA256,
        "v2_repair_protocol_sha256": v2.REPAIR_PROTOCOL_SHA256,
        "v1_runner_sha256": V1_RUNNER_SHA256,
        "v2_runner_sha256": V2_RUNNER_SHA256,
        "v1_implementation_freeze_sha256": V1_FREEZE_SHA256,
        "v2_implementation_freeze_sha256": V2_FREEZE_SHA256,
        "campaign086_v3_runner_sha256": C86_V3_RUNNER_SHA256,
        "formula_or_gate_changed": False,
    }
    manifest["implementation_freeze_status"] = (
        "empty_identity_repair_frozen_before_campaign087_feature_build_retry"
    )
    manifest["dataset_sha256"] = v1._json_digest(_dataset_material(manifest))
    v1.c85._atomic_json(manifest, manifest_path)
    return manifest_path


@contextlib.contextmanager
def _patched_v1_verifier() -> Iterator[None]:
    replacements = {
        "__file__": str(Path(__file__).resolve()),
        "DEFAULT_IMPLEMENTATION_FREEZE": DEFAULT_IMPLEMENTATION_FREEZE,
        "_load_implementation_freeze": _load_implementation_freeze,
    }
    original = {name: getattr(v1, name) for name in replacements}
    try:
        for name, value in replacements.items():
            setattr(v1, name, value)
        yield
    finally:
        for name, value in original.items():
            setattr(v1, name, value)


def verify_snapshot_files(manifest_path: Path) -> dict[str, Any]:
    _load_implementation_freeze()
    with _patched_v1_verifier():
        result = v1.verify_snapshot_files(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    repair = manifest.get("runtime_repair") or {}
    if not (
        repair.get("v3_repair_protocol_sha256") == REPAIR_PROTOCOL_SHA256
        and repair.get("v2_repair_protocol_sha256") == v2.REPAIR_PROTOCOL_SHA256
        and repair.get("v1_runner_sha256") == V1_RUNNER_SHA256
        and repair.get("v2_runner_sha256") == V2_RUNNER_SHA256
        and repair.get("campaign086_v3_runner_sha256") == C86_V3_RUNNER_SHA256
        and repair.get("formula_or_gate_changed") is False
    ):
        raise Campaign087FeatureV3Error("Campaign087 v3 repair semantics changed")
    return result


def status(data_root: Path = DEFAULT_DATA_ROOT) -> dict[str, Any]:
    return v1.status(data_root)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    build.add_argument("--workers", type=int, default=8)
    build.add_argument("--confirm-build", action="store_true")
    inspect = sub.add_parser("status")
    inspect.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    verify = sub.add_parser("verify")
    verify.add_argument("--manifest", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "status":
        print(json.dumps(status(args.data_root), sort_keys=True))
        return 0
    if args.command == "build":
        print(
            build_snapshot(
                data_root=args.data_root,
                workers=args.workers,
                confirm_build=args.confirm_build,
            )
        )
        return 0
    manifest = args.manifest or (
        v1.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
    )
    print(json.dumps(verify_snapshot_files(manifest), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
