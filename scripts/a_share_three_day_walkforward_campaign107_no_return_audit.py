#!/usr/bin/env python3
"""Run Campaign107's frozen coverage-first all-132 no-return audit."""

from __future__ import annotations

import gc
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign105_no_return_audit.py"
)
BASE_RUNNER_SHA256 = "8adbd44b0bcf1054fc21dd75d0ee07c000928f7602b625cacfee748b02405a01"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _file_sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign105 no-return audit runner changed")


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign105", "Campaign107"),
    ("campaign105", "campaign107"),
    ("campaign_105", "campaign_107"),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign107_no_return_audit_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)

Campaign107NoReturnAuditError = _generated["Campaign107NoReturnAuditError"]

from scripts import (
    a_share_three_day_walkforward_campaign103_features as c103,
)  # noqa: E402
from scripts import (
    a_share_three_day_walkforward_campaign105_features as c105,
)  # noqa: E402
from scripts import (
    a_share_three_day_walkforward_campaign105_no_return_audit as base105,
)  # noqa: E402
from scripts import (
    a_share_three_day_walkforward_campaign107_comparator_adapter as adapter,
)  # noqa: E402
from scripts import (
    a_share_three_day_walkforward_campaign107_features as candidate,
)  # noqa: E402


FACTOR_NAME = candidate.FACTOR_NAME
DEFAULT_DATA_ROOT = candidate.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_107/no_return"
)
SNAPSHOT_MANIFEST_PATH = (
    candidate.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
)
SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_107_feature_snapshot_binding_20260808.json"
)
AUDIT_ACTIVATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_107_no_return_audit_activation_binding_20260808.json"
)
ADAPTER_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_107_raw_comparator_adapter_implementation_freeze_20260808.json"
)
ADAPTER_FREEZE_SHA256 = (
    "07de45590082fcf98350a4b4f0b615ffd994a97fe3cec431ae476c058a95cc2b"
)
C105_MANIFEST_PATH = c105.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
C105_MANIFEST_SHA256 = (
    "56e2d016087ff09643ef98dd00cad0ac9c771e815d19ec9941cea9f5904824a5"
)
C105_DATASET_SHA256 = "912625c3763fe3868adb4c4f410b6a6ab72c9272f78b8b57db620daaf970018c"
C105_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_105_feature_snapshot_binding_20260808.json"
)
C105_BINDING_SHA256 = "9a59fee881c7661f122727faefa018bdba014ca0c0c9a031f76f099216e3dd5d"
EXPECTED_ROWS = candidate.EXPECTED_ROWS
EXPECTED_PARTITIONS = candidate.EXPECTED_PARTITIONS
EXPECTED_COMPARISON_COUNT = candidate.NUMERIC_COMPARATOR_COUNT


def _validate_adapter_freeze() -> dict[str, Any]:
    adapter.validate_contract()
    _generated["_require"](ADAPTER_FREEZE, ADAPTER_FREEZE_SHA256, "adapter freeze")
    record = json.loads(ADAPTER_FREEZE.read_text(encoding="utf-8"))
    implementation = record.get("implementation") or {}
    synthetic = record.get("synthetic_test") or {}
    usage = record.get("frozen_usage") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign107_raw_comparator_adapter_implementation_freeze"
        and implementation.get("sha256")
        == _file_sha256(Path(adapter.__file__).resolve())
        and synthetic.get("result") == "10 passed"
        and usage.get("register_every_raw_numeric_comparator_range_before_loading")
        is True
        and usage.get(
            "use_sorted_raw_comparator_arrays_instead_of_candidate_only_sorter"
        )
        is True
        and usage.get("preserve_nan_until_frozen_pairwise_overlap_gate") is True
        and usage.get("candidate_specific_drop_imputation_or_rescue_allowed") is False
    ):
        raise Campaign107NoReturnAuditError("Campaign107 adapter freeze changed")
    return record


