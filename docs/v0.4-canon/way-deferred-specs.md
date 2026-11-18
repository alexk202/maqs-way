Status: подготовлено для подписи владельца к релизу v0.4. Канон (SPEC.md,
SPEC-RU.md, maqs-way-standard.json) этим файлом НЕ меняется: файл содержит
текст на подпись и точные места его применения.

# Собственные отложенные спецификации Way — текст на подпись (v0.4), часть 2

Закрываются четыре пункта, отложенные решением scope v0.3 (SPEC §6):
`deletion_marker`, `identity_signature`, полная матрица прав роли
`operator`, метрика `knowledge_update` в JSON. Синхронизации с MAQS здесь
нет — формулировки написаны для этого релиза.

Модель данных не затрагивается: `schema_version way-v0.1.3` остаётся
заморожённой. `deletion_marker` закрывается сепарацией — поля живой записи
не появляется; `identity_signature` уже присутствует как поле и получает
спецификацию, а не новое место в модели.

## Формат

Каждая правка — пара «Заменить» / «На». Строка в блоке «Заменить» взята из
файла дословно на коммите `1d0a7ea` и встречается в нём **ровно один раз**;
применение — точная замена.

Проверено до подписи: все 10 замен применяются по одному разу, JSON после
них остаётся валидным, `check_release.py --target 0.3 --prev 0.2.1` —
RELEASE GREEN, conformance и гигиена конвейера зелёные. Отдельно проверено
совместное применение с частью 1: 140 вставок / 51 удаление по трём файлам
канона, конфликтов нет, гейт зелёный.

## Что именно решено

- **`deletion_marker`** — из трёх вариантов бэклога («подтвердить
  устаревание сепарацией / примечание §2.1 / специфицировать») выбран
  первый: живая запись не несёт такого поля вовсе, маркер существует только
  как отдельный артефакт под `schemas/deletion-marker.schema.json`.
- **`identity_signature`** — JCS RFC 8785 плюс Ed25519 над подписываемым
  представлением записи; формат поля с идентификатором ключа; проверка
  падает закрыто. Отдельно объявлен объём утверждения: подпись — это
  свидетельство неизменности записи в покое, а не доказательство истинности
  содержимого и не доказательство личности человека за пишущим агентом.
- **матрица прав `operator`** — перечисление разрешённого с запретом по
  умолчанию на всё остальное; удаление оператору запрещено и идёт через
  жизненный цикл; каждое разрешённое действие обязано дописать провенанс, и
  его отсутствие объявлено нарушением политики, а не пробелом логирования.
- **`knowledge_update`** — число не придумано: в таблице §3.2 строка
  «Knowledge update †» уже несёт «—» для CI-гейта и «≥0.7» для target, и в
  JSON переносится именно это, с `ci_gate: null`. Сноска † под таблицей
  перестаёт говорить «пока нет в JSON».

## Состав

| № | файл | место | источник |
|---|---|---|---|
| 1 | `SPEC.md` | §2.1, нота данных `identity_signature` — спецификация | отложенное v0.3 |
| 2 | `SPEC-RU.md` | §2.1, нота данных `identity_signature` — спецификация | отложенное v0.3 |
| 3 | `maqs-way-standard.json` | `logging.canonicalization_for_signature.status` | отложенное v0.3 |
| 4 | `SPEC.md` | §2.3, роль `operator` — матрица прав | отложенное v0.3 |
| 5 | `SPEC-RU.md` | §2.3, роль `operator` — матрица прав | отложенное v0.3 |
| 6 | `SPEC.md` | §2.1, примечание `deletion_marker` — закрытие отложенного | отложенное v0.3 |
| 7 | `SPEC-RU.md` | §2.1, примечание `deletion_marker` — закрытие отложенного | отложенное v0.3 |
| 8 | `maqs-way-standard.json` | `verification_suite.metrics` — новая метрика `knowledge_update` | stale-refs, §1 P3 |
| 9 | `SPEC.md` | §3.2, сноска † под таблицей метрик | stale-refs |
| 10 | `SPEC-RU.md` | §3.2, сноска † под таблицей метрик | stale-refs |

---

## 1. §2.1, нота данных `identity_signature` — спецификация — `SPEC.md`, источник: отложенное v0.3

**Заменить (в файле ровно одно вхождение):**

