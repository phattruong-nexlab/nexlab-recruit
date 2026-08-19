# nexlab-recruit — trích nội dung CV

Đọc CV của các đơn ứng tuyển rồi ghi text vào cột `Resume Content` của chính dòng đó
trên Notion. Từ đó người hay AI đọc được nội dung CV mà không phải mở PDF.

```
Tally (form website)  →  Notion "Job Application"      ← một bảng duy nhất
                                    │
        ┌───────────────────────────┤
        │  Cloud Scheduler 02:00    │  HR bấm nút ở /admin
        └────────► Cloud Run Job ◄──┘
                        │
        dòng có CV và `Resume Content` còn rỗng
                        │
        tải PDF  →  markitdown  →  text
                        └ PDF scan (text < 200 ký tự) → Gemini 2.5 Flash đọc ảnh
                        │
        pages.update: ghi text vào `Resume Content` của chính dòng đó
```

**Thư viện trước, LLM sau.** markitdown xử lý phần lớn CV; chỉ PDF dạng ảnh scan mới
gọi Gemini — OCR tốn tiền nên không dùng khi không cần.

## Vì sao ghi text chứ không upload file

CV trong Notion là `type: external` trỏ sang `storage.tally.so` — connector của Claude
chỉ mở được file do Notion quản lý nên bó tay. Ghi thẳng **text** vào một cột rich_text
giải quyết triệt để: Claude, HR, hay bất kỳ công cụ nào đọc Notion đều thấy nội dung,
không cần mở PDF, không tốn dung lượng lưu trữ Notion.

## Cấu trúc

```
backend/             Web service (/admin) + Cloud Run Job — Python 3.11
infra/               Terraform — Cloud Run service, job, scheduler, secrets (GCP)
.github/workflows/   CI + deploy
CLAUDE.md            hướng dẫn cho Claude Code
AGENT.md             hướng dẫn chung cho mọi AI coding agent
```

## Bắt đầu

```bash
cd backend
cp .env.example .env                    # điền NOTION_API_KEY, ADMIN_PASSWORD...
gcloud auth application-default login   # Vertex AI + Cloud Run API dùng ADC
uv sync --all-extras

uv run python main.py                                       # localhost:8000/admin
uv run python -m app.interface.jobs.extract_content --limit 3   # chạy thử job
```

Chi tiết: [backend/README.md](backend/README.md) · [infra/README.md](infra/README.md) ·
[.github/workflows/README.md](.github/workflows/README.md)

## Nguyên tắc thiết kế

**Không có database, không có checkpoint.** Cột `Resume Content` rỗng hay không chính là
dấu hiệu đã xử lý. Chạy lại bao nhiêu lần cũng không ghi đè cái đã xong, CV lỗi tự được
nhặt lại ở lượt sau, CV về muộn không bị sót.

**Một CV hỏng không làm chết cả lượt.** Nó vào báo cáo lỗi và được thử lại lần sau.

**HR tự chủ.** Đổi giờ chạy tự động và kích hoạt ngay đều làm được từ `/admin`,
không cần vào Cloud Console.
