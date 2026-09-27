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
