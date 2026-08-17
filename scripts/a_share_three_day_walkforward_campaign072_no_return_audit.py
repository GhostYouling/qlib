#!/usr/bin/env python3
"""Run Campaign072's frozen coverage-first, no-return overlap audit."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts import a_share_three_day_compact_comparator_cache_v4 as cache_v4
from scripts import a_share_three_day_walkforward_campaign071_features as c71
from scripts import a_share_three_day_walkforward_campaign072_features as candidate


C70_SNAPSHOT_DATASET_SHA256 = "35ea87d9e183b77a382a88789cedf96d79f6a102c5006e156bbde2ff87fd6efe"
C70_SNAPSHOT_BINDING_SHA256 = "4c573c47ce247cac96c492ae37f93c39356303db18f05c093f1446a765e8aa34"
candidate.C70_SNAPSHOT_DATASET_SHA256 = C70_SNAPSHOT_DATASET_SHA256
candidate.C70_SNAPSHOT_BINDING_SHA256 = C70_SNAPSHOT_BINDING_SHA256


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign071_no_return_audit.py"
TEMPLATE_SHA256 = "ecfd195d1853135b09ce29ac38d15ca481ff56e6aaabc6bfdb3070aa122159c3"
SNAPSHOT_MANIFEST_SHA256 = "14ca00ed8b9a233475445a2cedc4a0bbd57c35030e6de2948c80177156c98c2c"
SNAPSHOT_DATASET_SHA256 = "7baf6939336261bb307fd3dc13ccb8e9676eacbcc7e7d1139e019fb3b96f90b3"
SNAPSHOT_BINDING_SHA256 = "eb36b61ecc800b13e40f8947da5b0fd049542df784baafc8f86a3c38c82b2d1d"
SEQUENCE_RECORD_SHA256 = "cddf3537c70ea033cfc14a5e0b85e798d5d50ae9a4e4fba5228c792bf15f465f"
EXPECTED_ELIGIBLE_ROWS = 7_231_483
EXPECTED_COMPARISON_COUNT = 102
EXPECTED_COMPLETE_DEFINITION_COUNT = 103
EXPECTED_COMPARISON_ORDER_SHA256 = candidate.COMPARISON_ORDER_SHA256
EXPECTED_COMPLETE_DEFINITION_ORDER_SHA256 = candidate.FULL_DEFINITION_ORDER_SHA256
C71_SNAPSHOT_MANIFEST_PATH = c71.output_root(candidate.DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
C71_SNAPSHOT_BINDING = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_071_feature_snapshot_binding_20260806.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if not TEMPLATE.is_file() or _sha256(TEMPLATE) != TEMPLATE_SHA256:
    raise RuntimeError("frozen Campaign071 no-return audit runner changed")


_source = TEMPLATE.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign071", "Campaign072"),
    ("campaign071", "campaign072"),
    ("campaign_071", "campaign_072"),
    (
        "scripts import a_share_three_day_walkforward_campaign071_features as candidate",
        "scripts import a_share_three_day_walkforward_campaign072_features as candidate",
    ),
    ("438db2c72a0e5a166f87e680109024be7b28ed710edbd6b4d5ce6968e4a3f7fd", SNAPSHOT_MANIFEST_SHA256),
    ("8c6f1eff1b2238132f429eaeae13d9a7fbd9956e89f3499fa1cf68d54435528d", SNAPSHOT_DATASET_SHA256),
    ("8b6cb0bbab838bc72977ce0b8c59e4b1894633cfe78c903de01a2fcc65749a71", SNAPSHOT_BINDING_SHA256),
    ("fc73c79f4a7719d6ebeda10056352377f0d14985844fd3a0f88d11289baf9734", SEQUENCE_RECORD_SHA256),
    ("EXPECTED_ELIGIBLE_ROWS = 7_081_458", "EXPECTED_ELIGIBLE_ROWS = 7_231_483"),
    ("EXPECTED_COMPARISON_COUNT = 101", "EXPECTED_COMPARISON_COUNT = 102"),
    ("EXPECTED_COMPLETE_DEFINITION_COUNT = 102", "EXPECTED_COMPLETE_DEFINITION_COUNT = 103"),
    ("all_101_sources_loaded_in_frozen_order", "all_102_sources_loaded_in_frozen_order"),
):
    _source = _source.replace(_old, _new)

_runtime: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign072_no_return_audit_generated",
}
exec(compile(_source, str(TEMPLATE), "exec"), _runtime)

Campaign072NoReturnAuditError = _runtime["Campaign072NoReturnAuditError"]
FACTOR_NAME = candidate.FACTOR_NAME
DEFAULT_DATA_ROOT = candidate.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_072/no_return"
SNAPSHOT_MANIFEST_PATH = candidate.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
SNAPSHOT_BINDING = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_072_feature_snapshot_binding_20260806.json"
SEQUENCE_RECORD = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_072_audit_freeze_sequence_record_20260806.json"
AUDIT_IMPLEMENTATION_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_072_no_return_audit_implementation_freeze_v5_20260806.json"
AUDIT_ACTIVATION_BINDING = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_072_no_return_audit_activation_binding_v5_20260806.json"
TEST_PATH = REPO_ROOT / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign072_no_return_audit.py"
POSTCOVERAGE_FAILURE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_072_postcoverage_inner_append_helper_failure_20260806.json"
POSTCOVERAGE_FAILURE_SHA256 = "35c2357609669aa6f2680ea56a10ebc3a3a4b970ce8697a1785b2efd1f94bcbd"


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
            {"name": candidate.C71_FACTOR, "score_direction": "higher"},
        ]
    )
    if not (
        len(comparisons) == EXPECTED_COMPARISON_COUNT
        and candidate._runtime["_comparison_order_digest"](comparisons)
        == EXPECTED_COMPARISON_ORDER_SHA256
        and len(complete) == EXPECTED_COMPLETE_DEFINITION_COUNT
        and candidate._runtime["_comparison_order_digest"](complete)
        == EXPECTED_COMPLETE_DEFINITION_ORDER_SHA256
    ):
        raise Campaign072NoReturnAuditError("Campaign072 comparison order changed")
    spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"][
        "comparison_factors"
    ] = comparisons
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not AUDIT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign072NoReturnAuditError("Campaign072 v5 audit implementation freeze is absent")
    record = json.loads(AUDIT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    prior = record.get("prior_postcoverage_failure") or {}
    if not (
        record.get("version") == 5
        and record.get("kind")
        == "a_share_three_day_walkforward_campaign072_no_return_audit_implementation_freeze"
        and record.get("status")
        == "frozen_after_recorded_inner_helper_failure_before_repaired_retry"
        and (record.get("audit_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and (record.get("sequence_record") or {}).get("sha256")
        == SEQUENCE_RECORD_SHA256
        and prior.get("path") == str(POSTCOVERAGE_FAILURE.relative_to(REPO_ROOT))
        and prior.get("sha256") == POSTCOVERAGE_FAILURE_SHA256
        and _sha256(POSTCOVERAGE_FAILURE) == POSTCOVERAGE_FAILURE_SHA256
        and record.get("coverage_or_capacity_metrics_previously_computed") is True
        and record.get("comparison_values_previously_read") is True
        and record.get("historical_daily_price_fields_read") == []
        and record.get("historical_forward_returns_read") is False
        and record.get("provider_request_issued") is False
    ):
        raise Campaign072NoReturnAuditError("Campaign072 v5 audit implementation freeze changed")
    return record


def _load_activation_binding() -> dict[str, Any]:
    _load_implementation_freeze()
    if not AUDIT_ACTIVATION_BINDING.is_file():
        raise Campaign072NoReturnAuditError("Campaign072 v5 audit activation binding is absent")
    record = json.loads(AUDIT_ACTIVATION_BINDING.read_text(encoding="utf-8"))
    snapshot = record.get("candidate_snapshot") or {}
    if not (
        record.get("version") == 5
        and record.get("kind")
        == "a_share_three_day_walkforward_campaign072_no_return_audit_activation_binding"
        and record.get("status")
        == "frozen_after_prior_comparison_reads_before_inner_helper_retry"
        and (record.get("implementation_freeze") or {}).get("sha256")
        == _sha256(AUDIT_IMPLEMENTATION_FREEZE)
        and (record.get("snapshot_binding") or {}).get("sha256")
        == SNAPSHOT_BINDING_SHA256
        and snapshot.get("path") == str(SNAPSHOT_MANIFEST_PATH.resolve())
        and snapshot.get("sha256") == SNAPSHOT_MANIFEST_SHA256
        and snapshot.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
        and record.get("coverage_or_capacity_metrics_previously_computed") is True
        and record.get("comparison_values_previously_read") is True
        and record.get("historical_daily_price_fields_read") == []
        and record.get("historical_forward_returns_read") is False
        and record.get("provider_request_issued") is False
    ):
        raise Campaign072NoReturnAuditError("Campaign072 v5 audit activation binding changed")
    return record


_base_verify_static_bindings = _runtime["verify_static_bindings"]


def verify_static_bindings() -> dict[str, Any]:
    report = _base_verify_static_bindings()
    if _sha256(C71_SNAPSHOT_MANIFEST_PATH) != candidate.C71_SNAPSHOT_MANIFEST_SHA256:
        raise Campaign072NoReturnAuditError("Campaign071 comparator manifest changed")
    if _sha256(C71_SNAPSHOT_BINDING) != candidate.C71_SNAPSHOT_BINDING_SHA256:
        raise Campaign072NoReturnAuditError("Campaign071 comparator binding changed")
    c71_manifest = json.loads(C71_SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    if c71_manifest.get("dataset_sha256") != candidate.C71_SNAPSHOT_DATASET_SHA256:
        raise Campaign072NoReturnAuditError("Campaign071 comparator dataset changed")
    report["campaign071_comparator_manifest_sha256"] = candidate.C71_SNAPSHOT_MANIFEST_SHA256
    report["campaign071_comparator_dataset_sha256"] = candidate.C71_SNAPSHOT_DATASET_SHA256
    return report


_base_install_ranges = _runtime["_install_frozen_ranges"]


def _install_frozen_ranges(engine: Any) -> None:
    _base_install_ranges(engine)
    ranges = dict(getattr(engine, "FACTOR_RANGES", {}))
    if candidate.C71_FACTOR in ranges and tuple(ranges[candidate.C71_FACTOR]) != (0.0, 1.0):
        raise Campaign072NoReturnAuditError("Campaign071 comparator range changed")
    ranges[candidate.C71_FACTOR] = (0.0, 1.0)
    engine.FACTOR_RANGES = ranges


_base_load_comparisons = _runtime["_load_comparisons_after_coverage"]


def _load_comparisons_after_coverage(
    **kwargs: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    inherited_expected = _runtime.get("EXPECTED_COMPARISON_COUNT")
    _runtime["EXPECTED_COMPARISON_COUNT"] = 101
    try:
        comparisons, receipts = _base_load_comparisons(**kwargs)
    finally:
        _runtime["EXPECTED_COMPARISON_COUNT"] = inherited_expected
    if len(comparisons) != 101:
        raise Campaign072NoReturnAuditError(
            "Campaign071 inherited comparison count changed before Campaign071 append"
        )
    helper_runtime = _runtime.get("_runtime")
    if not isinstance(helper_runtime, dict) or "_append_snapshot_comparison" not in helper_runtime:
        raise Campaign072NoReturnAuditError("Campaign072 inner snapshot append helper is absent")
    result, receipt = helper_runtime["_append_snapshot_comparison"](
        manifest_path=C71_SNAPSHOT_MANIFEST_PATH,
        factor=candidate.C71_FACTOR,
        candidate_keys=kwargs["candidate_keys"],
        candidate_values=kwargs["candidate_values"],
        gate=kwargs["gate"],
        engine=kwargs["engine"],
        comparison_engine=kwargs["comparison_engine"],
        workers=kwargs["workers"],
        verifier=c71.verify_snapshot_files,
    )
    comparisons.append(result)
    receipts["campaign071_snapshot"] = receipt
    receipts["all_102_sources_loaded_in_frozen_order"] = True
    if len(comparisons) != EXPECTED_COMPARISON_COUNT:
        raise Campaign072NoReturnAuditError("Campaign072 comparison count changed")
    gc.collect()
    return comparisons, receipts


_override_map = {
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
    "_load_implementation_freeze": _load_implementation_freeze,
    "_load_activation_binding": _load_activation_binding,
    "verify_static_bindings": verify_static_bindings,
    "_install_frozen_ranges": _install_frozen_ranges,
    "_load_comparisons_after_coverage": _load_comparisons_after_coverage,
}
for _name, _value in _override_map.items():
    _runtime[_name] = _value

_inner_runtime = _runtime.get("_runtime")
if not isinstance(_inner_runtime, dict):
    raise RuntimeError("Campaign072 inherited audit runtime is absent")
for _name, _value in _override_map.items():
    _inner_runtime[_name] = _value

run_no_return_audit = _runtime["run_no_return_audit"]


def status(experiment_root: Path = DEFAULT_EXPERIMENT_ROOT) -> dict[str, Any]:
    audits = sorted(
        experiment_root.expanduser().resolve().glob("*_campaign072_no_return_audit.json")
    )
    return {
        "audit_implementation_freeze_exists": AUDIT_IMPLEMENTATION_FREEZE.is_file(),
        "audit_activation_binding_exists": AUDIT_ACTIVATION_BINDING.is_file(),
        "candidate_snapshot_exists": SNAPSHOT_MANIFEST_PATH.is_file(),
        "audit_count": len(audits),
        "coverage_or_capacity_metrics_previously_computed": True,
        "comparison_values_read_by_status": True,
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
        payload = {
            "audit": str(
                run_no_return_audit(
                    data_root=args.data_root,
                    experiment_root=args.experiment_root,
                    workers=args.workers,
                )
            )
        }
    else:
        payload = status(args.experiment_root)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
