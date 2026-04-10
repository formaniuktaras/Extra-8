# DOCX Indexer UA (PySide6)

Desktop-застосунок для індексації DOCX-наказів та формування персональних витягів по П.І.Б.

## Запуск

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

## Збірка Windows EXE (PyInstaller)

```bash
pyinstaller --noconsole --name docx-indexer-ua --onefile app/main.py
```

`config.json` шукається поруч із exe, далі поруч із кодом.

## Індексація

- Рекурсивний скан source каталогу, фільтрація службових файлів.
- Визначення нових/змінених/видалених файлів через `mtime+size`.
- DOCX читання через ZIP/XML (`word/document.xml`, `styles.xml`, `numbering.xml`).
- Для знайдених П.І.Б. формуються окремі DOCX витяги.
- Індекс у SQLite (WAL, індекси, транзакції).

## Нормалізація пошуку

- Заміна confusable latin/cyrillic.
- Нормалізація апострофів.
- Низький регістр + stem-like обрізка закінчень.
- Ключі фільтра: повний, прізвище+ім'я, лише прізвище.

## Обмеження

- Numbering реалізовано з runtime counters (без повного відтворення всіх Word-нюансів).
- Частина UI-операцій для файлового дерева базові; можна розширити permission-checks.

## Структура

Відповідає шарам `app/core/domain/infra/services/ui/tests`.
