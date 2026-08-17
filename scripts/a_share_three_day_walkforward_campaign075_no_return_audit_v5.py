#!/usr/bin/env python3
"""Retry Campaign075 with the frozen v4 correction and non-recursive config access."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from scripts import a_share_three_day_walkforward_campaign075_no_return_audit_v4 as v4


REPO_ROOT = Path(__file__).resolve().parents[1]
REPAIR_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_075_no_return_runtime_compatibility_recursion_repair_protocol_v5_20260806.json"
)
REPAIR_PROTOCOL_SHA256 = (
    "4c89f9b06542e2b215a225b381c2dfd8de68aa2bc1e960d854a0cd888304fb99"
)
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_075_no_return_v4_recursive_config_failure_20260806.json"
)
FAILURE_RECORD_SHA256 = (
    "dc07150b58077016d55365598a18298fbfac40a91e2723c1575ac0501e18f1ef"
)
IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_075_no_return_audit_implementation_freeze_v5_20260806.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign075_no_return_audit_v5.py"
)
_ORIGINAL_V3_SNAPSHOT_CONFIGS: Callable[[], dict[int, dict[str, Any]]] = (
    v4.v3._snapshot_configs
)


class Campaign075NoReturnAuditV5Error(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign075NoReturnAuditV5Error(f"{label} changed: {path}")


def load_repair_protocol() -> dict[str, Any]:
    for path, expected, label in (
        (REPAIR_PROTOCOL, REPAIR_PROTOCOL_SHA256, "v5 repair protocol"),
        (FAILURE_RECORD, FAILURE_RECORD_SHA256, "v4 recursion failure record"),
        (v4.CORRECTION_OVERLAY, v4.CORRECTION_OVERLAY_SHA256, "v4 correction overlay"),
    ):
        _require(path, expected, label)
    spec = json.loads(REPAIR_PROTOCOL.read_text(encoding="utf-8"))
    sole = spec.get("sole_implementation_repair") or {}
    unchanged = spec.get("unchanged") or {}
    retry = spec.get("retry") or {}
    if not (
        spec.get("version") == 5
        and spec.get("kind")
        == "a_share_three_day_walkforward_campaign075_no_return_runtime_compatibility_recursion_repair_protocol"
        and spec.get("status")
        == "frozen_after_v4_recursion_failure_before_full_retry"
        and sole.get("corrected_research_fields") == []
        and sole.get("additional_snapshot_hash_corrections") == []
        and sole.get("snapshot_or_manifest_files_may_be_rewritten") is False
        and all(unchanged.values())
        and retry.get("partial_statistics_reused") is False
        and retry.get("restart_from_candidate_snapshot_and_coverage") is True
    ):
        raise Campaign075NoReturnAuditV5Error("v5 repair protocol semantics changed")
    v4.load_correction_overlay()
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE.is_file():
        raise Campaign075NoReturnAuditV5Error("v5 implementation freeze is absent")
    record = json.loads(IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign075_no_return_audit_implementation_freeze"
        and record.get("version") == 5
        and record.get("status")
        == "frozen_before_full_retry_with_captured_original_snapshot_config_callable"
        and (record.get("repair_protocol") or {}).get("sha256")
        == REPAIR_PROTOCOL_SHA256
        and (record.get("v5_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("corrected_research_fields") == []
        and record.get("partial_statistics_reused") is False
        and record.get("snapshot_or_manifest_files_rewritten") is False
        and record.get("historical_daily_price_fields_read_before_retry") == []
        and record.get("historical_forward_returns_read_before_retry") is False
    ):
        raise Campaign075NoReturnAuditV5Error("v5 implementation freeze changed")
    return record


def _corrected_snapshot_configs() -> dict[int, dict[str, Any]]:
    load_repair_protocol()
    configs = _ORIGINAL_V3_SNAPSHOT_CONFIGS()
    if set(configs) != {68, 69, 70, 71, 72, 73, 74}:
        raise Campaign075NoReturnAuditV5Error("v3 finite snapshot scope changed")
    before = str(configs[70]["manifest_sha256"])
    if before != v4.INCORRECT_C70_MANIFEST_SHA256 or len(before) != 65:
        raise Campaign075NoReturnAuditV5Error(
            "the frozen Campaign070 transcription error no longer matches"
        )
    configs[70] = dict(configs[70])
    configs[70]["manifest_sha256"] = v4.CORRECT_C70_MANIFEST_SHA256
    if any(len(str(item["manifest_sha256"])) != 64 for item in configs.values()):
        raise Campaign075NoReturnAuditV5Error("a corrected manifest SHA is malformed")
    return configs


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    load_repair_protocol()
    _load_implementation_freeze()
    original = v4.v3._snapshot_configs
    if original is not _ORIGINAL_V3_SNAPSHOT_CONFIGS:
        raise Campaign075NoReturnAuditV5Error("v3 snapshot-config callable was prepatched")
    try:
        v4.v3._snapshot_configs = _corrected_snapshot_configs
        return v4.v3.run_no_return_audit(
            data_root=data_root,
            experiment_root=experiment_root,
            workers=workers,
        )
    finally:
        v4.v3._snapshot_configs = original


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=v4.v3.v1.DEFAULT_DATA_ROOT)
    parser.add_argument(
        "--experiment-root", type=Path, default=v4.v3.v1.DEFAULT_EXPERIMENT_ROOT
    )
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    payload = {
        "audit": str(
            run_no_return_audit(
                data_root=args.data_root,
                experiment_root=args.experiment_root,
                workers=args.workers,
            )
        ),
        "runtime_compatibility_recursion_repair_protocol_sha256": REPAIR_PROTOCOL_SHA256,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
