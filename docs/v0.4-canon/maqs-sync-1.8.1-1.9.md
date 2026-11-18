Status: подготовлено для подписи владельца к релизу v0.4. Канон (SPEC.md,
SPEC-RU.md, maqs-way-standard.json) этим файлом НЕ меняется: файл содержит
текст на подпись и точные места его применения.

# Синхронизация формулировок MAQS 1.8.1/1.9 в канон — текст на подпись (v0.4), часть 1

Источник: `docs/v0.4-candidates-from-maqs-1.8.1.md`, строки 1, 8–13, 15–17.
Строки 2, 3, 5, 6, 7 и часть 12/13 уже применены вне канона коммитами
`a22f042`, `e3b66ef`, `8d9304b` (файлы требований в `schemas/`, подписи не
требовали). Строки 4 и 14 (D8, D10) каноном не покрываются и записываются
как открытые пробелы с переносом в v0.5 — это делается в пакете стампов
вместе с переписыванием §6. Ссылка на ядро MAQS 1.9 → 1.10 подготовлена
отдельным файлом `docs/v0.4-canon/maqs-core-ref-1.10.md`.

Модель данных не затрагивается: `schema_version way-v0.1.3` остаётся
заморожённой, новых полей ядра не вводится. Всё ниже — расширения политики
и профиля (`extensions.policy` / `extensions` в maqs-way-standard.json).

## Формат

Каждая правка — пара «Заменить» / «На». Строка в блоке «Заменить» взята из
файла дословно на коммите `8d9304b` и встречается в нём **ровно один раз**;
применение — точная замена, а не поиск места по смыслу. Переносы строк
внутри блоков значимы.

Проверено до подписи: все 29 замен применяются по одному разу, и после их
применения `check_release.py --target 0.3 --prev 0.2.1` остаётся RELEASE
GREEN, гигиена конвейера GATE GREEN, name_guard без утечек.

## Состав

| № | файл | место | источник |
|---|---|---|---|
| 1 | `SPEC.md` | §3.5, строка j3_guard | 1 (J3) |
| 2 | `SPEC-RU.md` | §3.5, строка j3_guard | 1 (J3) |
| 3 | `SPEC.md` | §3.5, блок P10 | 12 (P10) |
| 4 | `SPEC-RU.md` | §3.5, блок P10 | 12 (P10) |
| 5 | `SPEC.md` | §3.5, новые блоки P11 и «доказательства аудита» + строка параметров | 11, 8, 9, 10 |
| 6 | `SPEC-RU.md` | §3.5, новые блоки P11 и «доказательства аудита» + строка параметров | 11, 8, 9, 10 |
| 7 | `SPEC.md` | §3.5, отложенный список | — |
| 8 | `SPEC.md` | §1, свойство P4, строка Verification | 15 (D11) |
| 9 | `SPEC-RU.md` | §1, свойство P4, строка Верификация | 15 (D11) |
| 10 | `SPEC.md` | §2.5, новый пункт C4 после пункта D8 | 16 (C4) |
| 11 | `SPEC-RU.md` | §2.5, новый пункт C4 после пункта D8 | 16 (C4) |
| 12 | `SPEC.md` | §2.4, новый пункт A4 после пункта E12 | 17 (A4) |
| 13 | `SPEC-RU.md` | §2.4, новый пункт A4 после пункта E12 | 17 (A4) |
| 14 | `SPEC.md` | §3.2, блок 0.5a | 13 (0.5a) |
| 15 | `SPEC-RU.md` | §3.2, блок 0.5a | 13 (0.5a) |
| 16 | `SPEC.md` | §3.2, отложенный список | — |
| 17 | `SPEC-RU.md` | §3.2, отложенный список | — |
| 18 | `SPEC.md` | §3.4, отложенный список (счётчики) | — |
| 19 | `SPEC-RU.md` | §3.4, отложенный список (счётчики) | — |
| 20 | `SPEC.md` | §3.4, отложенный список (обработчики) | — |
| 21 | `SPEC-RU.md` | §3.4, отложенный список (обработчики) | — |
| 22 | `SPEC.md` | §3.4, отложенный список (слои) | — |
| 23 | `SPEC-RU.md` | §3.4, отложенный список (слои) | — |
| 24 | `SPEC-RU.md` | §3.5, отложенный список | — |

---

## 1. §3.5, строка j3_guard — `SPEC.md`, источник: 1 (J3)

**Заменить (в файле ровно одно вхождение):**

