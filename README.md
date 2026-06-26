# Person Checker API

Сервис проверки физических лиц по 6 открытым государственным реестрам.

## Деплой на Railway (бесплатно, 10 минут)

1. Загрузите эту папку на GitHub (кнопка "Add file → Upload files")
2. Зайдите на railway.app → New Project → Deploy from GitHub repo
3. Выберите репозиторий → Railway сам всё сделает
4. Через 2 минуты получите URL вида `https://ваш-проект.up.railway.app`

## Использование

### Веб-форма
Откройте URL в браузере — там форма для ручных проверок.

### JSON API
```
POST https://ваш-проект.up.railway.app/api/check
Content-Type: application/json

{
  "last": "Синичкина",
  "first": "Валерия",
  "mid": "Валерьевна",
  "dob": "07.01.2004",
  "inn": ""
}
```

### Для Telegram-бота (n8n / Make / любой)
```
POST /api/check/telegram
→ вернёт { "text": "готовый текст", "parse_mode": "Markdown" }
```

## Статусы в ответе
- `overall_status: "success"` — чисто по всем источникам
- `overall_status: "warning"` — часть источников недоступна
- `overall_status: "danger"`  — найдены совпадения

## Источники
1. Федресурс — банкротство
2. ФССП — исполнительные производства
3. ФССП — розыск по ИП
4. ФССП — уголовный розыск
5. Росфинмониторинг — терроризм/экстремизм
6. ФСИН — розыск осуждённых
