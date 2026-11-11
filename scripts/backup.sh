#!/usr/bin/env bash
# Sao lưu CSDL + tệp đính kèm, mã hóa bằng BACKUP_PASSPHRASE (trong .env), giữ 30 bản gần nhất.
set -euo pipefail
cd "$(dirname "$0")/.."
source .env
: "${BACKUP_PASSPHRASE:?Đặt BACKUP_PASSPHRASE trong .env}"
DIR="${BACKUP_DIR:-./backups}"; mkdir -p "$DIR"
TS=$(date +%Y%m%d-%H%M%S)
TMP=$(mktemp -d)
docker compose exec -T db pg_dump -U "${POSTGRES_USER:-ioc}" -d "${POSTGRES_DB:-ioc}" -Fc > "$TMP/db.dump"
docker compose exec -T backend tar czf - -C /data/storage . > "$TMP/files.tar.gz"
tar cf - -C "$TMP" db.dump files.tar.gz | gpg --batch --yes --pinentry-mode loopback --passphrase "$BACKUP_PASSPHRASE" -c -o "$DIR/ioc-xp-$TS.tar.gpg"
rm -rf "$TMP"
ls -1t "$DIR"/ioc-xp-*.tar.gpg | tail -n +31 | xargs -r rm -f
echo "Đã sao lưu: $DIR/ioc-xp-$TS.tar.gpg"
