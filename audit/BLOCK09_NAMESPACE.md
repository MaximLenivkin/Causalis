# B09 · Уникальность имён multi-treatment DGP

Дата: 2026-10-06 (Europe/Moscow). Baseline: `74145665127f8fa5a0bf038d769697ab880854b8`. Ветка: `codex/correctness-roadmap`.

Реализация и focused проверки завершены; integration и GitHub matrix ещё проверяются. Scope — предотвращение перезаписи выходных столбцов в multi-treatment generator, без изменения sampling algorithm либо causal estimators.

Outcome, treatment, actual expanded confounders и включённые oracle columns теперь имеют единый namespace guard. Коллизия вызывает ValueError с именем и конфликтующими ролями. Непустые строковые имена сохраняются буквально; отключённые oracle и отсутствующий control CATE не резервируются. Проверки повторяются перед generate, включая изменённые публичные настройки.

Независимые regression tests: **123 passed, 3.65 s**. Точный baseline тех же tests на исходном generator/wrapper: **87 failed, 36 passed, 0.99 s**; это parameterized contract cases, а не 87 разных дефектов. Соседние numeric/assignment/semantics/latent-oracle tests: **217 passed, 6.91 s**. Counts пересекаются с будущей integration.

Детали: [implementation](B09_NAMESPACE_IMPLEMENTATION.md), [contract review](B09_NAMESPACE_CONTRACT.md), [new tests](../tests/data/test_multicausal_namespace_contract.py). Ожидаемый выбранный integration scope — 1916 прежних +123 новых cases. Проверка полного suite, sensitivity, standalone Sphinx и release не заявляется.

Отдельный подтверждённый residual — categorical Gaussian copula использует uniforms предыдущей координаты: первый categorical может вызвать UnboundLocalError; поздний искажает зависимость при identity correlation. Это следующий независимый sampling fix, вне B09. Полный namespace проверяется после успешного covariate sampling; этот старый сбой не переопределён.

Source/tests checkpoint, local integration и фактические CI artifacts будут добавлены после завершения проверки. На границе блока работа остановится по сохранённому правилу handoff.
