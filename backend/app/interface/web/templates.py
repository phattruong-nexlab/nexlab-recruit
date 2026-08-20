"""HTML cho trang quản trị. Không framework, không build step — một file là đủ."""

from __future__ import annotations

from html import escape

_STYLE = """
:root { color-scheme: light dark; --fg:#1a1a1a; --bg:#fafafa; --card:#fff;
        --line:#e4e4e7; --muted:#6b7280; --accent:#2563eb; --err:#dc2626; }
@media (prefers-color-scheme: dark) {
  :root { --fg:#ededed; --bg:#0f1115; --card:#181b21; --line:#2a2f38; --muted:#9ca3af; }
}
* { box-sizing: border-box; }
body { margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
       background:var(--bg); color:var(--fg); padding:24px;
       font-family: ui-sans-serif, system-ui, "Segoe UI", sans-serif; }
.card { background:var(--card); border:1px solid var(--line); border-radius:14px;
        padding:32px; width:100%; max-width:480px; }
h1 { font-size:19px; margin:0 0 4px; }
h2 { font-size:12px; font-weight:600; color:var(--muted); margin:0 0 10px;
     text-transform:uppercase; letter-spacing:.05em; }
p.sub { color:var(--muted); font-size:13px; margin:0 0 22px; }
.count { font-size:44px; font-weight:650; line-height:1.1; }
.count-label { color:var(--muted); font-size:13px; margin-top:2px; }
button, input, select { font:inherit; }
button { width:100%; margin-top:20px; padding:11px 16px; border:0; border-radius:9px;
         background:var(--accent); color:#fff; font-weight:600; cursor:pointer; }
button.ghost { background:transparent; color:var(--accent); border:1px solid var(--line);
               margin-top:0; width:auto; padding:9px 14px; }
button:disabled { opacity:.45; cursor:not-allowed; }
input, select { width:100%; padding:10px 12px; border:1px solid var(--line);
                border-radius:9px; background:transparent; color:var(--fg); }
input[type=time] { width:auto; }
.field { position:relative; }
.field input { padding-right:44px; }
.peek { position:absolute; right:6px; top:50%; transform:translateY(-50%);
        width:32px; height:32px; margin:0; padding:0; display:flex;
        align-items:center; justify-content:center; background:transparent;
        border:0; border-radius:7px; color:var(--muted); cursor:pointer; }
.peek:hover { color:var(--fg); }
.peek svg { width:18px; height:18px; }
.note { margin-top:14px; font-size:13px; color:var(--muted); }
.alert { margin-top:14px; padding:12px 14px; border-radius:9px; font-size:13px;
         white-space:pre-line; border:1px solid var(--err); color:var(--err); }
.err { color:#dc2626; font-size:13px; margin-top:12px; }
label { display:block; font-size:12px; color:var(--muted); margin-bottom:5px; }
hr { border:0; border-top:1px solid var(--line); margin:24px 0 18px; }
.row { display:flex; gap:10px; align-items:center; }
.grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.hint { color:var(--muted); font-size:12px; margin-top:8px; }
"""


# Icon vẽ thẳng bằng SVG: không tải font icon hay ảnh từ ngoài, trang vẫn tự chứa.
_EYE = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z"/>'
    '<circle cx="12" cy="12" r="3"/></svg>'
)
_EYE_OFF = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M10.6 6.1A9.9 9.9 0 0 1 12 6c6.4 0 10 7 10 7a17 17 0 0 1-2.7 3.6"/>'
    '<path d="M6.6 6.6A17 17 0 0 0 2 13s3.6 7 10 7a9.6 9.6 0 0 0 5-1.4"/>'
    '<path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/><path d="m3 3 18 18"/></svg>'
)


def render_login(error: str = "") -> str:
    problem = f'<p class="err">{escape(error)}</p>' if error else ""
    return f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Trích nội dung CV — Đăng nhập</title><style>{_STYLE}</style></head>
<body><div class="card">
  <h1>Trích nội dung CV</h1>
  <p class="sub">Nhập mật khẩu để tiếp tục.</p>
  <form method="post" action="/admin/login">
    <label for="password">Mật khẩu</label>
    <div class="field">
      <input id="password" name="password" type="password" autofocus required>
      <button type="button" id="peek" class="peek"
              aria-label="Hiện mật khẩu" aria-pressed="false" title="Hiện mật khẩu">
        {_EYE}
      </button>
    </div>
    {problem}
    <button type="submit">Vào</button>
  </form>
</div>
<script>
const input = document.getElementById('password');
const peek = document.getElementById('peek');
const EYE = `{_EYE}`;
const EYE_OFF = `{_EYE_OFF}`;

