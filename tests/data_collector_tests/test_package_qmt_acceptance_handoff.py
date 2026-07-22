"""Offline tests for the credential-free QMT acceptance handoff packager."""

import importlib.util
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "package_qmt_acceptance_handoff.py"
SPEC = importlib.util.spec_from_file_location(
    "package_qmt_acceptance_handoff", SCRIPT_PATH
)
HANDOFF = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(HANDOFF)


def read_members(path: Path) -> tuple[list[str], dict[str, bytes]]:
    """Read the ordered regular members from one generated archive."""

    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        assert all(not info.is_dir() for info in infos)
        return [info.filename for info in infos], {
            info.filename: archive.read(info) for info in infos
        }


def test_handoff_archive_is_deterministic_and_exactly_allowlisted(tmp_path):
    first = HANDOFF.package_qmt_acceptance_handoff(tmp_path / "first.zip")
    second = HANDOFF.package_qmt_acceptance_handoff(tmp_path / "second.zip")

    assert first.read_bytes() == second.read_bytes()
    names, members = read_members(first)
    expected = [
        "qmt_acceptance_handoff/RUN_QMT_ACCEPTANCE_EXPORT.ps1",
        "qmt_acceptance_handoff/docs/a_share_qmt_xtquant_one_minute_export_data_contract.json",
        "qmt_acceptance_handoff/qmt_acceptance_handoff.json",
        "qmt_acceptance_handoff/scripts/export_qmt_one_minute.py",
    ]
    assert names == expected
    assert members[expected[1]] == HANDOFF.CONTRACT_PATH.read_bytes()
    assert members[expected[3]] == HANDOFF.EXPORTER_PATH.read_bytes()

    manifest = json.loads(members[expected[2]])
    assert manifest["expected_archive_members"] == expected
    assert manifest["frozen_acceptance"] == {
        "trade_date": "2026-07-13",
        "source_symbols": [
            "600519.SH",
            "000001.SZ",
            "300750.SZ",
            "688981.SH",
        ],
        "period": "1m",
        "dividend_type": "none",
        "fill_data": False,
    }
    assert manifest["privacy"] == {
        "credential_account_cookie_token_client_path_machine_name_or_username_included": False,
        "provider_or_network_request_issued_by_packager": False,
        "qmt_runtime_or_export_rows_read_by_packager": False,
        "price_or_forward_return_fields_read_by_packager": False,
        "raw_qmt_cache_or_client_database_included": False,
    }
    recorded = {entry["path"]: entry["sha256"] for entry in manifest["payload_files"]}
    for path, digest in recorded.items():
        assert HANDOFF.byte_sha256(members[path]) == digest


def test_handoff_archive_has_fixed_zip_metadata(tmp_path):
    archive_path = HANDOFF.package_qmt_acceptance_handoff(tmp_path / "handoff.zip")
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            assert info.date_time == HANDOFF.ZIP_TIMESTAMP
            assert info.compress_type == zipfile.ZIP_STORED
            assert info.create_system == 3
            assert (info.external_attr >> 16) & 0o170000 == 0o100000


def test_extracted_exporter_finds_and_validates_its_bundled_contract(tmp_path):
    archive_path = HANDOFF.package_qmt_acceptance_handoff(tmp_path / "handoff.zip")
    extraction_root = tmp_path / "extracted"
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(extraction_root)
    exporter_path = (
        extraction_root
        / "qmt_acceptance_handoff/scripts/export_qmt_one_minute.py"
    )
    spec = importlib.util.spec_from_file_location(
        "extracted_export_qmt_one_minute", exporter_path
    )
    exporter = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(exporter)

    contract = exporter.load_contract()
    assert contract["formal_acceptance"]["trade_date"] == "2026-07-13"
    assert exporter.CONTRACT_PATH == (
        extraction_root
        / "qmt_acceptance_handoff/docs/"
        "a_share_qmt_xtquant_one_minute_export_data_contract.json"
    )


def test_handoff_launcher_verifies_payload_and_uses_one_fixed_export_command(
    tmp_path,
):
    archive_path = HANDOFF.package_qmt_acceptance_handoff(tmp_path / "handoff.zip")
    _, members = read_members(archive_path)
    launcher = members[
        "qmt_acceptance_handoff/RUN_QMT_ACCEPTANCE_EXPORT.ps1"
    ].decode("utf-8")

    assert launcher.count("Get-FileHash -Algorithm SHA256") == 1
    assert HANDOFF.CONTRACT_SHA256 in launcher
    assert HANDOFF.file_sha256(HANDOFF.EXPORTER_PATH) in launcher
    assert launcher.count("export-acceptance --output") == 1
    assert "download_history_data2" not in launcher
    assert "get_market_data_ex" not in launcher
    assert "TUSHARE_TOKEN" not in launcher


def test_handoff_packager_never_overwrites_an_existing_archive(tmp_path):
    destination = tmp_path / "handoff.zip"
    destination.write_bytes(b"keep-me")

    with pytest.raises(HANDOFF.QmtHandoffError, match="already exists"):
        HANDOFF.package_qmt_acceptance_handoff(destination)

    assert destination.read_bytes() == b"keep-me"


def test_handoff_packager_rejects_contract_fingerprint_drift(tmp_path):
    contract = tmp_path / HANDOFF.CONTRACT_PATH.name
    contract.write_bytes(HANDOFF.CONTRACT_PATH.read_bytes() + b"\n")

    with pytest.raises(HANDOFF.QmtHandoffError, match="fingerprint mismatch"):
        HANDOFF.package_qmt_acceptance_handoff(
            tmp_path / "handoff.zip",
            contract_path=contract,
        )

    assert not (tmp_path / "handoff.zip").exists()


def test_handoff_cli_uses_only_standard_library_and_emits_no_user_path_in_zip(
    tmp_path,
):
    destination = tmp_path / "handoff.zip"
    env = os.environ.copy()
    env["PYTHONPATH"] = ""
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--output", str(destination)],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    output = json.loads(completed.stdout)
    assert output["status"] == (
        "qmt_acceptance_handoff_packaged_without_provider_rows"
    )
    assert output["member_count"] == 4
    assert output["sha256"] == HANDOFF.file_sha256(destination)
    payload = destination.read_bytes()
    assert str(Path.home()).encode("utf-8") not in payload
    assert Path.home().name.encode("utf-8") not in payload
    assert b"TUSHARE_TOKEN" not in payload
    assert b"RQDATA_PASSWORD" not in payload
    assert b"JQDATA_PASSWORD" not in payload
