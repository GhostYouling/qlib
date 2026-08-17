#!/usr/bin/env python3
"""Retry Campaign075 after one frozen Campaign070 manifest-SHA transcription fix."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_walkforward_campaign075_no_return_audit_v3 as v3


REPO_ROOT = Path(__file__).resolve().parents[1]
CORRECTION_OVERLAY = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_075_no_return_runtime_compatibility_correction_overlay_v4_20260806.json"
)
CORRECTION_OVERLAY_SHA256 = (
    "dac49c32040bb94d98c0f29f9ddcd6f733a2ffdf340354d420c0bb8590183581"
)
IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_075_no_return_audit_implementation_freeze_v4_20260806.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign075_no_return_audit_v4.py"
)
INCORRECT_C70_MANIFEST_SHA256 = (
    "f828ee06ac609580880eb0bfcd2d1fbcaba590e872f57fe5639a468ec67edcbd7"
)
CORRECT_C70_MANIFEST_SHA256 = (
    "f828ee06ac609580880eb0bfcd2d1fbcaba590e872f57fe5639a468c67edcbd7"
)


class Campaign075NoReturnAuditV4Error(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign075NoReturnAuditV4Error(f"{label} changed: {path}")


def load_correction_overlay() -> dict[str, Any]:
    _require(CORRECTION_OVERLAY, CORRECTION_OVERLAY_SHA256, "v4 correction overlay")
    spec = json.loads(CORRECTION_OVERLAY.read_text(encoding="utf-8"))
    base = spec.get("base_v3_protocol") or {}
    sole = spec.get("sole_correction") or {}
    retry = spec.get("retry") or {}
    if not (
        spec.get("version") == 4
        and spec.get("kind")
        == "a_share_three_day_walkforward_campaign075_no_return_runtime_compatibility_correction_overlay"
        and spec.get("status")
        == "frozen_before_full_retry_single_sha_transcription_correction"
        and base.get("sha256") == v3.REPAIR_PROTOCOL_SHA256
        and base.get("preserved") is True
        and sole.get("campaign") == 70
        and sole.get("incorrect_65_character_value")
        == INCORRECT_C70_MANIFEST_SHA256
        and sole.get("correct_authoritative_64_character_value")
        == CORRECT_C70_MANIFEST_SHA256
        and sole.get("manifest_file_rewritten") is False
        and retry.get("partial_statistics_reused") is False
        and retry.get("restart_from_candidate_snapshot_and_coverage") is True
    ):
        raise Campaign075NoReturnAuditV4Error("v4 correction overlay semantics changed")
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE.is_file():
        raise Campaign075NoReturnAuditV4Error("v4 implementation freeze is absent")
    record = json.loads(IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign075_no_return_audit_implementation_freeze"
        and record.get("version") == 4
        and record.get("status")
        == "frozen_before_full_retry_after_single_campaign070_sha_transcription_correction"
        and (record.get("correction_overlay") or {}).get("sha256")
        == CORRECTION_OVERLAY_SHA256
        and (record.get("v4_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("corrected_fields")
        == ["finite_compatibility_snapshot_list[2].manifest_sha256"]
        and record.get("partial_statistics_reused") is False
        and record.get("snapshot_or_manifest_files_rewritten") is False
        and record.get("historical_daily_price_fields_read_before_retry") == []
        and record.get("historical_forward_returns_read_before_retry") is False
    ):
        raise Campaign075NoReturnAuditV4Error("v4 implementation freeze changed")
    return record


def _corrected_snapshot_configs() -> dict[int, dict[str, Any]]:
    load_correction_overlay()
    configs = v3._snapshot_configs()
    if set(configs) != {68, 69, 70, 71, 72, 73, 74}:
        raise Campaign075NoReturnAuditV4Error("v3 finite snapshot scope changed")
    before = str(configs[70]["manifest_sha256"])
    if before != INCORRECT_C70_MANIFEST_SHA256 or len(before) != 65:
        raise Campaign075NoReturnAuditV4Error(
            "the frozen Campaign070 transcription error no longer matches"
        )
    configs[70] = dict(configs[70])
    configs[70]["manifest_sha256"] = CORRECT_C70_MANIFEST_SHA256
    if len(str(configs[70]["manifest_sha256"])) != 64:
        raise Campaign075NoReturnAuditV4Error("corrected Campaign070 SHA is malformed")
    return configs


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    load_correction_overlay()
    _load_implementation_freeze()
    original = v3._snapshot_configs
    try:
        v3._snapshot_configs = _corrected_snapshot_configs
        return v3.run_no_return_audit(
            data_root=data_root,
            experiment_root=experiment_root,
            workers=workers,
        )
    finally:
        v3._snapshot_configs = original


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=v3.v1.DEFAULT_DATA_ROOT)
    parser.add_argument(
        "--experiment-root", type=Path, default=v3.v1.DEFAULT_EXPERIMENT_ROOT
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
        "runtime_compatibility_correction_overlay_sha256": CORRECTION_OVERLAY_SHA256,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
