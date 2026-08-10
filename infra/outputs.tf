output "mcp_url" {
  description = "URL endpoint MCP — điền vào cấu hình agent Notion (nhớ thêm /mcp)"
  value       = "${module.scan_cv.uri}/mcp"
}

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
