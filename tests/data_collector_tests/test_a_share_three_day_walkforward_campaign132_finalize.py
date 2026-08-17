import copy

import pytest

from scripts import a_share_three_day_walkforward_campaign132_finalize as finalize


def _ledger() -> dict:
    entry = {
        "attempt_id": "a",
        "previous_entry_sha256": finalize.CHAIN_GENESIS,
    }
    entry["entry_sha256"] = finalize.canonical_sha256(entry)
    return {
        "entries": [entry],
        "entry_count": 1,
        "infrastructure_failure_attempt_count": 0,
        "chain_tip_sha256": entry["entry_sha256"],
    }


def test_validate_chain_accepts_canonical_entry() -> None:
    ledger = _ledger()
    assert finalize.validate_chain(ledger) == ledger["chain_tip_sha256"]


def test_validate_chain_rejects_mutation() -> None:
    ledger = _ledger()
    ledger["entries"][0]["attempt_id"] = "changed"
    with pytest.raises(finalize.Campaign132FinalizeError, match="digest changed"):
        finalize.validate_chain(ledger)


def test_append_failure_extends_without_rewriting(monkeypatch) -> None:
    ledger = _ledger()
    before = copy.deepcopy(ledger)
    monkeypatch.setitem(finalize.EXPECTED, finalize.FAILURE_011, "f" * 64)
    result = finalize.append_failure(ledger)
    assert ledger == before
    assert result["entries"][:-1] == before["entries"]
    assert result["entry_count"] == 2
    assert result["infrastructure_failure_attempt_count"] == 1
    assert finalize.validate_chain(result) == result["chain_tip_sha256"]
