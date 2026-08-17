from scripts import a_share_three_day_walkforward_campaign075_no_return_audit_v5 as repair


def test_captured_original_callable_survives_monkeypatch_without_recursion() -> None:
    original = repair.v4.v3._snapshot_configs
    assert original is repair._ORIGINAL_V3_SNAPSHOT_CONFIGS
    try:
        repair.v4.v3._snapshot_configs = repair._corrected_snapshot_configs
        configs = repair.v4.v3._snapshot_configs()
    finally:
        repair.v4.v3._snapshot_configs = original
    assert configs[70]["manifest_sha256"] == repair.v4.CORRECT_C70_MANIFEST_SHA256


def test_v5_preserves_v4_single_field_correction() -> None:
    original = repair._ORIGINAL_V3_SNAPSHOT_CONFIGS()
    corrected = repair._corrected_snapshot_configs()
    changes = []
    for campaign in sorted(original):
        for key in original[campaign]:
            if original[campaign][key] != corrected[campaign][key]:
                changes.append((campaign, key))
    assert changes == [(70, "manifest_sha256")]
    assert all(len(str(item["manifest_sha256"])) == 64 for item in corrected.values())


def test_v5_protocol_freezes_full_restart_without_research_changes() -> None:
    spec = repair.load_repair_protocol()
    assert spec["sole_implementation_repair"]["corrected_research_fields"] == []
    assert spec["sole_implementation_repair"]["additional_snapshot_hash_corrections"] == []
    assert spec["retry"]["partial_statistics_reused"] is False
    assert spec["retry"]["restart_from_candidate_snapshot_and_coverage"] is True
