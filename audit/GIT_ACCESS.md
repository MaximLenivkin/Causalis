# Git: доступ и подключение личного fork

Проверено 2026-10-05 в `D:\codex\Causalis`.

| Проверка | Результат |
|---|---|
| Git | Установлен, `2.37.2.windows.2` |
| Автор локальных commits | Настроен как Maxim; email уже задан в Git config. Для commit GitHub login не нужен |
| Ветка / local commits | `codex/correctness-roadmap`, от audit SHA `ffe2c356c115f335b74b2f10117e19fe15585d46`; B00/B01 и четыре code commits B02 сохранены; текущий checkpoint через `git log -1` |
| Чтение GitHub | Исходный main совпадает с audit SHA; personal branch доступна |
| GitHub CLI | Установлен2.102.0; executable `C:\Program Files\GitHub CLI\gh.exe`. Старый PATH текущего Codex процесса может его не видеть; использовать полный путь |
| Credential helper | `gh auth setup-git` настроил GitHub helper; HTTPS push успешно проверен |
| Авторизация GitHub | Активен **MaximLenivkin**, credential в keyring; scopes `repo`, `workflow`, `read:org`, `gist`. Токен не выводился |
| Права аккаунта | Upstream:read безpush; personal fork:push/admin подтверждены API |
| Fork | [MaximLenivkin/Causalis](https://github.com/MaximLenivkin/Causalis), parent `causalis-causalcraft/Causalis` |
| Удалённая ветка | [codex/correctness-roadmap](https://github.com/MaximLenivkin/Causalis/tree/codex/correctness-roadmap); local tracking установлен, обычный push используется для checkpoints; latest remote SHA проверяется на завершении каждого блока |

Первый sandbox network вызов был заблокирован локальным proxy; разрешённый сетевой запуск успешно прочитал repository. Это не признак отсутствия доступа к публичному проекту. Локальные Git mutations выполняются с разрешением на `.git`; они уже разрешены пользовательским запросом и успешно создают branch.

## Первоначальная настройка — уже выполнена

Повторный login сейчас не требуется. Ниже сохранена инструкция для переустановки/другого компьютера.

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

## Fork и remotes — уже настроены

Следующая последовательность сохранена как справка для нового checkout. **В текущем проекте не повторять:** origin уже личный fork, upstream уже исходный проект. Всегда сначала проверить `git remote -v`.

```powershell
Set-Location -LiteralPath 'D:\codex\Causalis'
gh repo fork causalis-causalcraft/Causalis --clone=false
$causalisGitHubLogin = gh api user --jq '.login'
git remote rename origin upstream
git remote add origin "https://github.com/$causalisGitHubLogin/Causalis.git"
git remote -v
git push --set-upstream origin codex/correctness-roadmap
```

Команда fork сохраняет существующий checkout и local commits; подробности — [официальный manual](https://cli.github.com/manual/gh_repo_fork). Установленная версияCLI не принимает `--remote=false` вместе с явным repository argument; прежняя инструкция исправлена. Если GitHub fork уже есть, проверить owner/repository и использовать его; не создавать дубликат.

Фактическая структура:

- `origin` → `https://github.com/MaximLenivkin/Causalis.git`, туда пушим нашу branch;
- `upstream` → `causalis-causalcraft/Causalis`, оттуда читаем новые changes, включая sensitivity;
- local `main` хранит исходный baseline до осознанного обновления;
- local `codex/correctness-roadmap` хранит наши последовательные commits.

Локальная ветка отслеживает `origin/codex/correctness-roadmap`. Обычный `git push` сохраняет следующие законченные commits в личный fork. Публикация PR — отдельный этап после review готового блока; PR не создавался. Проверка remote/local SHA при завершении подключения записывается в PROGRESS.md.
