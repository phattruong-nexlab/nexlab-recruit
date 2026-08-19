# ---------------------------------------------------------------------------
# API cần bật trên project
# ---------------------------------------------------------------------------
resource "google_project_service" "required" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "aiplatform.googleapis.com",
    "cloudscheduler.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "cloudresourcemanager.googleapis.com",
  ])

  service            = each.value
  disable_on_destroy = false
}

# ---------------------------------------------------------------------------
# Artifact Registry — nơi chứa container image
# ---------------------------------------------------------------------------
module "artifact_registry" {
  source = "./modules/artifact-registry"

  project_id    = var.project_id
  region        = var.region
  repository_id = local.name_prefix
  labels        = local.common_labels

  depends_on = [google_project_service.required]
}

# ---------------------------------------------------------------------------
# Secret Manager — chỉ tạo "vỏ" secret, giá trị nạp ngoài Terraform
# ---------------------------------------------------------------------------
module "secrets" {
  source = "./modules/secrets"

  project_id  = var.project_id
  name_prefix = local.name_prefix
  secret_ids  = local.app_secret_ids
  labels      = local.common_labels

  depends_on = [google_project_service.required]
}

# ---------------------------------------------------------------------------
# Service account cho từng service (nguyên tắc đặc quyền tối thiểu)
# ---------------------------------------------------------------------------
resource "google_service_account" "scan_cv" {
  account_id   = "${local.name_prefix}-svc"
  display_name = "Cloud Run scan-cv (${var.environment})"
}

# Chỉ backend được đọc secret.
resource "google_secret_manager_secret_iam_member" "scan_cv_accessor" {
  for_each = module.secrets.secret_ids

  project   = var.project_id
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.scan_cv.email}"
}

# OCR cho CV dạng ảnh scan gọi Gemini qua Vertex AI, dùng chính danh tính của
# service account — không cần API key.
resource "google_project_iam_member" "vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.scan_cv.email}"
}

# ---------------------------------------------------------------------------
# Cloud Run service
# ---------------------------------------------------------------------------
module "scan_cv" {
  source = "./modules/cloud-run-service"

  project_id            = var.project_id
  region                = var.region
  name                  = "${local.name_prefix}-web"
  image                 = var.service_image
  service_account_email = google_service_account.scan_cv.email
  labels                = local.common_labels
  allow_unauthenticated = var.allow_public_service
  min_instances         = var.min_instances
  max_instances         = var.max_instances
  cpu                   = "1"
  memory                = "2Gi" # markitdown nạp khá nhiều thư viện
  health_check_path     = "/health"

  # Trang /admin tự bảo vệ bằng mật khẩu (ADMIN_PASSWORD), không dùng IAM,
  # để HR mở được link trực tiếp từ Notion mà không cần tài khoản Google.
  env_vars = {
    ENVIRONMENT              = var.environment
    LOG_LEVEL                = var.environment == "prod" ? "INFO" : "DEBUG"
    GCP_PROJECT_ID           = var.project_id
    GCP_REGION               = var.region
    CLOUD_RUN_JOB_NAME       = "${local.name_prefix}-scan-job"
    CLOUD_SCHEDULER_JOB_NAME = "${local.name_prefix}-daily-scan"
    VERTEX_LOCATION          = var.vertex_location
    GEMINI_MODEL             = var.gemini_model
  }

  secret_env_vars = local.app_secret_env_vars

  depends_on = [
    google_project_service.required,
    google_secret_manager_secret_iam_member.scan_cv_accessor,
  ]
}

# ---------------------------------------------------------------------------
# Cloud Run Job — quét CV theo lô
#
# Dùng CHUNG image với service, chỉ khác entrypoint. Chạy tới khi xong rồi tắt:
# không có endpoint HTTP, không cần mật khẩu, và link CV lấy thẳng từ Notion.
# ---------------------------------------------------------------------------
resource "google_cloud_run_v2_job" "scan" {
  name                = "${local.name_prefix}-scan-job"
  location            = var.region
  project             = var.project_id
  labels              = local.common_labels
  deletion_protection = false

  template {
    # Ngày cao điểm ~110 CV; mỗi CV ~30s, chạy song song nên vẫn dư thời gian.
    task_count = 1

    template {
      service_account = google_service_account.scan_cv.email
      timeout         = "${var.scan_timeout_seconds}s"
      max_retries     = 1

      containers {
        image   = var.service_image
        command = ["python", "-m", "app.interface.jobs.extract_content"]

        resources {
          limits = {
            cpu    = "2"
            memory = "2Gi"
          }
        }

        env {
          name  = "ENVIRONMENT"
          value = var.environment
        }
        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }
        env {
          name  = "SCAN_CONCURRENCY"
          value = tostring(var.scan_concurrency)
        }
        env {
          name  = "VERTEX_LOCATION"
          value = var.vertex_location
        }
        env {
          name  = "GEMINI_MODEL"
          value = var.gemini_model
        }

        dynamic "env" {
          for_each = local.app_secret_env_vars
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value
                version = "latest"
              }
            }
          }
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].template[0].containers[0].image,
      client,
      client_version,
    ]
  }

  depends_on = [
    google_project_service.required,
    google_secret_manager_secret_iam_member.scan_cv_accessor,
    google_project_iam_member.vertex_user,
  ]
}

# Nút bấm trên trang quản trị chạy dưới danh nghĩa service → service phải được
# phép kích hoạt job và đọc trạng thái execution.
resource "google_cloud_run_v2_job_iam_member" "service_can_run_job" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.scan.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scan_cv.email}"
}

resource "google_project_iam_member" "service_can_read_executions" {
  project = var.project_id
  role    = "roles/run.viewer"
  member  = "serviceAccount:${google_service_account.scan_cv.email}"
}

# ---------------------------------------------------------------------------
# Cloud Scheduler — chạy tự động hằng ngày (ngoài nút bấm tay của HR)
# ---------------------------------------------------------------------------
resource "google_cloud_scheduler_job" "daily_scan" {
  count = var.scan_schedule == "" ? 0 : 1

  name        = "${local.name_prefix}-daily-scan"
  project     = var.project_id
  region      = var.region
  schedule    = var.scan_schedule
  time_zone   = var.scan_timezone
  description = "Quét CV chưa xử lý mỗi ngày"

  http_target {
    http_method = "POST"
    uri = join("", [
      "https://run.googleapis.com/v2/projects/", var.project_id,
      "/locations/", var.region,
      "/jobs/", google_cloud_run_v2_job.scan.name, ":run",
    ])

    oauth_token {
      service_account_email = google_service_account.scan_cv.email
    }
  }

  # HR đổi giờ chạy từ trang /admin. Không có ignore_changes thì lần
  # `terraform apply` kế tiếp sẽ lặng lẽ kéo về giá trị trong code.
  lifecycle {
    ignore_changes = [schedule]
  }

  depends_on = [google_cloud_run_v2_job_iam_member.service_can_run_job]
}

# Trang quản trị đọc và sửa lịch chạy -> service cần quyền trên Cloud Scheduler.
resource "google_project_iam_member" "service_can_manage_scheduler" {
  project = var.project_id
  role    = "roles/cloudscheduler.admin"
  member  = "serviceAccount:${google_service_account.scan_cv.email}"
}
