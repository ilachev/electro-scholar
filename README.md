# ElectroScholar

[![CI](https://github.com/ilachev/electro-scholar/actions/workflows/ci.yml/badge.svg)](https://github.com/ilachev/electro-scholar/actions/workflows/ci.yml)
[![Release](https://github.com/ilachev/electro-scholar/actions/workflows/release.yml/badge.svg)](https://github.com/ilachev/electro-scholar/actions/workflows/release.yml)

ElectroScholar is a cross-platform electrical engineering learning project. It
combines a recovered legacy question bank with a modern Kotlin Multiplatform
application and a reviewable pipeline for turning technical images into
machine-readable formulas and circuit graphs.

The current corpus is Russian. The data contracts and tooling are deliberately
language-independent.

![Circuit IR review overlay](analysis/examples/circuit-ir-example-overlay.png)

## Current capabilities

- Reproducible extraction of 582 questions, 2,685 answers, 10 topics, and 582
  JPEG images from a 16-bit educational application.
- Runnable Compose Multiplatform applications for desktop and Android, with an
  iOS Xcode host, backed by shared SQLite resources and SQLDelight.
- A deterministic media inventory and a balanced 50-image annotation pilot.
- Versioned `Observation IR v1`, `Circuit IR v1`, and `Question IR v1` JSON
  Schemas.
- Semantic validation of components, pins, nets, operating states, provenance,
  and drawing layout.
- A deterministic `Question IR -> SQLite` compiler with searchable structured
  prompts and answer choices. The multiplatform learning UI publishes them only
  after the document reaches `verified` status.
- Source-image overlays for human verification of reconstructed schematics.

## Architecture

```text
Legacy database -> Python extractor -> SQLite + immutable JPEG
                                      |
Technical images -> Python CV/ML worker -> Observation IR
                                      |
                                      v
                                  Circuit IR
                                      |
Legacy fields + technical IR -> Question IR -> runtime SQLite
                                      |
                     KMP review UI / SPICE / KiCad / CircuitikZ
```

Python is an offline data and ML layer. The end-user application does not
require Python. SQLite, JSON Schema, and JSON keep the recovered and reviewed
data independent of any particular runtime.

## Run the shared application

Requirements: JDK 21. Gradle dependencies are resolved by the checked-in
wrapper and pinned by per-module lockfiles.

```bash
cd kmp-app
./gradlew :features:question-bank:jvmTest :desktopApp:run
```

## Releases

[GitHub Releases](https://github.com/ilachev/electro-scholar/releases) provide
self-contained desktop installers for macOS (`.dmg`), Debian-based Linux
(`.deb`), and Windows (`.msi`), an installable Android preview (`.apk`), an iOS
Simulator archive, and `SHA256SUMS`. Production store signing is intentionally
separate from these unsigned or development-signed artifacts.

Release Please derives versions and changelogs from Conventional Commits. It
opens a release pull request for human review. Merging that pull request creates
a draft release; the release is published only after data checks and every
platform build succeeds. See [`RELEASING.md`](RELEASING.md) for versioning and
signing rules.

## Run the data checks

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-analysis.txt
.venv/bin/python -m unittest discover -s tests -v

.venv/bin/python tools/validate_technical_ir.py \
  analysis/examples/observation-ir-example.json \
  analysis/examples/circuit-ir-example.json \
  analysis/questions/test2-018.question.json
```

## Repository layout

- `analysis` - recovered database, media inventory, schemas, and examples.
- `tools` - legacy decoder, media analysis, IR validation, and Ghidra scripts.
- `kmp-app` - shared vertical slices and native Android, iOS, and desktop hosts.
- `tests` - data-pipeline and schema conformance tests.
- `dist` - metadata for reproducible local packages; binaries are not tracked.

Detailed technical-data documentation is in
[`analysis/TECHNICAL_DATA.md`](analysis/TECHNICAL_DATA.md). The latest local
checkpoint is documented in [`CHECKPOINT.md`](CHECKPOINT.md).

Textbook-backed answer verification and learner feedback are specified in
[`analysis/SOURCE_VERIFICATION.md`](analysis/SOURCE_VERIFICATION.md).
Language-neutral concepts, reviewed translations, and comparisons across
authors and languages are specified in
[`analysis/MULTILINGUAL_KNOWLEDGE.md`](analysis/MULTILINGUAL_KNOWLEDGE.md).

The target interaction model is documented in
[`kmp-app/docs/PRODUCT_EXPERIENCE.md`](kmp-app/docs/PRODUCT_EXPERIENCE.md), and
the realistic cross-platform simulation boundary is documented in
[`kmp-app/docs/REALTIME_CIRCUIT_SIMULATION.md`](kmp-app/docs/REALTIME_CIRCUIT_SIMULATION.md).
Agent sessions use [`AGENTS.md`](AGENTS.md) as the durable documentation map and
must record significant decisions in the repository rather than relying on
chat history.

Canonical project documentation is English. The recovered Russian corpus is
preserved verbatim and Russian remains a supported product locale; localized
content is revisioned data rather than a competing source of truth.

## Data provenance and rights

The legacy executable and original archives are intentionally excluded from
Git. The repository does contain an extracted educational question bank and its
images for preservation, interoperability research, and migration work.

Ownership and licensing of that legacy content have not yet been established.
No license grant for third-party question text or images is implied. See
[`DATA_PROVENANCE.md`](DATA_PROVENANCE.md) before redistributing the corpus.

No open-source license has been selected for the newly written code yet.
