#!/usr/bin/env python3
"""Run Campaign094's exact one-trial historical walk-forward campaign."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign092.py"
BASE_RUNNER_SHA256 = "cc6f4b8fc8052c349b6e18638c737fd9bb7c30bbe436eb0cee546b43f75cd88d"
BASE_FACTOR = "intraday_interbar_gap_discovery_share_238p"
ADMITTED_FACTOR = "intraday_range_local_peak_clock_dispersion_236p"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign092 development runner changed")


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign092", "Campaign094"),
    ("campaign092", "campaign094"),
    ("campaign_092", "campaign_094"),
    ("wf092", "wf094"),
    (BASE_FACTOR, ADMITTED_FACTOR),
    (
        "06fbfcae04af4ce2a917601876b5047e5ac09f75cf19d17bebc0bca8d9ff019e",
        "1f1441e59bcef1cb3d18b0030c640453e2ee762668d05157dec9ca1c0f01c340",
    ),
    (
        "7df85a0b3a75b203661de4d1695d8f75890fdc649efbee7739b4f2241ab93321",
        "37865a7d4c5556ee9a79ba9550f0f05229e3c52bb511d8bd1ac3b1f2525a6b63",
    ),
    ("EXPECTED_ELIGIBLE_ROWS = 1_328_155", "EXPECTED_ELIGIBLE_ROWS = 1_314_834"),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign094_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)  # noqa: S102

DEFAULT_PREREGISTRATION = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_094_preregistration.json"
)
_generated["DEFAULT_PREREGISTRATION"] = DEFAULT_PREREGISTRATION
engine_namespace = _generated["engine_namespace"]
engine_namespace["DEFAULT_CAMPAIGN"] = DEFAULT_PREREGISTRATION
base = _generated["base"]
Campaign094Error = _generated["Campaign094Error"]
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
