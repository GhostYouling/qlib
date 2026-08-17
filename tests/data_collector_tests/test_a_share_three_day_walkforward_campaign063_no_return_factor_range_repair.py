from __future__ import annotations

import pytest

from scripts import a_share_three_day_walkforward_campaign063_no_return_factor_range_repair as repair


def test_repair_bindings_freeze_exact_factor_and_range() -> None:
    result = repair.verify_repair_bindings()
    assert result["factor"] == repair.core.FACTOR_NAME
    assert result["frozen_factor_range"] == [0.0, 1.0]


def test_install_adds_only_frozen_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = repair._generic_engine()
    monkeypatch.delitem(engine.FACTOR_RANGES, repair.core.FACTOR_NAME, raising=False)
    original_loader = engine.load_factor_frame
    original_coverage = engine.coverage_and_capacity
    repair.install_repair()
    assert engine.FACTOR_RANGES[repair.core.FACTOR_NAME] == (0.0, 1.0)
    assert engine.load_factor_frame is original_loader
    assert engine.coverage_and_capacity is original_coverage


def test_conflicting_range_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = repair._generic_engine()
    monkeypatch.setitem(engine.FACTOR_RANGES, repair.core.FACTOR_NAME, (-1.0, 1.0))
    with pytest.raises(
        repair.Campaign063NoReturnFactorRangeRepairError,
        match="already conflicts",
    ):
        repair.install_repair()
