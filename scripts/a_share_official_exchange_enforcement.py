"""Pure, zero-network adapter for official exchange enforcement listings.

The adapter intentionally has no transport implementation.  It resolves only the
finite metadata labels and canonicalizes already-supplied rows under Campaign113's
frozen source contract.  Production source access stays blocked until a later,
separately fingerprinted workflow is frozen.
"""

from __future__ import annotations

import hashlib
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_official_exchange_enforcement_source_contract_20260809.json"
)
CONTRACT_SHA256 = "d4eda5eb2fefd7e2795251bd4926fc7e7157ea264fcabc430904c40d5dfd91e4"

ROLE_LABELS = {
    "issuer_code": frozenset(("证券代码", "公司代码")),
    "action_type_or_family": frozenset(
        ("监管类型", "措施类型", "处分类型", "监管措施", "纪律处分")
    ),
    "action_date": frozenset(("处理日期", "发文日期", "发布日期")),
    "document_link": frozenset(("处理事由", "文件名称", "决定书", "监管函件", "标题")),
}
IGNORED_LABELS = frozenset(("证券简称", "公司简称", "涉及对象"))
REQUIRED_ROLES = tuple(ROLE_LABELS)

SSE_ACTION_FAMILIES = {
    "监管警示": "regulatory_measure",
    "监管工作函": "regulatory_measure",
    "通报批评": "disciplinary_action",
    "公开谴责": "disciplinary_action",
    "公开认定": "disciplinary_action",
}
SZSE_ACTION_FAMILIES = {
    "监管措施": "regulatory_measure",
    "纪律处分": "disciplinary_action",
}

LISTING_PAGE_METADATA = {
    "sse": {
        "exchange": "SSE",
        "listing_page": "https://www.sse.com.cn/regulation/supervision/measures/",
        "page_action_family": None,
    },
    "szse_regulatory_measure": {
        "exchange": "SZSE",
        "listing_page": (
            "https://www.szse.cn/disclosure/supervision/measure/measure/index.html"
        ),
        "page_action_family": "监管措施",
    },
    "szse_disciplinary_action": {
        "exchange": "SZSE",
        "listing_page": (
            "https://www.szse.cn/disclosure/supervision/measure/pushish/index.html"
        ),
        "page_action_family": "纪律处分",
    },
}

NORMALIZED_COLUMNS = (
    "action_date",
    "instrument",
    "exchange",
    "action_family",
    "action_type_token",
    "document_href_sha256",
    "provider",
)
EVENT_KEY_COLUMNS = (
    "exchange",
    "instrument",
    "action_date",
    "action_family",
    "document_href_sha256",
)

SSE_MAIN_PREFIXES = ("600", "601", "603", "605")
SSE_EXCHANGE_PREFIXES = SSE_MAIN_PREFIXES + (
    "500",
    "501",
    "502",
    "503",
    "505",
    "506",
    "508",
    "510",
    "511",
    "512",
    "513",
    "515",
    "516",
    "517",
    "518",
    "519",
    "560",
    "561",
    "562",
    "563",
    "588",
    "600",
    "601",
    "603",
    "605",
    "688",
    "689",
    "900",
)
SZSE_MAIN_CHINEXT_PREFIXES = ("000", "001", "002", "003", "300", "301")
SZSE_EXCHANGE_PREFIXES = SZSE_MAIN_CHINEXT_PREFIXES + (
    "101",
    "102",
    "103",
    "104",
    "105",
    "106",
    "107",
    "108",
    "109",
    "111",
    "112",
    "113",
    "114",
    "115",
    "116",
    "117",
    "118",
    "119",
    "123",
    "127",
    "128",
    "131",
    "159",
    "160",
    "161",
    "162",
    "163",
    "164",
    "165",
    "166",
    "167",
    "168",
    "169",
    "180",
    "200",
)


class EnforcementContractError(ValueError):
    """Raised when metadata or rows violate the frozen Campaign113 contract."""