```text
j3_guard: every fix closed with regression guard test; unexecuted test (silent skip, async without runner) = incomplete (MAQS J3)
```

**На:**

```text
j3_guard: every fix closed with regression guard test; unexecuted test (silent skip, async without runner) = incomplete (MAQS J3). "Executed" means the verdict reached the scoring channel and cannot be silently ignored: exactly one verdict channel (a dual runner where each side ignores the other's result is a false green), deterministic execution (no races with background workers, no side effects on shared process state), the guard operating on schema and state produced by the real migration path, and assertions on behavior rather than on source text. Inherited criticality: a J3 failure is scored [CRIT] when the guarded incident belongs to a [CRIT] item and [IMP] otherwise (precedent: I10, warnings in [CRIT] zones)
```

---

## 2. §3.5, строка j3_guard — `SPEC-RU.md`, источник: 1 (J3)

**Заменить (в файле ровно одно вхождение):**

```text
j3_guard: каждое исправление закрывается регрессионным guard-тестом; невыполненный тест (silent skip, async без runner) = незавершено (MAQS J3)
```

**На:**

```text
j3_guard: каждое исправление закрывается регрессионным guard-тестом; невыполненный тест (silent skip, async без runner) = незавершено (MAQS J3). «Выполнен» означает, что вердикт дошёл до канала подсчёта и не может быть молча проигнорирован: ровно один канал вердикта (двойной раннер, где каждая сторона игнорирует результат другой, — ложный зелёный), детерминированное исполнение (без гонок с фоновыми рабочими, без побочных эффектов на разделяемое состояние процесса), guard работает на схеме и состоянии, созданных реальным путём миграции, и проверяет поведение, а не текст исходника. Наследуемая критичность: провал J3 оценивается как [CRIT], если охраняемый инцидент относится к пункту [CRIT], и как [IMP] иначе (прецедент: I10, предупреждения в зонах [CRIT])
```

---

## 3. §3.5, блок P10 — `SPEC.md`, источник: 12 (P10)

**Заменить (в файле ровно одно вхождение):**

```text
FAILS P10. Write
```

**На:**

```text
FAILS P10. A declared read-only mode is not isolation: a dependency carrying a
lazy-initialization write path — table creation, seed data — writes to
the live store on first invocation even under `mode=ro`. Isolation is
established by the snapshot, not by the declared mode. Write
```

---

## 4. §3.5, блок P10 — `SPEC-RU.md`, источник: 12 (P10)

**Заменить (в файле ровно одно вхождение):**

```text
ПРОВАЛИВАЕТ P10. Право записи
```

**На:**

```text
ПРОВАЛИВАЕТ P10. Объявленный режим только для чтения изоляцией не является: зависимость с
путём ленивой инициализации — создание таблиц, засев данных — пишет в
живое хранилище при первом вызове даже под `mode=ro`. Изоляция
устанавливается снимком, а не объявленным режимом. Право записи
```

---

## 5. §3.5, новые блоки P11 и «доказательства аудита» + строка параметров — `SPEC.md`, источник: 11, 8, 9, 10

**Заменить (в файле ровно одно вхождение):**

```text
P9/P10 declare no tunable numeric parameters: their parameters are
```

**На:**

```text
**P11 — Agent audit discipline (MAQS §2.1, Step P11).** An auditing
agent must not invoke any method of the audited system that has write
side effects on live stores — including methods whose write is
incidental (counters, caches, lazy initialization). Diagnostic probes
run on file-level copies of the stores, never on the live ones. Any
exception is justified in the report and verified by before/after
counters on every affected store; an exception without counters is RED.

**Audit evidence and criticality counting (MAQS §2.2, steps 3 and 6,
item 4).** Evidence must establish that the claimed defect is reachable,
not merely that a pattern is present: gate conditions — flags, callers,
enclosing scopes, per-instance schema — are part of the evidence. Schema
and key claims are verified per instance by querying the catalog, never
inferred from naming. A verdict reached by reading alone is labeled
"static implementation evidence". A verdict later found false is
corrected in the same report, not in a separate note. Criticality is
counted separately: failures and partial implementations never merge
into one number, per-section codes reconcile to the totals without
intersections, and the counting is reproducible by the reader. An item
may state that its failure inherits the criticality of the item it
protects; the auditor records the inherited level and names the
protected item.

P9/P10/P11 declare no tunable numeric parameters: their parameters are
```

---

