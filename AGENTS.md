# Project memory for coding agents

This file is the entry point for future agent sessions. Significant product,
architecture, data, verification, release, and provenance decisions must be
written into the repository before a work session ends. Chat history is not an
authoritative project artifact.

## Read before changing the project

1. `README.md` - current product surface and repository map.
2. `CHECKPOINT.md` - implemented state, verification commands, and next step.
3. `kmp-app/docs/ARCHITECTURE.md` - platform boundaries, vertical slices, and
   Unix-style tooling rules.
4. `analysis/TECHNICAL_DATA.md` - canonical IR layers and data invariants.
5. `analysis/SOURCE_VERIFICATION.md` - textbook evidence, learner feedback,
   and answer-verification policy.
6. `analysis/MULTILINGUAL_KNOWLEDGE.md` - language-neutral concepts, localized
   content, and cross-source alignment.
7. `kmp-app/docs/PRODUCT_EXPERIENCE.md` - target learning interaction and UX.
8. `kmp-app/docs/REALTIME_CIRCUIT_SIMULATION.md` - physical-model and solver
   boundaries for interactive experiments.
9. `DATA_PROVENANCE.md` - rights and redistribution constraints.

Read `kmp-app/docs/QUESTION_REVIEW.md` when changing the review queue, local
review persistence, or the path from review decisions back to canonical IR.

Read `kmp-app/docs/LATEX_MIGRATION_PLAN.md` when changing formula recognition or
review. Read `RELEASING.md` before changing versions, CI, signing, or releases.

## Durable project decisions

- ElectroScholar is an educational product, not merely a preserved legacy app.
- The application must remain platform-independent at its core while exposing
  native capabilities through narrow platform ports.
- Features are implemented as complete vertical slices. Cross-slice contracts
  are introduced only when actual reuse requires them.
- Command-line tools do one job and communicate through versioned JSON, JSON
  Schema, SQLite, TSV, and immutable media.
- Original legacy records and images are immutable evidence. Machine output is
  always a candidate until review.
- Circuit topology is independent from drawing geometry. A rendered schematic
  is not the electrical source of truth.
- A physical concept or claim is independent from language, author, and source
  edition. Localized text and citations project onto stable semantic IDs.
- Cross-book exercise matching must state whether items are translations,
  parameter variants, isomorphic circuits, tests of the same claim, or merely
  related. Topic similarity is not equivalence.
- Formula and circuit extraction must retain provenance, deterministic
  validation, and explicit human approval.
- Formula review treats LaTeX and its searchable plain-text representation as
  one atomic value. A correction cannot publish only one side of that pair.
- Local review SQLite is an overlay, not canonical data. Decisions return to
  version control only through a base-hash-bound review patch and validated
  atomic application; applying a patch never marks a question verified.
- A legacy answer mask and a textbook citation are evidence, not proof. A
  verified answer also needs an independent derivation, calculation, or
  simulation and human review.
- Learner feedback should explain the selected distractor and link to a precise,
  human-verified source locator when available.
- Source agreement is not a vote. Verification normalizes assumptions,
  notation, and conventions and still requires an independent derivation,
  calculation, or simulation.
- Interactive simulation consumes verified topology plus separately versioned
  model and scenario data. It must expose idealizations, fidelity, uncertainty,
  diagnostics, and validity limits.
- Copyrighted textbooks are not committed or redistributed without a verified
  license. The repository may store bibliographic metadata, lawful links,
  locators, and hashes of user-supplied local copies.

## Documentation language

- English is the canonical language for project documentation, architecture,
  schemas, identifiers, and agent memory.
- Russian remains the immutable language of the recovered corpus and a fully
  supported application locale. Preserve source quotations and legacy labels
  verbatim when they are evidence.
- Localized product content is versioned data, not a second documentation
  source of truth. A translation never overwrites the source record.
- New canonical prose should be written in English. Add another-language copy
  only when it is itself a product artifact under review.

## Documentation discipline

- Update the authoritative topic document whenever a decision changes.
- Update `CHECKPOINT.md` when implementation state or the next continuation
  point changes.
- Mark planned contracts and workflows as planned; do not describe them as
  implemented until code and tests exist.
- Preserve versioned schemas. Breaking semantic changes require a new schema
  version or a separate versioned document with an explicit migration.
- Keep facts, working hypotheses, and unresolved questions visibly separate.
