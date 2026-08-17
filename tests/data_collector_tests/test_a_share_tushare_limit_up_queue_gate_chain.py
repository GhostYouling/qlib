from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from scripts import a_share_tushare_limit_up_queue_gate_chain as chain


def _plan(*, ready: bool, blockers: list[str]) -> dict[str, Any]:
    return {
        "ready": ready,
        "exit_code_if_executed": 0 if ready else 2,
        "blockers": blockers,
        "credential_loaded": False,
        "provider_request_issued": False,
        "candidate_or_comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "partition_year_2024_or_2025_values_read": False,
    }


def _inspection(status: str) -> dict[str, Any]:
    return {
        "valid": True,
        "status": status,
        "credential_loaded": False,
        "provider_request_issued": False,
    }


def test_closed_plans_are_validated_without_masking_their_exit_codes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake(stage: dict[str, Any]) -> tuple[int, str, str]:
        if stage["kind"] == "plan":
            return 2, json.dumps(_plan(ready=False, blockers=[stage["name"]])), ""
        return 0, json.dumps(_inspection(f"no_{stage['name']}")), ""

    monkeypatch.setattr(chain, "_run_stage", fake)
    payload = chain.build_status()
    assert payload["valid"] is True
    assert payload["all_scientific_plans_ready"] is False
    assert payload["provider_action_authorized_by_this_command"] is False
    assert {
        item["process_exit_code"]
        for name, item in payload["stages"].items()
        if name.endswith("_plan")
    } == {2}


def test_mismatched_or_unsafe_child_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stage = chain.STAGES[0]
    monkeypatch.setattr(
        chain,
        "_run_stage",
        lambda _stage: (0, json.dumps(_plan(ready=False, blockers=["closed"])), ""),
    )
    with pytest.raises(chain.GateChainError, match="plan exit semantics changed"):
        chain._validate_stage(stage)

    unsafe = _plan(ready=False, blockers=["closed"])
    unsafe["provider_request_issued"] = True
    monkeypatch.setattr(
        chain,
        "_run_stage",
        lambda _stage: (2, json.dumps(unsafe), ""),
    )
    with pytest.raises(chain.GateChainError, match="crossed zero-value boundary"):
        chain._validate_stage(stage)


def test_real_status_entry_preserves_every_exit_and_boundary() -> None:
    completed = subprocess.run(
        [sys.executable, str(Path(chain.__file__).resolve()), "status"],
        cwd=chain.ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=180,
    )
    assert completed.returncode == 0
    assert completed.stderr == ""
    payload = json.loads(completed.stdout)
    assert payload["valid"] is True
    assert payload["all_scientific_plans_ready"] is False
    assert payload["provider_action_authorized_by_this_command"] is False
    assert payload["provider_request_issued"] is False
    assert payload["candidate_or_comparator_values_read"] is False
    assert payload["historical_daily_price_or_forward_return_values_read"] is False
    assert payload["partition_year_2024_or_2025_values_read"] is False
    assert [
        payload["stages"][name]["process_exit_code"]
        for name in payload["stage_order"]
        if name.endswith("_plan")
    ] == [2, 2, 2, 2, 2]
