output "service_url" {
  description = "URL gốc của Cloud Run service"
  value       = module.scan_cv.uri
}

output "artifact_registry_repository" {
  description = "Đường dẫn Docker registry để push image"
  value       = module.artifact_registry.repository_url
}

output "secret_ids" {
  description = "Các secret cần nạp giá trị bằng: gcloud secrets versions add <id> --data-file=-"
  value       = values(module.secrets.secret_ids)
}

output "admin_url" {
  description = "Trang HR bấm nút quét — đặt link này vào Notion"
  value       = "${module.scan_cv.uri}/admin"
}

output "scan_job_name" {
  value = google_cloud_run_v2_job.scan.name
}
