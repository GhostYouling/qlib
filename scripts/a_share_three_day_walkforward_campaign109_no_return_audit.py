#!/usr/bin/env python3
"""Run Campaign109's frozen coverage-first all-132 no-return audit."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign108_no_return_audit.py"
)
BASE_RUNNER_SHA256 = "8fd5402b2a492380152efa4f1b0af077f65c1cee2ed6c2f25e1b5ea00a8e20e1"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _file_sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign108 v1 no-return audit changed")


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign108", "Campaign109"),
    ("campaign108", "campaign109"),
    ("campaign_108", "campaign_109"),
    (
        "a_share_three_day_walkforward_campaign108_features as candidate",
        "a_share_three_day_walkforward_campaign109_features as candidate",
    ),
):
    _source = _source.replace(_old, _new)
_hook = '_source = BASE_RUNNER.read_text(encoding="utf-8")'
_injection = "\n".join(
    [
        _hook,
        '_source = _source.replace("ranges[FACTOR_NAME] = (0.0, 1.0)", "ranges[FACTOR_NAME] = (-1.0, 1.0)")',
    ]
)
if _source.count(_hook) != 1:
    raise RuntimeError("Campaign109 audit generation hook changed")
_source = _source.replace(_hook, _injection)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign109_no_return_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)

Campaign109NoReturnAuditError = _generated["Campaign109NoReturnAuditError"]
candidate = _generated["candidate"]
FACTOR_NAME = _generated["FACTOR_NAME"]
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT = _generated["DEFAULT_EXPERIMENT_ROOT"]
SNAPSHOT_MANIFEST_PATH = _generated["SNAPSHOT_MANIFEST_PATH"]
SNAPSHOT_BINDING = _generated["SNAPSHOT_BINDING"]
AUDIT_ACTIVATION_BINDING = _generated["AUDIT_ACTIVATION_BINDING"]
ADAPTER_FREEZE = _generated["ADAPTER_FREEZE"]
ADAPTER_FREEZE_SHA256 = _generated["ADAPTER_FREEZE_SHA256"]
EXPECTED_ROWS = _generated["EXPECTED_ROWS"]
EXPECTED_PARTITIONS = _generated["EXPECTED_PARTITIONS"]
EXPECTED_COMPARISON_COUNT = _generated["EXPECTED_COMPARISON_COUNT"]
load_protocol = _generated["load_protocol"]
verify_static_bindings = _generated["verify_static_bindings"]
verify_candidate_snapshot = _generated["verify_candidate_snapshot"]
run_no_return_audit = _generated["run_no_return_audit"]
status = _generated["status"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
