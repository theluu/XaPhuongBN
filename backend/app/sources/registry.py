"""Đăng ký connector (lấy dữ liệu) và sink (ghi dữ liệu tổng hợp vào phân hệ).

Connector: async (source, tenant: Tenant, ky: str) -> list[dict]
Sink: (session, tenant_id, records) -> int  (có thể async)
"""
from collections.abc import Awaitable, Callable

CONNECTORS: dict[str, Callable[..., Awaitable[list[dict]]]] = {}
SINKS: dict[str, Callable] = {"noop": lambda s, tenant_id, records: len(records)}

PII_KEYS = {"ho_ten", "ten_cong_dan", "so_dinh_danh", "cccd", "cmnd", "ngay_sinh", "dia_chi", "so_dien_thoai", "sdt", "email"}


def connector(name: str):  # noqa: ANN201
    def deco(fn):  # noqa: ANN001, ANN202
        CONNECTORS[name] = fn
        return fn

    return deco


def sink(name: str):  # noqa: ANN201
    def deco(fn):  # noqa: ANN001, ANN202
        SINKS[name] = fn
        return fn

    return deco
