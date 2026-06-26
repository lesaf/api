"""
FastAPI сервис проверки физлиц — интерфейс в стиле HomeOffer.
GET  /          — веб-интерфейс
POST /api/check — JSON API
POST /api/check/telegram — для Telegram-бота
GET  /health    — статус
"""
import json
from datetime import datetime
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from checkers import check_all

app = FastAPI(title="Person Checker", version="1.0.0", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

STATUS_LABELS = {
    "clean":  ("✓ Не найдено", "#16a34a"),
    "found":  ("⚠ Найдено — проверьте", "#dc2626"),
    "error":  ("— Источник недоступен", "#94a3b8"),
}

def build_response(results, last, first, mid, dob, inn):
    has_found = any(r.status == "found" for r in results)
    has_error  = any(r.status == "error"  for r in results)
    if has_found:
        overall, overall_text = "danger", "Найдены совпадения — необходима ручная проверка"
    elif has_error:
        overall, overall_text = "warning", "Часть источников временно недоступна"
    else:
        overall, overall_text = "success", "По всем источникам совпадений не найдено"
    return {
        "checked_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "person": {"last_name": last, "first_name": first, "middle_name": mid, "dob": dob, "inn": inn or None},
        "overall_status": overall,
        "overall_text": overall_text,
        "sources": [{"name": r.source, "url": r.url, "status": r.status, "detail": r.detail} for r in results],
    }


# ── JSON API ──────────────────────────────────────────────────────────────────
@app.post("/api/check")
async def api_check(request: Request):
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


@app.post("/api/check/telegram")
async def api_telegram(request: Request):
    body = await request.json()
    last  = body.get("last",  "").strip()
    first = body.get("first", "").strip()
    mid   = body.get("mid",   "").strip()
    dob   = body.get("dob",   "").strip()
    inn   = body.get("inn",   "").strip()
    if not last or not first or not dob:
        return JSONResponse({"text": "Укажите: last, first, dob"}, status_code=400)
    results = await check_all(last, first, mid, dob, inn)
    data = build_response(results, last, first, mid, dob, inn)
    icons = {"clean": "✅", "found": "🔴", "error": "⚪"}
    ov = {"success": "✅", "warning": "⚡", "danger": "🔴"}
    lines = [
        f"*Проверка физлица*",
        f"👤 {last} {first} {mid}".strip() + f", {dob}",
        f"🕐 {data['checked_at']}",
        "",
        f"{ov.get(data['overall_status'], '•')} *{data['overall_text']}*",
        "",
    ]
    for s in data["sources"]:
        if s["status"] != "error":
            lines.append(f"{icons.get(s['status'], '•')} {s['name']}: {s['detail']}")
    return JSONResponse({"text": "\n".join(lines), "parse_mode": "Markdown"})


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


# ── СТРАНИЦЫ ──────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(PAGE_FORM)


@app.post("/check", response_class=HTMLResponse)
async def check_form(
    last: str = Form(...), first: str = Form(...), mid: str = Form(""),
    dob: str = Form(...), inn: str = Form(""),
):
    results = await check_all(last.strip(), first.strip(), mid.strip(), dob.strip(), inn.strip())
    data = build_response(results, last, first, mid, dob, inn)
    return HTMLResponse(render_result(data))


# ── HTML: форма ───────────────────────────────────────────────────────────────
PAGE_FORM = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Проверка контрагента — HomeOffer</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Inter', sans-serif; background: #f8fafc; color: #0f172a; min-height: 100vh; }

  /* Шапка */
  .header { background: #0f172a; padding: 0 32px; height: 60px; display: flex; align-items: center; justify-content: space-between; }
  .logo { color: #fff; font-size: 18px; font-weight: 700; letter-spacing: -0.3px; }
  .logo span { color: #3b82f6; }
  .header-tag { background: #1e293b; color: #94a3b8; font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 20px; letter-spacing: 0.5px; text-transform: uppercase; }

  /* Контент */
  .page { max-width: 560px; margin: 0 auto; padding: 48px 20px; }
  .eyebrow { font-size: 12px; font-weight: 600; color: #3b82f6; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 10px; }
  h1 { font-size: 28px; font-weight: 700; color: #0f172a; line-height: 1.2; margin-bottom: 8px; letter-spacing: -0.5px; }
  .desc { font-size: 15px; color: #64748b; line-height: 1.6; margin-bottom: 36px; }

  /* Форма */
  .form-card { background: #fff; border-radius: 16px; border: 1px solid #e2e8f0; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,.06); }
  .row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
  .row3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-bottom: 16px; }
  .field { display: flex; flex-direction: column; }
  .field label { font-size: 12px; font-weight: 600; color: #475569; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.4px; }
  .field input { border: 1.5px solid #e2e8f0; border-radius: 10px; padding: 11px 14px; font-size: 15px; font-family: inherit; color: #0f172a; background: #fafbfc; outline: none; transition: border-color .15s, box-shadow .15s; }
  .field input:focus { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,.12); background: #fff; }
  .field input::placeholder { color: #cbd5e1; }
  .divider { border: none; border-top: 1px solid #f1f5f9; margin: 20px 0; }
  .optional { font-size: 12px; color: #94a3b8; margin-bottom: 12px; }
  .btn { width: 100%; background: #1d4ed8; color: #fff; border: none; border-radius: 10px; padding: 14px; font-size: 15px; font-weight: 600; font-family: inherit; cursor: pointer; transition: background .15s; margin-top: 8px; letter-spacing: 0.1px; }
  .btn:hover:not(:disabled) { background: #1e40af; }
  .btn:disabled { background: #93c5fd; cursor: not-allowed; }

  /* Источники */
  .sources { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 28px; }
  .src-tag { font-size: 11px; color: #64748b; background: #f1f5f9; padding: 4px 10px; border-radius: 20px; }

  @media (max-width: 500px) {
    .row2, .row3 { grid-template-columns: 1fr; }
    .page { padding: 28px 16px; }
    .form-card { padding: 24px 20px; }
  }
</style>
</head>
<body>
<div class="header">
  <div class="logo">Home<span>Offer</span></div>
  <div class="header-tag">Проверка контрагента</div>
</div>
<div class="page">
  <div class="eyebrow">Due Diligence</div>
  <h1>Проверка физического лица</h1>
  <p class="desc">Автоматическая проверка по государственным реестрам — банкротство, долги, розыск, судимости, санкционные списки.</p>

  <div class="form-card">
    <form method="POST" action="/check" onsubmit="document.querySelector('.btn').disabled=true;document.querySelector('.btn').textContent='Проверяем...'">
      <div class="row3">
        <div class="field"><label>Фамилия *</label><input name="last" required placeholder="Иванов" autocomplete="off"></div>
        <div class="field"><label>Имя *</label><input name="first" required placeholder="Иван" autocomplete="off"></div>
        <div class="field"><label>Отчество</label><input name="mid" placeholder="Иванович" autocomplete="off"></div>
      </div>
      <div class="row2">
        <div class="field"><label>Дата рождения *</label><input name="dob" required placeholder="ДД.ММ.ГГГГ" pattern="\\d{2}\\.\\d{2}\\.\\d{4}" autocomplete="off"></div>
        <div class="field"><label>ИНН</label><input name="inn" placeholder="необязательно" maxlength="12" autocomplete="off"></div>
      </div>
      <hr class="divider">
      <button class="btn" type="submit">Проверить</button>
    </form>
  </div>

  <div class="sources">
    <span class="src-tag">Федресурс</span>
    <span class="src-tag">ФССП</span>
    <span class="src-tag">Росфинмониторинг</span>
    <span class="src-tag">ФСИН</span>
    <span class="src-tag">ГАС Правосудие</span>
  </div>
</div>
</body>
</html>"""


# ── HTML: результат ───────────────────────────────────────────────────────────
def render_result(data: dict) -> str:
    p = data["person"]
    name = f"{p['last_name']} {p['first_name']} {p.get('middle_name','') or ''}".strip()
    inn_str = f" · ИНН {p['inn']}" if p.get("inn") else ""

    overall = data["overall_status"]
    overall_text = data["overall_text"]

    if overall == "success":
        ov_bg, ov_border, ov_icon, ov_clr = "#f0fdf4", "#bbf7d0", "✓", "#15803d"
    elif overall == "danger":
        ov_bg, ov_border, ov_icon, ov_clr = "#fef2f2", "#fecaca", "!", "#b91c1c"
    else:
        ov_bg, ov_border, ov_icon, ov_clr = "#fefce8", "#fde68a", "~", "#a16207"

    rows = ""
    for s in data["sources"]:
        if s["status"] == "clean":
            icon, clr, bg = "✓", "#16a34a", "#f0fdf4"
            label = "Не найдено"
        elif s["status"] == "found":
            icon, clr, bg = "!", "#b91c1c", "#fef2f2"
            label = s["detail"]
        else:
            icon, clr, bg = "–", "#94a3b8", "#f8fafc"
            label = "Источник временно недоступен"

        rows += f"""
        <div style="display:flex;align-items:center;gap:14px;padding:14px 0;border-bottom:1px solid #f1f5f9;">
          <div style="width:32px;height:32px;border-radius:50%;background:{bg};border:1.5px solid {clr}20;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:13px;font-weight:700;color:{clr}">{icon}</div>
          <div style="flex:1;min-width:0;">
            <div style="font-size:14px;font-weight:600;color:#1e293b;margin-bottom:1px">{s['name']}</div>
            <div style="font-size:13px;color:{clr}">{label}</div>
          </div>
          <a href="{s['url']}" target="_blank" style="font-size:12px;color:#94a3b8;text-decoration:none;flex-shrink:0;white-space:nowrap">Источник →</a>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Результат проверки — HomeOffer</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Inter', sans-serif; background: #f8fafc; color: #0f172a; min-height: 100vh; }}
  .header {{ background: #0f172a; padding: 0 32px; height: 60px; display: flex; align-items: center; justify-content: space-between; }}
  .logo {{ color: #fff; font-size: 18px; font-weight: 700; letter-spacing: -0.3px; }}
  .logo span {{ color: #3b82f6; }}
  .back {{ color: #64748b; font-size: 13px; text-decoration: none; display: flex; align-items: center; gap: 6px; }}
  .back:hover {{ color: #94a3b8; }}
  .page {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
  .meta {{ font-size: 12px; color: #94a3b8; margin-bottom: 20px; }}
  .person-name {{ font-size: 22px; font-weight: 700; color: #0f172a; margin-bottom: 4px; letter-spacing: -0.3px; }}
  .person-dob {{ font-size: 14px; color: #64748b; margin-bottom: 24px; }}
  .verdict {{ background: {ov_bg}; border: 1.5px solid {ov_border}; border-radius: 12px; padding: 16px 20px; display: flex; align-items: center; gap: 14px; margin-bottom: 8px; }}
  .verdict-icon {{ width: 36px; height: 36px; border-radius: 50%; background: {ov_clr}; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 700; flex-shrink: 0; }}
  .verdict-text {{ font-size: 15px; font-weight: 600; color: {ov_clr}; }}
  .card {{ background: #fff; border-radius: 16px; border: 1px solid #e2e8f0; padding: 8px 24px; box-shadow: 0 1px 3px rgba(0,0,0,.05); margin-bottom: 16px; }}
  .new-check {{ display: inline-block; margin-top: 20px; background: #1d4ed8; color: #fff; padding: 12px 24px; border-radius: 10px; font-size: 14px; font-weight: 600; text-decoration: none; }}
  .new-check:hover {{ background: #1e40af; }}
  @media (max-width: 500px) {{ .page {{ padding: 24px 16px; }} .card {{ padding: 8px 16px; }} }}
</style>
</head>
<body>
<div class="header">
  <div class="logo">Home<span>Offer</span></div>
  <a href="/" class="back">← Новая проверка</a>
</div>
<div class="page">
  <div class="meta">Проверка выполнена {data['checked_at']}</div>
  <div class="person-name">{name}</div>
  <div class="person-dob">Дата рождения: {p['dob']}{inn_str}</div>

  <div class="verdict">
    <div class="verdict-icon">{ov_icon}</div>
    <div class="verdict-text">{overall_text}</div>
  </div>

  <div class="card">{rows}</div>

  <a href="/" class="new-check">Проверить другого человека</a>
</div>
</body>
</html>"""
