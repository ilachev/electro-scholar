# Machine-readable questions and technical data

## Sources of truth

Processing is split into independent layers:

1. An immutable JPEG is identified by SHA-256.
2. `Observation IR` stores regions, detected primitives, and reviewable
   hypotheses. A recognition error at this layer does not become a circuit fact.
3. `Circuit IR` stores verified components, pins, and electrical nets.
4. `layout` inside `Circuit IR` stores only how the same topology is drawn.
5. `Question IR` composes text, formulas, choices, hints, and technical-document
   references into one reviewable educational question.
6. The planned `Learning Evidence IR` independently links claims and choices to
   sources, calculations, and targeted learner feedback.
7. The planned Concept/Claim Registry and localization documents align the same
   semantics across languages, authors, and editions.
8. Planned Problem Alignment records distinguish translations, parameter
   variants, isomorphic circuits, and exercises that merely assess the same
   claim.
9. The planned `Simulation Model IR` and `Simulation Scenario IR` define
   reproducible ideal, practical, device-level, and measured experiments over a
   human-verified circuit.
10. SQLite, SPICE, KiCad, CircuitikZ, SVG, simulation results, and UI models are
   derived representations.

A component's position does not determine an electrical connection. A switch
state also does not alter source nets: nodes are merged only when constructing
the calculation graph for a specific operating state.

## Contents

- `schemas/observation-ir-v1.schema.json` - segmentation and recognition output
  before semantic decisions are accepted.
- `schemas/circuit-ir-v1.schema.json` - canonical circuit graph with a separate
  layout.
- `schemas/question-ir-v1.schema.json` - canonical composition of text, LaTeX
  formulas, circuits, and temporary source-image fragments.
- `schemas/question-review-patch-v1.schema.json` - deterministic transfer of
  local human decisions back to an exact base revision of `Question IR`.
- `questions` - editable question documents that become the source of truth for
  verified content.
- `SOURCE_VERIFICATION.md` - bibliographic sources, independent answer
  verification, and learner-facing citations.
- `MULTILINGUAL_KNOWLEDGE.md` - locale-independent concepts and claims,
  reviewed translations, and cross-source alignment.
- `examples` - linked documents based on the real `TEST2_018.jpg` source.
- `examples/circuit-ir-example-overlay.png` - example geometry overlaid on the
  immutable source for visual verification.
- `media/inventory.json` and `inventory.csv` - 582 images with SHA-256,
  dimensions, and reproducible visual features.
- `media/pilot-50.json` - five diverse images from each topic.
- `media/pilot-contact-sheet.jpg` - pilot overview for initial annotation.

## Reproduction

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
  analysis/examples/circuit-ir-example.json \
  analysis/questions/test2-018.question.json

.venv/bin/python tools/compile_question_bank.py analysis/questions \
  --base-database analysis/database/question-bank.sqlite \
  --output analysis/database/question-bank.sqlite

.venv/bin/python tools/render_circuit_overlay.py \
  analysis/examples/circuit-ir-example.json \
  --image-root kmp-app/features/question-bank/src/commonMain/composeResources/drawable \
  --output analysis/examples/circuit-ir-example-overlay.png

.venv/bin/python -m unittest discover -s tests -v
```

The inventory tool does not assign content types automatically. Such a heuristic
would create false training labels. The first human action is to create
`Observation IR` documents for the 50 pilot items with `text`, `formula`,
`circuit`, `plot`, `table`, or `illustration` regions. Manual annotation is
stored separately from generated `pilot-50.json`, so repeated analysis cannot
overwrite it.

## Circuit IR invariants

- entity IDs are unique within a document;
- every pin belongs to exactly one component;
- a pin belongs to at most one electrical net;
- layout refers only to existing components, pins, and nets;
- evidence refers to an existing source-image observation;
- the same source has the same SHA-256 at every layer;
- ambiguity remains a hypothesis until a human resolves it.

JSON Schema validates document shape. `validate_technical_ir.py` additionally
checks referential integrity that JSON Schema cannot express.

## Question IR invariants

- `source_file + source_index` uniquely identifies the source record;
- every fragment has a producer, evidence, and its own review status;
- a formula stores LaTeX and a searchable text representation, and review or
  patch application changes that pair atomically;
- a circuit is linked through `Circuit IR`, not copied into the question;
- correct positions exist among choices and match the legacy mask;
- `verified` is impossible while checks remain incomplete or the answer key is
  unconfirmed;
- the source JPEG is immutable and remains the visual fallback;
- runtime SQLite is always compiled from the legacy export and JSON documents.

The first end-to-end document is `TEST2/19`. It contains prompt text, parameter
formulas, terminal notation, five choices, two hints, and a reference to the
existing `Circuit IR`. Its status is `in_review`, deliberately avoiding any
claim that machine transcription is a human-verified fact. The compiler stores
the candidate in SQLite for the review UI, while normal application queries
publish structured text only after `verified`.

## Implemented review boundary

The `features/question-review` KMP slice now reads compiled `Question IR`, shows
the immutable original and exact evidence crop, exposes text and LaTeX editing,
lists verification checks, and records accept/correct/reject/defer events in a
separate local SQLite overlay. It runs through the shared Compose application
and has JVM, Android, and iOS database drivers. It does not mutate canonical IR
or bypass the publication gate. See
[`../kmp-app/docs/QUESTION_REVIEW.md`](../kmp-app/docs/QUESTION_REVIEW.md).

`export_question_review_patch.py` deterministically exports a local overlay as
`question-review-patch/v1`. `apply_question_review_patch.py` validates the base
document fingerprint, source asset, targets, event identities, and original
values before atomically producing revised `Question IR`. Formula events carry
both LaTeX and searchable plain text and cannot apply a partial correction.
Applying review events never marks a question verified.

## Next increment

Connect isolated LaTeX compilation, render-back, overlay, and visual diff to
the review contract without making a platform host or the GUI the source of
truth. Then process the first 10 questions through review patch export,
application, independent answer verification, and the publication gate before
expanding annotation to the 50-image pilot. CV/ML models should be measured and
selected only after a verified reference set exists.

The parallel source slice is specified in `SOURCE_VERIFICATION.md`: exact
edition registry, legacy `part + lecture` mappings, `Learning Evidence IR`,
independent derivations, and distractor-specific explanations. An unreviewed
citation is never published to learners.

The multilingual slice is specified in `MULTILINGUAL_KNOWLEDGE.md`: stable
concept and claim IDs, reviewed localized variants, notation normalization,
problem-family equivalence, and comparison across languages, authors, and
books.

The future interactive simulation slice is specified in
`../kmp-app/docs/REALTIME_CIRCUIT_SIMULATION.md`: separate model and scenario
contracts, replaceable numerical engines, ideal-to-measured fidelity, and
mandatory analytic, KCL/KVL, power-balance, cross-engine, cross-platform, and
laboratory checks.
