# B12: независимое review wrapper/conversion namespace

Review sign-off: **в шести изменённых library paths и новом test module открытых material findings нет (`issues: []`)**. Baseline: `eb6dfe23f0a97991b6e3d6109febc1b0170e128d`; source/test checkpoint: `0b30db33fd2593dc25ea1b823a91795c789e0191`. Применён навык `code-review`. Reviewer не менял library/tests/git state и не запускал full suite.

## Scope и проверенные инварианты

Просмотрен полный baseline-to-working-tree diff, затем его committed-byte linkage: shared `causalis/dgp/base.py`, binary base/functional/preperiod, IV base/functional и весь новый `tests/data/test_wrapper_namespace_contract.py` (162 cases). Прочитаны фактические callers: multi helpers, multi-outcome RCT и classic-RCT/CUPED scenario aliases; эти дополнительные paths остались неизменными.

Namespace checks резервируют только реально добавляемые pre/ancillary поля. Shared guards проверяют существующие labels, duplicate input labels, prospective additions и nonempty literal strings до helper callbacks/RNG. Pre helper проверяет namespace после mutable builder и непосредственно перед assignment; Tweedie helper проверяет до sampling и перед assignment. Prospective `_latent_A` конфликтует с pre только когда будет emitted.

Core snapshot содержит immutable sampled-name tuple и output-role tuple, captured непосредственно перед assembly и опубликованные только после successful generation. IV сохраняет actual instrument/oracle roles при late callbacks. Raw ordering проецирует каждый actual column один раз; отключённые oracle-looking names и numeric `user_id` сохраняются как features, instrument role сохраняется при `user_id` instrument. Только ancillary-added ID получает identifier role. Explicit direct feature selection сохраняется.

## Независимые runtime references

Frozen graph содержит 11 полных baseline modules: shared base; binary base/preperiod/functional; IV base/functional; multi base/functional; multi-outcome RCT; classic-RCT/CUPED scenario aliases. Compilation и runtime overlay `sys.modules` связывает old wrappers с old helpers/classes, включая dynamic imports. Old IV inheritance, class/helper identities проверены явно; old wrappers не используют новый общий helper.

**300 valid wrapper configurations** прошли точные old/current comparisons полного DataFrame: values, labels/order, dtypes, complete contract model metadata. Перехвачены все созданные `np.random.default_rng`, включая temporary samplers и wrapper/core streams; сравнивались их полные states и next 10 draws. Ancillary exact references используют deterministic IDs. Nondeterministic UUID identity не проверялась.

Основные 260 configs: RCT четыре family, pre/ancillary/oracle on/off и raw/contract; IV четыре family, independent/copula/custom X и ancillary/oracle/raw/contract; observational пять family; binary/Tweedie CUPED; classic aliases; multi четыре family. Дополнительные 40 boundary configs: multi-outcome RCT обе encodings, ID/oracle/contract flags и четыре outcome families вместе; classic/CUPED scenario aliases.

**80 valid core conversion configurations × 2 последовательные генерации = 160 exact frames**, с complete contract metadata и next 10 RNG draws. Binary continuous/binary/poisson/gamma/Tweedie gamma/Tweedie lognormal; IV continuous/binary/poisson/gamma; default/independent/copula/custom X; oracle on/off. Всего 460 exact frame comparisons. Валидные historical fixtures используют обычные feature names; исправляемые schemas с ранее потерянными disabled-oracle/user_id features отдельно проверяются как intended behavior changes, без blanket old=current claim.

Дополнительно прошли **45 rejection cases, 34 permitted-name/conversion cases, 6 core callback/success-snapshot cases, 5 wrapper/helper callback checks и 2 constructor checks**. Проверены disabled/unused pre names, actual-enabled collisions, direct helper frame/RNG invariance на early rejection, builder-created pre preservation, late IV instrument/include_oracle mutation, raw и contract wrappers до/после frame assembly, Tweedie callback-created pre preservation. Failed generation обоих семейств сохраняет previous-success snapshots. Runtime warnings: 0.

## Закрытые review findings

