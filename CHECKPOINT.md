# Checkpoint: 2026-09-30

After the first runnable KMP increment, work began on an independent layer for
technical-data and electrical-circuit analysis.

## Recorded result

- Recovered the `TEST1.DAT` and `TEST2.DAT` formats.
- Exported 582 questions, 10 topics, 2,685 choices, and 582 JPEG images.
- Extracted correct answers from the original application's bit mask.
- Created the normalized `analysis/database/question-bank.sqlite` database.
- Created the ElectroScholar Compose Multiplatform application for Android,
  iOS, macOS, Linux, and Windows under `kmp-app`.
- Implemented the question bank as an independent vertical slice: models,
  SQLDelight, resources, and UI live in `features/question-bank/commonMain`.
- Isolated native hosts in `androidApp`, `iosApp`, and `desktopApp`.
- Built a self-contained macOS `.app` with its own JRE and an installer DMG.
- Pinned Gradle, Kotlin, Compose, SQLDelight, and transitive dependencies.
- Inventoried all 582 JPEG files by SHA-256, dimensions, and reproducible visual
  features; no exact duplicates were found.
- Created a deterministic 50-image pilot with 5 images from each topic.
- Added `Observation IR v1` and `Circuit IR v1` JSON Schemas.
- Added `Question IR v1` to compose text, LaTeX, choices, hints, source assets,
  and technical documents.
- Created the first end-to-end document for `TEST2/19`; its machine
  transcription remains `in_review` until a human confirms it.
- Added a separate `Question IR -> SQLite` compiler. The version 2 runtime
  database stores canonical JSON, normalized content nodes, and search views.
- The Compose application can inspect status and structured nodes, but
  publishes prompts, choices, hints, and search text only after `verified`;
  an `in_review` candidate never replaces the source material.
- Created a linked observation, topology, layout, and two-switch-state example
  from the real `TEST2_018.jpg` source.
- Added referential-integrity validation, a visual overlay renderer, and seven
  Python tests.
- Renamed the project to ElectroScholar. The
  `io.github.ilachev.electroscholar` namespace, bundle ID, database, user
  directory, and build artifacts no longer use the TOE working name.
- Added GitHub Actions CI for the data layer, shared JVM, Android, and iOS.
- Adopted textbook-backed verification: a source supports theory but does not
  replace independent calculation and human review.
- Found 322 TOE-course references in legacy hints across 236 questions: 99
  references to `Ч.1` and 223 to `Ч.3`. These are currently treated as lecture
  course parts, not textbook volume numbers.
- Recorded the 4th expanded edition of the three-volume Demirchyan, Neiman,
  Korovkin, and Chechurin set as the working bibliographic candidate. Its exact
  relationship to the legacy lectures still requires verification.
- Designed targeted learner feedback: explain each distractor, cite an exact
  textbook locator, include an independent derivation, and publish only after
  review.
- Recorded a future highly interactive product experience based on direct
  circuit manipulation, linked formulas and plots, immediate feedback, and
  non-manipulative mastery progress.
- Recorded realistic interactive simulation as a future slice, with separate
  simulation model and scenario contracts, ideal/practical/measured fidelity,
  replaceable engines, and laboratory validation.
- Recorded multilingual content and cross-source alignment through stable
  concept and claim IDs rather than duplicated language-specific truth.
- Defined reviewed problem-family relationships so cross-book exercises can be
  distinguished as translations, parameter variants, isomorphic circuits,
  same-claim assessments, or merely related material.
- Added `AGENTS.md`; future agent sessions must read project documentation and
  record significant decisions in the repository.
- Adopted English as the canonical documentation language. Russian remains the
  immutable corpus language and an application locale.

## Verification

```bash
cd kmp-app
./gradlew :features:question-bank:jvmTest
./gradlew :androidApp:assembleDebug
./gradlew :desktopApp:packageDmg
```

At this checkpoint, four smoke tests pass: database structure, question and
answer-key reads, search plus preservation of the known `TEST2/121` defect, and
the publication gate for compiled `Question IR`.

Eleven data, circuit, referential-integrity, and compiler tests also pass:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## Artifact

- File: `dist/ElectroScholar-1.0.0.dmg`
- SHA-256: `663de788124b28217d3c58cc23c03ab4816fb691a6ed1458fb1f01a9781c1bcd`
- Size: 105,105,991 bytes.

The DMG is not yet signed with a Developer ID or notarized by Apple. This is
acceptable for local verification; a public release must add signing,
notarization, and automated CI packaging.

## Known source-data defects

- `TEST2`, question 121: the correct-answer mask is missing.
- `TEST2`, question 316: the second-choice marker is corrupted.

## Continuation point

The current contract is documented in `analysis/TECHNICAL_DATA.md`. The next
step is a local Compose review interface for `Question IR`: original image and
crop, text/LaTeX editing, formula render-back, accept/correct/reject/defer
decisions, and a separate queue for ambiguous junctions. After the first 10
verified questions, expand annotation to the 50-image pilot and compare CV/ML
models.

The related source slice is documented in `analysis/SOURCE_VERIFICATION.md`:
verify concrete PDFs for all three volumes, create a source registry and
`Learning Evidence IR`, map legacy `part + lecture` references to book
sections, and add verified feedback to the first 10 questions.

The multilingual continuation is documented in
`analysis/MULTILINGUAL_KNOWLEDGE.md`: define concept and claim IDs, create
human-reviewed English variants, and align Russian and English sources and
problem families without duplicating physical truth.

The later interactive slice is documented in
`kmp-app/docs/PRODUCT_EXPERIENCE.md` and
`kmp-app/docs/REALTIME_CIRCUIT_SIMULATION.md`. Begin it only after verified
circuits exist, starting with one complete DC flow from parameter control to
solver, probes, overlay, distractor explanation, source comparison, and
ideal/practical comparison.
