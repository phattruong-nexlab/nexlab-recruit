# Chỉ tạo "vỏ" secret. Giá trị KHÔNG bao giờ đi qua Terraform state —
# nạp bằng: gcloud secrets versions add <id> --data-file=-
resource "google_secret_manager_secret" "this" {
  for_each = toset(var.secret_ids)

  project   = var.project_id
  secret_id = "${var.name_prefix}-${each.value}"
  labels    = var.labels

  replication {
    auto {}
  }
}
