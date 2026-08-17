#!/usr/bin/env python3
"""Run the exact one-trial Campaign080 historical walk-forward campaign."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign074.py"
BASE_RUNNER_SHA256 = "8677b23a3cc64150a8e0136bdc7f81f22a1c121cda0e2912771e7c588746afc0"
BASE_FACTOR = "intraday_terminal_bar_amount_share_240m"
ADMITTED_FACTOR = "intraday_above_median_amount_longest_run_240m"
FROZEN_TRIAL_ID = "wf080_intraday_above_median_amount_longest_run_240m_single_higher"
DEFAULT_PREREGISTRATION = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_080_preregistration.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign074 development runner changed")

_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign074", "Campaign080"),
    ("campaign074", "campaign080"),
    ("campaign_074", "campaign_080"),
    ("wf074", "wf080"),
    (BASE_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign080_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)

engine_namespace: dict[str, Any] = _generated["engine_namespace"]
engine_namespace["DEFAULT_CAMPAIGN"] = DEFAULT_PREREGISTRATION

base = _generated["base"]
Campaign080Error = _generated["Campaign080Error"]
build_trial_catalog = _generated["build_trial_catalog"]
load_campaign = _generated["load_campaign"]
parser = _generated["parser"]
run_development = _generated["run_development"]
run_exposed_stress = _generated["run_exposed_stress"]
status = _generated["status"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
