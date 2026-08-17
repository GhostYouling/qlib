#!/usr/bin/env python3
"""Publish additive fingerprint bindings for Campaign048 stage transitions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
RUNNER_V1 = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign048_features.py"
RUNNER_V2 = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign048_features_v2.py"
RUNNER_V3 = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign048_features_v3.py"
TESTS = REPO_ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign048_features.py"
PROTOCOL = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_no_return_preregistration.json"
MECHANISM = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_mechanism_overlap_audit.json"
CONCEPT = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_concept_scouting.json"
IMPLEMENTATION = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_feature_implementation_freeze_20260801.json"
SNAPSHOT_BINDING = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_snapshot_publication_binding_20260801.json"
NO_RETURN_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_048_no_return_audit_freeze_20260801.json"
SNAPSHOT = DATA_ROOT / "derived/a_share/rich/tushare/minute_walkforward_campaign048_feature_library/tushare_stk_mins_1m_2019_2025_ea0cbb8f_walkforward_campaign048_feature_library_v1/snapshot_manifest.json"
EXPERIMENT_ROOT = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_048/no_return"
FACTOR_NAME = "intraday_two_sided_wick_absorption_balance_240m"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_or_absolute(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def write_new(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        if json.loads(path.read_text(encoding="utf-8")) != record:
            raise RuntimeError(f"refuse to rewrite frozen record: {path}")
        return
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def implementation() -> Path:
    record = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign048_feature_implementation_freeze",
        "status": "frozen_before_campaign048_candidate_values",
        "recorded_at": "2026-08-01T04:06:00Z",
        "concept_scouting": {"path": relative_or_absolute(CONCEPT), "sha256": sha256(CONCEPT)},
        "mechanism_overlap_audit": {"path": relative_or_absolute(MECHANISM), "sha256": sha256(MECHANISM)},
        "no_return_protocol": {"path": relative_or_absolute(PROTOCOL), "sha256": sha256(PROTOCOL)},
        "feature_runner": {"path": relative_or_absolute(RUNNER_V1), "sha256": sha256(RUNNER_V1)},
        "feature_tests": {"path": relative_or_absolute(TESTS), "sha256": sha256(TESTS), "passed": 8},
        "freeze_publisher": {"path": relative_or_absolute(Path(__file__).resolve()), "sha256": sha256(Path(__file__).resolve())},
        "formula_or_direction_changed_after_preregistration": False,
        "candidate_values_read_before_freeze": False,
        "comparison_values_read_before_freeze": False,
        "historical_daily_price_fields_read_before_freeze": [],
        "historical_forward_returns_read_before_freeze": False,
        "provider_request_issued": False,
        "candidate49_ledgers_changed": False,
        "candidate50_activation_created": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }
    write_new(IMPLEMENTATION, record)
    return IMPLEMENTATION


def snapshot() -> Path:
    if not RUNNER_V2.is_file():
        raise RuntimeError("Campaign048 bound build runner v2 is absent")
    implementation_record = json.loads(IMPLEMENTATION.read_text(encoding="utf-8"))
    manifest = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    if not (
        manifest.get("kind") == "a_share_three_day_walkforward_campaign048_feature_snapshot"
        and manifest.get("status") == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("candidate49_historical_return_read") is False
    ):
        raise RuntimeError("Campaign048 snapshot is not eligible for publication binding")
    record = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign048_snapshot_publication_binding",
        "status": "immutable_candidate_snapshot_bound_before_comparison_values",
        "recorded_at": "2026-08-01T04:07:00Z",
        "implementation_freeze": {"path": relative_or_absolute(IMPLEMENTATION), "sha256": sha256(IMPLEMENTATION)},
        "implementation_freeze_runner_sha256": implementation_record["feature_runner"]["sha256"],
        "bound_build_runner": {"path": relative_or_absolute(RUNNER_V2), "sha256": sha256(RUNNER_V2)},
        "candidate_snapshot": {
            "path": str(SNAPSHOT),
            "sha256": sha256(SNAPSHOT),
            "dataset_sha256": manifest["dataset_sha256"],
            "partitions": manifest["partitions"],
            "rows": manifest["rows"],
            "eligible_rows": manifest["factor_eligible_rows"][FACTOR_NAME],
        },
        "freeze_publisher": {"path": relative_or_absolute(Path(__file__).resolve()), "sha256": sha256(Path(__file__).resolve())},
        "all_partition_byte_and_frame_hashes_must_be_revalidated_before_comparisons": True,
        "comparison_values_read_before_binding": False,
        "historical_daily_price_fields_read_before_binding": [],
        "historical_forward_returns_read_before_binding": False,
        "provider_request_issued": False,
        "candidate49_ledgers_changed": False,
        "candidate50_activation_created": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }
    write_new(SNAPSHOT_BINDING, record)
    return SNAPSHOT_BINDING


def no_return() -> Path:
    if not RUNNER_V3.is_file():
        raise RuntimeError("Campaign048 bound no-return runner v3 is absent")
    audits = sorted(EXPERIMENT_ROOT.glob("*_campaign048_no_return_audit.json"))
    if len(audits) != 1:
        raise RuntimeError("Campaign048 must have exactly one no-return audit")
    audit_path = audits[0]
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if not (
        audit.get("kind") == "a_share_three_day_walkforward_campaign048_no_return_audit"
        and audit.get("historical_forward_return_fields_read") is False
        and audit.get("candidate49_prospective_ledgers_changed") is False
        and audit.get("current_scoring_selection_sizing_or_orders_performed") is False
    ):
        raise RuntimeError("Campaign048 no-return audit boundary changed")
    record = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign048_no_return_audit_freeze",
        "status": "immutable_ordered_no_return_audit_bound_before_historical_returns",
        "recorded_at": "2026-08-01T04:08:00Z",
        "snapshot_publication_binding": {"path": relative_or_absolute(SNAPSHOT_BINDING), "sha256": sha256(SNAPSHOT_BINDING)},
        "bound_no_return_runner": {"path": relative_or_absolute(RUNNER_V3), "sha256": sha256(RUNNER_V3)},
        "no_return_audit": {"path": relative_or_absolute(audit_path), "sha256": sha256(audit_path)},
        "admissible_factor_count": audit["admissible_factor_count"],
        "comparison_factor_count": (audit.get("uniqueness", {}).get(FACTOR_NAME, {}).get("comparison_factor_count", 0)),
        "historical_daily_price_fields_read": [],
        "historical_forward_returns_read": False,
        "provider_request_issued": False,
        "candidate49_ledgers_changed": False,
        "candidate50_activation_created": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }
    write_new(NO_RETURN_FREEZE, record)
    return NO_RETURN_FREEZE


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("implementation", "snapshot", "no-return"))
    args = parser.parse_args()
    path = {"implementation": implementation, "snapshot": snapshot, "no-return": no_return}[args.stage]()
    print(json.dumps({"status": f"campaign048_{args.stage}_freeze_written", "path": str(path), "sha256": sha256(path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