peek.addEventListener('click', () => {{
  const hidden = input.type === 'password';
  input.type = hidden ? 'text' : 'password';
  peek.innerHTML = hidden ? EYE_OFF : EYE;
  peek.setAttribute('aria-pressed', String(hidden));
  const label = hidden ? 'Ẩn mật khẩu' : 'Hiện mật khẩu';
  peek.setAttribute('aria-label', label);
  peek.title = label;
  // Giữ con trỏ ở cuối chuỗi, tránh nhảy về đầu khi đổi type.
  input.focus();
  const end = input.value.length;
  input.setSelectionRange(end, end);
}});
</script></body></html>"""


def render_page() -> str:
    return f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Trích nội dung CV</title><style>{_STYLE}</style></head>
<body><div class="card">
  <h1>Trích nội dung CV</h1>
  <p class="sub">Đọc CV rồi ghi text vào cột <code>Resume Content</code>.
     CV đã có nội dung sẽ được bỏ qua, nên bấm nhiều lần không làm lại việc cũ.</p>

  <div class="grid">
    <div>
      <label for="since">Từ ngày</label>
      <input type="date" id="since">
    </div>
    <div>
      <label for="job">Vị trí (để trống = tất cả)</label>
      <input id="job" list="joblist" placeholder="junior-frontend">
      <datalist id="joblist"></datalist>
    </div>
  </div>
  <div class="hint" id="scope">Đang kiểm tra…</div>

  <div class="count" id="count" style="margin-top:18px">…</div>
  <div class="count-label">CV chưa có nội dung</div>

  <button id="run" disabled>Đang kiểm tra…</button>
  <div class="note" id="note" hidden></div>
  <div class="alert" id="alert" hidden></div>

  <hr>

  <h2>Chạy tự động</h2>
  <div class="row">
    <input type="time" id="time" value="02:00">
    <button class="ghost" id="save-time">Lưu giờ</button>
  </div>
  <div class="hint" id="schedule-hint">Đang tải…</div>
  <div class="alert" id="schedule-alert" hidden></div>
</div>
<script>
const $ = (id) => document.getElementById(id);
let timer = null;

function criteria() {{
  return {{ since: $('since').value || '', job: $('job').value.trim() }};
}}

// Chỉ hiện khi CÓ VẤN ĐỀ. Chạy êm thì im lặng — số đếm tụt xuống là bằng chứng đủ rõ.
function fail(text) {{ const a = $('alert'); a.hidden = false; a.textContent = text; }}
function clearFail() {{ $('alert').hidden = true; }}
function note(text) {{ const n = $('note'); n.hidden = !text; n.textContent = text || ''; }}

async function refresh() {{
  const qs = new URLSearchParams(criteria()).toString();
  $('run').disabled = true;
  try {{
    const r = await fetch('/admin/pending?' + qs);
    const d = await r.json();
    if (d.error) throw new Error(d.error);
    clearFail();
    $('count').textContent = d.pending;
    $('scope').textContent = 'Phạm vi: ' + d.scope;
    $('run').disabled = d.pending === 0;
    $('run').textContent = d.pending === 0 ? 'Không có CV nào' : 'Xử lý ' + d.pending + ' CV';

    const list = $('joblist');
    list.innerHTML = '';
    (d.jobs || []).forEach((j) => {{
      const o = document.createElement('option');
      o.value = j.slug;
      o.label = j.slug + ' (' + j.count + ')';
      list.appendChild(o);
    }});
  }} catch (e) {{
    $('count').textContent = '—';
    fail('Không đếm được số CV: ' + e.message);
  }}
}}

let debounce = null;
['since', 'job'].forEach((id) => {{
  $(id).addEventListener('input', () => {{
    clearTimeout(debounce);
    debounce = setTimeout(refresh, 500);
  }});
}});

async function loadSchedule() {{
  try {{
    const r = await fetch('/admin/schedule');
    const d = await r.json();
    if (d.error) throw new Error(d.error);
    if (!d.configured) {{
      $('schedule-hint').textContent = 'Chưa cấu hình lịch chạy tự động.';
      $('save-time').disabled = true;
      return;
    }}
    if (d.time) $('time').value = d.time;
    $('schedule-hint').textContent = d.time
      ? 'Chạy mỗi ngày lúc ' + d.time + ' (' + d.timezone + '), xử lý CV trong 7 ngày gần nhất.'
      : 'Lịch hiện tại: ' + d.cron + ' (' + d.timezone + ')';
  }} catch (e) {{
    $('schedule-alert').hidden = false;
    $('schedule-alert').textContent = 'Không đọc được lịch: ' + e.message;
  }}
}}

$('save-time').addEventListener('click', async () => {{
  $('save-time').disabled = true;
  $('schedule-alert').hidden = true;
  try {{
    const r = await fetch('/admin/schedule', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ time: $('time').value }}),
    }});
    const d = await r.json();
    if (d.error) throw new Error(d.error);
    $('schedule-hint').textContent =
      'Chạy mỗi ngày lúc ' + d.time + ', xử lý CV trong 7 ngày gần nhất.';
  }} catch (e) {{
    $('schedule-alert').hidden = false;
    $('schedule-alert').textContent = 'Không lưu được giờ: ' + e.message;
  }} finally {{
    $('save-time').disabled = false;
  }}
}});

async function poll(execution) {{
  let d;
  try {{
    const r = await fetch('/admin/status?execution=' + encodeURIComponent(execution));
    d = await r.json();
  }} catch (e) {{
    clearInterval(timer);
    note('');
    fail('Mất kết nối khi theo dõi lượt chạy: ' + e.message);
    return;
  }}

  if (d.error) {{
    clearInterval(timer);
    note('');
    fail('Lỗi khi theo dõi lượt chạy: ' + d.error);
    return;
  }}
  if (!d.finished) return;

  clearInterval(timer);
  note('');
  if (d.failed > 0) {{
    fail('Lượt chạy kết thúc với lỗi. Mở log Cloud Run của job để xem CV nào hỏng.');
  }}
  refresh();
}}

$('run').addEventListener('click', async () => {{
  $('run').disabled = true;
  clearFail();
  note('Đang gửi yêu cầu…');
  try {{
    const r = await fetch('/admin/run', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify(criteria()),
    }});
    const d = await r.json();
    if (d.error) throw new Error(d.error);
    note('Đang chạy nền (' + d.scope + '). Có thể đóng trang này.');
    timer = setInterval(() => poll(d.execution), 5000);
  }} catch (e) {{
    note('');
    fail('Không khởi động được: ' + e.message);
    $('run').disabled = false;
  }}
}});

refresh();
loadSchedule();
</script></body></html>"""
