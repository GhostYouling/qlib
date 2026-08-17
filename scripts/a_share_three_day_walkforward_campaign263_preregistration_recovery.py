#!/usr/bin/env python3
"""Publish Campaign263's post-format pre-return preregistration recovery."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_263_preregistration.json"
)
OUTPUT = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_263_preregistration_v2.json"
)
RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign263.py"
LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_263/research_attempt_ledger_v7.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, Any]:
    source_sha256 = _sha256(SOURCE)
    if (
        source_sha256
        != "2ef440957da7ba956d16361744b2f1bb373a1ff0d9d28f9946546d556f43a1d3"
    ):
        raise RuntimeError("Campaign263 superseded preregistration changed")
    runner_sha256 = _sha256(RUNNER)
    if (
        runner_sha256
        != "5b9df26ceed7dea1408f111de0d2bacadb9b5a595a30b70d42758f04cee58577"
    ):
        raise RuntimeError("Campaign263 formatted runner changed")
    ledger_sha256 = _sha256(LEDGER)
    if (
        ledger_sha256
        != "cd2ea26d309c2193f0ba200a1545288f084b07302cb18c91ff11231d41f110c1"
    ):
        raise RuntimeError("Campaign263 recovery ledger changed")
    value = json.loads(SOURCE.read_text(encoding="utf-8"))
    value["version"] = 1
    value["status"] = "frozen_before_campaign263_2019_2023_development_return_read"
    value["frozen_at"] = "2026-08-16T13:58:00Z"
    value["purpose"] = (
        "Replace only the superseded pre-format runner and pre-failure ledger "
        "bindings while preserving the sole Campaign263 factor, exact one-trial "
        "catalog and every inherited research gate before any development return read."
    )
    value["governance_bindings"]["research_attempt_ledger_before_return_read"] = {
        "path": str(LEDGER.relative_to(REPO_ROOT)),
        "sha256": ledger_sha256,
        "entry_count": 28,
        "chain_tip_sha256": "8e088a1f1e19ca37bc8b1e9d64f38dab1c826461e710a5bd5ff77e6f75008f2f",
    }
    value["implementation"]["script"]["sha256"] = runner_sha256
    value["implementation"]["development_command"] = (
        "python -m scripts.a_share_three_day_walkforward_campaign263 "
        "--campaign docs/a_share_three_day_walkforward_campaign_263_preregistration_v2.json "
        "run-development"
    )
    value["implementation"]["exposed_stress_command"] = (
        "python -m scripts.a_share_three_day_walkforward_campaign263 "
        "--campaign docs/a_share_three_day_walkforward_campaign_263_preregistration_v2.json "
        "run-exposed-stress --confirm-exposed-stress"
    )
    return value


def main() -> int:
    value = build()
    OUTPUT.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"path": str(OUTPUT), "sha256": _sha256(OUTPUT)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
