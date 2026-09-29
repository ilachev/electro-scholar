# Exported database

The primary file is `question-bank.sqlite`. Open it with DB Browser for SQLite,
DataGrip, DBeaver, or the system `sqlite3` utility. The `sources`, `topics`,
`questions`, and `answers` tables contain the legacy export. The
`question_documents`, `question_content_nodes`, `question_answer_content`, and
`question_hint_content` tables are compiled from reviewable `Question IR`
documents.

Quick schema inspection:

```bash
sqlite3 question-bank.sqlite ".tables"
sqlite3 -header -column question-bank.sqlite "SELECT * FROM sources;"
sqlite3 -header -column question-bank.sqlite "SELECT * FROM topics;"
sqlite3 -header -column question-bank.sqlite \
  "SELECT document_id, review_status, prompt_text FROM question_documents;"
```

First questions with their topics:

```bash
sqlite3 -header -column question-bank.sqlite \
  "SELECT source_file, topic, question_number, question FROM question_catalog LIMIT 20;"
```

Choices and the correct answer for a specific question:

```bash
sqlite3 -header -column question-bank.sqlite \
  "SELECT answer_position, answer, is_correct FROM answer_catalog WHERE source_file='TEST1.DAT' AND question_number=1;"
```

JPEG paths in the `questions` table are relative to this directory.

A complete rebuild uses two independent tools:

```bash
python3 tools/inspect_legacy_db.py test --export-database analysis/database
python3 tools/compile_question_bank.py analysis/questions \
  --base-database analysis/database/question-bank.sqlite \
  --output analysis/database/question-bank.sqlite
```

The first step knows nothing about manual annotations. The second validates JSON
Schema, referential integrity, source-record identity, and the answer key, then
atomically creates the version 2 runtime database.
