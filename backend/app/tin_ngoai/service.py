"""Lấy tin từ nguồn RSS/Atom do đơn vị cấu hình (Cổng TTĐT phường/thành phố…) để chạy trên dải bản tin.

An toàn: chỉ https; chặn địa chỉ mạng nội bộ/loopback (chống SSRF) ở mọi bước chuyển hướng; giới hạn dung lượng, thời gian;
không nhận DOCTYPE/ENTITY; chỉ giữ liên kết http(s). Không đọc trang HTML: nguồn không có RSS/Atom thì báo lỗi, không cào trang."""
import asyncio
import ipaddress
import logging
import socket
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy import delete, select

from app.core.db import admin_sessionmaker, tenant_session
from app.platform.models import Tenant
from app.tin_ngoai.models import TinNgoai

log = logging.getLogger("ioc.tin_ngoai")
MAX_BYTES = 2_000_000
TIMEOUT = 10.0
GIU_TOI_DA = 50
UA = "IOC-XP feed reader (doc nguon tin cong khai)"


class FeedError(Exception):
    pass


def check_url(url: str) -> str:
    u = urlparse(url.strip())
    if u.scheme != "https" or not u.hostname:
        raise FeedError("Địa chỉ nguồn tin phải bắt đầu bằng https://")
    if len(url) > 500:
        raise FeedError("Địa chỉ quá dài")
    return url.strip()


async def _public_host(host: str) -> None:
    try:
        infos = await asyncio.get_running_loop().run_in_executor(None, socket.getaddrinfo, host, 443)
    except socket.gaierror as e:
        raise FeedError("Không phân giải được tên miền nguồn tin") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise FeedError("Nguồn tin trỏ tới địa chỉ mạng nội bộ — không được phép")


async def fetch(url: str, client: httpx.AsyncClient | None = None) -> bytes:
    url = check_url(url)
    own = client is None
    client = client or httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"})
    try:
        for _ in range(4):
            await _public_host(urlparse(url).hostname or "")
            async with client.stream("GET", url) as r:
                if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
                    url = check_url(urljoin(url, r.headers["location"]))
                    continue
                if r.status_code != 200:
                    raise FeedError(f"Nguồn tin trả về mã {r.status_code}")
                buf = bytearray()
                async for chunk in r.aiter_bytes():
                    buf += chunk
                    if len(buf) > MAX_BYTES:
                        raise FeedError("Nguồn tin quá lớn")
                return bytes(buf)
        raise FeedError("Chuyển hướng quá nhiều lần")
    except httpx.HTTPError as e:
        raise FeedError("Không kết nối được nguồn tin") from e
    finally:
        if own:
            await client.aclose()


def _text(el: ET.Element | None) -> str:
    return " ".join((el.text or "").split()) if el is not None else ""


def _date(s: str) -> datetime | None:
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def parse(data: bytes) -> list[dict]:
    head = data[:4096].lower()
    if b"<!doctype" in head or b"<!entity" in data.lower():
        raise FeedError("Nội dung không phải nguồn tin RSS/Atom (có thể là trang web hoặc trang chặn truy cập)")
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        raise FeedError("Nội dung không phải RSS/Atom hợp lệ") from e
    tag = root.tag.split("}")[-1].lower()
    out = []
    if tag in ("rss", "rdf"):
        for it in root.iter():
            if it.tag.split("}")[-1] != "item":
                continue
            kids = {c.tag.split("}")[-1]: c for c in it}
            link = _text(kids.get("link"))
            out.append({"tieu_de": _text(kids.get("title")), "lien_ket": link, "guid": _text(kids.get("guid")) or link,
                        "ngay_dang": _date(_text(kids.get("pubDate")) or _text(kids.get("date")))})
    elif tag == "feed":
        for it in root:
            if it.tag.split("}")[-1] != "entry":
                continue
            kids: dict[str, ET.Element] = {}
            link = ""
            for c in it:
                n = c.tag.split("}")[-1]
                kids.setdefault(n, c)
                if n == "link" and c.get("rel", "alternate") == "alternate" and not link:
                    link = c.get("href", "")
            out.append({"tieu_de": _text(kids.get("title")), "lien_ket": link, "guid": _text(kids.get("id")) or link,
                        "ngay_dang": _date(_text(kids.get("published")) or _text(kids.get("updated")))})
    else:
        raise FeedError("Nội dung không phải RSS/Atom")
    return [x for x in out if x["tieu_de"] and urlparse(x["lien_ket"]).scheme in ("http", "https")][:GIU_TOI_DA]


async def refresh_tenant(tid: int, client: httpx.AsyncClient | None = None) -> dict:
    """Lấy tin mọi nguồn của đơn vị; ghi trạng thái từng nguồn vào cấu hình đơn vị."""
    async with admin_sessionmaker()() as a:
        t = await a.get(Tenant, tid)
        nguon = list((t.config or {}).get("nguon_tin") or [])
    status: dict[str, dict] = {}
    for src in nguon:
        url, ten = src.get("url", ""), src.get("ten", "Nguồn tin")
        try:
            items = parse(await fetch(url, client))
            async with tenant_session([tid]) as s:
                have = set((await s.execute(select(TinNgoai.guid).where(TinNgoai.tenant_id == tid))).scalars())
                for x in items:
                    g = x["guid"][:500]
                    if g in have:
                        continue
                    have.add(g)
                    s.add(TinNgoai(tenant_id=tid, nguon=url, ten_nguon=ten[:200], guid=g, tieu_de=x["tieu_de"][:500], lien_ket=x["lien_ket"][:500],
                                   ngay_dang=x["ngay_dang"]))
                await s.flush()
                keep = select(TinNgoai.id).where(TinNgoai.tenant_id == tid, TinNgoai.nguon == url).order_by(
                    TinNgoai.ngay_dang.desc().nullslast(), TinNgoai.id.desc()).limit(GIU_TOI_DA)
                await s.execute(delete(TinNgoai).where(TinNgoai.tenant_id == tid, TinNgoai.nguon == url, TinNgoai.id.not_in(keep)))
                await s.commit()
            status[url] = {"ok": True, "luc": datetime.now(UTC).isoformat(), "so_tin": len(items), "loi": ""}
        except FeedError as e:
            status[url] = {"ok": False, "luc": datetime.now(UTC).isoformat(), "so_tin": 0, "loi": str(e)}
        except Exception:  # noqa: BLE001
            log.exception("Lỗi lấy nguồn tin %s của đơn vị %s", url, tid)
            status[url] = {"ok": False, "luc": datetime.now(UTC).isoformat(), "so_tin": 0, "loi": "Lỗi không xác định khi đọc nguồn tin"}
    async with admin_sessionmaker()() as a:
        t = await a.get(Tenant, tid)
        t.config = {**(t.config or {}), "nguon_tin_trang_thai": status}
        await a.commit()
    return status


async def refresh_all() -> None:
    async with admin_sessionmaker()() as a:
        rows = list((await a.execute(select(Tenant).where(Tenant.cap.in_(["xa", "phuong"]), Tenant.trang_thai == "hoat_dong"))).scalars())
        ids = [t.id for t in rows if (t.config or {}).get("nguon_tin")]
    for tid in ids:
        await refresh_tenant(tid)
