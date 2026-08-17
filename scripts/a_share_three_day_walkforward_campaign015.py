#!/usr/bin/env python3
"""Run the single frozen Campaign015 three-session walk-forward trial.

Campaign015 reuses the byte-bound Campaign014 orchestration and unchanged
Campaign006 execution engine. Only deterministic campaign namespace and
admitted-factor substitutions are allowed; folds, execution assumptions,
survivor gates, and conditional exposed-stress rules remain inherited.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN014_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign014.py"
)
CAMPAIGN014_RUNNER_SHA256 = (
    "c3acd5039e953c9a0df53cddd9edc9a669328da0b46fd8a07aa8392500d97616"
)
OLD_FACTOR = "intraday_global_price_range_revisit_240m"
ADMITTED_FACTOR = "intraday_prior_range_breakout_pressure_238p"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN014_RUNNER) != CAMPAIGN014_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign014 orchestration fingerprint changed")

_source = CAMPAIGN014_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign014", "Campaign015"),
    ("campaign014", "campaign015"),
    ("campaign_014", "campaign_015"),
    ("wf014", "wf015"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign015_generated",
}
exec(compile(_source, str(CAMPAIGN014_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign015Error = _generated["Campaign015Error"]
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
