#!/usr/bin/env python3
"""Publish Campaign263's frozen-byte exemption authority."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RP = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_263_terminal_result_v5_20260816.json"
)
RO = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_263_terminal_result_v6_20260816.json"
)
PP = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v413_20260816.json"
)
PO = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v414_20260816.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_263/research_attempt_ledger_v13.json"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    if not (
        _sha(RP) == "111fd75315ff5815ee450cca1cac615c0b8d481a632b5cde9ddddc78cd0914fd"
        and _sha(PP)
        == "5393402db783cb60378c8241508ce95a01a3271bb07cca100ae5f2e55dd2bc1c"
        and _sha(LEDGER)
        == "e6075d529195cf87364b8b873d273eea57e23450cfb248f77ceead7782ca2af2"
    ):
        raise RuntimeError("Campaign263 exemption publication inputs changed")
    result = json.loads(RP.read_text(encoding="utf-8"))
    result["status"] = (
        "terminal_frozen_black_exemption_accounted_zero_scientific_change"
    )
    result["recorded_at"] = "2026-08-16T14:42:00Z"
    result["supersedes_without_rewriting"] = {
        "path": str(RP.relative_to(ROOT)),
        "sha256": _sha(RP),
        "scientific_result_changed": False,
    }
    result["authoritative_inputs"].pop("campaign263_attempt_ledger_v12")
    result["authoritative_inputs"]["campaign263_attempt_ledger_v13"] = {
        "path": str(LEDGER.relative_to(ROOT)),
        "sha256": _sha(LEDGER),
    }
    result["attempt_accounting"].update(
        {
            "campaign263_effective_entry_count": 34,
            "infrastructure_failure_count": 25,
            "cumulative_historical_research_attempt_count": 2597,
        }
    )
    _write(RO, result)
    policy = json.loads(PP.read_text(encoding="utf-8"))
    policy["version"] = 414
    policy["status"] = (
        "campaign263_terminal_frozen_black_exemption_numeric_comparator_143"
    )
    policy["recorded_at"] = "2026-08-16T14:43:00Z"
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
            "campaign263_effective_entry_count": 34,
            "infrastructure_failure_count": 25,
            "cumulative_historical_research_attempt_count": 2597,
        }
    )
    policy["static_validation_boundary"] = {
        "black_non_exempt_file_count": 17,
        "black_frozen_exempt_file_count": 5,
        "frozen_files_rewritten": False,
        "ruff_all_campaign263_files_required": True,
    }
    _write(PO, policy)
    print(
        json.dumps(
            {"result_v6_sha256": _sha(RO), "policy_v414_sha256": _sha(PO)},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
