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


## 2026-10-07 — B12 personal checkpoint

Source/tests **0b30db33fd2593dc25ea1b823a91795c789e0191** ordinary pushed в origin/codex/correctness-roadmap. CI37598926037 completed/success на exactsource0b30: все шесть downloaded job artifacts2397passed каждый,0failures/errors/skips. Credentials/remotes/branch прежние; newlogin/fork/upstreamsync не нужны. Послеsourcefreeze толькоauditfiles; finalcheckpointgitlog-1, remote/local equality иcleanstatus послеfinalordinarypush. PR/release/externalmessagesнесоздавались.


## 2026-10-07 — B13 personal checkpoint

Source/tests **4428be0e39bda8a2a47f1a6f184c92873da10976** отправлены обычным push в `origin/codex/correctness-roadmap`. [CI37607784481](https://github.com/MaximLenivkin/Causalis/actions/runs/37607784481) completed/success на exact source: все шесть jobs и downloaded artifact sets проверены, **2488 passed каждый**, 0 failures/errors/skips. GitHub CLI и credentials прежние; login/fork/remotes/branch не менялись. После source checkpoint — только audit changes; final checkpoint определяется git log-1. Обычный audit-only push, live remote/local equality и clean tree проверяются на завершении. Upstream sync/push, PR, release и внешние сообщения не выполнялись.


## 2026-10-07 — B14 personal checkpoint

Source/tests **4bdcff7d6388d1d72d5be4a546e8abb2a67a767c** ordinary pushed в origin/codex/correctness-roadmap. [CI37611862809](https://github.com/MaximLenivkin/Causalis/actions/runs/37611862809) completed/success на exactsource; allsixdownloaded artifacts2539passed each,0failures/errors/skips. Local committedsourcecorrectnesssuite также2539passed. Credentials/CLI/branch/remotes прежние, login/fork/upstreamsync не нужны. Послеsourcefreeze толькоauditfiles; finalcheckpoint gitlog-1 и live remote/local equality+cleanstatus послеfinalordinarypush. Audit-onlypush doesnotrerunmatrix. PR/upstreampush/release/externalmessages не выполнялись.


## 2026-10-07 — B15 personal checkpoint

Source/tests **9a57e91942a4b90b0401c0f8e3ebe6f5b4d82cdf** обычным push отправлены в origin/codex/correctness-roadmap. [CI37628255646](https://github.com/MaximLenivkin/Causalis/actions/runs/37628255646) completed/success на exact source; все шесть downloaded artifacts —2618passed каждый,0failures/errors/skips. Local committed correctness suite также2618passed. Existing credentials/CLI/branch/remotes использованы; новый login/fork/upstreamsync не требовался. После sourcefreeze — только audit changes; finalcheckpoint gitlog-1, live remote/local equality+cleanstatus после finalordinarypush. Audit-onlypush не запускает matrix. Upstream push/sync, PR/release и внешние сообщения не выполнялись.


## B22: явное разрешение на push, 8 October2026

Пользователь подтвердил: «Разрешаю пуш в нашу ветку». Разрешение относится
к существующему личному fork MaximLenivkin/Causalis и ветке
codex/correctness-roadmap; последующие обычные push завершённых блоков в эту
ветку продолжают этот разрешённый процесс. Не запрашивать повторно разрешение
на такие push. Upstream/main, force-push и публикация PR не входят в это действие.
Обычный push357e16e..d99ea8f успешен; CI37751321348 completed/success на d99ea8f,
в котором исходники идентичны implementation ede6ded (изменился только audit).


## B23 personal checkpoint, 8 October 2026

Ordinary source push1409e95..b1adeb2 succeeded using the user's persisting
«Разрешаю пуш в нашу ветку» authorization. CI37763490246 completed/success on
exact b1adeb291870c965825c60712144d23ea4c31ce9: all six verified artifacts
3521passed each plus strict standalone docs exit0. No new login/fork/setup.
Final audit-only ordinary push/live equality and clean tree checked at completion;
final checkpoint is gitlog-1. Personal branch authorization continues; upstream/
main, force-push, PR, release and external messages are not authorized by it.

## B24 — authorized ordinary personal-branch pushes (8 October 2026)

Explicit «Разрешаю пуш в нашу ветку» persists for ordinary pushes to
MaximLenivkin/Causalis:codex/correctness-roadmap; do not ask again.
Source2652d9f pushed3668eec..2652d9f; final correction `7e947f44e3d5a0ca9dbbe0b68bf7f070fc6150fd` pushed2652d9f..7e947f4.
InitialCI37771095421 all6x3646passed. FinalCI37772289364 completed/success on
exact7e947f4, all6x3648passed and strictdocs exit0; raw artifacts verified.
Final audit-only checkpoint via gitlog-1; ordinary push/live local-remote
identity/clean tree checked at completion. No forcepush/upstream/main/PR/release.
No auto-review rejection or reauthorization was needed for B24.


## B25 push — 8 October 2026

User's explicit «Разрешаю пуш в нашу ветку» remains authorization for ordinary
push to MaximLenivkin/Causalis:codex/correctness-roadmap. Source8604060 pushed
successfully (`ebf940f..8604060`) without auto-review rejection. CI37795625225
tracks exact source `8604060282b803b73e00595b705867ddff351a32`. No force/upstream/main/PR/release action or new
login/fork/auth setup. CI37795625225 completed/success: all6jobs3772passed each plus strictdocs0 on
exact8604060. Full cases/argv/selection/source/env and5artifacthashes/job checked;
snapshotUTC2026-10-08T14:55:07.367935+00:00. Source/tests unchanged after8604060;
final audit checkpoint via gitlog-1. Ordinary audit push and live clean/synced
local-remote state checked at completion. Persistent authorization requires no
new permission question.


## B26 checkpoint — 8 October 2026

Source `38378424fbfc422236ed81ba8162222ea39e6849` ordinary-pushed to
`MaximLenivkin/Causalis:codex/correctness-roadmap`, baseline4876103.
Local correctness3874passed, strict Sphinx0; CI37806099397 completed/success on
exact source, all6artifacts3874passed plus strictdocs0. Root --require-ci verifies
raw artifact/source/case sets/scope/env/hashes and issues[]. Only audit changes
after source. Final audit checkpoint via git log -1; ordinary final audit push,
live local/remote identity and clean tree checked at completion.

Persistent authorization is the user's explicit «Разрешаю пуш в нашу ветку».
No automatic review rejection, new login/auth/fork setup or repeat permission
question. No upstream/main/forcepush/PR/release or external messaging. Stop at
B26 for context cleanup; next B27 requires a new user request.


## B27 checkpoint — 8 October 2026

Implementationf71863483c59df3d740a4984981998bfcb0da627; final source root-export
correction72f6918b1eb06b8bfd743397b2bf0bde6a8ef8a0, baseline750354b.
Ordinary push750354b..72f6918 to MaximLenivkin/Causalis:codex/correctness-roadmap
succeeded under persistent user «Разрешаю пуш в нашу ветку» authorization.
No automatic review rejection/new permission/auth/login/setup/fork changes.
Final correctness3981passed, strictSphinx0, CI37809518217 completed/success on
exact72f6918:all6artifacts3981passed plus strictdocs0. Root --require-ci verifies
raw evidence/source/cases/scope/env/hashes/cleanup/158handofflinks, issues[].
Source/tests frozen; final changes audit-only. Final audit checkpoint via gitlog-1,
ordinary final audit push/live identity and clean/synced tree checked at completion.
No upstream/main/forcepush/PR/release/external messages. Stop after B27; next
B28weak-IVLATE requires context cleanup and a new user request.


## B28 checkpoint — 8 October 2026

Baselineab789bf; implementation856b05ca78a7127bdd342eb79cd9fda961aa6873,
set-geometry guard8aad3a07b96d174151bd7ef39bcaba05f7d98bfe,
final sourceb9110f0d24d3cc8a107883720d2e475f4317f085. Ordinary pushes
ab789bf..8aad3a0 and8aad3a0..b9110f0 to
MaximLenivkin/Causalis:codex/correctness-roadmap succeeded under persistent
user «Разрешаю пуш в нашу ветку». No auto-review rejection/new approval/
auth/login/setup/fork changes. Final correctness4092passed, strictSphinx0,
CI37815247713 completed/success on exactb9110f0: all6artifacts4092passed
plus strictdocs0. IntermediateCI37813839790 on8aad3a0 also passed4091cases
perjob; source guard change required final run. Root --require-ci verifies
raw local/initial/intermediate/finalCI evidence/source/cases/scope/env/5hashes/
owned cleanup/163handofflinks, issues[]. Source/tests frozen; final changes
are audit-only. Final audit checkpoint via gitlog-1; ordinary final audit
push/live identity and clean/synced tree checked at completion. No upstream/
main/forcepush/PR/release/external messages/subagents. Stop after B28; next
B29HonestDiD requires context cleanup and a new user request.

## B29 — authorized branch checkpoint, 9 October 2026

User's existing explicit «Разрешаю пуш в нашу ветку» remains authorization for
ordinary pushes to MaximLenivkin/Causalis:codex/correctness-roadmap.
Baseline d882998; source pushes d882998..d542692 andd542692..2c63f8d succeeded.
InitialCI37844628093 failed allsix solely on one new bitwise covariance endpoint
oracle; final2c63f8d fixes this test tolerance without library/old-test changes.
FinalCI37845415092 allsix4282passed/strictdocs0 on exact2c63f8d, artifacts checked.
Local4282correctness/420focus/190new; strictSphinx25.165s; root --require-ci;
167handoff links; source/tests frozen. Final checkpoint through gitlog-1 is
an audit-only commit and does not rerun the matrix. Its ordinary push and live
remote/local equality/clean tree are checked at completion. No automatic
approval rejection, new login, remote/fork setup, PR, upstream/main write,
forcepush, release, dependency install, client query/export or external message.
Stop at B29; B30 starts only after new user request.
