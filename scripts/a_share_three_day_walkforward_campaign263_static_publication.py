#!/usr/bin/env python3
"""Publish Campaign263's terminal static-check recovery authority."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULT_PRIOR = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_263_terminal_result_v3_20260816.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_263_terminal_result_v4_20260816.json"
)
POLICY_PRIOR = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v411_20260816.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v412_20260816.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_263/research_attempt_ledger_v11.json"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    if not (
        _sha(RESULT_PRIOR)
        == "d611cb913eb953d3720dd4f1ad95a829d4557bd7636311243f7fbe7a489842d1"
        and _sha(POLICY_PRIOR)
        == "d2c021746d0c664f0884fdcea1ffa4d43109b51cb6ec6d810f9efc63bf0cb359"
        and _sha(LEDGER)
        == "fabbfa757863f8389ed30c55a3b7a5f8c1f73267167ad1b7b7678bd38a73bb5e"
    ):
        raise RuntimeError("Campaign263 static publication inputs changed")
    result = json.loads(RESULT_PRIOR.read_text(encoding="utf-8"))
    result["status"] = (
        "terminal_static_recovery_black_failure_accounted_zero_scientific_change"
    )
    result["recorded_at"] = "2026-08-16T14:30:00Z"
    result["supersedes_without_rewriting"] = {
        "path": str(RESULT_PRIOR.relative_to(ROOT)),
        "sha256": _sha(RESULT_PRIOR),
        "scientific_result_changed": False,
    }
    result["authoritative_inputs"].pop("campaign263_attempt_ledger_v10")
    result["authoritative_inputs"]["campaign263_attempt_ledger_v11"] = {
        "path": str(LEDGER.relative_to(ROOT)),
        "sha256": _sha(LEDGER),
    }
    result["attempt_accounting"].update(
        {
            "campaign263_effective_entry_count": 32,
            "infrastructure_failure_count": 23,
            "cumulative_historical_research_attempt_count": 2595,
        }
    )
    _write(RESULT, result)
    policy = json.loads(POLICY_PRIOR.read_text(encoding="utf-8"))
    policy["version"] = 412
    policy["status"] = "campaign263_terminal_static_recovery_numeric_comparator_143"
    policy["recorded_at"] = "2026-08-16T14:31:00Z"
    policy["supersedes_without_rewriting"] = {
        "path": str(POLICY_PRIOR.relative_to(ROOT)),
        "sha256": _sha(POLICY_PRIOR),
    }
    policy["authoritative_campaign263_terminal_result"] = {
        "path": str(RESULT.relative_to(ROOT)),
        "sha256": _sha(RESULT),
    }
    policy["recovery_accounting"].update(
        {
            "campaign263_effective_entry_count": 32,
            "infrastructure_failure_count": 23,
            "cumulative_historical_research_attempt_count": 2595,
        }
    )
    _write(POLICY, policy)
    print(
        json.dumps(
            {"result_v4_sha256": _sha(RESULT), "policy_v412_sha256": _sha(POLICY)},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
