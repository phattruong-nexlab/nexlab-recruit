# ---------------------------------------------------------------------------
# Bootstrap — chạy MỘT LẦN bằng tay, trước khi CI có thể chạy Terraform.
#
# Vòng luẩn quẩn cần gỡ: CI muốn chạy `terraform apply` thì phải có Workload
# Identity Provider + service account; nhưng chính Terraform lại là thứ tạo ra
# chúng. Nên tách phần này ra, apply thủ công một lần với quyền Owner.
# ---------------------------------------------------------------------------

resource "google_project_service" "required" {
  for_each = toset([
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "storage.googleapis.com",
    "serviceusage.googleapis.com",
  ])

  service            = each.value
  disable_on_destroy = false
}

# --- Nơi lưu state của config chính ----------------------------------------
resource "google_storage_bucket" "tfstate" {
  name                        = var.state_bucket_name
  location                    = var.state_bucket_location
  uniform_bucket_level_access = true
  force_destroy               = false

  versioning {
    enabled = true # state hỏng thì còn bản cũ để lùi
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 20
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.required]
}

# --- Danh tính cho GitHub Actions -------------------------------------------
module "github_oidc" {
  source = "./github-oidc"

  project_id        = var.project_id
  name_prefix       = var.app_name
  github_repository = var.github_repository
  allowed_branches  = var.allowed_branches

  depends_on = [google_project_service.required]
}

# Chỉ cấp quyền ghi state trên đúng bucket này, không phải storage.admin toàn project.
resource "google_storage_bucket_iam_member" "deployer_state" {
  bucket = google_storage_bucket.tfstate.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${module.github_oidc.service_account_email}"
}
