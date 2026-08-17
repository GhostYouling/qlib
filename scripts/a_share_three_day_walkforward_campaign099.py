#!/usr/bin/env python3
"""Run Campaign099's exact one-trial historical walk-forward campaign."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign098.py"
BASE_RUNNER_SHA256 = "6bfc39a91e0e0375c51103e31a90ce97ccd42320e90ebd3c19420e4cdb15ab1c"
BASE_FACTOR = "intraday_range_clock_variance_240m"
ADMITTED_FACTOR = "intraday_market_close_location_profile_synchronization_240m"
COMPACT_MANIFEST = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign099_compact_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign099_compact_feature_library_v1/snapshot_manifest.json"
)
COMPACT_MANIFEST_SHA256 = (
    "a973f7d71a871e56294f50a0c39267006f9b859f1b9490599c89c51cbab5fe90"
)
COMPACT_DATASET_SHA256 = (
    "1ac5ddd9c59401a48876df69e409ba86b6fd71923c5be61936efb30a56c3de9b"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign098 development runner changed")


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign098", "Campaign099"),
    ("campaign098", "campaign099"),
    ("campaign_098", "campaign_099"),
    ("wf098", "wf099"),
    (BASE_FACTOR, ADMITTED_FACTOR),
    (
        "371429a81292a91ef2bfa1292f467c81bf73e176fbfbc9888084f74eaaac1dc5",
        COMPACT_MANIFEST_SHA256,
    ),
    (
        "921f06fad98aed942550d86b1475c888aea6d2025c37d53ec55917401bd34b33",
        COMPACT_DATASET_SHA256,
    ),
    (
        "minute_walkforward_campaign099_feature_library",
        "minute_walkforward_campaign099_compact_feature_library",
    ),
    (
        "walkforward_campaign099_feature_library_v1",
        "walkforward_campaign099_compact_feature_library_v1",
    ),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign099_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)  # noqa: S102

_generated["CANDIDATE_MANIFEST"] = COMPACT_MANIFEST
_generated["CANDIDATE_MANIFEST_SHA256"] = COMPACT_MANIFEST_SHA256
_generated["CANDIDATE_DATASET_SHA256"] = COMPACT_DATASET_SHA256

DEFAULT_PREREGISTRATION = _generated["DEFAULT_PREREGISTRATION"]
DEVELOPMENT_IMPLEMENTATION_FREEZE = _generated["DEVELOPMENT_IMPLEMENTATION_FREEZE"]
DEVELOPMENT_ACTIVATION_BINDING = _generated["DEVELOPMENT_ACTIVATION_BINDING"]
TEST_PATH = _generated["TEST_PATH"]
base = _generated["base"]
Campaign099Error = _generated["Campaign099Error"]
FROZEN_TRIAL_ID = _generated["FROZEN_TRIAL_ID"]
CANDIDATE_MANIFEST = _generated["CANDIDATE_MANIFEST"]
CANDIDATE_MANIFEST_SHA256 = _generated["CANDIDATE_MANIFEST_SHA256"]
CANDIDATE_DATASET_SHA256 = _generated["CANDIDATE_DATASET_SHA256"]
EXPECTED_ROWS = _generated["EXPECTED_ROWS"]
EXPECTED_ELIGIBLE_ROWS = _generated["EXPECTED_ELIGIBLE_ROWS"]
build_trial_catalog = _generated["build_trial_catalog"]
load_campaign = _generated["load_campaign"]
status = _generated["status"]
_decode_stock_day_keys = _generated["_decode_stock_day_keys"]
_load_compact_factor_panel = _generated["_load_compact_factor_panel"]
_temporary_compact_factor_loader = _generated["_temporary_compact_factor_loader"]
run_development = _generated["run_development"]
run_exposed_stress = _generated["run_exposed_stress"]
_load_development_activation = _generated["_load_development_activation"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
