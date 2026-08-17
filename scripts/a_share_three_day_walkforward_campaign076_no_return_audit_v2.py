#!/usr/bin/env python3
"""Retry Campaign076 after the frozen timestamp-provider repair."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

from scripts import a_share_three_day_walkforward_campaign076_no_return_audit as v1


REPO_ROOT = Path(__file__).resolve().parents[1]
REPAIR_PROTOCOL = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_076_no_return_timestamp_provider_repair_protocol_v2_20260806.json"
REPAIR_PROTOCOL_SHA256 = "8411708b84773fe664a5ff68936a15cf7c56249d04038c7bb4fe9ffbf770280f"
FAILURE_RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_076_no_return_v1_timestamp_provider_failure_20260806.json"
FAILURE_RECORD_SHA256 = "38e30c627a9c7bc4ebe352f4f4121797009f90579397b5150d2a4579894de3fd"
IMPLEMENTATION_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_076_no_return_audit_implementation_freeze_v2_20260806.json"
TEST_PATH = REPO_ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign076_no_return_audit_v2.py"


class Campaign076NoReturnAuditV2Error(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign076NoReturnAuditV2Error(f"{label} changed: {path}")


def load_repair_protocol() -> dict[str, Any]:
    _require(REPAIR_PROTOCOL, REPAIR_PROTOCOL_SHA256, "v2 repair protocol")
    _require(FAILURE_RECORD, FAILURE_RECORD_SHA256, "v1 failure record")
    spec = json.loads(REPAIR_PROTOCOL.read_text(encoding="utf-8"))
    sole = spec.get("sole_repair") or {}
    retry = spec.get("retry") or {}
    if not (spec.get("kind") == "a_share_three_day_walkforward_campaign076_no_return_timestamp_provider_repair_protocol" and spec.get("status") == "frozen_after_v1_failure_before_full_retry" and (spec.get("base_v1_runner") or {}).get("sha256") == "a9371fbfeaf48163a41768c8300fec6f944e8a4e14ef04f20eb58853ad2a2d9d" and sole.get("candidate_formula_changed") is False and sole.get("coverage_gate_changed") is False and sole.get("comparison_library_or_order_changed") is False and sole.get("uniqueness_threshold_changed") is False and sole.get("snapshot_or_manifest_rewritten") is False and sole.get("research_value_or_return_field_changed") is False and retry.get("partial_statistics_reused") is False and retry.get("restart_from_candidate_snapshot_verification_and_coverage") is True and retry.get("expected_audit_count_before_retry") == 0):
        raise Campaign076NoReturnAuditV2Error("v2 repair protocol semantics changed")
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE.is_file():
        raise Campaign076NoReturnAuditV2Error("v2 implementation freeze is absent")
    record = json.loads(IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (record.get("kind") == "a_share_three_day_walkforward_campaign076_no_return_audit_implementation_freeze" and record.get("version") == 2 and record.get("status") == "frozen_before_full_retry_after_timestamp_provider_repair" and (record.get("repair_protocol") or {}).get("sha256") == REPAIR_PROTOCOL_SHA256 and (record.get("v2_runner") or {}).get("sha256") == _sha256(Path(__file__).resolve()) and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH) and record.get("corrected_fields") == ["runtime timestamp provider binding only"] and record.get("partial_statistics_reused") is False and record.get("snapshot_or_manifest_files_rewritten") is False and record.get("historical_daily_price_fields_read_before_retry") == [] and record.get("historical_forward_returns_read_before_retry") is False):
        raise Campaign076NoReturnAuditV2Error("v2 implementation freeze changed")
    return record


def _timestamp_target_and_provider() -> tuple[Any, Any]:
    prior, *_rest = v1.cache_v4.v1.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    target = v1.cache_v4.v1.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044
    provider = prior.research
    if not callable(getattr(provider, "_timestamp", None)):
        raise Campaign076NoReturnAuditV2Error("frozen timestamp provider changed")
    return target, provider


@contextmanager
def _temporary_timestamp_binding() -> Iterator[None]:
    target, provider = _timestamp_target_and_provider()
    existed = hasattr(target, "research")
    original = getattr(target, "research", None)
    if existed:
        raise Campaign076NoReturnAuditV2Error("timestamp target unexpectedly already bound")
    setattr(target, "research", provider)
    try:
        yield
    finally:
        if existed:
            setattr(target, "research", original)
        else:
            delattr(target, "research")


def run_no_return_audit(*, data_root: Path, experiment_root: Path, workers: int) -> Path:
    load_repair_protocol()
    _load_implementation_freeze()
    if v1.status(experiment_root).get("audit_count") != 0:
        raise Campaign076NoReturnAuditV2Error("v2 retry requires zero published audits")
    with _temporary_timestamp_binding():
        return v1.run_no_return_audit(data_root=data_root, experiment_root=experiment_root, workers=workers)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=v1.DEFAULT_DATA_ROOT)
    parser.add_argument("--experiment-root", type=Path, default=v1.DEFAULT_EXPERIMENT_ROOT)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    payload = {"audit": str(run_no_return_audit(data_root=args.data_root, experiment_root=args.experiment_root, workers=args.workers)), "timestamp_provider_repair_protocol_sha256": REPAIR_PROTOCOL_SHA256}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
