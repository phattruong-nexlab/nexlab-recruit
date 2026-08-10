# Infra — nexlab-recruit

Terraform dựng hạ tầng trên **Google Cloud**: một Cloud Run service chạy MCP server,
Artifact Registry và Secret Manager.

## Cấu trúc

```
infra/
├── bootstrap/        CHẠY MỘT LẦN BẰNG TAY — tạo state bucket + danh tính cho CI
│   └── github-oidc/  Workload Identity Federation + service account cho GitHub
├── main.tf           config chính, CI quản
├── modules/
│   ├── artifact-registry/
│   ├── cloud-run-service/
│   └── secrets/
└── envs/
    ├── dev/{dev.tfvars,backend.hcl}
    └── prod/{prod.tfvars,backend.hcl}
```

## Vì sao phải tách `bootstrap/`

CI muốn chạy `terraform apply` thì cần Workload Identity Provider và service account.
Nhưng chính Terraform mới là thứ tạo ra chúng — con gà và quả trứng.

`bootstrap/` gỡ nút thắt đó: chạy **một lần, bằng tay, với tài khoản có quyền Owner**,
tạo sẵn state bucket + danh tính. Sau đó CI tự lo phần còn lại.

`bootstrap/` cố ý dùng **local state** vì nó tạo ra chính cái bucket chứa state.

---

## Bước 1 — Bootstrap (một lần cho mỗi project)

```bash
cd infra/bootstrap
cp terraform.tfvars.example terraform.tfvars   # điền project_id, github_repository

gcloud auth application-default login
terraform init
terraform apply
```

Xong sẽ in ra 4 giá trị. Vào **GitHub → Settings → Secrets and variables → Actions**
tạo đúng 4 repository secret:

| Secret | Lấy từ |
|---|---|
| `GCP_PROJECT_ID` | output `github_secrets` |
| `GCP_REGION` | output `github_secrets` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | output `github_secrets` |
| `GCP_DEPLOY_SERVICE_ACCOUNT` | output `github_secrets` |

Giữ file `terraform.tfstate` của bootstrap ở nơi an toàn (không commit — đã gitignore).
Mất cũng không chết: `terraform import` lại được, hoặc xoá thủ công rồi apply lại.

## Bước 2 — Tạo GitHub Environment

**Settings → Environments** → tạo `dev` và `prod`.

Với `prod` nên bật **Required reviewers** để `terraform apply` phải có người duyệt.

## Bước 3 — Apply lần đầu: PHẢI chia hai pha

Cloud Run gắn secret vào biến môi trường. Secret chưa có version nào thì container
không khởi động được, và `terraform apply` sẽ fail ở bước tạo service.

Nên lần đầu phải tạo secret trước, nạp giá trị, rồi mới apply phần còn lại:

```bash
cd infra
terraform init -backend-config=envs/dev/backend.hcl

# Pha 1: chỉ tạo "vỏ" secret
terraform apply -var-file=envs/dev/dev.tfvars -target=module.secrets
```

Terraform chỉ tạo vỏ; giá trị KHÔNG bao giờ đi qua Terraform state — nạp thủ công.

Chỉ còn **3 secret**: Gemini không dùng API key nữa (xem mục Vertex AI bên dưới).

```bash
# Cách gọn: đọc thẳng từ backend/.env, hỏi tay cái nào thiếu
bash seed-secrets.sh dev

# Hoặc từng cái một:
printf '%s' "$NOTION_API_KEY" | \
  gcloud secrets versions add nexlab-recruit-dev-notion-api-key --data-file=-

printf '%s' "$NOTION_TARGET_DATA_SOURCE_ID" | \
  gcloud secrets versions add nexlab-recruit-dev-notion-target-data-source-id --data-file=-

python -c "import secrets; print(secrets.token_urlsafe(32))" | tr -d '\n' | \
  gcloud secrets versions add nexlab-recruit-dev-mcp-auth-token --data-file=-
```

```bash
# Pha 2: apply toàn bộ (Artifact Registry, Cloud Run, IAM)
terraform apply -var-file=envs/dev/dev.tfvars
```

Lần đầu Cloud Run chạy image placeholder `cloudrun/container/hello` — đúng như thiết
kế. Image thật do workflow `deploy.yml` push lên sau đó; Terraform không kéo ngược
lại vì `image` nằm trong `ignore_changes`.

Các lần apply sau không cần chia pha nữa.

## Bước 4 — CI tự chạy

| Sự kiện | Workflow làm gì |
|---|---|
| PR vào `develop` | `fmt` · `validate` · `plan` rồi dán kết quả vào PR |
| Merge vào `develop` | `plan` → `apply` lên môi trường `dev` |
| Chạy tay (`workflow_dispatch`) | Chọn env, tick `apply` mới apply thật |

Apply dùng **đúng file plan đã sinh ra ở job trước** (artifact `tfplan`), không plan
lại — thứ được apply luôn khớp với thứ đã review trong PR.

Không có thay đổi nào (`plan` exit code 0) thì job `apply` bị bỏ qua.

---

## Chạy tay ở máy

```bash
cd infra
terraform init -backend-config=envs/dev/backend.hcl
terraform plan  -var-file=envs/dev/dev.tfvars
terraform apply -var-file=envs/dev/dev.tfvars
```

## Gemini qua Vertex AI — không có API key

Service gọi Gemini bằng **Application Default Credentials**, không phải API key:

- Trên Cloud Run: service account `<prefix>-svc` gắn vào service, được cấp
  `roles/aiplatform.user` ở project level.
- Ở máy local: `gcloud auth application-default login`.

Terraform lo sẵn: bật `aiplatform.googleapis.com`, tạo IAM binding, truyền
`GCP_PROJECT_ID` / `VERTEX_LOCATION` / `GEMINI_MODEL` vào biến môi trường.

`vertex_location` mặc định `"global"` để tránh chuyện model chưa có ở một region cụ thể.
Đổi bằng `-var vertex_location=asia-southeast1` nếu cần dữ liệu ở lại một vùng.

So với API key: không còn secret nào để rò rỉ hay xoay vòng, quota và chi phí tính vào
chính project GCP, và audit log của Vertex AI ghi lại mọi lời gọi.

## Bảo mật

- `attribute_condition` của WIF khoá theo **repository và branch** (`develop`, `main`).
  Repo khác hoặc branch lạ không lấy được token. Không được bỏ điều kiện này.
- Service account CI có quyền khá rộng (tạo SA, secret, bật API) vì Terraform cần thế.
  Đổi lại nó bị giới hạn ở đúng một project và đúng repo/branch.
- Quyền ghi state chỉ cấp trên đúng bucket tfstate, không phải `storage.admin` toàn project.
- Endpoint MCP để `allow_unauthenticated = true` ở tầng IAM, bảo vệ bằng Bearer token
  (`MCP_AUTH_TOKEN`) trong ứng dụng — vì agent Notion chỉ gửi được header tĩnh.
- Không commit `*.tfstate` hay tfvars chứa secret.

## Chưa có (thêm khi cần)

Custom domain + load balancer · Cloud Armor / WAF · budget alert · alerting policy ·
môi trường `prod` tự động (hiện chỉ chạy tay hoặc qua `workflow_dispatch`).
