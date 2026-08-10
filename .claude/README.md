# .claude/

Cấu hình Claude Code cho repo này.

| File / thư mục | Vai trò |
|---|---|
| `settings.json` | Cấu hình dùng chung, **commit vào git**. Allowlist các lệnh đọc/kiểm tra an toàn; chặn đọc secret và chặn `terraform apply/destroy`. |
| `settings.local.json` | Cấu hình cá nhân, **không commit** (đã có trong `.gitignore`). |
| `commands/` | Slash command tự định nghĩa (`/<tên-file>`). |
| `agents/` | Subagent tự định nghĩa. |

Hướng dẫn kiến trúc và quy ước code nằm ở [../CLAUDE.md](../CLAUDE.md).
