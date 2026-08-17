#!/usr/bin/env python3
"""Run Campaign110's frozen coverage-first all-133 no-return audit."""

from __future__ import annotations

import gc
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign109_no_return_audit.py"
)
BASE_RUNNER_SHA256 = "7c487fde1b4b7e789d0f6f8602c7384be5d2c58d7278121c7a8a6770dcd4ba9f"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _file_sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign109 no-return audit changed")


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign109", "Campaign110"),
    ("campaign109", "campaign110"),
    ("campaign_109", "campaign_110"),
    (
        "a_share_three_day_walkforward_campaign110_features as candidate",
        "a_share_three_day_walkforward_campaign110_features as candidate",
    ),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign110_no_return_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)

_base_generated: dict[str, Any] = _generated["_generated"]
Campaign110NoReturnAuditError = _generated["Campaign110NoReturnAuditError"]

from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign107_comparator_adapter as adapter,
)
from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign107_no_return_audit as c107_audit,
)
from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign109_features as c109,
)
from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign109_no_return_audit as c109_audit,
)
from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign110_features as candidate,
)


FACTOR_NAME = candidate.FACTOR_NAME
DEFAULT_DATA_ROOT = candidate.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_110/no_return"
)
SNAPSHOT_MANIFEST_PATH = (
    candidate.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
)
SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_110_feature_snapshot_binding_20260808.json"
)
AUDIT_ACTIVATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_110_no_return_audit_activation_binding_20260808.json"
)
ADAPTER_FREEZE = c109_audit.ADAPTER_FREEZE
ADAPTER_FREEZE_SHA256 = c109_audit.ADAPTER_FREEZE_SHA256
C109_MANIFEST_PATH = c109.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
C109_MANIFEST_SHA256 = (
    "b212eac0921bbca2c3a84c6eceb7f6741939c52ccb96a21e3897d1533c8b6aba"
)
C109_DATASET_SHA256 = "f222c80e80acb9872cc7e29a0fc89ab37e51bc1ee02f40f19f683c3757fcdb90"
C109_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_109_feature_snapshot_binding_20260808.json"
)
C109_BINDING_SHA256 = "eb5df1a26abdcb4252a4299ef16c7aef856032ee271b43407dd3379393cb9a64"
EXPECTED_ROWS = candidate.EXPECTED_ROWS
EXPECTED_PARTITIONS = candidate.EXPECTED_PARTITIONS
EXPECTED_COMPARISON_COUNT = candidate.NUMERIC_COMPARATOR_COUNT
GENERATED_DOCSTRING = (
    "Run Campaign110's frozen coverage-first all-133 no-return audit."
)


def _validate_adapter_freeze() -> dict[str, Any]:
    return c109_audit._generated["_validate_adapter_freeze"]()


def load_protocol() -> dict[str, Any]:
    frozen = candidate.load_protocol()
    gates = list(frozen.get("ordered_no_return_gates") or [])
    if [item.get("gate") for item in gates] != [1, 2, 3]:
        raise Campaign110NoReturnAuditError("Campaign110 gate order changed")
    runtime = json.loads(json.dumps(frozen))
    runtime["frozen_ordered_no_return_gates"] = gates
    runtime["ordered_no_return_gates"] = {
        "coverage_and_capacity_before_comparison_values": {
            "holding_period_sessions": 3,
            "minimum_median_coverage": 0.95,
            "minimum_p05_coverage": 0.90,
            "minimum_p05_eligible_names": 50,
            "minimum_non_overlapping_three_session_cohorts": 200,
            "minimum_observed_calendar_years": 5,
        },
        "uniqueness_after_coverage_only": {
            "comparison_factors": candidate.reconstruct_comparisons(),
            "minimum_pairwise_names_per_session": 50,
            "minimum_pairwise_sessions_per_comparison": 100,
            "maximum_allowed_absolute_median_daily_rank_correlation": 0.8,
            "all_numeric_comparators_must_pass": True,
            "insufficient_pairwise_overlap_fails_closed": True,
            "raw_comparator_nan_preserved_until_pairwise_overlap": True,
        },
    }
    return runtime


