#!/usr/bin/env python3
"""Run Campaign108's frozen coverage-first all-132 no-return audit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


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
    ("Campaign105", "Campaign108"),
    ("campaign105", "campaign108"),
    ("campaign_105", "campaign_108"),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign108_no_return_audit_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)

Campaign108NoReturnAuditError = _generated["Campaign108NoReturnAuditError"]

from scripts import (
    a_share_three_day_walkforward_campaign103_features as c103,
)  # noqa: E402
from scripts import (
    a_share_three_day_walkforward_campaign105_features as c105,
)  # noqa: E402
from scripts import (
    a_share_three_day_walkforward_campaign107_no_return_audit as c107_audit,
)  # noqa: E402
from scripts import (
    a_share_three_day_walkforward_campaign108_features as candidate,
)  # noqa: E402


FACTOR_NAME = candidate.FACTOR_NAME
DEFAULT_DATA_ROOT = candidate.DEFAULT_DATA_ROOT
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_108/no_return"
)
SNAPSHOT_MANIFEST_PATH = (
    candidate.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
)
SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_108_feature_snapshot_binding_20260808.json"
)
AUDIT_ACTIVATION_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_108_no_return_audit_activation_binding_20260808.json"
)
ADAPTER_FREEZE = c107_audit.ADAPTER_FREEZE
ADAPTER_FREEZE_SHA256 = c107_audit.ADAPTER_FREEZE_SHA256
C105_MANIFEST_PATH = c107_audit.C105_MANIFEST_PATH
C105_MANIFEST_SHA256 = c107_audit.C105_MANIFEST_SHA256
C105_DATASET_SHA256 = c107_audit.C105_DATASET_SHA256
C105_BINDING = c107_audit.C105_BINDING
C105_BINDING_SHA256 = c107_audit.C105_BINDING_SHA256
EXPECTED_ROWS = candidate.EXPECTED_ROWS
EXPECTED_PARTITIONS = candidate.EXPECTED_PARTITIONS
EXPECTED_COMPARISON_COUNT = candidate.NUMERIC_COMPARATOR_COUNT


def _validate_adapter_freeze() -> dict[str, Any]:
    return c107_audit._validate_adapter_freeze()


def load_protocol() -> dict[str, Any]:
    frozen = candidate.load_protocol()
    gates = list(frozen.get("ordered_no_return_gates") or [])
    if [item.get("gate") for item in gates] != [1, 2, 3]:
        raise Campaign108NoReturnAuditError("Campaign108 gate order changed")
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
        raise Campaign108NoReturnAuditError("Campaign108 audit activation is absent")
    record = json.loads(AUDIT_ACTIVATION_BINDING.read_text(encoding="utf-8"))
    snapshot = record.get("candidate_snapshot") or {}
    binding = record.get("snapshot_binding") or {}
    c102_source = record.get("first_130_directional_comparators") or {}
    c103_source = record.get("comparator_131") or {}
    c105_source = record.get("comparator_132") or {}
    adapter_source = record.get("raw_comparator_adapter_freeze") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign108_no_return_audit_activation_binding"
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
        raise Campaign108NoReturnAuditError("Campaign108 activation semantics changed")
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
        raise Campaign108NoReturnAuditError("Campaign108 snapshot binding failed")
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


def _load_comparisons_after_coverage(
    **kwargs: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if (kwargs.get("coverage") or {}).get(
        "gate_passed_before_comparison_values"
    ) is not True:
        raise Campaign108NoReturnAuditError(
            "comparison loader called before Campaign108 coverage pass"
        )
    return c107_audit._load_comparisons_after_coverage(**kwargs)


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
_sha256 = _generated["_sha256"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
