#!/usr/bin/env python3
"""Compile reviewed Question IR documents into a runtime SQLite database."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Iterable

try:
    from tools.validate_technical_ir import (
        Diagnostic,
        load_json,
        question_content_nodes,
        schema_diagnostics,
        semantic_diagnostics,
    )
except ModuleNotFoundError as error:
    if error.name != "tools":
        raise
    from validate_technical_ir import (
        Diagnostic,
        load_json,
        question_content_nodes,
        schema_diagnostics,
        semantic_diagnostics,
    )


DATABASE_SCHEMA_VERSION = 2


class CompilationError(RuntimeError):
    pass


def discover_question_documents(paths: Iterable[Path]) -> list[Path]:
    documents: list[Path] = []
    for path in paths:
        if path.is_dir():
            documents.extend(path.rglob("*.question.json"))
        elif path.is_file():
            documents.append(path)
        else:
            raise CompilationError(f"Question document path does not exist: {path}")
    result = sorted({path.resolve() for path in documents})
    if not result:
        raise CompilationError("No Question IR documents found")
    return result


def referenced_document_refs(document: dict[str, Any]) -> set[str]:
    references: set[str] = set()
    for _, node in question_content_nodes(document):
        document_ref = node.get("document_ref")
        if isinstance(document_ref, str):
            references.add(document_ref)
        for evidence in node.get("evidence", []):
            evidence_ref = evidence.get("document_ref")
            if isinstance(evidence_ref, str):
                references.add(evidence_ref)
    for evidence in document.get("answer_key", {}).get("evidence", []):
        evidence_ref = evidence.get("document_ref")
        if isinstance(evidence_ref, str):
            references.add(evidence_ref)
    return references


def load_referenced_documents(
    question_documents: Iterable[dict[str, Any]], project_root: Path
) -> dict[str, dict[str, Any]]:
    referenced: dict[str, dict[str, Any]] = {}
    for question in question_documents:
        for reference in sorted(referenced_document_refs(question)):
            path = Path(reference)
            resolved = path if path.is_absolute() else project_root / path
            try:
                referenced[reference] = load_json(resolved)
            except (OSError, ValueError, json.JSONDecodeError) as error:
                raise CompilationError(f"Unable to load referenced document {reference}: {error}") from error
    return referenced


def format_diagnostics(path: Path | str, diagnostics: Iterable[Diagnostic]) -> str:
    return "\n".join(
        f"{item.level.upper()} {path}:{item.path}: {item.message}"
        for item in diagnostics
    )


def validate_inventory_binding(
    path: Path,
    document: dict[str, Any],
    inventory_by_document_id: dict[str, dict[str, Any]],
) -> None:
    inventory = inventory_by_document_id.get(document["document_id"])
    if inventory is None:
        raise CompilationError(
            f"{path}: document_id {document['document_id']!r} is absent from the media inventory"
        )
    source = document["source_record"]
    expected_source = (
        inventory.get("source_file"),
        inventory.get("source_index"),
        inventory.get("question_number"),
    )
    actual_source = (
        source["source_file"],
        source["source_index"],
        source["question_number"],
    )
    if actual_source != expected_source:
        raise CompilationError(f"{path}: source_record does not match the media inventory")

    matching_assets = [
        asset
        for asset in document["assets"]
        if asset.get("role") == "source"
        and asset.get("asset_id") == inventory.get("asset_id")
    ]
    if len(matching_assets) != 1:
        raise CompilationError(
            f"{path}: expected exactly one source asset matching the media inventory"
        )
    asset = matching_assets[0]
    expected_asset = {
        "sha256": inventory.get("sha256"),
        "mime_type": inventory.get("mime_type"),
        "width": inventory.get("width"),
        "height": inventory.get("height"),
        "uri": inventory.get("image_path"),
    }
    actual_asset = {key: asset.get(key) for key in expected_asset}
    if actual_asset != expected_asset:
        raise CompilationError(f"{path}: source asset does not match the media inventory")


def validate_documents(
    paths: list[Path], project_root: Path
) -> list[dict[str, Any]]:
    schema_dir = project_root / "analysis" / "schemas"
    inventory_path = project_root / "analysis" / "media" / "inventory.json"
    try:
        inventory_payload = load_json(inventory_path)
        inventory_by_document_id = {
            item["document_id"]: item for item in inventory_payload.get("assets", [])
        }
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        raise CompilationError(f"Unable to load media inventory {inventory_path}: {error}") from error
    loaded: list[tuple[Path, dict[str, Any]]] = []
    for path in paths:
        try:
            document = load_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            raise CompilationError(f"Unable to load {path}: {error}") from error
        if document.get("schema_version") != "question-ir/v1":
            raise CompilationError(f"{path}: expected schema_version 'question-ir/v1'")
        loaded.append((path, document))

    documents = [document for _, document in loaded]
    referenced = load_referenced_documents(documents, project_root)

    for reference, document in referenced.items():
        diagnostics = schema_diagnostics(document, schema_dir)
        if not diagnostics:
            observation = None
            if document.get("schema_version") == "circuit-ir/v1":
                observation_ref = document.get("source_asset", {}).get("observation_document")
                observation = referenced.get(observation_ref)
            diagnostics.extend(semantic_diagnostics(document, observation, referenced))
        if any(item.level == "error" for item in diagnostics):
            raise CompilationError(format_diagnostics(reference, diagnostics))

    seen_document_ids: dict[str, Path] = {}
    seen_records: dict[tuple[str, int], Path] = {}
    for path, document in loaded:
        diagnostics = schema_diagnostics(document, schema_dir)
        if not diagnostics:
            diagnostics.extend(semantic_diagnostics(document, referenced_documents=referenced))
        if any(item.level == "error" for item in diagnostics):
            raise CompilationError(format_diagnostics(path, diagnostics))
        validate_inventory_binding(path, document, inventory_by_document_id)

        document_id = document["document_id"]
        if document_id in seen_document_ids:
            raise CompilationError(
                f"{path}: duplicate document_id {document_id!r}; first used by {seen_document_ids[document_id]}"
            )
        seen_document_ids[document_id] = path

        source = document["source_record"]
        record_key = (source["source_file"], source["source_index"])
        if record_key in seen_records:
            raise CompilationError(
                f"{path}: duplicate source record {record_key!r}; first used by {seen_records[record_key]}"
            )
        seen_records[record_key] = path
    return documents


def node_plain_text(node: dict[str, Any]) -> str:
    if node.get("kind") == "text":
        return str(node.get("text", ""))
    return str(node.get("plain_text") or node.get("alt_text") or "")


def render_plain_text(nodes: Iterable[dict[str, Any]]) -> str:
    raw = "".join(node_plain_text(node) for node in nodes)
    return re.sub(r"\s+", " ", raw).strip()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def create_structured_tables(connection: sqlite3.Connection) -> None:
    connection.execute("DROP TABLE IF EXISTS question_hint_content")
    connection.execute("DROP TABLE IF EXISTS question_answer_content")
    connection.execute("DROP TABLE IF EXISTS question_content_nodes")
    connection.execute("DROP TABLE IF EXISTS question_documents")
    connection.execute(
        """
        CREATE TABLE question_documents (
            question_id INTEGER PRIMARY KEY REFERENCES questions(id) ON DELETE CASCADE,
            document_id TEXT NOT NULL UNIQUE,
            schema_version TEXT NOT NULL,
            review_status TEXT NOT NULL,
            prompt_text TEXT NOT NULL,
            search_text TEXT NOT NULL,
            search_text_folded TEXT NOT NULL,
            document_json TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE question_content_nodes (
            question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
            node_id TEXT NOT NULL,
            container_kind TEXT NOT NULL CHECK(container_kind IN ('prompt', 'answer', 'hint')),
            container_position INTEGER NOT NULL,
            node_position INTEGER NOT NULL,
            kind TEXT NOT NULL,
            plain_text TEXT,
            latex TEXT,
            document_ref TEXT,
            asset_id TEXT,
            review_status TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            PRIMARY KEY(question_id, node_id),
            UNIQUE(question_id, container_kind, container_position, node_position)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE question_answer_content (
            question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
            answer_position INTEGER NOT NULL,
            plain_text TEXT NOT NULL,
            review_status TEXT NOT NULL,
            PRIMARY KEY(question_id, answer_position)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE question_hint_content (
            question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
            hint_position INTEGER NOT NULL,
            plain_text TEXT NOT NULL,
            review_status TEXT NOT NULL,
            PRIMARY KEY(question_id, hint_position)
        )
        """
    )
    connection.execute(
        "CREATE INDEX question_documents_review_idx ON question_documents(review_status, question_id)"
    )
    connection.execute(
        "CREATE INDEX question_content_nodes_container_idx "
        "ON question_content_nodes("
        "question_id, container_kind, container_position, node_position)"
    )


def resolve_question(
    connection: sqlite3.Connection, document: dict[str, Any]
) -> tuple[int, set[int]]:
    source = document["source_record"]
    row = connection.execute(
        """
        SELECT q.id, q.question_number, q.question_label, q.correct_answer_mask
        FROM questions q
        JOIN sources s ON s.id = q.source_id
        WHERE s.file_name = ? AND q.source_index = ?
        """,
        (source["source_file"], source["source_index"]),
    ).fetchone()
    if row is None:
        raise CompilationError(
            f"{document['document_id']}: source record {source['source_file']}:{source['source_index']} does not exist"
        )
    question_id, question_number, question_label, answer_mask = row
    if question_number != source["question_number"] or question_label != source["question_label"]:
        raise CompilationError(
            f"{document['document_id']}: source question number or label does not match the database"
        )

    database_positions = {
        item[0]
        for item in connection.execute(
            "SELECT position FROM answers WHERE question_id = ?", (question_id,)
        )
    }
    document_positions = {item["position"] for item in document["answers"]}
    if document_positions != database_positions:
        actual = sorted(document_positions)
        expected = sorted(database_positions)
        raise CompilationError(
            f"{document['document_id']}: answer positions {actual} "
            f"do not match database positions {expected}"
        )

    answer_key = document["answer_key"]
    if answer_key["status"] in {"extracted", "verified"}:
        mask_positions = {
            position for position in database_positions if answer_mask & (1 << (position - 1))
        }
        if set(answer_key["positions"]) != mask_positions:
            raise CompilationError(
                f"{document['document_id']}: answer key does not match the legacy bit mask"
            )
    return question_id, database_positions


def insert_content_nodes(
    connection: sqlite3.Connection,
    question_id: int,
    container_kind: str,
    container_position: int,
    nodes: list[dict[str, Any]],
) -> None:
    for node_position, node in enumerate(nodes):
        asset_id = (
            node.get("asset_id")
            or node.get("fallback_asset_id")
            or node.get("rendered_asset_id")
        )
        connection.execute(
            """
            INSERT INTO question_content_nodes(
                question_id, node_id, container_kind, container_position,
                node_position, kind, plain_text, latex, document_ref,
                asset_id, review_status, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                question_id,
                node["id"],
                container_kind,
                container_position,
                node_position,
                node["kind"],
                node_plain_text(node) or None,
                node.get("latex"),
                node.get("document_ref"),
                asset_id,
                node["review_status"],
                canonical_json(node),
            ),
        )


def insert_question_document(
    connection: sqlite3.Connection, document: dict[str, Any]
) -> None:
    question_id, _ = resolve_question(connection, document)
    prompt_text = render_plain_text(document["prompt"])
    answer_texts = [render_plain_text(item["content"]) for item in document["answers"]]
    hint_texts = [render_plain_text(item["content"]) for item in document["hints"]]
    search_text = re.sub(
        r"\s+", " ", " ".join([prompt_text, *answer_texts, *hint_texts])
    ).strip()
    review_status = document["verification"]["status"]

    connection.execute(
        """
        INSERT INTO question_documents(
            question_id, document_id, schema_version, review_status,
            prompt_text, search_text, search_text_folded, document_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            question_id,
            document["document_id"],
            document["schema_version"],
            review_status,
            prompt_text,
            search_text,
            search_text.casefold(),
            canonical_json(document),
        ),
    )
    insert_content_nodes(connection, question_id, "prompt", 0, document["prompt"])

    for answer in document["answers"]:
        answer_text = render_plain_text(answer["content"])
        connection.execute(
            """
            INSERT INTO question_answer_content(
                question_id, answer_position, plain_text, review_status
            ) VALUES (?, ?, ?, ?)
            """,
            (question_id, answer["position"], answer_text, answer["review_status"]),
        )
        insert_content_nodes(
            connection,
            question_id,
            "answer",
            answer["position"],
            answer["content"],
        )

    for hint in document["hints"]:
        hint_text = render_plain_text(hint["content"])
        connection.execute(
            """
            INSERT INTO question_hint_content(
                question_id, hint_position, plain_text, review_status
            ) VALUES (?, ?, ?, ?)
            """,
            (question_id, hint["position"], hint_text, hint["review_status"]),
        )
        insert_content_nodes(
            connection,
            question_id,
            "hint",
            hint["position"],
            hint["content"],
        )


def compile_question_bank(
    base_database: Path,
    output_database: Path,
    document_paths: Iterable[Path],
    project_root: Path,
) -> int:
    paths = discover_question_documents(document_paths)
    documents = validate_documents(paths, project_root)
    if not base_database.is_file():
        raise CompilationError(f"Base database does not exist: {base_database}")

    output_database.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_database.name}.", suffix=".tmp", dir=output_database.parent
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        shutil.copyfile(base_database, temporary_path)
        connection = sqlite3.connect(temporary_path)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            required_tables = {"sources", "topics", "questions", "answers", "metadata"}
            existing_tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            missing_tables = required_tables - existing_tables
            if missing_tables:
                raise CompilationError(
                    f"Base database is missing tables: {', '.join(sorted(missing_tables))}"
                )

            with connection:
                create_structured_tables(connection)
                for document in documents:
                    insert_question_document(connection, document)
                connection.execute(
                    "INSERT OR REPLACE INTO metadata(key, value) VALUES ('schema_version', ?)",
                    (str(DATABASE_SCHEMA_VERSION),),
                )
                connection.execute(
                    "INSERT OR REPLACE INTO metadata(key, value) VALUES ('question_ir_version', 'question-ir/v1')"
                )
                connection.execute(
                    "INSERT OR REPLACE INTO metadata(key, value) VALUES ('structured_question_count', ?)",
                    (str(len(documents)),),
                )
                connection.execute(f"PRAGMA user_version = {DATABASE_SCHEMA_VERSION}")

            foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
            if foreign_key_errors:
                raise CompilationError(f"Foreign-key validation failed: {foreign_key_errors}")
        finally:
            connection.close()
        os.replace(temporary_path, output_database)
    finally:
        temporary_path.unlink(missing_ok=True)
    return len(documents)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Compile Question IR JSON into a copy of the legacy question-bank SQLite database."
    )
    parser.add_argument("documents", type=Path, nargs="+", help="Question IR file or directory")
    parser.add_argument("--base-database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=project_root)
    args = parser.parse_args()

    try:
        count = compile_question_bank(
            args.base_database.resolve(),
            args.output.resolve(),
            args.documents,
            args.project_root.resolve(),
        )
    except CompilationError as error:
        print(f"ERROR: {error}")
        raise SystemExit(1) from error
    print(f"Compiled {count} Question IR document(s) into {args.output}")


if __name__ == "__main__":
    main()
