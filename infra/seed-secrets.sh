#!/usr/bin/env bash
# Nạp giá trị cho các secret trên Google Secret Manager.
#
# Terraform chỉ tạo "vỏ" secret; giá trị không bao giờ đi qua Terraform state.
# Script này đọc giá trị từ backend/.env (nếu có) hoặc hỏi trực tiếp, rồi đẩy lên.
#
#   ./seed-secrets.sh dev
#   ./seed-secrets.sh prod
#
# Không in giá trị ra màn hình, không để lại trong shell history.

set -euo pipefail

ENVIRONMENT="${1:-dev}"
APP_NAME="${APP_NAME:-nexlab-recruit}"
PREFIX="${APP_NAME}-${ENVIRONMENT}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$REPO_ROOT/backend/.env"

if ! command -v gcloud >/dev/null; then
  echo "Cần cài gcloud CLI trước." >&2
  exit 1
fi

PROJECT="$(gcloud config get-value project 2>/dev/null)"
if [ -z "$PROJECT" ] || [ "$PROJECT" = "(unset)" ]; then
  echo "Chưa chọn project. Chạy: gcloud config set project <PROJECT_ID>" >&2
  exit 1
fi

echo "Project: $PROJECT"
echo "Môi trường: $ENVIRONMENT (secret prefix: $PREFIX)"
echo

# Đọc một biến từ backend/.env mà không nạp cả file vào shell.
read_from_env_file() {
  local key="$1"
  [ -f "$ENV_FILE" ] || return 1
  local line
  line="$(grep -m1 "^${key}=" "$ENV_FILE" 2>/dev/null)" || return 1
  local value="${line#*=}"
  value="${value%\"}"
  value="${value#\"}"
  [ -n "$value" ] || return 1
  printf '%s' "$value"
}

# Đẩy một version mới. Dùng printf '%s' để KHÔNG thêm newline ở cuối —
# newline thừa sẽ làm token so sánh không khớp và API key bị từ chối.
push_secret() {
  local secret_id="$1" value="$2"
  if ! gcloud secrets describe "$secret_id" --project "$PROJECT" >/dev/null 2>&1; then
    echo "  BỎ QUA $secret_id — secret chưa tồn tại."
    echo "         Chạy: terraform apply -var-file=envs/$ENVIRONMENT/$ENVIRONMENT.tfvars -target=module.secrets"
    return 1
  fi
  printf '%s' "$value" | gcloud secrets versions add "$secret_id" \
    --project "$PROJECT" --data-file=- >/dev/null
  echo "  OK  $secret_id  (${#value} ký tự)"
}

# Thứ tự tìm giá trị: biến môi trường -> backend/.env -> hỏi người dùng.
seed() {
  local secret_suffix="$1" env_key="$2"
  local secret_id="${PREFIX}-${secret_suffix}"
  local value="${!env_key:-}"
  local source="biến môi trường"

  if [ -z "$value" ]; then
    if value="$(read_from_env_file "$env_key")"; then
      source="backend/.env"
    else
      value=""
    fi
  fi

  if [ -z "$value" ] && [ -t 0 ]; then
    # Chỉ hỏi khi có terminal thật; chạy trong CI hay pipe thì bỏ qua.
    read -rsp "  Nhập $env_key (Enter để bỏ qua): " value || value=""
    echo
    source="nhập tay"
  fi

  if [ -z "$value" ]; then
    echo "  BỎ QUA $secret_id — không có giá trị."
    return 0
  fi

  echo -n "  [$source] "
  push_secret "$secret_id" "$value" || true
}

echo "Nạp secret:"
seed "notion-api-key" "NOTION_API_KEY"
seed "notion-source-data-source-id" "NOTION_SOURCE_DATA_SOURCE_ID"
seed "notion-mirror-data-source-id" "NOTION_MIRROR_DATA_SOURCE_ID"

# Mật khẩu trang quản trị: tự sinh nếu chưa có ở đâu cả.
ADMIN_SECRET="${PREFIX}-admin-password"
ADMIN_VALUE="${ADMIN_PASSWORD:-}"
[ -n "$ADMIN_VALUE" ] || ADMIN_VALUE="$(read_from_env_file ADMIN_PASSWORD || true)"

if [ -z "$ADMIN_VALUE" ]; then
  ADMIN_VALUE="$(python -c 'import secrets; print(secrets.token_urlsafe(32), end="")')"
  echo
  echo "  Đã sinh ADMIN_PASSWORD mới. Đưa mật khẩu này cho HR:"
  echo "  ADMIN_PASSWORD=$ADMIN_VALUE"
  echo
fi
echo -n "  "
push_secret "$ADMIN_SECRET" "$ADMIN_VALUE" || true

echo
echo "Kiểm tra (chỉ hiện số version, không hiện giá trị):"
for suffix in notion-api-key notion-source-data-source-id notion-mirror-data-source-id admin-password; do
  count="$(gcloud secrets versions list "${PREFIX}-${suffix}" --project "$PROJECT" \
    --filter='state=ENABLED' --format='value(name)' 2>/dev/null | wc -l | tr -d ' ')"
  printf '  %-45s %s version\n' "${PREFIX}-${suffix}" "$count"
done
