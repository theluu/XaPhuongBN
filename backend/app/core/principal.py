from dataclasses import dataclass, field


@dataclass(frozen=True)
class CurrentUser:
    id: int
    tenant_id: int | None
    tenant_ids: list[int]
    roles: set[str] = field(default_factory=set)
    # nhóm dữ liệu -> tập quyền {"doc","nhap","duyet"}; khóa "*" = mọi nhóm
    permissions: dict[str, set[str]] = field(default_factory=dict)
    username: str = ""

    def can(self, quyen: str, nhom: str | None = None) -> bool:
        if quyen in self.permissions.get("*", set()):
            return True
        return nhom is not None and quyen in self.permissions.get(nhom, set())
