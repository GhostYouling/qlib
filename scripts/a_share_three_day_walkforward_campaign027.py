#!/usr/bin/env python3
"""Run the single frozen Campaign027 three-session walk-forward trial.

Campaign027 reuses the byte-bound Campaign026 orchestration and unchanged
Campaign006 execution engine. Only deterministic campaign namespace and
admitted-factor substitutions are allowed; folds, execution assumptions,
survivor gates, and conditional exposed-stress rules remain inherited.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN026_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign026.py"
)
CAMPAIGN026_RUNNER_SHA256 = (
    "cc9807d5773e8a4a7a00af45abacbddb65aab5bd9f856b80d1e61c0d81811222"
)
OLD_FACTOR = "intraday_market_up_down_correlation_asymmetry_238m"
ADMITTED_FACTOR = "intraday_morning_afternoon_return_profile_persistence_119p"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN026_RUNNER) != CAMPAIGN026_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign026 orchestration fingerprint changed")

_source = CAMPAIGN026_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign026", "Campaign027"),
    ("campaign026", "campaign027"),
    ("campaign_026", "campaign_027"),
    ("wf026", "wf027"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign027_generated",
}
exec(compile(_source, str(CAMPAIGN026_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign027Error = _generated["Campaign027Error"]
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
