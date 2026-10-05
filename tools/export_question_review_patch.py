#!/usr/bin/env python3
"""Export one Question IR review overlay from SQLite as a deterministic JSON patch."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

try:
    from tools.review_patch_common import (
        PATCH_SCHEMA_VERSION,
        canonical_sha256,
        load_json,
        patch_identity,
        question_targets,
        source_asset_sha256,
        stable_event_id,
        target_plain_text,
        target_value,
    )
except ModuleNotFoundError as error:
    if error.name != "tools":
        raise
    from review_patch_common import (
        PATCH_SCHEMA_VERSION,
        canonical_sha256,
        load_json,
        patch_identity,
        question_targets,
        source_asset_sha256,
        stable_event_id,
        target_plain_text,
        target_value,
    )


class ReviewExportError(RuntimeError):
    pass


def select_document_id(connection: sqlite3.Connection, requested: str | None) -> str:
    reviewed = [
        row[0]
        for row in connection.execute(
            "SELECT DISTINCT document_id FROM review_events ORDER BY document_id"
        )
    ]
    if requested is not None:
        if requested not in reviewed:
            raise ReviewExportError(f"No review events found for {requested!r}")
        return requested
    if not reviewed:
        raise ReviewExportError("The review database contains no review events")
    if len(reviewed) != 1:
        raise ReviewExportError("Multiple documents have review events; pass --document-id")
    return reviewed[0]


def export_patch(connection: sqlite3.Connection, document_id: str | None = None) -> dict[str, Any]:
    try:
        selected_id = select_document_id(connection, document_id)
        snapshot_row = connection.execute(
            "SELECT schema_version, base_document_json "
            "FROM review_documents WHERE document_id = ?",
            (selected_id,),
        ).fetchone()
    except sqlite3.Error as error:
        raise ReviewExportError(f"Invalid review database: {error}") from error
    if snapshot_row is None:
        raise ReviewExportError(f"Review snapshot is missing for {selected_id!r}")
    schema_version, base_document_json = snapshot_row
    try:
        base_document = json.loads(base_document_json)
    except json.JSONDecodeError as error:
        raise ReviewExportError(f"Stored Question IR is invalid JSON: {error}") from error
    if schema_version != "question-ir/v1" or base_document.get("schema_version") != schema_version:
        raise ReviewExportError("Stored Question IR schema metadata is inconsistent")
    if base_document.get("document_id") != selected_id:
        raise ReviewExportError("Stored Question IR document_id is inconsistent")

    targets = question_targets(base_document)
    rows = connection.execute(
        "SELECT id, node_id, reviewer, decision, comment, original_value, "
        "submitted_value, original_plain_text, submitted_plain_text, created_at "
        "FROM review_events "
        "WHERE document_id = ? ORDER BY id",
        (selected_id,),
    ).fetchall()
    events: list[dict[str, Any]] = []
    for row in rows:
        (
            source_event_id,
            target_ref,
            reviewer,
            decision,
            comment,
            original,
            submitted,
            original_plain_text,
            submitted_plain_text,
            created,
        ) = row
        target = targets.get(target_ref)
        if target is None:
            raise ReviewExportError(f"Review event targets unknown node {target_ref!r}")
        if target_value(target) != original:
            raise ReviewExportError(f"Original value does not match base node {target_ref!r}")
        base_plain_text = target_plain_text(target)
        if base_plain_text != original_plain_text:
            raise ReviewExportError(
                f"Original plain text does not match base node {target_ref!r}"
            )
        if target.get("kind") == "formula":
            if not isinstance(submitted_plain_text, str) or not submitted_plain_text.strip():
                raise ReviewExportError(
                    f"Formula node {target_ref!r} requires submitted plain text"
                )
        elif original_plain_text is not None or submitted_plain_text is not None:
            raise ReviewExportError(
                f"Non-formula node {target_ref!r} cannot contain formula plain text"
            )
        if decision == "accept" and (
            submitted != original or submitted_plain_text != original_plain_text
        ):
            raise ReviewExportError(f"Accepted node {target_ref!r} contains an unmarked correction")
        if decision == "correct" and (
            submitted == original and submitted_plain_text == original_plain_text
        ):
            raise ReviewExportError(f"Corrected node {target_ref!r} did not change")
        event = {
            "source_event_id": source_event_id,
            "target_ref": target_ref,
            "reviewer": reviewer,
            "decision": decision,
            "comment": comment,
            "original_value": original,
            "submitted_value": submitted,
            "original_plain_text": original_plain_text,
            "submitted_plain_text": submitted_plain_text,
            "created_at": created,
        }
        event["id"] = stable_event_id(selected_id, event)
        events.append({"id": event.pop("id"), **event})

    body = {
        "schema_version": PATCH_SCHEMA_VERSION,
        "document_id": selected_id,
        "base_document_sha256": canonical_sha256(base_document),
        "source_asset_sha256": source_asset_sha256(base_document),
        "events": events,
    }
    return {
        "schema_version": body["schema_version"],
        "patch_id": patch_identity(body),
        "document_id": body["document_id"],
        "base_document_sha256": body["base_document_sha256"],
        "source_asset_sha256": body["source_asset_sha256"],
        "events": body["events"],
    }


def validate_patch(patch: dict[str, Any], schema_path: Path) -> None:
    schema = load_json(schema_path)
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(patch),
        key=lambda item: list(item.path),
    )
    if errors:
        details = "; ".join(error.message for error in errors)
        raise ReviewExportError(f"Generated patch does not match its schema: {details}")


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(payload)
        os.replace(temporary_name, path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise


def build_parser() -> argparse.ArgumentParser:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path.home() / ".electroscholar" / "question-review.sqlite",
    )
    parser.add_argument("--document-id")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--schema",
        type=Path,
        default=project_root / "analysis" / "schemas" / "question-review-patch-v1.schema.json",
    )
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    if not arguments.database.is_file():
        raise SystemExit(f"Review database does not exist: {arguments.database}")
    try:
        with sqlite3.connect(f"file:{arguments.database}?mode=ro", uri=True) as connection:
            patch = export_patch(connection, arguments.document_id)
        validate_patch(patch, arguments.schema)
        write_json_atomic(arguments.output, patch)
    except (ReviewExportError, ValueError, OSError, sqlite3.Error) as error:
        raise SystemExit(str(error)) from error
    print(f"Exported {len(patch['events'])} events to {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
