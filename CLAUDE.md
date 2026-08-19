# CLAUDE.md

Hướng dẫn cho Claude Code khi làm việc trong repo này.

## Tổng quan

`nexlab-recruit` — service **scan CV** chạy theo lô trên Google Cloud.

Cloud Run Job đối chiếu bảng đơn ứng tuyển (Tally đổ vào) với bảng kết quả, xử lý
những CV chưa có, rồi ghi vào bảng đích. Kích hoạt bằng Cloud Scheduler theo lịch
hoặc bằng nút bấm trên trang `/admin` cho HR.

Trả về: **Applied Job · University · GPA · Experience · Skill · Certificate · Language**

## Cấu trúc repo

```
backend/     Web service + Cloud Run Job (Python 3.11), DDD / Clean Architecture
infra/       Terraform — Cloud Run service + job + scheduler trên Google Cloud
.github/     GitHub Actions workflows (CI/CD)
```

Không có frontend. Không có database.

## Luồng xử lý (bất biến)

```
[đơn nguồn] − [Source ID đã có ở bảng đích]   ← phép TRỪ TẬP HỢP, không dùng mốc thời gian
        │
        └→ tải file → markitdown → Markdown → Vertex AI (1 call) → JSON
                                                                    │
                          Notion (bảng đích) ← mapping tĩnh, KHÔNG LLM ←┘
```

- **LLM chỉ được gọi ĐÚNG MỘT LẦN**, ở bước trích xuất. Mọi bước khác là code thuần.
- **Ghi Notion lỗi ⇒ vẫn trả kết quả phân tích** cho agent (`published: false`).
  Đọc CV tốn một lần gọi LLM, không được vứt đi vì Notion hỏng.
- **`applied_job` suy từ `job_url`**, không để LLM đoán — Job URL là nguồn chính xác.
- **Cột `Source ID` là bộ nhớ duy nhất.** Không lưu checkpoint trong service; chạy lại
  bao nhiêu lần cũng không tạo dòng trùng, CV lỗi tự được nhặt lại ở lượt sau.
- **Không bịa dữ liệu**: không tìm thấy field thì trả `null` / `[]`.

## Backend — quy tắc kiến trúc (BẮT BUỘC tuân thủ)

Dependency chỉ được trỏ **vào trong**: `interface → application → domain`.
`infrastructure` implement các interface do `application` định nghĩa.

| Layer | Đường dẫn | Được phép import | Cấm |
|---|---|---|---|
| Domain | `backend/app/domain/` | stdlib, `dataclasses` | markitdown, genai, notion, starlette, pydantic-settings |
| Application | `backend/app/application/` | `domain` | SDK bên ngoài, framework web |
| Infrastructure | `backend/app/infrastructure/` | `domain`, `application`, mọi SDK | — |
| Interface | `backend/app/interface/` | `application`, `domain`, starlette | truy cập SDK trực tiếp |

- Domain là **pure Python** (dataclass), không I/O, không async.
- Application định nghĩa **ports** (ABC) trong `application/ports/`; infrastructure là **adapters**.
- Wiring / DI nằm ở `backend/app/interface/dependencies.py`.
- `main.py` và `config.py` nằm ở **root của `backend/`**, không nằm trong `app/`.
- Mọi secret đọc qua `config.py` (`pydantic-settings`), không `os.environ` rải rác.

## Lệnh thường dùng

```bash
# Backend
cd backend
uv sync --all-extras
uv run python main.py                 # trang quản trị: http://localhost:8000/admin
uv run python -m app.interface.jobs.scan_pending --limit 2   # chạy thử job
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy .

# Infra
cd infra
terraform init -backend-config=envs/dev/backend.hcl
terraform plan  -var-file=envs/dev/dev.tfvars
terraform apply -var-file=envs/dev/dev.tfvars
```

## Quy ước

- Commit theo Conventional Commits: `feat:`, `fix:`, `chore:`, `refactor:`, `docs:`, `test:`.
- Branch: `feat/<slug>`, `fix/<slug>`. Không commit thẳng vào `main`.
- Không commit `.env`, `*.tfvars` chứa secret, service account key, hay CV đã tải về
  (`backend/data/`). Chỉ commit `*.example`.
- Đặt tên biến / hàm bằng tiếng Anh; comment và tài liệu có thể tiếng Việt.

## Điều cần tránh

- Không gọi LLM ở bước nào khác ngoài `CvExtractor`. Mapping sang Notion là code thuần.
- Không thêm database — service stateless, không có source of truth riêng.
- Không thêm multi-agent / ADK.
- Không import SDK bên ngoài vào `domain/`.
- Không để trang `/admin` không có `ADMIN_PASSWORD` khi chạy ngoài local.
- Không dùng mốc thời gian để nhớ đã xử lý tới đâu — luôn đối chiếu bằng `Source ID`.
- Không quay lại dùng Gemini API key — xác thực qua Vertex AI + ADC.
