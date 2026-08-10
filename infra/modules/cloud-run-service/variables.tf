variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "name" {
  type = string
}

variable "image" {
  description = "Full image URI kèm tag"
  type        = string
}

variable "service_account_email" {
  type = string
}

variable "container_port" {
  type    = number
  default = 8080
}

variable "cpu" {
  type    = string
  default = "1"
}

variable "memory" {
  type    = string
  default = "512Mi"
}

variable "min_instances" {
  type    = number
  default = 0
}

variable "max_instances" {
  type    = number
  default = 3
}

variable "request_timeout_seconds" {
  description = "Extraction gọi LLM nên cần timeout rộng hơn mặc định"
  type        = number
  default     = 300
}

variable "ingress" {
  type    = string
  default = "INGRESS_TRAFFIC_ALL"
}

variable "allow_unauthenticated" {
  type    = bool
  default = false
}

variable "health_check_path" {
  type    = string
  default = "/"
}

variable "env_vars" {
  description = "Biến môi trường thường (KHÔNG chứa secret)"
  type        = map(string)
  default     = {}
}

variable "secret_env_vars" {
  description = "map TÊN_BIẾN -> secret_id trong Secret Manager"
  type        = map(string)
  default     = {}
}

variable "labels" {
  type    = map(string)
  default = {}
}
