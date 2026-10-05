# Git: доступ и подключение личного fork

Проверено 2026-10-05 в `D:\codex\Causalis`.

| Проверка | Результат |
|---|---|
| Git | Установлен, `2.37.2.windows.2` |
| Автор локальных commits | Настроен как Maxim; email уже задан в Git config. Для commit GitHub login не нужен |
| Ветка | `codex/correctness-roadmap`, от audit SHA `ffe2c356c115f335b74b2f10117e19fe15585d46` |
| Чтение GitHub | `git ls-remote origin main` успешно: тот же SHA |
| GitHub CLI | `gh` не найден в PATH |
| Credential helper | Helper не настроен; установлен старый `git-credential-manager-core`2.0.785 |
| Сохранённая GitHub credential | Не найдена при noninteractive проверке через GCM; browser login не запускался |
| Права GitHub account / upstream push | Не установлены: нет подтверждённой авторизации |
| Удалённый fork / push | Не выполнены. Локальные branch/commits от этого независимы |

Первый sandbox network вызов был заблокирован локальным proxy; разрешённый сетевой запуск успешно прочитал repository. Это не признак отсутствия доступа к публичному проекту. Локальные Git mutations выполняются с разрешением на `.git`; они уже разрешены пользовательским запросом и успешно создают branch.

## Что сделать пользователю

В обычном PowerShell установить [GitHub CLI](https://cli.github.com/) (через официальный Windows installer либо WinGet):

```powershell
winget install --id GitHub.cli --exact
```

Открыть **новый** PowerShell, чтобы обновился PATH. Войти под своим GitHub account через браузер:

```powershell
gh auth login --hostname github.com --git-protocol https --web --scopes workflow
gh auth setup-git --hostname github.com
gh auth status
```

Официальные команды: [login](https://cli.github.com/manual/gh_auth_login), [setup-git](https://cli.github.com/manual/gh_auth_setup-git). `workflow` понадобится для запланированных изменений CI/release workflow. Пароль/токен в чат передавать не требуется. После входа достаточно сообщить, что авторизация готова; следующие fork/remote/push действия агент уже может выполнить в рамках запроса. HTTPS с browser login — выбранный способ; ручное создание SSH key или PAT для него не нужно.

## Как будет создан fork и remote

Ниже также можно выполнить самому **один раз после авторизации**, находясь в текущем checkout. Сначала проверить `git remote -v`: сейчас origin указывает на исходный проект, upstream ещё отсутствует. Если структура уже изменена, не повторять rename/add blindly.

```powershell
Set-Location -LiteralPath 'D:\codex\Causalis'
gh repo fork causalis-causalcraft/Causalis --clone=false --remote=false
$causalisGitHubLogin = gh api user --jq '.login'
git remote rename origin upstream
git remote add origin "https://github.com/$causalisGitHubLogin/Causalis.git"
git remote -v
git push --set-upstream origin codex/correctness-roadmap
```

Команда fork сохраняет существующий checkout и local commits; подробности — [официальный manual](https://cli.github.com/manual/gh_repo_fork). Если GitHub fork уже есть, проверить owner/repository и использовать его; не создавать дубликат. Возможные SSO/org policies или ограничения account выявляются только после входа, они пока не подтверждены.

Ожидаемая структура:

- `origin` → личный `<ваш-login>/Causalis`, туда пушим нашу branch;
- `upstream` → `causalis-causalcraft/Causalis`, оттуда читаем новые changes, включая sensitivity;
- local `main` хранит исходный baseline до осознанного обновления;
- local `codex/correctness-roadmap` хранит наши последовательные commits.

Промежуточные commits уже сохраняются локально. До первого успешного push удалённой резервной копии этой ветки нет. После него обычный `git push` сохраняет следующие commits в fork; публикация PR — отдельный этап после review готового блока.
