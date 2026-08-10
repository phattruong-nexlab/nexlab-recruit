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


variable "vertex_location" {
  description = "Vùng của Vertex AI. \"global\" tránh được chuyện model chưa có ở region."
  type        = string
  default     = "global"
}

variable "gemini_model" {
  type    = string
  default = "gemini-2.5-flash"
}
