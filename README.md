# nexlab-recruit — đồng bộ CV ứng viên

Nhân bản đơn ứng tuyển từ Notion sang bảng gương, kèm CV **upload thẳng vào Notion**
để connector của Claude mở được file.

```
Tally (form website)  →  Notion "Job Application"      ← nguồn, có sẵn
                                    │
        ┌───────────────────────────┤
        │  Cloud Scheduler 02:00    │  HR bấm nút ở /admin
        └────────► Cloud Run Job ◄──┘
                        │
        [đơn nguồn] − [Source ID đã có ở bảng gương]   ← phép trừ tập hợp
                        │
        tải PDF từ Tally  →  upload vào Notion  →  tạo dòng: 64 cột + Resume
                        │
        Notion "Job Application (1)"   ← Resume là type:file, Claude đọc được
```

**Không đọc nội dung CV, không gọi LLM.** Toàn bộ là chép giá trị property.

## Vì sao phải upload lại file

CV trong bảng nguồn là `type: external` — Notion chỉ giữ link trỏ sang
`storage.tally.so`, không lưu file. Connector Notion của Claude chỉ tải được file
do **Notion quản lý**, nên gặp `external` là bó tay. Đổi sang GCS cũng vô ích vì
vẫn là link ngoài. Chỉ upload vào Notion mới đổi được `type` thành `file`.

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
gcloud auth application-default login   # gọi Cloud Run/Scheduler API bằng ADC
uv sync --all-extras

uv run python main.py                                       # localhost:8000/admin
uv run python -m app.interface.jobs.mirror_rows --limit 5   # chạy thử job
```

Chi tiết: [backend/README.md](backend/README.md) · [infra/README.md](infra/README.md) ·
[.github/workflows/README.md](.github/workflows/README.md)

## Nguyên tắc thiết kế

**Không có database, không có checkpoint.** Cột `Source ID` trên bảng gương chính là
bộ nhớ. Mỗi lượt đọc lại cả hai bảng rồi trừ nhau — chạy lại bao nhiêu lần cũng không
tạo dòng trùng, dòng lỗi tự được nhặt lại, đơn về muộn không bị sót.

**Một dòng hỏng không làm chết cả lượt.** Tải CV lỗi thì vẫn chép các cột còn lại.

**HR tự chủ.** Đổi giờ chạy tự động và kích hoạt ngay đều làm được từ `/admin`,
không cần vào Cloud Console.
