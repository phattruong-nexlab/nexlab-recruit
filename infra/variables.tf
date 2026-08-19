variable "project_id" {
  description = "ID project Google Cloud"
  type        = string
}

variable "region" {
  description = "Region triển khai (mặc định Singapore — gần VN nhất)"
  type        = string
  default     = "asia-southeast1"
}

variable "environment" {
  description = "Tên môi trường: dev | prod"
  type        = string

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "environment chỉ nhận giá trị 'dev' hoặc 'prod'."
  }
}

variable "app_name" {
  description = "Tiền tố đặt tên cho mọi resource"
  type        = string
  default     = "nexlab-recruit"
}

variable "service_image" {
  description = "Image đầy đủ tag. CI ghi đè giá trị này mỗi lần deploy."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "min_instances" {
  description = "Số instance tối thiểu (0 = scale-to-zero; cold start ~10s vì markitdown nặng)"
  type        = number
  default     = 0
}

variable "max_instances" {
  type    = number
  default = 3
}

variable "allow_public_service" {
  description = "Cho phép gọi không cần IAM. Cần true vì agent chỉ gửi Bearer token."
  type        = bool
  default     = true
}



variable "scan_concurrency" {
  description = <<-EOT
    Số dòng xử lý song song. Notion giới hạn ~3 request/giây và mỗi dòng tốn 3
    lời gọi, nên để cao hơn 3 sẽ dính 429 khi chạy hàng nghìn dòng.
  EOT
  type        = number
  default     = 3
}

variable "scan_timeout_seconds" {
  description = "Thời gian tối đa cho một lượt quét (mặc định 2 giờ)"
  type        = number
  default     = 7200
}

variable "scan_schedule" {
  description = <<-EOT
    Lịch cron cho lượt chạy tự động. Rỗng = chỉ chạy khi HR bấm nút.

    Đây chỉ là giá trị KHỞI TẠO — HR đổi giờ được từ trang /admin, và Terraform
    không ghi đè lại (xem lifecycle.ignore_changes ở main.tf).
  EOT
  type        = string
  default     = "0 2 * * *"
}

variable "scan_timezone" {
  type    = string
  default = "Asia/Ho_Chi_Minh"
}
