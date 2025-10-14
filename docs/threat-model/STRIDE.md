# P04 — STRIDE анализ

Таблица охватывает основные элементы и потоки `F1…F12` из `DFD.md`, связывая угрозы со связанными рисками и контролями. Контроли ссылаются на NFR из P03 и подтверждаются существующими или планируемыми артефактами проверки.

| Поток/Элемент | Угроза (STRIDE) | Риск | Контроль | Ссылка на NFR | Проверка/Артефакт |
|---------------|-----------------|------|----------|---------------|-------------------|
| F1: HTTPS POST /ideas | T — Tampering (инъекции в payload) | R1 | Валидация полей через Pydantic, очистка тегов и описаний | NFR-02 | `pytest -q` (валидационные тесты) |
| F2: POST /ideas/{id}/evaluations | T — Tampering (повторные оценки для накрутки) | R2 | Запрет повторных оценок пользователя для одной идеи, мягкая дедупликация | NFR-04 | `tests/security/test_eval_dedup.py` |
| F3: GET /ideas | I — Information Disclosure (избыточные данные/ошибки) | R9 | Анонимизация внутренних кодов ошибок, whitelisting полей ответа | NFR-02 | Контрактные тесты `tests/test_ideas.py` |
| F4: PATCH /ideas/{id} (JWT) | S — Spoofing (подмена админ-токена) | R3 | JWT RS256 с TTL ≤ 60 мин, проверка audience/issuer | NFR-01 | `tests/security/test_admin_access.py` |
| API Gateway (F1–F4) | D — Denial of Service (rate-limit bypass) | R4 | Rate limiting + WAF правила на burst/spike, блокировка IP | NFR-03 | k6 `scripts/loadtest/ideas-rate-limit.js` |
| F5: Internal HTTP + JWT claims | T — Tampering (man-in-the-middle внутри периметра) | R10 | mTLS между gateway и API, network segmentation | NFR-03 | OPA политика `gw-tls-required` в GitOps pipeline |
| F6/F7: CRUD идеи ↔ хранилище | T — Tampering (несанкционированное изменение данных) | R5 | Транзакционный доступ, проверка статуса, idempotent update | NFR-02 | Интеграционные тесты `tests/security/test_eval_dedup.py` |
| F8: Security events → sink | R — Repudiation (отсутствие аудита 401/403) | R6 | централизованные security-логи 401/403, trace-id | NFR-05 | `scripts/check_security_logs.py` в CI |
| F9/F10: Secrets ↔ Vault | I — Information Disclosure (утечка секретов/ключей) | R7 | Vault с TTL ≤ 30 дней, авто-ротация сервисных токенов | NFR-07 | `scripts/secrets_ttl.py` + Vault отчёт |
| F11/F12: CI ↔ pip-audit | E — Elevation of Privilege (уязвимость в зависимостях) | R8 | Еженедельный `pip-audit`, блокирующий PR с High/Critical | NFR-06 | GitHub Actions job `ci/pip-audit` |
