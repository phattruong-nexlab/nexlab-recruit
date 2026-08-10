output "secret_ids" {
  description = "map tên ngắn -> secret_id đầy đủ trên GCP"
  value       = { for key, secret in google_secret_manager_secret.this : key => secret.secret_id }
}
