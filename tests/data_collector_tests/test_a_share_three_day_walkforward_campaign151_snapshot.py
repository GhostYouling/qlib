from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import a_share_three_day_walkforward_campaign151_snapshot as c151


TEST_PATH = Path(__file__).resolve()


def _activation_payload() -> dict:
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign151_snapshot_runner_activation",
        "status": "runner_and_tests_frozen_before_campaign151_historical_values",
        "authoritative_inputs": {
            "plan_runner": {
                "path": str(Path(c151.__file__).resolve()),
                "sha256": c151._sha256(Path(c151.__file__).resolve()),
            },
            "plan_runner_test": {
                "path": str(TEST_PATH),
                "sha256": c151._sha256(TEST_PATH),
            },
            "plan_launch_failure": {
                "path": str(c151.PLAN_LAUNCH_FAILURE),
                "sha256": c151.PLAN_LAUNCH_FAILURE_SHA256,
            },
            "builder_implementation_freeze": {
                "path": str(c151.BUILDER_IMPLEMENTATION_FREEZE),
                "sha256": c151.BUILDER_IMPLEMENTATION_FREEZE_SHA256,
            },
            "source_bound_builder": {
                "path": str(c151.BUILDER_MODULE_PATH),
                "sha256": c151.BUILDER_MODULE_SHA256,
            },
            "source_bound_builder_test": {
                "path": str(c151.BUILDER_TEST_PATH),
                "sha256": c151.BUILDER_TEST_SHA256,
            },
            "campaign151_state_v2": {
                "path": str(c151.STATE_PATH),
                "sha256": c151.STATE_SHA256,
            },
            "numeric_policy_v205": {
                "path": str(c151.POLICY_PATH),
                "sha256": c151.POLICY_SHA256,
            },
            "formula_frozen_validation": {
                "path": str(c151.FORMULA_VALIDATION_PATH),
                "sha256": c151.FORMULA_VALIDATION_SHA256,
            },
        },
        "plan_contract": {
            "metadata_only": True,
            "parquet_or_npz_opened": False,
            "ready_true_and_exit_zero_required": True,
        },
        "build_contract": {
            "confirmed_build_required": True,
            "rerun_same_plan_in_process": True,
        },
        "research_boundary": {
            "historical_minute_source_rows_or_values_read_by_activation_or_plan": False,
            "prior_authorized_build_historical_minute_amount_values_read": True,
            "provider_request_issued": False,
            "credential_loaded": False,
        },
    }


@pytest.fixture
def activation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "activation.json"
    path.write_text(
        json.dumps(_activation_payload(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(c151, "DEFAULT_ACTIVATION_RECORD", path)
    return path


def test_campaign151_plan_is_zero_value_and_ready(
    activation: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("metadata-only plan opened a historical value payload")

    monkeypatch.setattr(c151.features.pd, "read_parquet", forbidden)
    monkeypatch.setattr(c151.features.np, "load", forbidden)
    monkeypatch.setattr(
        c151,
        "_validate_output_gate",
        lambda _data_root: {
            "final_root_exists": False,
            "resume_partial": True,
            "lock_available": True,
            "free_bytes": c151.MINIMUM_FREE_BYTES,
            "minimum_free_bytes": c151.MINIMUM_FREE_BYTES,
        },
    )
    plan = c151.plan_status(workers=4, activation_record=activation)
    assert plan["ready"] is True
    assert plan["failed_gates"] == []
    assert all(gate["ready"] for gate in plan["gates"].values())
    assert plan["historical_parquet_or_npz_payload_opened_by_plan"] is False
    assert plan["historical_minute_source_rows_or_values_read_by_plan"] is False
    assert plan["prior_authorized_build_historical_minute_amount_values_read"] is True
    assert plan["provider_request_issued"] is False
    assert plan["credential_loaded"] is False
    assert plan["gates"]["source_metadata"]["evidence"] == {
        "raw_partitions": 33_015,
        "joint_partitions": 33_015,
        "joint_rows": 7_724_498,
        "symbols": 5_396,
    }


def test_campaign151_plan_fails_closed_on_activation_hash_change(
    activation: Path,
) -> None:
    payload = json.loads(activation.read_text(encoding="utf-8"))
    payload["authoritative_inputs"]["plan_runner"]["sha256"] = "0" * 64
    activation.write_text(json.dumps(payload), encoding="utf-8")
    plan = c151.plan_status(workers=4, activation_record=activation)
    assert plan["ready"] is False
    assert "activation" in plan["failed_gates"]
    assert plan["gates"]["activation"]["ready"] is False


def test_campaign151_partial_layout_accepts_only_frozen_checkpoint_shapes(
    tmp_path: Path,
) -> None:
    partial = c151.features.partial_root(tmp_path)
    partial.mkdir(parents=True)
    (partial / ".metadata").mkdir()
    (partial / ".metadata/raw_amount_accumulator.npz").write_bytes(b"not-opened")
    (partial / "partitions/2021").mkdir(parents=True)
    (partial / "partitions/2021/sh600000.parquet").write_bytes(b"not-opened")
    (partial / ".metadata/partitions/2021").mkdir(parents=True)
    (partial / ".metadata/partitions/2021/sh600000.json").write_text("{}")
    assert c151._partial_layout_is_metadata_safe(partial) is True
    (partial / "unexpected.txt").write_text("reject")
    assert c151._partial_layout_is_metadata_safe(partial) is False


def test_campaign151_output_gate_rejects_final_and_accepts_safe_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(c151, "MINIMUM_FREE_BYTES", 1)
    partial = c151.features.partial_root(tmp_path)
    partial.mkdir(parents=True)
    evidence = c151._validate_output_gate(tmp_path)
    assert evidence["resume_partial"] is True
    final = c151.features.output_root(tmp_path)
    final.mkdir(parents=True)
    with pytest.raises(c151.Campaign151SnapshotPlanError, match="never overwritten"):
        c151._validate_output_gate(tmp_path)


def test_campaign151_missing_confirmation_never_calls_builder(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        c151,
        "plan_status",
        lambda **_kwargs: {
            "ready": True,
            "status": "ready_for_confirmed_build",
            "failed_gates": [],
            "gates": {},
        },
    )

    def forbidden(**_kwargs):
        raise AssertionError("builder called without confirmation")

    monkeypatch.setattr(c151.features, "build_snapshot", forbidden)
    assert c151.main(["build", "--workers", "2"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["ready"] is False
    assert result["failed_gates"] == ["confirm_build"]


def test_campaign151_confirmed_build_repeats_ready_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        c151,
        "plan_status",
        lambda **_kwargs: {
            "ready": True,
            "status": "ready_for_confirmed_build",
            "failed_gates": [],
            "gates": {},
        },
    )
    manifest = tmp_path / "snapshot_manifest.json"
    manifest.write_text("{}\n", encoding="utf-8")
    observed: list[dict] = []

    def fake_build(**kwargs):
        observed.append(kwargs)
        return manifest

    monkeypatch.setattr(c151.features, "build_snapshot", fake_build)
    assert c151.main(["build", "--workers", "3", "--confirm-build"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["ready_plan_repeated_in_process"] is True
    assert result["manifest_path"] == str(manifest)
    assert observed == [
        {
            "data_root": c151.DEFAULT_DATA_ROOT,
            "workers": 3,
            "confirm_build": True,
        }
    ]
