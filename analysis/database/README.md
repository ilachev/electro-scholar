# Экспортированная база

Главный файл — `toe.sqlite`. Его можно открыть в DB Browser for SQLite,
DataGrip, DBeaver или через системную утилиту `sqlite3`.

Быстрый просмотр структуры:

```bash
sqlite3 toe.sqlite ".tables"
sqlite3 -header -column toe.sqlite "SELECT * FROM sources;"
sqlite3 -header -column toe.sqlite "SELECT * FROM topics;"
```

Первые вопросы с темами:

```bash
sqlite3 -header -column toe.sqlite \
  "SELECT source_file, topic, question_number, question FROM question_catalog LIMIT 20;"
```

Варианты и правильный ответ для конкретного вопроса:

```bash
sqlite3 -header -column toe.sqlite \
  "SELECT answer_position, answer, is_correct FROM answer_catalog WHERE source_file='TEST1.DAT' AND question_number=1;"
```

Пути к JPEG в таблице `questions` заданы относительно этой директории.
