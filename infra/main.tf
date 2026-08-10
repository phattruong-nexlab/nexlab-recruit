# ---------------------------------------------------------------------------
# API cần bật trên project
# ---------------------------------------------------------------------------
resource "google_project_service" "required" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "aiplatform.googleapis.com",
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
  display_name = "Cloud Run MCP scan-cv (${var.environment})"
}

# Chỉ backend được đọc secret.
resource "google_secret_manager_secret_iam_member" "scan_cv_accessor" {
  for_each = module.secrets.secret_ids

  project   = var.project_id
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.scan_cv.email}"
}

# Gọi Gemini qua Vertex AI bằng chính danh tính của service — không cần API key.
resource "google_project_iam_member" "scan_cv_vertex" {
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
  name                  = "${local.name_prefix}-mcp"
  image                 = var.service_image
  service_account_email = google_service_account.scan_cv.email
  labels                = local.common_labels
  allow_unauthenticated = var.allow_public_service
  min_instances         = var.min_instances
  max_instances         = var.max_instances
  cpu                   = "1"
  memory                = "2Gi" # markitdown nạp khá nhiều thư viện
  health_check_path     = "/health"

  # Endpoint được bảo vệ bằng Bearer token (MCP_AUTH_TOKEN), không phải IAM,
  # vì agent Notion chỉ gửi được header Authorization tĩnh.
  env_vars = {
    ENVIRONMENT     = var.environment
    LOG_LEVEL       = var.environment == "prod" ? "INFO" : "DEBUG"
    MCP_PATH        = "/mcp"
    GCP_PROJECT_ID  = var.project_id
    VERTEX_LOCATION = var.vertex_location
    GEMINI_MODEL    = var.gemini_model
  }

  secret_env_vars = {
    NOTION_API_KEY               = module.secrets.secret_ids["notion-api-key"]
    NOTION_TARGET_DATA_SOURCE_ID = module.secrets.secret_ids["notion-target-data-source-id"]
    MCP_AUTH_TOKEN               = module.secrets.secret_ids["mcp-auth-token"]
  }

  depends_on = [
    google_project_service.required,
    google_secret_manager_secret_iam_member.scan_cv_accessor,
    google_project_iam_member.scan_cv_vertex,
  ]
}
