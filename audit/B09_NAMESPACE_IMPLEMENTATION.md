# B09 · Проверка имён выходной схемы

Baseline: `74145665127f8fa5a0bf038d769697ab880854b8` (library source соответствует B08 `9fb8041`). Ветка: `codex/correctness-roadmap`. Python: локальная `.venv/bin/python`, 3.12.14, macOS arm64. Этап выполняется по новому запросу пользователя; три субагента независимо разбирают контракт, пишут regression tests и проверяют patch.

## Контракт и реализация

Все фактически генерируемые имена должны быть непустыми строками и уникальными. Валидатор резервирует outcome `y`, имена treatment и фактические expanded confounders. При включённых oracle он добавляет `m_`, `m_obs_`, `tau_link_`, `g_` для каждого treatment и `cate_` только для noncontrol treatment. Отключённые oracle и отсутствующий control CATE не резервируются.

Обнаруженная коллизия вызывает ValueError с конкретным именем и двумя ролями. Пустые и non-string фактические имена тоже отклоняются явно. Строки не обрезаются и не переименовываются; уникальная whitespace-строка остаётся строкой. Ordered tuple/NumPy containers сохраняются там, где ранее поддерживались.

Treatment/oracle subset проверяется при construction и перед каждой generate attempt. Полная схема проверяется после успешного `_sample_X` и проверки его численной формы, до U, structural callbacks, назначения treatment и outcome. Дополнительно число confounder names должно совпадать с шириной X. Это использует реальные имена трёх разных sampling paths, сохраняя existing fallback/expansion rules.

Валидатор не меняет DataFrame insertion order, арифметику генерации, имена либо RNG на корректных схемах. Он не добавляет marginal propensity, selected ATT или новую assignment policy. Wrapper runtime forwarding не меняется; его docstring сообщает новый контракт.

## Проверки

Независимые baseline/current corruption probes и focused tests сохраняются в отдельных артефактах. Соседние B08 numeric/assignment/semantics/latent-oracle modules: **217 passed, 6.91 s**, raw [block09_neighbor_tests.log](block09_neighbor_tests.log). Это проверка рабочего patch до финального source checkpoint, не полная integration.

Общая integration и Linux matrix выполнены на committed source `1e2b544f7f91a57ad3e049572915a4b3891b084a`. Linux matrix: все6jobs/artifacts2039passed; local macOS:2038passed1подтверждённый baseline DiD failure,80warnings117.46s. Точные результаты и source SHA сохранены в [BLOCK09_NAMESPACE.md](BLOCK09_NAMESPACE.md), `block09_*_result.json` и [local failure note](B09_LOCAL_INTEGRATION_NOTE.md). Deferred sensitivity modules сохраняются ровно в прежнем scope; local suite не считается чистым.

## Следующий независимый дефект

Shared `_gaussian_copula` обращается к `u` в categorical branch до установки uniforms текущей координаты. Первый categorical вызывает UnboundLocalError; поздний categorical использует предыдущие continuous uniforms и искажает зависимость даже при identity correlation. Ошибка воспроизведена независимыми reviewer agents и записана в [B09_NAMESPACE_CONTRACT.md](B09_NAMESPACE_CONTRACT.md). Sampling algorithm не меняется внутри B09; такой сбой может произойти до полной namespace validation. Преобразование этой ошибки в ValueError не заявляется.

Sensitivity, SC08 leave-one-donor-out, full release и standalone Sphinx остаются вне блока. Upstream sync, PR, внешний documentation publish и release не выполняются.
