# nexlab-recruit — scan CV

Service phân tích CV ứng viên, chạy như một **MCP server** để agent Notion gọi.

```
Đơn ứng tuyển mới trên Notion
        │  agent lấy: Resume·CL (file), Job URL, Email, Phone, Created time
        ▼
   MCP tool  parse_cv(file_url, job_url, email, phone, created_time)
        │
        │  tải file → markitdown → Markdown → Gemini (1 call) → JSON
        ▼
   Applied Job · University · GPA · Experience · Skill · Certificate · Language
        │
        ▼
   Ghi một dòng mới vào bảng Notion đích  (mapping tĩnh, không LLM)
```

## Cấu trúc

```
backend/             MCP server — Python 3.11, DDD / Clean Architecture
infra/               Terraform — 1 Cloud Run service (GCP)
.github/workflows/   CI + deploy
CLAUDE.md            hướng dẫn cho Claude Code
AGENT.md             hướng dẫn chung cho mọi AI coding agent
```

## Bắt đầu

```bash
cd backend
cp .env.example .env       # điền GEMINI_API_KEY, NOTION_API_KEY, MCP_AUTH_TOKEN...
uv sync --all-extras
uv run python main.py
```

- MCP endpoint: `http://localhost:8000/mcp`
- Health: `http://localhost:8000/health`

Chi tiết: [backend/README.md](backend/README.md) · [infra/README.md](infra/README.md) ·
[.github/workflows/README.md](.github/workflows/README.md)

## Nguyên tắc thiết kế

**Một lần gọi LLM duy nhất.** Chỉ ở bước trích xuất field từ Markdown. Việc ghi sang
Notion là mapping tĩnh trong code — cùng đầu vào luôn ra cùng payload.

**Stateless.** Không database. Service nhận link CV, trả kết quả, ghi Notion. Agent
giữ vai trò điều phối.

**Ghi Notion lỗi không làm mất kết quả.** Tool vẫn trả về dữ liệu đã phân tích kèm
`published: false` để agent tự xử lý.
