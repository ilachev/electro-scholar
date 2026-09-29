# Data provenance and rights status

## Origin

The question bank was recovered from a legacy 16-bit educational application
named `TEST`. Its two principal databases are identified inside the recovered
format as `TEST1.DAT` and `TEST2.DAT`.

The original executable, archives, statistics, and raw `.DAT` files are excluded
from Git. The repository contains these derived artifacts:

- `analysis/database/question-bank.sqlite`;
- normalized JSON and TSV exports;
- 582 extracted JPEG question images bundled with the desktop application;
- hashes, visual measurements, and review examples derived from those images.

The extraction process is documented and reproducible with
`tools/inspect_legacy_db.py`. Stable `legacy-test:*` identifiers intentionally
preserve the source lineage and are not product branding.

## Rights status

The copyright owner and license terms of the legacy questions and images have
not been established. Their presence in this repository does not grant a license
to redistribute, republish, or commercially use that content.

The corpus is currently retained for software preservation, format research,
interoperability work, and migration into a reviewable modern representation.
Before a formal public release or downstream redistribution, provenance and
permission should be reviewed by the project owner.

No repository-wide open-source license has been selected for the newly written
code. Until one is added, normal copyright rules apply.

## External reference works

Textbooks used to verify formulas, methods, and answers remain separate from
the recovered corpus. A publicly reachable PDF is not by itself evidence of a
redistribution license. Copyrighted reference PDFs must not be committed,
bundled into releases, or mirrored by the project unless their license has been
verified and recorded.

The repository may retain bibliographic metadata, lawful catalog or viewer
links, precise page locators, rights status, and SHA-256 hashes of legally
obtained local copies. Learner-facing explanations should be original
paraphrases with citations; scans or substantial excerpts require separate
rights review. The verification design is documented in
`analysis/SOURCE_VERIFICATION.md`.

Source language, edition, translation relationships, access terms, and license
must be recorded independently. Translating a copyrighted passage does not
create redistribution rights, and linking to a source does not authorize local
mirroring. Cross-language alignment should normally store semantic claims,
short original paraphrases, and precise locators rather than copied passages.
The alignment model is documented in `analysis/MULTILINGUAL_KNOWLEDGE.md`.
