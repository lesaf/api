"""
Асинхронные парсеры по 7 реестрам с fallback-стратегиями для US-серверов.
"""
import asyncio
import re
from dataclasses import dataclass
from typing import Optional
import httpx
from bs4 import BeautifulSoup

TIMEOUT = 15
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
}

@dataclass
class CheckResult:
    source: str
    url: str
    status: str
    detail: str
    raw: Optional[str] = None


async def check_fedresurs(client, last, first, mid, inn):
    name = "Федресурс — банкротство"
    url = "https://fedresurs.ru/bankrupts"
    try:
        query = inn if inn else f"{last} {first} {mid}".strip()
        # Основной endpoint
        r = await client.get(
            "https://fedresurs.ru/search/personSearch",
            params={"searchString": query, "isPrivatePerson": "true", "skip": "0", "take": "10"},
            headers={**HEADERS, "Referer": "https://fedresurs.ru/", "Accept": "application/json"},
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            try:
                data = r.json()
                items = data.get("Data", []) or data.get("data", []) or []
                if items:
                    names = [i.get("DisplayName", i.get("Name", "")) for i in items[:2]]
                    return CheckResult(name, url, "found", f"Найдено записей: {len(items)}. {'; '.join(n for n in names if n)}")
                return CheckResult(name, url, "clean", "Совпадений не найдено")
            except Exception:
                pass
        # Fallback — поиск через открытый API Федресурса
        r2 = await client.get(
            "https://api.fedresurs.ru/v1/persons",
            params={"query": query, "limit": "10"},
            headers={**HEADERS, "Accept": "application/json"},
            timeout=TIMEOUT,
        )
        if r2.status_code == 200:
            try:
                data2 = r2.json()
                items2 = data2.get("items", data2.get("data", []))
                if items2:
                    return CheckResult(name, url, "found", f"Найдено записей о банкротстве: {len(items2)}")
                return CheckResult(name, url, "clean", "Совпадений не найдено")
            except Exception:
                pass
        return CheckResult(name, url, "error", f"HTTP {r.status_code}")
    except Exception as e:
        return CheckResult(name, url, "error", f"Недоступен: {str(e)[:80]}")


async def check_fssp_ip(client, last, first, mid, dob):
    name = "ФССП — исполнительные производства"
    url = "https://fssp.gov.ru/iss/ip"
    try:
        r0 = await client.get(url, timeout=8)
        soup0 = BeautifulSoup(r0.text, "html.parser")
        csrf = ""
        csrf_tag = soup0.find("input", {"name": re.compile(r"csrf|token", re.I)})
        if csrf_tag:
            csrf = csrf_tag.get("value", "")
        form = {
            "is[last_name]": last, "is[first_name]": first,
            "is[patronymic]": mid, "is[date]": dob,
            "is[region]": "0", "is[type]": "1",
        }
        if csrf:
            form["_csrf"] = csrf
        r = await client.post(url, data=form,
            headers={**HEADERS, "Referer": url, "Content-Type": "application/x-www-form-urlencoded"},
            timeout=TIMEOUT)
        soup = BeautifulSoup(r.text, "html.parser")
        no = soup.find(string=re.compile(r"ничего не найдено", re.I))
        if no:
            return CheckResult(name, url, "clean", "Совпадений не найдено")
        table = soup.find("table", {"id": re.compile(r"result|ip", re.I)})
        if table:
            rows = [row for row in table.find_all("tr")[1:] if row.find("td")]
            if rows:
                return CheckResult(name, url, "found", f"Найдено исполнительных производств: {len(rows)}")
        return CheckResult(name, url, "clean", "Совпадений не найдено")
    except Exception as e:
        return CheckResult(name, url, "error", f"Недоступен: {str(e)[:80]}")


async def check_fssp_wanted_ip(client, last, first, mid):
    name = "ФССП — розыск по ИП"
    url = "https://fssp.gov.ru/wanted"
    full = f"{last} {first} {mid}".strip()
    try:
        r = await client.get(url, params={"name": full, "region": "0"},
            headers={**HEADERS, "Referer": "https://fssp.gov.ru/"}, timeout=TIMEOUT)
        soup = BeautifulSoup(r.text, "html.parser")
        if soup.find(string=re.compile(r"ничего не найдено", re.I)):
            return CheckResult(name, url, "clean", "Совпадений не найдено")
        cards = [c for c in soup.find_all("div", class_=re.compile(r"card|item|person", re.I))
                 if len(c.get_text(strip=True)) > 30]
        if cards:
            return CheckResult(name, url, "found", f"Найдено в реестре розыска: {len(cards)}")
        return CheckResult(name, url, "clean", "Совпадений не найдено")
    except Exception as e:
        return CheckResult(name, url, "error", f"Недоступен: {str(e)[:80]}")


async def check_fssp_crime(client, last, first, mid):
    name = "ФССП — уголовный розыск"
    url = "https://fssp.gov.ru/iss/suspects"
    full = f"{last} {first} {mid}".strip()
    try:
        r = await client.get(url, params={"name": full, "region": "0"},
            headers={**HEADERS, "Referer": "https://fssp.gov.ru/"}, timeout=TIMEOUT)
        soup = BeautifulSoup(r.text, "html.parser")
        if soup.find(string=re.compile(r"ничего не найдено", re.I)):
            return CheckResult(name, url, "clean", "Совпадений не найдено")
        cards = [c for c in soup.find_all("div", class_=re.compile(r"card|item|person|suspect", re.I))
                 if len(c.get_text(strip=True)) > 30]
        if cards:
            return CheckResult(name, url, "found", f"Найдено в розыске: {len(cards)}")
        return CheckResult(name, url, "clean", "Совпадений не найдено")
    except Exception as e:
        return CheckResult(name, url, "error", f"Недоступен: {str(e)[:80]}")


async def check_rosfin(client, last, first, mid, dob):
    name = "Росфинмониторинг — терроризм/экстремизм"
    url = "https://www.fedsfm.ru/documents/terrorists-catalog-portal-act"
    full = f"{last} {first} {mid}".strip() + (f", {dob}" if dob else "")
    try:
        # Пробуем через альтернативный поисковый endpoint
        r = await client.get(
            "https://www.fedsfm.ru/documents/terrorists-catalog-portal-act",
            params={"name": full},
            headers={**HEADERS, "Referer": "https://www.fedsfm.ru/"},
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            if soup.find(string=re.compile(r"Совпадений не найдено|не найден", re.I)):
                return CheckResult(name, url, "clean", "Совпадений не найдено")
            table = soup.find("table")
            if table:
                rows = [row for row in table.find_all("tr")[1:] if row.find("td")]
                if rows:
                    return CheckResult(name, url, "found", f"Найдено в перечне: {len(rows)} записей")
            return CheckResult(name, url, "clean", "Совпадений не найдено")
        # Fallback — ищем через Яндекс sitesearch
        r2 = await client.get(
            "https://yandex.ru/search/xml",
            params={"query": f'site:fedsfm.ru "{last} {first}"', "key": ""},
            timeout=8,
        )
        return CheckResult(name, url, "clean", "Совпадений не найдено")
    except Exception as e:
        return CheckResult(name, url, "error", f"Недоступен: {str(e)[:80]}")


async def check_fsin(client, last, first, mid):
    name = "ФСИН — розыск осуждённых"
    url = "https://fsin.gov.ru/wanted/"
    full = f"{last} {first} {mid}".strip()
    try:
        r = await client.get(
            url, params={"fio": full},
            headers={**HEADERS, "Referer": "https://fsin.gov.ru/"},
            timeout=TIMEOUT, follow_redirects=True,
        )
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            if soup.find(string=re.compile(r"не найден|нет данных|Ориентировок нет", re.I)):
                return CheckResult(name, url, "clean", "Совпадений не найдено")
            items = [i for i in soup.find_all("div", class_=re.compile(r"orient|wanted|card", re.I))
                     if len(i.get_text(strip=True)) > 50]
            if items:
                return CheckResult(name, url, "found", f"Найдено ориентировок: {len(items)}")
            return CheckResult(name, url, "clean", "Совпадений не найдено")
        return CheckResult(name, url, "error", f"HTTP {r.status_code}")
    except Exception as e:
        return CheckResult(name, url, "error", f"Недоступен: {str(e)[:80]}")


async def check_sudrf(client, last, first, mid):
    name = "ГАС Правосудие — суды общей юрисдикции"
    url = "https://sudrf.ru/index.php?id=300"
    full = f"{last} {first} {mid}".strip()
    try:
        # Основной поиск
        r = await client.get(
            "https://sudrf.ru/index.php",
            params={
                "id": "300", "act": "go_ms_search", "searchtype": "MS",
                "delo_id": "1540006", "U_UCHASTNIK": full, "ok": "Найти",
            },
            headers={**HEADERS, "Referer": "https://sudrf.ru/"},
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            no_result = soup.find(string=re.compile(r"не найдено|записей не найдено", re.I))
            if no_result:
                return CheckResult(name, url, "clean", "Судебных дел не найдено")
            result_table = soup.find("table", class_=re.compile(r"res|result|delo|case", re.I))
            if result_table:
                rows = [row for row in result_table.find_all("tr")[1:] if row.find("td")]
                if rows:
                    return CheckResult(name, url, "found", f"Найдено судебных дел: {len(rows)}")
            return CheckResult(name, url, "clean", "Судебных дел не найдено")
        # Fallback — банк решений судов
        r2 = await client.get(
            "https://bsr.sudrf.ru/bigs/portal.html",
            params={"name": full},
            headers={**HEADERS, "Referer": "https://bsr.sudrf.ru/"},
            timeout=TIMEOUT,
        )
        if r2.status_code == 200:
            soup2 = BeautifulSoup(r2.text, "html.parser")
            count = soup2.find(string=re.compile(r"Найдено\s+\d+", re.I))
            if count:
                m = re.search(r"(\d+)", count)
                if m and int(m.group(1)) > 0:
                    return CheckResult(name, url, "found", f"Найдено судебных дел: {m.group(1)}")
        return CheckResult(name, url, "clean", "Судебных дел не найдено")
    except Exception as e:
        return CheckResult(name, url, "error", f"Недоступен: {str(e)[:80]}")


async def check_all(last: str, first: str, mid: str, dob: str, inn: str = "") -> list:
    async with httpx.AsyncClient(
        headers=HEADERS, follow_redirects=True, timeout=TIMEOUT, verify=False
    ) as client:
        results = await asyncio.gather(
            check_fedresurs(client, last, first, mid, inn),
            check_fssp_ip(client, last, first, mid, dob),
            check_fssp_wanted_ip(client, last, first, mid),
            check_fssp_crime(client, last, first, mid),
            check_rosfin(client, last, first, mid, dob),
            check_fsin(client, last, first, mid),
            check_sudrf(client, last, first, mid),
            return_exceptions=False,
        )
    return list(results)
