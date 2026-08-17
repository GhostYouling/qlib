#!/usr/bin/env python3
"""Snapshot-bound Campaign057 ordered no-return audit implementation."""

from __future__ import annotations

import gc
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_AUDIT = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign056_no_return_audit.py"
BASE_AUDIT_SHA256 = "95332e841b643b66818983549613149a2e6ba445fcbfa19138088dd1288786c1"
BASE_FACTOR = "intraday_day_over_day_amount_profile_similarity_240b"
FACTOR_NAME = "intraday_day_over_day_absolute_return_profile_similarity_238b"
EXPECTED_COMPARISON_COUNT = 80
EXPECTED_COMPARISON_ORDER_SHA256 = "67e70655596658de91c8285ff998c17e8d2a7d83d0f571d416182e635e8180ae"

# These publication identities are replaced exactly once after the frozen
# Campaign057 snapshot and its additive binding record exist.  The audit is
# not executable while any sentinel remains.
SNAPSHOT_BINDING_SHA256 = "a48d754e8b64201e35fd324e5f894957f0347932915ba3aaca85b7c873903e62"
SNAPSHOT_MANIFEST_SHA256 = "7aba63621b2c6bd2b9d511d11ab56fc5331ae1dcf7a3c6055dbe6455d437d0ed"
SNAPSHOT_DATASET_SHA256 = "b24d183b15feb98015d7353160740273ffb5acc14dcf0031a984d9eb3003f19d"
EXPECTED_ELIGIBLE_ROWS = 7_671_540


def _local_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _local_sha256(BASE_AUDIT) != BASE_AUDIT_SHA256:
    raise RuntimeError("frozen Campaign056 no-return audit changed")

_source = BASE_AUDIT.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign056", "Campaign057"),
    ("campaign056", "campaign057"),
    ("campaign_056", "campaign_057"),
    (BASE_FACTOR, FACTOR_NAME),
    ("c9e8e1edeeb1ded3bb1d913d078f7cf26c06f5b2c9e88124aa774355a57e92f2", SNAPSHOT_BINDING_SHA256),
    ("cec4ce7db7a5a0a1715a8a117a09b74afe75bd94e3042df52493678ca6d6031b", SNAPSHOT_MANIFEST_SHA256),
    ("b29accb9698fd6d62238540f49b85a32c6a3e7fd882bc64cb7fabd7ef1ec1d02", SNAPSHOT_DATASET_SHA256),
    ("EXPECTED_ELIGIBLE_ROWS = 7_715_898", "EXPECTED_ELIGIBLE_ROWS = 7_671_540"),
    ("EXPECTED_COMPARISON_COUNT = 79", "EXPECTED_COMPARISON_COUNT = 80"),
    ("669a996cc0b8d2582f8a1c0cd2f7d9a8503fdcfe7fb5f1b79033ac7832bb4e67", EXPECTED_COMPARISON_ORDER_SHA256),
    ('"minute_amount_fields_read": ["amount"],', '"minute_amount_fields_read": [],'),
    ('"minute_open_high_low_close_volume_fields_read": [],', '"minute_open_high_low_close_volume_fields_read": ["close"],'),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign057_no_return_audit_generated",
}
exec(compile(_source, str(BASE_AUDIT), "exec"), _generated)

from scripts import a_share_three_day_walkforward_campaign056_no_return_audit as c56_audit

Campaign057NoReturnAuditError = _generated["Campaign057NoReturnAuditError"]
candidate = _generated["candidate"]
prior_audit = _generated["prior_audit"]
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT = _generated["DEFAULT_EXPERIMENT_ROOT"]
SNAPSHOT_BINDING = _generated["SNAPSHOT_BINDING"]
SNAPSHOT_MANIFEST_PATH = _generated["SNAPSHOT_MANIFEST_PATH"]
EXPECTED_ROWS = _generated["EXPECTED_ROWS"]
EXPECTED_PARTITIONS = _generated["EXPECTED_PARTITIONS"]
C56_SNAPSHOT_PATH = c56_audit.SNAPSHOT_MANIFEST_PATH

