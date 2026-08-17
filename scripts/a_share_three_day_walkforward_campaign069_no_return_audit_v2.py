#!/usr/bin/env python3
"""Retry Campaign069 after the frozen signed-comparator range registration repair."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign069_no_return_audit as v1


REPO_ROOT = Path(__file__).resolve().parents[1]
REPAIR_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_069_no_return_audit_range_registration_repair_protocol_20260806.json"
)
REPAIR_PROTOCOL_SHA256 = "b752a7617e7724eb208f741e5d903e9f4f56e724d1eabb21007d76f4ea36155e"
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_069_no_return_audit_execution_failure_20260806.json"
)
FAILURE_RECORD_SHA256 = "9743576d0e5f4fdcbbd5ea8500bfbadfbe928aaae880f2f6c1dfc50faada0de5"
V1_RUNNER_SHA256 = "6b02c861740bb46e47097a6f688be0cf1783d3d7a02e508c906d1e18ca87a478"
IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_069_no_return_audit_implementation_freeze_v2_20260806.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign069_no_return_audit_v2.py"
)


class Campaign069NoReturnAuditV2Error(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_repair_protocol() -> dict[str, Any]:
    for path, expected, label in (
        (REPAIR_PROTOCOL, REPAIR_PROTOCOL_SHA256, "repair protocol"),
        (FAILURE_RECORD, FAILURE_RECORD_SHA256, "failure record"),
        (Path(v1.__file__).resolve(), V1_RUNNER_SHA256, "v1 audit runner"),
    ):
        if not path.is_file() or _sha256(path) != expected:
            raise Campaign069NoReturnAuditV2Error(f"Campaign069 {label} changed")
    spec = json.loads(REPAIR_PROTOCOL.read_text(encoding="utf-8"))
    repair = spec.get("sole_repair") or {}
    unchanged = spec.get("unchanged_semantics") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign069_no_return_audit_range_registration_repair_protocol"
        and spec.get("status")
        == "frozen_before_v2_retry_or_additional_comparator_value_read"
        and (spec.get("recorded_failure") or {}).get("sha256")
        == FAILURE_RECORD_SHA256
        and (repair.get("install_candidate_range") or {}).get("range")
        == [-1.0, 1.0]
        and (repair.get("install_campaign068_comparator_range") or {}).get(
            "factor"
        )
        == v1.candidate.C68_FACTOR
        and (repair.get("install_campaign068_comparator_range") or {}).get(
            "range"
        )
        == [-1.0, 1.0]
        and repair.get("delegate_all_other_behavior_to_immutable_v1_runner")
        is True
        and unchanged.get("numeric_comparator_count") == 99
        and unchanged.get("numeric_comparator_order_sha256")
        == v1.EXPECTED_COMPARISON_ORDER_SHA256
        and unchanged.get("coverage_gates_changed") is False
        and unchanged.get("uniqueness_gates_changed") is False
        and boundary.get(
            "additional_comparator_values_read_after_failure_before_this_freeze"
        )
        is False
        and boundary.get("historical_daily_price_fields_read") == []
        and boundary.get("historical_forward_return_fields_read") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign069NoReturnAuditV2Error("Campaign069 repair semantics changed")
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE.is_file():
        raise Campaign069NoReturnAuditV2Error("v2 implementation freeze is absent")
    record = json.loads(IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign069_no_return_audit_implementation_freeze"
        and record.get("version") == 2
        and record.get("status")
        == "frozen_before_v2_same_parameter_retry_or_additional_comparator_value_read"
        and (record.get("repair_protocol") or {}).get("sha256")
        == REPAIR_PROTOCOL_SHA256
        and (record.get("v2_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("historical_daily_price_fields_read_before_freeze") == []
        and record.get("historical_forward_returns_read_before_freeze") is False
        and record.get("provider_request_issued_before_freeze") is False
    ):
        raise Campaign069NoReturnAuditV2Error("v2 implementation freeze changed")
    return record


def install_repaired_ranges(engine: Any) -> None:
    ranges = dict(getattr(engine, "FACTOR_RANGES", {}))
    for factor in (v1.FACTOR_NAME, v1.candidate.C68_FACTOR):
        if factor in ranges and tuple(ranges[factor]) != (-1.0, 1.0):
            raise Campaign069NoReturnAuditV2Error(
                f"conflicting signed range for {factor}"
            )
        ranges[factor] = (-1.0, 1.0)
    engine.FACTOR_RANGES = ranges


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    load_repair_protocol()
    _load_implementation_freeze()
    original = v1._install_frozen_candidate_range
    try:
        v1._install_frozen_candidate_range = install_repaired_ranges
        return v1.run_no_return_audit(
            data_root=data_root,
            experiment_root=experiment_root,
            workers=workers,
        )
    finally:
        v1._install_frozen_candidate_range = original


def status(experiment_root: Path = v1.DEFAULT_EXPERIMENT_ROOT) -> dict[str, Any]:
    payload = v1.status(experiment_root)
    payload.update(
        {
            "v2_repair_protocol_sha256": REPAIR_PROTOCOL_SHA256,
            "v1_failure_preserved": True,
            "historical_daily_price_fields_read_by_status": [],
            "historical_forward_return_fields_read_by_status": False,
            "provider_request_issued_by_status": False,
        }
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("status")
    inspect.add_argument(
        "--experiment-root", type=Path, default=v1.DEFAULT_EXPERIMENT_ROOT
    )
    run = sub.add_parser("run")
    run.add_argument("--data-root", type=Path, default=v1.DEFAULT_DATA_ROOT)
    run.add_argument(
        "--experiment-root", type=Path, default=v1.DEFAULT_EXPERIMENT_ROOT
    )
    run.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.command == "status":
        payload: Any = status(args.experiment_root)
    else:
        payload = {
            "audit": str(
                run_no_return_audit(
                    data_root=args.data_root,
                    experiment_root=args.experiment_root,
                    workers=args.workers,
                )
            )
        }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
