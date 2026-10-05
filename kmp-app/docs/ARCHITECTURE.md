# Architecture and longevity

## Goal

A product workflow should be implemented once and run on Android, iOS, macOS,
Linux, and Windows. Shared code must not prevent access to native APIs. Any
operating-system dependency stays behind a narrow contract implemented in the
appropriate source set or host module.

The durable semantic core is also independent of presentation language. A
question, physical concept, circuit, formula, claim, and verification result
have stable identifiers; localized text and source editions are projections of
that core.

## Module graph

```text
androidApp ---+
desktopApp ---+--> shared (composition root) --> features:question-bank
iosApp -------+                  |              +-- commonMain/androidMain/iosMain/jvmMain
                                 |
                                 +-------------> features:question-review
                                                +-- commonMain/androidMain/iosMain/jvmMain
```

- `androidApp` owns the Android lifecycle, manifest, and system integration.
- `desktopApp` owns the JVM entry point, window management, and native
  packaging.
- `iosApp` is a regular SwiftUI/Xcode host that embeds a Compose controller.
- `shared` only composes the application from feature modules and owns no data.
- `features/question-bank` is a complete vertical slice: UI, workflows, models,
  SQLDelight, resources, platform adapters, and tests stay together.
- `features/question-review` is a separate vertical slice: `Question IR`
  parsing, review state, UI, local event storage, platform drivers, and tests
  stay together. It receives raw documents and source-image slots from the
  composition root and does not depend on the question-bank slice.

New domains are added as adjacent slices, for example
`features/formula-review`, `features/circuit-review`, and
`features/circuit-lab`. A slice does not import host modules or call another
slice directly. A stable shared contract moves into a small `core/*` module
only after real reuse requires it.

## Vertical-slice rule

A change should run vertically from a user action through data and a test
inside one feature module. The project does not use global `ui`, `data`, or
`domain` layers that gradually absorb unrelated features. Internal packages
inside a slice are allowed, but do not automatically become cross-module APIs.

The public surface of a slice stays minimal. The question-bank slice currently
exposes `QuestionBankFeature()` and an Android initializer. Other declarations
should become `internal` when SQLDelight generation and tests permit it.

## Native capabilities

A shared workflow declares a narrow port only when it needs one, such as
`ImageSource`, `DocumentExporter`, `ShareService`, `HapticFeedback`, or
`SimulationClock`. Implementations live in `androidMain`, `iosMain`, and
`jvmMain`, or are supplied by a host module.

The current slice already follows this approach:

- Android stores SQLite data through `AndroidSqliteDriver` and handles system
  Back through an Android adapter.
- iOS stores SQLite data in Application Support through a native SQLDelight
  driver and starts from SwiftUI.
- Desktop stores SQLite data in the user's data directory through JDBC and
  produces native DMG, DEB, and MSI packages.
- Question review stores drafts and append-only decisions in its own local
  database on every platform. It cannot rewrite packaged data or canonical IR.

Native screens and views are allowed inside the shared application. UIKit,
SwiftUI, Android Views, Compose platform APIs, and desktop APIs do not move
into `commonMain`; shared code sees only a contract and result data.

## Unix philosophy for tools

Every program in `tools/` performs one job, runs without a GUI, and has explicit
inputs, outputs, and exit codes. Tools compose through durable SQLite, JSON,
JSON Schema, TSV, and image files.

```text
legacy files -> inspect_legacy_db.py -> SQLite/JPEG
JPEG -> media/ML worker -> Observation IR
Observation IR -> validator/reviewer -> Circuit IR
legacy fields + Observation/Circuit IR -> Question IR
Question IR -> compiler -> runtime SQLite

reference works -> source registry/index -> source records
source records -> Concept/Claim Registry -> Learning Evidence IR
questions/exercises -> Problem Alignment -> problem families
localized variants + Learning Evidence IR -> localized learner feedback
Question IR + Learning Evidence IR -> verified answer explanations

Circuit IR -> independent exporters -> SPICE/KiCad/CircuitikZ
verified Circuit IR + Simulation Model IR + Simulation Scenario IR
  -> SimulationEngine -> observable frames -> circuit-lab UI
```

ML and Python remain offline workers. End-user applications do not require
Python and do not care which tool produced a valid IR document.

`Learning Evidence IR`, `Simulation Model IR`, and `Simulation Scenario IR`
are planned separate contracts, not implicit extensions of `Question IR v1` or
`Circuit IR v1`. This keeps question content, electrical topology, physical
model fidelity, experiment settings, and bibliography independently versioned.

The source and multilingual rules are specified in
[`../../analysis/SOURCE_VERIFICATION.md`](../../analysis/SOURCE_VERIFICATION.md)
and
[`../../analysis/MULTILINGUAL_KNOWLEDGE.md`](../../analysis/MULTILINGUAL_KNOWLEDGE.md).
The interactive product model and simulation boundary are specified in
[`PRODUCT_EXPERIENCE.md`](PRODUCT_EXPERIENCE.md) and
[`REALTIME_CIRCUIT_SIMULATION.md`](REALTIME_CIRCUIT_SIMULATION.md).

## Data and versions

The question bank is read-only and ships as a Compose resource. User answers,
settings, and progress are stored separately and migrate without rewriting the
source corpus. The legacy export creates database version 1. The `Question IR`
compiler atomically creates runtime SQLite with `PRAGMA user_version = 2`,
matching the SQLDelight schema.

Kotlin, Compose, SQLDelight, AGP, and Gradle versions are pinned. CI separately
checks the common/JVM cycle, Android APK, iOS Simulator build, and desktop
packages. A target is not considered supported merely because its name appears
in Gradle.

`./gradlew checkArchitecture` makes boundaries executable: it rejects platform
imports in `commonMain` and feature dependencies on hosts, `shared`, or sibling
slices.

`./gradlew checkVersionConsistency` verifies SemVer and alignment between the
Gradle applications and iOS host. Release Please updates both files in one PR.
