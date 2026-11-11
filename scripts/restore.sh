#!/usr/bin/env bash
# Khôi phục từ bản sao lưu:  ./scripts/restore.sh backups/ioc-xp-YYYYmmdd-HHMMSS.tar.gpg
# Diễn tập khôi phục hằng tháng trên máy staging (DT III.2: sao lưu, quy trình khôi phục).
set -euo pipefail
cd "$(dirname "$0")/.."
source .env
F="${1:?Chỉ rõ tệp sao lưu}"
read -r -p "Khôi phục sẽ GHI ĐÈ dữ liệu hiện tại. Gõ KHOI PHUC để tiếp tục: " ok
[[ "$ok" == "KHOI PHUC" ]] || { echo "Đã hủy"; exit 1; }
TMP=$(mktemp -d)
gpg --batch --pinentry-mode loopback --passphrase "$BACKUP_PASSPHRASE" -d "$F" | tar xf - -C "$TMP"
docker compose exec -T db pg_restore -U "${POSTGRES_USER:-ioc}" -d "${POSTGRES_DB:-ioc}" --clean --if-exists < "$TMP/db.dump"
docker compose exec -T backend sh -c 'rm -rf /data/storage/* && tar xzf - -C /data/storage' < "$TMP/files.tar.gz"
rm -rf "$TMP"
docker compose restart backend
echo "Đã khôi phục từ $F"
