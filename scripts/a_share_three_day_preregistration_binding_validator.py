#!/usr/bin/env python3
"""Fail closed on stale or mistyped preregistration file fingerprints."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")


class BindingValidationError(RuntimeError):
    """Raised when a record cannot be inspected safely."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_path(value: str, *, data_root: Path | None = None) -> Path:
    path = Path(value).expanduser()
    if data_root is not None:
        return (data_root / path).resolve()
    if path.is_absolute():
        return path.resolve()
    return (REPO_ROOT / path).resolve()


def _binding_candidates(
    value: Any,
    *,
    pointer: str = "",
    data_root: Path,
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if isinstance(value.get("path"), str) and isinstance(
            value.get("sha256"), str
        ):
            found.append(
                {
                    "json_pointer": pointer or "/",
                    "path": _resolve_path(value["path"]),
                    "expected_sha256": value["sha256"],
                    "binding_form": "path_sha256",
                }
            )
        if isinstance(value.get("path_below_data_root"), str) and isinstance(
            value.get("sha256"), str
        ):
            found.append(
                {
                    "json_pointer": pointer or "/",
                    "path": _resolve_path(
                        value["path_below_data_root"], data_root=data_root
                    ),
                    "expected_sha256": value["sha256"],
                    "binding_form": "path_below_data_root_sha256",
                }
            )
        if isinstance(value.get("manifest_path"), str) and isinstance(
            value.get("manifest_sha256"), str
        ):
            found.append(
                {
                    "json_pointer": pointer or "/",
                    "path": _resolve_path(value["manifest_path"]),
                    "expected_sha256": value["manifest_sha256"],
                    "binding_form": "manifest_path_manifest_sha256",
                }
            )
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            found.extend(
                _binding_candidates(
                    child,
                    pointer=f"{pointer}/{escaped}",
                    data_root=data_root,
                )
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(
                _binding_candidates(
                    child,
                    pointer=f"{pointer}/{index}",
                    data_root=data_root,
                )
            )
    return found


def validate_record(
    record_path: Path,
    *,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> dict[str, Any]:
    """Validate every recognized existing-file binding in one JSON record."""

    record_path = record_path.expanduser().resolve()
    data_root = data_root.expanduser().resolve()
    if not record_path.is_file():
        raise BindingValidationError(f"record is not a file: {record_path}")
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BindingValidationError(f"invalid JSON record: {record_path}") from exc
    candidates = _binding_candidates(record, data_root=data_root)
    if not candidates:
        raise BindingValidationError(
            f"record has no recognized file fingerprint bindings: {record_path}"
        )
    results: list[dict[str, Any]] = []
    for candidate in candidates:
        path = Path(candidate["path"])
        expected = str(candidate["expected_sha256"])
        exists = path.is_file()
        observed = sha256(path) if exists else None
        results.append(
            {
                "json_pointer": candidate["json_pointer"],
                "binding_form": candidate["binding_form"],
                "path": str(path),
                "expected_sha256": expected,
                "observed_sha256": observed,
                "exists": exists,
                "passed": exists and observed == expected,
            }
        )
    failed = [item for item in results if not item["passed"]]
    return {
        "version": 1,
        "kind": "a_share_three_day_preregistration_binding_validation",
        "record_path": str(record_path),
        "record_sha256": sha256(record_path),
        "data_root": str(data_root),
        "binding_count": len(results),
        "passed_binding_count": len(results) - len(failed),
        "failed_binding_count": len(failed),
        "all_bindings_passed": not failed,
        "failed_bindings": failed,
        "results": results,
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("records", nargs="+", type=Path)
    value.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    reports: list[dict[str, Any]] = []
    try:
        for record in args.records:
            reports.append(validate_record(record, data_root=args.data_root))
    except BindingValidationError as exc:
        print(
            json.dumps(
                {
                    "status": "binding_validation_error",
                    "error": str(exc),
                    "all_bindings_passed": False,
                },
                sort_keys=True,
            )
        )
        return 2
    passed = all(item["all_bindings_passed"] for item in reports)
    print(
        json.dumps(
            {
                "status": (
                    "all_preregistration_bindings_valid"
                    if passed
                    else "preregistration_binding_mismatch"
                ),
                "all_bindings_passed": passed,
                "reports": reports,
            },
            sort_keys=True,
        )
    )
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
