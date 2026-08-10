# Feature Spec — CV Extraction Pilot (nexlab)

> Tài liệu này dùng để đưa cho **Claude Code** triển khai. Mọi quyết định kiến trúc đã được chốt; phần cuối có checklist và các câu hỏi mở cần xác nhận trước khi code.

---

## 1. Mục tiêu

Xây dựng tính năng **trích xuất thông tin ứng viên từ CV (PDF)** → lưu vào **Supabase** (source of truth) → đẩy lên **Notion** (view cho HR thao tác).

Đây là **pilot đầu tiên**, cố ý giữ ĐƠN GIẢN: **1 LLM call + structured output**, KHÔNG dùng multi-agent, KHÔNG dùng ADK ở giai đoạn này (lý do ở mục 9).

---

## 2. Phạm vi (Scope)

### ✅ In scope
- Input: file CV định dạng **PDF** (text-based, không phải scan ảnh — xem mục Câu hỏi mở).
- Trích xuất 3 nhóm field:
  - **Trường đại học** (university)
  - **Kinh nghiệm** — tách theo từng job, mỗi job gồm: tên công ty, năm bắt đầu, năm kết thúc, mô tả công việc.
  - **Skills** — danh sách kỹ năng.
- Lưu vào Supabase (2 bảng: `candidates`, `experiences`).
- Đẩy bản ghi lên 1 Notion database đã format sẵn.
- Đồng bộ **1 chiều**: Supabase → Notion.

### 🚫 Out of scope (giai đoạn này)
- OCR cho CV dạng ảnh scan.
- Semantic search / embedding (thiết kế sẵn cột `embedding` nhưng CHƯA implement).
- Đồng bộ 2 chiều Notion → Supabase.
- Matching / ranking / chấm điểm ứng viên (đây là feature sau, mới cần multi-agent).
- Xử lý batch quy mô lớn / queue (pilot chỉ cần xử lý tuần tự từng file).

---

## 3. Kiến trúc & luồng dữ liệu

```
CV PDF
  │
  ▼
[1] Parse PDF → plain text        (PyMuPDF hoặc pdfplumber)
  │
  ▼
[2] LLM extract (Gemini)          (1 call + JSON schema → structured output)
  │
  ▼
[3] Validate + normalize          (kiểm tra năm hợp lệ, chuẩn hoá dữ liệu)
  │
  ▼
[4] Ghi Supabase (candidates + experiences)   ← GHI TRƯỚC (source of truth)
  │
  ▼
[5] Đẩy lên Notion (tạo page trong database)   ← GHI SAU (nếu lỗi vẫn còn bản gốc)
  │
  ▼
[6] Lưu notion_page_id ngược lại Supabase       (để map 2 hệ về sau)
```

**Nguyên tắc quan trọng:** bước [4] Supabase phải thành công trước khi [5] Notion. Nếu [5] lỗi → không rollback [4], chỉ log lỗi + cho phép retry đẩy Notion sau. Không được để mất dữ liệu gốc.

---

## 4. Tech stack

| Thành phần | Lựa chọn | Ghi chú |
|---|---|---|
| Ngôn ngữ | Python 3.10+ | |
| Parse PDF | `pymupdf` (fitz) | Nhanh, ổn định cho text-based PDF. Fallback `pdfplumber` nếu layout phức tạp. |
| LLM | **Gemini** (google-genai SDK) | Dùng structured output / JSON mode. Có free tier. |
| Database | **Supabase** (Postgres + pgvector) | Free tier đủ dùng. pgvector bật sẵn nhưng chưa dùng ở pilot. |
| Supabase client | `supabase-py` | |
| Notion | Notion API (`notion-client`) | Đẩy dữ liệu vào database đã có sẵn. |
| Config | `.env` + `pydantic-settings` | Giữ secret ngoài code. |

**Lưu ý về ADK:** pilot này KHÔNG dùng ADK. Nhưng nên viết phần LLM call tách rời (1 module `extractor.py` độc lập) để sau này dễ bọc vào ADK Tool nếu nâng cấp lên agent. Xem mục 9.

