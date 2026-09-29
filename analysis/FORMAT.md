# Legacy TEST database format

The original `TEST1.DAT` and `TEST2.DAT` files use a proprietary binary format
from a 16-bit Windows application. The format was recovered through static
analysis of `TEST.EXE` and validated against every record in both databases.

## Contents

- `TEST1.DAT`: 265 questions across 5 topics.
- `TEST2.DAT`: 317 questions across 5 topics.
- Total: 582 questions and 582 JPEG images.
- A question contains up to 8 choices, two hints, an image, and a bit mask of
  correct choices.
- Russian text is stored as Windows-1251 and converted to UTF-8 during export.

## Question index

The main index consists of 89-byte records:

| Offset | Size | Value |
|---:|---:|---|
| 0 | 4 | question-text offset |
| 4 | 4 | question-text size |
| 8 | 32 | sizes of the eight answer choices |
| 40 | 4 | first-hint size |
| 44 | 4 | second-hint size |
| 48 | 4 | image size |
| 52 | 1 | correct-choice bit mask |
| 53 | 4 | internal record number |
| 57 | 32 | encrypted Pascal string containing the question number |

Bit 0 of the mask represents the first choice, bit 1 the second choice, and so
on. Text blocks use a simple XOR transformation; images have an additional XOR
with `0x20`.

## Known source defects

- `TEST2`, question 121: the correct-answer mask is zero. The correct choice
  cannot be recovered without an external reference.
- `TEST2`, question 316: the second choice has an invalid internal marker. Its
  text and answer mask remain readable.
- Many choices intentionally have no text: their labels are drawn in the image,
  while the binary record contains only a selection-button marker.

## Export

`tools/inspect_legacy_db.py` creates:

- `analysis/database/question-bank.sqlite` - normalized SQLite database;
- `analysis/database/questions.tsv` - flat table;
- `analysis/database/questions.json` and `topics.json`;
- `analysis/database/images/*.jpg`.

Rebuild command:

```bash
python3 tools/inspect_legacy_db.py test --export-database analysis/database
```
