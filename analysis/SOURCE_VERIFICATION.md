# Learning sources and answer verification

## Status

This document records an accepted product and architecture direction. The
source registry, PDF index, citation alignment, claim registry, and
choice-specific learner feedback are not implemented yet.

## Goal

After answering, a learner should receive more than a correctness mark. The
application should explain:

- why the selected choice is correct or incorrect;
- which law, formula, or method applies;
- where it appears in a reference: edition, volume, chapter, section, and
  printed pages;
- how to open an available local copy or lawful external viewer;
- which independent derivation, calculation, or simulation supports the
  answer.

Feedback is attached to each answer choice. It can therefore explain the exact
distractor and likely misconception instead of showing one generic message.
The source link remains available after a correct answer for optional review.

## Preliminary Russian source identification

The working hypothesis for the recovered corpus is:

> K. S. Demirchyan, L. R. Neiman, N. V. Korovkin, and V. L. Chechurin.
> *Theoretical Foundations of Electrical Engineering*, three volumes, fourth
> supplemented edition. Saint Petersburg: Piter, 2003-2006.

Bibliographic checkpoints:

- Russian State Library catalog: <https://search.rsl.ru/ru/record/01002354970>;
- MPEI course program listing all three volumes:
  <https://df.mpei.ru/sveden/education/Documents/%D0%A0%D0%9F_2025_%D0%9E/%D0%911.%D0%92.18%20%D0%A2%D0%B5%D0%BE%D1%80%D0%B5%D1%82%D0%B8%D1%87%D0%B5%D1%81%D0%BA%D0%B8%D0%B5%20%D0%BE%D1%81%D0%BD%D0%BE%D0%B2%D1%8B%20%D1%8D%D0%BB%D0%B5%D0%BA%D1%82%D1%80%D0%BE%D1%82%D0%B5%D1%85%D0%BD%D0%B8%D0%BA%D0%B8_%D0%BE.pdf>;
- BMSTU library catalog, including later reprints and a different fifth
  edition: <https://library.bmstu.ru/Catalog/Details/199220>.

These links were checked on 2026-09-30. Before batch alignment, title pages and
tables of contents must be verified against the actual files in use. Year,
edition, volume, ISBN, page count, and SHA-256 are recorded separately for each
digital copy.

Candidate digital access points:

- the Russian State Library record above reports full viewer access to volume
  one;
- volume one at the Elec.ru technical library:
  <https://www.elec.ru/library/nauchnaya-i-tehnicheskaya-literatura/teoret-osnovy-elektrotehniki-1/>;
- a volume-two PDF on the JASU library domain:
  <https://jasulib.org.kg/wp-content/uploads/2024/03/%D0%A2%D0%9E%D0%AD-%D1%87.2.pdf>;
- volume three at the Elec.ru technical library:
  <https://www.elec.ru/library/nauchnaya-i-tehnicheskaya-literatura/teoret-osnovy-elektrotehniki-3/>.

These are checkpoints for verification and lawful local research, not
permission to republish. Their licensing status is not established. Until
rights are verified, PDFs do not enter Git, release assets, or application
resources.

## Evidence already present in the legacy corpus

In `analysis/database/questions.tsv`:

- 236 of 582 questions contain at least one explicit `ТОЭ` reference;
- 322 course-part references were found;
- 99 references have the form `Ч.1`;
- 223 references have the form `Ч.3`.

Reproduce the count from the repository root:

```bash
rg -i -c 'тоэ' analysis/database/questions.tsv
rg -o -i 'тоэ,[[:space:]]*ч\.?[[:space:]]*[13]' \
  analysis/database/questions.tsv \
  | sed -E 's/[[:space:].,]//g' \
  | tr '[:upper:]' '[:lower:]' \
  | sort \
  | uniq -c
```

Hints contain raw strings such as `ТОЭ, Ч.1, лекция 8` and
`ТОЭ, Ч.3, лекция 2`. They cannot automatically be interpreted as book volume
or section numbers. Electromagnetic-field questions use `Ч.3`, while the
fourth textbook edition describes field theory as the fourth course part. The
legacy marker probably refers to an internal lecture sequence. This remains a
working hypothesis and needs an explicit, reviewed crosswalk.

Example future mapping:

```text
legacy: ТОЭ, Ч.3, лекция 2
    -> source: demirchyan-toe-4e-volume-3
    -> chapter/section: after contents verification
    -> printed pages: after human verification
    -> PDF pages: specific to the file SHA-256
```

