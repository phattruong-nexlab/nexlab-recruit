# CLAUDE.md

Hướng dẫn cho Claude Code khi làm việc trong repo này.

## Tổng quan

`nexlab-recruit` — service **scan CV**, chạy như một **MCP server** để agent Notion gọi.

Agent lấy `Resume, CL` (file CV), `Job URL`, `Email`, `Phone`, `Created time` từ đơn
ứng tuyển mới → gọi tool `parse_cv` → service tải CV, đọc nội dung, trích xuất thông
tin bằng **một** lần gọi LLM, rồi ghi một dòng mới vào bảng Notion đích.

Trả về: **Applied Job · University · GPA · Experience · Skill · Certificate · Language**

## Cấu trúc repo

```
backend/     MCP server (Python 3.11), kiến trúc DDD / Clean Architecture
infra/       Terraform — 1 Cloud Run service trên Google Cloud
.github/     GitHub Actions workflows (CI/CD)
```

Không có frontend. Không có database.

## Luồng xử lý (bất biến)

```
file_url → tải file → markitdown → Markdown → Gemini/Vertex AI (1 call) → JSON
                                                                  │
                    Notion (bảng đích) ← mapping tĩnh, KHÔNG LLM ←┘
```

- **LLM chỉ được gọi ĐÚNG MỘT LẦN**, ở bước trích xuất. Mọi bước khác là code thuần.
- **Ghi Notion lỗi ⇒ vẫn trả kết quả phân tích** cho agent (`published: false`).
  Đọc CV tốn một lần gọi LLM, không được vứt đi vì Notion hỏng.
- **`applied_job` suy từ `job_url`**, không để LLM đoán — Job URL là nguồn chính xác.
- **Không bịa dữ liệu**: không tìm thấy field thì trả `null` / `[]`.

## Backend — quy tắc kiến trúc (BẮT BUỘC tuân thủ)

Dependency chỉ được trỏ **vào trong**: `interface → application → domain`.
`infrastructure` implement các interface do `application` định nghĩa.

| Layer | Đường dẫn | Được phép import | Cấm |
|---|---|---|---|
| Domain | `backend/app/domain/` | stdlib, `dataclasses` | mcp, markitdown, genai, notion, pydantic-settings |
| Application | `backend/app/application/` | `domain` | SDK bên ngoài, framework web |
| Infrastructure | `backend/app/infrastructure/` | `domain`, `application`, mọi SDK | — |
| Interface | `backend/app/interface/` | `application`, `domain`, mcp, starlette | truy cập SDK trực tiếp |

- Domain là **pure Python** (dataclass), không I/O, không async.
- Application định nghĩa **ports** (ABC) trong `application/ports/`; infrastructure là **adapters**.
- Wiring / DI nằm ở `backend/app/interface/mcp/dependencies.py`.
- `main.py` và `config.py` nằm ở **root của `backend/`**, không nằm trong `app/`.
- Mọi secret đọc qua `config.py` (`pydantic-settings`), không `os.environ` rải rác.

## Lệnh thường dùng

```bash
# Backend
cd backend
uv sync --all-extras
uv run python main.py                 # MCP tại http://localhost:8000/mcp
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
- Không đọc ngược dữ liệu từ Notion; agent lo phần đó và truyền vào qua tham số tool.
- Không thêm multi-agent / ADK.
- Không import SDK bên ngoài vào `domain/`.
- Không để endpoint MCP không có `MCP_AUTH_TOKEN` khi chạy ngoài local.
- Không quay lại dùng Gemini API key — xác thực qua Vertex AI + ADC.
