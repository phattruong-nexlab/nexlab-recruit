variable "project_id" {
  type = string
}

variable "name_prefix" {
  type = string
}

variable "github_repository" {
  description = "Định dạng owner/repo — chỉ repo này được phép lấy token"
  type        = string
}

variable "allowed_branches" {
  description = "Branch được phép lấy token. Rỗng = mọi branch của repo."
  type        = list(string)
  default     = []
}

variable "deployer_roles" {
  description = <<-EOT
    Quyền để CI chạy `terraform apply` và deploy image.

    Rộng hơn mức chỉ deploy, vì Terraform còn tạo service account, secret,
    Artifact Registry và bật API. Đây là mức tối thiểu để config chính chạy được.
  EOT
  type        = list(string)
  default = [
    "roles/run.admin",                       # tạo/sửa Cloud Run service
    "roles/artifactregistry.admin",          # tạo repo + push image
    "roles/secretmanager.admin",             # tạo secret + gán quyền đọc
    "roles/iam.serviceAccountAdmin",         # tạo service account cho Cloud Run
    "roles/iam.serviceAccountUser",          # deploy service chạy dưới danh nghĩa SA đó
    "roles/serviceusage.serviceUsageAdmin",  # bật API trên project
    "roles/resourcemanager.projectIamAdmin", # gán roles/aiplatform.user cho SA của Cloud Run
  ]
}
