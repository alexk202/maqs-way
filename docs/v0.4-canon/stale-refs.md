Status: подготовлено для подписи владельца. Канон (SPEC.md, SPEC-RU.md,
maqs-way-standard.json) и гейты этим файлом НЕ меняются.

# Синхронизация устаревших ссылок на версии в каноне — текст на подпись (v0.4, подготовка)

Источник: внешний обзор, P0 (задача владельца, 2026-10-29). Инвентаризация —
grep по maqs-way и maqs-way-evidence (кроме .git), классы H (история — не
трогать) / S (неверное утверждение о текущем состоянии) / F (обещание на
будущее, обращённое к версии ≤ v0.4) / ? (не уверен — в отчёт, не трогать).
Образец формы: docs/v0.3-canon/b4.md. История (§7, docs/releases/*,
docs/v0.3-canon/*, proposals/*, docs/audits/*, evals/results/*) не
переписывается. Часть вне канона уже применена отдельным коммитом maqs-way
(aa5d0f7): docs/mapping-to-maqs.md H1 → v0.3; README.md «(v0.2.1)» → «(v0.3)»;
schemas/deletion-marker.schema.json «defined in v0.2» → «defined in v0.4
(see SPEC §6 Backlog)»; гейт G7 в schemas/check_release.py. Правки
maqs-way-evidence — отдельным коммитом того же репозитория.

## 1. Инвентарь канона: классы S и F вне §7 (EN и RU — построчно в паре)

| № | файл:строка | класс | текущий текст (цитата) | проверка обещания |
|---|---|---|---|---|
| 1a | SPEC.md:39 | S | «…Architecture and Verification layers aligned to the same pattern in v0.2):**» | ложно: выравнивание P/V/E для §2/§3 отложено в v0.4 (§6 п.2, «P/V/E alignment for Architecture and Verification layers») |
| 1b | SPEC-RU.md:39 | S | «…слои «Архитектура» и «Верификация» выравниваются по тому же паттерну в v0.2):**» | то же |
| 2a | SPEC.md:45 | F | «Normative thresholds in v0.2.» | НЕ выполнено: §3.2 остаётся indicative; пункта в бэклоге v0.4 нет → дополнение §6 (п.4 настоящего файла) |
| 2b | SPEC-RU.md:45 | F | «Нормативные пороги — в v0.2.» | то же |
| 3a | SPEC.md:57 | F | «`identity_signature` = Ed25519 over canonical JSON (specification deferred to v0.2, see Backlog §6.2).» | НЕ выполнено: JSON `canonicalization_for_signature.status` всё ещё TODO, спецификации нет; пункт в бэклоге v0.4 ЕСТЬ; раздела «Бэклог §6.2» в текущем SPEC НЕ существует (§6 — нумерованный список 1–3, подразделов нет) → правка также чинит висячий указатель |
| 3b | SPEC-RU.md:57 | F | «`identity_signature` = Ed25519 над каноническим JSON (спецификация перенесена в v0.2, см. Бэклог §6.2).» | то же |
| 4a | SPEC.md:151 | F | «specification (Ed25519 over canonical JSON) deferred to v0.2 — see Backlog §6.2.» | то же, что 3a |
| 4b | SPEC-RU.md:151 | F | «спецификация (Ed25519 над каноническим JSON) перенесена в v0.2 — см. Бэклог §6.2.» | то же |
| 5a | SPEC.md:171 | F | «full operator permission matrix — TODO v0.2).» | НЕ выполнено; пункт в бэклоге v0.4 ЕСТЬ («operator role full permission matrix for §2.3») |
| 5b | SPEC-RU.md:171 | F | «полная матрица прав operator — TODO v0.2).» | то же |
| 6a | SPEC.md:185 | F | «Full permission matrix — TODO v0.2.» | то же, что 5a |
| 6b | SPEC-RU.md:185 | F | «Полная матрица прав — TODO v0.2.» | то же |
| 7a | SPEC.md:319 | S | «Architecture and Verification layers aligned to the same pattern in v0.2.» | ложно, см. 1a |
| 7b | SPEC-RU.md:321 | S | «слои «Архитектура» и «Верификация» выравниваются по тому же паттерну в v0.2.» | то же |
| 8a | SPEC.md:346 | F | «† Knowledge update target from §1 P3 — not yet in JSON `metrics`, to be added in v0.2 (see §6).» | НЕ выполнено: в JSON `verification_suite.metrics` метрики knowledge_update нет (12 метрик: R_at_5 … E11.verify_placement); пункта в бэклоге v0.4 нет → дополнение §6 (п.4) |
| 8b | SPEC-RU.md:348 | F | «† Target обновления знаний из §1 P3 — пока нет в JSON `metrics`, будет добавлен в v0.2 (см. §6).» | то же |
| 9 | maqs-way-standard.json:692 | S/F | `"status": "TODO_v0.2 - identity_signature Ed25519 over canonical JSON to be defined; currently noted as gap"` | НЕ выполнено (спецификации нет, пункт в бэклоге v0.4 есть); «currently noted as gap» устарело: с v0.3 открытых known gap'ов нет — это отложенный пункт бэклога, а не gap |

Формулировок «deferred to v0.» / «TODO v0.» / «to be added in v0.» вне §7 в
каноне, кроме перечисленных, нет (инвентаризация 2026-10-29).
maqs-way-standard.json:273 «calibration deferred to v0.4 list» — корректная
ссылка на текущий бэклог, не трогается.

## 2. Принцип новых формулировок

Новые тексты НЕ содержат маркеров версий («v0.N»): обещание указывает на
Бэклог (§6), а не на номер версии. Это делает гейт G7 «forward refs to
released versions» (schemas/check_release.py, активен с --target 0.4)
осмысленным и после канонизации: обещание, адресованное уже вышедшей версии,
для G7 — stale-ссылка. Содержание обещаний не меняется — меняется только
адресат (раздел вместо номера версии) и исправляется висячий указатель
«§6.2» → «§6».

## 3. Точные правки (старый → новый, дословно; применять без интерпретаций)

### 3.1 Паттерн P/V/E, §1 (строки 1a/1b)

---EN OLD BEGIN---
**Structure per principle (P/V/E pattern applied to this layer from v0.1.1; Architecture and Verification layers aligned to the same pattern in v0.2):**
---EN OLD END---
---EN NEW BEGIN---
**Structure per principle (P/V/E pattern applied to this layer from v0.1.1; Architecture and Verification layers — P/V/E alignment deferred, see Backlog §6):**
---EN NEW END---
---RU OLD BEGIN---
**Структура каждого принципа (паттерн P/V/E применён к этому слою с v0.1.1; слои «Архитектура» и «Верификация» выравниваются по тому же паттерну в v0.2):**
---RU OLD END---
---RU NEW BEGIN---
**Структура каждого принципа (паттерн P/V/E применён к этому слою с v0.1.1; слои «Архитектура» и «Верификация» — выравнивание P/V/E отложено, см. Бэклог §6):**
---RU NEW END---

### 3.2 Нормативные пороги, §1 (строки 2a/2b)

---EN OLD BEGIN---
> Thresholds in this version are **indicative engineering targets, subject to revision after first real run**. Normative thresholds in v0.2.
---EN OLD END---
---EN NEW BEGIN---
> Thresholds in this version are **indicative engineering targets, subject to revision after first real run**. Normative thresholds — deferred, see Backlog §6.
---EN NEW END---
---RU OLD BEGIN---
> Пороговые значения в этой версии — **ориентировочные инженерные цели, подлежат пересмотру после первого прогона на реальной системе**. Нормативные пороги — в v0.2.
---RU OLD END---
---RU NEW BEGIN---
> Пороговые значения в этой версии — **ориентировочные инженерные цели, подлежат пересмотру после первого прогона на реальной системе**. Нормативные пороги — отложены, см. Бэклог §6.
---RU NEW END---

Обещание НЕ выполнено (§3.2 остаётся indicative), пункта в бэклоге v0.4 нет →
точный текст добавляемого пункта §6 — в п.4 настоящего файла.

### 3.3 identity_signature, §1 P2 Верификация (строки 3a/3b)

---EN OLD BEGIN---
`identity_signature` = Ed25519 over canonical JSON (specification deferred to v0.2, see Backlog §6.2).
---EN OLD END---
---EN NEW BEGIN---
`identity_signature` = Ed25519 over canonical JSON (specification deferred, see Backlog §6).
---EN NEW END---
---RU OLD BEGIN---
`identity_signature` = Ed25519 над каноническим JSON (спецификация перенесена в v0.2, см. Бэклог §6.2).
---RU OLD END---
---RU NEW BEGIN---
`identity_signature` = Ed25519 над каноническим JSON (спецификация отложена, см. Бэклог §6).
---RU NEW END---

Обещание НЕ выполнено (JSON `canonicalization_for_signature.status` всё ещё
TODO); пункт в бэклоге v0.4 есть. Указатель «Backlog §6.2» висячий: раздела
§6.2 в текущем SPEC нет — новый текст указывает на §6.

### 3.4 identity_signature, §2.1 Data model notes (строки 4a/4b)

---EN OLD BEGIN---
- **identity_signature:** removed from the live-record example; specification (Ed25519 over canonical JSON) deferred to v0.2 — see Backlog §6.2.
---EN OLD END---
---EN NEW BEGIN---
- **identity_signature:** removed from the live-record example; specification (Ed25519 over canonical JSON) deferred — see Backlog §6.
---EN NEW END---
---RU OLD BEGIN---
- **identity_signature:** убрано из примера живой записи; спецификация (Ed25519 над каноническим JSON) перенесена в v0.2 — см. Бэклог §6.2.
---RU OLD END---
---RU NEW BEGIN---
- **identity_signature:** убрано из примера живой записи; спецификация (Ed25519 над каноническим JSON) отложена — см. Бэклог §6.
---RU NEW END---

### 3.5 Матрица прав operator, §2.2 (строки 5a/5b)

---EN OLD BEGIN---
Role of the reviewing human = `operator` (defined in §2.3; full operator permission matrix — TODO v0.2).
---EN OLD END---
---EN NEW BEGIN---
Role of the reviewing human = `operator` (defined in §2.3; full operator permission matrix — deferred, see Backlog §6).
---EN NEW END---
---RU OLD BEGIN---
Роль рассматривающего человека = `operator` (определена в §2.3; полная матрица прав operator — TODO v0.2).
---RU OLD END---
---RU NEW BEGIN---
Роль рассматривающего человека = `operator` (определена в §2.3; полная матрица прав operator — отложена, см. Бэклог §6).
---RU NEW END---

### 3.6 Матрица прав operator, §2.3 (строки 6a/6b)

---EN OLD BEGIN---
Full permission matrix — TODO v0.2.
---EN OLD END---
---EN NEW BEGIN---
Full permission matrix — deferred, see Backlog §6.
---EN NEW END---
---RU OLD BEGIN---
Полная матрица прав — TODO v0.2.
---RU OLD END---
---RU NEW BEGIN---
Полная матрица прав — отложена, см. Бэклог §6.
---RU NEW END---

### 3.7 Паттерн P/V/E, §3 (строки 7a/7b)

---EN OLD BEGIN---
**Structure:** P/V/E pattern applied to Principles layer (§1) from v0.1.1; Architecture and Verification layers aligned to the same pattern in v0.2.
---EN OLD END---
---EN NEW BEGIN---
**Structure:** P/V/E pattern applied to Principles layer (§1) from v0.1.1; Architecture and Verification layers — P/V/E alignment deferred, see Backlog §6.
---EN NEW END---
---RU OLD BEGIN---
**Структура:** паттерн P/V/E применён к слою принципов (§1) с v0.1.1; слои «Архитектура» и «Верификация» выравниваются по тому же паттерну в v0.2.
---RU OLD END---
---RU NEW BEGIN---
**Структура:** паттерн P/V/E применён к слою принципов (§1) с v0.1.1; слои «Архитектура» и «Верификация» — выравнивание P/V/E отложено, см. Бэклог §6.
---RU NEW END---

### 3.8 Метрика knowledge update, §3.2 сноска (строки 8a/8b)

---EN OLD BEGIN---
† Knowledge update target from §1 P3 — not yet in JSON `metrics`, to be added in v0.2 (see §6).
---EN OLD END---
---EN NEW BEGIN---
† Knowledge update target from §1 P3 — not yet in JSON `metrics`; deferred, see Backlog §6.
---EN NEW END---
---RU OLD BEGIN---
† Target обновления знаний из §1 P3 — пока нет в JSON `metrics`, будет добавлен в v0.2 (см. §6).
---RU OLD END---
---RU NEW BEGIN---
† Target обновления знаний из §1 P3 — пока нет в JSON `metrics`; отложен, см. Бэклог §6.
---RU NEW END---

Обещание НЕ выполнено (в JSON `verification_suite.metrics` метрики нет),
пункта в бэклоге v0.4 нет → точный текст добавляемого пункта §6 — в п.4.

### 3.9 JSON, canonicalization_for_signature.status (строка 9)

---JSON OLD BEGIN---
"status": "TODO_v0.2 - identity_signature Ed25519 over canonical JSON to be defined; currently noted as gap",
---JSON OLD END---
---JSON NEW BEGIN---
"status": "deferred -- identity_signature Ed25519 over canonical JSON to be defined, tracked in the Backlog (SPEC §6); until defined, ed25519_signature is provisional",
---JSON NEW END---

Стиль строки — ASCII («--», без «—») как в соседних строках JSON-бэклога.
«currently noted as gap» убрано: с v0.3 открытых known gap'ов нет, пункт
отложен в бэклог, а не числится gap'ом.

## 4. Дополнения §6 (применять только после подписи; точный текст)

В §6 п.2 «Backlog v0.4» добавить третий bullet ПОСЛЕ существующего второго
(«From the MAQS 1.8.1 sync … rows 1–13 …»), ПЕРЕД п.3:

---EN BEGIN---
   - From the stale-refs inventory (`docs/v0.4-canon/stale-refs.md`): normative thresholds for the §3.2 metrics (promotion from indicative to normative after a first real-system run); `knowledge_update` target metric in JSON `verification_suite.metrics` (§1 P3: LongMemEval updates / FactConsolidation, target ≥0.7).
---EN END---

Зеркало в SPEC-RU.md §6 п.2, в то же место:

---RU BEGIN---
   - Из инвентаризации устаревших ссылок (`docs/v0.4-canon/stale-refs.md`): нормативные пороги для метрик §3.2 (повышение из ориентировочных до нормативных после первого прогона на реальной системе); метрика target обновления знаний `knowledge_update` в JSON `verification_suite.metrics` (§1 P3: LongMemEval updates / FactConsolidation, target ≥0.7).
---RU END---

Остальные F-обещания уже имеют пункты в бэклоге v0.4 (identity_signature —
полная спецификация; operator — полная матрица прав для §2.3; выравнивание
P/V/E) — новых пунктов §6 для них не требуется.

## 5. Строка §7 для будущей канонизации (ПРЕДЛОЖЕНИЕ, НЕ ВСТАВЛЯТЬ)

EN (в SPEC.md §7, после записи «v0.2.1 → v0.3»):

---EN BEGIN---
- **v0.3 → v0.4 (…):** stale version references synced per the signed stale-refs package (docs/v0.4-canon/stale-refs.md): pre-v0.3 forward references ("Normative thresholds in v0.2", "specification deferred to v0.2", "TODO v0.2" ×2, "to be added in v0.2", JSON `canonicalization_for_signature` TODO_v0.2) retargeted to the Backlog (§6) without version markers; dangling "Backlog §6.2" pointers corrected to §6; the false "aligned to the same pattern in v0.2" claims in the §1/§3 layer headers corrected to the actual deferral status; Backlog §6 gained the normative-thresholds and knowledge_update-metric items. No formulation, threshold, vector, or model changes (way-v0.1.3 frozen). RU mirrors verbatim.
---EN END---

RU (в SPEC-RU.md §7, после записи «v0.2.1 → v0.3»):

---RU BEGIN---
- **v0.3 → v0.4 (…):** синхронизация устаревших ссылок на версии по подписанному пакету stale-refs (docs/v0.4-canon/stale-refs.md): до-v0.3 обещания, адресованные прошлым версиям («Нормативные пороги — в v0.2», «спецификация перенесена в v0.2», «TODO v0.2» ×2, «будет добавлен в v0.2», JSON `canonicalization_for_signature` TODO_v0.2), переадресованы на Бэклог (§6) без маркеров версий; висячие указатели «Бэклог §6.2» исправлены на §6; ложные утверждения «выравниваются по тому же паттерну в v0.2» в шапках слоёв §1/§3 исправлены на фактический статус отложенности; в Бэклог §6 добавлены пункты о нормативных порогах и метрике knowledge_update. Без изменений формулировок, порогов, векторов и модели (way-v0.1.3 заморожен). EN-зеркало дословно.
---RU END---

## 6. Связь с гейтом G7 (информационно, на момент подготовки файла)

Список G7-попаданий на текущем каноне (target 0.4): SPEC.md:57, 151, 171,
185, 346; SPEC-RU.md:171, 185 (7 строк) — все совпадают с классом F
настоящего инвентаря. После подписи и применения настоящего пакета G7 на
target 0.4 должен стать зелёным (новые формулировки без маркеров версий).
Ограничения списка паттернов G7 (зафиксированы в докстринге гейта):
формулировки без маркера («Normative thresholds in v0.2») и русские
парафразы вне списка («перенесена в v0.N» — SPEC-RU.md:57, 151;
«будет добавлен в v0.N» — SPEC-RU.md:348) гейтом не ловятся — они закрыты
настоящей инвентаризацией, а не гейтом.
