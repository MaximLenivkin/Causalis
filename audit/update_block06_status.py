"""Update continuation/status prose from final B06 evidence."""
import json
from pathlib import Path
import re

AUDIT = Path(__file__).resolve().parent
SOURCE = "09e00de5a9d3dc915c6d59627f8b0ebc875dd4e9"


if __name__ == "__main__":
    local = json.loads((AUDIT / "block06_integration_result.json").read_text())
    ci = json.loads((AUDIT / "block06_ci_result.json").read_text())
    assert local["tested_source_checkpoint"] == ci["tested_source_checkpoint"] == SOURCE
    assert local["passed"] == 1582 and local["exit_code"] == 0
    matrix_text = ("Все шесть clean Linux jobs и artifacts прошли; каждый — 1582 cases без failures/errors/skips."
                   if ci["matrix_verified"] else
                   f"CI verification пока pending: {ci['verified_successful_jobs']}/6 успешных jobs подтверждены. "
                   "На следующей итерации сначала завершить проверку matrix; pending не является pass.")
    status = (f"B06: implementation и локальная integration завершены: **1582 passed, 0 failed/skipped, "
              f"{local['warnings']} warnings, {local['pytest_elapsed_seconds']:.2f}s**. 206 новых cases, "
              "7 sensitivity modules явно исключены. Pydantic>=2, full release pytest gate, CI matrix, "
              "duplicate screening, linear binary detection, bounded Gaussian KDE и NumPy1.x IV fix. "
              f"{matrix_text} Финальный source09e00de; evidence в BLOCK06_COMPATIBILITY_PERFORMANCE.md. "
              "Owned arrays остаются audit-only; полный sensitivity/release/docs build не подтверждался.")

    path = AUDIT / "FIX_PLAN.md"
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^- B06:.*$", "- " + status, text, flags=re.MULTILINE)
    text = text.replace(
        "- B06 начат по новому запросу пользователя; финальный checkpoint и CI execution state сохраняются перед остановкой. Следующий feature block не запускается автоматически.",
        "- B06 завершён; следующий самостоятельный блок выбирается после нового запроса пользователя. Sensitivity по-прежнему отложена.")
    text = text.replace("Обновлён: 2026-10-05.", "Обновлён: 2026-10-06.")
    path.write_text(text, encoding="utf-8")

    continuation = f"""**B06 — финальное состояние.** {status}

Полный source/tests checkpoint `{SOURCE}`; после него меняются только audit artifacts. Commits: f31b743 (CI), 5977bb8 (duplicates), 74c0ff0 (binary), d292b3c (KDE), 1be6b67 (audit-only push filter), 50ad33e (benchmark/notes), 09e00de (IV compatibility). Final documentation commit определяется git log-1. Git author/auth/remotes прежние; повторная authorization не нужна.

Реальная legacy CI обнаружила 53 IV failures на NumPy1.26: Unicode array `+` не поддерживался. Installation прошла; canceled status исходного job не скрывает этот pytest failure. Исправлено np.char.add, добавлены13 fold/reference cases; actual fixed legacy source проверяется отдельно. Первоначальные integration1569 и matrix successes сохранены как initial/before_fix evidence; не смешивать их с final1582/09e00de.

Final matrix run **{ci['run_id']}**, exact source09e00de, snapshot {ci['snapshot_observed_at']}. {matrix_text} Full versions/JUnit/elapsed — block06_ci_result.json. Первые runs37371536543/37372133090 superseded config/fix pushes; prior legacy failure сохранён отдельно. GitHub runner-delay incident3q1yb5m7ltvb объясняет возможную очередь по внешнему статусу. Не делать бессмысленные reruns/смену Ubuntu labels. Final audit-only push не перезапускает матрицу.

Release runner defaultfull и **включает sensitivity**; не заменять на scoped для получения green. Branch correctness имеет ровно7 явных named exclusions; новый sensitivity test требует scope review. Docs extra не подтверждает Sphinx build (current docs test file без collected tests). Локальный env Python3.12.14, Windows, unchanged; нет pip/build/twine. Полный release/tag/PyPI не запускались.

Benchmark отдельно: baselinebf2ea87/currentd292, два последовательных fresh processes, seed731, native1. Constructor speed1.22–2.24×, IRM extraction1.37–4.14×; KDE30k×800 traced peak549.32→8.13MiB, max density difference5.88e-15. Matched IRM20k×8 fit1.24×, same folds/predictions/score/IF/ATE/SE. Tracemalloc не RSS; fit excludesconstruction/estimate. IV split fix не входит в measured operations, benchmark не повторяли. Owned candidate2.23/1.05/1.47× current extraction, audit-only без snapshot/invalidation contract.

**Следующий шаг:** отдельный backlog review: earliest universal DiD pre-cell, DGP marginal propensity/supplied-U/true-ATT semantics, finite/extreme output guards, numeric/object duplicate policy, public snapshot API и dedicated Sphinx build. Feature priorities: repeated cross-fitting → group/cluster-aware cross-fitting → external OOF → DR/R-CATE. Один новый block после запроса пользователя; ничего из этого не начиналось в B06. Sensitivity и SC08LOO остаются deferred до upstream sync.

"""
    path = AUDIT / "NEXT_SESSION.md"
    text = path.read_text(encoding="utf-8")
    start = text.index("**B06 implementation/local verification завершены**")
    stop = text.index("Документация для пересылки готова", start)
    text = text[:start] + continuation + text[stop:]
    text = text.replace(";49links,issues0,local-only linksнет", ";70links,issues0,local-only linksнет")
    path.write_text(text, encoding="utf-8")

    path = AUDIT / "README.md"
    text = path.read_text(encoding="utf-8")
    text = text.replace("Последний блок **B05 завершён**", "Предыдущий блок **B05 завершён**")
    text = text.replace("Следующий B06 compatibility/CI/performance начинается после нового запроса пользователя.",
                        "B06 compatibility/CI/performance завершён; актуальный результат ниже.")
    text = re.sub(r"^Текущий \*\*B06\*\*:.*$",
                  "Текущий **B06**: [BLOCK06_COMPATIBILITY_PERFORMANCE.md](D:/codex/Causalis/audit/BLOCK06_COMPATIBILITY_PERFORMANCE.md). "
                  + status + " [CI evidence](D:/codex/Causalis/audit/block06_ci_result.json).", text, flags=re.MULTILINE)
    path.write_text(text, encoding="utf-8")

    path = AUDIT / "PROGRESS.md"
    text = path.read_text(encoding="utf-8")
    text = text.replace("## 2026-10-05 — B06\n", "## 2026-10-05 — B06, первая проверка\n")
    text += f"""
## 2026-10-06 — B06, финальный checkpoint

- Реальная legacy matrix выявила NumPy1.x IV string-add bug:1516pass/53fail с одной причиной. Failure сохранён отдельно от canceled status job; latest-stack successes не считались доказательством старого stack.
- Commit09e00de исправил joint labels через np.char.add без смены split policy. До fix один simulated compatibility case упал; после focused156pass. Добавлены13cases, суммарно206new.
- {status}
- Raw initial/final integration, prior legacy failure, before_fix/current CI versions/JUnit и последовательный benchmark сохранены. Source/tests совпадают с09e00de; sensitivity paths0. DOCHANDOFF дополнен IV migration и immutable source/test links.
- Финальный audit commit и normal push сохраняют отчёт и continuation; remote/local equality проверяется на завершении. Новый feature block не начат, upstream не merge/rebase; PR/issues/externalmessages/release не создавались.
"""
    path.write_text(text, encoding="utf-8")
    print(json.dumps(dict(local_passed=local["passed"], matrix_verified=ci["matrix_verified"],
                          source=SOURCE, updated=["FIX_PLAN", "NEXT_SESSION", "README", "PROGRESS"])))
    path = AUDIT / "GIT_ACCESS.md"
    text = path.read_text(encoding="utf-8")
    start = text.index("## B06 checkpoint")
    text = text[:start] + f"""## B06 checkpoint

Финальный library/tests checkpoint `{SOURCE}` сохранён в личной ветке. Локально1582passed; {matrix_text} Exact CI run {ci['run_id']} использует09e00de. Commits f31b743/5977bb8/74c0ff0/d292b3c/1be6b67/50ad33e/09e00de; final documentation checkpoint — git log-1. После09e00de source/tests не меняются, толькоaudit artifacts; final audit-only push не запускает повторнуюmatrix.

Credentials/remotes/branch прежние. GitHub Actions enabled/workflow access подтверждены actualrun и artifacts. Release/tag/PyPI/PR/issues/externalmessages не создавались. Remote/local equality иcleanstatus проверяются после обычного finalpush; новой authorization не требуется.
"""
    path.write_text(text, encoding="utf-8")
