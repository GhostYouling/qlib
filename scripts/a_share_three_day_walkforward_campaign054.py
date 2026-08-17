#!/usr/bin/env python3
"""Run the exact one-trial Campaign054 historical walk-forward campaign."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign051.py"
BASE_RUNNER_SHA256 = (
    "1760ca1fec62c54016f7af8dbf4984121f6d775ec050c249e939ac0872e2697c"
)
BASE_FACTOR = "intraday_close_range_occupancy_entropy_10b"
ADMITTED_FACTOR = "intraday_volume_weighted_transaction_price_bowley_skew_240m"
FROZEN_TRIAL_ID = (
    "wf054_intraday_volume_weighted_transaction_price_bowley_skew_240m_single_higher"
)
DEFAULT_PREREGISTRATION = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_054_preregistration.json"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign051 development runner changed")

_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign051", "Campaign054"),
    ("campaign051", "campaign054"),
    ("campaign_051", "campaign_054"),
    ("wf051", "wf054"),
    (BASE_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign054_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)

engine_namespace: dict[str, Any] = _generated["engine_namespace"]
engine_namespace["DEFAULT_CAMPAIGN"] = DEFAULT_PREREGISTRATION

base = _generated["base"]
Campaign054Error = _generated["Campaign054Error"]
build_trial_catalog = _generated["build_trial_catalog"]
load_campaign = _generated["load_campaign"]
parser = _generated["parser"]
run_development = _generated["run_development"]
run_exposed_stress = _generated["run_exposed_stress"]
status = _generated["status"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
