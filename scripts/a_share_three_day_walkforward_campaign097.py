#!/usr/bin/env python3
"""Run Campaign097's exact one-trial historical walk-forward campaign."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign094.py"
BASE_RUNNER_SHA256 = "bbf7d9affc8d1b26f65637898bc0324423c37979c18e769a96aed1351ae6bbdd"
BASE_FACTOR = "intraday_range_local_peak_clock_dispersion_236p"
ADMITTED_FACTOR = "intraday_market_range_profile_synchronization_240m"
COMPACT_MANIFEST = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign097_compact_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign097_compact_feature_library_v1/snapshot_manifest.json"
)
COMPACT_MANIFEST_SHA256 = (
    "fac652d7097de579c8f3d6c5812ce9573762ec8885d6729706e2ef7e0cd81227"
)
COMPACT_DATASET_SHA256 = (
    "dfdeda35efb8e443e4f33a6ab217032ec2ba6793270f8eb7fcf36d9494f7bf97"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign094 development runner changed")


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign094", "Campaign097"),
    ("campaign094", "campaign097"),
    ("campaign_094", "campaign_097"),
    ("wf094", "wf097"),
    (BASE_FACTOR, ADMITTED_FACTOR),
    (
        "1f1441e59bcef1cb3d18b0030c640453e2ee762668d05157dec9ca1c0f01c340",
        COMPACT_MANIFEST_SHA256,
    ),
    (
        "37865a7d4c5556ee9a79ba9550f0f05229e3c52bb511d8bd1ac3b1f2525a6b63",
        COMPACT_DATASET_SHA256,
    ),
    ("EXPECTED_ELIGIBLE_ROWS = 1_314_834", "EXPECTED_ELIGIBLE_ROWS = 1_328_449"),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign097_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)  # noqa: S102

DEFAULT_PREREGISTRATION = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_097_preregistration.json"
)
_generated["DEFAULT_PREREGISTRATION"] = DEFAULT_PREREGISTRATION
_generated["CANDIDATE_MANIFEST"] = COMPACT_MANIFEST
_generated["CANDIDATE_MANIFEST_SHA256"] = COMPACT_MANIFEST_SHA256
_generated["CANDIDATE_DATASET_SHA256"] = COMPACT_DATASET_SHA256
_generated["EXPECTED_ROWS"] = 1_331_759
_generated["EXPECTED_ELIGIBLE_ROWS"] = 1_328_449
engine_namespace = _generated["engine_namespace"]
engine_namespace["DEFAULT_CAMPAIGN"] = DEFAULT_PREREGISTRATION
base = _generated["base"]
Campaign097Error = _generated["Campaign097Error"]
ADMITTED_FACTOR = _generated["ADMITTED_FACTOR"]
FROZEN_TRIAL_ID = _generated["FROZEN_TRIAL_ID"]
CANDIDATE_MANIFEST = _generated["CANDIDATE_MANIFEST"]
CANDIDATE_MANIFEST_SHA256 = _generated["CANDIDATE_MANIFEST_SHA256"]
CANDIDATE_DATASET_SHA256 = _generated["CANDIDATE_DATASET_SHA256"]
EXPECTED_ROWS = _generated["EXPECTED_ROWS"]
EXPECTED_ELIGIBLE_ROWS = _generated["EXPECTED_ELIGIBLE_ROWS"]
build_trial_catalog = _generated["build_trial_catalog"]
load_campaign = _generated["load_campaign"]
parser = _generated["parser"]
status = _generated["status"]
_decode_stock_day_keys = _generated["_decode_stock_day_keys"]
_load_compact_factor_panel = _generated["_load_compact_factor_panel"]
_temporary_compact_factor_loader = _generated["_temporary_compact_factor_loader"]
run_development = _generated["run_development"]
run_exposed_stress = _generated["run_exposed_stress"]
_inherited_main = _generated["main"]


def main() -> int:
    return _inherited_main()


if __name__ == "__main__":
    raise SystemExit(main())
