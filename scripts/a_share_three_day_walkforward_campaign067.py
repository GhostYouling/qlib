#!/usr/bin/env python3
"""Run the exact one-trial Campaign067 historical walk-forward campaign."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign066.py"
BASE_RUNNER_SHA256 = (
    "82452db05b76ae60bb1f4014d01d0ddfd540768066a2528d334582c03fb5387f"
)
BASE_FACTOR = "quarterly_quality_rank_balance_3f"
ADMITTED_FACTOR = "quarterly_roe_profit_scale_efficiency_gap_2r"
FROZEN_TRIAL_ID = "wf067_quarterly_roe_profit_scale_efficiency_gap_2r_single_higher"
DEFAULT_PREREGISTRATION = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_067_preregistration.json"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign066 development runner changed")

_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign066", "Campaign067"),
    ("campaign066", "campaign067"),
    ("campaign_066", "campaign_067"),
    ("wf066", "wf067"),
    (BASE_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign067_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)

engine_namespace: dict[str, Any] = _generated["engine_namespace"]
engine_namespace["DEFAULT_CAMPAIGN"] = DEFAULT_PREREGISTRATION

base = _generated["base"]
Campaign067Error = _generated["Campaign067Error"]
build_trial_catalog = _generated["build_trial_catalog"]
load_campaign = _generated["load_campaign"]
parser = _generated["parser"]
run_development = _generated["run_development"]
run_exposed_stress = _generated["run_exposed_stress"]
status = _generated["status"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
