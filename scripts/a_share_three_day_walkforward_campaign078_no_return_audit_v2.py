#!/usr/bin/env python3
"""Retry Campaign078 with the frozen helper-path-only repair."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

from scripts import a_share_three_day_walkforward_campaign078_no_return_audit as v1


REPO_ROOT = Path(__file__).resolve().parents[1]
REPAIR_PROTOCOL = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_078_no_return_helper_path_repair_protocol_v2_20260806.json"
REPAIR_PROTOCOL_SHA256 = "3d12ad46d953f8bfd00fe0ce3ff616c2486c17baf17e4043f25ccb41bc4fe9f0"
FAILURE_RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_078_no_return_v1_helper_path_failure_20260806.json"
FAILURE_RECORD_SHA256 = "9b19c97d0b88f458ce8a4d8ec48a2891a21cf5503d16629051ab14bcb3fafba2"
BASE_V1_SHA256 = "5f194ab765b7d5e42cd6b2a34abb482c69196a3cf0f3d29b065afcb8e588c7a3"
IMPLEMENTATION_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_078_no_return_audit_implementation_freeze_v2_20260806.json"
TEST_PATH = REPO_ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign078_no_return_audit_v2.py"


class Campaign078NoReturnAuditV2Error(RuntimeError):
    """Fail-closed Campaign078 v2 audit error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign078NoReturnAuditV2Error(f"{label} changed: {path}")


def load_repair_protocol() -> dict[str, Any]:
    _require(REPAIR_PROTOCOL, REPAIR_PROTOCOL_SHA256, "v2 repair protocol")
    _require(FAILURE_RECORD, FAILURE_RECORD_SHA256, "v1 failure record")
    _require(Path(v1.__file__).resolve(), BASE_V1_SHA256, "v1 audit runner")
    spec = json.loads(REPAIR_PROTOCOL.read_text(encoding="utf-8"))
    sole = spec.get("sole_repair") or {}
    retry = spec.get("retry") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign078_no_return_helper_path_repair_protocol"
        and spec.get("status")
        == "frozen_after_v1_helper_path_failure_before_full_retry"
        and sole.get("old_attribute_path")
        == "c77_audit.c75_v5.v4.v3.v1.base.base._append_snapshot_comparison"
        and sole.get("new_attribute_path")
        == "c77_audit.c76_audit.c75_v5.v4.v3.v1.base.base._append_snapshot_comparison"
        and all(
            sole.get(key) is False
            for key in (
                "candidate_formula_changed",
                "candidate_snapshot_or_manifest_changed",
                "coverage_gate_changed",
                "comparison_library_or_order_changed",
                "uniqueness_threshold_changed",
                "legacy_runtime_binding_changed",
                "historical_daily_price_or_return_field_changed",
                "development_or_stress_rule_changed",
                "provider_or_candidate49_workflow_changed",
            )
        )
        and retry.get("partial_statistics_reused") is False
        and retry.get("restart_from_candidate_snapshot_verification_and_coverage")
        is True
        and retry.get("expected_audit_count_before_retry") == 0
        and retry.get("maximum_authorized_v2_retries") == 1
    ):
        raise Campaign078NoReturnAuditV2Error("v2 repair protocol semantics changed")
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE.is_file():
        raise Campaign078NoReturnAuditV2Error("v2 implementation freeze is absent")
    record = json.loads(IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign078_no_return_audit_implementation_freeze"
        and record.get("version") == 2
        and record.get("status")
        == "frozen_before_full_retry_with_helper_path_only_repair"
        and (record.get("repair_protocol") or {}).get("sha256")
        == REPAIR_PROTOCOL_SHA256
        and (record.get("v2_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("partial_statistics_reused") is False
        and record.get("candidate_snapshot_or_manifest_rewritten") is False
        and record.get("historical_daily_price_fields_read_before_retry") == []
        and record.get("historical_forward_returns_read_before_retry") is False
    ):
        raise Campaign078NoReturnAuditV2Error("v2 implementation freeze changed")
    return record


def _fixed_load_comparisons_after_coverage(**kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    comparisons, receipts = v1.c77_audit._load_comparisons_after_coverage(**kwargs)
    helper = v1.c77_audit.c76_audit.c75_v5.v4.v3.v1.base.base._append_snapshot_comparison
    workers = int(kwargs["workers"])
    result, receipt = helper(
        manifest_path=v1.C77_SNAPSHOT_MANIFEST_PATH,
        factor=v1.candidate.C77_FACTOR,
        candidate_keys=kwargs["candidate_keys"],
        candidate_values=kwargs["candidate_values"],
        gate=kwargs["gate"],
        engine=kwargs["engine"],
        comparison_engine=kwargs["comparison_engine"],
        workers=workers,
        verifier=lambda _path, workers=workers: v1.verify_campaign077_snapshot(
            workers=workers
        ),
    )
    comparisons.append(result)
    receipts["campaign077_snapshot"] = receipt
    receipts.pop("all_107_sources_loaded_in_frozen_order", None)
    receipts["all_108_sources_loaded_in_frozen_order"] = True
    if len(comparisons) != v1.EXPECTED_COMPARISON_COUNT:
        raise Campaign078NoReturnAuditV2Error("Campaign078 comparison count changed")
    return comparisons, receipts


@contextmanager
def _temporary_helper_path_repair() -> Iterator[None]:
    original = v1._load_comparisons_after_coverage
    v1._load_comparisons_after_coverage = _fixed_load_comparisons_after_coverage
    try:
        yield
    finally:
        v1._load_comparisons_after_coverage = original


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    load_repair_protocol()
    _load_implementation_freeze()
    if v1.status(experiment_root).get("audit_count") != 0:
        raise Campaign078NoReturnAuditV2Error("v2 retry requires zero published audits")
    with _temporary_helper_path_repair():
        return v1.run_no_return_audit(
            data_root=data_root,
            experiment_root=experiment_root,
            workers=workers,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=v1.DEFAULT_DATA_ROOT)
    parser.add_argument(
        "--experiment-root", type=Path, default=v1.DEFAULT_EXPERIMENT_ROOT
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
        "helper_path_repair_protocol_sha256": REPAIR_PROTOCOL_SHA256,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
