import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.core.db import admin_sessionmaker, tenant_session
from app.core.principal import CurrentUser
from app.core.tenancy import descendant_ids, tenant_scope
from app.platform.models import ResidentialGroup, SharedCatalog, Tenant


async def _mk_tenants():
    async with admin_sessionmaker()() as s:
        tinh = Tenant(ma_dvhc="T-24", ten="Tỉnh Bắc Ninh", cap="tinh")
        s.add(tinh)
        await s.flush()
        a = Tenant(ma_dvhc="P-A", ten="Phường A", cap="phuong", parent_id=tinh.id)
        b = Tenant(ma_dvhc="P-B", ten="Phường B", cap="phuong", parent_id=tinh.id)
        s.add_all([a, b])
        await s.flush()
        s.add_all([
            ResidentialGroup(tenant_id=a.id, ma_tdp="TDP1", ten="TDP 1"),
            ResidentialGroup(tenant_id=a.id, ma_tdp="TDP2", ten="TDP 2"),
            ResidentialGroup(tenant_id=b.id, ma_tdp="TDP1", ten="TDP 1"),
        ])
        await s.commit()
        return tinh.id, a.id, b.id


@pytest.fixture(scope="module")
async def tenants():
    return await _mk_tenants()


async def test_descendants_include_self_and_children(tenants):
    tinh, a, b = tenants
    async with admin_sessionmaker()() as s:
        assert set(await descendant_ids(s, tinh)) == {tinh, a, b}
        assert set(await descendant_ids(s, a)) == {a}


def test_ward_user_cannot_switch_tenant():
    u = CurrentUser(id=1, tenant_id=10, tenant_ids=[10], roles={"lanh_dao"})
    assert tenant_scope(u, requested=99) == 10
    assert tenant_scope(u, requested=None) == 10


def test_multi_tenant_user_must_pick_allowed_tenant():
    u = CurrentUser(id=2, tenant_id=None, tenant_ids=[10, 11], roles={"chuyen_nganh"})
    assert tenant_scope(u, requested=11) == 11
    with pytest.raises(HTTPException) as e:
        tenant_scope(u, requested=None)
    assert e.value.status_code == 400
    with pytest.raises(HTTPException) as e:
        tenant_scope(u, requested=12)
    assert e.value.status_code == 404


async def test_rls_blocks_raw_sql_cross_tenant(tenants):
    _, a, b = tenants
    async with tenant_session([a]) as s:
        rows = (await s.execute(text("SELECT tenant_id FROM residential_group"))).scalars().all()
        assert rows and set(rows) == {a}
        await s.commit()
        # sau commit, giao dịch mới vẫn phải giữ ngữ cảnh đơn vị
        rows = (await s.execute(text("SELECT tenant_id FROM residential_group"))).scalars().all()
        assert set(rows) == {a}


async def test_rls_without_context_sees_nothing(tenants):
    async with tenant_session([]) as s:
        n = (await s.execute(text("SELECT count(*) FROM residential_group"))).scalar_one()
        assert n == 0


async def test_rls_blocks_insert_into_other_tenant(tenants):
    _, a, b = tenants
    async with tenant_session([a]) as s:
        s.add(ResidentialGroup(tenant_id=b, ma_tdp="X", ten="Chen"))
        with pytest.raises(Exception):
            await s.commit()


async def test_shared_catalog_unique_per_type():
    async with admin_sessionmaker()() as s:
        s.add(SharedCatalog(loai="nguon_von", ma="NSNN", ten="Ngân sách nhà nước"))
        await s.commit()
        s.add(SharedCatalog(loai="nguon_von", ma="NSNN", ten="Trùng"))
        with pytest.raises(Exception):
            await s.commit()
