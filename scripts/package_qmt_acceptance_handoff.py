#!/usr/bin/env python3
"""Build a deterministic, credential-free QMT acceptance handoff ZIP.

The packager is local-only. It reads the frozen exporter and data contract,
adds a hash-checking PowerShell launcher, and never imports XtQuant, reads QMT
rows, or accesses prices and returns. The resulting ZIP is intended to be
unpacked inside an already-lawful Windows MiniQMT/XtQuant Python environment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORTER_PATH = REPO_ROOT / "scripts" / "export_qmt_one_minute.py"
CONTRACT_PATH = (
    REPO_ROOT / "docs" / "a_share_qmt_xtquant_one_minute_export_data_contract.json"
)
CONTRACT_SHA256 = (
    "a5ccb8bb4a7356a2c655d3cfd3ffc72365cc93c19198476110fb793c2fa71399"
)
ARCHIVE_ROOT = "qmt_acceptance_handoff"
HANDOFF_MANIFEST_NAME = "qmt_acceptance_handoff.json"
WINDOWS_LAUNCHER_NAME = "RUN_QMT_ACCEPTANCE_EXPORT.ps1"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


class QmtHandoffError(RuntimeError):
    """A deterministic handoff-package contract violation."""


def byte_sha256(payload: bytes) -> str:
    """Return the SHA-256 digest of in-memory bytes."""

    return hashlib.sha256(payload).hexdigest()


def file_sha256(path: Path) -> str:
    """Return the SHA-256 digest of one local file."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_frozen_inputs(
    *, exporter_path: Path, contract_path: Path
) -> tuple[bytes, bytes, dict[str, Any]]:
    """Read and validate only the two allowlisted repository inputs."""

    exporter = exporter_path.expanduser().resolve()
    contract = contract_path.expanduser().resolve()
    if exporter.name != "export_qmt_one_minute.py" or not exporter.is_file():
        raise QmtHandoffError("frozen QMT exporter is missing or misnamed")
    if (
        contract.name
        != "a_share_qmt_xtquant_one_minute_export_data_contract.json"
        or not contract.is_file()
    ):
        raise QmtHandoffError("frozen QMT export contract is missing or misnamed")
    exporter_bytes = exporter.read_bytes()
    contract_bytes = contract.read_bytes()
    if byte_sha256(contract_bytes) != CONTRACT_SHA256:
        raise QmtHandoffError("QMT export contract fingerprint mismatch")
    try:
        contract_payload = json.loads(contract_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QmtHandoffError("QMT export contract is not canonical UTF-8 JSON") from exc
    exporter_protocol = contract_payload.get("exporter_protocol") or {}
    acceptance = contract_payload.get("formal_acceptance") or {}
    if (
        contract_payload.get("version") != 1
        or contract_payload.get("kind")
        != "a_share_qmt_xtquant_one_minute_export_data_contract"
        or exporter_protocol.get("script_path")
        != "scripts/export_qmt_one_minute.py"
        or exporter_protocol.get("allowed_operation") != "export-acceptance"
        or acceptance.get("trade_date") != "2026-07-13"
        or acceptance.get("source_symbols")
        != ["600519.SH", "000001.SZ", "300750.SZ", "688981.SH"]
        or contract_payload.get("qmt_runtime_or_export_rows_observed_before_freeze")
        is not False
        or contract_payload.get("forward_return_fields_read") is not False
    ):
        raise QmtHandoffError("QMT export contract changed after freeze")
    return exporter_bytes, contract_bytes, contract_payload


def _windows_launcher(exporter_sha256: str) -> bytes:
    """Return a path-independent PowerShell launcher with payload hash checks."""

    script = f'''param(
    [string]$Python = "python",
    [string]$Output = (Join-Path $PSScriptRoot "qmt-1m-acceptance-20260713")
)

$ErrorActionPreference = "Stop"

function Assert-Sha256 {{
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Expected
    )
    $Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
    if ($Actual -ne $Expected) {{
        throw "Handoff payload fingerprint mismatch: $Path"
    }}
}}

$Exporter = Join-Path $PSScriptRoot "scripts\\export_qmt_one_minute.py"
$Contract = Join-Path $PSScriptRoot "docs\\a_share_qmt_xtquant_one_minute_export_data_contract.json"
Assert-Sha256 -Path $Exporter -Expected "{exporter_sha256}"
Assert-Sha256 -Path $Contract -Expected "{CONTRACT_SHA256}"

& $Python $Exporter export-acceptance --output $Output
if ($LASTEXITCODE -ne 0) {{
    exit $LASTEXITCODE
}}
'''
    return script.encode("utf-8")


def _handoff_manifest(
    *,
    exporter_sha256: str,
    launcher_sha256: str,
    contract: dict[str, Any],
) -> bytes:
    """Return the canonical manifest for the non-data handoff archive."""

    acceptance = contract["formal_acceptance"]
    payload_paths = [
        f"{ARCHIVE_ROOT}/{WINDOWS_LAUNCHER_NAME}",
        f"{ARCHIVE_ROOT}/docs/{CONTRACT_PATH.name}",
        f"{ARCHIVE_ROOT}/scripts/{EXPORTER_PATH.name}",
    ]
    manifest_path = f"{ARCHIVE_ROOT}/{HANDOFF_MANIFEST_NAME}"
    payload = {
        "version": 1,
        "kind": "a_share_qmt_xtquant_one_minute_acceptance_handoff",
        "status": "ready_for_lawful_windows_qmt_runtime_without_provider_rows",
        "purpose": (
            "Transfer the exact frozen four-symbol QMT acceptance exporter and "
            "contract to an already-lawful Windows runtime without cloning the "
            "whole research repository."
        ),
        "archive_root": ARCHIVE_ROOT,
        "expected_archive_members": sorted(payload_paths + [manifest_path]),
        "payload_files": [
            {
                "path": f"{ARCHIVE_ROOT}/{WINDOWS_LAUNCHER_NAME}",
                "sha256": launcher_sha256,
                "role": "hash_checking_windows_launcher",
            },
            {
                "path": f"{ARCHIVE_ROOT}/docs/{CONTRACT_PATH.name}",
                "sha256": CONTRACT_SHA256,
                "role": "frozen_data_contract",
            },
            {
                "path": f"{ARCHIVE_ROOT}/scripts/{EXPORTER_PATH.name}",
                "sha256": exporter_sha256,
                "role": "frozen_exporter",
            },
        ],
        "windows_run": {
            "working_directory": ARCHIVE_ROOT,
            "command": (
                "powershell -ExecutionPolicy Bypass -File "
                f".\\{WINDOWS_LAUNCHER_NAME}"
            ),
            "default_output_directory": "qmt-1m-acceptance-20260713",
            "custom_python_parameter": "-Python <lawful-qmt-python-command>",
            "custom_output_parameter": "-Output <new-directory>",
        },
        "frozen_acceptance": {
            "trade_date": acceptance["trade_date"],
            "source_symbols": acceptance["source_symbols"],
            "period": contract["exporter_protocol"]["period"],
            "dividend_type": contract["exporter_protocol"]["dividend_type"],
            "fill_data": contract["exporter_protocol"]["fill_data"],
        },
        "privacy": {
            "credential_account_cookie_token_client_path_machine_name_or_username_included": False,
            "provider_or_network_request_issued_by_packager": False,
            "qmt_runtime_or_export_rows_read_by_packager": False,
            "price_or_forward_return_fields_read_by_packager": False,
            "raw_qmt_cache_or_client_database_included": False,
        },
        "selection_or_promotion_allowed": False,
    }
    return (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _zip_info(path: str) -> zipfile.ZipInfo:
    """Return fixed metadata for one deterministic regular-file ZIP member."""

    info = zipfile.ZipInfo(path, date_time=ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = (0o100644 & 0xFFFF) << 16
    return info


def package_qmt_acceptance_handoff(
    output_path: Path,
    *,
    exporter_path: Path = EXPORTER_PATH,
    contract_path: Path = CONTRACT_PATH,
) -> Path:
    """Create one deterministic handoff ZIP without overwriting a destination."""

    destination = output_path.expanduser().resolve()
    if destination.suffix.lower() != ".zip":
        raise QmtHandoffError("QMT handoff destination must end with .zip")
    if destination.exists():
        raise QmtHandoffError(f"QMT handoff destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    exporter_bytes, contract_bytes, contract = _read_frozen_inputs(
        exporter_path=exporter_path,
        contract_path=contract_path,
    )
    exporter_digest = byte_sha256(exporter_bytes)
    launcher_bytes = _windows_launcher(exporter_digest)
    files = {
        f"{ARCHIVE_ROOT}/{WINDOWS_LAUNCHER_NAME}": launcher_bytes,
        f"{ARCHIVE_ROOT}/docs/{CONTRACT_PATH.name}": contract_bytes,
        f"{ARCHIVE_ROOT}/scripts/{EXPORTER_PATH.name}": exporter_bytes,
    }
    files[f"{ARCHIVE_ROOT}/{HANDOFF_MANIFEST_NAME}"] = _handoff_manifest(
        exporter_sha256=exporter_digest,
        launcher_sha256=byte_sha256(launcher_bytes),
        contract=contract,
    )

    with tempfile.NamedTemporaryFile(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".partial",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
    try:
        with zipfile.ZipFile(temporary, mode="w") as archive:
            for path in sorted(files):
                archive.writestr(_zip_info(path), files[path])
        try:
            os.link(temporary, destination)
        except FileExistsError as exc:
            raise QmtHandoffError(
                f"QMT handoff destination already exists: {destination}"
            ) from exc
        return destination
    finally:
        temporary.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    """Build the fixed local-only packaging CLI."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="new .zip path; an existing destination is never overwritten",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Build one archive and print only its path, digest, and member count."""

    args = build_parser().parse_args(argv)
    try:
        archive = package_qmt_acceptance_handoff(args.output)
    except QmtHandoffError as exc:
        print(f"error: {exc}")
        return 2
    print(
        json.dumps(
            {
                "archive": str(archive),
                "sha256": file_sha256(archive),
                "member_count": 4,
                "status": "qmt_acceptance_handoff_packaged_without_provider_rows",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