На раннем patch IV захватывал mutable sampler names после late callbacks: callback мог изменить внешний names list после assembly и вызвать conversion `KeyError`. Root перенёс immutable tuple capture перед assembly. Независимый subclass-sampler/callback regression теперь проходит: actual frame/snapshot/contract сохраняют исходное sampled name.

В раннем test fixture `_sample_X` присваивался slotted instance, что давало `AttributeError` до intended assertion. Regression agent заменил fixture class-level monkeypatch с automatic restore. Исправленные bytes просмотрены. Авторский evidence manifest на exact committed bytes подтверждает final baseline 136 failed/26 passed и focused 162 passed, 0 failures/errors/skips/warnings; reviewer эти pytest runs не повторял.

Добавлены два private dataclass fields с `init=False`, `repr=False`, `compare=False`, необходимые для slotted instances. Public constructor signatures old/current совпадают; `dataclasses.fields/asdict` намеренно включают private state. Изменение сериализации отражено явно, а не скрыто утверждением о неизменных dataclass fields.

## Подтверждённый residual за пределами B12

`causalis/scenarios/classic_rct/dgp.py::generate_classic_rct_26(n=256, seed=731, add_pre=True, pre_name='conversion', add_ancillary=False, return_causal_data=False)` создаёт valid underlying `y` и pre `conversion`, затем собственный late `y→conversion` rename возвращает два `conversion` labels. Frozen baseline и current одинаковы: `['user_id', 'conversion', 'd', 'platform_ios', 'country_usa', 'source_paid', 'conversion']`. Contract conversion отвергает duplicate labels. Нужен отдельный scenario-boundary follow-up; source scope не расширялся. CUPED26 имеет собственный reserved-name guard, его отсутствие не заявляется.

## Provenance и пределы вывода

`audit/block12_review_probe.json` хранит frozen module SHA256, current library SHA256, final test-module SHA256, exact configs/checks и `issues: []`. Все 11 referenced library files и final test module byte-for-byte сравнены с Git objects checkpoint `0b30db33fd2593dc25ea1b823a91795c789e0191`. Основной full reference process был precommit; committed bytes совпадают, поэтому повторный broad run не потребовался. Metadata refresh записал точный source checkpoint без утверждения о новом postcommit full process.

Воспроизведение: `.venv/bin/python audit/block12_review_probe.py` с native thread limits 1, Agg и `.venv/matplotlib`. Evidence: `block12_review_probe.py`, `block12_review_probe.json`, `block12_review_probe.log`. Все fixtures synthetic. Review не устанавливает numeric/finite-value policy, статистическую calibration guarantee, новые estimands, sensitivity validity или DiD readiness. Полная local integration принадлежит root.

## Независимая CI artifact verification

[GitHub Actions run 37598926037](https://github.com/MaximLenivkin/Causalis/actions/runs/37598926037) завершился `success` на точном source `0b30db33fd2593dc25ea1b823a91795c789e0191`. Read-only `gh run view --repo MaximLenivkin/Causalis --json headSha,url,status,conclusion,jobs` snapshot сохранён с `observed_at=2026-10-07T09:15:10.818155+00:00`. Reviewer скачал все шесть artifacts без workflow mutation/retrigger.

Для каждого Linux job проверены фактические `selection.json`, `result.json`, `junit.xml`: exact source checkpoint, Python stack, correctness selection, семь явных sensitivity deferrals, `collect_only=False`, `selected_full_suite=False`, `exit_code=0`. JUnit каждого artifact: **2397 tests / 2397 passed / 0 failures / 0 errors / 0 skipped**. Matrix: Python 3.10 legacy и 3.10/3.11/3.12/3.13/3.14 latest. Это шесть фактически выполненных jobs, а не вывод по workflow configuration.

Root summarizer `audit/summarize_block12_ci.py --run-id 37598926037 --source 0b30db33fd2593dc25ea1b823a91795c789e0191 --expected-tests 2397` и дополнительная per-job count проверка reviewer завершились успешно. `audit/block12_ci_result.json`: `verified_successful_jobs=6`, `matrix_verified=True`, `issues=[]`. Raw downloads/snapshot находятся в ignored `audit/block12_ci_test_temp/run-37598926037/`. CI вывод ограничен Linux и шестью representative stacks; sensitivity, standalone Sphinx build, release и все возможные dependency combinations не проверены.
