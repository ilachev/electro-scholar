# Multilingual knowledge and cross-source alignment

## Status

This document records an accepted product and architecture direction.
Multilingual question content, a concept registry, cross-source alignment, and
the comparison UI are not implemented yet.

## Principle

The underlying physics is independent of language, author, and country. Wording,
notation, sign conventions, examples, and the order of presentation are not.
ElectroScholar must therefore align sources through a language-neutral semantic
core instead of treating one translation or textbook as the universal truth.

```text
question / answer / experiment
             |
             v
     concept and claim IDs
             |
     normalized semantics
      /       |        \
 Russian   English    future locales
 sources   sources       sources
      \       |        /
       derivation + simulation
```

## Language-neutral core

The following data must not be duplicated per locale:

- stable question, answer, concept, claim, circuit, and scenario IDs;
- circuit topology and component identity;
- formula semantic AST and symbolic relationships;
- physical quantities, dimensions, and SI values;
- assumptions and validity ranges;
- answer verdicts and independent derivations;
- verification and review history.

Human-readable text, notation help, explanations, search terms, source
citations, and accessibility descriptions are locale-specific projections of
that core.

## Original content and translations

The recovered Russian text remains immutable source evidence. A translation is
a new revisioned artifact and never overwrites it.

Each localized content variant needs:

- a BCP 47 language tag such as `ru` or `en`;
- the source content revision and hash;
- translator or model producer and version;
- `candidate`, `in_review`, `human_verified`, or `rejected` status;
- terminology and notation profile;
- review events and comments;
- an explicit fallback locale.

Machine translation can prepare a candidate but cannot publish technical
content. Numbers, signs, units, labels, and answer identity are checked
independently from natural-language fluency.

## Concepts and claims

A broad topic is represented by a stable concept, for example:

```text
concept:circuit.thevenin_equivalent
concept:circuit.kirchhoff_current_law
concept:field.gauss_law
```

A claim is a precise, reviewable statement under explicit assumptions. It may
contain a semantic formula and references to circuit entities:

```text
claim:thevenin.open_circuit_voltage_equals_terminal_voltage
```

Questions, answer explanations, derivations, simulations, and textbook
citations point to claims. This allows one verified explanation or source
alignment to support multiple questions without copying prose.

## Problem families and equivalence

Cross-book comparison must not equate exercises merely because they share a
topic label. A planned `Problem Alignment` record assigns a stable
`problem_family_id` and one reviewed relationship:

- `same_source_problem`: the same original exercise or an authorized
  translation;
- `parameter_variant`: the same semantic structure with changed values,
  labels, or orientation;
- `isomorphic_circuit`: equivalent topology and requested quantities despite a
  different drawing or component naming;
- `assesses_same_claim`: a different exercise testing the same physical claim
  or method;
- `related`: useful nearby material that is not equivalent;
- `disputed`: apparent alignment that has unresolved assumptions or outcomes.

The comparison uses language-neutral features rather than wording similarity:

- normalized givens, unknowns, units, and validity conditions;
- semantic formula AST and expected transformation;
- canonical circuit graph and operating state;
- concept and claim IDs;
- required reasoning method and answer dimension;
- ideal, practical, transient, or steady-state model profile.

A semantic fingerprint can suggest candidates, but a person approves the
relationship. It must not be used to reconstruct or republish copyrighted
problem text. Two exercises may concern the same law yet have different answers
because their reference directions, initial conditions, or model assumptions
differ.

## Cross-source evidence matrix

One claim can have multiple source alignments:

| Claim | Locale | Source | Locator | Convention | Status |
|---|---|---|---|---|---|
| Thevenin voltage | ru | Demirchyan, vol. 1 | section/page | passive sign | verified |
| Thevenin voltage | en | Nilsson and Riedel | section/page | passive sign | candidate |
| Thevenin voltage | en | MIT 6.002 | lecture/note | stated assumptions | candidate |

The matrix records agreement at the semantic level. A source does not receive
extra authority merely because several later books repeat it. Provenance and
independence matter; a citation count is not a vote on physical truth.

When sources appear to disagree, review must first compare:

- RMS, peak, amplitude, and peak-to-peak values;
- current and voltage reference directions;
- passive versus active sign convention;
- `e^(j omega t)` versus `e^(-j omega t)` phasor convention;
- degrees versus radians;
- SI units, prefixes, and per-unit values;
- ideal versus practical component models;
- steady-state, transient, small-signal, and large-signal assumptions;
- terminology and transliteration;
- edition-specific errata.

