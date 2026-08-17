#!/usr/bin/env python3
"""Run the single frozen Campaign047 three-session walk-forward trial.

Campaign047 reuses the byte-bound Campaign045 orchestration, which in turn
reuses the unchanged Campaign043/Campaign006 execution engine. Only the
deterministic campaign namespace and admitted-factor substitutions are
allowed; folds, execution assumptions, survivor gates, and conditional
exposed-stress rules remain inherited.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN045_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign045.py"
)
CAMPAIGN045_RUNNER_SHA256 = (
    "e6775605206bd34f78f8bf223677bf7ecd43d333eb245c4bef6f1593d3a4f227"
)
OLD_FACTOR = "intraday_volatility_activity_lead_lag_asymmetry_236p"
ADMITTED_FACTOR = "intraday_body_next_microgap_reversal_238p"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN045_RUNNER) != CAMPAIGN045_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign045 orchestration fingerprint changed")

_source = CAMPAIGN045_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign045", "Campaign047"),
    ("campaign045", "campaign047"),
    ("campaign_045", "campaign_047"),
    ("wf045", "wf047"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign047_generated",
}
exec(compile(_source, str(CAMPAIGN045_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign047Error = _generated["Campaign047Error"]
build_trial_catalog = _generated["build_trial_catalog"]
load_campaign = _generated["load_campaign"]
parser = _generated["parser"]
run_development = _generated["run_development"]
run_exposed_stress = _generated["run_exposed_stress"]
status = _generated["status"]
main = _generated["main"]
engine_namespace = _generated["engine_namespace"]
_inherited_survivor_decision = _generated[
    "_inherited_survivor_decision"
]
_survivor_decision_with_canonical_complexity = _generated[
    "_survivor_decision_with_canonical_complexity"
]


if __name__ == "__main__":
    raise SystemExit(main())
