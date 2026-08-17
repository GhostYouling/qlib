#!/usr/bin/env python3
"""Run the single frozen Campaign017 three-session walk-forward trial.

Campaign017 reuses the byte-bound Campaign016 orchestration and unchanged
Campaign006 execution engine. Only deterministic campaign namespace and
admitted-factor substitutions are allowed; folds, execution assumptions,
survivor gates, and conditional exposed-stress rules remain inherited.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN016_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign016.py"
)
CAMPAIGN016_RUNNER_SHA256 = (
    "fdf6063c0a196d92cfa300cdcfde1ab095b93af3cb5c26b962e5d3e4d6d4f800"
)
OLD_FACTOR = "intraday_interbar_gap_body_confirmation_238p"
ADMITTED_FACTOR = "intraday_midrange_width_change_coupling_238p"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN016_RUNNER) != CAMPAIGN016_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign016 orchestration fingerprint changed")

_source = CAMPAIGN016_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign016", "Campaign017"),
    ("campaign016", "campaign017"),
    ("campaign_016", "campaign_017"),
    ("wf016", "wf017"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign017_generated",
}
exec(compile(_source, str(CAMPAIGN016_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign017Error = _generated["Campaign017Error"]
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
