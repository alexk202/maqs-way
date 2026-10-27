# Paired per-question comparisons under confirmed byte-identity (v0.5, NOT canon)

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

---

## v0.5 (2026-10-26, по ответам Совета; всё ещё NOT canon)

Исправление правила принадлежности окна (v0.4 говорила «прогоны, начатые до
граничной контрольной панели, принадлежат закрывшемуся окну» — это неверно:
разошедшийся контроль ПОСЛЕ прогона оставляет режим прогона неизвестным):

1. **Прогон принадлежит окну, только если обрамлён СОВПАВШИМИ контролями ДО
   и ПОСЛЕ** (контроль до = открытие окна; контроль после = подтверждение,
   что режим не сменился в течение прогона). Контроль ПОСЛЕ разошёлся →
   **режим прогона неизвестен** → любые по-вопросные выводы о нём
   запрещены; допускаются **только агрегаты**.
2. **«Совпадение» = побайтная идентичность ВСЕХ выходов панели** (raw
   extraction-выходы каждого вопроса; эквивалентные чеки — stored texts и
   frames). **Одно расхождение = граница окна** (частичного совпадения нет).
3. **Канарейка — в каждом прогоне**: метка режима (fingerprint выводов
   канарейки) печатается в заголовке отчёта каждого прогона — диагностическая
   метка, не разрешение (v0.3/v0.4 правила о межоконных агрегатах без
   изменений).

---

## v0.6 (2026-10-27): ВТОРОЙ СТЕНД — побайтовая идентичность воспроизведена (iGPU, Vulkan0)

Формальный запуск пункта «Into canon only after a SECOND stand reproduces the
byte-identity result» (status-строка вверху). Второй стенд = встроенная
графика Intel Arc (Core Ultra 9 185H), устройство Vulkan0 в нумерации
llama-server; llama.cpp сборка 9177, те же флаги, что RTX-стенд (кроме
`--device Vulkan0`, порт 8087), seed 42, та же модель (md5 6eb593f3…).
Prereg: `evals/prereg-stand2-igpu.md` (коммит до запуска).

**Протокол**: панель-12 (конфиг g1-iso, изоляция по вопросам, H5-гард):
канарейка → проход 1 → канарейка → проход 2 (один экземпляр сервера) →
перезапуск сервера → канарейка → проход 3 (свежий экземпляр).

**Результат**: проходы 1–2 подряд побайтно идентичны **12/12** (raw + stored +
frames); проход 3 после перезапуска идентичен проходам 1–2 **12/12** (raw +
stored + frames). Критерий prereg ВЫПОЛНЕН. Диагностические отпечатки
канарейки зафиксированы в каждом проходе (проход 2 отличается — накопление
стора канарейки внутри инвокации; метка, не разрешение). Сравнение с RTX-
эталоном не выполнялось (по ТЗ — не критерий).

**Эвиденс**: `evals/results/stand2_igpu_panel12_A.json`, `…_B.json`,
`stand2_igpu_determinism_check.json`, `stand2_igpu_note.md`.

**Статус**: cross-stand воспроизведение зафиксировано; канонизация по-прежнему
только решение владельца (status-строка вверху не меняется — append-only).

