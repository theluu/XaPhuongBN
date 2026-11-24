from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, tenant_db
from app.core.principal import CurrentUser
from app.files import storage
from app.files.models import StoredFile

router = APIRouter(prefix="/api/files", tags=["tep"])


@router.post("", status_code=201)
async def upload(file: UploadFile = File(...), s: AsyncSession = Depends(tenant_db),
                 user: CurrentUser = Depends(get_current_user)) -> dict:
    if not any("nhap" in q for q in user.permissions.values()):
        raise HTTPException(403, "Bạn không có quyền tải tệp lên")
    content = await file.read(storage.MAX_BYTES + 1)
    if len(content) > storage.MAX_BYTES:
        raise HTTPException(422, "Tệp vượt quá 10 MB")
    ctype = storage.sniff(content)
    if ctype is None:
        raise HTTPException(422, "Định dạng tệp không được chấp nhận (chỉ ảnh JPG/PNG/WEBP, PDF, Excel, Word)")
    tid = s.info["tenant_id"]
    key = storage.save(tid, content, ctype)
    s.add(StoredFile(tenant_id=tid, key=key, ten_goc=(file.filename or "tep")[:300], content_type=ctype,
                     kich_thuoc=len(content), nguoi_tai_len_id=user.id))
    await s.commit()
    return {"key": key, "content_type": ctype, "ten_goc": file.filename}


@router.get("/{key}")
async def download(key: str, s: AsyncSession = Depends(tenant_db), user: CurrentUser = Depends(get_current_user)) -> Response:
    from app.tin_nhan.router import may_read_file

    f = (await s.execute(select(StoredFile).where(StoredFile.key == key))).scalar()
    if f is None or not await may_read_file(s, key, user):
        raise HTTPException(404, "Không tìm thấy tệp")
    return Response(storage.load(f.tenant_id, f.key, f.content_type), media_type=f.content_type,
                    headers={"Content-Disposition": "inline", "X-Content-Type-Options": "nosniff", "Cache-Control": "private"})


async def keys_exist(s: AsyncSession, keys: list[str]) -> bool:
    if not keys:
        return True
    found = set((await s.execute(select(StoredFile.key).where(StoredFile.key.in_(keys)))).scalars())
    return found == set(keys)
