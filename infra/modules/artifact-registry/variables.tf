variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "repository_id" {
  type = string
}

variable "labels" {
  type    = map(string)
  default = {}
}

variable "keep_recent_versions" {
  description = "Số image gần nhất giữ lại cho mỗi repo"
  type        = number
  default     = 10
}
