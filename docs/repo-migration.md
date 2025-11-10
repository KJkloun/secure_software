# Перенос репозитория в новый проект

Эта инструкция сохраняет историю, ветки, теги и защитные настройки при миграции.

## 1. Подготовка
- Убедитесь, что локальная копия синхронизирована: `git fetch --all --tags`.
- Зафиксируйте текущие branch protection/secret настройки из `docs/repo-setup.md`.

## 2. Создаём зеркало
```bash
git clone --mirror git@github.com:old-org/course-project.git course-project-mirror
cd course-project-mirror
```
`--mirror` копирует весь `.git`, включая refs и конфиги.

## 3. Настраиваем новый origin
```bash
git remote set-url origin git@github.com:new-org/secure_software.git
# или добавляем дополнительный remote:
git remote add new-origin git@github.com:new-org/secure_software.git
```

## 4. Пушим все объекты
```bash
git push --mirror origin   # перенос всех refs
# либо
git push new-origin --all
git push new-origin --tags
```

## 5. Восстанавливаем защиту и CI
1. Включите branch protection/required checks (см. `docs/repo-setup.md`).
2. Перенесите secrets и переменные GitHub Actions.
3. Проверьте `CODEOWNERS`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`.

## 6. Проверяем и чистим
- `git ls-remote <new-origin>` — количество refs совпадает.
- Создайте тестовый PR (ветка `p02/...`), убедитесь, что workflow **CI** зелёный.
- Зеркальный клон можно удалить только после того, как все разработчики переключили `origin`.
