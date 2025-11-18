# Idea Catalog API

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
pytest -q
```

## CI
В репозитории настроен workflow **CI** (GitHub Actions) — required check для `main`.
Badge добавится автоматически после загрузки шаблона в GitHub.

## Контейнеры
```bash
cp .env.example .env   # задаёт IDEA_API_PORT, IDEA_ATTACHMENT_DIR и лимиты
docker compose up --build
# скрипт проверяет здоровье контейнера и uid процесса
scripts/test_container.sh
```

Dockerfile использует multi-stage сборку на базе `python:3.11.9-slim-bookworm`
с зафиксированным digest, non-root пользователем и `HEALTHCHECK`. Для
дополнительных проверок:

```bash
hadolint Dockerfile
docker compose build           # соберёт образ idea-catalog:local
trivy image idea-catalog:local
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