## 6. §3.5, новые блоки P11 и «доказательства аудита» + строка параметров — `SPEC-RU.md`, источник: 11, 8, 9, 10

**Заменить (в файле ровно одно вхождение):**

```text
P9/P10 не объявляют настраиваемых числовых параметров: их параметры —
```

**На:**

```text
**P11 — Дисциплина агента-аудитора (MAQS §2.1, шаг P11).** Агент,
проводящий аудит, не вызывает ни одного метода аудируемой системы,
имеющего побочные эффекты записи в живые хранилища, — включая методы,
где запись побочна (счётчики, кэши, ленивая инициализация).
Диагностические зонды выполняются на файловых копиях хранилищ, а не на
живых. Любое исключение обосновывается в отчёте и подтверждается
счётчиками до и после по каждому затронутому хранилищу; исключение без
счётчиков — RED.

**Доказательства аудита и подсчёт критичности (MAQS §2.2, шаги 3 и 6,
пункт 4).** Доказательство обязано устанавливать достижимость
заявленного дефекта, а не только наличие образца: условия срабатывания —
флаги, вызывающие, объемлющие области, схема по каждому экземпляру —
входят в доказательство. Утверждения о схеме и ключах проверяются по
каждому экземпляру запросом к каталогу, а не выводятся из имён. Вердикт,
полученный только чтением, помечается как «статическое доказательство
реализации». Вердикт, впоследствии признанный неверным, исправляется в
том же отчёте, а не отдельной запиской. Критичность считается раздельно:
провалы и частичные реализации не сливаются в одно число, коды по
разделам сходятся с итогами без пересечений, подсчёт воспроизводим
читателем. Пункт может оговорить, что его провал наследует критичность
пункта, который он защищает; аудитор фиксирует наследуемый уровень и
называет защищаемый пункт.

P9/P10/P11 не объявляют настраиваемых числовых параметров: их параметры —
```

---

## 7. §3.5, отложенный список — `SPEC.md`, источник: —

**Заменить (в файле ровно одно вхождение):**

```text
Deferred (v0.4 list): P10 — lazy-initialization write paths (`mode=ro`
alone is not isolation); P11 — agent audit discipline.
```

**На:**

```text
Deferred list: none — both entries (P10 lazy-initialization write
paths, P11 agent audit discipline) are closed in this release.
```

---

## 8. §1, свойство P4, строка Verification — `SPEC.md`, источник: 15 (D11)

**Заменить (в файле ровно одно вхождение):**

```text
access after revocation.
```

**На:**

```text
access after revocation. Scope isolation in a shared retrieval index is part of this property: per-scope filtering is applied before the top-K cut, or the extraction window is proportionally oversized — selecting top-K globally and filtering afterwards lets other scopes' records consume the result window with no visible error (MAQS D11 [IMP]; Way side: evaluator check P4a, cheatsheets `pattern-mem0-isolation` / `pattern-graphiti-invalidation`). This is slot displacement, not cross-scope data access (G2), and it is verified structurally, not by observed hit rates.
```

---

## 9. §1, свойство P4, строка Верификация — `SPEC-RU.md`, источник: 15 (D11)

**Заменить (в файле ровно одно вхождение):**

```text
доступ после отзыва.
```

**На:**

```text
доступ после отзыва. Изоляция областей в общем индексе выборки входит в это свойство: фильтрация по области применяется до среза top-K либо окно извлечения пропорционально увеличивается — выбор top-K глобально с фильтрацией после позволяет записям чужих областей занимать окно результатов без видимой ошибки (MAQS D11 [IMP]; на стороне Way: проверка оценщика P4a, шпаргалки `pattern-mem0-isolation` / `pattern-graphiti-invalidation`). Это вытеснение слотов, а не кросс-областной доступ к данным (G2), и проверяется структурно, а не по наблюдаемым hit rate.
```

---

## 10. §2.5, новый пункт C4 после пункта D8 — `SPEC.md`, источник: 16 (C4)

**Заменить (в файле ровно одно вхождение):**

```text
- **D8 incompatible embeddings (MAQS D8 [CRIT]):** dimension/language mismatch → explicit rejection with diagnostics, not a burst of warnings during search; re-index or migrate before mixed-model retrieval.
```

**На:**

