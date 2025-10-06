# BDD-сценарии проверки Security NFR

Feature: Access control for administrative actions
  Scenario: Authenticated user can list audit events
    Given stage окружение использует JWT с подписью RS256 и TTL 60 минут
    And у меня есть действительный токен администратора
    When я отправляю GET запрос на /admin/audit-events с этим токеном
    Then ответ имеет статус 200
    And тело содержит список событий без персональных данных

  Scenario: Запрос без токена отклоняется
    Given stage окружение использует JWT с подписью RS256 и TTL 60 минут
    When я отправляю GET запрос на /admin/audit-events без заголовка Authorization
    Then ответ имеет статус 401
    And тело ошибки содержит код "unauthorized"

Feature: Rate limiting для создания идей
  Scenario: Превышение лимита приводит к 429
    Given включён лимит 100 успешных POST /ideas на одного пользователя в минуту
    And пользователь уже создал 100 идей в последнюю минуту
    When пользователь отправляет ещё один POST запрос на /ideas
    Then ответ имеет статус 429
    And тело ошибки содержит код "rate_limit_exceeded"

Feature: Контроль SCA отчётов
  Scenario: CI помечает пайплайн как failed при просроченной уязвимости
    Given зависимость помечена как High severity и исправление откладывается > 7 дней
    When nightly SCA job выполняет `pip-audit`
    Then отчёт содержит запись о просроченном SLA
    And пайплайн CI завершается со статусом failed

Feature: Audit log for repeated authorization failures
  Scenario: Три подряд ошибки авторизации попадают в security.log (негативный случай)
    Given включено централизованное логирование в файл security.log
    And атакующий отправил два запроса с неверными токенами в последние 30 секунд
    When атакующий отправляет ещё один запрос с неверным токеном
    Then ответ имеет статус 401
    And security.log получает запись с уровнем WARN и идентификатором клиента
