"""HTML cho trang quản trị. Không framework, không build step — một file là đủ."""

from __future__ import annotations

from html import escape

_STYLE = """
:root { color-scheme: light dark; --fg:#1a1a1a; --bg:#fafafa; --card:#fff;
        --line:#e4e4e7; --muted:#6b7280; --accent:#2563eb; }
@media (prefers-color-scheme: dark) {
  :root { --fg:#ededed; --bg:#0f1115; --card:#181b21; --line:#2a2f38; --muted:#9ca3af; }
}
* { box-sizing: border-box; }
body { margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
       background:var(--bg); color:var(--fg); padding:24px;
       font-family: ui-sans-serif, system-ui, "Segoe UI", sans-serif; }
.card { background:var(--card); border:1px solid var(--line); border-radius:14px;
        padding:32px; width:100%; max-width:460px; }
h1 { font-size:19px; margin:0 0 4px; }
p.sub { color:var(--muted); font-size:13px; margin:0 0 24px; }
.count { font-size:44px; font-weight:650; line-height:1.1; }
.count-label { color:var(--muted); font-size:13px; margin-top:2px; }
button, input { font:inherit; }
button { width:100%; margin-top:22px; padding:11px 16px; border:0; border-radius:9px;
         background:var(--accent); color:#fff; font-weight:600; cursor:pointer; }
button:disabled { opacity:.45; cursor:not-allowed; }
input { width:100%; padding:10px 12px; border:1px solid var(--line); border-radius:9px;
        background:transparent; color:var(--fg); }
.status { margin-top:18px; padding:12px 14px; border-radius:9px; background:var(--bg);
          border:1px solid var(--line); font-size:13px; white-space:pre-line; }
.err { color:#dc2626; font-size:13px; margin-top:12px; }
label { display:block; font-size:13px; color:var(--muted); margin-bottom:6px; }
"""


def render_login(error: str = "") -> str:
    problem = f'<p class="err">{escape(error)}</p>' if error else ""
    return f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Quét CV — Đăng nhập</title><style>{_STYLE}</style></head>
<body><div class="card">
  <h1>Quét CV ứng viên</h1>
  <p class="sub">Nhập mật khẩu để tiếp tục.</p>
  <form method="post" action="/admin/login">
    <label for="password">Mật khẩu</label>
    <input id="password" name="password" type="password" autofocus required>
    {problem}
    <button type="submit">Vào</button>
  </form>
</div></body></html>"""


def render_page() -> str:
    return f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Quét CV ứng viên</title><style>{_STYLE}</style></head>
<body><div class="card">
  <h1>Quét CV ứng viên</h1>
  <p class="sub">Chỉ xử lý những CV chưa có trong bảng kết quả.
     Bấm nhiều lần không tạo dòng trùng.</p>

  <div class="count" id="count">…</div>
  <div class="count-label">CV chưa xử lý</div>

  <button id="run" disabled>Đang kiểm tra…</button>
  <div class="status" id="status" hidden></div>
</div>
<script>
const $ = (id) => document.getElementById(id);
let timer = null;

async function refresh() {{
  try {{
    const r = await fetch('/admin/pending');
    const d = await r.json();
    if (d.error) throw new Error(d.error);
    $('count').textContent = d.pending;
    $('run').disabled = d.pending === 0;
    const label = d.pending === 0 ? 'Không có CV mới' : `Xử lý ${{d.pending}} CV mới`;
    $('run').textContent = label;
  }} catch (e) {{
    $('count').textContent = '—';
    show('Không đếm được: ' + e.message);
  }}
}}

function show(text) {{ const s = $('status'); s.hidden = false; s.textContent = text; }}

async function poll(execution) {{
  const r = await fetch('/admin/status?execution=' + encodeURIComponent(execution));
  const d = await r.json();
  if (d.error) {{ show('Lỗi: ' + d.error); clearInterval(timer); return; }}
  show(`${{d.label}} — thành công ${{d.succeeded}}, lỗi ${{d.failed}}`);
  if (d.finished) {{
    clearInterval(timer);
    $('run').disabled = false;
    refresh();
  }}
}}

$('run').addEventListener('click', async () => {{
  $('run').disabled = true;
  show('Đang khởi động…');
  try {{
    const r = await fetch('/admin/run', {{ method: 'POST' }});
    const d = await r.json();
    if (d.error) throw new Error(d.error);
    show('Đã khởi động. Đang chạy nền, có thể đóng trang này.');
    timer = setInterval(() => poll(d.execution), 5000);
  }} catch (e) {{
    show('Không khởi động được: ' + e.message);
    $('run').disabled = false;
  }}
}});

refresh();
</script></body></html>"""