def load_protocol() -> dict[str, Any]:
    """Materialize fixed numeric gates from the validated base+overlay protocol."""

    effective = candidate.load_protocol()
    base = effective["base"]
    gates = list(base.get("ordered_no_return_gates") or [])
    if [item.get("gate") for item in gates] != [1, 2, 3]:
        raise Campaign107NoReturnAuditError("Campaign107 gate order changed")
    runtime = json.loads(json.dumps(base))
    runtime["effective_binding_overlay"] = effective["overlay"]
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
        raise Campaign107NoReturnAuditError("Campaign107 audit activation is absent")
    record = json.loads(AUDIT_ACTIVATION_BINDING.read_text(encoding="utf-8"))
    snapshot = record.get("candidate_snapshot") or {}
    binding = record.get("snapshot_binding") or {}
    c102_source = record.get("first_130_directional_comparators") or {}
    c103_source = record.get("comparator_131") or {}
    c105_source = record.get("comparator_132") or {}
    adapter_source = record.get("raw_comparator_adapter_freeze") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign107_no_return_audit_activation_binding"
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
        and c102_source.get("path") == str(_generated["C102_MANIFEST_PATH"])
        and c102_source.get("sha256") == _generated["C102_MANIFEST_SHA256"]
        and c102_source.get("dataset_sha256") == _generated["C102_DATASET_SHA256"]
        and c102_source.get("factor_count") == 130
        and c103_source.get("path") == str(_generated["C103_MANIFEST_PATH"])
        and c103_source.get("sha256") == _generated["C103_MANIFEST_SHA256"]
        and c103_source.get("dataset_sha256") == _generated["C103_DATASET_SHA256"]
        and c103_source.get("factor") == c103.FACTOR_NAME
        and c103_source.get("value_range") == [0.0, 1.0]
        and c105_source.get("path") == str(C105_MANIFEST_PATH)
        and c105_source.get("sha256") == C105_MANIFEST_SHA256
        and c105_source.get("dataset_sha256") == C105_DATASET_SHA256
        and c105_source.get("factor") == c105.FACTOR_NAME
        and c105_source.get("value_range") == [0.0, 1.0]
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
        raise Campaign107NoReturnAuditError("Campaign107 activation semantics changed")
    return record


def verify_static_bindings() -> dict[str, Any]:
    activation = _load_activation_binding()
    snapshot_binding = activation["snapshot_binding"]
    _generated["_require"](
        SNAPSHOT_BINDING, str(snapshot_binding["sha256"]), "candidate snapshot binding"
    )
    _generated["_require"](
        _generated["C102_MANIFEST_PATH"],
        _generated["C102_MANIFEST_SHA256"],
        "Campaign102 matrix manifest",
    )
    _generated["_require"](
        _generated["C103_MANIFEST_PATH"],
        _generated["C103_MANIFEST_SHA256"],
        "Campaign103 manifest",
    )
    _generated["_require"](
        _generated["C103_BINDING"],
        _generated["C103_BINDING_SHA256"],
        "Campaign103 snapshot binding",
    )
    _generated["_require"](
        C105_MANIFEST_PATH, C105_MANIFEST_SHA256, "Campaign105 manifest"
    )
    _generated["_require"](C105_BINDING, C105_BINDING_SHA256, "Campaign105 binding")
    report = candidate.bindings.validate_record(
        SNAPSHOT_BINDING, data_root=DEFAULT_DATA_ROOT
    )
    if report.get("all_bindings_passed") is not True:
        raise Campaign107NoReturnAuditError("Campaign107 snapshot binding failed")
    return {
        "implementation_freeze_sha256": candidate._sha256(
            candidate.DEFAULT_IMPLEMENTATION_FREEZE
        ),
        "audit_activation_binding_sha256": candidate._sha256(AUDIT_ACTIVATION_BINDING),
        "snapshot_binding_sha256": snapshot_binding["sha256"],
        "candidate_manifest_sha256": activation["candidate_snapshot"]["sha256"],
        "candidate_dataset_sha256": activation["candidate_snapshot"]["dataset_sha256"],
        "adapter_freeze_sha256": ADAPTER_FREEZE_SHA256,
        "comparison_count": EXPECTED_COMPARISON_COUNT,
        "comparison_order_sha256": candidate.NUMERIC_COMPARATOR_ORDER_SHA256,
        "complete_definition_count": candidate.COMPLETE_DEFINITION_COUNT,
        "complete_definition_order_sha256": candidate.COMPLETE_DEFINITION_ORDER_SHA256,
        "comparator_values_read": False,
    }


def _register_raw_ranges(engine: Any) -> dict[str, tuple[float, float]]:
    ranges = adapter.register_raw_factor_range(
        getattr(engine, "FACTOR_RANGES", {}),
        factor=c103.FACTOR_NAME,
        value_range=(0.0, 1.0),
    )
    ranges = adapter.register_raw_factor_range(
        ranges, factor=c105.FACTOR_NAME, value_range=(0.0, 1.0)
    )
    engine.FACTOR_RANGES = ranges
    return ranges


