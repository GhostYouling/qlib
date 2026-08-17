#!/usr/bin/env python3
"""Run Campaign090's exact one-trial historical walk-forward campaign."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign089.py"
BASE_RUNNER_SHA256 = "591d89e0d50b88b5664c521ec6473b8acc05b29f700c2e3c8678d4e6535ef6b8"
BASE_FACTOR = "intraday_directional_amount_timing_spread_238m"
ADMITTED_FACTOR = "intraday_range_clock_center_240m"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign089 development runner changed")


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign089", "Campaign090"),
    ("campaign089", "campaign090"),
    ("campaign_089", "campaign_090"),
    ("wf089", "wf090"),
    (BASE_FACTOR, ADMITTED_FACTOR),
    (
        "3ab55cc6f61bebb6713aeacb9e54125c20183295b862717617be0b13c9d0a204",
        "c065e81f4eec91b214a3e1f69d8e15e567fac5bd879e173c5b985777ab4ba2ed",
    ),
    (
        "c4f8794f42f1fffe2847ade875232827c8ca532a7fd75dd1123686c41456655a",
        "d1da6b2c1d059038e473c55a15c76ba2efaf1a282d5a6bec1f302cd37a76ca31",
    ),
    ("EXPECTED_ELIGIBLE_ROWS = 1_327_577", "EXPECTED_ELIGIBLE_ROWS = 1_328_449"),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign090_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)  # noqa: S102

engine_namespace = _generated["engine_namespace"]
base = _generated["base"]
Campaign090Error = _generated["Campaign090Error"]
ADMITTED_FACTOR = _generated["ADMITTED_FACTOR"]
FROZEN_TRIAL_ID = _generated["FROZEN_TRIAL_ID"]
DEFAULT_PREREGISTRATION = _generated["DEFAULT_PREREGISTRATION"]
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
