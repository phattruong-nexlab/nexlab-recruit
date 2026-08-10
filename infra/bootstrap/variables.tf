variable "project_id" {
  description = "ID project Google Cloud"
  type        = string
}

variable "region" {
  type    = string
  default = "asia-southeast1"
}

variable "app_name" {
  type    = string
  default = "nexlab-recruit"
}

variable "github_repository" {
  description = "Định dạng owner/repo — chỉ repo này được phép lấy token"
  type        = string
}

variable "allowed_branches" {
  description = <<-EOT
    Các branch được phép chạy terraform apply. Rỗng = mọi branch của repo.
    Siết theo branch để một PR từ branch lạ không apply được hạ tầng.
  EOT
  type        = list(string)
  default     = ["develop", "main"]
}

variable "state_bucket_name" {
  description = "Bucket GCS lưu terraform state của config chính"
  type        = string
  default     = "nexlab-recruit-tfstate"
}

variable "state_bucket_location" {
  type    = string
  default = "asia-southeast1"
}
