from __future__ import annotations

import pytest

from scripts import a_share_three_day_walkforward_campaign063_manifest_namespace_repair as repair


EXPECTED_NAMES = {
    "campaign004",
    "MARKET_BENCHMARK_MANIFEST_SHA256",
    "MARKET_BENCHMARK_BYTE_SHA256",
    "MARKET_BENCHMARK_FRAME_SHA256",
    "MINIMUM_LEAVE_ONE_OUT_PEERS",
    "MINIMUM_INFORMATIVE_POSITIONS",
}


def test_repair_bindings_fix_exact_six_name_set() -> None:
    result = repair.verify_repair_bindings()
    assert set(result["injected_names"]) == EXPECTED_NAMES
    assert set(repair.FROZEN_NAMESPACE_BINDINGS) == EXPECTED_NAMES


def test_install_only_injects_frozen_publication_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        repair.core._engine,
        "extract_amount_profiles",
        repair.empty_repair._ORIGINAL_EXTRACT_PROFILES,
    )
    for name in EXPECTED_NAMES:
        monkeypatch.delitem(repair.core._engine, name, raising=False)
    original_compute = repair.core._engine["compute_output_frame"]
    original_validate = repair.core._engine["_validate_manifest"]
    repair.install_repair()
    assert repair.core._engine["extract_amount_profiles"] is repair.empty_repair.extract_profiles_compat
    assert repair.core._engine["compute_output_frame"] is original_compute
    assert repair.core._engine["_validate_manifest"] is original_validate
    for name, value in repair.FROZEN_NAMESPACE_BINDINGS.items():
        assert repair.core._engine[name] is value or repair.core._engine[name] == value


def test_conflicting_existing_namespace_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        repair.core._engine,
        "extract_amount_profiles",
        repair.empty_repair._ORIGINAL_EXTRACT_PROFILES,
    )
    monkeypatch.setitem(
        repair.core._engine,
        "MINIMUM_INFORMATIVE_POSITIONS",
        235,
    )
    with pytest.raises(
        repair.Campaign063ManifestNamespaceRepairError,
        match="conflicting MINIMUM_INFORMATIVE_POSITIONS",
    ):
        repair.install_repair()
