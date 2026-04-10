# Extra-8 DOCX Indexer (PySide6)

## Що це
Desktop-застосунок для індексації DOCX, побудови витягів по знайдених ПІБ та пошуку по індексу.

## Архітектура
- `ui/` — Qt view + controller (`AppController`) і worker-и на `QObject` + `QThread`.
- `services/` — orchestration: indexing/search/extract/diagnostics/settings.
- `infra/storage/` — SQLite store та міграції.
- `infra/docx/` — читання/пакування DOCX.
- `infra/filesystem/` — безпечні atomic file operations.

## Threading model
- Кожен worker — `QObject` без parent.
- Запуск через окремий `QThread` + `moveToThread`.
- `worker.finished/cancelled -> thread.quit`, `worker.deleteLater`, `thread.deleteLater`.
- UI не оновлюється з worker thread напряму, тільки через сигнали.

## SQLite strategy
- **connection-per-operation** через `SQLiteConnectionFactory`.
- Немає shared `sqlite3.Connection` між потоками.
- Кожне публічне звернення store відкриває власний connection.
- PRAGMA: `foreign_keys=ON`, `journal_mode=WAL`, `synchronous=NORMAL`.
- Retry policy для `database is locked` у transaction context.

## Indexing workflow
1. Scan source root (`*.docx`).
2. Detect new/changed/removed через key+mtime+size.
3. Для кожного changed/new: parse DOCX, згенерувати витяги, оновити DB.
4. Для removed — видалити записи документа (extracts каскадно).

## DOCX extract logic
- Нормалізація ПІБ: casefold + апострофи + confusable replacements.
- Selection strategy: matched paragraph + context window (N prev/N next).
- Writer формує тільки bytes (`build_extract_package`), запис виконує `SafeFileOperator.atomic_write_bytes`.

## Settings location
- User settings зберігаються в `QStandardPaths.AppConfigLocation`.

## Відомі обмеження
- Highlight абзаців у preview поки текстовий (без rich selection overlays).
- Нумерація DOCX відтворюється на рівні базових block clones.
- Частина UX для settings/theme ще базова.

## Design decisions
- Відмова від shared DB connection усуває `sqlite thread` runtime blockers.
- Atomic write винесено в file layer, щоб уникнути подвійного запису.
- MainWindow залишено container view; orchestration у controller.

## Why connection-per-thread for SQLite
SQLite connection потоко-афінна за замовчуванням (`check_same_thread=True`).
Замість глобального lock/shared connection обрано незалежні короткоживучі connection-и:
- безпечніше в Qt worker model,
- простіше rollback/retry при lock contention,
- чистий життєвий цикл без міжпотокових side-effects.

## Запуск
```bash
python -m app.main
```

## Тести
```bash
pytest
```

## Static checks
```bash
ruff check .
black --check .
mypy .
```

## PyInstaller
```bash
pyinstaller --noconfirm --windowed --name extra8 app/main.py
```
