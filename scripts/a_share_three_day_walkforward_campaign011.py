#!/usr/bin/env python3
"""Run the single frozen Campaign011 three-session walk-forward trial.

Campaign011 reuses the byte-bound Campaign009 orchestration wrapper and the
unchanged Campaign006 execution engine. Only deterministic campaign namespace
and admitted-factor substitutions are allowed; folds, execution assumptions,
survivor gates, and conditional exposed-stress rules remain inherited.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN009_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign009.py"
)
CAMPAIGN009_RUNNER_SHA256 = (
    "c0f2a8894602f1f0d63d23a25b6839a6189ffe977de4d13b3e92ce2fc489f5d5"
)
OLD_FACTOR = "intraday_intrabar_body_range_efficiency_240m"
ADMITTED_FACTOR = "intraday_intrabar_range_participation_entropy_240m"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN009_RUNNER) != CAMPAIGN009_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign009 orchestration fingerprint changed")

_source = CAMPAIGN009_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign009", "Campaign011"),
    ("campaign009", "campaign011"),
    ("campaign_009", "campaign_011"),
    ("wf009", "wf011"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign011_generated",
}
exec(compile(_source, str(CAMPAIGN009_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign011Error = _generated["Campaign011Error"]
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
