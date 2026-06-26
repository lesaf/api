"""
FastAPI сервис проверки физлиц.
GET  /          — веб-форма
POST /api/check — JSON API
GET  /health    — статус сервиса
"""
import asyncio
import json
from datetime import datetime
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from checkers import check_all, CheckResult

app = FastAPI(title="Person Checker API", version="1.0.0", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

def build_response(results, last, first, mid, dob, inn):
    has_found = any(r.status == "found" for r in results)
    has_error  = any(r.status == "error"  for r in results)
    if has_found:
        overall, overall_text = "danger", "Найдены совпадения — требуется проверка"
    elif has_error:
        overall, overall_text = "warning", "Часть источников недоступна — результат неполный"
    else:
        overall, overall_text = "success", "По всем источникам совпадений не найдено"
    return {
        "checked_at": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        "person": {"last_name": last, "first_name": first, "middle_name": mid, "dob": dob, "inn": inn or None},
        "overall_status": overall,
        "overall_text": overall_text,
        "sources": [{"name": r.source, "url": r.url, "status": r.status, "detail": r.detail} for r in results],
    }

# ── JSON API ──────────────────────────────────────────────────────────────────
@app.post("/api/check")
async def api_check(request: Request):
    """
    Проверка физлица. Тело запроса (JSON):
    { "last": "Фамилия", "first": "Имя", "mid": "Отчество", "dob": "ДД.ММ.ГГГГ", "inn": "необязательно" }
    """
    body = await request.json()
    last  = body.get("last",  "").strip()
    first = body.get("first", "").strip()
    mid   = body.get("mid",   "").strip()
    dob   = body.get("dob",   "").strip()
    inn   = body.get("inn",   "").strip()
    if not last or not first or not dob:
        return JSONResponse({"error": "Обязательные поля: last, first, dob"}, status_code=400)
    results = await check_all(last, first, mid, dob, inn)
    return JSONResponse(build_response(results, last, first, mid, dob, inn))

# ── Telegram bot webhook helper ───────────────────────────────────────────────
@app.post("/api/check/telegram")
async def api_check_telegram(request: Request):
    """
    Упрощённый формат для Telegram-бота:
    возвращает готовый текст для отправки пользователю.
    """
    body = await request.json()
    last  = body.get("last",  "").strip()
    first = body.get("first", "").strip()
    mid   = body.get("mid",   "").strip()
    dob   = body.get("dob",   "").strip()
    inn   = body.get("inn",   "").strip()
    if not last or not first or not dob:
        return JSONResponse({"text": "❌ Укажите: last, first, dob"}, status_code=400)
    results = await check_all(last, first, mid, dob, inn)
    data = build_response(results, last, first, mid, dob, inn)
    icons = {"clean": "✅", "found": "🔴", "error": "⚠️"}
    overall_icon = {"success": "✅", "warning": "⚡", "danger": "🔴"}
    lines = [
        f"*Проверка физлица*",
        f"👤 {last} {first} {mid}".strip() + f", {dob}",
        f"📅 {data['checked_at']}",
        "",
        f"{overall_icon.get(data['overall_status'], '•')} *{data['overall_text']}*",
        "",
    ]
    for s in data["sources"]:
        lines.append(f"{icons.get(s['status'], '•')} {s['name']}")
        lines.append(f"   _{s['detail']}_")
    return JSONResponse({"text": "\n".join(lines), "parse_mode": "Markdown"})

# ── Веб-форма ─────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(HTML_FORM)

@app.post("/check", response_class=HTMLResponse)
async def check_form(
    last: str = Form(...), first: str = Form(...), mid: str = Form(""),
    dob: str = Form(...), inn: str = Form(""),
):
    results = await check_all(last.strip(), first.strip(), mid.strip(), dob.strip(), inn.strip())
    data = build_response(results, last, first, mid, dob, inn)
    return HTMLResponse(render_page(data))

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "checked_at": datetime.now().isoformat()}

