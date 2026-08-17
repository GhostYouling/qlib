#!/usr/bin/env python3
"""Run the single frozen Campaign012 three-session walk-forward trial.

Campaign012 reuses the byte-bound Campaign011 orchestration wrapper and the
unchanged Campaign006 execution engine. Only deterministic campaign namespace
and admitted-factor substitutions are allowed; folds, execution assumptions,
survivor gates, and conditional exposed-stress rules remain inherited.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN011_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign011.py"
)
CAMPAIGN011_RUNNER_SHA256 = (
    "e408344c56532081be1a05f836224ca0c30344a529ee9c8bd00d308f751a37e9"
)
OLD_FACTOR = "intraday_intrabar_range_participation_entropy_240m"
ADMITTED_FACTOR = "intraday_intrabar_range_reversal_238p"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN011_RUNNER) != CAMPAIGN011_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign011 orchestration fingerprint changed")

_source = CAMPAIGN011_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign011", "Campaign012"),
    ("campaign011", "campaign012"),
    ("campaign_011", "campaign_012"),
    ("wf011", "wf012"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign012_generated",
}
exec(compile(_source, str(CAMPAIGN011_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign012Error = _generated["Campaign012Error"]
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
