# Backend — nexlab scan-cv

Python 3.11, kiến trúc **DDD / Clean Architecture**. Một image, hai entrypoint:

| Entrypoint | Chạy ở đâu | Việc |
|---|---|---|
| `main.py` (Starlette) | Cloud Run **Service** | Trang `/admin` cho HR bấm nút, `/health` |
| `app.interface.jobs.scan_pending` | Cloud Run **Job** | Quét CV chưa xử lý rồi ghi Notion |

Service **không** làm việc nặng — nút bấm chỉ kích hoạt job qua Cloud Run Admin API
rồi hỏi tiến độ.

## Luồng xử lý

```
[đơn nguồn có CV] − [Source ID đã có ở bảng đích]     ← phép trừ tập hợp
        │
        └→ tải file → markitdown → Markdown → Vertex AI (1 call) → JSON
                                                                    │
                             Notion (bảng đích) ← mapping tĩnh ←────┘
```

LLM chỉ được gọi **đúng một lần**, ở bước trích xuất. Mapping sang Notion là code thuần
trong `infrastructure/notion/property_mapping.py`.

Không có checkpoint: cột `Source ID` trên bảng đích là bộ nhớ duy nhất. Chạy lại bao
nhiêu lần cũng không tạo dòng trùng.

## Cấu trúc

```
backend/
├── main.py                     # Starlette: /admin + /health
├── config.py                   # Settings — nơi DUY NHẤT đọc env
├── app/
│   ├── domain/                 # ❶ Pure Python: Candidate, Experience, value object
│   ├── application/            # ❷ Use case + ports
│   │   ├── ports/              #    CvDownloader · CvReader · CvExtractor
│   │   │                       #    CandidatePublisher · ApplicationSource
│   │   └── use_cases/          #    ParseCvUseCase · ScanPendingUseCase
│   ├── infrastructure/         # ❸ Adapters
│   │   ├── http/               #    tải file (chặn SSRF, giới hạn dung lượng)
│   │   ├── reader/             #    markitdown → Markdown
│   │   ├── llm/                #    Vertex AI structured output
│   │   ├── notion/             #    đọc bảng nguồn, ghi bảng đích, mapping property
│   │   └── gcp/                #    kích hoạt Cloud Run Job
│   └── interface/
│       ├── dependencies.py     # ❹ composition root
│       ├── jobs/               #    entrypoint Cloud Run Job
│       └── web/                #    trang quản trị (HTML render từ server)
├── scripts/                    # script chạy tay: tải CV từ Notion về máy
└── tests/
```

## Chạy local

```bash
cp .env.example .env
gcloud auth application-default login   # Vertex AI dùng ADC, không cần API key
uv sync --all-extras

uv run python main.py                   # http://localhost:8000/admin
uv run python -m app.interface.jobs.scan_pending --limit 2
```

`--limit` để thử vài CV trước khi chạy cả lượt.

## Kiểm tra

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy .
uv run pytest
```

## Cấu hình bảng Notion đích

`FIELD_TO_COLUMN` trong `app/infrastructure/notion/property_mapping.py` quyết định field
nào vào cột nào. Dạng payload tự khớp theo **kiểu** của cột — đổi kiểu cột trên Notion
không phải sửa code. Cột không tồn tại bị bỏ qua kèm cảnh báo trong log; cột Notion tự
sinh (`created_time`, `formula`, `rollup`...) bị chặn vì ghi vào sẽ lỗi 400.

Bảng đích **bắt buộc** có cột `Source ID` (rich_text) — thiếu nó thì mỗi lượt chạy sẽ
xử lý lại từ đầu và tạo dòng trùng.

Xem schema:

```bash
uv run python -m scripts.inspect_notion --database-id "<URL bảng>"
```
