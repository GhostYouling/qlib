#!/usr/bin/env python3
"""Run the exact one-trial Campaign056 historical walk-forward campaign."""

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
ADMITTED_FACTOR = "intraday_day_over_day_amount_profile_similarity_240b"
FROZEN_TRIAL_ID = (
    "wf056_intraday_day_over_day_amount_profile_similarity_240b_single_higher"
)
DEFAULT_PREREGISTRATION = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_056_preregistration.json"
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
    ("Campaign051", "Campaign056"),
    ("campaign051", "campaign056"),
    ("campaign_051", "campaign_056"),
    ("wf051", "wf056"),
    (BASE_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign056_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _generated)

engine_namespace: dict[str, Any] = _generated["engine_namespace"]
engine_namespace["DEFAULT_CAMPAIGN"] = DEFAULT_PREREGISTRATION

base = _generated["base"]
Campaign056Error = _generated["Campaign056Error"]
build_trial_catalog = _generated["build_trial_catalog"]
load_campaign = _generated["load_campaign"]
parser = _generated["parser"]
run_development = _generated["run_development"]
run_exposed_stress = _generated["run_exposed_stress"]
status = _generated["status"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