```text
specification (Ed25519 over canonical JSON) deferred — see Backlog §6.
```

**На:**

```text
specification: Ed25519 over the JCS (RFC 8785) canonical serialization of the record's signed view — the record with `identity_signature`, the derived `status` and any transport metadata removed, every remaining field present in full. Field format: `ed25519:<base64url-signature>:<key_id>`, where `key_id` names the signing key in the deployment's key registry. Verification recomputes the canonical form, checks the signature against the registered key, and fails closed on an unknown key, a missing field or a canonicalization error — never degrading to "unverified but accepted". The signature binds content and provenance, not retrieval position or lifecycle state: re-signing is required on any content or provenance change and is never performed on a status transition. Scope of the claim: the signature is tamper-evidence for a record at rest, not proof of the truth of its content nor of the identity of the human behind the writing agent.
```

---

## 2. §2.1, нота данных `identity_signature` — спецификация — `SPEC-RU.md`, источник: отложенное v0.3

**Заменить (в файле ровно одно вхождение):**

```text
спецификация (Ed25519 над каноническим JSON) отложена — см. Бэклог §6.
```

**На:**

```text
спецификация: Ed25519 над JCS-канонизацией (RFC 8785) подписываемого представления записи — запись без `identity_signature`, без производного `status` и без транспортных метаданных, все остальные поля в полном виде. Формат поля: `ed25519:<base64url-подпись>:<key_id>`, где `key_id` называет подписывающий ключ в реестре ключей развёртывания. Проверка пересчитывает каноническую форму, сверяет подпись с зарегистрированным ключом и падает закрыто при неизвестном ключе, отсутствующем поле или ошибке канонизации — никогда не переходя в состояние «не проверено, но принято». Подпись связывает содержимое и провенанс, а не позицию в выборке и не состояние жизненного цикла: переподписание обязательно при любом изменении содержимого или провенанса и никогда не делается при переходе состояния. Объём утверждения: подпись — свидетельство неизменности записи в покое, а не доказательство истинности её содержимого и не доказательство личности человека за пишущим агентом.
```

---

## 3. `logging.canonicalization_for_signature.status` — `maqs-way-standard.json`, источник: отложенное v0.3

**Заменить (в файле ровно одно вхождение):**

```text
      "status": "deferred -- identity_signature Ed25519 over canonical JSON to be defined, tracked in the Backlog (SPEC §6); until defined, ed25519_signature is provisional",
```

**На:**

```text
      "status": "defined (v0.4, owner signature) -- identity_signature = Ed25519 over the JCS RFC8785 canonical serialization of the signed view (record without identity_signature, derived status and transport metadata); field format ed25519:<base64url-signature>:<key_id>; verification fails closed on unknown key, missing field or canonicalization error; signature binds content and provenance, re-signing on content/provenance change only, never on a status transition. Normative text: SPEC §2.1.",
```

---

## 4. §2.3, роль `operator` — матрица прав — `SPEC.md`, источник: отложенное v0.3

**Заменить (в файле ровно одно вхождение):**

```text
Full permission matrix — deferred, see Backlog §6.
```

**На:**

```text
Full permission matrix (Profile B; anything not listed is denied by default): read a contested record together with its provenance — allowed, and only for records escalated to this operator; read records that are not contested — denied; confirm or override the outcome of an appeal — allowed; write or edit memory content — denied; delete a record — denied, deletion runs through the lifecycle (§2.2) and its governance tombstone; change policy, thresholds or scope definitions — denied; grant or revoke another actor's access — denied; export a contested record outside the review channel — denied. Every allowed action appends a provenance entry naming the operator and the appeal it answers; an allowed action performed without that entry is a policy violation, not a logging gap.
```

---

## 5. §2.3, роль `operator` — матрица прав — `SPEC-RU.md`, источник: отложенное v0.3

**Заменить (в файле ровно одно вхождение):**

```text
Полная матрица прав — отложена, см. Бэклог §6.
```

**На:**