# ── HTML ──────────────────────────────────────────────────────────────────────
HTML_FORM = """<!DOCTYPE html>
<html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Проверка физлица</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;background:#f0f2f5;padding:32px 16px;color:#1a1a2e}
.wrap{max-width:660px;margin:0 auto}
.card{background:#fff;border-radius:14px;box-shadow:0 2px 12px rgba(0,0,0,.08);padding:28px;margin-bottom:20px}
h1{font-size:21px;font-weight:700;color:#0d47a1;margin-bottom:3px}
.sub{font-size:13px;color:#64748b;margin-bottom:22px}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px}
.row3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin-bottom:14px}
label{display:block;font-size:11px;font-weight:700;color:#475569;margin-bottom:5px;text-transform:uppercase;letter-spacing:.5px}
input{width:100%;border:1.5px solid #e2e8f0;border-radius:8px;padding:10px 12px;font-size:15px;outline:none;background:#fafbfc;transition:border .15s}
input:focus{border-color:#0d47a1;box-shadow:0 0 0 3px rgba(13,71,161,.1);background:#fff}
.btn{width:100%;background:#0d47a1;color:#fff;border:none;border-radius:10px;padding:13px;font-size:15px;font-weight:600;cursor:pointer;margin-top:8px;transition:background .15s}
.btn:hover:not(:disabled){background:#1565c0}
.btn:disabled{background:#90b8e8;cursor:not-allowed}
.api-box{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px;margin-top:18px;font-size:12px;color:#475569;line-height:1.7}
.api-box code{background:#e2e8f0;padding:1px 5px;border-radius:4px;font-family:monospace}
a{color:#0d47a1}
</style></head>
<body><div class="wrap"><div class="card">
<h1>Проверка физического лица</h1>
<div class="sub">6 государственных реестров · параллельно · JSON API готов</div>
<form method="POST" action="/check" onsubmit="this.querySelector('.btn').disabled=true;this.querySelector('.btn').textContent='⏳ Проверяем...'">
<div class="row3">
<div><label>Фамилия *</label><input name="last" required placeholder="Синичкина"></div>
<div><label>Имя *</label><input name="first" required placeholder="Валерия"></div>
<div><label>Отчество</label><input name="mid" placeholder="Валерьевна"></div>
</div>
<div class="row2">
<div><label>Дата рождения * (ДД.ММ.ГГГГ)</label><input name="dob" required placeholder="07.01.2004" pattern="\\d{2}\\.\\d{2}\\.\\d{4}"></div>
<div><label>ИНН (необязательно)</label><input name="inn" placeholder="повышает точность" maxlength="12"></div>
</div>
<button class="btn" type="submit">🔍 Проверить</button>
</form>
<div class="api-box">
<b>JSON API:</b> POST <code>/api/check</code> · <a href="/docs">Swagger UI</a> · <a href="/health">Health</a><br>
<b>Telegram:</b> POST <code>/api/check/telegram</code> → готовый текст для бота
</div>
</div></div></body></html>"""


def render_page(data):
    ICON = {"clean": "✅", "found": "🔴", "error": "⚠️"}
    CLR  = {"clean": "#16a34a", "found": "#dc2626", "error": "#d97706"}
    BG   = {"clean": "#f0fdf4", "found": "#fef2f2", "error": "#fffbeb"}
    OV   = {
        "success": ("#dcfce7", "#15803d", "#bbf7d0", "✅ По всем источникам совпадений не найдено"),
        "warning": ("#fefce8", "#a16207", "#fde68a", "⚡ Часть источников недоступна — результат неполный"),
        "danger":  ("#fee2e2", "#b91c1c", "#fecaca", "⚠️ Найдены совпадения — требуется ручная проверка"),
    }
    obg, oclr, obrd, otxt = OV.get(data["overall_status"], OV["warning"])
    rows = ""
    for s in data["sources"]:
        rows += f"""<div style="background:{BG.get(s['status'],'#fff')};border:1px solid #e5e7eb;border-radius:8px;padding:12px 16px;margin-bottom:8px;display:flex;gap:12px;align-items:flex-start">
<span style="font-size:18px">{ICON.get(s['status'],'•')}</span>
<div><div style="font-weight:600;font-size:14px;color:#1e293b">{s['name']}</div>
<div style="color:{CLR.get(s['status'],'#888')};font-size:13px;margin-top:2px">{s['detail']}</div>
<a href="{s['url']}" target="_blank" style="font-size:11px;color:#94a3b8;text-decoration:none">↗ открыть источник</a></div></div>"""
    p = data["person"]
    pname = f"{p['last_name']} {p['first_name']} {p['middle_name']}".strip()
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    return f"""<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Результат проверки</title>
<style>*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;background:#f0f2f5;padding:32px 16px;color:#1a1a2e}}.wrap{{max-width:660px;margin:0 auto}}.card{{background:#fff;border-radius:14px;box-shadow:0 2px 12px rgba(0,0,0,.08);padding:28px;margin-bottom:16px}}h1{{font-size:21px;font-weight:700;color:#0d47a1;margin-bottom:3px}}.meta{{font-size:13px;color:#64748b;margin-bottom:16px}}a{{color:#0d47a1;text-decoration:none}}pre{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px;font-size:12px;overflow-x:auto;margin-top:10px}}summary{{cursor:pointer;font-size:13px;color:#64748b;margin-top:14px;padding-top:12px;border-top:1px solid #f1f5f9}}</style>
</head><body><div class="wrap"><div class="card">
<h1>Результат проверки</h1>
<div class="meta">👤 <b>{pname}</b> · д.р. {p['dob']} · {data['checked_at']} · <a href="/">← новая проверка</a></div>
<div style="background:{obg};border:1px solid {obrd};color:{oclr};border-radius:10px;padding:13px 16px;font-weight:600;font-size:15px;margin-bottom:16px">{otxt}</div>
{rows}
<details><summary>JSON-ответ (для разработчика / интеграции)</summary><pre>{json_str}</pre></details>
</div></div></body></html>"""
