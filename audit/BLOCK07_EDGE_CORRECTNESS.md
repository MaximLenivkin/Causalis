# B07 — граничные случаи DiD и nuisance predictions

Дата: 2026-10-06 (Europe/Moscow). Начальный checkpoint: `c234e647e010f5d8bfb805af7ece61392e327537`; ветка `codex/correctness-roadmap`.

## Scope и порядок

1. **B07-DID, P2:** восстановить earliest universal pre-treatment comparison. Фиксированный base не требует периода до target; varying base по-прежнему требует его. Проверить support, модель, event/diagnostic tables, missing pairs, anticipation, короткое pre-window и сохранение post-treatment inference.
2. **B07-NUISANCE, P1:** binary/multi IRM должны отклонять NaN и бесконечные прогнозы до clipping/normalization и сохранения. Сейчас infinity может превращаться в допустимую propensity/outcome probability или сохраняться как continuous outcome prediction. Сохранить существующую политику для конечных прогнозов и сверить нормальный fit с независимой прежней реализацией.
3. Независимое ревью DGP oracle semantics подготовит следующую задачу. Изменение смысла `m_<arm>` и новый marginal-propensity API в этот блок не входят.

Каждый fix: воспроизведение до patch → independent regression/reference → patch → focused neighbors → отдельный commit. Затем integration с прежними семью явными sensitivity exclusions, portable documentation handoff, итоговый отчёт, continuation и push в личный fork.

Sensitivity analysis, SC-08 leave-one-donor-out, generic sensitivity/refit lifecycle, новые causal estimators, snapshot API и docs-build gate остаются вне B07. Полный исторический аудит не повторяется. Реальные результаты и commit SHA будут дописаны по завершении.

## Progress

- Начало: workspace чист, local HEAD/tracking/remote SHA совпадают; авторизация и personal fork действуют.
- Подтверждён DiD enumeration defect; primary reference проверен: [официальный did::att_gt](https://bcallaway11.github.io/did/reference/att_gt.html) и [compute.att_gt](https://raw.githubusercontent.com/bcallaway11/did/master/R/compute.att_gt.R). Universal и varying используют разные начальные targets; это не заявление о полной идентичности R/Python inference.
- Три параллельных subagents: независимые DiD tests, nuisance boundary fix, read-only DGP follow-up. Root: scope, DiD implementation, review, integration и Git checkpoints.

## Результаты

Работа выполняется. Итог будет записан после фактических проверок.