---

## 5. Schema Supabase

```sql
-- Bảng ứng viên
create table candidates (
  id uuid primary key default gen_random_uuid(),
  full_name text,
  university text,
  skills text[],                    -- mảng skill
  raw_cv_text text,                 -- text gốc, để re-extract nếu cần
  source_file text,                 -- tên/đường dẫn file CV gốc
  notion_page_id text,              -- map tới trang Notion
  embedding vector(1536),           -- ĐỂ TRỐNG ở pilot, bật khi làm semantic search
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Bảng kinh nghiệm (1 candidate : nhiều experience)
create table experiences (
  id uuid primary key default gen_random_uuid(),
  candidate_id uuid references candidates(id) on delete cascade,
  company text,                     -- "Wow Entertainment"
  start_year int,                   -- 2025
  end_year int,                     -- 2026 (null nếu đang làm)
  is_current boolean default false, -- true nếu đang làm việc
  description text,                 -- mô tả công việc
  order_index int                   -- thứ tự xuất hiện trong CV
);

-- Index chuẩn bị cho semantic search sau này (chưa cần chạy ở pilot)
-- create index on candidates using hnsw (embedding vector_cosine_ops);
```

**Lý do tách `experiences` thành bảng riêng** (không nhét JSON vào 1 cột): yêu cầu "phân tích rõ theo từng job, từng năm" → tách bảng cho phép query "ai từng làm ở công ty X", "ai có >N năm kinh nghiệm" dễ dàng về sau.

---

## 6. JSON Schema cho LLM extraction

Ép Gemini trả về đúng cấu trúc này (dùng structured output / response schema):

```json
{
  "full_name": "string | null",
  "university": "string | null",
  "skills": ["string"],
  "experiences": [
    {
      "company": "string",
      "start_year": "integer | null",
      "end_year": "integer | null",
      "is_current": "boolean",
      "description": "string"
    }
  ]
}
```

### Yêu cầu prompt cho extraction
- Nếu không tìm thấy field → trả `null` (với string) hoặc `[]` (với array), KHÔNG bịa.
- Với kinh nghiệm: tách riêng từng job, mỗi job 1 object. Nếu CV ghi "2025 - hiện tại" → `end_year: null`, `is_current: true`.
- `description` giữ nguyên nội dung mô tả công việc từ CV, tóm gọn nếu quá dài nhưng KHÔNG thêm thông tin không có trong CV.
- Nếu năm không rõ (chỉ ghi tháng, hoặc mơ hồ) → để `null`, không đoán bừa.


## 11. Câu hỏi mở cần xác nhận trước/trong khi code

1. **CV scan ảnh:** pilot có cần xử lý CV là ảnh scan (cần OCR) không? → Hiện đang giả định CHỈ PDF text-based. Nếu có scan, cần thêm bước OCR (out of scope hiện tại).
2. **Notion database schema:** bảng Notion đã format sẵn có những cột (properties) gì? Cần map chính xác field → property. Kinh nghiệm nhiều job sẽ hiển thị thế nào trên Notion (gộp 1 cột text, hay Notion sub-items)?
3. **Dedup:** khi 1 ứng viên nộp CV 2 lần, xử lý ra sao — tạo mới, ghi đè, hay báo trùng? Dựa vào field nào để nhận diện trùng (tên? email?)?
4. **Email/liên hệ:** có cần trích thêm email/SĐT ứng viên không? (Spec hiện chỉ có ĐH/kinh nghiệm/skill — nhưng email thường cần để dedup và liên hệ.)
5. **Ngôn ngữ CV:** CV tiếng Việt, tiếng Anh, hay cả hai? Ảnh hưởng tới prompt extraction.
6. **Volume:** pilot xử lý bao nhiêu CV (vài chục để test, hay ngay lập tức hàng trăm)? Ảnh hưởng tới việc có cần rate-limit/batch không.
