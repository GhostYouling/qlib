from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign265_no_return_audit as audit


def _private_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def _synthetic_accepted_source(root: Path, sessions: list[str]) -> tuple[int, str]:
    requests = audit.request_sequence(sessions)
    request_digest = audit.canonical_json_sha256(requests)
    source_root = root / audit.SOURCE_ROOT_RELATIVE
    source_root.mkdir(parents=True)
    (source_root / "cb_daily").mkdir()
    sidecar_order: list[dict] = []
    for request in requests:
        checkpoint, schema = audit._source_checkpoint(source_root, request)
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_bytes(f"checkpoint-{request['ordinal']}".encode())
        checkpoint.chmod(0o600)
        sidecar = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign265_source_checkpoint",
            "request_ordinal": request["ordinal"],
            "api": request["api"],
            "parameters": request["parameters"],
            "fields": request["fields"],
            "checkpoint_relative_path": str(checkpoint.relative_to(source_root)),
            "checkpoint_sha256": audit.file_sha256(checkpoint),
            "frame_sha256": f"{request['ordinal']:064x}",
            "schema": list(schema),
            "counters": {
                "source_rows": 1,
                "network_or_credential_access_performed": False,
                "forbidden_fields_read": False,
            },
            "raw_provider_response_persisted": False,
        }
        _private_json(checkpoint.with_suffix(checkpoint.suffix + ".meta.json"), sidecar)
        sidecar_order.append(
            {
                "request_ordinal": sidecar["request_ordinal"],
                "checkpoint_relative_path": sidecar["checkpoint_relative_path"],
                "checkpoint_sha256": sidecar["checkpoint_sha256"],
                "frame_sha256": sidecar["frame_sha256"],
            }
        )
    internal = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign265_source_manifest",
        "status": "complete_source_snapshot_pending_coverage_and_uniqueness",
        "provider": "Tushare Pro",
        "request_sequence_canonical_json_sha256": request_digest,
        "committed_request_count": len(requests),
        "checkpoint_order_sha256": audit.canonical_json_sha256(sidecar_order),
        "raw_provider_response_persisted": False,
        "daily_price_or_forward_return_read": False,
    }
    internal_path = source_root / "source_manifest.json"
    _private_json(internal_path, internal)
    repository = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign265_source_acceptance_manifest",
        "status": "accepted_source_snapshot_pending_coverage_and_ordered_uniqueness",
        "final_root": str(audit.SOURCE_ROOT_RELATIVE),
        "internal_manifest": str(audit.SOURCE_ROOT_RELATIVE / "source_manifest.json"),
        "internal_manifest_sha256": audit.file_sha256(internal_path),
        "committed_request_count": len(requests),
        "request_sequence_canonical_json_sha256": request_digest,
        "credential_value_or_digest_persisted": False,
        "raw_provider_response_persisted": False,
        "candidate_or_comparator_value_read": False,
        "daily_price_or_forward_return_read": False,
        "current_use_authorized": False,
    }
    _private_json(root / audit.SOURCE_MANIFEST_RELATIVE, repository)
    return len(requests), request_digest


def test_protocol_and_complete_numeric_comparator_order_are_exact() -> None:
    spec = audit.load_protocol()
    definitions = audit.comparison_definitions()
    assert len(definitions) == 143
    assert definitions[-1] == {
        "name": "intraday_amount_profile_spectral_entropy_60f",
        "score_direction": "higher",
    }
    assert (
        audit.c263.candidate._order_digest(definitions)
        == spec["ordered_numeric_uniqueness"]["comparator_order_sha256"]
        == audit.EXPECTED_COMPARATOR_ORDER_SHA256
    )


def test_calendar_universe_and_request_schedule_are_exact() -> None:
    sessions = audit.accepted_sessions()
    universe = audit.factor_universe()
    requests = audit.request_sequence(sessions)
    assert (len(sessions), sessions[0], sessions[-1]) == (
        1699,
        "2019-01-02",
        "2025-12-31",
    )
    assert len(universe) == 5451
    assert len(requests) == 1700
    assert (
        audit.canonical_json_sha256(requests) == audit.EXPECTED_REQUEST_SEQUENCE_SHA256
    )


