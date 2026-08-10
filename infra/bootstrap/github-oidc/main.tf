# Workload Identity Federation: GitHub Actions lấy được token Google mà KHÔNG cần
# service account key JSON lưu trong secret của repo.

locals {
  repository_condition = "assertion.repository == '${var.github_repository}'"

  branch_condition = length(var.allowed_branches) == 0 ? null : join(
    " || ",
    [for branch in var.allowed_branches : "assertion.ref == 'refs/heads/${branch}'"]
  )

  attribute_condition = local.branch_condition == null ? local.repository_condition : (
    "${local.repository_condition} && (${local.branch_condition})"
  )
}

resource "google_iam_workload_identity_pool" "github" {
  project                   = var.project_id
  workload_identity_pool_id = "${var.name_prefix}-gh-pool"
  display_name              = "GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "${var.name_prefix}-gh-provider"
  display_name                       = "GitHub OIDC"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  # BẮT BUỘC: không chặn theo repository thì MỌI repo GitHub đều mạo danh được.
  # Kèm điều kiện branch để PR từ branch lạ không apply được hạ tầng.
  attribute_condition = local.attribute_condition

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account" "deployer" {
  project      = var.project_id
  account_id   = "${var.name_prefix}-deployer"
  display_name = "GitHub Actions deployer"
}

resource "google_service_account_iam_member" "workload_identity_user" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}

resource "google_project_iam_member" "deployer" {
  for_each = toset(var.deployer_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.deployer.email}"
}
