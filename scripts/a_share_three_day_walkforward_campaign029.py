#!/usr/bin/env python3
"""Run the single frozen Campaign029 three-session walk-forward trial.

Campaign029 reuses the byte-bound Campaign028 orchestration and unchanged
Campaign006 execution engine. Only deterministic campaign namespace and
admitted-factor substitutions are allowed; folds, execution assumptions,
survivor gates, and conditional exposed-stress rules remain inherited.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN028_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign028.py"
)
CAMPAIGN028_RUNNER_SHA256 = (
    "df30fb96e5324e400a125d388ecacdec4410dca0f4d14cb7460130aa76bd1b68"
)
OLD_FACTOR = "intraday_absolute_return_serial_persistence_236p"
ADMITTED_FACTOR = "intraday_market_shock_magnitude_decoupling_238m"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN028_RUNNER) != CAMPAIGN028_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign028 orchestration fingerprint changed")

_source = CAMPAIGN028_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign028", "Campaign029"),
    ("campaign028", "campaign029"),
    ("campaign_028", "campaign_029"),
    ("wf028", "wf029"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign029_generated",
}
exec(compile(_source, str(CAMPAIGN028_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign029Error = _generated["Campaign029Error"]
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
