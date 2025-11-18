# Idea Catalog API
[![CI](https://github.com/KJkloun/secure_software/actions/workflows/ci.yml/badge.svg)](https://github.com/KJkloun/secure_software/actions/workflows/ci.yml)

Проектное задание HSE SecDev 2025: каталог продуктовых идей с оценкой ценности.

## Быстрый старт
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
pre-commit install
uvicorn app.main:app --reload
```

## Ритуал перед PR
```bash
ruff --fix .
black .
isort .
pytest -q
pre-commit run --all-files
```

- Локальный `pre-commit` не даст закоммитить прямо в `main`, поэтому работу
  всегда начинаем с ветки `p02/...`.

## Тесты
```bash
mkdir -p reports
pytest -q --junitxml=reports/junit.xml
```

## CI
Workflow `.github/workflows/ci.yml` (GitHub Actions) гоняет линтеры (`ruff`,
`black --check`, `isort --check-only`) и `pytest -q --junitxml=reports/junit.xml`
под Python 3.12 для событий `push/pull_request`. Pip кэшируется, у шагов задан
таймаут, а `reports/` загружается артефактом, чтобы можно было смотреть
результаты тестов в UI.

## Контейнеры
```bash
docker build -t secdev-app .
docker run --rm -p 8000:8000 secdev-app
# или
docker compose up --build
```

## Эндпойнты
- `GET /health` — пинг сервиса
- `POST /ideas` — создать идею
- `GET /ideas` — список идей с фильтрами по тегу, статусу или минимальной оценке
- `GET /ideas/{id}` — получить конкретную идею
- `PATCH /ideas/{id}` — обновить описание, теги или статус
- `POST /ideas/{id}/evaluations` — добавить оценку
- `GET /ideas/{id}/evaluations` — посмотреть историю оценок

## Формат ошибок
Все ошибки — JSON-обёртка:
```json
{
  "error": {"code": "idea_not_found", "message": "idea not found"}
}
```

Полезные документы:
- `docs/branching.md` — схема веток под P02
- `REVIEW_CHECKLIST.md` — что проверяем при ревью

См. также: `SECURITY.md`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`.
