#!/usr/bin/env python3
"""Publish Campaign263's final pre-validation authority."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RP = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_263_terminal_result_v4_20260816.json"
)
RO = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_263_terminal_result_v5_20260816.json"
)
PP = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v412_20260816.json"
)
PO = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v413_20260816.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_263/research_attempt_ledger_v12.json"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    if not (
        _sha(RP) == "dd984f651e8e63334ffe57b7b9cfb774f76b0717a5c5a29adcaf7b8fd15ee1d1"
        and _sha(PP)
        == "b7d1bdd1669c6ba124fb3fb4889751925e63e866b8d42c2b9a1e83c79df079e1"
        and _sha(LEDGER)
        == "d1d716c2b5a6ad61bb122ea8fb967b2232cd38550c948f56691e56222efb8dfb"
    ):
        raise RuntimeError("Campaign263 final publication inputs changed")
    result = json.loads(RP.read_text(encoding="utf-8"))
    result["status"] = (
        "terminal_final_prevalidation_all_failures_accounted_zero_scientific_change"
    )
    result["recorded_at"] = "2026-08-16T14:35:00Z"
    result["supersedes_without_rewriting"] = {
        "path": str(RP.relative_to(ROOT)),
        "sha256": _sha(RP),
        "scientific_result_changed": False,
    }
    result["authoritative_inputs"].pop("campaign263_attempt_ledger_v11")
    result["authoritative_inputs"]["campaign263_attempt_ledger_v12"] = {
        "path": str(LEDGER.relative_to(ROOT)),
        "sha256": _sha(LEDGER),
    }
    result["attempt_accounting"].update(
        {
            "campaign263_effective_entry_count": 33,
            "infrastructure_failure_count": 24,
            "cumulative_historical_research_attempt_count": 2596,
        }
    )
    _write(RO, result)
    policy = json.loads(PP.read_text(encoding="utf-8"))
    policy["version"] = 413
    policy["status"] = "campaign263_terminal_final_prevalidation_numeric_comparator_143"
    policy["recorded_at"] = "2026-08-16T14:36:00Z"
    policy["supersedes_without_rewriting"] = {
        "path": str(PP.relative_to(ROOT)),
        "sha256": _sha(PP),
    }
    policy["authoritative_campaign263_terminal_result"] = {
        "path": str(RO.relative_to(ROOT)),
        "sha256": _sha(RO),
    }
    policy["recovery_accounting"].update(
        {
            "campaign263_effective_entry_count": 33,
            "infrastructure_failure_count": 24,
            "cumulative_historical_research_attempt_count": 2596,
        }
    )
    _write(PO, policy)
    print(
        json.dumps(
            {"result_v5_sha256": _sha(RO), "policy_v413_sha256": _sha(PO)},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
