# nexlab-recruit — scan CV

Trích xuất thông tin ứng viên từ CV, chạy theo lô trên Google Cloud.

```
Tally (form trên website)  →  Notion "Job Application"   ← nguồn, có sẵn
                                        │
        ┌───────────────────────────────┤
        │  Cloud Scheduler 18:00        │  HR bấm nút ở /admin
        └───────────────► Cloud Run Job ◄┘
                                │
        [đơn nguồn] − [Source ID đã có ở bảng đích]   ← phép trừ tập hợp
                                │
        tải CV → markitdown → Markdown → Vertex AI (1 call) → JSON
                                │
        Notion "Candidate CV Scan Results"  ← mapping tĩnh, KHÔNG LLM
```

Trả về: **Applied Job · University · GPA · Experience · Skill · Certificate · Language**

## Cấu trúc

```
backend/             Web service (/admin) + Cloud Run Job — Python 3.11, DDD / Clean Architecture
infra/               Terraform — Cloud Run service, job, scheduler, secrets (GCP)
.github/workflows/   CI + deploy
CLAUDE.md            hướng dẫn cho Claude Code
AGENT.md             hướng dẫn chung cho mọi AI coding agent
```

## Bắt đầu

```bash
cd backend
cp .env.example .env                    # điền NOTION_API_KEY, ADMIN_PASSWORD...
gcloud auth application-default login   # Gemini dùng ADC, không cần API key
uv sync --all-extras

uv run python main.py                             # trang HR: localhost:8000/admin
uv run python -m app.interface.jobs.scan_pending --limit 2   # chạy thử job
```

Chi tiết: [backend/README.md](backend/README.md) · [infra/README.md](infra/README.md) ·
[.github/workflows/README.md](.github/workflows/README.md)

## Nguyên tắc thiết kế

**Một lần gọi LLM duy nhất**, ở bước trích xuất field từ Markdown. Việc ghi sang Notion
là mapping tĩnh trong code — cùng đầu vào luôn ra cùng payload.

**Không có database, không có checkpoint.** Cột `Source ID` trên bảng đích chính là bộ
nhớ. Mỗi lượt chạy đọc lại cả hai bảng rồi trừ nhau, nên chạy lại bao nhiêu lần cũng
không tạo dòng trùng, CV lỗi tự được nhặt lại ở lượt sau, và CV về muộn không bị sót.

**Một CV hỏng không làm chết cả lượt.** Nó vào báo cáo lỗi và được thử lại lần sau.
