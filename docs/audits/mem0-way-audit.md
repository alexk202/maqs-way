# Way-аудит Mem0 OSS (пример применения MAQS-Way v0.2)

> Статус: draft примера аудита, НЕ часть канона. Тон — помощь, не разнос.
> Метод: статическое чтение кода (без запуска, без инфры).
> Аудируемый код: `mem0ai/mem0` @ `0724291` (2026-10-14), shallow clone.
> Аудитор: MAQS-Way v0.2 (принципы P1–P8 + write integrity B1–B6).
> Правило: только факты из кода/документации с путями; чего не проверено — так и написано.

## Сводка

| Свойство Way | Вердикт | Одна строка |
|---|---|---|
| P4 Isolation | COVERED | Фильтры tenant до top-k, ключи не подделать через metadata |
| P2 Provenance | PARTIAL | actor/role в history есть; нет source ref, policy, confidence на записи |
| P3 Aging | PARTIAL | expiration opt-in есть; decay — только platform, не OSS |
| P5 Deletability | PARTIAL | delete чистит вектор + пишет history; history остаётся читаемой, tombstone нет |
| B Write integrity | PARTIAL | Дедуп md5 на уровне приложения, без UNIQUE и транзакций; есть тихие пути |
| P1 Veracity | GAP | Нет типизации model_output / trust-ceiling на саммаризацию |
| P8 Measurability | GAP (in-tree) | `evaluation/` — пустой сабмодуль, harness не вендорирован |
| Logging (§3.4-like) | PARTIAL | Ближайшее к audit trail — SQLite history; structured sink нет |

## Что сделано хорошо (и стоит отметить)

1. **Изоляция (P4) — образцово.** `mem0/memory/main.py:1471-1475` — `search/get_all`
   требуют tenant-фильтр (`user_id|agent_id|run_id`), иначе `ValueError`;
   фильтры уходят в `query_filter` векторного стора до top-k
   (`qdrant.py:428-434`, over-fetch `max(limit*4,60)`); подделка ключей через
   `metadata` отсекается `_strip_identity_keys()` (`main.py:138-162`). Это ровно
   паттерн «граница доказывается попытками нарушений», который требует MAQS G1.
2. **History как audit trail.** SQLite `history` (`storage.py:150-191`) хранит
   `old/new_memory, event, actor_id, role, is_deleted` — происхождение мутаций
   прослеживаемо, `created_at` сохраняется при update (`main.py:2072-2080`).
3. **Expiration opt-in.** `expiration_date + _payload_is_expired()`
   (`main.py:427-451`) —TTL-механика есть, пусть и скрывающая, а не чистящая.

## Gap'ы с конкретикой (что улучшить, по файлам)

1. **P1 — типизировать model_output.** LLM-извлечённые факты пишутся как
   `payload["data"]` напрямую (`main.py:1031-1034`); процедурное требование
   «каждый вывод агента записывать дословно» (`configs/prompts.py:327,352`) —
   без trust-ceiling. Предложение: поле `source.type` + потолок доверия до
   подтверждения внешним источником (паттерн MAQS F8).
2. **P2 — source ref + confidence на записи.** `MemoryItem` (`configs/base.py:16-26`)
   не несёт source ref/URL, policy/version, confidence. History это частично
   закрывает, но сама запись — нет.
3. **P5 — residue history.** Удалённая запись остаётся читаемой через `history()`
   (`storage.py:227-255`); векторного tombstone и purge кэша нет. Для GDPR-строгости
   нужен cascade + governance tombstone (паттерн Way P5).
4. **B — транзакционность и тишина.** `vector_store.insert`, затем `batch_add_history`
   в разных `try` (`main.py:1056-1098`): частичная запись возможна. Тихие пути:
   JSON-парс → `return []` (`984-991`); entity-upsert проглочен в warning/debug
   (`649-663`). Предложение: outbox/компенсация + метрики на каждый silent-путь (B5).
5. **P3 — decay только в platform** (`client/project.py:400-412`, ранжирование при
   поиске); OSS `notices.py:134` прямо говорит «не поддерживается». Честная
   граница продукта, но для OSS-юзера decay нет вообще.

## Честные границы этого аудита

- Не запускалось: поведение рантайма, реальный residue векторов, метрики —
  не проверены (нужен bench, не чтение).
- Platform-код (decay, linked_memory_ids) виден частично — вердикты только про OSS.
- Бенчмарки — во внешнем репозитории-сабмодуле, не инициализирован: что там —
  не утверждаю.

## Что дальше

- Показать отчёт авторам Mem0 через issue, дать время ответить (план, шаг 4).
- Их правки/возражения — в этот файл вторым коммитом, не переписывая находки.
