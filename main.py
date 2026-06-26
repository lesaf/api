"""
FastAPI сервис проверки физлиц — стиль HomeOffer (янтарь, белый, Inter).
"""
import json
from datetime import datetime
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from checkers import check_all

app = FastAPI(title="Person Checker", version="1.0.0", docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET","POST","OPTIONS"], allow_headers=["*"])

def build_response(results, last, first, mid, dob, inn):
    has_found = any(r.status == "found" for r in results)
    has_error  = any(r.status == "error"  for r in results)
    if has_found:   overall, overall_text = "danger",  "Найдены совпадения — необходима ручная проверка"
    elif has_error: overall, overall_text = "warning", "Часть источников временно недоступна"
    else:           overall, overall_text = "success", "По всем источникам совпадений не найдено"
    return {
        "checked_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "person": {"last_name": last, "first_name": first, "middle_name": mid, "dob": dob, "inn": inn or None},
        "overall_status": overall, "overall_text": overall_text,
        "sources": [{"name": r.source, "url": r.url, "status": r.status, "detail": r.detail} for r in results],
    }

@app.post("/api/check")
async def api_check(request: Request):
    body = await request.json()
    last=body.get("last","").strip(); first=body.get("first","").strip()
    mid=body.get("mid","").strip(); dob=body.get("dob","").strip(); inn=body.get("inn","").strip()
    if not last or not first or not dob:
        return JSONResponse({"error": "Обязательные поля: last, first, dob"}, status_code=400)
    results = await check_all(last, first, mid, dob, inn)
    return JSONResponse(build_response(results, last, first, mid, dob, inn))

@app.post("/api/check/telegram")
async def api_telegram(request: Request):
    body = await request.json()
    last=body.get("last","").strip(); first=body.get("first","").strip()
    mid=body.get("mid","").strip(); dob=body.get("dob","").strip(); inn=body.get("inn","").strip()
    if not last or not first or not dob:
        return JSONResponse({"text": "Укажите: last, first, dob"}, status_code=400)
    results = await check_all(last, first, mid, dob, inn)
    data = build_response(results, last, first, mid, dob, inn)
    icons = {"clean": "✅", "found": "🔴", "error": "⚪"}
    ov = {"success": "✅", "warning": "⚡", "danger": "🔴"}
    lines = [f"*Проверка физлица*", f"👤 {last} {first} {mid}".strip()+f", {dob}",
             f"🕐 {data['checked_at']}", "", f"{ov.get(data['overall_status'],'•')} *{data['overall_text']}*", ""]
    for s in data["sources"]:
        if s["status"] != "error":
            lines.append(f"{icons.get(s['status'],'•')} {s['name']}: {s['detail']}")
    return JSONResponse({"text": "\n".join(lines), "parse_mode": "Markdown"})

@app.get("/health")
async def health():
    return {"status": "ok"}

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

# ── Цвета HomeOffer ───────────────────────────────────────────────────────────
# Янтарь #F5C842, фон #FAFAF8, текст #1A1A1A, серый #6B7280, карточка белая

PAGE_FORM = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Проверка контрагента — HomeOffer</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',sans-serif;background:#FAFAF8;color:#1A1A1A;min-height:100vh}

/* Шапка — как у HomeOffer */
.header{background:#fff;border-bottom:1px solid #F0F0EC;padding:0 28px;height:58px;display:flex;align-items:center;gap:12px}
.logo{display:flex;align-items:center;gap:10px;text-decoration:none}
.header-sep{width:1px;height:20px;background:#E5E5E0;margin:0 4px}
.header-label{font-size:13px;color:#6B7280;font-weight:500}

/* Страница */
.page{max-width:540px;margin:0 auto;padding:44px 20px 60px}

/* Хлебные крошки */
.breadcrumb{font-size:12px;color:#9CA3AF;margin-bottom:24px}
.breadcrumb span{color:#1A1A1A;font-weight:500}

h1{font-size:26px;font-weight:700;letter-spacing:-0.4px;margin-bottom:6px;line-height:1.25}
.subtitle{font-size:14px;color:#6B7280;line-height:1.6;margin-bottom:32px}

/* Карточка формы */
.card{background:#fff;border-radius:16px;border:1px solid #EBEBЕ7;padding:28px;box-shadow:0 1px 4px rgba(0,0,0,.05)}

.section-label{font-size:11px;font-weight:700;color:#9CA3AF;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:14px}

.row2{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
.row3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:12px}
.field label{display:block;font-size:11px;font-weight:600;color:#6B7280;margin-bottom:5px;text-transform:uppercase;letter-spacing:0.4px}
.field input{width:100%;border:1.5px solid #E5E5E0;border-radius:10px;padding:10px 13px;font-size:14px;font-family:inherit;color:#1A1A1A;background:#FAFAF8;outline:none;transition:border .15s,box-shadow .15s}
.field input:focus{border-color:#F5C842;box-shadow:0 0 0 3px rgba(245,200,66,.18);background:#fff}
.field input::placeholder{color:#C4C4BC}

.divider{border:none;border-top:1px solid #F0F0EC;margin:20px 0}

.btn{width:100%;background:#F5C842;color:#1A1A1A;border:none;border-radius:10px;padding:13px;font-size:15px;font-weight:700;font-family:inherit;cursor:pointer;transition:background .15s,transform .1s;letter-spacing:-0.1px}
.btn:hover:not(:disabled){background:#ECC030}
.btn:active:not(:disabled){transform:scale(0.99)}
.btn:disabled{background:#F5E9A0;color:#9CA3AF;cursor:not-allowed}

/* Теги источников */
.sources{margin-top:20px;display:flex;flex-wrap:wrap;gap:6px}
.src{font-size:11px;color:#6B7280;background:#fff;border:1px solid #E5E5E0;padding:4px 10px;border-radius:20px}

@media(max-width:480px){.row2,.row3{grid-template-columns:1fr}.page{padding:28px 16px}.card{padding:20px}}
</style>
</head>
<body>
<div class="header">
  <a class="logo" href="/">
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
      <!-- Жёлтый домик-пятиугольник -->
      <path d="M18 2L34 13V36H2V13L18 2Z" fill="url(#hg)" rx="6"/>
      <defs><linearGradient id="hg" x1="18" y1="2" x2="18" y2="36" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stop-color="#FFD95A"/>
        <stop offset="100%" stop-color="#F5C040"/>
      </linearGradient></defs>
      <!-- Крыша (треугольник поверх) -->
      <path d="M18 2L34 14H2L18 2Z" fill="#F0B830"/>
      <!-- Монетки: стопка 3 диска -->
      <ellipse cx="15" cy="26" rx="5" ry="2" fill="#3D3D3D"/>
      <rect x="10" y="22" width="10" height="4" rx="2" fill="#3D3D3D"/>
      <ellipse cx="15" cy="22" rx="5" ry="2" fill="#555"/>
      <rect x="10" y="18" width="10" height="4" rx="2" fill="#555"/>
      <ellipse cx="15" cy="18" rx="5" ry="2" fill="#666"/>
      <!-- Шар справа -->
      <circle cx="24" cy="24" r="5" fill="#3D3D3D"/>
    </svg>
    <span style="font-family:Georgia,serif;font-size:19px;font-weight:700;color:#333;letter-spacing:-0.2px">HomeOffer</span>
  </a>
  <div class="header-sep"></div>
  <div class="header-label">Проверка контрагента</div>
</div>
<div class="page">
  <div class="breadcrumb">AI-инструменты · <span>Проверка физлица</span></div>
  <h1>Проверка физического лица</h1>
  <p class="subtitle">Автоматически проверяем по государственным реестрам — банкротство, долги, розыск, санкционные списки и судебные дела.</p>

  <div class="card">
    <div class="section-label">Данные лица</div>
    <form method="POST" action="/check" onsubmit="this.querySelector('.btn').disabled=true;this.querySelector('.btn').textContent='Проверяем...'">
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
    <div class="src">Федресурс</div>
    <div class="src">ФССП</div>
    <div class="src">Росфинмониторинг</div>
    <div class="src">ФСИН</div>
    <div class="src">ГАС Правосудие</div>
    <div class="src">5 реестров</div>
  </div>
</div>
</body>
</html>"""


def render_result(data: dict) -> str:
    p = data["person"]
    name = f"{p['last_name']} {p['first_name']} {p.get('middle_name','') or ''}".strip()
    inn_str = f" · ИНН {p['inn']}" if p.get("inn") else ""
    overall = data["overall_status"]

    if overall == "success":
        ov_bg,ov_brd,ov_dot,ov_clr,ov_icon = "#F0FDF4","#BBF7D0","#16A34A","#15803D","✓"
    elif overall == "danger":
        ov_bg,ov_brd,ov_dot,ov_clr,ov_icon = "#FEF2F2","#FECACA","#EF4444","#B91C1C","!"
    else:
        ov_bg,ov_brd,ov_dot,ov_clr,ov_icon = "#FEFCE8","#FDE68A","#F59E0B","#92400E","~"

    rows = ""
    for s in data["sources"]:
        if s["status"] == "clean":
            dot,clr,detail = "#16A34A","#16A34A","Не найдено"
        elif s["status"] == "found":
            dot,clr,detail = "#EF4444","#B91C1C", s["detail"]
        else:
            dot,clr,detail = "#D1D5DB","#9CA3AF","Временно недоступен"

        rows += f"""<div style="display:flex;align-items:center;gap:14px;padding:13px 0;border-bottom:1px solid #F5F5F2">
  <div style="width:8px;height:8px;border-radius:50%;background:{dot};flex-shrink:0;margin-left:2px"></div>
  <div style="flex:1;min-width:0">
    <div style="font-size:13px;font-weight:600;color:#1A1A1A">{s['name']}</div>
    <div style="font-size:13px;color:{clr};margin-top:1px">{detail}</div>
  </div>
  <a href="{s['url']}" target="_blank" style="font-size:12px;color:#9CA3AF;text-decoration:none;white-space:nowrap;flex-shrink:0">↗</a>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Результат — HomeOffer</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',sans-serif;background:#FAFAF8;color:#1A1A1A;min-height:100vh}}
.header{{background:#fff;border-bottom:1px solid #F0F0EC;padding:0 28px;height:58px;display:flex;align-items:center;gap:12px}}
.logo{{display:flex;align-items:center;gap:10px;text-decoration:none}}
.header-sep{{width:1px;height:20px;background:#E5E5E0}}
.back{{font-size:13px;color:#6B7280;text-decoration:none;font-weight:500}}
.back:hover{{color:#1A1A1A}}
.page{{max-width:540px;margin:0 auto;padding:36px 20px 60px}}
.ts{{font-size:12px;color:#9CA3AF;margin-bottom:16px}}
.pname{{font-size:22px;font-weight:700;letter-spacing:-0.3px;margin-bottom:3px}}
.pdob{{font-size:13px;color:#6B7280;margin-bottom:22px}}
.verdict{{background:{ov_bg};border:1.5px solid {ov_brd};border-radius:12px;padding:14px 18px;display:flex;align-items:center;gap:12px;margin-bottom:6px}}
.verdict-dot{{width:10px;height:10px;border-radius:50%;background:{ov_dot};flex-shrink:0}}
.verdict-text{{font-size:14px;font-weight:600;color:{ov_clr}}}
.card{{background:#fff;border-radius:16px;border:1px solid #EBEBЕ7;padding:4px 20px 4px;box-shadow:0 1px 4px rgba(0,0,0,.05);margin-bottom:16px}}
.btn-new{{display:inline-block;margin-top:18px;background:#F5C842;color:#1A1A1A;padding:12px 24px;border-radius:10px;font-size:14px;font-weight:700;text-decoration:none}}
.btn-new:hover{{background:#ECC030}}
@media(max-width:480px){{.page{{padding:24px 16px}}.card{{padding:4px 16px 4px}}}}
</style>
</head>
<body>
<div class="header">
  <a class="logo" href="/">
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
      <!-- Жёлтый домик-пятиугольник -->
      <path d="M18 2L34 13V36H2V13L18 2Z" fill="url(#hg)" rx="6"/>
      <defs><linearGradient id="hg" x1="18" y1="2" x2="18" y2="36" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stop-color="#FFD95A"/>
        <stop offset="100%" stop-color="#F5C040"/>
      </linearGradient></defs>
      <!-- Крыша (треугольник поверх) -->
      <path d="M18 2L34 14H2L18 2Z" fill="#F0B830"/>
      <!-- Монетки: стопка 3 диска -->
      <ellipse cx="15" cy="26" rx="5" ry="2" fill="#3D3D3D"/>
      <rect x="10" y="22" width="10" height="4" rx="2" fill="#3D3D3D"/>
      <ellipse cx="15" cy="22" rx="5" ry="2" fill="#555"/>
      <rect x="10" y="18" width="10" height="4" rx="2" fill="#555"/>
      <ellipse cx="15" cy="18" rx="5" ry="2" fill="#666"/>
      <!-- Шар справа -->
      <circle cx="24" cy="24" r="5" fill="#3D3D3D"/>
    </svg>
    <span style="font-family:Georgia,serif;font-size:19px;font-weight:700;color:#333;letter-spacing:-0.2px">HomeOffer</span>
  </a>
  <div class="header-sep"></div>
  <a href="/" class="back">← Новая проверка</a>
</div>
<div class="page">
  <div class="ts">Проверено {data['checked_at']}</div>
  <div class="pname">{name}</div>
  <div class="pdob">Дата рождения: {p['dob']}{inn_str}</div>
  <div class="verdict"><div class="verdict-dot"></div><div class="verdict-text">{data['overall_text']}</div></div>
  <div class="card">{rows}</div>
  <a href="/" class="btn-new">Проверить другого</a>
</div>
</body>
</html>"""
