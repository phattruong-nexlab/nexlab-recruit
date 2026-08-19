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
    "admin-password",
    "notion-source-data-source-id",
  ]

  # Secret nào gắn vào biến môi trường nào — service và job dùng CHUNG bộ này.
  app_secret_env_vars = {
    NOTION_API_KEY               = module.secrets.secret_ids["notion-api-key"]
    NOTION_SOURCE_DATA_SOURCE_ID = module.secrets.secret_ids["notion-source-data-source-id"]
    ADMIN_PASSWORD               = module.secrets.secret_ids["admin-password"]
  }
}
