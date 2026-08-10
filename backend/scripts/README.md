# scripts/

Script chạy tay, không thuộc runtime của API.

| Script | Việc |
|---|---|
| `inspect_notion.py` | Xem integration được share những database nào, property nào chứa file |
| `download_notion_files.py` | Tải toàn bộ file đính kèm của một database về local |

## Cần cấp quyền gì trước khi chạy

Notion API **không** dùng tài khoản đăng nhập của bạn — phải tạo một integration riêng:

1. Vào <https://www.notion.so/my-integrations> → **New integration**
   - Associated workspace: `nexlabtechnology`
   - Capabilities: chỉ cần **Read content** (không cần insert/update cho việc tải về)
2. Copy **Internal Integration Secret** (dạng `ntn_...`) vào `backend/.env`:
   ```
   NOTION_API_KEY=ntn_xxxxxxxxxxxx
   NOTION_DATABASE_ID=25d2c7d6a903802da4a8cba604f09689
   ```
3. **Share database cho integration** — bước hay bị quên nhất. Mở database trên Notion →
   nút `•••` góc phải trên → **Connections** → chọn integration vừa tạo.
   Thiếu bước này API sẽ trả `object_not_found` dù id đúng.

Token này nằm trong `.env` trên máy bạn, đã được `.gitignore` chặn commit.

## Chạy

```bash
cd backend

# 1) Xem integration thấy database nào
uv run python -m scripts.inspect_notion

# 2) Xem schema database (property nào là Files & media)
uv run python -m scripts.inspect_notion --database-id "https://app.notion.com/p/nexlabtechnology/25d2c7d6a903802da4a8cba604f09689?v=..."

# 3) Liệt kê file sẽ tải, chưa tải
uv run python -m scripts.download_notion_files --dry-run

# 4) Tải thật
uv run python -m scripts.download_notion_files --output-dir ./data/cv

# CV nằm sâu trong trang (toggle/column/sub-page lồng nhau):
uv run python -m scripts.download_notion_files --max-depth 5 --output-dir ./data/cv

# Chỉ quét property, bỏ nội dung trang (nhanh hơn nhiều):
uv run python -m scripts.download_notion_files --skip-blocks
```

Mặc định script quét **cả hai chỗ**: property kiểu `Files & media` **và** nội dung từng
trang (đệ quy 3 cấp) — vì CV thường được đính thẳng vào trong trang chứ không nằm ở cột.

### Hai chế độ nguồn

| Cờ | Khi nào dùng | Notion API gọi |
|---|---|---|
| `--database-id` | Cần quét **mọi dòng** của một bảng | `databases.retrieve` → `data_sources.query` → `blocks.children.list` |
| `--page-id` | Chỉ cần **vài trang cụ thể** | `pages.retrieve` → `blocks.children.list` |

`--page-id` bỏ hẳn khâu query bảng nên không dính khái niệm data source, và lặp lại được
cho nhiều trang:

```bash
uv run python -m scripts.download_notion_files \
  --page-id "https://app.notion.com/p/ws/<page-1>" \
  --page-id "<page-2-id>" \
  --output-dir ./data/cv
```

Kết quả: file nằm trong `--output-dir`, kèm `manifest.json` ghi lại page nguồn của từng file.
Thư mục `backend/data/` đã được gitignore — CV là dữ liệu cá nhân, không commit.

## Lưu ý

- Link file Notion trả về **hết hạn sau ~1 giờ**. Script tải ngay trong lúc chạy;
  đừng lưu link lại để tải sau.
- Notion giới hạn ~3 request/giây, script đã tự nghỉ giữa các call. Quét nội dung trang
  tốn ít nhất 1 request/trang nên với vài trăm trang sẽ mất vài phút.
- Chạy lại sẽ bỏ qua file đã có; dùng `--overwrite` nếu muốn tải đè.
- **Bảng lồng được đi xuyên qua tự động.** Cấu trúc thật ở nexlab là 3 tầng:

  ```
  Job Post NEXLAB (bảng)
  └── "PM/BA Senior" (dòng = 1 trang)
      └── "Job Application for ..." (BẢNG LỒNG trong trang)
          └── "Ha Thi Ngoc Thao" (dòng = 1 ứng viên)  ← CV ở đây
  ```

  Script gặp bảng lồng thì query luôn bảng đó và quét từng ứng viên. Tắt bằng
  `--no-child-databases`. Có chống lặp vô hạn nếu các bảng nhúng chéo nhau.

## Vì sao không dùng Notion MCP

MCP server của Notion cũng cần đúng token và đúng bước share như trên — không đi vòng
được khâu cấp quyền. Ngoài ra nó trả nội dung dạng text cho hội thoại, không tải file nhị
phân hàng loạt, mà link file lại hết hạn sau 1 giờ. Với việc kéo vài trăm CV về đĩa thì
script trực tiếp gọn và lặp lại được hơn.
