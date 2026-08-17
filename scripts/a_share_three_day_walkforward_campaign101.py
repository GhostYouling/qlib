#!/usr/bin/env python3
"""Run Campaign101's exact one-trial historical walk-forward campaign."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign099.py"
BASE_RUNNER_SHA256 = "b251b3049095f05b4aec87d6f6784c12517ac32c1542dbc63eaf6f1511d4bef4"
BASE_FACTOR = "intraday_market_close_location_profile_synchronization_240m"
ADMITTED_FACTOR = "full_numeric_library_directional_lower_quartile_consensus_129f"
COMPACT_MANIFEST = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign101_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign101_feature_library_v1/snapshot_manifest.json"
)
COMPACT_MANIFEST_SHA256 = (
    "7a2db929fff69f46edbc93d57cdca9cc4427c47dd542291b4f58d879dd91a3b6"
)
COMPACT_DATASET_SHA256 = (
    "ed024ab2736b9766e1adb122b155189029f30a5d14e11d4d67a403ff9befef24"
)
EXPECTED_CAMPAIGN101_ELIGIBLE_ROWS = 1_327_637


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign099 development runner changed")


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign099", "Campaign101"),
    ("campaign099", "campaign101"),
    ("campaign_099", "campaign_101"),
    ("wf099", "wf101"),
    (BASE_FACTOR, ADMITTED_FACTOR),
    (
        "a973f7d71a871e56294f50a0c39267006f9b859f1b9490599c89c51cbab5fe90",
        COMPACT_MANIFEST_SHA256,
    ),
    (
        "1ac5ddd9c59401a48876df69e409ba86b6fd71923c5be61936efb30a56c3de9b",
        COMPACT_DATASET_SHA256,
    ),
    (
        "minute_walkforward_campaign101_compact_feature_library",
        "minute_walkforward_campaign101_feature_library",
    ),
    (
        "walkforward_campaign101_compact_feature_library_v1",
        "walkforward_campaign101_feature_library_v1",
    ),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign101_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)  # noqa: S102

CAMPAIGN101_PREREGISTRATION_V2 = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_101_preregistration_v2.json"
)
_generated["CANDIDATE_MANIFEST"] = COMPACT_MANIFEST
_generated["CANDIDATE_MANIFEST_SHA256"] = COMPACT_MANIFEST_SHA256
_generated["CANDIDATE_DATASET_SHA256"] = COMPACT_DATASET_SHA256
_generated["EXPECTED_ELIGIBLE_ROWS"] = EXPECTED_CAMPAIGN101_ELIGIBLE_ROWS
_generated["DEFAULT_PREREGISTRATION"] = CAMPAIGN101_PREREGISTRATION_V2
_inner_generated: dict[str, Any] = _generated["_generated"]
_inner_generated["DEFAULT_PREREGISTRATION"] = CAMPAIGN101_PREREGISTRATION_V2
_inner_generated["engine_namespace"][
    "DEFAULT_CAMPAIGN"
] = CAMPAIGN101_PREREGISTRATION_V2

DEFAULT_PREREGISTRATION = _generated["DEFAULT_PREREGISTRATION"]
DEVELOPMENT_IMPLEMENTATION_FREEZE = _generated["DEVELOPMENT_IMPLEMENTATION_FREEZE"]
DEVELOPMENT_ACTIVATION_BINDING = _generated["DEVELOPMENT_ACTIVATION_BINDING"]
TEST_PATH = _generated["TEST_PATH"]
base = _generated["base"]
Campaign101Error = _generated["Campaign101Error"]
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