for _name, _value in {
    "SNAPSHOT_BINDING_SHA256": SNAPSHOT_BINDING_SHA256,
    "SNAPSHOT_MANIFEST_SHA256": SNAPSHOT_MANIFEST_SHA256,
    "SNAPSHOT_DATASET_SHA256": SNAPSHOT_DATASET_SHA256,
    "EXPECTED_ELIGIBLE_ROWS": EXPECTED_ELIGIBLE_ROWS,
    "EXPECTED_COMPARISON_COUNT": EXPECTED_COMPARISON_COUNT,
    "EXPECTED_COMPARISON_ORDER_SHA256": EXPECTED_COMPARISON_ORDER_SHA256,
}.items():
    _generated[_name] = _value


def _require_finalized_identities() -> None:
    values = (
        SNAPSHOT_BINDING_SHA256,
        SNAPSHOT_MANIFEST_SHA256,
        SNAPSHOT_DATASET_SHA256,
    )
    if EXPECTED_ELIGIBLE_ROWS < 0 or any(value.startswith("__") for value in values):
        raise Campaign057NoReturnAuditError(
            "Campaign057 audit identities are not frozen"
        )


_base_verify_static_bindings = _generated["verify_static_bindings"]


def verify_static_bindings() -> dict[str, Any]:
    _require_finalized_identities()
    return _base_verify_static_bindings()


def _load_bound_prior_snapshots(workers: int) -> dict[str, Any]:
    snapshots = c56_audit._load_bound_prior_snapshots(workers)
    c56_path = C56_SNAPSHOT_PATH.resolve()
    c56_audit._require_file(
        c56_path,
        c56_audit.SNAPSHOT_MANIFEST_SHA256,
        "Campaign056 terminal snapshot",
    )
    manifest = json.loads(c56_path.read_text(encoding="utf-8"))
    if manifest.get("dataset_sha256") != c56_audit.SNAPSHOT_DATASET_SHA256:
        raise Campaign057NoReturnAuditError("Campaign056 snapshot dataset changed")
    verification = c56_audit.candidate.verify_snapshot_files(
        c56_path, workers=workers
    )
    return {
        **snapshots,
        "c56_manifest": manifest,
        "c56_verification": verification,
    }


def _append_all_prior_comparisons(
    *,
    data_root: Path,
    workers: int,
    keys: Any,
    values: Any,
    gate: dict[str, Any],
    directions: dict[str, str],
    snapshots: dict[str, Any],
    engine: Any,
    candidate49: Any,
    comparison_engine: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Reconstruct the exact 80-factor order: prior 79, then C56."""

    comparisons, verifications = c56_audit._append_all_prior_comparisons(
        data_root=data_root,
        workers=workers,
        keys=keys,
        values=values,
        gate=gate,
        directions=directions,
        snapshots=snapshots,
        engine=engine,
        candidate49=candidate49,
        comparison_engine=comparison_engine,
    )
    factor = c56_audit.candidate.FACTOR_NAME
    comparison_values = engine._load_filtered_comparison_values_explicit(
        snapshots["c56_manifest"], [factor], keys
    )[factor]
    comparisons.append(
        comparison_engine._aligned_comparison_result(
            candidate_keys=keys,
            candidate_values=values,
            comparison_values=comparison_values,
            comparison=factor,
            direction=directions[factor],
            gate=gate,
        )
    )
    del comparison_values
    gc.collect()
    return comparisons, {
        **verifications,
        "campaign056_snapshot_file_verification": snapshots["c56_verification"],
    }


for _name, _value in {
    "verify_static_bindings": verify_static_bindings,
    "_load_bound_prior_snapshots": _load_bound_prior_snapshots,
    "_append_all_prior_comparisons": _append_all_prior_comparisons,
}.items():
    _generated[_name] = _value

load_candidate_frame = _generated["load_candidate_frame"]
run_no_return_audit = _generated["run_no_return_audit"]
status = _generated["status"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