def test_source_metadata_verification_hashes_bytes_without_decoding_parquet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sessions = ["2019-01-02", "2019-01-03", "2019-01-04"]
    count, digest = _synthetic_accepted_source(tmp_path, sessions)

    def forbidden(*args, **kwargs):
        raise AssertionError("source verifier decoded Parquet")

    monkeypatch.setattr(audit.pd, "read_parquet", forbidden)
    receipt = audit.verify_accepted_source_snapshot(
        repo_root=tmp_path,
        dates=sessions,
        expected_request_count=count,
        expected_request_digest=digest,
    )
    assert receipt["checkpoint_count"] == 4
    assert receipt["checkpoint_byte_hashes_verified"] == 4
    assert receipt["parquet_rows_decoded"] == 0
    assert receipt["candidate_values_read"] is False


def test_source_metadata_tamper_fails_closed_before_parquet_decode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sessions = ["2019-01-02"]
    count, digest = _synthetic_accepted_source(tmp_path, sessions)
    checkpoint = tmp_path / audit.SOURCE_ROOT_RELATIVE / "cb_daily" / "20190102.parquet"
    checkpoint.write_bytes(b"tampered")
    checkpoint.chmod(0o600)
    monkeypatch.setattr(
        audit.pd,
        "read_parquet",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("source verifier decoded Parquet")
        ),
    )
    with pytest.raises(audit.Campaign265NoReturnAuditError, match="checkpoint"):
        audit.verify_accepted_source_snapshot(
            repo_root=tmp_path,
            dates=sessions,
            expected_request_count=count,
            expected_request_digest=digest,
        )


def test_plan_missing_source_is_read_only_and_returns_one_blocker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(audit, "validate_static_bindings", lambda: {"frozen": True})
    monkeypatch.setattr(audit, "accepted_sessions", lambda: ["2019-01-02"])
    monkeypatch.setattr(
        audit.pd,
        "read_parquet",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("plan decoded Parquet")
        ),
    )
    output = tmp_path / "out.json"
    plan = audit.build_plan(repo_root=tmp_path, output_path=output)
    assert plan["ready"] is False
    assert plan["blockers"] == ["source_acceptance_manifest_absent_or_unsafe"]
    assert plan["source_parquet_rows_decoded"] == 0
    assert plan["candidate_values_read"] is False
    assert not output.exists()


def test_factor_formula_uses_same_bond_endpoints_and_issuer_median() -> None:
    basic = pd.DataFrame(
        [
            ["110001.SH", "CB", "SH600000", date(2018, 1, 1), None, "SH"],
            ["110002.SH", "CB", "SH600000", date(2018, 1, 1), None, "SH"],
            ["123001.SZ", "CB", "SZ000001", date(2018, 1, 1), None, "SZ"],
        ],
        columns=audit.adapter.NORMALIZED_BASIC_FIELDS,
    )
    lag = pd.DataFrame(
        [
            ["110001.SH", date(2019, 1, 2), 100.0, 25.0],
            ["110002.SH", date(2019, 1, 2), 100.0, 11.0],
            ["123001.SZ", date(2019, 1, 2), 100.0, 20.0],
        ],
        columns=audit.adapter.NORMALIZED_DAILY_FIELDS,
    )
    signal = pd.DataFrame(
        [
            ["110001.SH", date(2019, 1, 7), 100.0, 20.0],
            ["110002.SH", date(2019, 1, 7), 100.0, 10.0],
            ["123001.SZ", date(2019, 1, 7), 0.0, 19.0],
        ],
        columns=audit.adapter.NORMALIZED_DAILY_FIELDS,
    )
    values, stats = audit.factor_values_on_session(
        basic,
        lag,
        signal,
        lag_session="2019-01-02",
        signal_session="2019-01-07",
        universe=frozenset({"SH600000", "SZ000001"}),
    )
    assert values == [("SH600000", 3.0)]
    assert stats == {
        "denominator_equity_count": 2,
        "eligible_equity_count": 1,
        "active_cb_count": 3,
        "eligible_cb_count": 2,
    }


