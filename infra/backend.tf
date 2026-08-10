# State lưu trên GCS. Bucket phải được tạo TRƯỚC (một lần, thủ công):
#
#   gcloud storage buckets create gs://nexlab-recruit-tfstate \
#     --project=<PROJECT_ID> --location=asia-southeast1 --uniform-bucket-level-access
#   gcloud storage buckets update gs://nexlab-recruit-tfstate --versioning
#
# Init theo env:
#   terraform init -backend-config=envs/dev/backend.hcl
terraform {
  backend "gcs" {}
}
