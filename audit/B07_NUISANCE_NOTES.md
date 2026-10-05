# B07: конечность предсказаний nuisance learners

**Статус: реализовано и локально проверено; итоговый source checkpoint и integration сообщает основной отчёт B07.** Проверка 2026-10-06, Windows, repo-local Python3.12.14, native threads1. Sensitivity modules/formulas/tests не менялись и специально не запускались.

## Подтверждённая ошибка — P2

Финитность исходных данных не гарантировала финитность выхода пользовательского learner. Binary/multi IRM проверяли итоговые cross-fitted массивы только на NaN. Положительная/отрицательная бесконечность в propensity или binary outcome могла превратиться в обычную вероятность при clipping; бесконечный continuous outcome оставался в fitted state и давал NaN estimate. Это реальная пропущенная проверка контракта, не изменение статистической формулы.

Независимый standalone probe до source patch использовал120 finite observations, seed931, clone-compatible custom learners и store_diagnostics=False. Binary/multi fit с g=+inf завершался успешно; estimate возвращал NaN. Binary m=+inf превращался в0.99, estimate.value=0.9261107040954353. Multiclass predict_proba=[inf,.25,.25] превращался в[2/3,1/6,1/6], estimates=[0.1468213136941522,-0.22170861737204328]. Эти числа иллюстрируют masking, а не подтверждают содержательный causal target такого learner.

Отдельно review выявил прежний supported fallback: classifier с одной probability column и отсутствующим classes_ вызывает predict(); np.where(isclose(pred,1),1,0) превращал NaN/±inf hard labels в0 ещё до финальной проверки. Public fit воспроизвёл этот путь и в binary IRM, и транзитивно в IIVM.

## Изменение

- [Binary prediction adapter](../causalis/scenarios/unconfoundedness/_utils.py) проверяет весь predict_proba output до выбора class1, predict result до clipping и числовые fallback hard labels до np.where.
- [Binary model](../causalis/scenarios/unconfoundedness/model.py) проверяет все g0/g1/m в storage посредством np.isfinite, до overlap policy и записи fitted nuisance arrays.
- [Multiclass prediction adapter](../causalis/scenarios/multi_unconfoundedness/_utils.py) проверяет весь raw probability matrix до class alignment, clipping и renormalization.
- [Multi model](../causalis/scenarios/multi_unconfoundedness/model.py) проверяет raw binary probability outputs до выбора класса, continuous/binary predicted outcome до clipping и оба cross-fit/storage boundaries.

NaN/±inf вызывают RuntimeError с non-finite и контекстом prediction method/role. Поведение **finite** outputs вне[0,1] сохранено: прежние warnings, clipping, row normalization и single-class mapping. Проверяется также невыбранная probability column: неконечный raw output не становится допустимым вследствие выбора другого класса.

Binary adapter переиспользуется IIVM. Поэтому его проверка распространяется на instrument m, treatment r и outcome g без правок IV source/formulas/lifecycle. Никакие score, IF, overlap thresholds, folds, estimands или finite probability policies не менялись.

## Проверка и честный учёт baseline

[104 новых cases](../tests/inference/test_nuisance_prediction_contract.py) включают public fit custom learners по трём типам модели, continuous/binary g и m, NaN/±inf, n_jobs1/2; IV r; raw unselected probability column; public fit с injected fold outputs для отдельной storage проверки; metadata fallback; finite out-of-range policies и single-class mappings. Шесть sklearn reference cases сравнивают finite predictions, score arrays и inference с независимым API adapter без finite rejection. Для binary проверяется сохранение full fold assignment; IV/multi successful folds покрываются также существующими neighbor tests. Input DataFrame сохраняется.

| Evidence | Результат | Интерпретация |
|---|---:|---|
| [Initial fixture run](block07_nuisance_initial_fixture_tests.log) |83failed,11passed,17.01s|Первый harness передавал IIVM unsupported store_diagnostics. Это сохранённый сырой лог, не количество ошибок библиотеки.|
| [Corrected main baseline](block07_nuisance_before_tests.log) |81failed,13passed,15.45s|50cases не отвергали non-finite;25 уже отвергали NaN с прежним текстом;6 прежних direct-storage probes дошли до unrelated missing fit metadata. Последний fixture затем заменён public fit.|
| [Exact previous storage methods](block07_nuisance_storage_before_tests.log) |15failed,79deselected,2.39s|Финальный public-fit fixture + exact c234e64 old methods:10 пропущенных infinity rejection,5 прежних NaN message-only failures,0fixture errors.|
| [Fallback baseline](block07_nuisance_fallback_before_tests.log) |6failed,4passed,94deselected,11.08s|Все6invalid hard-label public-fit probes не вызвали исключения;4finite mappings сохранены.|
| [First fix + broad focused neighbors](block07_nuisance_after_tests.log) |222passed,4warnings,20.90s|94new+128neighbor cases, до усиления storage fixture и добавления10fallback cases.|
| [Final fix + relevant neighbors](block07_nuisance_final_tests.log) |191passed,1warning,25.75s|104final new+87shared binary/IV helper neighbor cases;0failures/skips. Warning — существующий low relative-baseline guard.|

Counts разных runs пересекаются и не суммируются. Первоначальные83/81 failures включают test expectations/message/fixture differences; они не являются81new library bugs. Exact old-method probe загружает UTF-8 source commit c234e647e010f5d8bfb805af7ece61392e327537 в isolated Python process и заменяет только storage methods, не редактируя checkout. Script: [probe_block07_storage_baseline.py](probe_block07_storage_baseline.py). Machine-readable JUnit summary: [block07_nuisance_result.json](block07_nuisance_result.json).

Предыдущий intermediate94passed run после подготовки private storage metadata сохранён как [block07_nuisance_intermediate_storage_tests.log](block07_nuisance_intermediate_storage_tests.log). Окончательный fixture использует public fit и подтверждён final191passed run; intermediate не выдаётся за окончательную verification.

## Ограничения и отложенный scope

Это входной контракт выхода learner, а не гарантия конечности любых downstream floating-point computations. Огромные, но finite outcomes/predictions могут переполнить score arithmetic; отдельная политика extreme DGP inputs и overflow output guards остаётся follow-up. Generic failed-refit scalar/sensitivity cache invalidation не менялось. Малформированные shapes, complex learner outputs, class metadata и изменение finite clipping policy требуют отдельных контрактных решений и в этот patch не включены.

Finite/extreme configurations и callback outputs low-level DGP требуют отдельного input/output validation follow-up вместе с reference-law/propensity semantics. Они не включены в доказательства этого patch; здесь DGP code не меняется.

Primary reference на принцип проверки finite nuisance predictions: [DoubleML _checks.py](https://raw.githubusercontent.com/DoubleML/doubleml-for-py/main/doubleml/utils/_checks.py), _check_finite_predictions (root проверил2026-10-06). Это независимое подтверждение validity boundary, не заявление об одинаковом API/score/finite clipping policy.