def test_candidate_builder_reads_exact_numeric_date_paths(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "cb_daily").mkdir(parents=True)
    basic = pd.DataFrame(
        [["110001.SH", "CB", "SH600000", date(2018, 1, 1), None, "SH"]],
        columns=audit.adapter.NORMALIZED_BASIC_FIELDS,
    )
    basic.to_parquet(source / "cb_basic.parquet", index=False)
    sessions = ["2019-01-02", "2019-01-03", "2019-01-04", "2019-01-07"]
    premiums = [25.0, 24.0, 23.0, 20.0]
    for session, premium in zip(sessions, premiums, strict=True):
        daily = pd.DataFrame(
            [["110001.SH", date.fromisoformat(session), 100.0, premium]],
            columns=audit.adapter.NORMALIZED_DAILY_FIELDS,
        )
        daily.to_parquet(
            source / "cb_daily" / f"{session.replace('-', '')}.parquet",
            index=False,
        )
    frame, receipt = audit.build_candidate_panel(
        source_root=source,
        sessions=sessions,
        universe=["SH600000"],
    )
    assert frame.to_dict(orient="records") == [
        {
            "trade_date": "2019-01-07",
            "symbol": "SH600000",
            audit.adapter.FACTOR_NAME: 5.0,
        }
    ]
    assert receipt["normalized_cb_daily_rows_decoded"] == 4
    assert (
        receipt["coverage_and_variation"]["gate_passed_before_comparator_values"]
        is False
    )


def test_coverage_gate_passes_only_with_all_six_frozen_conditions() -> None:
    sessions = pd.bdate_range("2019-01-02", periods=1300)
    passing = [
        {
            "signal_session": value.date().isoformat(),
            "denominator_equity_count": 100,
            "finite_values": np.arange(95, dtype=np.float64),
        }
        for value in sessions
    ]
    result = audit.coverage_and_variation(passing)
    assert result["gate_passed_before_comparator_values"] is True
    assert result["median_daily_coverage"] == 0.95
    assert result["eligible_names_p05"] == 95.0
    failing = [dict(row, finite_values=np.ones(95)) for row in passing]
    result = audit.coverage_and_variation(failing)
    assert result["gate_passed_before_comparator_values"] is False
    assert result["nonconstant_cross_sectional_sessions"] == 0


def test_ordered_comparator_audit_stops_at_first_failure() -> None:
    definitions = [
        {"name": "one", "score_direction": "higher"},
        {"name": "two", "score_direction": "higher"},
        {"name": "three", "score_direction": "higher"},
    ]
    calls: list[int] = []

    def loader(ordinal: int, definition: dict[str, str]):
        calls.append(ordinal)
        return {
            "comparison_factor": definition["name"],
            "gate_passed": ordinal == 1,
        }, {"read": definition["name"]}

    results, receipts, failed = audit.audit_ordered_comparators(definitions, loader)
    assert calls == [1, 2]
    assert [item["comparison_factor"] for item in results] == ["one", "two"]
    assert [item["ordinal"] for item in receipts] == [1, 2]
    assert failed == 2


def test_alignment_is_exact_intersection_without_fill() -> None:
    aligned, matched = audit._aligned_values(
        source_keys=np.asarray([10, 30], dtype=np.int64),
        source_values=np.asarray([1.0, 3.0]),
        target_keys=np.asarray([10, 20, 30], dtype=np.int64),
    )
    assert matched == 2
    assert aligned[[0, 2]].tolist() == [1.0, 3.0]
    assert np.isnan(aligned[1])


def test_atomic_publication_is_exclusive_and_private(tmp_path: Path) -> None:
    output = tmp_path / "result.json"
    audit.atomic_exclusive_json(output, {"status": "first"})
    assert json.loads(output.read_text(encoding="utf-8")) == {"status": "first"}
    assert output.stat().st_mode & 0o777 == 0o600
    with pytest.raises(audit.Campaign265NoReturnAuditError, match="already exists"):
        audit.atomic_exclusive_json(output, {"status": "second"})
    assert json.loads(output.read_text(encoding="utf-8")) == {"status": "first"}
