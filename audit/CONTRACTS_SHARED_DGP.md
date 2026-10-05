# Ревью data contracts, shared и DGP

Снимок: `ffe2c356c115f335b74b2f10117e19fe15585d46`, 2026-10-05. Исходники не исправлялись.
Проверки: `repro_contracts_shared.py`, `repro_dgp.py`; машинные результаты в одноимённых `results_*.json`.

## Подтверждённые находки

### ROOT-01 · P1 · Неверные natural-scale oracle means в multi-treatment DGP с латентным U

Источник: `causalis/dgp/multicausaldata/base.py:501`, `:519–527`.
При генерации outcomes используется `u_strength_y * U`, но `g_<arm>` и `cate_<arm>` вычисляются при U=0. Для nonlinear links это не интегрированный потенциальный outcome mean. Даже без confounding (`u_strength_d=0`) эффект не равен заявленной oracle CATE.

Воспроизведение: gamma outcome, baseline=0, theta=[0,1,2], `u_strength_y=1`, `u_strength_d=0`, 200 000 строк. Возвращаемый `g_d_0=1`, тогда как (E[Y(0)|X]=\exp(1/2)=1.64872\) (при используемом clipping хвостовая поправка здесь пренебрежимо мала). Наблюдаемое control mean=1.64102. Возвращаемый CATE=1.71828, правильный=2.83297. Это может исказить оценку bias/RMSE и ranking estimators в benchmarks.

Исправление: интегрировать U на natural scale (например, Gauss–Hermite, как в binary-treatment DGP) или явно переименовать эти величины в conditional means при U=0. Для user-supplied U дополнительно определить закон/условность oracle. При latent confounding отдельно различать (E[Y(d)|X]\) и (E[Y|D=d,X]\): они не совпадают автоматически.

### ROOT-02 · P2 · CausalData/IVCausalData и PanelDataSCM пропускают бесконечные outcomes

Источник: `data_contracts/causaldata.py:201–249`, `panel_data_scm.py:196–200`; IVCausalData наследует базовую проверку outcomes/X.
Проверки numeric dtype и isna недостаточно: `np.inf` не считается NaN. `CausalData` принимает outcome с Infinity, после чего `DiffInMeans().fit(...).estimate()` возвращает `value=Infinity`, `p_value=NaN`, оба CI=NaN. `PanelDataSCM` также принимает Infinity. RctCausalData и PanelDataDID уже имеют finite check: контрактная политика неодинакова.

Исправление: column-wise finite real check во всех contracts и finite guard в estimator output. Проверка должна быть до создания snapshot. Не заменять inf на 0: это изменяет данные/estimand.

### ROOT-03 · P2 · Complex numeric принимается контрактом для real-valued causal analysis

Источник: `data_contracts/causaldata.py:201`, `:222`, `:442`; аналогичная опасность float conversion в `multicausaldata.py:318/327` и `panel_data_did.py:327/338`.
CausalData принимает complex outcome, хотя текст ошибки ограничивает dtype int/float/bool. Fingerprint приводит его к float и отбрасывает imaginary часть с warning; t-test затем падает с TypeError. В проверке CausalData это подтверждено выполнением, для Multi/DID — статический риск такого же dtype admission, полный estimator repro не выполнен.

Исправление: явно отвергать complex dtype (RctCausalData уже делает это). Не считать float cast валидацией реальности.

### ROOT-04 · P2 · Shared balance возвращает SMD=0 при полном separation

Источник: `shared/confounders_balance.py:36–41`.
Пусть confounder `x=3+2*d`: внутри каждой группы variance=0, но control mean=3, treated mean=5. Возвращается `smd=0`, хотя разность=2 и группы полностью разделены. KS здесь отдельно обнаруживает различие, но SMD misleading и порядок сортировки неверен. Это связано с DML balance refutation, где Inf также может быть исключён из агрегирования и дать PASS (см. DML report).

Исправление: denominator=0 и equal means =>0; denominator=0 и unequal means =>signed Inf/явный severe flag. Nonfinite imbalance нельзя исключать как обычную недоступную статистику.

### ROOT-05 · P2 · Default UUID ID может массово нарушать собственный контракт

Источник: `dgp/base.py:115–118`; `dgp/causaldata/functional.py:112`, `:377`, `:408`.
`deterministic_ids=False` (default у legacy RCT generators) использует всего пять hex-символов UUID: 20 бит. При n=20 000 ожидается около 190.7 collision pairs. В выполненном raw generation получено 212 duplicate IDs; отдельный `generate_rct(..., return_causal_data=True)` падает с validation error duplicate user_id. `random_state` не управляет uuid4.