```text
- **D8 incompatible embeddings (MAQS D8 [CRIT]):** dimension/language mismatch → explicit rejection with diagnostics, not a burst of warnings during search; re-index or migrate before mixed-model retrieval.
- **C4 derived-representations sync (MAQS C4 [CRIT]):** every derived representation — vectors, re-embedded chunks, summaries, caches — is synchronized on content updates and on identifier-schema migrations, not only on deletion; synchronization is verified by set difference between the source and the derived store, and a migration stamp is invalidated by a schema change.
```

---

## 11. §2.5, новый пункт C4 после пункта D8 — `SPEC-RU.md`, источник: 16 (C4)

**Заменить (в файле ровно одно вхождение):**

```text
- **D8 несовместимые эмбеддинги (MAQS D8 [CRIT]):** несовпадение размерности/языка → явный отказ с диагностикой, а не всплеск предупреждений при поиске; перед смешанным поиском — переиндексация или миграция.
```

**На:**

```text
- **D8 несовместимые эмбеддинги (MAQS D8 [CRIT]):** несовпадение размерности/языка → явный отказ с диагностикой, а не всплеск предупреждений при поиске; перед смешанным поиском — переиндексация или миграция.
- **C4 синхронизация производных представлений (MAQS C4 [CRIT]):** каждое производное представление — векторы, переэмбеддингованные фрагменты, суммаризации, кэши — синхронизируется при изменении содержимого и при миграции схемы идентификаторов, а не только при удалении; синхронность проверяется разностью множеств между источником и производным хранилищем, а отметка миграции аннулируется изменением схемы.
```

---

## 12. §2.4, новый пункт A4 после пункта E12 — `SPEC.md`, источник: 17 (A4)

**Заменить (в файле ровно одно вхождение):**

```text
- **E12 artifact precedence (MAQS E12):** current artifact retains factual precedence over memory; conflict stays observable, memory must not silently substitute or reconstruct the artifact representation.
```

**На:**

```text
- **E12 artifact precedence (MAQS E12):** current artifact retains factual precedence over memory; conflict stays observable, memory must not silently substitute or reconstruct the artifact representation.
- **A4 degraded extraction (MAQS A4 [IMP]):** records produced by a degraded extraction path — fallback extractor, timeout, partial parse — are marked as such, demoted in ranking, and excluded from derived structures (summaries, graph edges, consolidated facts) until re-extracted. The marker is a profile extension field (see `extensions` in maqs-way-standard.json); the core data model (`schema_version way-v0.1.3`) is unchanged.
```

---

## 13. §2.4, новый пункт A4 после пункта E12 — `SPEC-RU.md`, источник: 17 (A4)

**Заменить (в файле ровно одно вхождение):**

```text
- **Приоритет артефакта E12 (MAQS E12):** текущий артефакт сохраняет фактический приоритет над памятью; конфликт остаётся наблюдаемым, память не должна молча подменять или реконструировать представление артефакта.
```

**На:**

```text
- **Приоритет артефакта E12 (MAQS E12):** текущий артефакт сохраняет фактический приоритет над памятью; конфликт остаётся наблюдаемым, память не должна молча подменять или реконструировать представление артефакта.
- **A4 деградировавшее извлечение (MAQS A4 [IMP]):** записи, созданные деградировавшим путём извлечения — резервный извлекатель, таймаут, частичный разбор, — помечаются как таковые, понижаются в ранжировании и исключаются из производных структур (суммаризации, рёбра графа, консолидированные факты) до повторного извлечения. Пометка — поле расширения профиля (см. `extensions` в maqs-way-standard.json); ядро модели данных (`schema_version way-v0.1.3`) не меняется.
```

---

## 14. §3.2, блок 0.5a — `SPEC.md`, источник: 13 (0.5a)

**Заменить (в файле ровно одно вхождение):**

```text
not a check. 0.5a declares no numeric parameters.
```

**На:**

```text
not a check. A production call site is not sufficient: the control must be able to
fire under production configuration, so its trigger conditions must
reference state that exists in production (columns, tables, flags,
platform capabilities). An invoked-but-unsatisfiable control — a phantom
schema, a silently absent platform dependency — is the same false safety
signal as dead code. Verification: a negative live probe, or a trace of
the trigger conditions against production state. 0.5a declares no numeric parameters.
```

---

## 15. §3.2, блок 0.5a — `SPEC-RU.md`, источник: 13 (0.5a)

**Заменить (в файле ровно одно вхождение):**

```text
проверка. 0.5a не объявляет числовых параметров.
```

**На:**

