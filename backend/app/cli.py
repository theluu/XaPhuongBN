"""Lệnh quản trị: python -m app.cli bootstrap"""
import asyncio
import sys


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "bootstrap":
        from app.core.bootstrap import bootstrap

        asyncio.run(bootstrap())
        print("Đã khởi tạo CSDL")
    else:
        print("Lệnh: bootstrap")
        sys.exit(1)


if __name__ == "__main__":
    main()
