# Backend — nexlab trích nội dung CV

Python 3.11, kiến trúc **DDD / Clean Architecture**. Một image, hai entrypoint:

| Entrypoint | Chạy ở đâu | Việc |
|---|---|---|
| `main.py` (Starlette) | Cloud Run **Service** | Trang `/admin` cho HR bấm nút, `/health` |
| `app.interface.jobs.extract_content` | Cloud Run **Job** | Đọc CV rồi ghi text vào `Resume Content` |

Service **không** làm việc nặng — nút bấm chỉ kích hoạt job qua Cloud Run Admin API
rồi hỏi tiến độ.

## Luồng xử lý

```
dòng có CV và `Resume Content` còn rỗng
        │
        ├→ tải PDF từ Tally
        ├→ markitdown → text
        │     └ text < 200 ký tự (PDF scan) → Gemini 2.5 Flash đọc ảnh
        └→ pages.update: ghi vào `Resume Content` của chính dòng đó
```

Thư viện trước, LLM sau — OCR chỉ chạy khi markitdown không moi được text.

Không có checkpoint: cột `Resume Content` rỗng hay không chính là dấu hiệu đã xử lý.

## Cấu trúc

```
backend/
├── main.py                     # Starlette: /admin + /health
├── config.py                   # Settings — nơi DUY NHẤT đọc env
├── app/
│   ├── domain/                 # ❶ Pure Python: exceptions
│   ├── application/            # ❷ Use case + ports
│   │   ├── ports/              #    CvDownloader · CvReader · CvOcr
│   │   │                       #    ApplicationSource · ResumeContentWriter
│   │   └── use_cases/          #    ExtractResumeContentUseCase
│   ├── infrastructure/         # ❸ Adapters
│   │   ├── http/               #    tải file (chặn SSRF, giới hạn dung lượng)
│   │   ├── reader/             #    markitdown → text
│   │   ├── llm/                #    Gemini OCR cho PDF scan (Vertex AI)
│   │   ├── notion/             #    tìm dòng cần xử lý, ghi Resume Content
│   │   └── gcp/                #    kích hoạt Cloud Run Job, đổi lịch Scheduler
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
gcloud auth application-default login   # gọi Cloud Run/Scheduler API bằng ADC
uv sync --all-extras

uv run python main.py                   # http://localhost:8000/admin
uv run python -m app.interface.jobs.extract_content --limit 3
```

`--limit` để thử vài CV trước khi chạy cả lượt.

## Kiểm tra

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy .
uv run pytest
```

## Cấu hình bảng Notion

Mỗi bảng nguồn cần đúng hai cột dưới đây (cộng `Created time` và `Job URL` để lọc).
Khai nhiều bảng bằng cách ngăn cách id với dấu phẩy trong
`NOTION_SOURCE_DATA_SOURCE_IDS`; luồng xử lý đọc song song rồi gộp kết quả.

| Cột | Kiểu | Việc |
|---|---|---|
| `Resume, CL` | files | CV do Tally đổ vào (link `external`) |
| `Resume Content` | rich_text | Nơi ghi text đã trích. Rỗng = chưa xử lý. |

Notion giới hạn 2000 ký tự mỗi text object nên nội dung dài được cắt thành nhiều mảnh
trong cùng property; tối đa 100 mảnh (200.000 ký tự).

Xem schema:

```bash
uv run python -m scripts.inspect_notion --database-id "<URL bảng>"
```
