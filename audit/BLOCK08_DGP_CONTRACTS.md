# B08 · Контракты multi-treatment DGP и закон назначения

Дата: 2026-10-06 (Europe/Moscow). Исходный checkpoint: `b33922f1c0db8885ae9e8e071c45fc46de5205b6`. Ветка: `codex/correctness-roadmap`.

**B08 завершён.** Source/tests checkpoint: `9fb8041300410b560da80a45cabac4b541d1629d`, pushed в личный fork. После него только audit artifacts; final audit checkpoint — git log-1. Sensitivity analysis и SC08 leave-one-donor-out остаются отложенными.

## Ограниченный scope

1. Воспроизвести и исправить принятие non-finite параметров, X/U и callback outputs до sigmoid/exp clipping; проверить формы и конечность промежуточных/возвращаемых значений.
2. Сделать политику назначения явной: default `ensure_all` сохраняет совместимость; opt-in `iid` делает единственную независимую выборку без гарантии наличия каждого arm.
3. Исправить fallback `ensure_all`, который мог удалять последний пример существующей группы при вставке отсутствующей.
4. Проверить исходные успешные finite конфигурации, RNG/schema и независимые reference draws; выполнить integration и CI на committed source, сохранить переносимые документационные исправления.

Marginal Gaussian propensity, calibration under latent integration и selected ATT не входят в B08: сначала необходимо отдельно определить numerical accuracy policy и API. Числа B06/B07 не служат результатами новых проверок.

## Независимые воспроизведения

Contract review: `alpha_y=inf` при binary outcome возвращал конечный frame с y=1; `g_y(X)=inf` при gamma outcome скрывался за exponential clipping; `gamma_shape=inf` возвращал NaN outcome. Неиспользуемый infinite X мог попасть в возвращённый DataFrame. Это ошибки валидации, а не новые ошибки статистических формул.

Sampling review: при `n=3`, `k=0`, `alpha_d=[0,0,-1000]`, supplied U=0, seed3 старый fallback возвращал counts `[0,2,1]`, хотя обещал наличие всех классов; inserted arm2 имеет nominal propensity0. Retry/forcing также меняют joint assignment law. `m_obs` описывает исходные row probabilities, а не вероятность назначения после coverage conditioning/repair.

