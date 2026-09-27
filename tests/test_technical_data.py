from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from tools.analyze_media import build_inventory, select_diverse_pilot
from tools.render_circuit_overlay import render_overlay
from tools.validate_technical_ir import schema_diagnostics, semantic_diagnostics


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "analysis" / "schemas"
EXAMPLE_DIR = ROOT / "analysis" / "examples"
DATABASE = ROOT / "analysis" / "database" / "question-bank.sqlite"
IMAGE_ROOT = ROOT / "kmp-app" / "composeApp" / "src" / "desktopMain" / "resources" / "images"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TechnicalIrTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.observation = load_json(EXAMPLE_DIR / "observation-ir-example.json")
        cls.circuit = load_json(EXAMPLE_DIR / "circuit-ir-example.json")

    def test_schemas_are_valid_draft_2020_12(self) -> None:
        for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
            with self.subTest(path=path.name):
                Draft202012Validator.check_schema(load_json(path))

    def test_examples_pass_schema_and_semantic_validation(self) -> None:
        self.assertEqual([], schema_diagnostics(self.observation, SCHEMA_DIR))
        self.assertEqual([], semantic_diagnostics(self.observation))
        self.assertEqual([], schema_diagnostics(self.circuit, SCHEMA_DIR))
        self.assertEqual([], semantic_diagnostics(self.circuit, self.observation))

    def test_validator_rejects_pin_assigned_to_two_nets(self) -> None:
        invalid = copy.deepcopy(self.circuit)
        invalid["nets"][1]["pin_ids"].append("pin:r1-top:1")
        messages = [item.message for item in semantic_diagnostics(invalid, self.observation)]
        self.assertTrue(any("already belongs to net" in message for message in messages))

    def test_example_is_bound_to_immutable_source_image(self) -> None:
        image = IMAGE_ROOT / "TEST2_018.jpg"
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        self.assertEqual(self.observation["source_asset"]["sha256"], digest)
        self.assertEqual(self.circuit["source_asset"]["sha256"], digest)

    def test_circuit_overlay_can_be_rendered_for_review(self) -> None:
        image = IMAGE_ROOT / "TEST2_018.jpg"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "overlay.png"
            render_overlay(self.circuit, image, output)
            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 1_000)


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