## A source is not an oracle

A textbook can support a definition, law, formula, or solution method. It does
not by itself prove that a legacy answer mask selected the correct choice for a
specific problem. A `verified` result requires independent evidence layers:

1. immutable source record and JPEG with SHA-256;
2. approved transcription of text, formulas, and circuit;
3. extracted legacy answer mask;
4. exact theory locator in a fixed source edition;
5. independent derivation, calculation, dimensional check, or simulation;
6. explicit human decision with a review log.

A disagreement is never corrected silently. It moves the question or claim to
`needs_review` or `disputed` and remains available as diagnostic evidence.

Several citations are also not a vote. Sources can share derivations, errors,
or conventions. Cross-language and cross-author comparison must align precise
claims, assumptions, and notation while tracking provenance independence. See
[`MULTILINGUAL_KNOWLEDGE.md`](MULTILINGUAL_KNOWLEDGE.md).

## Planned contracts

The next vertical slice should add independent versioned documents without
retroactively changing `Question IR v1` semantics.

### Source registry

A bibliographic source record contains at least:

- stable `source_id`;
- authors, title, edition, volume, publisher, year, and ISBN;
- BCP 47 language tag and source type;
- official or library URL;
- rights and access state;
- details for a specific digital copy: SHA-256 and PDF page count;
- mapping from PDF pages to printed pages;
- known errata and relationships to translations or derived editions.

A PDF is not required in the repository. The registry works with a local
user-supplied copy, remote viewer, or bibliographic record alone.

### Concept and claim registry

A stable `concept_id` identifies a broad physical idea. A stable `claim_id`
identifies one precise statement under explicit assumptions. Questions, answer
choices, derivations, simulations, and source locators refer to these IDs
instead of attempting to align whole pages or translated prose.

Every source alignment records its notation and convention profile, model
fidelity, locator, review status, and relationship to the claim: `supports`,
`refutes`, `defines`, or `explains_method`.

### Learning Evidence IR

`Learning Evidence IR` refers to a question `document_id`, stable answer or
content-node IDs, and relevant `concept_id` and `claim_id` values. For each
claim or answer choice, it stores:

- `target_ref` and claim references;
- verdict and concise explanation for the choice;
- citation relationship;
- `source_ref` and exact edition;
- chapter, section, printed pages, and PDF pages;
- optional short paraphrase without copying large passages;
- link to an independent derivation or simulation scenario;
- `candidate` or `human_verified` status;
- producer, confidence, evidence, and review events.

The compiler verifies each target, source, claim, and locator, then creates a
read-only runtime SQLite projection. An unverified citation may appear in the
review application but is not presented to learners as authoritative.

### Problem alignment

Exercises from different books or languages are linked through a separate
reviewed relationship, not by copying their text into one canonical question.
The relation distinguishes the same source problem, parameter variants,
isomorphic circuits, exercises that assess the same claim, and merely related
material. The detailed equivalence rules are defined in
[`MULTILINGUAL_KNOWLEDGE.md`](MULTILINGUAL_KNOWLEDGE.md).

## Learner workflow

After selecting an answer, the result view can show:

```text
Answer does not match

With this branch open, no current flows through R2, therefore ...
Correct answer: 40 V

Demirchyan et al., 4th ed., vol. 1, section ..., p. ...
[Show derivation] [Open source] [Compare sources]
```

The public application does not embed a full scanned page without confirmed
rights. It may show an original explanation and formula, exact locator, and a
button that opens a lawful source.

The shared KMP code sees only a narrow source-opening port. Android, iOS, and
desktop implement local PDF navigation and external URLs natively. A missing
PDF never blocks the test itself.

`Compare sources` aligns the same claim across languages and authors, showing
notation mappings, assumptions, locators, independent derivation, simulation,
and unresolved differences without reproducing long copyrighted passages.

## First increment

1. Register the three Russian volumes and verify concrete files by title page,
   table of contents, page mapping, and SHA-256.
2. Define versioned schemas for the source registry, Concept/Claim Registry,
   localization records, Problem Alignment records, and `Learning Evidence IR`.
3. Build a reproducible text index with printed-to-PDF page mapping.
4. Map legacy `part + lecture` labels to textbook sections.
5. Select 10 concepts and align one Russian plus at least two independent
   English sources where coverage exists.
6. Attach source locators and independent solutions to the first 10 questions.
7. Add locator, translation, notation, and distractor-review flows to Compose.
8. Publish feedback only after technical and language review.