Семантика finite-check соответствует [NumPy isfinite](https://numpy.org/doc/2.3/reference/generated/numpy.isfinite.html). Определение вероятностной выборки сверялось с [NumPy random sampling](https://numpy.org/doc/stable/reference/random/index.html); различие conditioned и iid law следует непосредственно из алгоритма повторной выборки.

## Результаты и продолжение

Добавлены **187 cases**:112 contracts и75 assignment policy. Final focused:149passed/1ожидаемое overflow warning/46.14s (112+37neighbors) и75passed/0warnings/8.45s; counts пересекаются с integration, не суммировать.

Точные baseline replays без замены checkout файлов: final contracts112cases на B07 дают100failed/12passed/36warnings/7.00s; final sampling75cases на exact B07 generator+wrapper дают29failed/46passed/2.33s. Из sampling failures19 показывают один coverage defect в разных случаях,10 проверяют новый отсутствовавший API. Это не129разных bugs. Первоначальные21contractcases17failed/4passed сохранены отдельно; mixed-state pre-policy sampling run и ошибочная regex expectation не служат exact baseline.

Independent old/current finite reference:16configs (4families×oracleonoff×customcallbackonoff), exact values/schema и следующие10RNGdraws. First-success assignment и safe historical fallback дополнительно сверены с независимыми draw/RNG references. Ошибочные repairs теперь могут менятьlabels/RNG; opt-in iid намеренно меняет sampling law.

Подробные notes: [B08_CONTRACT_REVIEW.md](D:/codex/Causalis/audit/B08_CONTRACT_REVIEW.md), [B08_SAMPLING_REVIEW.md](D:/codex/Causalis/audit/B08_SAMPLING_REVIEW.md), [B08_METHOD_REVIEW.md](D:/codex/Causalis/audit/B08_METHOD_REVIEW.md). Raw final logs: [contracts](D:/codex/Causalis/audit/block08_contract_final_tests.log), [sampling](D:/codex/Causalis/audit/block08_sampling_final_tests.log). Seeded reference: [JSON](D:/codex/Causalis/audit/block08_finite_reference_result.json).

## Actual CI evidence

**Local integration:**1916passed,0failures/errors/skips,78warnings,400.69s,exit0; Windows/Python3.12.14, native1/Agg. 187newcases включены;1729B07+187=1916. Один новый warning — deliberately overflowing matmul regression с проверкой contextualValueError;77прочих были вB07. Source/tests совпадают с checkpoint9fb8041 после run. Evidence: [raw log](D:/codex/Causalis/audit/block08_integration_tests.log), [selection](D:/codex/Causalis/audit/block08_integration_selection.json), [result](D:/codex/Causalis/audit/block08_integration_result.json). JUnit вignoredblock08_integration_test_temp/junit.xml. Семь exclusions перечислены вselection; scoped_suite_clean=true,full_suite_clean=false,sensitivity_validated=false.

[Run37420288433](https://github.com/MaximLenivkin/Causalis/actions/runs/37420288433) completed/success на exactsource9fb8041. Проверены downloaded selection/environment/JUnit/result artifacts всех6Linuxjobs: Python3.10–3.14latest-compatible и3.10legacy. Каждый **1916passed,0failures/errors/skips**. [block08_ci_result.json](D:/codex/Causalis/audit/block08_ci_result.json): matrix_verified=true, verified_successful_jobs=6,issues0; полный versions/timing/snapshot вJSON. Это representative stacks, не все сочетания dependencies/OS. Семь named sensitivity modules исключены, standaloneSphinx/release не подтверждены.

## Закрытые findings и совместимость

Все четыре группы — **P2**: некорректные numeric/callback values могли скрываться за bounded links; некорректные формы U/X и параметры приводили к corrupt frame/incidental errors; huge finite target weights переполнялись при нормализации; fallback мог удалять последний пример другого arm. Изменение nominal assignment law — существующая особенность legacy policy, теперь явно документированная и снабжённая iid альтернативой.

Real finite values проверяются до преобразований; complex coefficients отклоняются до float casts. Finite scores, outcome links, draws, g/cate проверяются по границам вычислений. ScalarU broadcasting сохранён, (n,), (n,1), (1,n) нормализованы; baseline callbacks scalar/(1,)/(n,) и tau outputs с n elements сохранены. k=0 и sigma_y=0 остаются допустимыми. target normalizing arithmetic сохраняется при finite sum; max scaling включается только при overflow sum.

`assignment_policy` добавлен в конец старых init/wrapper parameter lists. Default ensure_all требуетn>=K, сохраняет10attempts и safe insertion proposals; новые replacement draws только для singleton-erasing proposals. iid permits positive n<K и missing arms в rawDataFrame. MultiCausalData и downstream estimators сохраняют собственные требования; multiple absent arms могут нарушать separate duplicate-column contract. Нет новой Gaussian-marginal propensity/latent-selectedATT promise.

## Ограничения и приоритет следующего блока

1. **P2, подтверждено: namespace collisions**. d_names=['y','arm'] overwrites outcome; confounder name'd_0' overwrites treatment; confounder'g_d_0' overwritten by oracle. Следующий ограниченный correctness block: validate complete generated namespace (включая expanded categorical names/oracles), fail clearly вместо silent suffixing. Detailed reproductions в method review.
2. **Extreme finite Gaussian oracle arithmetic**: square representability overflow теперь explicitValueError; конечность не доказывает arbitrary-strength accuracy. При strength1e8 exploratory reference difference~6.46e-9relative; robust bounded integration/accuracy policy отдельно. Не вводилась blanketnan_to_num/новаяlatentlaw.
3. **Другие DGP модули и confounder-spec parameter validation**: новый центральный finite boundary не является comprehensive hardening всех generators. Также остаются learner shape/IVstorage, finite score arithmetic и Sphinx gate из FIX_PLAN.
4. **Feature oracle**: include_marginal_propensity, actuallatent calibration и selectedATT остаются отдельным API/numerics block после contracts. B07 proposal сохраняется.

Скорость не измерялась; B06benchmark исторический. DML/DiD/IVscores, IF, inference и sensitivity source/tests не менялись. Standalone Sphinx, full sensitivity/release и upstream sync не выполнялись.

## Handoff и завершение

[DOCUMENTATION_HANDOFF.md](D:/codex/Causalis/audit/DOCUMENTATION_HANDOFF.md) содержит готовые тексты по policies, finite/shapecontracts, targetcalibration и limits;85immutableGitHublinks проверены,issues0. [NEXT_SESSION.md](D:/codex/Causalis/audit/NEXT_SESSION.md) содержит актуальный checkpoint и задачу следующего блока. Проверка artifacts/source/JUnit/CI/reference/scope выполняется verify_block08.py; итогJSON/log сохраняют actualcounts. Finalauditcommit/push не запускает новую matrix. На границе B08 остановиться; следующий блок только по новому запросу.

Finalartifactverification: issues0,10PythonASTfiles,36localartifactlinks,2librarypaths,2newtestfiles,187newJUnitcases,16exactfiniteconfigreferences,6verifiedCIjobs и0sensitivitypaths. Evidence:block08_validation_checks.json/log. Source/tests после integration не менялись; finalauditcommit содержит толькоauditfiles, ignoredtesttemps не сохраняются.
