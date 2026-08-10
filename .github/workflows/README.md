# CI/CD

| Workflow | Trigger | Việc làm |
|---|---|---|
| `backend-ci.yml` | đổi `backend/**` | ruff · mypy · pytest · build Docker (không push) |
| `terraform.yml` | đổi `infra/**` | fmt · validate · plan (env `dev`) |
| `deploy.yml` | push `main` hoặc chạy tay | build & push image → deploy Cloud Run → gọi `/health` |

## Secrets cần cấu hình trong GitHub

| Secret | Lấy từ đâu |
|---|---|
| `GCP_PROJECT_ID` | project GCP |
| `GCP_REGION` | ví dụ `asia-southeast1` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `terraform output github_workload_identity_provider` |
| `GCP_DEPLOY_SERVICE_ACCOUNT` | `terraform output github_deployer_service_account` |

Xác thực bằng Workload Identity Federation (OIDC) — **không** lưu service account key JSON.

## Ghi chú

- Terraform không quản lý tag image đang chạy (`ignore_changes`), CI mới là nguồn sự thật.
- Endpoint MCP là `<service-url>/mcp`, bảo vệ bằng Bearer token (`MCP_AUTH_TOKEN` trong
  Secret Manager), không dùng IAM — vì agent Notion chỉ gửi được header tĩnh.
- Tạo GitHub Environment `dev` và `prod`; gắn required reviewer cho `prod` nếu muốn chặn deploy nhầm.