An unresolved difference is stored as `disputed`; it is not silently translated
into apparent agreement.

## Candidate English source set

There is no exact single-volume English replacement for the scope of the
three-volume Demirchyan set. The initial English source registry should evaluate
separate references by subject area.

### Circuit analysis

- James W. Nilsson and Susan Riedel, *Electric Circuits*, 12th Global Edition.
  Pearson's official page lists the 2024 publication and the print ISBN
  9781292736198:
  <https://www.pearson.com/en-gb/subject-catalog/p/electric-circuits-global-edition/P200000012127/9781292477480>.
- William H. Hayt, Jack E. Kemmerly, Jamie D. Phillips, and Steven M. Durbin,
  *Engineering Circuit Analysis*, 10th edition candidate. Official product
  page: <https://www.mheducation.com/highered/product/engineering-circuit-analysis-hayt.html>.
- MIT OpenCourseWare 6.002, *Circuits and Electronics*, for openly accessible
  lecture notes, problem sets, and a university course crosswalk:
  <https://ocw.mit.edu/courses/6-002-circuits-and-electronics-spring-2007/>.

### Electromagnetic fields

- William H. Hayt and John A. Buck, *Engineering Electromagnetics*, 9th
  edition. Official product page:
  <https://www.mheducation.com/highered/product/engineering-electromagnetics-hayt>.
- Samuel J. Ling, William Moebs, and Jeff Sanny, *University Physics Volume 2*,
  for an openly accessible electricity-and-magnetism reference:
  <https://openstax.org/books/university-physics-volume-2/pages/preface>.

These are candidates, not yet adopted authorities. Exact editions, ISBNs,
access rights, scope coverage, errata, and page mappings must be recorded before
citations become learner-facing. MIT OpenCourseWare's
[current terms](https://ocw.mit.edu/pages/privacy-and-terms-of-use/) and the
current English OpenStax volume use CC BY-NC-SA terms; license compatibility
and any source-specific restrictions must be reviewed before incorporating or
adapting content. Linking and original paraphrase are separate from
redistributing source material.

## Localization behavior

- The app selects UI and authored content by the user's locale and explicit
  language preference.
- Missing localized content follows a visible fallback chain; it never appears
  to be a completed translation.
- A learner may choose a preferred source independently of UI language.
- Search indexes localized text, transliterations, symbols, and reviewed
  terminology aliases while preserving exact identifiers.
- Formulas retain semantic identity while presentation conventions may vary.
- Decimal separators, typography, unit names, and plural forms follow locale;
  stored numeric values remain locale-neutral.
- Source links resolve to the exact edition and locator available to that user.
- Offline packs declare which locales and source metadata they contain.

## Learner experience

The default explanation uses the learner's language and one verified accessible
source. `Compare sources` opens a structured comparison of the same claim:

- equivalent statements from different authors and languages;
- normalized formulas and notation mappings;
- assumptions and model fidelity;
- exact source locators;
- independent derivation and simulation evidence;
- known differences or errata.

For aligned exercises, the view also states the exact relationship: direct
translation, parameter variant, isomorphic circuit, or same assessed claim. It
never labels merely related exercises as duplicates.

The comparison should help the learner understand notation and perspective, not
display long copyrighted passages side by side. Source text remains behind its
lawful viewer unless redistribution rights are recorded.

## Verification

A localized claim is publishable only after:

1. schema and reference validation;
2. number, sign, unit, and symbol preservation checks;
3. dimensional and, where possible, symbolic equivalence checks;
4. comparison with the language-neutral derivation;
5. source-locator verification for that exact edition;
6. technical language review by a human;
7. learner-facing wording review in the target language.

Reviewers may approve translation quality and technical correctness separately.
Both are required for `human_verified` learner content.

## First vertical slice

1. Define a small Concept/Claim Registry and locale-neutral IDs.
2. Define a versioned localization document rather than modifying Russian
   source fields in place.
3. Select 10 concepts represented in the first reviewed questions.
4. Create human-reviewed English question and feedback variants.
5. Register one Russian and at least two independent English source alignments
   per concept where coverage exists.
6. Normalize notation and record assumptions for each alignment.
7. Add locale fallback and source preference to the KMP data contract.
8. Align a small set of exercises with explicit problem-family relationships.
9. Implement one `Compare sources` flow linked to a derivation and simulation.
