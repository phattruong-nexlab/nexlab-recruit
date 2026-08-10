locals {
  name_prefix = "${var.app_name}-${var.environment}"

  common_labels = {
    app         = var.app_name
    environment = var.environment
    managed_by  = "terraform"
  }

  # Secret ứng dụng — giá trị KHÔNG nằm trong Terraform.
  # Tạo secret rỗng ở đây rồi nạp version bằng tay / bằng CI:
  #   gcloud secrets versions add <name> --data-file=-
  app_secret_ids = [
    "notion-api-key",
    "notion-target-data-source-id",
    "mcp-auth-token",
  ]
}