def _load_activation_binding() -> dict[str, Any]:
    candidate._validate_implementation_freeze()
    _validate_adapter_freeze()
    if not AUDIT_ACTIVATION_BINDING.is_file():
        raise Campaign110NoReturnAuditError("Campaign110 audit activation is absent")
    record = json.loads(AUDIT_ACTIVATION_BINDING.read_text(encoding="utf-8"))
    snapshot = record.get("candidate_snapshot") or {}
    binding = record.get("snapshot_binding") or {}
    c102_source = record.get("first_130_directional_comparators") or {}
    c103_source = record.get("comparator_131") or {}
    c105_source = record.get("comparator_132") or {}
    c109_source = record.get("comparator_133") or {}
    adapter_source = record.get("raw_comparator_adapter_freeze") or {}
    c107_inner = c107_audit._generated
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign110_no_return_audit_activation_binding"
        and record.get("status")
        == "frozen_after_verified_candidate_snapshot_before_coverage_or_comparator_values"
        and (record.get("implementation_freeze") or {}).get("sha256")
        == candidate._sha256(candidate.DEFAULT_IMPLEMENTATION_FREEZE)
        and binding.get("path") == str(SNAPSHOT_BINDING.relative_to(REPO_ROOT))
        and len(str(binding.get("sha256") or "")) == 64
        and snapshot.get("path") == str(SNAPSHOT_MANIFEST_PATH.resolve())
        and len(str(snapshot.get("sha256") or "")) == 64
        and len(str(snapshot.get("dataset_sha256") or "")) == 64
        and snapshot.get("partitions") == EXPECTED_PARTITIONS
        and snapshot.get("rows") == EXPECTED_ROWS
        and 0 <= int(snapshot.get("eligible_rows", -1)) <= EXPECTED_ROWS
        and c102_source.get("path") == str(c107_inner["C102_MANIFEST_PATH"])
        and c102_source.get("sha256") == c107_inner["C102_MANIFEST_SHA256"]
        and c102_source.get("dataset_sha256")
        == c107_inner["C102_DATASET_SHA256"]
        and c102_source.get("factor_count") == 130
        and c103_source.get("path") == str(c107_inner["C103_MANIFEST_PATH"])
        and c103_source.get("sha256") == c107_inner["C103_MANIFEST_SHA256"]
        and c103_source.get("dataset_sha256")
        == c107_inner["C103_DATASET_SHA256"]
        and c103_source.get("factor") == c107_audit.c103.FACTOR_NAME
        and c103_source.get("value_range") == [0.0, 1.0]
        and c105_source.get("path") == str(c107_audit.C105_MANIFEST_PATH)
        and c105_source.get("sha256") == c107_audit.C105_MANIFEST_SHA256
        and c105_source.get("dataset_sha256") == c107_audit.C105_DATASET_SHA256
        and c105_source.get("factor") == c107_audit.c105.FACTOR_NAME
        and c105_source.get("value_range") == [0.0, 1.0]
        and c109_source.get("path") == str(C109_MANIFEST_PATH)
        and c109_source.get("sha256") == C109_MANIFEST_SHA256
        and c109_source.get("dataset_sha256") == C109_DATASET_SHA256
        and c109_source.get("factor") == c109.FACTOR_NAME
        and c109_source.get("value_range") == [-1.0, 1.0]
        and adapter_source.get("path") == str(ADAPTER_FREEZE.relative_to(REPO_ROOT))
        and adapter_source.get("sha256") == ADAPTER_FREEZE_SHA256
        and record.get("coverage_or_capacity_metrics_computed_before_activation")
        is False
        and record.get("comparator_values_read_before_activation") is False
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_activation"
        )
        is False
        and record.get("provider_request_issued_before_activation") is False
        and record.get("single_use") is True
    ):
        raise Campaign110NoReturnAuditError("Campaign110 activation semantics changed")
    return record


