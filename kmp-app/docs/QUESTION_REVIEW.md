# Question review slice

## Purpose

`features/question-review` is the human-in-the-loop boundary between a
machine-produced `Question IR` candidate and canonical verified educational
content. It is a complete Kotlin Multiplatform vertical slice: parser, review
workflow, Compose UI, local SQLite persistence, platform database drivers, and
tests live in the same module.

The slice currently reviews the real `legacy-test:test2:018` document compiled
into the runtime question bank. The composition root obtains raw documents
through a narrow read-only API from `features/question-bank` and maps them to
`QuestionReviewInput`. Neither feature imports the other.

## Current workflow

1. Open **Review** from the question-bank header.
2. Select a `Question IR` document and one content node.
3. Compare the immutable source JPEG with the crop referenced by that node.
4. Inspect or edit text and LaTeX candidates.
5. Enter a stable reviewer identity and optional comment.
6. Record `accept`, `correct`, `reject`, or `defer`.

The UI also exposes source verification checks, basic LaTeX brace validation,
and a denylist for commands that must never reach a compiler. Formula review
edits LaTeX and its searchable/accessibility `plain_text` as one pair. The UI
does not render LaTeX yet; an isolated compiler, render-back, overlay, and
perceptual diff remain required before formula verification can pass.

## Storage boundary

Reviewing never mutates the packaged question database, source JPEG, or
canonical JSON. Base-document snapshots, drafts, and append-only events are
stored in a separate local `question-review.sqlite` database:

- desktop: `~/.electroscholar/question-review.sqlite`;
- Android: the application's private database directory;
- iOS: the application's SQLDelight database directory.

Each event retains the original value and submitted value. Formula drafts and
events additionally retain original and submitted `plain_text`; the LaTeX and
plain-text pair is accepted or corrected atomically. `correct` is rejected
unless at least one reviewed value differs, and every decision requires a
non-empty reviewer identity. The local database is a review overlay, not a new
source of truth. The base snapshot cannot be replaced after events exist;
changed source data must be exported or explicitly rebased instead of being
silently overwritten.

## Publication boundary

No local decision is published automatically. Two independent CLI programs now
move decisions back into version-controlled data:

```bash
.venv/bin/python tools/export_question_review_patch.py \
  --output analysis/review-patches/test2-018.review.patch.json

.venv/bin/python tools/apply_question_review_patch.py \
  analysis/review-patches/test2-018.review.patch.json \
  analysis/questions/test2-018.question.json \
  --check

.venv/bin/python tools/apply_question_review_patch.py \
  analysis/review-patches/test2-018.review.patch.json \
  analysis/questions/test2-018.question.json \
  --output analysis/questions/test2-018.question.json
```

Export produces `question-review-patch/v1`. It is deterministic and binds all
events to the canonical SHA-256 of the base JSON plus the immutable source
asset SHA-256. Apply validates the patch schema, IDs, event order, base
fingerprint, source hash, target IDs, and original values before making one
atomic write. Formula correction fails if either the LaTeX or its searchable
plain text is absent; application updates both fields together.

Applying a patch transfers corrected values, review statuses, reviewers, and
the event log, but never sets `verification.status` to `verified`. Accepting an
extracted answer key records human evidence but does not make it independently
verified. Formula `plain_text`, render-back, circuit topology, answer checks,
and other pending verification remain gated. The existing `Question IR ->
SQLite` compiler remains the only path into learner-facing data.

This separation is intentional:

```text
Question IR + immutable media -> review UI -> local review overlay
local review overlay -> export_question_review_patch.py -> review patch v1
Question IR + review patch -> apply_question_review_patch.py -> revised Question IR
revised Question IR -> validation -> runtime SQLite
```

## Verification

```bash
cd kmp-app
./gradlew :features:question-review:jvmTest \
  :features:question-bank:jvmTest \
  checkArchitecture
```

Five KMP tests parse the real `test2-018.question.json`, require 22 review
targets, exercise correction persistence and schema migration, prevent a
reviewed base snapshot from being replaced, and check basic LaTeX rejection
rules. Four data-tool tests cover deterministic export, schema-valid atomic
formula application, partial-formula rejection, the non-verification
invariant, and base-revision conflicts.
Desktop visual verification must cover the full source, exact crop, fragment
selection, editor, checks, and decision controls.
