from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from tools.analyze_media import build_inventory, select_diverse_pilot
from tools.compile_question_bank import CompilationError, compile_question_bank
from tools.render_circuit_overlay import render_overlay
from tools.validate_technical_ir import schema_diagnostics, semantic_diagnostics


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "analysis" / "schemas"
EXAMPLE_DIR = ROOT / "analysis" / "examples"
QUESTION_DIR = ROOT / "analysis" / "questions"
DATABASE = ROOT / "analysis" / "database" / "question-bank.sqlite"
PACKAGED_DATABASE = (
    ROOT
    / "kmp-app"
    / "features"
    / "question-bank"
    / "src"
    / "commonMain"
    / "composeResources"
    / "files"
    / "database"
    / "question_bank.sqlite"
)
IMAGE_ROOT = (
    ROOT
    / "kmp-app"
    / "features"
    / "question-bank"
    / "src"
    / "commonMain"
    / "composeResources"
    / "drawable"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TechnicalIrTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.observation = load_json(EXAMPLE_DIR / "observation-ir-example.json")
        cls.circuit = load_json(EXAMPLE_DIR / "circuit-ir-example.json")
        cls.question = load_json(QUESTION_DIR / "test2-018.question.json")
        cls.referenced_documents = {
            "analysis/examples/observation-ir-example.json": cls.observation,
            "analysis/examples/circuit-ir-example.json": cls.circuit,
        }

    def test_schemas_are_valid_draft_2020_12(self) -> None:
        for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
            with self.subTest(path=path.name):
                Draft202012Validator.check_schema(load_json(path))

    def test_examples_pass_schema_and_semantic_validation(self) -> None:
        self.assertEqual([], schema_diagnostics(self.observation, SCHEMA_DIR))
        self.assertEqual([], semantic_diagnostics(self.observation))
        self.assertEqual([], schema_diagnostics(self.circuit, SCHEMA_DIR))
        self.assertEqual([], semantic_diagnostics(self.circuit, self.observation))
        self.assertEqual([], schema_diagnostics(self.question, SCHEMA_DIR))
        self.assertEqual(
            [],
            semantic_diagnostics(
                self.question, referenced_documents=self.referenced_documents
            ),
        )

    def test_validator_rejects_pin_assigned_to_two_nets(self) -> None:
        invalid = copy.deepcopy(self.circuit)
        invalid["nets"][1]["pin_ids"].append("pin:r1-top:1")
        messages = [item.message for item in semantic_diagnostics(invalid, self.observation)]
        self.assertTrue(any("already belongs to net" in message for message in messages))

    def test_example_is_bound_to_immutable_source_image(self) -> None:
        image = IMAGE_ROOT / "test2_018.jpg"
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        self.assertEqual(self.observation["source_asset"]["sha256"], digest)
        self.assertEqual(self.circuit["source_asset"]["sha256"], digest)

    def test_circuit_overlay_can_be_rendered_for_review(self) -> None:
        image = IMAGE_ROOT / "test2_018.jpg"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "overlay.png"
            render_overlay(self.circuit, image, output)
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 1_000)

    def test_verified_question_requires_completed_human_review(self) -> None:
        invalid = copy.deepcopy(self.question)
        invalid["verification"]["status"] = "verified"
        messages = [
            item.message
            for item in semantic_diagnostics(
                invalid, referenced_documents=self.referenced_documents
            )
        ]
        self.assertTrue(any("verified answer key" in message for message in messages))
        self.assertTrue(any("was not accepted" in message for message in messages))
        self.assertTrue(any("incomplete verification" in message for message in messages))

    def test_question_ir_compiles_into_searchable_runtime_tables(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "question-bank.sqlite"
            count = compile_question_bank(DATABASE, output, [QUESTION_DIR], ROOT)
            self.assertEqual(1, count)

            connection = sqlite3.connect(output)
            try:
                self.assertEqual(
                    2, connection.execute("PRAGMA user_version").fetchone()[0]
                )
                row = connection.execute(
                    """
                    SELECT qd.prompt_text, qd.search_text_folded, qac.plain_text
                    FROM question_documents qd
                    JOIN question_answer_content qac
                      ON qac.question_id = qd.question_id
                    WHERE qd.document_id = 'legacy-test:test2:018'
                      AND qac.answer_position = 5
                    """
                ).fetchone()
                self.assertIsNotNone(row)
                self.assertIn("эквивалентным генератором", row[0])
                self.assertIn("напряжению", row[1])
                self.assertEqual("Нулю.", row[2])
                self.assertEqual(
                    "ЭДС генератора равна напряжению U_AB на разомкнутых "
                    "выходных зажимах цепи.",
                    connection.execute(
                        """
                        SELECT plain_text
                        FROM question_hint_content
                        WHERE hint_position = 1
                        """
                    ).fetchone()[0],
                )
                self.assertEqual(
                    21,
                    connection.execute(
                        "SELECT COUNT(*) FROM question_content_nodes"
                    ).fetchone()[0],
                )
            finally:
                connection.close()

    def test_question_compiler_rejects_asset_not_in_inventory(self) -> None:
        invalid = copy.deepcopy(self.question)
        invalid["assets"][0]["uri"] = "images/not-the-source.jpg"
        with tempfile.TemporaryDirectory() as directory:
            document_path = Path(directory) / "invalid.question.json"
            document_path.write_text(
                json.dumps(invalid, ensure_ascii=False), encoding="utf-8"
            )
            with self.assertRaisesRegex(CompilationError, "media inventory"):
                compile_question_bank(
                    DATABASE,
                    Path(directory) / "output.sqlite",
                    [document_path],
                    ROOT,
                )

    def test_runtime_database_matches_analysis_database(self) -> None:
        self.assertEqual(
            hashlib.sha256(DATABASE.read_bytes()).digest(),
            hashlib.sha256(PACKAGED_DATABASE.read_bytes()).digest(),
        )


class MediaInventoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = build_inventory(DATABASE, IMAGE_ROOT)
        cls.snapshot = load_json(ROOT / "analysis" / "media" / "inventory.json")
        cls.pilot_snapshot = load_json(ROOT / "analysis" / "media" / "pilot-50.json")

    def test_all_question_images_are_inventoried_and_unique(self) -> None:
        self.assertEqual(582, len(self.records))
        self.assertEqual(582, len({record["sha256"] for record in self.records}))
        self.assertEqual(
            [record["document_id"] for record in self.snapshot["assets"]],
            [record["document_id"] for record in self.records],
        )
        self.assertEqual(
            [record["sha256"] for record in self.snapshot["assets"]],
            [record["sha256"] for record in self.records],
        )

    def test_pilot_is_reproducible_and_balanced_by_topic(self) -> None:
        pilot = select_diverse_pilot(self.records, per_topic=5)
        self.assertEqual(50, len(pilot))
        self.assertEqual(
            [item["document_id"] for item in self.pilot_snapshot["items"]],
            [item["document_id"] for item in pilot],
        )
        topic_counts: dict[str, int] = {}
        for item in pilot:
            topic_counts[item["topic_key"]] = topic_counts.get(item["topic_key"], 0) + 1
        self.assertEqual(10, len(topic_counts))
        self.assertEqual({5}, set(topic_counts.values()))


if __name__ == "__main__":
    unittest.main()