def verify_static_bindings() -> dict[str, Any]:
    activation = _load_activation_binding()
    snapshot_binding = activation["snapshot_binding"]
    _base_generated["_require"](
        SNAPSHOT_BINDING, str(snapshot_binding["sha256"]), "candidate snapshot binding"
    )
    c107_inner = c107_audit._generated
    _base_generated["_require"](
        c107_inner["C102_MANIFEST_PATH"],
        c107_inner["C102_MANIFEST_SHA256"],
        "Campaign102 matrix manifest",
    )
    _base_generated["_require"](
        c107_inner["C103_MANIFEST_PATH"],
        c107_inner["C103_MANIFEST_SHA256"],
        "Campaign103 manifest",
    )
    _base_generated["_require"](
        c107_inner["C103_BINDING"],
        c107_inner["C103_BINDING_SHA256"],
        "Campaign103 snapshot binding",
    )
    _base_generated["_require"](
        c107_audit.C105_MANIFEST_PATH,
        c107_audit.C105_MANIFEST_SHA256,
        "Campaign105 manifest",
    )
    _base_generated["_require"](
        c107_audit.C105_BINDING,
        c107_audit.C105_BINDING_SHA256,
        "Campaign105 binding",
    )
    _base_generated["_require"](
        C109_MANIFEST_PATH, C109_MANIFEST_SHA256, "Campaign109 manifest"
    )
    _base_generated["_require"](C109_BINDING, C109_BINDING_SHA256, "Campaign109 binding")
    report = candidate.bindings.validate_record(
        SNAPSHOT_BINDING, data_root=DEFAULT_DATA_ROOT
    )
    if report.get("all_bindings_passed") is not True:
        raise Campaign110NoReturnAuditError("Campaign110 snapshot binding failed")
    return {
        "implementation_freeze_sha256": candidate._sha256(
            candidate.DEFAULT_IMPLEMENTATION_FREEZE
        ),
        "audit_activation_binding_sha256": candidate._sha256(
            AUDIT_ACTIVATION_BINDING
        ),
        "snapshot_binding_sha256": snapshot_binding["sha256"],
        "candidate_manifest_sha256": activation["candidate_snapshot"]["sha256"],
        "candidate_dataset_sha256": activation["candidate_snapshot"][
            "dataset_sha256"
        ],
        "adapter_freeze_sha256": ADAPTER_FREEZE_SHA256,
        "comparison_count": EXPECTED_COMPARISON_COUNT,
        "comparison_order_sha256": candidate.NUMERIC_COMPARATOR_ORDER_SHA256,
        "complete_definition_count": candidate.COMPLETE_DEFINITION_COUNT,
        "complete_definition_order_sha256": candidate.COMPLETE_DEFINITION_ORDER_SHA256,
        "comparator_values_read": False,
    }