```text
проверка. Production-вызова недостаточно: управление должно быть способно
сработать при production-конфигурации, поэтому условия его срабатывания
обязаны ссылаться на состояние, существующее в production (колонки,
таблицы, флаги, возможности платформы). Вызываемое, но неисполнимое
управление — фантомная схема, молча отсутствующая зависимость платформы
— такой же ложный сигнал безопасности, как мёртвый код. Проверка:
негативный живой зонд либо трассировка условий срабатывания по
production-состоянию. 0.5a не объявляет числовых параметров.
```

---

## 16. §3.2, отложенный список — `SPEC.md`, источник: —

**Заменить (в файле ровно одно вхождение):**

```text
Deferred (v0.4 list): 0.5a — invoked-but-unsatisfiable control (a
production call site is not enough; the control must be able to fire
under production configuration); golden canary corpus for P9; auditor
certification checklist; canonical drift tolerances per store;
aggregating standalone gates into the audit CLI.
```

**На:**

```text
Deferred (v0.5 list, retargeted by this release decision — no silent
rollover): golden canary corpus for P9; auditor certification checklist;
canonical drift tolerances per store (no real-system run yet);
aggregating standalone gates into the audit CLI. The 0.5a invoked-but-
unsatisfiable control is closed in this release (above).
```

---

## 17. §3.2, отложенный список — `SPEC-RU.md`, источник: —

**Заменить (в файле ровно одно вхождение):**

```text
Отложено (список v0.4): 0.5a — вызванный-но-неудовлетворимый контроль
(производственная точка вызова — недостаточно; контроль должен уметь
сработать при производственной конфигурации); золотой корпус канареек
для P9; чек-лист сертификации аудитора; канонические допуски дрейфа по
хранилищам; агрегация standalone-гейтов в audit CLI.
```

**На:**

```text
Отложено (список v0.5, перенесено решением этого релиза — без молчаливого
перекатывания): золотой корпус канареек для P9; чек-лист сертификации
аудитора; канонические допуски дрейфа по хранилищам (прогона на реальной
системе пока нет); агрегация standalone-гейтов в audit CLI. Вызванный-
но-неудовлетворимый контроль 0.5a закрыт этим релизом (выше).
```

---

## 18. §3.4, отложенный список (счётчики) — `SPEC.md`, источник: —

**Заменить (в файле ровно одно вхождение):**

```text
Deferred (v0.4 list): per-scope/per-subject counter partitioning (cf.
E10 cap semantics); per-deployment tumbling-window adoption.
```

**На:**

```text
Deferred (v0.5 list, retargeted by this release decision — no silent
rollover): per-scope/per-subject counter partitioning (cf. E10 cap
semantics — a design decision, not a wording sync); per-deployment
tumbling-window adoption.
```

---

## 19. §3.4, отложенный список (счётчики) — `SPEC-RU.md`, источник: —

**Заменить (в файле ровно одно вхождение):**

```text
Отложено (список v0.4): per-scope/per-subject разбиение счётчиков (ср.
семантика квоты E10); переход деплойментов на tumbling-окна.
```

**На:**

```text
Отложено (список v0.5, перенесено решением этого релиза — без молчаливого
перекатывания): per-scope/per-subject разбиение счётчиков (ср. семантика
квоты E10 — проектное решение, а не синхронизация формулировки); переход
деплойментов на tumbling-окна.
```

---

## 20. §3.4, отложенный список (обработчики) — `SPEC.md`, источник: —

**Заменить (в файле ровно одно вхождение):**

```text
Deferred (v0.4 list): owners_registry / SLA / fallback schema for
escalation paths (no canon source for SLA scales); tumbling catalog
review; exception taxonomy import.
```

**На:**

```text
Deferred (v0.5 list, retargeted by this release decision — no silent
rollover): owners_registry / SLA / fallback schema for escalation paths
(no canon source for SLA scales — inventing one in a sync release is not
allowed); tumbling catalog review; exception taxonomy import.
```

---

## 21. §3.4, отложенный список (обработчики) — `SPEC-RU.md`, источник: —

**Заменить (в файле ровно одно вхождение):**

```text
Отложено (список v0.4): owners_registry / SLA / fallback-схема для
путей эскалации (нет канонического источника шкал SLA); ревизия
каталога tumbling; импорт таксономии исключений.
```

**На:**

```text
Отложено (список v0.5, перенесено решением этого релиза — без молчаливого
перекатывания): owners_registry / SLA / fallback-схема для путей
эскалации (канонического источника шкал SLA нет — выдумывать его в
релизе синхронизации нельзя); ревизия каталога tumbling; импорт
таксономии исключений.
```

