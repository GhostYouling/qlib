#!/usr/bin/env python3
"""Campaign108 audit entry point bound to the additive feature v2 recovery."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_IMPLEMENTATION = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign108_no_return_audit.py"
)
BASE_IMPLEMENTATION_SHA256 = (
    "8fd5402b2a492380152efa4f1b0af077f65c1cee2ed6c2f25e1b5ea00a8e20e1"
)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _file_sha256(BASE_IMPLEMENTATION) != BASE_IMPLEMENTATION_SHA256:
    raise RuntimeError("frozen Campaign108 v1 no-return audit changed")


_source = BASE_IMPLEMENTATION.read_text(encoding="utf-8")
_old = "a_share_three_day_walkforward_campaign108_features as candidate"
_new = "a_share_three_day_walkforward_campaign108_features_v2 as candidate"
if _source.count(_old) != 1:
    raise RuntimeError("Campaign108 v1 candidate import changed")
_source = _source.replace(_old, _new)

_impl: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign108_no_return_audit_v2_generated",
}
exec(compile(_source, str(BASE_IMPLEMENTATION), "exec"), _impl)


Campaign108NoReturnAuditError = _impl["Campaign108NoReturnAuditError"]
candidate = _impl["candidate"]
FACTOR_NAME = _impl["FACTOR_NAME"]
DEFAULT_DATA_ROOT = _impl["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT = _impl["DEFAULT_EXPERIMENT_ROOT"]
SNAPSHOT_MANIFEST_PATH = _impl["SNAPSHOT_MANIFEST_PATH"]
SNAPSHOT_BINDING = _impl["SNAPSHOT_BINDING"]
AUDIT_ACTIVATION_BINDING = _impl["AUDIT_ACTIVATION_BINDING"]
EXPECTED_ROWS = _impl["EXPECTED_ROWS"]
EXPECTED_PARTITIONS = _impl["EXPECTED_PARTITIONS"]
EXPECTED_COMPARISON_COUNT = _impl["EXPECTED_COMPARISON_COUNT"]
load_protocol = _impl["load_protocol"]
_validate_adapter_freeze = _impl["_validate_adapter_freeze"]
_load_activation_binding = _impl["_load_activation_binding"]
verify_static_bindings = _impl["verify_static_bindings"]
verify_candidate_snapshot = _impl["verify_candidate_snapshot"]
_load_comparisons_after_coverage = _impl["_load_comparisons_after_coverage"]
run_no_return_audit = _impl["run_no_return_audit"]
status = _impl["status"]
main = _impl["main"]


if __name__ == "__main__":
    raise SystemExit(main())
