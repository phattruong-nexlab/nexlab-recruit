# AGENT.md

Hướng dẫn chung cho mọi AI coding agent làm việc trên repo `nexlab-recruit`.

> Claude Code: xem thêm [CLAUDE.md](CLAUDE.md) — chi tiết hơn về workflow.

## Bối cảnh

Service **scan CV** chạy như **MCP server**. Agent Notion gọi tool `parse_cv` với link
file CV + vài field từ đơn ứng tuyển; service trả về thông tin đã trích xuất và ghi
một dòng vào bảng Notion đích.

## Bản đồ thư mục

| Thư mục | Nội dung |
|---|---|
| `backend/app/domain/` | Entity, value object, domain service — pure Python |
| `backend/app/application/` | Use case `ParseCvUseCase` + ports (ABC) |
| `backend/app/infrastructure/` | Adapters: httpx, markitdown, Gemini, Notion |
| `backend/app/interface/mcp/` | MCP server, tool `parse_cv`, Bearer auth, DI |
| `backend/scripts/` | Script chạy tay: tải CV từ Notion về máy |
| `infra/` | Terraform cho Cloud Run |

## Nguyên tắc bắt buộc

1. **Hướng dependency**: `interface → application → domain`. `domain` chỉ import stdlib.
2. **Ports & adapters**: mọi truy cập hệ thống ngoài đi qua ABC trong `application/ports/`.
3. **Một lần gọi LLM**: chỉ trong `CvExtractor`. Mapping Notion là code thuần.
4. **Config tập trung**: đọc env duy nhất qua `backend/config.py`.
5. **Không bịa dữ liệu**: thiếu field thì `null` / `[]`.
6. **Ghi Notion lỗi ⇒ vẫn trả kết quả** phân tích cho agent.
7. **Secret không vào git**: chỉ commit `*.example`. CV đã tải (`backend/data/`) cũng không.

## Trước khi kết thúc một task

```bash
cd backend && uv run ruff check . && uv run mypy . && uv run pytest
cd infra   && terraform fmt -check -recursive && terraform validate
```

## Ngoài phạm vi (đừng tự ý thêm)

Frontend · database / persistence · OCR cho CV scan ảnh · embedding / semantic search ·
đọc ngược dữ liệu từ Notion · multi-agent hay ADK · gọi LLM ở bước ngoài extraction.