```text
Полная матрица прав (профиль B; всё не перечисленное запрещено по умолчанию): читать оспоренную запись вместе с её провенансом — разрешено, и только для записей, эскалированных этому оператору; читать записи, которые не оспорены — запрещено; подтверждать или переопределять исход обжалования — разрешено; писать или править содержимое памяти — запрещено; удалять запись — запрещено, удаление идёт через жизненный цикл (§2.2) и его governance tombstone; менять политику, пороги или определения областей — запрещено; выдавать или отзывать доступ другого актора — запрещено; выгружать оспоренную запись за пределы канала рассмотрения — запрещено. Каждое разрешённое действие дописывает запись провенанса, называющую оператора и обжалование, на которое он отвечает; разрешённое действие, совершённое без такой записи, — нарушение политики, а не пробел в логировании.
```

---

## 6. §2.1, примечание `deletion_marker` — закрытие отложенного — `SPEC.md`, источник: отложенное v0.3

**Заменить (в файле ровно одно вхождение):**

```text
Shown in P5 example for schema awareness only.
```

**На:**

```text
Shown in P5 example for schema awareness only. The deferral recorded in the previous release is resolved by separation: a live record carries no `deletion_marker` field at all, the marker exists only as the separate artifact described above, and no core data-model field is introduced (`schema_version way-v0.1.3` unchanged).
```

---

## 7. §2.1, примечание `deletion_marker` — закрытие отложенного — `SPEC-RU.md`, источник: отложенное v0.3

**Заменить (в файле ровно одно вхождение):**

```text
Показан в примере P5 только для наглядности схемы.
```

**На:**

```text
Показан в примере P5 только для наглядности схемы. Отложенное решение предыдущего релиза закрыто сепарацией: живая запись не несёт поля `deletion_marker` вовсе, маркер существует только как отдельный артефакт, описанный выше, и новых полей ядра модели данных не вводится (`schema_version way-v0.1.3` без изменений).
```

---

## 8. `verification_suite.metrics` — новая метрика `knowledge_update` — `maqs-way-standard.json`, источник: stale-refs, §1 P3

**Заменить (в файле ровно одно вхождение):**

```text
      "temporal_accuracy": {
```

**На:**

```text
      "knowledge_update": {
        "dataset": "LongMemEval updates, FactConsolidation",
        "target_threshold": 0.7,
        "operator": ">=",
        "ci_gate": null,
        "note": "No CI gate declared: the SPEC §3.2 table row carries — for min and ≥0.7 for target, mirrored here verbatim. Source: §1 P3 verification line. Indicative until the first real-system run.",
        "source": "SPEC §1 P3, §3.2 table row Knowledge update"
      },
      "temporal_accuracy": {
```

---

## 9. §3.2, сноска † под таблицей метрик — `SPEC.md`, источник: stale-refs

**Заменить (в файле ровно одно вхождение):**

```text
† Knowledge update target from §1 P3 — not yet in JSON `metrics`; deferred, see Backlog §6.
```

**На:**

```text
† Knowledge update target from §1 P3, mirrored in JSON `metrics` as
`knowledge_update` (target 0.7, no CI gate declared) since this release.
```

---

## 10. §3.2, сноска † под таблицей метрик — `SPEC-RU.md`, источник: stale-refs

**Заменить (в файле ровно одно вхождение):**

```text
† Target обновления знаний из §1 P3 — пока нет в JSON `metrics`; отложен, см. Бэклог §6.
```

**На:**

```text
† Target обновления знаний из §1 P3, с этого релиза отражён в JSON `metrics` как
`knowledge_update` (target 0.7, CI-гейт не объявлен).
```

---

## Порядок применения и подпись

1. Этот файл лежит в репозитории как подготовка; канон не тронут.
2. Применение — одним коммитом: часть 1
   (`docs/v0.4-canon/maqs-sync-1.8.1-1.9.md`, 24 замены), часть 2
   (этот файл, 10 замен) и ссылка на ядро MAQS 1.10
   (`docs/v0.4-canon/maqs-core-ref-1.10.md`, 11 упоминаний плюс поле
   `maqs_core_reference`).
3. Затем стампы v0.4, запись §7, §6 (бэклог v0.5, открытые пробелы D8/D10)
   и `spec-manifest.json` (`release_targets`, `version`, `spec_ref`).
4. Подпись владельца ставится на хеши применённых файлов канона —
   `SPEC.md`, `SPEC-RU.md`, `maqs-way-standard.json` — и указывается в
   сообщении коммита применения.
5. Гейт после применения: `check_release.py --target 0.4 --prev 0.3` →
   RELEASE GREEN; `--self-test` → 6/6.
