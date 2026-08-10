# Backend — nexlab scan-cv

**MCP server** cho agent Notion gọi. Python 3.11, kiến trúc DDD / Clean Architecture.

## Tool expose ra

| Tool | Input | Output |
|---|---|---|
| `parse_cv` | `file_url` (bắt buộc), `job_url`, `email`, `phone`, `created_time` | Applied Job · University · GPA · Experience · Skill · Certificate · Language |

Sau khi phân tích, service tự ghi một dòng mới vào bảng Notion đích và trả về
`notion_page_id`. Ghi Notion lỗi thì vẫn trả kết quả phân tích (`published: false`).

## Luồng xử lý

```
file_url  →  tải file  →  markitdown → Markdown  →  Vertex AI (1 call)  →  JSON
                                                                          │
                       Notion (bảng đích)  ←  mapping tĩnh, KHÔNG LLM  ←──┘
```

LLM chỉ được gọi **đúng một lần**, ở bước trích xuất. Mapping sang Notion là code
thuần trong `infrastructure/notion/property_mapping.py`.

## Cấu trúc

```
backend/
├── main.py                     # Starlette: mount MCP + /health + Bearer auth
├── config.py                   # Settings (pydantic-settings) — nơi DUY NHẤT đọc env
├── app/
│   ├── domain/                 # ❶ Pure Python: Candidate, Experience, value object
│   │   ├── entities/
│   │   ├── value_objects/
│   │   ├── services/           #    applied_job (suy từ Job URL), normalizer
│   │   └── exceptions.py
│   ├── application/            # ❷ Use case + ports
│   │   ├── dto/parse_cv.py
│   │   ├── ports/              #    CvDownloader, CvReader, CvExtractor, CandidatePublisher
│   │   └── use_cases/parse_cv.py
│   ├── infrastructure/         # ❸ Adapters
│   │   ├── http/               #    tải file (chặn SSRF, giới hạn dung lượng)
│   │   ├── reader/             #    markitdown → Markdown
│   │   ├── llm/                #    Gemini structured output
│   │   └── notion/             #    ghi bảng đích + mapping property
│   └── interface/mcp/          # ❹ MCP: tool parse_cv, Bearer auth, DI
├── scripts/                    # script chạy tay: tải CV từ Notion về máy
└── tests/
```

## Chạy local

```bash
cp .env.example .env       # điền NOTION_API_KEY, MCP_AUTH_TOKEN, ...
gcloud auth application-default login   # Gemini dùng ADC, không cần API key
uv sync --all-extras
uv run python main.py      # http://localhost:8000/mcp
```

Kiểm tra nhanh:

```bash
curl localhost:8000/health

curl -s localhost:8000/mcp/ \
  -H "Authorization: Bearer $MCP_AUTH_TOKEN" \
  -H "Accept: application/json, text/event-stream" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## Kiểm tra

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy .
uv run pytest
```

## Cấu hình bảng Notion đích

`FIELD_TO_COLUMN` trong `app/infrastructure/notion/property_mapping.py` quyết định
field nào vào cột nào. Dạng payload tự khớp theo **kiểu** của cột (title, rich_text,
select, multi_select, number, email, phone_number, url, date) — đổi kiểu cột trên
Notion không phải sửa code. Cột không tồn tại sẽ bị bỏ qua kèm cảnh báo trong log.

Xem schema bảng đích:

```bash
uv run python -m scripts.inspect_notion --database-id "<URL bảng đích>"
```
