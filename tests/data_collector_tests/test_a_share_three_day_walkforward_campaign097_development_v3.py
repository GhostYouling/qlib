from __future__ import annotations

from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign097_v3 as repair


def test_v2_freezes_failure_and_two_entry_ledger_are_immutable() -> None:
    assert repair._sha256(Path(repair.v2.__file__).resolve()) == repair.V2_RUNNER_SHA256
    assert (
        repair._sha256(repair.v2.AUDIT_IMPLEMENTATION_FREEZE)
        == repair.V2_IMPLEMENTATION_FREEZE_SHA256
    )
    assert (
        repair._sha256(repair.v2.AUDIT_ACTIVATION_BINDING)
        == repair.V2_ACTIVATION_SHA256
    )
    assert repair._sha256(repair.FAILURE_RECORD) == repair.FAILURE_RECORD_SHA256
    ledger = (
        repair.REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_097/walkforward/trial_ledger.json"
    )
    assert repair._sha256(ledger) == repair.FAILED_LEDGER_SHA256


def test_active_namespace_is_wrapped_generator_globals() -> None:
    namespace = repair.active_loader_namespace()
    assert namespace is repair.v2.v1.run_development.__globals__
    assert (
        namespace["_load_compact_factor_panel"]
        is repair.v2.v1._load_compact_factor_panel
    )


def test_active_loader_patch_reaches_contextmanager_and_restores() -> None:
    namespace = repair.active_loader_namespace()
    original = namespace["_load_compact_factor_panel"]
    with repair._temporary_active_loader_repair():
        assert (
            namespace["_load_compact_factor_panel"]
            is repair.v2._load_compact_factor_panel
        )
        with repair.v2.v1._temporary_compact_factor_loader():
            assert (
                repair.v2.v1.base.load_factor_panel
                is repair.v2._load_compact_factor_panel
            )
    assert namespace["_load_compact_factor_panel"] is original


def test_append_only_two_failures_are_preserved() -> None:
    ledger = repair.v2.v1.base.load_json(
        repair.REPO_ROOT
        / "data/experiments/short_horizon/historical_walkforward/campaign_097/walkforward/trial_ledger.json"
    )
    assert [entry["phase"] for entry in ledger["entries"]] == [
        "infrastructure_failure",
        "infrastructure_failure",
    ]
    assert [entry["ordinal"] for entry in ledger["entries"]] == [1, 2]
