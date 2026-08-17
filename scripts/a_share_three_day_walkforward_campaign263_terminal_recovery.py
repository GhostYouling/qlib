#!/usr/bin/env python3
"""Append Campaign263's post-result report-publication failure."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PREDECESSOR = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_263/research_attempt_ledger_v8.json"
)
FAILURE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_263_unified_report_patch_failure_20260816.json"
)
OUTPUT = PREDECESSOR.with_name("research_attempt_ledger_v9.json")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _entry_hash(entry: dict[str, Any]) -> str:
    body = {key: value for key, value in entry.items() if key != "entry_sha256"}
    payload = json.dumps(
        body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def build() -> dict[str, Any]:
    prior = json.loads(PREDECESSOR.read_text(encoding="utf-8"))
    if (
        _sha256(PREDECESSOR)
        != "6c6918d5a985f6fed72e5ce339299351b3f48ac006831f7877dfdf9220dbe6d8"
    ):
        raise RuntimeError("Campaign263 terminal ledger v8 changed")
    entry: dict[str, Any] = {
        "ordinal": 30,
        "attempt_id": "campaign263_infrastructure_021",
        "attempt_class": "infrastructure_failure",
        "phase": "unified_report_publication",
        "status": "failed_apply_patch_parser_before_any_file_write",
        "scientific_attempt": False,
        "result_consumed": False,
        "artifact": {
            "path": str(FAILURE.relative_to(REPO_ROOT)),
            "sha256": _sha256(FAILURE),
        },
        "previous_entry_sha256": prior["chain_tip_sha256"],
    }
    entry["entry_sha256"] = _entry_hash(entry)
    return {
        "schema_version": 9,
        "kind": "a_share_three_day_walkforward_campaign263_append_only_research_attempt_ledger",
        "status": "campaign263_terminal_recovery_twenty_one_infrastructure_failures_eight_prevalue_routes_one_return_reading_development_trial_zero_survivors_stress_closed",
        "recorded_at": "2026-08-16T14:16:00Z",
        "chain_hash_algorithm": "sha256_of_canonical_json_without_entry_sha256",
        "authoritative_predecessor": {
            "path": str(PREDECESSOR.relative_to(REPO_ROOT)),
            "sha256": _sha256(PREDECESSOR),
            "effective_entry_count": prior["effective_entry_count"],
            "chain_tip_sha256": prior["chain_tip_sha256"],
            "cumulative_historical_research_attempt_count": prior[
                "cumulative_historical_research_attempt_count"
            ],
            "cumulative_return_reading_development_trial_count": prior[
                "cumulative_return_reading_development_trial_count"
            ],
        },
        "delta_entries": [entry],
        "effective_entry_count": 30,
        "effective_infrastructure_failure_attempt_count": 21,
        "effective_prevalue_scientific_attempt_count": 8,
        "effective_complete_factor_attempt_count": 1,
        "effective_return_reading_development_trial_count": 1,
        "cumulative_historical_research_attempt_count": 2593,
        "cumulative_return_reading_development_trial_count": 315,
        "library_state": prior["library_state"],
        "research_boundary": prior["research_boundary"],
        "candidate49": prior["candidate49"],
        "chain_tip_sha256": entry["entry_sha256"],
    }


def main() -> int:
    value = build()
    OUTPUT.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"path": str(OUTPUT), "sha256": _sha256(OUTPUT)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
