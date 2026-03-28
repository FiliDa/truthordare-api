# 🎲 Truth or Dare API (FastAPI)

[![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat&logo=sqlite&logoColor=white)](https://www.sqlite.org/)

Минималистичное API и админка для игры «Правда или Действие», построенные на FastAPI и SQLite. База создаётся автоматически и заполняется стартовыми наборами фраз, есть веб‑админка и WebSocket‑оповещения для клиентов.

## ✨ Основные возможности

- REST API для управления фразами (truth/dare) и выбора случайной фразы
- Категории: family, party, work, kids, couples, travel
- Админ‑панель с фильтрами, пагинацией и массовым добавлением
- WebSocket broadcast при изменении базы
- SQLite база, создаётся автоматически в папке данных

## 🗂 Структура проекта

```
truthordareAPI/
└── pravda/
    ├── app.py               # Основное приложение FastAPI
    ├── requirements.txt     # Зависимости
    ├── templates/
    │   ├── admin.html       # Админ‑панель (SSR)
    │   └── tester.html      # Тестовая страница
    ├── static/
    │   └── styles.css
    └── data/
        └── pravda.db        # Автоматически создаётся при запуске (в .gitignore)
```

- Код: [pravda/app.py](file:///e:/GITR — копия/truthordareAPI/pravda/app.py)
- Шаблоны: [templates](file:///e:/GITR — копия/truthordareAPI/pravda/templates)
- Статика: [static](file:///e:/GITR — копия/truthordareAPI/pravda/static)

## ⚙️ Установка и запуск

1) Установите зависимости:

```bash
cd pravda
pip install -r requirements.txt
```

2) Запустите приложение:

```bash
uvicorn pravda.app:app --reload
# или
python -m uvicorn pravda.app:app --reload
```

3) Откройте в браузере:
- Админка: http://127.0.0.1:8000/admin
- Тестовая страница: http://127.0.0.1:8000/tester
- Swagger: http://127.0.0.1:8000/docs

База данных будет создана автоматически по пути: [pravda/data/pravda.db](file:///e:/GITR — копия/truthordareAPI/pravda/data/).

## 🔌 Эндпоинты API

- GET `/api/phrases` — список всех фраз (опц. ?category=family)
- GET `/api/phrases/truth` — список «правда» (опц. ?category=)
- GET `/api/phrases/dare` — список «действие» (опц. ?category=)
- POST `/api/phrases` — добавить одну фразу
  - body: `{ "type": "truth|dare", "text": "строка", "category": "family" }`
- POST `/api/phrases/bulk` — добавить несколько фраз
  - body: `[ { "type": "...", "text": "...", "category": "..." }, ... ]`
- PUT `/api/phrases/{id}` — обновить поля фразы (query: type, text, language, category)
- DELETE `/api/phrases/{id}` — удалить фразу
- GET `/api/random` — случайная фраза (опц. ?type=truth|dare&category=)
- GET `/api/base` — агрегированная база по категориям

## 🧑‍💼 Админка

- `/admin` — фильтры по типу/категории, поиск, пагинация, массовое добавление
- `/tester` — выбрать случайную фразу по типу/категории

## 🛡 Чистота репозитория

Убрано всё лишнее:
- удалены тестовые дампы и утилиты из `pravda/tests/`
- удалена локальная база `pravda/data/pravda.db` (создаётся при запуске)
- добавлен .gitignore, чтобы не попадали `.db`, `__pycache__`, артефакты и .env

## 📦 Зависимости

Файл: [pravda/requirements.txt](file:///e:/GITR — копия/truthordareAPI/pravda/requirements.txt)

Минимум для запуска:
- fastapi, uvicorn
- sqlalchemy
- jinja2

## 📝 Примечания

- Язык фраз по умолчанию — `en`. Начальная база генерируется при старте.
- Таблицы и недостающие поля создаются автоматически.

## 👤 Автор

Filippov D.A. — Backend Engineer  
Email: phoenixmediacall@gmail.com  
GitHub: https://github.com/FiliDa

---

Если проект полезен — поставьте ⭐ и предложите улучшения через Issues.
