# Paired per-question comparisons under confirmed byte-identity (v0.4, NOT canon)

> Status: **experimental, ONE stand** (the reference stand only). NOT
> normative; NOT applied anywhere in this repo — the branch canon
> «per-question intersections are NOT interpreted» stays operative until
> owner canonization. **Into canon only after a SECOND stand reproduces the
> byte-identity result** (cross-stand determinism is untested:
> REPRODUCE.md §0, 2026-10-25 formulation). Owner decision pending.
> v0.1 → v0.2 (2026-10-25, owner-directed): status sharpened to
> experimental/one-stand; control panel defined by QUESTION IDS (panel-12 +
> attractor set); control-divergence consequence fixed (whole-window
> invalidation, byte-diff to log, aggregates only); stand checklist added.

## Current rule (branch canon, Oct 2026)

Per-question intersections between runs are NOT interpreted; numbers are
compared in bands and class compositions. Origin: the b3-empty-probe era —
9/11 empty questions did not reproduce between runs, attributed at the time
to GPU nondeterminism (annotated 2026-10-25: probable cause was shared
history tails, i.e. different prompts — `evals/results/g1iso_attractors_note.md`).

## Proposed rule (isolated runs, same reference stand, v0.2)

For runs under **per-question history isolation** (the post-`ffb5879` runner
family) on the **same reference stand**, paired per-question comparisons ARE
admissible when the control panel is byte-identical in the same time window:

1. **Control panel = two sets, by question ids** (not commit hashes):
   - the frozen 12-id verbatim pair-panel: `75832dbd, 0a34ad58, 1faac195,
     b0479f84, fca70973, 311778f1, afdc33df, 19b5f2b3, e47becba, 58bf7951,
     3b6f954b, faba32e5` (stable questions);
   - the attractor set from `run_g1iso_attractors.py`: `8cf51dda, cc539528,
     118b2229, 853b0a1d, e8a79c70, e48988bc, 4fd1909e` (+ its two stable
     controls `75832dbd, e47becba` when run standalone).
   The control runs use the SAME config family as the compared runs and dump
   raw extraction outputs (current tooling already does).
2. The control must come out **byte-identical** (raw extraction outputs)
   within the window.
3. Then paired per-question interpretation between the isolated runs is
   admissible (differences attributed to the runs' controlled deltas).
4. **If the control diverges**: paired per-question comparisons are
   **invalid for the WHOLE window**; the byte-diff goes to the log; any
   conclusion in that window — **aggregates only** (bands rule applies
   unchanged).

## Stand checklist (recorded per window, before the control counts)

- OS (kernel, distro);
- GPU driver version;
- llama.cpp build (build id / commit) and launch flags;
- runner file hashes (the evals/ scripts that executed);
- model file md5.

Reference values for the current stand: recorded per-run in the artifacts'
provenance blocks; the checklist makes them explicit per window so a future
second stand can be compared field-by-field.

## Boundary (why scoped)

- **One stand only**: canonization requires a second stand reproducing the
  byte-identity (until then: experimental).
- **Isolated runs only**: any run still carrying a history-tail channel has
  prompt variance by construction — the tail shifted fact vectors at
  ~135/156 questions (`evals/results/history_confound_forensics.md`,
  `g1iso_attractors_crosscheck.json`).
- **Evidence basis**: `results/g1iso_determinism_check.json` (panel-12,
  within and across restarts), `results/g1iso_attractors_crosscheck.json`
  (attractor questions, three server instances, same day).

## Effect if canonized

Unlocks paired per-question analysis for isolated same-stand comparisons
((ii)-line per-member deltas, worst-20 paired analysis, per-question
regression attribution) without N-repeat bands for every question — the
control panel carries the determinism burden once per window. Past preregs
keep their wording; future preregs cite this rule in their decision sections.

---

## v0.3 (2026-10-26, после зонда дрейфа; всё ещё NOT canon)

Дополнение к правилу — **длинные окна**: побайтовая идентичность — свойство
ОКНА последовательных прогонов, а не инстанса: во время 7-часового
full-500-iso произошла персистентная смена режима (2/12 стабильных вопросов
панели сменили выходы; смена переживает перезапуск сервера — свежий
экземпляр воспроизводит смещённые выходы; прежние не воспроизводятся;
`evals/results/drift_probe_note.md`). Правило v0.2 дополняется:

1. Контрольная панель сравнивается с эталоном ТОГО ЖЕ окна; эталон
   привязывается к окну (пере-привязка при смене режима = расхождение
   контроля с эталоном прошлого окна — это смена режима, не ошибка прогона).
2. Парные по-вопросные сравнения допустимы только внутри режима,
   подтверждённого собственным контролем окна.
3. Между окнами (и после длинной непрерывной нагрузки) — только агрегаты.

Статус unchanged: experimental, один стенд; в канон — только после второго
стенда. Шаги B/C (тесты cache_prompt) зонда не исполнялись по правилу
остановки; при санкции владельца — отдельный мини-зонд.

---

## v0.4 (2026-10-26, NOT canon): формальное определение окна + канарейка режима

Дополнение к v0.3 (границы окон были названы, но не определены операционально
— исправляет замечание ревью: «"внутри режима" — не проверяемое условие,
пока нет критерия границы окна»):

1. **Окно = серия прогонов между СОВПАВШИМИ контрольными панелями.**
   - Окно ОТКРЫВАЕТСЯ контрольной панелью, совпавшей с текущим эталоном
     (эталон привязан к окну — v0.3); окно ПРОДОЛЖАЕТСЯ, пока каждая
     очередная контрольная панель совпадает с эталоном окна; **первое
     расхождение контроля с эталоном = ГРАНИЦА ОКНА** — оно закрывает окно,
     открывает новое (с пере-привязкой эталона на новый вывод контроля) и
     логируется как событие смены режима.
   - Прогоны, начатые до пограничной контрольной панели, принадлежат
     закрывшемуся окну; их по-вопросные парные сравнения — только внутри
     их окна (v0.3 без изменений).
2. **Канарейка режима** (диагностическая метка, не разрешение):
   - состав: 2 известных режимо-различающих вопроса (по данным зонда дрейфа:
     `311778f1`, `faba32e5`) + 1 стабильный контроль (например,
     `e47becba`);
   - перед каждым прогоном пакета: короткий прогон канарейки, отпечаток
     (хеш выводов) — в заголовок отчёта прогона («режим: A/B/…»);
   - **совпадение канарейки НЕ разблокирует байтовые/по-вопросные сравнения
     между окнами** — правило v0.3 (агрегаты между окнами) остаётся
     единственным межоконным режимом; канарейка — метка для чтения отчётов
     и раннего обнаружения смены режима, не доказательство совпадения
     режимов на всех входах (3 вопроса не покрывают 12/9/500).
3. Статус unchanged: experimental, один стенд; в канон — только после
   второго стенда. Вопрос-состав канарейки (какие именно id различают
   режимы) может меняться с данными — фиксируется в артефактах, не в каноне.