Исправление: полный UUID/достаточная длина с uniqueness check либо уникальная RNG permutation, уже реализованная `_deterministic_ids`. Указать воспроизводимость ID отдельно. Exact duplicate count случайно изменяется при rerun; причина и вероятность воспроизводимы.

### ROOT-06 · P2 · return_rows у outlier detector неверен на duplicate pandas index

Источник: `shared/outcome_outliers.py:164–165`.
Contract допускает duplicate index. Флаг выбран позиционно, но возвращаются `raw_df.loc[flagged_index]`: label может соответствовать нескольким строкам, включая невыбросы. В probe summary сообщает 1 выброс, результат содержит 2 строки с outcomes [0,100]. При повторении label в нескольких flagged rows возможны дополнительные дубли.

Исправление: сохранять boolean mask/row positions исходного frame и выбирать через iloc; альтернатива — явно запрещать nonunique index в API, но positional extraction лучше сохраняет поддерживаемые данные.

### ROOT-07 · P2 · NaN allocation weights принимаются splitter и дают пустое назначение

Источник: `shared/rct_design/split.py:31–40`, `:105–111`.
`variants={'control':np.nan,'treated':.5}` проходит validation (сравнения NaN с 0/1 дают False), затем cumulative становится NaN, и всем строкам присваивается None. Это не корректная coverage allocation.

Исправление: numeric finite checks до суммирования, запрет bool как weight если не предусмотрено контрактом. Проверять также missing entity IDs и структурную неоднозначность строкового составного ключа; последние два пункта — рекомендации, не воспроизведённые independent bugs.

### ROOT-08 · P2 · Dependencies не декларируют требуемую версию Pydantic

Источник: `pyproject.toml:53`, `data_contracts/causaldata.py:15`.
Разрешено любое `pydantic`, но `model_validator`, `field_validator` и ConfigDict требуют v2. В уже существующем окружении Pydantic 1.x dependency resolver может оставить установленную версию, которая удовлетворяет metadata, после чего import ломается. Подтверждено контрактом dependencies и API usage; отдельное v1 окружение не создавалось.

Исправление: задать проверенный minimum `pydantic>=2` (точный minor зависит от AliasChoices и остальных используемых API), добавить dependency bounds/compatibility matrix для действительно используемых возможностей и test install в чистом окружении.

### ROOT-09 · P2 · Release workflow не выполняет тесты

Источник: `.github/workflows/release.yml:17`, `:88–91`; см. также docs finding CONTRIBUTING.
Job называется «Test and build distributions», но исполняет install, verify tag, build, twine check; pytest шага нет. Поэтому failing tests не блокируют публикацию этого workflow. Это engineering release-control defect, не самостоятельная ошибка causal estimator.

Исправление: pytest до build/publish; CI на PR/main с dependency matrix; publish needs успешный test job. Одна версия Python 3.12 не подтверждает весь declared диапазон 3.10–3.14.

## Покрытие и то, что нельзя считать доказательством ошибки

- Инвентаризация и AST parse всех source modules — `MODULE_INVENTORY.csv`; static review затронул contracts CausalData/Multi/Rct/IV/PanelDID/PanelSCM, estimate/diagnostic containers, shared outcome/balance/clustering/SRM/SUTVA/planning/split и DGP families. Глубина максимальна в validation, data ownership, oracle quantities и shared numerical paths; plotting/formatting и некоторые DGP convenience wrappers проверены менее глубоко.
- Constant covariates и идентичные columns явно отвергаются контрактом. Это ограничение API, не скрытый баг. Возможное улучшение: warning+drop redundant covariates и отдельный strict mode.
- Frozen Panel contracts защищают validated snapshots. Public mutable DataFrame в других contracts требует осторожного cache design при оптимизации.
- RCT planning уже использует обе tails нормального power calculation, historical controls, checks rank/positive residual variance, exact total allocation для MDE и численную защиту размера. Общая future-arm variance и отсутствие multiplicity correction явно задокументированы: это modeling limitations, не отдельные «найденные ошибки».
- Correlation-based confounder clustering не определяет causal sufficiency и не даёт права выбирать adjustment set только по predictive importance.
- SUTVA helper — checklist, не statistical proof. Измерение confounders до treatment и общий measurement window полезны, но не составляют формальную SUTVA (consistency/treatment versions и interference); docs review рассматривает misleading claims отдельно.
- SRM использует unrounded p для decision и rounded p для output. Из-за округления displayed p может не точно отражать порог; это задокументированная reporting choice.

## Производительность

Измерения и отдельный top-10 безопасных оптимизаций находятся в `PERFORMANCE.md`. `to_numpy(copy=False)` не гарантирует zero-copy, особенно при mixed/extension dtype ([pandas API](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_numpy.html)). Ownership/индекс и causal score должны сохраняться в оптимизации.
