output "github_secrets" {
  description = "Copy nguyên các giá trị này vào GitHub → Settings → Secrets → Actions"
  value = {
    GCP_PROJECT_ID                 = var.project_id
    GCP_REGION                     = var.region
    GCP_WORKLOAD_IDENTITY_PROVIDER = module.github_oidc.workload_identity_provider
    GCP_DEPLOY_SERVICE_ACCOUNT     = module.github_oidc.service_account_email
  }
}

output "state_bucket" {
  description = "Điền vào envs/<env>/backend.hcl"
  value       = google_storage_bucket.tfstate.name
}
