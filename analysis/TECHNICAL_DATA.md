# Технические данные и электрические схемы

## Источник истины

Обработка разделена на независимые слои:

1. Неизменяемый JPEG идентифицируется SHA-256.
2. `Observation IR` хранит области, обнаруженные примитивы и проверяемые
   гипотезы. Ошибка распознавания на этом уровне не становится фактом схемы.
3. `Circuit IR` хранит подтверждённые компоненты, выводы и электрические сети.
4. `layout` внутри `Circuit IR` хранит только способ изображения той же
   топологии.
5. SPICE, KiCad, CircuitikZ и SVG являются производными экспортами.

Положение компонента не определяет электрическое соединение. Состояние ключа
также не изменяет исходные сети: объединение узлов выполняется только при
построении расчётного графа для конкретного operating state.

## Содержимое

- `schemas/observation-ir-v1.schema.json` — контракт результатов сегментации и
  распознавания до принятия семантических решений.
- `schemas/circuit-ir-v1.schema.json` — канонический граф схемы и отдельный
  layout.
- `examples` — связанные документы на основе реального `TEST2_018.jpg`.
- `examples/circuit-ir-example-overlay.png` — геометрия примера, наложенная на
  неизменяемый источник для визуальной проверки.
- `media/inventory.json` и `inventory.csv` — 582 изображения с SHA-256,
  размерами и воспроизводимыми визуальными признаками.
- `media/pilot-50.json` — по пять разнообразных изображений из каждой темы.
- `media/pilot-contact-sheet.jpg` — обзор пилота для первичной разметки.

## Воспроизведение

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-analysis.txt

.venv/bin/python tools/analyze_media.py \
  --database analysis/database/question-bank.sqlite \
  --image-root kmp-app/features/question-bank/src/commonMain/composeResources/drawable \
  --output-dir analysis/media \
  --pilot-per-topic 5

.venv/bin/python tools/validate_technical_ir.py \
  analysis/examples/observation-ir-example.json \
  analysis/examples/circuit-ir-example.json

.venv/bin/python tools/render_circuit_overlay.py \
  analysis/examples/circuit-ir-example.json \
  --image-root kmp-app/features/question-bank/src/commonMain/composeResources/drawable \
  --output analysis/examples/circuit-ir-example-overlay.png

.venv/bin/python -m unittest discover -s tests -v
```

Инвентаризатор не назначает тип содержимого автоматически. Такая эвристика
создала бы ложную обучающую разметку. Первое человеческое действие — создать для
50 элементов документы `Observation IR` с областями `text`, `formula`,
`circuit`, `plot`, `table` или `illustration`. Ручная разметка хранится отдельно
от генерируемого `pilot-50.json` и поэтому не теряется при повторном анализе.

## Инварианты Circuit IR

- идентификаторы сущностей уникальны внутри документа;
- каждый вывод принадлежит ровно одному компоненту;
- вывод может принадлежать не более чем одной электрической сети;
- layout ссылается на существующие компоненты, выводы и сети;
- evidence ссылается на существующее наблюдение исходного изображения;
- один источник во всех слоях имеет одинаковый SHA-256;
- неоднозначность остаётся гипотезой до решения человека.

JSON Schema проверяет форму документов. `validate_technical_ir.py` дополнительно
проверяет ссылочную целостность, которую JSON Schema выразить не может.

## Следующий инкремент

Сделать локальный интерфейс разметки пилота: область изображения, набор типов
содержимого, примитивы схемы и отдельная очередь неоднозначных junction. Только
после появления проверенного эталона следует измерять и выбирать CV/ML-модели.