def _load_comparisons_after_coverage(
    *,
    coverage: dict[str, Any],
    candidate_keys: np.ndarray,
    candidate_values: np.ndarray,
    gate: dict[str, Any],
    comparison_engine: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if coverage.get("gate_passed_before_comparison_values") is not True:
        raise Campaign110NoReturnAuditError(
            "comparison loader called before Campaign110 coverage pass"
        )
    _validate_adapter_freeze()
    context = c107_audit._generated[
        "cache_v4"
    ].v1.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    engine = context[2]
    registrations = c107_audit._register_raw_ranges(engine)
    registrations = adapter.register_raw_factor_range(
        registrations, factor=c109.FACTOR_NAME, value_range=(-1.0, 1.0)
    )
    engine.FACTOR_RANGES = registrations
    first_results, receipts = c109_audit._load_comparisons_after_coverage(
        coverage=coverage,
        candidate_keys=candidate_keys,
        candidate_values=candidate_values,
        gate=gate,
        comparison_engine=comparison_engine,
    )
    definitions = candidate.reconstruct_comparisons()
    if [item["comparison_factor"] for item in first_results] != [
        item["name"] for item in definitions[:132]
    ]:
        raise Campaign110NoReturnAuditError("first 132 comparator order changed")

    verification = c109.verify_snapshot_files(C109_MANIFEST_PATH, workers=4)
    if not (
        verification.get("manifest_sha256") == C109_MANIFEST_SHA256
        and verification.get("dataset_sha256") == C109_DATASET_SHA256
        and verification.get("rows") == EXPECTED_ROWS
    ):
        raise Campaign110NoReturnAuditError("Campaign109 comparator snapshot changed")
    manifest = json.loads(C109_MANIFEST_PATH.read_text(encoding="utf-8"))
    frame = engine.load_factor_frame(C109_MANIFEST_PATH, manifest, c109.FACTOR_NAME)
    source_keys, source_values = adapter.sorted_raw_comparator_arrays(
        frame,
        factor=c109.FACTOR_NAME,
        value_range=(-1.0, 1.0),
        compact_key_fn=comparison_engine._compact_stock_day_keys,
    )
    del frame
    gc.collect()
    aligned = adapter.align_raw_comparator_values(
        source_keys=source_keys,
        source_values=source_values,
        target_keys=candidate_keys,
    )
    legal_nan_count = int(np.isnan(aligned).sum())
    final_result = comparison_engine._aligned_comparison_result(
        candidate_keys=candidate_keys,
        candidate_values=candidate_values,
        comparison_values=aligned,
        comparison=c109.FACTOR_NAME,
        direction="higher",
        gate=gate,
    )
    final_result["source_score_direction"] = "higher"
    final_result["comparison_value_semantics"] = (
        "frozen Campaign109 raw factor value with legal NaN preserved until pairwise overlap"
    )
    final_result["aligned_legal_nan_count_before_pairwise_overlap"] = legal_nan_count
    results = [*first_results, final_result]
    if [item["comparison_factor"] for item in results] != [
        item["name"] for item in definitions
    ]:
        raise Campaign110NoReturnAuditError("Campaign110 comparison order changed")
    receipts = dict(receipts)
    receipts["raw_range_registrations"] = {
        **dict(receipts.get("raw_range_registrations") or {}),
        c109.FACTOR_NAME: list(registrations[c109.FACTOR_NAME]),
    }
    receipts["campaign109_comparator_133"] = {
        "manifest_path": str(C109_MANIFEST_PATH),
        "manifest_sha256": C109_MANIFEST_SHA256,
        "dataset_sha256": C109_DATASET_SHA256,
        "factor": c109.FACTOR_NAME,
        "legal_nan_preserved_count": legal_nan_count,
        "verification": verification,
    }
    receipts.pop("all_132_sources_loaded_in_frozen_order", None)
    receipts["all_133_sources_loaded_in_frozen_order"] = True
    return results, receipts


for _name, _value in {
    "candidate": candidate,
    "FACTOR_NAME": FACTOR_NAME,
    "DEFAULT_DATA_ROOT": DEFAULT_DATA_ROOT,
    "DEFAULT_EXPERIMENT_ROOT": DEFAULT_EXPERIMENT_ROOT,
    "SNAPSHOT_MANIFEST_PATH": SNAPSHOT_MANIFEST_PATH,
    "SNAPSHOT_BINDING": SNAPSHOT_BINDING,
    "AUDIT_ACTIVATION_BINDING": AUDIT_ACTIVATION_BINDING,
    "ADAPTER_FREEZE": ADAPTER_FREEZE,
    "ADAPTER_FREEZE_SHA256": ADAPTER_FREEZE_SHA256,
    "C109_MANIFEST_PATH": C109_MANIFEST_PATH,
    "C109_MANIFEST_SHA256": C109_MANIFEST_SHA256,
    "C109_DATASET_SHA256": C109_DATASET_SHA256,
    "C109_BINDING": C109_BINDING,
    "C109_BINDING_SHA256": C109_BINDING_SHA256,
    "EXPECTED_ROWS": EXPECTED_ROWS,
    "EXPECTED_PARTITIONS": EXPECTED_PARTITIONS,
    "EXPECTED_COMPARISON_COUNT": EXPECTED_COMPARISON_COUNT,
    "__doc__": GENERATED_DOCSTRING,
    "load_protocol": load_protocol,
    "_load_activation_binding": _load_activation_binding,
    "verify_static_bindings": verify_static_bindings,
    "_load_comparisons_after_coverage": _load_comparisons_after_coverage,
}.items():
    _generated[_name] = _value
    _base_generated[_name] = _value


verify_candidate_snapshot = _base_generated["verify_candidate_snapshot"]
run_no_return_audit = _base_generated["run_no_return_audit"]
status = _base_generated["status"]
main = _base_generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
