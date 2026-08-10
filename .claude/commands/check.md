---
description: Chạy toàn bộ lint / typecheck / test cho backend, frontend và infra
---

Chạy tuần tự các bước kiểm tra dưới đây, báo cáo gọn kết quả từng phần
(PASS/FAIL + lỗi thực tế nếu có). Nếu một phần chưa cài dependency thì ghi rõ
"skipped — chưa cài", đừng coi là pass.

```bash
cd backend  && uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run pytest
cd frontend && npm run lint && npm run typecheck && npm run build
cd infra    && terraform fmt -check -recursive && terraform validate
```

Sau khi chạy xong: tóm tắt các lỗi cần sửa, ưu tiên lỗi chặn build trước.
