#!/usr/bin/env python3
"""Run the single frozen Campaign018 three-session walk-forward trial.

Campaign018 reuses the byte-bound Campaign017 orchestration and unchanged
Campaign006 execution engine. Only deterministic campaign namespace and
admitted-factor substitutions are allowed; folds, execution assumptions,
survivor gates, and conditional exposed-stress rules remain inherited.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN017_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign017.py"
)
CAMPAIGN017_RUNNER_SHA256 = (
    "c6b715de892c02e29d665c5ea12266c3c27a9ae0e53dc8b0e3efb3e0309f3bf9"
)
OLD_FACTOR = "intraday_midrange_width_change_coupling_238p"
ADMITTED_FACTOR = "intraday_range_share_volume_confirmation_240m"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN017_RUNNER) != CAMPAIGN017_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign017 orchestration fingerprint changed")

_source = CAMPAIGN017_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign017", "Campaign018"),
    ("campaign017", "campaign018"),
    ("campaign_017", "campaign_018"),
    ("wf017", "wf018"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign018_generated",
}
exec(compile(_source, str(CAMPAIGN017_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign018Error = _generated["Campaign018Error"]
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