def file_sha256(path: Path) -> str:
    """Return a lowercase SHA-256 hex digest without interpreting file contents."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_frozen_contract() -> None:
    """Fail closed if the bound source contract is absent or changed."""

    if not CONTRACT_PATH.is_file() or file_sha256(CONTRACT_PATH) != CONTRACT_SHA256:
        raise EnforcementContractError(
            "Campaign113 source contract fingerprint changed"
        )


def normalize_metadata_label(value: Any) -> str:
    """Apply only the contract-permitted NFKC and surrounding trim to a label."""

    if not isinstance(value, str):
        raise EnforcementContractError("schema label must be a string")
    normalized = unicodedata.normalize("NFKC", value).strip()
    if not normalized:
        raise EnforcementContractError("schema label must be complete")
    return normalized


def resolve_schema_roles(labels: Sequence[Any]) -> dict[str, str]:
    """Resolve exactly one physical label for every frozen semantic role."""

    assert_frozen_contract()
    if isinstance(labels, (str, bytes)):
        raise EnforcementContractError("schema labels must be an ordered sequence")
    normalized = [normalize_metadata_label(label) for label in labels]
    if len(normalized) != len(set(normalized)):
        raise EnforcementContractError("duplicate normalized schema label")

    resolved: dict[str, str] = {}
    known = set(IGNORED_LABELS)
    for role, allowed in ROLE_LABELS.items():
        known.update(allowed)
        matches = [label for label in normalized if label in allowed]
        if len(matches) != 1:
            raise EnforcementContractError(
                f"role {role} must resolve from exactly one frozen label"
            )
        resolved[role] = matches[0]
    unknown = sorted(set(normalized).difference(known))
    if unknown:
        raise EnforcementContractError("unknown schema label")
    return resolved


def _normalize_scalar(value: Any, role: str) -> str:
    if not isinstance(value, str):
        raise EnforcementContractError(f"{role} must be a string")
    normalized = unicodedata.normalize("NFKC", value).strip()
    if not normalized:
        raise EnforcementContractError(f"{role} must be complete")
    return normalized


def _canonical_instrument(exchange: str, value: Any) -> str | None:
    code = _normalize_scalar(value, "issuer_code")
    if len(code) != 6 or not code.isascii() or not code.isdecimal():
        raise EnforcementContractError("issuer_code must be exactly six ASCII digits")
    prefix = code[:3]
    if exchange == "SSE":
        if prefix in SSE_MAIN_PREFIXES:
            return f"SH{code}"
        if prefix in SZSE_EXCHANGE_PREFIXES:
            raise EnforcementContractError("issuer_code conflicts with SSE")
        return None
    if exchange == "SZSE":
        if prefix in SZSE_MAIN_CHINEXT_PREFIXES:
            return f"SZ{code}"
        if prefix in SSE_EXCHANGE_PREFIXES:
            raise EnforcementContractError("issuer_code conflicts with SZSE")
        return None
    raise EnforcementContractError("exchange is not frozen")


def _strict_iso_date(value: Any) -> str:
    text = _normalize_scalar(value, "action_date")
    if len(text) != 10:
        raise EnforcementContractError("action_date must be strict YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise EnforcementContractError(
            "action_date must be a valid strict ISO calendar date"
        ) from exc
    if parsed.isoformat() != text:
        raise EnforcementContractError("action_date must be strict YYYY-MM-DD")
    return text


def _action_family(
    exchange: str, value: Any, page_action_family: str | None
) -> tuple[str, str]:
    token = _normalize_scalar(value, "action_type_or_family")
    if exchange == "SSE":
        if page_action_family is not None or token not in SSE_ACTION_FAMILIES:
            raise EnforcementContractError("SSE action label is not frozen")
        return SSE_ACTION_FAMILIES[token], token
    if exchange == "SZSE":
        if page_action_family not in SZSE_ACTION_FAMILIES:
            raise EnforcementContractError("SZSE page family is not frozen")
        if token != page_action_family:
            raise EnforcementContractError(
                "SZSE row family conflicts with listing page"
            )
        return SZSE_ACTION_FAMILIES[token], token
    raise EnforcementContractError("exchange is not frozen")


def _official_href_sha256(listing_page: str, value: Any) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise EnforcementContractError("document href must be a complete exact string")
    resolved = urljoin(listing_page, value)
    listing = urlparse(listing_page)
    parsed = urlparse(resolved)
    if (
        parsed.scheme != "https"
        or parsed.hostname != listing.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise EnforcementContractError(
            "document href is not on the frozen official host"
        )
    return hashlib.sha256(resolved.encode("utf-8")).hexdigest()


def canonicalize_listing_rows(
    page_id: str,
    labels: Sequence[Any],
    rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int | bool]]:
    """Canonicalize supplied rows without transport, source persistence, or text use."""

    assert_frozen_contract()
    if page_id not in LISTING_PAGE_METADATA:
        raise EnforcementContractError("listing page identifier is not frozen")
    if isinstance(rows, (str, bytes)):
        raise EnforcementContractError("rows must be a sequence of mappings")
    metadata = LISTING_PAGE_METADATA[page_id]
    exchange = str(metadata["exchange"])
    listing_page = str(metadata["listing_page"])
    page_action_family = metadata["page_action_family"]
    roles = resolve_schema_roles(labels)

    normalized_by_key: dict[tuple[str, ...], dict[str, Any]] = {}
    identity_by_document: dict[tuple[str, str, str], tuple[str, str]] = {}
    excluded = 0
    repeated = 0
    for row in rows:
        if not isinstance(row, Mapping):
            raise EnforcementContractError("source row must be a mapping")
        missing_labels = [label for label in labels if label not in row]
        if missing_labels:
            raise EnforcementContractError("source row is missing a declared label")
        instrument = _canonical_instrument(exchange, row[roles["issuer_code"]])
        if instrument is None:
            excluded += 1
            continue
        action_date = _strict_iso_date(row[roles["action_date"]])
        action_family, action_type_token = _action_family(
            exchange,
            row[roles["action_type_or_family"]],
            page_action_family if isinstance(page_action_family, str) else None,
        )
        href_sha256 = _official_href_sha256(listing_page, row[roles["document_link"]])
        event = {
            "action_date": action_date,
            "instrument": instrument,
            "exchange": exchange,
            "action_family": action_family,
            "action_type_token": action_type_token,
            "document_href_sha256": href_sha256,
            "provider": "official_exchange",
        }
        key = tuple(str(event[column]) for column in EVENT_KEY_COLUMNS)
        document_identity = (exchange, instrument, href_sha256)
        event_state = (action_date, action_family)
        if (
            document_identity in identity_by_document
            and identity_by_document[document_identity] != event_state
        ):
            raise EnforcementContractError(
                "document identity has conflicting event state"
            )
        identity_by_document[document_identity] = event_state
        if key in normalized_by_key:
            if normalized_by_key[key] != event:
                raise EnforcementContractError(
                    "normalized event key has conflicting token"
                )
            repeated += 1
            continue
        normalized_by_key[key] = event

    normalized = sorted(
        normalized_by_key.values(),
        key=lambda event: tuple(str(event[column]) for column in EVENT_KEY_COLUMNS),
    )
    return normalized, {
        "input_source_rows": len(rows),
        "normalized_supported_events": len(normalized),
        "unsupported_complete_codes_excluded": excluded,
        "exact_repeated_event_keys_collapsed": repeated,
        "free_text_read_into_factor_logic_or_persisted": False,
        "network_or_document_fetch_performed": False,
    }
