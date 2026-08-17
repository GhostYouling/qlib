#!/usr/bin/env python3
"""Run Campaign087's additive predecessor-identity build repair."""

from __future__ import annotations

import argparse
import contextlib
import json
from pathlib import Path
from typing import Any, Iterator

from scripts import a_share_three_day_walkforward_campaign086_features as c86
from scripts import a_share_three_day_walkforward_campaign086_features_v4 as c86_v4
from scripts import a_share_three_day_walkforward_campaign087_features as v1

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = v1.DEFAULT_DATA_ROOT
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_087_feature_implementation_freeze_v2_20260807.json"
)
REPAIR_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_087_v2_predecessor_identity_repair_protocol_20260807.json"
)
REPAIR_PROTOCOL_SHA256 = (
    "b7358cd87d5259ea02d64463548f1f9c50bfcd4c13c318f9530fc30d31779650"
)
V1_RUNNER_SHA256 = (
    "1a30b769a4b42bf8607d74b83d537e9350a3090422538ed6f540753735e83d13"
)
V1_FREEZE_SHA256 = (
    "6dc5636fdde912c61ba35afd88f91a05b455236838be6866b66178115bc547d6"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign087_features_v2.py"
)
C86_FACTOR_NAME = "intraday_intrabar_close_location_serial_persistence_238p"


class Campaign087FeatureV2Error(RuntimeError):
    """Fail-closed Campaign087 v2 identity-repair error."""


def _sha256(path: Path) -> str:
    return v1._sha256(path)


def _require(path: Path, expected: str, label: str) -> None:
    if not expected or not path.is_file() or _sha256(path) != expected:
        raise Campaign087FeatureV2Error(f"Campaign087 v2 {label} changed: {path}")


def _load_protocol_with_predecessor_identity() -> dict[str, Any]:
    current = c86.FACTOR_NAME
    if current != v1.FACTOR_NAME:
        raise Campaign087FeatureV2Error("Campaign087 build identity was not installed")
    c86.FACTOR_NAME = C86_FACTOR_NAME
    try:
        return v1.load_protocol()
    finally:
        c86.FACTOR_NAME = current


@contextlib.contextmanager
def _corrected_campaign086_builder() -> Iterator[None]:
    replacements = {
        "__file__": str(Path(v1.__file__).resolve()),
        "DEFAULT_PROTOCOL": v1.DEFAULT_PROTOCOL,
        "DEFAULT_IMPLEMENTATION_FREEZE": v1.DEFAULT_IMPLEMENTATION_FREEZE,
        "FACTOR_NAME": v1.FACTOR_NAME,
        "FACTOR_FORMULA": v1.FACTOR_FORMULA,
        "OUTPUT_RUN_ID": v1.OUTPUT_RUN_ID,
        "RAW_COLUMNS": v1.RAW_COLUMNS,
        "OUTPUT_COLUMNS": v1.OUTPUT_COLUMNS,
        "load_protocol": _load_protocol_with_predecessor_identity,
        "_load_implementation_freeze": v1._load_implementation_freeze,
        "extract_serial_persistence": v1.extract_profile_alignment,
        "compact_stock_day_keys": c86_v4.compact_stock_day_keys,
        "output_root": v1.output_root,
    }
    original = {name: getattr(c86, name) for name in replacements}
    try:
        for name, value in replacements.items():
            setattr(c86, name, value)
        yield
    finally:
        for name, value in original.items():
            setattr(c86, name, value)


def _load_implementation_freeze() -> dict[str, Any]:
    _require(REPAIR_PROTOCOL, REPAIR_PROTOCOL_SHA256, "repair protocol")
    _require(Path(v1.__file__).resolve(), V1_RUNNER_SHA256, "v1 runner")
    _require(v1.DEFAULT_IMPLEMENTATION_FREEZE, V1_FREEZE_SHA256, "v1 freeze")
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign087FeatureV2Error("Campaign087 v2 freeze is absent")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign087_feature_implementation_freeze_v2"
        and record.get("status")
        == "predecessor_identity_repair_frozen_before_campaign087_feature_build_retry"
        and (record.get("protocol") or {}).get("sha256") == v1.PROTOCOL_SHA256
        and (record.get("repair_protocol") or {}).get("sha256")
        == REPAIR_PROTOCOL_SHA256
        and (record.get("v1_implementation_freeze") or {}).get("sha256")
        == V1_FREEZE_SHA256
        and (record.get("v2_feature_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("v2_tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("candidate_source_rows_read_before_v2_freeze") is False
        and record.get("candidate_values_computed_before_v2_freeze") is False
        and record.get("comparison_values_read_before_v2_freeze") is False
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_v2_freeze"
        )
        is False
        and record.get("provider_request_issued_before_v2_freeze") is False
    ):
        raise Campaign087FeatureV2Error("Campaign087 v2 freeze changed")
    return record


def _dataset_material(manifest: dict[str, Any]) -> dict[str, Any]:
    return v1._dataset_material(manifest)


def build_snapshot(
    *, data_root: Path, workers: int = 8, confirm_build: bool = False
) -> Path:
    if not confirm_build:
        raise Campaign087FeatureV2Error("Campaign087 v2 build requires --confirm-build")
    _load_implementation_freeze()
    if v1.output_root(data_root.expanduser().resolve()).exists():
        raise Campaign087FeatureV2Error("Campaign087 output already exists")
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
        "scope": "predecessor factor identity during inherited protocol validation only",
        "repair_protocol_sha256": REPAIR_PROTOCOL_SHA256,
        "v1_runner_sha256": V1_RUNNER_SHA256,
        "v1_implementation_freeze_sha256": V1_FREEZE_SHA256,
        "campaign086_predecessor_factor_name": C86_FACTOR_NAME,
        "campaign087_build_factor_name": v1.FACTOR_NAME,
        "formula_or_gate_changed": False,
    }
    manifest["implementation_freeze_status"] = (
        "predecessor_identity_repair_frozen_before_campaign087_feature_build_retry"
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
        repair.get("repair_protocol_sha256") == REPAIR_PROTOCOL_SHA256
        and repair.get("v1_runner_sha256") == V1_RUNNER_SHA256
        and repair.get("v1_implementation_freeze_sha256") == V1_FREEZE_SHA256
        and repair.get("campaign086_predecessor_factor_name") == C86_FACTOR_NAME
        and repair.get("campaign087_build_factor_name") == v1.FACTOR_NAME
        and repair.get("formula_or_gate_changed") is False
    ):
        raise Campaign087FeatureV2Error("Campaign087 v2 repair semantics changed")
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
