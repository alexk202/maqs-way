Signed by owner 2026-10-27 (file at 0214de1, no amendments); applied in <hash>

# Детерминизм и сравнимость прогонов — текст на подпись (v0.3, шаг 10 из 11, часть А)

Status: подготовлено для подписи владельца. Канон (SPEC.md, SPEC-RU.md,
maqs-way-standard.json) и гейты этим файлом НЕ меняются. Источник:
proposals/determinism-paired-per-question.md (разделы v0.2…v0.7;
v0.7 — «Accepted by owner 2026-10-27 after second-stand reproduction;
normative text enters SPEC with release v0.3»; граница применения —
same stand + same window only). Данные-основания: evals/REPRODUCE.md §0,
evals/results/stand2_igpu_note.md, g1iso_determinism_check.json,
g1iso_attractors_crosscheck.json, drift_probe_note.md,
stand2_canary_fix_check.json. Это НЕ пункт MAQS и не gap: фикстур и
гейта для него нет — не изобретать. Образец формы:
docs/v0.3-canon/b4.md (шаг 9, коммиты 50a7088 / f548587 / 9f18082 /
45e4011); образец канонизации: шаги 3–9.

MAQS 1.8.1 extensions not yet reflected: неприменимо (не пункт MAQS).

## (а) Нормативный текст EN — SPEC.md, НОВЫЙ раздел «### 3.6 Run
determinism and comparability» (в конец §3, после блока P9/P10; перед
«## 4. Application Profiles»)

---EN BEGIN---
The run-comparability rules below are policy extension settings (see
`extensions.policy` in maqs-way-standard.json); they are not part of the
core data model (`schema_version way-v0.1.3`, frozen). They govern how
evaluation runs of this project may be compared and how their evidence
is aggregated.

**Byte-identity conditions.** Two runs are comparable byte-for-byte only
when produced on the SAME stand — same GPU, same driver, same inference
build and flags, same model — with per-question history isolation and a
fixed seed. Any of these differing puts the runs in different classes:
byte comparison between them is not allowed.

**Windows.** A window is a series of runs between MATCHING control
panels; "matching" means byte identity of ALL panel outputs. A run
belongs to a window only if it is bracketed by matching control panels
BEFORE and AFTER it. A divergence is a window boundary: for a run next
to a divergence the regime is unknown — it supports aggregate
comparisons only.

**Pairing.** Paired per-question comparisons are allowed ONLY within one
stand and one window. Across stands and across windows — aggregate
comparisons only. Fact-illustration: the iGPU panel outputs matched the
RTX reference 0/12 byte-identically while evidence_hit held 12/12 — the
same detection quality with different bytes; byte comparison across
stands is meaningless, aggregate comparison is not.

**Regime canary.** The canary is a diagnostic label printed in a run's
report header, produced on a FRESH store; it marks the regime and does
NOT unlock byte or per-question comparisons across windows or stands.
The composition of the canary and of the control panel lives in the run
artifacts, not in this canon.

**Stand checklist.** Every prereg fixes the stand it runs on: OS, GPU
driver version, inference build (llama.cpp) and launch flags, model
md5, runner file hashes, CONFIG_SHA256 — recorded per prereg, so a
future second stand can be compared field by field.

The data behind the facts above lives in `evals/results/` (the stand2
iGPU/RTX note, the determinism and attractor crosschecks, the drift
probe note, the canary fix check); this canon cites the files, not
their numbers.
---EN END---

## (б) RU-зеркало — SPEC-RU.md, НОВЫЙ раздел «### 3.6 Детерминизм и
сравнимость прогонов» (в конец §3, после блока P9/P10; перед
«## 4. Профили применения»)

---RU BEGIN---
Правила сравнимости прогонов ниже — настройки расширения политики (см.
`extensions.policy` в maqs-way-standard.json); они не входят в ядро
модели данных (`schema_version way-v0.1.3`, заморожена). Они определяют,
как могут сравниваться прогоны этого проекта и как агрегируется их
доказательная база.

**Условия побайтной воспроизводимости.** Два прогона сравнимы
побайтно только если получены на ОДНОМ стенде — тот же GPU, тот же
драйвер, та же сборка инференса и флаги, та же модель — с по-вопросной
изоляцией истории и фиксированным seed. Любое расхождение в этих
условиях относит прогоны к разным классам: побайтное сравнение между
ними не допускается.

**Окна.** Окно — серия прогонов между СОВПАВШИМИ контрольными
панелями; «совпадение» означает побайтную идентичность ВСЕХ выходов
панели. Прогон принадлежит окну, только если обрамлён совпавшими
контрольными панелями ДО и ПОСЛЕ него. Расхождение — граница окна:
для прогона, соседнего с расхождением, режим неизвестен — он
допускает только агрегатные сравнения.

**Парность.** Парные по-вопросные сравнения допустимы ТОЛЬКО внутри
одного стенда и одного окна. Между стендами и между окнами — только
агрегатные сравнения. Факт-иллюстрация: выходы панели iGPU совпали с
RTX-эталоном побайтно в 0/12 случаев при evidence_hit 12/12 — то же
качество обнаружения при других байтах; побайтное сравнение между
стендами бессмысленно, агрегатное — нет.

**Канарейка режима.** Канарейка — диагностическая метка, печатаемая в
заголовке отчёта прогона и снимаемая на СВЕЖЕМ сторе; она помечает
режим и НЕ разблокирует побайтные или по-вопросные сравнения между
окнами и стендами. Состав канарейки и контрольной панели живёт в
артефактах прогонов, не в этом каноне.

**Чеклист стенда.** Каждый пререг фиксирует стенд, на котором
выполняется: ОС, версия драйвера GPU, сборка инференса (llama.cpp) и
флаги запуска, md5 модели, хеши файлов раннеров, CONFIG_SHA256 —
запись ведётся в каждом пререге, чтобы будущий второй стенд
сравнивался поле за полем.

Данные за фактами выше лежат в `evals/results/` (заметка по стенду 2
iGPU/RTX, кросс-чеки детерминизма и аттракторов, заметка зонда дрейфа,
проверка починки канарейки); этот канон ссылается на файлы, а не на их
числа.
---RU END---

## (в) План изменений канона (исполняется ТОЛЬКО после подписи)

0. Порядок коммитов: (i) один коммит канонизации (пп. 1–5: SPEC §3.6,
   spec-manifest, JSON, §7, указатели в REPRODUCE §0); (ii) коммит
   указателей (заполнение «applied in <hash>» в этом файле + строка
   «Canonized in <hash>» в proposals/determinism-paired-per-question.md).
   MAQS_VALID НЕ меняется (не пункт MAQS); фикстур и гейта НЕТ — не
   изобретать; новых check-скриптов НЕТ. История не переписывается;
   name guard обязан пройти.

1. **SPEC.md / SPEC-RU.md — НОВЫЙ подраздел «### 3.6 Run determinism
   and comparability» / «### 3.6 Детерминизм и сравнимость прогонов».**
   Разместить в конце §3: после блока P9/P10 (§3.5), перед
   «## 4. Application Profiles» / «## 4. Профили применения»;
   существующий текст не менять. Обоснование выбора НОВОГО подраздела
   (а не дозаписи в §3.4/§3.5): правило — методология верификации
   (как сравниваются прогоны и их доказательства), семантически
   отдельная ниша от логирования (§3.4) и состава отчётности (§3.5);
   отдельный подраздел делает правило находимым и не перегружает §3.5,
   который уже несёт j3_guard и процедуру аудита P9/P10.
   spec-manifest.json: sections += "3.6" (единственная правка фикстуры;
   индекс owner-resolution — добавление аддитивно, гейты check_b/
   check_c8 резолвят владельцев по этому списку, version lockstep не
   меняется).

2. **maqs-way-standard.json.**
   - НЕ трогать: data_model, profiles, backlog_v0_2,
     extensions.fields, существующие extensions.policy (alive_cap,
     overflow, escalate_after_denials, critical_zone_fraction,
     counters, i14_handler_registry, i15_layers, audit_procedure,
     pipeline_hygiene, b4_write_atomicity), logging (включая
     e10_e11_events, i10_i11_i12_events), verification_suite.metrics,
     lifecycle.states, штампы версии. schema_version way-v0.1.3
     заморожена; новых полей модели НЕТ.
   - extensions.policy += "run_determinism" — обоснование: единый
     JSON-якорь для каждого канонизированного нормативного блока
     (паттерн шагов 3–9); настраиваемых величин правило не вводит —
     блок структурный. Содержимое: note «Run determinism and
     comparability norms (owner decision 2026-10-27 after second-stand
     reproduction; SPEC §3.6). Not a MAQS item; no fixture/gate by
     design.»; byte_identity {same stand: same GPU, same driver, same
     inference build and flags, same model; per-question history
     isolation; fixed seed — значение seed живёт в пререгах и
     артефактах, не в каноне}; window {"series of runs between MATCHING
     control panels; matching = byte identity of ALL panel outputs;
     membership requires matching brackets BEFORE and AFTER;
     divergence = boundary, regime unknown -> aggregates only"};
     pairing {"per-question pairing ONLY within one stand and one
     window; across stands and across windows -- aggregates only"};
     canary {"diagnostic label from a FRESH store; does NOT unlock byte
     or per-question comparisons across windows/stands; composition in
     run artifacts, not in canon"}; stand_checklist ["OS", "GPU driver
     version", "inference build (llama.cpp) and launch flags", "model
     md5", "runner file hashes", "CONFIG_SHA256"] ("recorded per
     prereg"); data_ref {"evals/results/ files cited by SPEC §3.6;
     numbers live in the artifacts, not in canon"}.

3. **SPEC §7 (оба файла).** К СУЩЕСТВУЮЩЕЙ записи «v0.2.1 → v0.3
   (in progress)» дописать в конце строки: «; determinism rule
   canonized in §3.6 (owner signature 2026-10-27; second-stand
   reproduction); run comparability as policy extension, core data
   model unchanged (way-v0.1.3).» (RU зеркально: «; правило
   детерминизма канонизировано в §3.6 (подпись владельца 2026-10-27;
   воспроизведение на втором стенде); сравнимость прогонов —
   расширение политики, модель данных ядра не изменена
   (way-v0.1.3).»). Новую запись §7 не создавать.

4. **evals/REPRODUCE.md §0 и evals/REPRODUCE-RU.md §0 — ссылки на
   раздел SPEC (EN+RU).** В конец §0 каждого файла добавить строку:
   EN — «Comparability rules (windows, pairing, canary): SPEC §3.6
   (normative since v0.3).»; RU — «Правила сравнимости (окна,
   парность, канарейка): SPEC-RU §3.6 (нормативно с v0.3).» Больше в
   §0 ничего не менять.

5. **proposals/determinism-paired-per-question.md** (в коммите
   указателей): строка 1 «Canonized in <hash> (SPEC §3.6, v0.3). This
   file is the historical formulation; the normative text is in
   SPEC.», остальное в файле не трогать (append-only история версий
   v0.2…v0.7 сохраняется как есть).

6. **Ожидаемые выводы гейтов после применения:**
   maqs_way_audit all — GATE GREEN, namespaces ok, строк «GAP
   (enumerated, not folded)» нет (список пуст с шага 9); check_release
   — RELEASE GREEN с G6 (12 гейтов GREEN; новых check-скриптов нет);
   check_pipeline_hygiene — GATE GREEN БЕЗ флагов дрейфа (новый файл
   в docs/v0.3-canon/, не в proposals/ — счётчики базлайна
   неизменны); check_b / check_c8 — GATE GREEN (owner-resolution:
   «3.6» добавлен в sections аддитивно); name guard scan-all —
   0 leaks; дословная сверка §3.6-блоков обоих SPEC с подписанным
   текстом (программно).
