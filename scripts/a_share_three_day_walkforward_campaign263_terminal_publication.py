#!/usr/bin/env python3
"""Publish Campaign263's recovery terminal result and numeric policy."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
RESULT_V1 = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_263_terminal_result_20260816.json"
)
RESULT_V2 = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_263_terminal_result_v2_20260816.json"
)
POLICY_V409 = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v409_20260816.json"
)
POLICY_V410 = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v410_20260816.json"
)
LEDGER_V9 = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_263/research_attempt_ledger_v9.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    if not (
        _sha256(RESULT_V1)
        == "825c5b28a1916b949a0ab7d0f5357b47b95619e4df2580389e6bf0b3bd0e2b89"
        and _sha256(POLICY_V409)
        == "baad967cacfd732db7333a87e5d5d63f001b0176687242d94e2333d1955cc0f1"
        and _sha256(LEDGER_V9)
        == "dea448279b10f0321a4d250e3dc870529a17136b7304fae5b17ba9759b4d07c0"
    ):
        raise RuntimeError("Campaign263 terminal publication inputs changed")

    result = json.loads(RESULT_V1.read_text(encoding="utf-8"))
    result["status"] = (
        "terminal_recovery_all_142_uniqueness_gates_passed_one_frozen_"
        "development_trial_zero_survivors_stress_closed_report_failure_accounted"
    )
    result["recorded_at"] = "2026-08-16T14:17:00Z"
    result["supersedes_without_rewriting"] = {
        "path": str(RESULT_V1.relative_to(REPO_ROOT)),
        "sha256": _sha256(RESULT_V1),
        "scientific_result_changed": False,
    }
    result["authoritative_inputs"].pop("campaign263_attempt_ledger_v8")
    result["authoritative_inputs"]["campaign263_attempt_ledger_v9"] = {
        "path": str(LEDGER_V9.relative_to(REPO_ROOT)),
        "sha256": _sha256(LEDGER_V9),
    }
    result["attempt_accounting"].update(
        {
            "campaign263_effective_entry_count": 30,
            "infrastructure_failure_count": 21,
            "cumulative_historical_research_attempt_count": 2593,
        }
    )
    _write(RESULT_V2, result)

    policy = json.loads(POLICY_V409.read_text(encoding="utf-8"))
    policy["version"] = 410
    policy["status"] = (
        "campaign263_terminal_recovery_numeric_comparator_143_report_failure_accounted"
    )
    policy["recorded_at"] = "2026-08-16T14:18:00Z"
    policy["supersedes_without_rewriting"] = {
        "path": str(POLICY_V409.relative_to(REPO_ROOT)),
        "sha256": _sha256(POLICY_V409),
    }
    policy["authoritative_campaign263_terminal_result"] = {
        "path": str(RESULT_V2.relative_to(REPO_ROOT)),
        "sha256": _sha256(RESULT_V2),
    }
    policy["recovery_accounting"] = {
        "campaign263_effective_entry_count": 30,
        "infrastructure_failure_count": 21,
        "prevalue_scientific_route_count": 8,
        "return_reading_development_trial_count": 1,
        "cumulative_historical_research_attempt_count": 2593,
        "cumulative_return_reading_development_trial_count": 315,
        "scientific_result_changed": False,
    }
    _write(POLICY_V410, policy)
    print(
        json.dumps(
            {
                "result_v2_sha256": _sha256(RESULT_V2),
                "policy_v410_sha256": _sha256(POLICY_V410),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
