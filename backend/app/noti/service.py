"""Tạo thông báo cá nhân. Gọi sau khi nghiệp vụ đã lưu; lỗi thông báo không làm hỏng nghiệp vụ."""
import logging
from datetime import UTC, datetime
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import Grant, User
from app.core.db import admin_sessionmaker
from app.noti.models import Noti

log = logging.getLogger("ioc.noti")


async def users_by_name(tid: int, ho_ten: str | None) -> list[int]:
    """Tài khoản của cán bộ theo họ tên (người phụ trách ghi bằng tên trong hồ sơ)."""
    if not ho_ten or not ho_ten.strip():
        return []
    async with admin_sessionmaker()() as a:
        return list((await a.execute(select(User.id).where(User.tenant_id == tid, User.trang_thai == "hoat_dong",
                                                           User.ho_ten.ilike(ho_ten.strip())))).scalars())


async def users_with(tid: int, *, roles: set[str] | None = None, duyet: str | None = None) -> list[int]:
    """Tài khoản theo vai trò, hoặc có quyền xác nhận một nhóm dữ liệu."""
    async with admin_sessionmaker()() as a:
        rows = (await a.execute(select(Grant, User).join(User, User.id == Grant.user_id)
                                .where(Grant.tenant_id == tid, User.trang_thai == "hoat_dong"))).all()
    out = set()
    for g, u in rows:
        if roles and g.role in roles:
            out.add(u.id)
        if duyet and "duyet" in (g.quyen or []) and (g.nhom_du_lieu is None or duyet in g.nhom_du_lieu) and g.role != "quan_tri_don_vi":
            out.add(u.id)
    return sorted(out)


async def notify(s: AsyncSession, tid: int, user_ids: Iterable[int], loai: str, tieu_de: str, noi_dung: str = "", lien_ket: str | None = None,
                 muc_do: str = "thuong", khoa: str | None = None, bo_qua: int | None = None, is_sample: bool = False) -> int:
    """Gửi cho danh sách người (bỏ người gây ra sự kiện). `khoa` gộp: cùng khóa thì cập nhật và đánh dấu chưa đọc lại."""
    ids = sorted({i for i in user_ids if i and i != bo_qua})
    if not ids:
        return 0
    try:
        old = {}
        if khoa:
            old = {n.user_id: n for n in (await s.execute(select(Noti).where(Noti.khoa == khoa, Noti.user_id.in_(ids)))).scalars()}
        now = datetime.now(UTC)
        for uid in ids:
            n = old.get(uid)
            if n is None:
                s.add(Noti(tenant_id=tid, user_id=uid, loai=loai, tieu_de=tieu_de[:300], noi_dung=noi_dung[:2000], lien_ket=lien_ket,
                           muc_do=muc_do, khoa=khoa, is_sample=is_sample))
            else:
                n.tieu_de, n.noi_dung, n.lien_ket, n.muc_do, n.tao_luc, n.da_doc_luc = tieu_de[:300], noi_dung[:2000], lien_ket, muc_do, now, None
        await s.commit()
        return len(ids)
    except Exception:  # noqa: BLE001
        log.exception("Không tạo được thông báo %s", loai)
        await s.rollback()
        return 0


async def mark_read_key(s: AsyncSession, user_id: int, khoa: str) -> None:
    for n in (await s.execute(select(Noti).where(Noti.user_id == user_id, Noti.khoa == khoa, Noti.da_doc_luc.is_(None)))).scalars():
        n.da_doc_luc = datetime.now(UTC)
