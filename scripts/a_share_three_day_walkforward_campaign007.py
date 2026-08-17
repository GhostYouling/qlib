#!/usr/bin/env python3
"""Run the single frozen Campaign007 three-session walk-forward trial.

Campaign007 reuses the byte-bound Campaign006 orchestration layer and its
unchanged execution engine. Only deterministic namespace and admitted-factor
substitutions are allowed; folds, execution assumptions, survivor gates, and
conditional exposed-stress rules remain inherited unchanged.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN006_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign006.py"
)
CAMPAIGN006_RUNNER_SHA256 = (
    "b25b0c1cd7086bd0a82d4d0df0272c0563ea7b91e0a8d5f5229716f70daf627b"
)
OLD_FACTOR = "intraday_transaction_price_path_confirmation_238p"
ADMITTED_FACTOR = "intraday_share_volume_transaction_price_coupling_238p"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN006_RUNNER) != CAMPAIGN006_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign006 orchestration fingerprint changed")

_source = CAMPAIGN006_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign006", "Campaign007"),
    ("campaign006", "campaign007"),
    ("campaign_006", "campaign_007"),
    ("wf006", "wf007"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign007_generated",
}
exec(compile(_source, str(CAMPAIGN006_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign007Error = _generated["Campaign007Error"]
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
