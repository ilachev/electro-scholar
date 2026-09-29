# Formula subsystem plan

## Goal

Convert formulas and printed text from JPEG into structured data without
publishing any formula that lacks traceable provenance and explicit human
approval. Formula recognition is part of the broader Technical Document Lab;
the circuit model and current priority are described in
[`../../analysis/TECHNICAL_DATA.md`](../../analysis/TECHNICAL_DATA.md).

## Standalone product

The pipeline is not an internal feature of the electrical-engineering learning
application. It is a module of a separate local-purpose tool, Technical
Document Lab. ElectroScholar is its first client, but the contract contains no
concepts such as subject, topic, or question.

Minimum input:

- an image or rectangular image region;
- source MIME type, dimensions, and SHA-256;
- optional external identifier and contextual text.

The output is a versioned `Observation IR` package: detected regions, candidate
LaTeX, validator results, renders, confidence values, and a human decision log.
The package is available through stable JSON Schema, SQLite, and CLI contracts,
so desktop, mobile, web, PDF batch processing, and third-party systems can all
consume it.

Recognition and ML adapters should be a separate offline Python worker because
the OCR and computer-vision ecosystem is stronger there. The KMP application
depends only on a versioned contract, not on a particular model. Recognition
engines can therefore change without migrating client applications.

## Core rules

1. The original JPEG is immutable and always retained.
2. Recognition operates on labeled regions, not the image as a whole: text,
   formula, table, electrical schematic, or illustration.
3. Model output is a candidate, not ground truth.
4. A candidate cannot enter a production question until automated checks pass
   and a reviewer makes an explicit decision.
5. Every formula change creates a new revision; history is never overwritten.

## Stage 1: inventory and annotation

- Calculate SHA-256 for every original and associate it with its question.
- Use the fixed 50-image pilot: five samples from each topic, including poor
  scans, long formulas, subscripts, fractions, and mixed circuit images.
- Annotate rectangular regions and their content type.
- Send schematic regions to `Circuit IR`. Formulas and circuits share
  provenance and review logs but use different semantic models.
- Treat CircuitikZ and SVG as derived rendering formats, not the source of
  electrical topology.

## Stage 2: automated recognition

Run a recognition mode appropriate to each region:

- Russian printed text: OCR preserving case and line coordinates;
- formula: image-to-LaTeX model;
- mixed region: another segmentation pass;
- schematic or illustration: no automatic textual replacement.

Every run records the engine, exact version, parameters, timestamp, confidence,
and raw output. Models run offline and are pinned by checksum.

## Stage 3: normalization

- Allow a constrained LaTeX subset without arbitrary commands or file
  operations.
- Normalize whitespace, braces, and equivalent commands while retaining the
  original model response.
- Store Unicode text, formula LaTeX, and the source crop reference separately.
- Do not silently correct OCR errors from the inferred meaning of the physics
  problem.

## Stage 4: automated verification

A candidate receives independent check results:

1. Parse the permitted LaTeX syntax.
2. Compile in an isolated process without shell escape or network access.
3. Render to PNG at approximately the source region's dimensions.
4. Compare the source crop and render using line geometry, symbol count, SSIM,
   and perceptual diff.
5. Cross-check numbers, subscripts, operation signs, Greek letters, and units
   with a second OCR pass.
6. Raise a disagreement flag when independent models produce different tokens.

High confidence may prioritize the review queue, but never replaces a person.

## Stage 5: human in the loop

The application provides a review mode with four synchronized views:

- original image with the region highlighted;
- enlarged crop;
- editable LaTeX;
- rendered output and a translucent overlay or diff.

Reviewer actions:

- `Approve`: the candidate becomes an approved revision;
- `Correct and approve`: retain both the original and corrected values;
- `Reject`: return the record to the queue;
- `Not a formula`: correct the region type;
- `Second review required`: flag an ambiguous or illegible expression.

Every action records the reviewer, time, comment, and preceding revision. Bulk
approval without viewing each item is prohibited.

## Proposed data model

### `media_assets`

`id`, `question_id`, `original_path`, `sha256`, `width`, `height`, `mime_type`.

### `content_regions`

`id`, `asset_id`, `x`, `y`, `width`, `height`, `kind`, `created_by`, `status`.

### `recognition_runs`

`id`, `region_id`, `engine`, `engine_version`, `model_sha256`, `parameters_json`,
`raw_output`, `confidence`, `created_at`.

### `formula_revisions`

`id`, `region_id`, `recognition_run_id`, `latex_source`, `render_sha256`,
`compile_status`, `visual_score`, `created_by`, `created_at`, `supersedes_id`.

### `review_events`

`id`, `revision_id`, `reviewer_id`, `decision`, `comment`, `created_at`.

## Acceptance criteria

- Every formula references its original and exact region coordinates.
- Every approved formula compiles in the isolated validator.
- Every approved formula has a human review event.
- No original is deleted or overwritten.
- Every question screen can expose the source and transformation history.
- The 50-image pilot is reviewed before batch processing begins.

## Next formula increment

1. Extend the existing `Observation IR` JSON Schema only through a new version
   and migrated test fixtures.
2. Reuse image import, SHA-256, and region annotation.
3. Add provenance and review tables in a domain-neutral schema.
4. Put one text OCR engine and one image-to-LaTeX engine behind replaceable
   adapters without changing the contract or UI.
5. Implement isolated compilation and visual diff.
6. Build the review queue and complete the 50-image ElectroScholar pilot.
7. Connect approved Formula Lab packages to the KMP application through an
   adapter.
