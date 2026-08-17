import hashlib
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "a_share_official_exchange_enforcement.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "a_share_official_exchange_enforcement", MODULE_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_schema_role_resolution_is_exact_finite_and_nfkc_only() -> None:
    module = load_module()
    resolved = module.resolve_schema_roles(
        [" 证券代码 ", "监管类型", "发布日期", "标题", "公司简称"]
    )
    assert resolved == {
        "issuer_code": "证券代码",
        "action_type_or_family": "监管类型",
        "action_date": "发布日期",
        "document_link": "标题",
    }
    with pytest.raises(module.EnforcementContractError):
        module.resolve_schema_roles(
            ["证券代码", "监管类型", "发布日期", "标题", "日期"]
        )
    with pytest.raises(module.EnforcementContractError):
        module.resolve_schema_roles(
            ["证券代码", "公司代码", "监管类型", "发布日期", "标题"]
        )
    with pytest.raises(module.EnforcementContractError):
        module.resolve_schema_roles(["证券代码", "监管类型", "发布日期", "标题名称"])


def test_sse_rows_are_privacy_minimized_mapped_and_deduplicated() -> None:
    module = load_module()
    labels = ["证券代码", "监管类型", "处理日期", "处理事由", "涉及对象"]
    row = {
        "证券代码": "600519",
        "监管类型": "监管警示",
        "处理日期": "2025-01-03",
        "处理事由": "/regulation/doc/A%2Fb.PDF?X=Case",
        "涉及对象": "ignored personal and free text",
    }
    rows, stats = module.canonicalize_listing_rows("sse", labels, [row, dict(row)])
    resolved = "https://www.sse.com.cn/regulation/doc/A%2Fb.PDF?X=Case"
    assert rows == [
        {
            "action_date": "2025-01-03",
            "instrument": "SH600519",
            "exchange": "SSE",
            "action_family": "regulatory_measure",
            "action_type_token": "监管警示",
            "document_href_sha256": hashlib.sha256(resolved.encode()).hexdigest(),
            "provider": "official_exchange",
        }
    ]
    assert stats["exact_repeated_event_keys_collapsed"] == 1
    assert stats["free_text_read_into_factor_logic_or_persisted"] is False
    assert stats["network_or_document_fetch_performed"] is False
    assert "涉及对象" not in rows[0]


def test_szse_page_family_is_exact_and_unsupported_complete_code_is_counted() -> None:
    module = load_module()
    labels = ["公司代码", "纪律处分", "发文日期", "决定书"]
    rows, stats = module.canonicalize_listing_rows(
        "szse_disciplinary_action",
        labels,
        [
            {
                "公司代码": "300750",
                "纪律处分": "纪律处分",
                "发文日期": "2024-12-31",
                "决定书": "//www.szse.cn/path/Case.PDF?q=%2F",
            },
            {
                "公司代码": "200001",
                "纪律处分": "纪律处分",
                "发文日期": "2024-12-31",
                "决定书": "/ignored-b-share.pdf",
            },
        ],
    )
    assert len(rows) == 1
    assert rows[0]["instrument"] == "SZ300750"
    assert rows[0]["action_family"] == "disciplinary_action"
    assert stats["unsupported_complete_codes_excluded"] == 1
    with pytest.raises(module.EnforcementContractError):
        module.canonicalize_listing_rows(
            "szse_disciplinary_action",
            labels,
            [
                {
                    "公司代码": "300750",
                    "纪律处分": "监管措施",
                    "发文日期": "2024-12-31",
                    "决定书": "/conflict.pdf",
                }
            ],
        )


@pytest.mark.parametrize(
    ("page_id", "labels", "row"),
    [
        (
            "sse",
            ["证券代码", "监管类型", "处理日期", "标题"],
            {
                "证券代码": "000001",
                "监管类型": "监管警示",
                "处理日期": "2025-01-03",
                "标题": "/wrong-exchange.pdf",
            },
        ),
        (
            "sse",
            ["证券代码", "监管类型", "处理日期", "标题"],
            {
                "证券代码": "600519",
                "监管类型": "监管警示",
                "处理日期": "20250103",
                "标题": "/bad-date.pdf",
            },
        ),
        (
            "sse",
            ["证券代码", "监管类型", "处理日期", "标题"],
            {
                "证券代码": "600519",
                "监管类型": "监管警示",
                "处理日期": "2025-01-03",
                "标题": "https://example.com/offsite.pdf",
            },
        ),
    ],
)
def test_malformed_cross_exchange_and_official_host_violations_fail_closed(
    page_id, labels, row
) -> None:
    module = load_module()
    with pytest.raises(module.EnforcementContractError):
        module.canonicalize_listing_rows(page_id, labels, [row])


def test_document_state_and_action_token_conflicts_fail_closed() -> None:
    module = load_module()
    labels = ["证券代码", "监管类型", "处理日期", "标题"]
    base = {
        "证券代码": "600519",
        "监管类型": "监管警示",
        "处理日期": "2025-01-03",
        "标题": "/same-document.pdf",
    }
    conflicting_date = dict(base, 处理日期="2025-01-04")
    with pytest.raises(module.EnforcementContractError):
        module.canonicalize_listing_rows("sse", labels, [base, conflicting_date])
    conflicting_token = dict(base, 监管类型="监管工作函")
    with pytest.raises(module.EnforcementContractError):
        module.canonicalize_listing_rows("sse", labels, [base, conflicting_token])


def test_adapter_has_no_transport_or_cli_entrypoint() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    forbidden = ("requests", "urllib.request", "httpx", "tushare", "__main__")
    assert all(token not in source for token in forbidden)
