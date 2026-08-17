from scripts import a_share_three_day_walkforward_campaign075_no_return_audit_v4 as repair


def test_overlay_changes_only_campaign070_manifest_sha() -> None:
    original = repair.v3._snapshot_configs()
    corrected = repair._corrected_snapshot_configs()
    assert set(original) == set(corrected) == {68, 69, 70, 71, 72, 73, 74}
    changes = []
    for campaign in sorted(original):
        for key in original[campaign]:
            if original[campaign][key] != corrected[campaign][key]:
                changes.append((campaign, key))
    assert changes == [(70, "manifest_sha256")]


def test_campaign070_correction_is_exact_and_all_manifest_hashes_are_well_formed() -> None:
    corrected = repair._corrected_snapshot_configs()
    assert corrected[70]["manifest_sha256"] == repair.CORRECT_C70_MANIFEST_SHA256
    assert all(len(str(item["manifest_sha256"])) == 64 for item in corrected.values())


def test_overlay_preserves_full_restart_and_no_reuse_semantics() -> None:
    spec = repair.load_correction_overlay()
    assert spec["retry"]["partial_statistics_reused"] is False
    assert spec["retry"]["restart_from_candidate_snapshot_and_coverage"] is True
    assert spec["sole_correction"]["manifest_file_rewritten"] is False
