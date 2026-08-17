#!/usr/bin/env python3
"""Retry Campaign069 with frozen comparator-key missing-value alignment semantics."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign069_no_return_audit as v1
from scripts import a_share_three_day_walkforward_campaign069_no_return_audit_v2 as v2


REPO_ROOT = Path(__file__).resolve().parents[1]
REPAIR_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_069_no_return_audit_comparator_alignment_repair_protocol_20260806.json"
)
REPAIR_PROTOCOL_SHA256 = "843255899622d681d3fae06115de909bb996b08af47633e70363cbbcf8c83cf1"
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_069_no_return_audit_execution_failure_2_20260806.json"
)
FAILURE_RECORD_SHA256 = "b58b273f79d9ed931af2ef2d36089e5d7f0c09accf988683389cdf9422624794"
V2_RUNNER_SHA256 = "bc42919451913cded07c35d2a58d0ee9093d3353305b24afe7e72ff63d10d4f4"
IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_069_no_return_audit_implementation_freeze_v3_20260806.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign069_no_return_audit_v3.py"
)


class Campaign069NoReturnAuditV3Error(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_repair_protocol() -> dict[str, Any]:
    for path, expected, label in (
        (REPAIR_PROTOCOL, REPAIR_PROTOCOL_SHA256, "v3 repair protocol"),
        (FAILURE_RECORD, FAILURE_RECORD_SHA256, "second failure record"),
        (Path(v2.__file__).resolve(), V2_RUNNER_SHA256, "v2 audit runner"),
    ):
        if not path.is_file() or _sha256(path) != expected:
            raise Campaign069NoReturnAuditV3Error(f"Campaign069 {label} changed")
    spec = json.loads(REPAIR_PROTOCOL.read_text(encoding="utf-8"))
    repair = spec.get("sole_repair") or {}
    unchanged = spec.get("unchanged_semantics") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign069_no_return_audit_comparator_alignment_repair_protocol"
        and spec.get("status")
        == "frozen_before_v3_retry_or_additional_comparator_value_read"
        and (spec.get("recorded_failure") or {}).get("sha256")
        == FAILURE_RECORD_SHA256
        and repair.get("delegate_all_other_behavior_to_immutable_v1_and_v2_runners")
        is True
        and "retain finite and NaN comparator values unchanged"
        in repair.get("campaign068_comparator_sorter_semantics", "")
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
        raise Campaign069NoReturnAuditV3Error("Campaign069 v3 repair semantics changed")
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE.is_file():
        raise Campaign069NoReturnAuditV3Error("v3 implementation freeze is absent")
    record = json.loads(IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign069_no_return_audit_implementation_freeze"
        and record.get("version") == 3
        and record.get("status")
        == "frozen_before_v3_same_parameter_retry_or_additional_comparator_value_read"
        and (record.get("repair_protocol") or {}).get("sha256")
        == REPAIR_PROTOCOL_SHA256
        and (record.get("v3_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("historical_daily_price_fields_read_before_freeze") == []
        and record.get("historical_forward_returns_read_before_freeze") is False
        and record.get("provider_request_issued_before_freeze") is False
    ):
        raise Campaign069NoReturnAuditV3Error("v3 implementation freeze changed")
    return record


def build_comparator_sorter(
    *, original: Callable[..., tuple[np.ndarray, np.ndarray]], comparison_engine: Any
) -> Callable[..., tuple[np.ndarray, np.ndarray]]:
    def sorted_arrays(frame: pd.DataFrame, factor: str) -> tuple[np.ndarray, np.ndarray]:
        if factor != v1.candidate.C68_FACTOR:
            return original(frame, factor)
        keys = comparison_engine._compact_stock_day_keys(
            frame["trade_date"], frame["symbol"]
        )
        values = pd.to_numeric(frame[factor], errors="coerce").to_numpy(dtype=float)
        order = np.argsort(keys, kind="stable")
        keys = keys[order]
        values = values[order]
        if len(np.unique(keys)) != len(keys):
            raise Campaign069NoReturnAuditV3Error(
                "Campaign068 comparator keys are not unique"
            )
        return keys, values

    return sorted_arrays


def run_no_return_audit(
    *, data_root: Path, experiment_root: Path, workers: int
) -> Path:
    load_repair_protocol()
    _load_implementation_freeze()
    _, _, engine, _, _, comparison_engine = (
        v1.cache_v4.v1.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    )
    original = engine._sorted_candidate_arrays
    engine._sorted_candidate_arrays = build_comparator_sorter(
        original=original, comparison_engine=comparison_engine
    )
    try:
        return v2.run_no_return_audit(
            data_root=data_root,
            experiment_root=experiment_root,
            workers=workers,
        )
    finally:
        engine._sorted_candidate_arrays = original


def status(experiment_root: Path = v1.DEFAULT_EXPERIMENT_ROOT) -> dict[str, Any]:
    payload = v2.status(experiment_root)
    payload.update(
        {
            "v3_repair_protocol_sha256": REPAIR_PROTOCOL_SHA256,
            "first_two_failures_preserved": True,
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
