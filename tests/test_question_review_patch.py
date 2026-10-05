from __future__ import annotations

import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from tools.apply_question_review_patch import ReviewApplyError, apply_patch, validate_result
from tools.export_question_review_patch import export_patch
from tools.review_patch_common import (
    canonical_json,
    patch_identity,
    stable_event_id,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUESTION_PATH = PROJECT_ROOT / "analysis" / "questions" / "test2-018.question.json"
PATCH_SCHEMA_PATH = (
    PROJECT_ROOT / "analysis" / "schemas" / "question-review-patch-v1.schema.json"
)


class QuestionReviewPatchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.question = json.loads(QUESTION_PATH.read_text(encoding="utf-8"))
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.database_path = Path(self.temporary_directory.name) / "review.sqlite"
        self.connection = sqlite3.connect(self.database_path)
        self.addCleanup(self.connection.close)
        self.connection.executescript(
            """
            CREATE TABLE review_documents (
                document_id TEXT NOT NULL PRIMARY KEY,
                schema_version TEXT NOT NULL,
                base_document_json TEXT NOT NULL
            );
            CREATE TABLE review_events (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                reviewer TEXT NOT NULL,
                decision TEXT NOT NULL,
                comment TEXT NOT NULL,
                original_value TEXT NOT NULL,
                submitted_value TEXT NOT NULL,
                original_plain_text TEXT,
                submitted_plain_text TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        self.connection.execute(
            "INSERT INTO review_documents VALUES (?, ?, ?)",
            (
                self.question["document_id"],
                self.question["schema_version"],
                canonical_json(self.question),
            ),
        )
        self.connection.executemany(
            """
            INSERT INTO review_events(
                document_id, node_id, reviewer, decision, comment,
                original_value, submitted_value, original_plain_text,
                submitted_plain_text, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    self.question["document_id"],
                    "prompt:text:1",
                    "reviewer:test",
                    "accept",
                    "Matches the source crop",
                    "Дано: ",
                    "Дано: ",
                    None,
                    None,
                    "2026-10-02T09:00:00.000Z",
                ),
                (
                    self.question["document_id"],
                    "prompt:formula:u0",
                    "reviewer:test",
                    "correct",
                    "Corrected the value for the patch test",
                    "U_0 = 120\\,\\text{В}",
                    "U_0 = 121\\,\\text{В}",
                    "U₀ = 120 В",
                    "U₀ = 121 В",
                    "2026-10-02T09:01:00.000Z",
                ),
                (
                    self.question["document_id"],
                    "answer-key",
                    "reviewer:test",
                    "accept",
                    "Legacy extraction confirmed visually",
                    "5",
                    "5",
                    None,
                    None,
                    "2026-10-02T09:02:00.000Z",
                ),
            ],
        )
        self.connection.commit()

    def test_export_is_deterministic_and_matches_schema(self) -> None:
        first = export_patch(self.connection)
        second = export_patch(self.connection, self.question["document_id"])

        self.assertEqual(first, second)
        self.assertEqual(3, len(first["events"]))
        self.assertTrue(first["patch_id"].startswith("question-review-patch:"))
        schema = json.loads(PATCH_SCHEMA_PATH.read_text(encoding="utf-8"))
        errors = list(
            Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(first)
        )
        self.assertEqual([], errors)

    def test_apply_updates_candidates_but_never_verifies_question(self) -> None:
        patch = export_patch(self.connection)
        original = copy.deepcopy(self.question)

        result = apply_patch(self.question, patch)
        validate_result(result, PROJECT_ROOT / "analysis" / "schemas")

        self.assertEqual(original, self.question)
        self.assertEqual("accepted", result["prompt"][0]["review_status"])
        self.assertEqual("corrected", result["prompt"][1]["review_status"])
        self.assertEqual("U_0 = 121\\,\\text{В}", result["prompt"][1]["latex"])
        self.assertEqual("U₀ = 121 В", result["prompt"][1]["plain_text"])
        self.assertEqual("in_review", result["verification"]["status"])
        self.assertEqual(["reviewer:test"], result["verification"]["reviewers"])
        self.assertEqual("extracted", result["answer_key"]["status"])
        self.assertEqual(3, len(result["review_events"]))

    def test_apply_rejects_a_different_base_revision(self) -> None:
        patch = export_patch(self.connection)
        changed = copy.deepcopy(self.question)
        changed["prompt"][0]["text"] = "Изменено: "

        with self.assertRaisesRegex(ReviewApplyError, "base fingerprint"):
            apply_patch(changed, patch)

    def test_apply_rejects_a_partial_formula_correction(self) -> None:
        patch = export_patch(self.connection)
        formula_event = next(
            event for event in patch["events"] if event["target_ref"] == "prompt:formula:u0"
        )
        formula_event["submitted_plain_text"] = None
        formula_event["id"] = stable_event_id(patch["document_id"], formula_event)
        patch["patch_id"] = patch_identity(
            {key: value for key, value in patch.items() if key != "patch_id"}
        )

        with self.assertRaisesRegex(ReviewApplyError, "requires submitted plain text"):
            apply_patch(self.question, patch)


if __name__ == "__main__":
    unittest.main()
