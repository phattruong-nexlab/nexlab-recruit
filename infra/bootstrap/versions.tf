terraform {
  required_version = ">= 1.9.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

# CỐ Ý dùng local state.
#
# Bootstrap tạo ra chính cái bucket chứa state của config chính, nên không thể tự
# lưu state vào đó. Chạy MỘT LẦN bằng tay với tài khoản có quyền Owner.
# File terraform.tfstate sinh ra đã bị .gitignore — giữ lại ở máy hoặc trong
# password manager của team; mất thì import lại được (xem README).
