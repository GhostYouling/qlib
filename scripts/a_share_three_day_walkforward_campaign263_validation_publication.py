#!/usr/bin/env python3
"""Publish Campaign263's failed-regression recovery result and policy."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULT_V2 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_263_terminal_result_v2_20260816.json"
)
RESULT_V3 = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_263_terminal_result_v3_20260816.json"
)
POLICY_V410 = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v410_20260816.json"
)
POLICY_V411 = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v411_20260816.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_263/research_attempt_ledger_v10.json"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    if not (
        _sha(RESULT_V2)
        == "5b6966d11ecf79922ad09f11e8e0238e8fa5bfb0d23a722ff074d7f355181f1c"
        and _sha(POLICY_V410)
        == "20329b35da4c86a4b0f4baf5e79ee1f4a268f34cd0d4d5acc2891db0d50e62e6"
        and _sha(LEDGER)
        == "1b5d08d4b5062b442b741c5e57363107296923eee5581cfb7858d0ab5135470d"
    ):
        raise RuntimeError("Campaign263 validation publication inputs changed")
    result = json.loads(RESULT_V2.read_text(encoding="utf-8"))
    result["status"] = (
        "terminal_validation_recovery_first_focused_run_failed_zero_scientific_change"
    )
    result["recorded_at"] = "2026-08-16T14:24:00Z"
    result["supersedes_without_rewriting"] = {
        "path": str(RESULT_V2.relative_to(ROOT)),
        "sha256": _sha(RESULT_V2),
        "scientific_result_changed": False,
    }
    result["authoritative_inputs"].pop("campaign263_attempt_ledger_v9")
    result["authoritative_inputs"]["campaign263_attempt_ledger_v10"] = {
        "path": str(LEDGER.relative_to(ROOT)),
        "sha256": _sha(LEDGER),
    }
    result["attempt_accounting"].update(
        {
            "campaign263_effective_entry_count": 31,
            "infrastructure_failure_count": 22,
            "cumulative_historical_research_attempt_count": 2594,
        }
    )
    _write(RESULT_V3, result)

    policy = json.loads(POLICY_V410.read_text(encoding="utf-8"))
    policy["version"] = 411
    policy["status"] = "campaign263_terminal_validation_recovery_numeric_comparator_143"
    policy["recorded_at"] = "2026-08-16T14:25:00Z"
    policy["supersedes_without_rewriting"] = {
        "path": str(POLICY_V410.relative_to(ROOT)),
        "sha256": _sha(POLICY_V410),
    }
    policy["authoritative_campaign263_terminal_result"] = {
        "path": str(RESULT_V3.relative_to(ROOT)),
        "sha256": _sha(RESULT_V3),
    }
    policy["recovery_accounting"].update(
        {
            "campaign263_effective_entry_count": 31,
            "infrastructure_failure_count": 22,
            "cumulative_historical_research_attempt_count": 2594,
        }
    )
    _write(POLICY_V411, policy)
    print(
        json.dumps(
            {
                "result_v3_sha256": _sha(RESULT_V3),
                "policy_v411_sha256": _sha(POLICY_V411),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