---

## 22. §3.4, отложенный список (слои) — `SPEC.md`, источник: —

**Заменить (в файле ровно одно вхождение):**

```text
Deferred (v0.4 list): heuristic layer assignment with declared
confidence (source-backed inference; inference without source remains
RED); tumbling-window review of layer expectations; semantic adequacy
of expectations.
```

**На:**

```text
Deferred (v0.5 list, retargeted by this release decision — no silent
rollover): heuristic layer assignment with declared confidence (source-
backed inference; inference without source remains RED — relaxing this
is a design decision carrying risk); tumbling-window review of layer
expectations; semantic adequacy of expectations.
```

---

## 23. §3.4, отложенный список (слои) — `SPEC-RU.md`, источник: —

**Заменить (в файле ровно одно вхождение):**

```text
Отложено (список v0.4): эвристическое назначение слоя с объявленной
уверенностью (вывод с источником; вывод без источника остаётся RED);
tumbling-ревизия ожиданий по слоям; семантическая адекватность
ожиданий.
```

**На:**

```text
Отложено (список v0.5, перенесено решением этого релиза — без молчаливого
перекатывания): эвристическое назначение слоя с объявленной уверенностью
(вывод с источником; вывод без источника остаётся RED — смягчение этого
правила проектное решение с риском); tumbling-ревизия ожиданий по слоям;
семантическая адекватность ожиданий.
```

---

## 24. §3.5, отложенный список — `SPEC-RU.md`, источник: —

**Заменить (в файле ровно одно вхождение):**

```text
Отложено (список v0.4): P10 — пути записи с ленивой инициализацией
(`mode=ro` сам по себе не изоляция); P11 — дисциплина агентного
```

**На:**

```text
Отложенный список: пуст — оба пункта (P10 пути записи с ленивой
инициализацией, P11 дисциплина агента-аудитора) закрыты этим релизом.
```

---

## 25. §2.4, отложенная калибровка зон E11 (шестая ссылка, строчной буквой) — `SPEC.md`, источник: —

**Заменить (в файле ровно одно вхождение):**

```text
owner: E11; calibration → v0.4 list);
```

**На:**

```text
owner: E11; calibration deferred to the v0.5 list);
```

---

## 26. §2.4, семантическая адекватность размеров зон — `SPEC.md`, источник: —

**Заменить (в файле ровно одно вхождение):**

```text
deferred (v0.4 list).
```

**На:**

```text
deferred to the v0.5 list.
```

---

## 27. §2.4, отложенная калибровка зон E11 (шестая ссылка) — `SPEC-RU.md`, источник: —

**Заменить (в файле ровно одно вхождение):**

```text
owner: E11; калибровка →
```

**На:**

```text
owner: E11; калибровка отложена в
```

---

## 28. §2.4, список для калибровки зон — `SPEC-RU.md`, источник: —

**Заменить (в файле ровно одно вхождение):**

```text
список v0.4); критический блок
```

**На:**

```text
список v0.5); критический блок
```

---

## 29. §2.4, семантическая адекватность размеров зон — `SPEC-RU.md`, источник: —

**Заменить (в файле ровно одно вхождение):**

```text
адекватность размеров зон — отложено (список v0.4).
```

**На:**

```text
адекватность размеров зон — отложено в список v0.5.
```

---

## Порядок применения и подпись

1. Этот файл и `docs/v0.4-canon/maqs-core-ref-1.10.md` лежат в репозитории
   как подготовка; канон не тронут.
2. Вторая часть текста на подпись — собственные спецификации Way
   (`deletion_marker`, `identity_signature`, матрица прав `operator`,
   метрика `knowledge_update`) — готовится отдельным файлом.
3. Применение обеих частей плюс ссылки на ядро — одним коммитом.
4. Затем стампы v0.4, запись §7, §6 (бэклог v0.5, открытые пробелы D8/D10)
   и `spec-manifest.json` (`release_targets`, `version`, `spec_ref`).
5. Подпись владельца ставится на хеши применённых файлов канона —
   `SPEC.md`, `SPEC-RU.md`, `maqs-way-standard.json` — и указывается в
   сообщении коммита применения. Этот подготовительный файл в канон не
   входит и сам не подписывается.
6. Гейт после применения: `check_release.py --target 0.4 --prev 0.3` →
   RELEASE GREEN; `--self-test` → 6/6.
