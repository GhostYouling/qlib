#!/usr/bin/env python3
"""Publish Campaign099's admitted factor on the frozen compact stock-day grid."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign097_compact_features.py"
)
BASE_RUNNER_SHA256 = "b4af5e78ba31585469c67619da6943f91182fcd0494ceca5d89ed756c92f105a"
AUTHORITATIVE_AUDIT_PATH = (
    "data/experiments/short_horizon/historical_walkforward/campaign_099/no_return/"
    "20260807T105112Z_campaign099_no_return_audit.json"
)
AUTHORITATIVE_AUDIT_SHA256 = (
    "6df7bfca75a59d00b34a431e2fe5c57d9872587a43b270fa23c5f17ba6411f72"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign097 compact publisher changed")


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign097", "Campaign099"),
    ("campaign097", "campaign099"),
    ("campaign_097", "campaign_099"),
    (
        "a_share_three_day_walkforward_campaign099_no_return_audit_v4 as audit_v4",
        "a_share_three_day_walkforward_campaign099_no_return_audit as audit_v4",
    ),
    ("align_candidate_year(", "align_candidate_year_with_missing("),
    ("keys, values, _ =", "keys, values, _, _ ="),
    (
        "audit_v1.compact_stock_day_keys",
        "audit_v1.c97_audit.compact_stock_day_keys",
    ),
    (
        "data/experiments/short_horizon/historical_walkforward/campaign_099/no_return/20260807T063355Z_campaign099_no_return_audit.json",
        AUTHORITATIVE_AUDIT_PATH,
    ),
    (
        "e95544ba9928c416a00aeaea66c187a4620d3955a48c1418fb697379704bd35b",
        AUTHORITATIVE_AUDIT_SHA256,
    ),
    ("== 125", "== 127"),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign099_compact_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)  # noqa: S102

_generated["DEFAULT_IMPLEMENTATION_FREEZE"] = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_099_compact_feature_implementation_freeze_v2_20260807.json"
)

FACTOR_NAME = _generated["FACTOR_NAME"]
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
SOURCE_MANIFEST = _generated["SOURCE_MANIFEST"]
SOURCE_MANIFEST_SHA256 = _generated["SOURCE_MANIFEST_SHA256"]
SOURCE_DATASET_SHA256 = _generated["SOURCE_DATASET_SHA256"]
ELIGIBILITY_MANIFEST = _generated["ELIGIBILITY_MANIFEST"]
ELIGIBILITY_MANIFEST_SHA256 = _generated["ELIGIBILITY_MANIFEST_SHA256"]
AUTHORITATIVE_NO_RETURN_AUDIT = _generated["AUTHORITATIVE_NO_RETURN_AUDIT"]
AUTHORITATIVE_NO_RETURN_AUDIT_SHA256 = _generated[
    "AUTHORITATIVE_NO_RETURN_AUDIT_SHA256"
]
DEFAULT_IMPLEMENTATION_FREEZE = _generated["DEFAULT_IMPLEMENTATION_FREEZE"]
OUTPUT_RUN_ID = _generated["OUTPUT_RUN_ID"]
EXPECTED_ROWS = _generated["EXPECTED_ROWS"]
EXPECTED_ELIGIBLE_ROWS = _generated["EXPECTED_ELIGIBLE_ROWS"]
Campaign099CompactFeatureError = _generated["Campaign099CompactFeatureError"]
output_root = _generated["output_root"]
build_snapshot = _generated["build_snapshot"]
verify_snapshot = _generated["verify_snapshot"]
status = _generated["status"]
main = _generated["main"]
GENERATED_SOURCE = _source


if __name__ == "__main__":
    raise SystemExit(main())
