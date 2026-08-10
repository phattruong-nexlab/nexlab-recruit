variable "project_id" {
  type = string
}

variable "name_prefix" {
  type = string
}

variable "secret_ids" {
  description = "Tên secret (chưa có prefix)"
  type        = list(string)
}

variable "labels" {
  type    = map(string)
  default = {}
}