def _load_comparisons_after_coverage(
    *,
    coverage: dict[str, Any],
    candidate_keys: np.ndarray,
    candidate_values: np.ndarray,
    gate: dict[str, Any],
    comparison_engine: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if coverage.get("gate_passed_before_comparison_values") is not True:
        raise Campaign107NoReturnAuditError(
            "comparison loader called before Campaign107 coverage pass"
        )
    _validate_adapter_freeze()
    context = _generated[
        "cache_v4"
    ].v1.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    engine = context[2]
    registrations = _register_raw_ranges(engine)
    first_results, receipts = base105._load_comparisons_after_coverage(
        coverage=coverage,
        candidate_keys=candidate_keys,
        candidate_values=candidate_values,
        gate=gate,
        comparison_engine=comparison_engine,
    )
    definitions = candidate.reconstruct_comparisons()
    if [item["comparison_factor"] for item in first_results] != [
        item["name"] for item in definitions[:131]
    ]:
        raise Campaign107NoReturnAuditError("first 131 comparator order changed")

    verification = c105.verify_snapshot_files(C105_MANIFEST_PATH, workers=4)
    if not (
        verification.get("manifest_sha256") == C105_MANIFEST_SHA256
        and verification.get("dataset_sha256") == C105_DATASET_SHA256
        and verification.get("rows") == EXPECTED_ROWS
    ):
        raise Campaign107NoReturnAuditError("Campaign105 comparator snapshot changed")
    manifest = json.loads(C105_MANIFEST_PATH.read_text(encoding="utf-8"))
    frame = engine.load_factor_frame(C105_MANIFEST_PATH, manifest, c105.FACTOR_NAME)
    source_keys, source_values = adapter.sorted_raw_comparator_arrays(
        frame,
        factor=c105.FACTOR_NAME,
        value_range=(0.0, 1.0),
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
        comparison=c105.FACTOR_NAME,
        direction="higher",
        gate=gate,
    )
    final_result["source_score_direction"] = "higher"
    final_result["comparison_value_semantics"] = (
        "frozen Campaign105 raw factor value with legal NaN preserved until pairwise overlap"
    )
    final_result["aligned_legal_nan_count_before_pairwise_overlap"] = legal_nan_count
    results = [*first_results, final_result]
    if [item["comparison_factor"] for item in results] != [
        item["name"] for item in definitions
    ]:
        raise Campaign107NoReturnAuditError("Campaign107 comparison order changed")
    receipts = dict(receipts)
    receipts["raw_range_registrations"] = {
        c103.FACTOR_NAME: list(registrations[c103.FACTOR_NAME]),
        c105.FACTOR_NAME: list(registrations[c105.FACTOR_NAME]),
    }
    receipts["campaign105_comparator_132"] = {
        "manifest_path": str(C105_MANIFEST_PATH),
        "manifest_sha256": C105_MANIFEST_SHA256,
        "dataset_sha256": C105_DATASET_SHA256,
        "factor": c105.FACTOR_NAME,
        "legal_nan_preserved_count": legal_nan_count,
        "verification": verification,
    }
    receipts.pop("all_131_sources_loaded_in_frozen_order", None)
    receipts["all_132_sources_loaded_in_frozen_order"] = True
    return results, receipts


for _name, _value in {
    "candidate": candidate,
    "FACTOR_NAME": FACTOR_NAME,
    "DEFAULT_DATA_ROOT": DEFAULT_DATA_ROOT,
    "DEFAULT_EXPERIMENT_ROOT": DEFAULT_EXPERIMENT_ROOT,
    "SNAPSHOT_MANIFEST_PATH": SNAPSHOT_MANIFEST_PATH,
    "SNAPSHOT_BINDING": SNAPSHOT_BINDING,
    "AUDIT_ACTIVATION_BINDING": AUDIT_ACTIVATION_BINDING,
    "EXPECTED_ROWS": EXPECTED_ROWS,
    "EXPECTED_PARTITIONS": EXPECTED_PARTITIONS,
    "EXPECTED_COMPARISON_COUNT": EXPECTED_COMPARISON_COUNT,
    "load_protocol": load_protocol,
    "_load_activation_binding": _load_activation_binding,
    "verify_static_bindings": verify_static_bindings,
    "_load_comparisons_after_coverage": _load_comparisons_after_coverage,
}.items():
    _generated[_name] = _value


verify_candidate_snapshot = _generated["verify_candidate_snapshot"]
run_no_return_audit = _generated["run_no_return_audit"]
status = _generated["status"]
_directionally_normalized_result = _generated["_directionally_normalized_result"]
_aligned_columns = _generated["_aligned_columns"]
_sha256 = _generated["_sha256"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
