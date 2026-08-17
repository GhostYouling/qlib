#!/usr/bin/env python3
"""Run Campaign071's frozen coverage-first, no-return overlap audit."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from scripts import a_share_three_day_compact_comparator_cache_v4 as cache_v4
from scripts import a_share_three_day_walkforward_campaign070_features as c70
from scripts import a_share_three_day_walkforward_campaign071_features as candidate


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign070_no_return_audit.py"
TEMPLATE_SHA256 = "534ad73ff13459e3585c4349e49bbc65a2962ec433f93682db9c6fc88f4d54eb"
SNAPSHOT_MANIFEST_SHA256 = "438db2c72a0e5a166f87e680109024be7b28ed710edbd6b4d5ce6968e4a3f7fd"
SNAPSHOT_DATASET_SHA256 = "8c6f1eff1b2238132f429eaeae13d9a7fbd9956e89f3499fa1cf68d54435528d"
SNAPSHOT_BINDING_SHA256 = "8b6cb0bbab838bc72977ce0b8c59e4b1894633cfe78c903de01a2fcc65749a71"
SEQUENCE_RECORD_SHA256 = "fc73c79f4a7719d6ebeda10056352377f0d14985844fd3a0f88d11289baf9734"
EXPECTED_ELIGIBLE_ROWS = 7_081_458
EXPECTED_COMPARISON_COUNT = 101
EXPECTED_COMPLETE_DEFINITION_COUNT = 102
EXPECTED_COMPARISON_ORDER_SHA256 = candidate.COMPARISON_ORDER_SHA256
EXPECTED_COMPLETE_DEFINITION_ORDER_SHA256 = candidate.FULL_DEFINITION_ORDER_SHA256
C70_SNAPSHOT_MANIFEST_PATH = c70.output_root(candidate.DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
C70_SNAPSHOT_BINDING = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_070_feature_snapshot_binding_20260806.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if not TEMPLATE.is_file() or _sha256(TEMPLATE) != TEMPLATE_SHA256:
    raise RuntimeError("frozen Campaign070 no-return audit runner changed")


_source = TEMPLATE.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign070", "Campaign071"),
    ("campaign070", "campaign071"),
    ("campaign_070", "campaign_071"),
    ("scripts import a_share_three_day_walkforward_campaign070_features as candidate", "scripts import a_share_three_day_walkforward_campaign071_features as candidate"),
    ("f828ee06ac609580880eb0bfcd2d1fbcaba590e872f57fe5639a468c67edcbd7", SNAPSHOT_MANIFEST_SHA256),
    ("35ea87d9e183b77a382a88789cedf96d79f6a102c5006e156bbde2ff87fd6efe", SNAPSHOT_DATASET_SHA256),
    ("4c573c47ce247cac96c492ae37f93c39356303db18f05c093f1446a765e8aa34", SNAPSHOT_BINDING_SHA256),
    ("360781d40a9925c25df40db049b2de862d0b969273b6ca67ca0485d89aaba85b", SEQUENCE_RECORD_SHA256),
    ("EXPECTED_ELIGIBLE_ROWS = 6_353_795", "EXPECTED_ELIGIBLE_ROWS = 7_081_458"),
    ("EXPECTED_COMPARISON_COUNT = 100", "EXPECTED_COMPARISON_COUNT = 101"),
    ("EXPECTED_COMPLETE_DEFINITION_COUNT = 101", "EXPECTED_COMPLETE_DEFINITION_COUNT = 102"),
    ("all_100_sources_loaded_in_frozen_order", "all_101_sources_loaded_in_frozen_order"),
):
    _source = _source.replace(_old, _new)

_runtime: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign071_no_return_audit_generated",
}
exec(compile(_source, str(TEMPLATE), "exec"), _runtime)

Campaign071NoReturnAuditError = _runtime["Campaign071NoReturnAuditError"]
FACTOR_NAME = candidate.FACTOR_NAME
DEFAULT_DATA_ROOT = candidate.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_071/no_return"
SNAPSHOT_MANIFEST_PATH = candidate.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
SNAPSHOT_BINDING = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_071_feature_snapshot_binding_20260806.json"
SEQUENCE_RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_071_audit_freeze_sequence_record_20260806.json"
AUDIT_IMPLEMENTATION_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_071_no_return_audit_implementation_freeze_20260806.json"
AUDIT_ACTIVATION_BINDING = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_071_no_return_audit_activation_binding_20260806.json"
TEST_PATH = REPO_ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign071_no_return_audit.py"


def load_protocol() -> dict[str, Any]:
    spec = candidate.load_protocol()
    comparisons = candidate.reconstruct_comparisons(spec)
    complete = [
        {"name": str(item["name"]), "score_direction": str(item["score_direction"])}
        for item in cache_v4._library_layout()["complete_definitions"]
    ]
    complete.extend(
        [
            {"name": candidate.C68_FACTOR, "score_direction": "higher"},
            {"name": candidate.C69_FACTOR, "score_direction": "higher"},
            {"name": candidate.C70_FACTOR, "score_direction": "higher"},
        ]
    )
    if not (
        len(comparisons) == EXPECTED_COMPARISON_COUNT
        and candidate._runtime["_comparison_order_digest"](comparisons) == EXPECTED_COMPARISON_ORDER_SHA256
        and len(complete) == EXPECTED_COMPLETE_DEFINITION_COUNT
        and candidate._runtime["_comparison_order_digest"](complete) == EXPECTED_COMPLETE_DEFINITION_ORDER_SHA256
    ):
        raise Campaign071NoReturnAuditError("Campaign071 comparison order changed")
    spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]["comparison_factors"] = comparisons
    return spec


_base_verify_static_bindings = _runtime["verify_static_bindings"]


def verify_static_bindings() -> dict[str, Any]:
    report = _base_verify_static_bindings()
    if _sha256(C70_SNAPSHOT_MANIFEST_PATH) != candidate.C70_SNAPSHOT_MANIFEST_SHA256:
        raise Campaign071NoReturnAuditError("Campaign070 comparator manifest changed")
    if _sha256(C70_SNAPSHOT_BINDING) != candidate.C70_SNAPSHOT_BINDING_SHA256:
        raise Campaign071NoReturnAuditError("Campaign070 comparator binding changed")
    c70_manifest = json.loads(C70_SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    if c70_manifest.get("dataset_sha256") != candidate.C70_SNAPSHOT_DATASET_SHA256:
        raise Campaign071NoReturnAuditError("Campaign070 comparator dataset changed")
    report["campaign070_comparator_manifest_sha256"] = candidate.C70_SNAPSHOT_MANIFEST_SHA256
    report["campaign070_comparator_dataset_sha256"] = candidate.C70_SNAPSHOT_DATASET_SHA256
    return report


_base_install_ranges = _runtime["_install_frozen_ranges"]


def _install_frozen_ranges(engine: Any) -> None:
    _base_install_ranges(engine)
    ranges = dict(getattr(engine, "FACTOR_RANGES", {}))
    if candidate.C70_FACTOR in ranges and tuple(ranges[candidate.C70_FACTOR]) != (0.0, 1.0):
        raise Campaign071NoReturnAuditError("Campaign070 comparator range changed")
    ranges[candidate.C70_FACTOR] = (0.0, 1.0)
    engine.FACTOR_RANGES = ranges


_base_load_comparisons = _runtime["_load_comparisons_after_coverage"]


def _load_comparisons_after_coverage(**kwargs: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    comparisons, receipts = _base_load_comparisons(**kwargs)
    result, receipt = _runtime["_append_snapshot_comparison"](
        manifest_path=C70_SNAPSHOT_MANIFEST_PATH,
        factor=candidate.C70_FACTOR,
        candidate_keys=kwargs["candidate_keys"],
        candidate_values=kwargs["candidate_values"],
        gate=kwargs["gate"],
        engine=kwargs["engine"],
        comparison_engine=kwargs["comparison_engine"],
        workers=kwargs["workers"],
        verifier=c70.verify_snapshot_files,
    )
    comparisons.append(result)
    receipts["campaign070_snapshot"] = receipt
    receipts["all_101_sources_loaded_in_frozen_order"] = True
    if len(comparisons) != EXPECTED_COMPARISON_COUNT:
        raise Campaign071NoReturnAuditError("Campaign071 comparison count changed")
    gc.collect()
    return comparisons, receipts


for _name, _value in {
    "FACTOR_NAME": FACTOR_NAME,
    "DEFAULT_DATA_ROOT": DEFAULT_DATA_ROOT,
    "DEFAULT_EXPERIMENT_ROOT": DEFAULT_EXPERIMENT_ROOT,
    "SNAPSHOT_MANIFEST_PATH": SNAPSHOT_MANIFEST_PATH,
    "SNAPSHOT_MANIFEST_SHA256": SNAPSHOT_MANIFEST_SHA256,
    "SNAPSHOT_DATASET_SHA256": SNAPSHOT_DATASET_SHA256,
    "SNAPSHOT_BINDING": SNAPSHOT_BINDING,
    "SNAPSHOT_BINDING_SHA256": SNAPSHOT_BINDING_SHA256,
    "SEQUENCE_RECORD": SEQUENCE_RECORD,
    "SEQUENCE_RECORD_SHA256": SEQUENCE_RECORD_SHA256,
    "AUDIT_IMPLEMENTATION_FREEZE": AUDIT_IMPLEMENTATION_FREEZE,
    "AUDIT_ACTIVATION_BINDING": AUDIT_ACTIVATION_BINDING,
    "TEST_PATH": TEST_PATH,
    "EXPECTED_ELIGIBLE_ROWS": EXPECTED_ELIGIBLE_ROWS,
    "EXPECTED_COMPARISON_COUNT": EXPECTED_COMPARISON_COUNT,
    "EXPECTED_COMPLETE_DEFINITION_COUNT": EXPECTED_COMPLETE_DEFINITION_COUNT,
    "EXPECTED_COMPARISON_ORDER_SHA256": EXPECTED_COMPARISON_ORDER_SHA256,
    "EXPECTED_COMPLETE_DEFINITION_ORDER_SHA256": EXPECTED_COMPLETE_DEFINITION_ORDER_SHA256,
    "load_protocol": load_protocol,
    "verify_static_bindings": verify_static_bindings,
    "_install_frozen_ranges": _install_frozen_ranges,
    "_load_comparisons_after_coverage": _load_comparisons_after_coverage,
}.items():
    _runtime[_name] = _value

run_no_return_audit = _runtime["run_no_return_audit"]


def status(experiment_root: Path = DEFAULT_EXPERIMENT_ROOT) -> dict[str, Any]:
    audits = sorted(experiment_root.expanduser().resolve().glob("*_campaign071_no_return_audit.json"))
    return {
        "audit_implementation_freeze_exists": AUDIT_IMPLEMENTATION_FREEZE.is_file(),
        "audit_activation_binding_exists": AUDIT_ACTIVATION_BINDING.is_file(),
        "candidate_snapshot_exists": SNAPSHOT_MANIFEST_PATH.is_file(),
        "audit_count": len(audits),
        "comparison_values_read_by_status": False,
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "provider_request_issued": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("status")
    inspect.add_argument("--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT)
    run = sub.add_parser("run")
    run.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    run.add_argument("--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT)
    run.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.command == "run":
        payload = {"audit": str(run_no_return_audit(data_root=args.data_root, experiment_root=args.experiment_root, workers=args.workers))}
    else:
        payload = status(args.experiment_root)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
