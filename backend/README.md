# Backend — nexlab đồng bộ CV

Python 3.11, kiến trúc **DDD / Clean Architecture**. Một image, hai entrypoint:

| Entrypoint | Chạy ở đâu | Việc |
|---|---|---|
| `main.py` (Starlette) | Cloud Run **Service** | Trang `/admin` cho HR bấm nút, `/health` |
| `app.interface.jobs.mirror_rows` | Cloud Run **Job** | Nhân bản đơn sang bảng gương + upload CV |

Service **không** làm việc nặng — nút bấm chỉ kích hoạt job qua Cloud Run Admin API
rồi hỏi tiến độ.

## Luồng xử lý

```
[đơn nguồn] − [Source ID đã có ở bảng gương]     ← phép trừ tập hợp
        │
        ├→ tải PDF từ Tally
        ├→ file_uploads.create → send            ← đưa file vào Notion
        └→ pages.create: chép 64 cột + Resume(type:file) + Source ID
```

Không gọi LLM. Chép property là code thuần trong
`infrastructure/notion/property_copier.py`.

Không có checkpoint: cột `Source ID` trên bảng gương là bộ nhớ duy nhất.

## Cấu trúc

```
backend/
├── main.py                     # Starlette: /admin + /health
├── config.py                   # Settings — nơi DUY NHẤT đọc env
├── app/
│   ├── domain/                 # ❶ Pure Python: exceptions
│   ├── application/            # ❷ Use case + ports
│   │   ├── ports/              #    CvDownloader · ApplicationSource · RowMirror
│   │   └── use_cases/          #    MirrorApplicationsUseCase
│   ├── infrastructure/         # ❸ Adapters
│   │   ├── http/               #    tải file (chặn SSRF, giới hạn dung lượng)
│   │   ├── notion/             #    đọc nguồn, chép property, upload file, tạo dòng
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
uv run python -m app.interface.jobs.mirror_rows --limit 5
```

`--limit` để thử vài dòng trước khi chạy cả lượt.

## Kiểm tra

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy .
uv run pytest
```

## Cấu hình bảng gương

Bảng gương phải có cột **trùng tên và trùng kiểu** với bảng nguồn — cột nào lệch sẽ bị
bỏ qua kèm cảnh báo trong log, không làm hỏng cả dòng. Ngoài ra bắt buộc có:

| Cột | Kiểu | Việc |
|---|---|---|
| `Source ID` | rich_text | Khoá chống trùng. Thiếu nó thì mỗi lượt nhân bản lại từ đầu. |
| `Resume` | files | Nơi đặt CV do Notion lưu (`type: file`). |

Cột Notion tự sinh (`created_time`, `formula`, `rollup`...) bị bỏ qua vì ghi vào sẽ lỗi
400. Lưu ý `Created time` ở bảng gương là **lúc nhân bản**, không phải lúc nộp đơn.

Xem schema:

```bash
uv run python -m scripts.inspect_notion --database-id "<URL bảng>"
```
