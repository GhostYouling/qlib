#!/usr/bin/env python3
"""Run the single frozen Campaign016 three-session walk-forward trial.

Campaign016 reuses the byte-bound Campaign015 orchestration and unchanged
Campaign006 execution engine. Only deterministic campaign namespace and
admitted-factor substitutions are allowed; folds, execution assumptions,
survivor gates, and conditional exposed-stress rules remain inherited.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN015_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign015.py"
)
CAMPAIGN015_RUNNER_SHA256 = (
    "0696ea5da8d629fd288c51c90d9895e7e8ed022b921b9b9e00ec30ffef80111c"
)
OLD_FACTOR = "intraday_prior_range_breakout_pressure_238p"
ADMITTED_FACTOR = "intraday_interbar_gap_body_confirmation_238p"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN015_RUNNER) != CAMPAIGN015_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign015 orchestration fingerprint changed")

_source = CAMPAIGN015_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign015", "Campaign016"),
    ("campaign015", "campaign016"),
    ("campaign_015", "campaign_016"),
    ("wf015", "wf016"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign016_generated",
}
exec(compile(_source, str(CAMPAIGN015_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign016Error = _generated["Campaign016Error"]
build_trial_catalog = _generated["build_trial_catalog"]
load_campaign = _generated["load_campaign"]
parser = _generated["parser"]
run_development = _generated["run_development"]
run_exposed_stress = _generated["run_exposed_stress"]
status = _generated["status"]
main = _generated["main"]
engine_namespace = run_exposed_stress.__globals__


if __name__ == "__main__":
    raise SystemExit(main())
