#!/usr/bin/env python3
"""Run the single frozen Campaign028 three-session walk-forward trial.

Campaign028 reuses the byte-bound Campaign027 orchestration and unchanged
Campaign006 execution engine. Only deterministic campaign namespace and
admitted-factor substitutions are allowed; folds, execution assumptions,
survivor gates, and conditional exposed-stress rules remain inherited.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN027_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign027.py"
)
CAMPAIGN027_RUNNER_SHA256 = (
    "01bd362f423433dae0ce7d71bf1e65e2752ab10b7df9822de7e884fde1a984b2"
)
OLD_FACTOR = "intraday_morning_afternoon_return_profile_persistence_119p"
ADMITTED_FACTOR = "intraday_absolute_return_serial_persistence_236p"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN027_RUNNER) != CAMPAIGN027_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign027 orchestration fingerprint changed")

_source = CAMPAIGN027_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign027", "Campaign028"),
    ("campaign027", "campaign028"),
    ("campaign_027", "campaign_028"),
    ("wf027", "wf028"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign028_generated",
}
exec(compile(_source, str(CAMPAIGN027_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign028Error = _generated["Campaign028Error"]
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
