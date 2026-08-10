output "repository_url" {
  description = "Dùng làm tiền tố khi tag image"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.this.repository_id}"
}

output "repository_id" {
  value = google_artifact_registry_repository.this.repository_id
}
