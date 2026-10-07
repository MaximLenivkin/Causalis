# Git: доступ и подключение личного fork

Проверено 2026-10-05 в `D:\codex\Causalis`. B05 tested source: `1b2477755c9b89bd2f69f260fd094002bdc26fe2`. Предыдущие B04 code checkpoints: `87228e267aed3dc71dadd4bbe19b969a95463591` (clusters), `57dbba1e2ecc0c1cab413b1da7f40cfdd8b22131` (DiD controls/full IF/aggregation). Финальный documentation checkpoint и remote/local equality проверяются на границе блока.

| Проверка | Результат |
|---|---|
| Git | Установлен, `2.37.2.windows.2` |
| Автор локальных commits | Настроен как Maxim; email уже задан в Git config. Для commit GitHub login не нужен |
| Ветка / local commits | `codex/correctness-roadmap`, от audit SHA `ffe2c356c115f335b74b2f10117e19fe15585d46`; B00–B05 сохранены; текущие B05 code commits перечислены ниже. Исторические B03 code commits c925907/e6a9275/6084b34/113c693; текущий documentation checkpoint через `git log -1` |
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

## B05 checkpoint

Code commits: bb31a4b09c20046faafbbd29a541e5acbe50b99d /5e0379507bac4b6ec9f561e7978e8835194c2247 /3c000b10eed1b5366f46cc038870500791b75579 /1b2477755c9b89bd2f69f260fd094002bdc26fe2. Последний code checkpoint протестирован:1376passed,0failed вне7sensitivitymodules. Final documentation checkpoint определяется git log-1; обычный push вorigin/codex/correctness-roadmap иremote/local SHA equality проверяются на завершении. Credentials/remotes/branch те же, повторная authorization не нужна. Causalis upstream не fetch/merge/rebase; PR/issues не создавались.

## B06 checkpoint

Финальный library/tests checkpoint `09e00de5a9d3dc915c6d59627f8b0ebc875dd4e9` сохранён в личной ветке. Локально1582passed; Все шесть clean Linux jobs и artifacts прошли; каждый — 1582 cases без failures/errors/skips. Exact CI run 37373828518 использует09e00de. Commits f31b743/5977bb8/74c0ff0/d292b3c/1be6b67/50ad33e/09e00de; final documentation checkpoint — git log-1. После09e00de source/tests не меняются, толькоaudit artifacts; final audit-only push не запускает повторнуюmatrix.

Credentials/remotes/branch прежние. GitHub Actions enabled/workflow access подтверждены actualrun и artifacts. Release/tag/PyPI/PR/issues/externalmessages не создавались. Remote/local equality иcleanstatus проверяются после обычного finalpush; новой authorization не требуется.

## B07 checkpoint

Code/doc checkpoints **43f0b3e170f28138fb0155ee99d3680d373b5d52**, **d3b67096dd847792b3b6f79b2a2d43749cab30b0**, **a2109a6ecd3c8422fbd4e8a7fd8d5d59334e8159** отправлены обычным push в origin/codex/correctness-roadmap. Последний — final source/tests checkpoint:1729localpassed и1729passed в каждом из6LinuxCIjobs; actual run37385736343/artifacts verified. После него только audit artifacts; final checkpoint определяется `git log -1`.

Fork/account/author/remotes не менялись. Auth/workflow scopes действуют; повторный login/новый fork не требуются. Final audit-only push не запускает matrix, не переписывает историю и не публикует release. Remote/local equality и чистота workspace проверяются после final push. Upstream/sensitivity sync, PR/issues/external messages не выполнялись.

## B08 checkpoint

Source/tests commit **9fb8041300410b560da80a45cabac4b541d1629d** pushed normally to origin/codex/correctness-roadmap. Actual CI37420288433 completed/success: sixjobs/artifacts verified,1916passed each. Final local integration and documentation checkpoint recorded in BLOCK08_DGP_CONTRACTS.md and git log-1. Credentials/remotes unchanged; no new auth required. Final audit-only push preserves history without restarting source CI. No upstream push, sync, PR/issues/messages/tag/PyPI publication.

## B09: текущий macOS checkout

Рабочая копия: `/Users/m.lenivkin/Documents/tclaude_folder/git-lab-projects/Causalis`; Python entrypoint `.venv/bin/python` (3.12.14, macOS arm64). Окружение восстановлено локально, старую Windows `.venv` не переносили. Исторические Windows пути и installer instructions выше не являются фактами об этом компьютере. Текущий GitHub CLI: `/Users/m.lenivkin/.local/bin/gh`; для CI явно передавать `--repo MaximLenivkin/Causalis`, поскольку автоматический выбор repository может указывать на upstream.

Текущий account **MaximLenivkin** проверен живым API; personal fork push подтверждён фактическим обычным push. Branch/remotes не изменены. Source/tests checkpoint **1e2b544f7f91a57ad3e049572915a4b3891b084a** pushed в `origin/codex/correctness-roadmap`. [CI37530152376](https://github.com/MaximLenivkin/Causalis/actions/runs/37530152376) completed/success: все шесть jobs и скачанные artifacts проверены, каждый2039passed. Последующие изменения только в audit; final documentation checkpoint определяется `git log -1`.

Разрешённый сетевой запуск требуется при sandbox DNS restrictions. Partial clone может подгружать недостающие исторические blobs во время `git show`; это отличается от отсутствующего файла в linked commit. Повторный login, fork setup и upstream sync не требуются. Final audit-only ordinary push не перезапускает source matrix. Remote/local equality и clean tree проверяются на завершении. PR, upstream push, release и внешние сообщения не выполнялись.

## 2026-10-07 — B10 personal checkpoint

Source/tests95a8b7599fb129fb2c5973f50e9b4a8018732f6c pushed обычным способом в origin/codex/correctness-roadmap. CI37532909989 completed/success: все6jobs/artifacts2072passed каждый, exactsource95a. После него меняются только audit artifacts. Итоговый checkpoint — git log -1; remote/local equality и clean tree проверяются после финального ordinary push. Existing GitHub credentials использованы без нового login; upstream не обновлялся, PR/release не создавались.


## 2026-10-07 — B11 personal checkpoint

Source/tests **cdc2c9590246c5b049d2184ba3479324217b2b00** ordinary pushed в `origin/codex/correctness-roadmap`. CI37589241406 completed/success: exactsourcecdc, все6downloadedjobartifacts2235passed каждый. Послеcdc толькоauditchanges; итоговый checkpoint — git log -1, finalremote/localequality+cleantree проверяются послеaudit-onlypush. Existing credentials/remotes использованы безnewlogin/fork/upstreamsync; PR/release/externalmessages несоздавались.
