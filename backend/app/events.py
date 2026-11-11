"""Sự kiện nội bộ đơn giản (VD: số liệu được xác nhận → chạy lại quy tắc cảnh báo)."""
import inspect
from collections import defaultdict
from collections.abc import Callable

_handlers: dict[str, list[Callable]] = defaultdict(list)


def on(name: str):  # noqa: ANN201
    def deco(fn):  # noqa: ANN001, ANN202
        _handlers[name].append(fn)
        return fn

    return deco


async def emit(name: str, **kw) -> None:  # noqa: ANN003
    for h in _handlers[name]:
        r = h(**kw)
        if inspect.isawaitable(r):
            await r
