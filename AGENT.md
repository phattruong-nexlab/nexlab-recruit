# AGENT.md

Hướng dẫn chung cho mọi AI coding agent làm việc trên repo `nexlab-recruit`.

> Claude Code: xem thêm [CLAUDE.md](CLAUDE.md) — chi tiết hơn về workflow.

## Bối cảnh

Service **scan CV** chạy theo lô. Cloud Run Job đối chiếu bảng đơn ứng tuyển với bảng
kết quả, xử lý CV chưa có rồi ghi vào bảng đích. Kích hoạt bằng Cloud Scheduler hoặc
bằng nút bấm trên trang `/admin` cho HR.

## Bản đồ thư mục

| Thư mục | Nội dung |
|---|---|
| `backend/app/domain/` | Entity, value object, domain service — pure Python |
| `backend/app/application/` | `ParseCvUseCase`, `ScanPendingUseCase` + ports (ABC) |
| `backend/app/infrastructure/` | Adapters: httpx, markitdown, Vertex AI, Notion, Cloud Run API |
| `backend/app/interface/jobs/` | Entrypoint cho Cloud Run Job |
| `backend/app/interface/web/` | Trang quản trị cho HR (HTML render từ server) |
| `backend/scripts/` | Script chạy tay: tải CV từ Notion về máy |
| `infra/` | Terraform |

## Nguyên tắc bắt buộc

1. **Hướng dependency**: `interface → application → domain`. `domain` chỉ import stdlib.
2. **Ports & adapters**: mọi truy cập hệ thống ngoài đi qua ABC trong `application/ports/`.
3. **Một lần gọi LLM**: chỉ trong `CvExtractor`. Mapping Notion là code thuần.
4. **Config tập trung**: đọc env duy nhất qua `backend/config.py`.
5. **Không bịa dữ liệu**: thiếu field thì `null` / `[]`.
6. **Đối chiếu bằng `Source ID`**, không dùng mốc thời gian.
7. **Một CV hỏng không làm chết cả lượt** — gom vào báo cáo, lượt sau nhặt lại.
8. **Secret không vào git**: chỉ commit `*.example`. CV đã tải (`backend/data/`) cũng không.

## Trước khi kết thúc một task

```bash
cd backend && uv run ruff check . && uv run mypy . && uv run pytest
cd infra   && terraform fmt -check -recursive && terraform validate
```

## Ngoài phạm vi (đừng tự ý thêm)

Frontend SPA · database / persistence · OCR cho CV scan ảnh · embedding / semantic
search · multi-agent hay ADK · gọi LLM ở bước ngoài extraction · checkpoint theo thời gian.
