#!/usr/bin/env python3
"""Validate and apply one review patch to a Question IR document atomically."""

from __future__ import annotations

import argparse
import copy
import json
import os
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
    from tools.validate_technical_ir import schema_diagnostics, semantic_diagnostics
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
    from validate_technical_ir import schema_diagnostics, semantic_diagnostics


class ReviewApplyError(RuntimeError):
    pass


def validate_patch_identity(patch: dict[str, Any]) -> None:
    body = {key: value for key, value in patch.items() if key != "patch_id"}
    if patch.get("schema_version") != PATCH_SCHEMA_VERSION:
        raise ReviewApplyError("Unsupported review patch schema")
    if patch.get("patch_id") != patch_identity(body):
        raise ReviewApplyError("Review patch_id does not match its content")
    previous_source_id = 0
    seen_event_ids: set[str] = set()
    for event in patch.get("events", []):
        if event["source_event_id"] <= previous_source_id:
            raise ReviewApplyError("Review events are not in strict source order")
        previous_source_id = event["source_event_id"]
        if event["id"] in seen_event_ids:
            raise ReviewApplyError(f"Duplicate review event id {event['id']!r}")
        seen_event_ids.add(event["id"])
        if event["id"] != stable_event_id(patch["document_id"], event):
            raise ReviewApplyError(f"Review event id {event['id']!r} does not match its content")


def aggregate_container_status(content: list[dict[str, Any]]) -> str:
    statuses = [node.get("review_status") for node in content]
    if "rejected" in statuses:
        return "rejected"
    if statuses and all(status in {"accepted", "corrected"} for status in statuses):
        return "corrected" if "corrected" in statuses else "accepted"
    return "needs_review"


def apply_patch(document: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    validate_patch_identity(patch)
    if document.get("document_id") != patch.get("document_id"):
        raise ReviewApplyError("Patch document_id does not match Question IR")
    if document.get("verification", {}).get("status") == "verified":
        raise ReviewApplyError("A review patch cannot be applied to a verified Question IR")
    if canonical_sha256(document) != patch.get("base_document_sha256"):
        raise ReviewApplyError("Question IR does not match the patch base fingerprint")
    if source_asset_sha256(document) != patch.get("source_asset_sha256"):
        raise ReviewApplyError("Question IR source asset does not match the patch")

    result = copy.deepcopy(document)
    answer_key_id = document["answer_key"]["id"]
    base_targets = question_targets(document)
    result_targets = question_targets(result)
    existing_event_ids = {event.get("id") for event in result.get("review_events", [])}
    patch_event_ids = {event["id"] for event in patch["events"]}
    duplicate_ids = sorted(existing_event_ids & patch_event_ids)
    if duplicate_ids:
        raise ReviewApplyError(f"Review events are already present: {', '.join(duplicate_ids)}")

    latest_by_target: dict[str, dict[str, Any]] = {}
    for event in patch["events"]:
        target_ref = event["target_ref"]
        base_target = base_targets.get(target_ref)
        if base_target is None:
            raise ReviewApplyError(f"Unknown review target {target_ref!r}")
        if target_value(base_target) != event["original_value"]:
            raise ReviewApplyError(f"Original value conflict for {target_ref!r}")
        base_plain_text = target_plain_text(base_target)
        if base_plain_text != event["original_plain_text"]:
            raise ReviewApplyError(f"Original plain text conflict for {target_ref!r}")
        if base_target.get("kind") == "formula":
            submitted_plain_text = event["submitted_plain_text"]
            if not isinstance(submitted_plain_text, str) or not submitted_plain_text.strip():
                raise ReviewApplyError(
                    f"Formula target {target_ref!r} requires submitted plain text"
                )
        elif (
            event["original_plain_text"] is not None
            or event["submitted_plain_text"] is not None
        ):
            raise ReviewApplyError(
                f"Non-formula target {target_ref!r} cannot contain formula plain text"
            )
        if event["decision"] == "accept" and (
            event["submitted_value"] != event["original_value"]
            or event["submitted_plain_text"] != event["original_plain_text"]
        ):
            raise ReviewApplyError(f"Accepted target {target_ref!r} contains a correction")
        if event["decision"] == "correct" and (
            event["submitted_value"] == event["original_value"]
            and event["submitted_plain_text"] == event["original_plain_text"]
        ):
            raise ReviewApplyError(f"Corrected target {target_ref!r} did not change")
        latest_by_target[target_ref] = event
        result.setdefault("review_events", []).append(
            {
                "id": event["id"],
                "target_ref": target_ref,
                "reviewer": event["reviewer"],
                "decision": event["decision"],
                "comment": event["comment"],
                "created_at": event["created_at"],
            }
        )

    rejected = False
    for target_ref, event in latest_by_target.items():
        target = result_targets[target_ref]
        decision = event["decision"]
        if target_ref == answer_key_id:
            if decision == "reject":
                target["status"] = "disputed"
                rejected = True
            elif decision == "correct":
                raise ReviewApplyError("Answer-key correction requires a dedicated verification workflow")
            continue

        if decision == "correct":
            if target.get("kind") == "text":
                target["text"] = event["submitted_value"]
            elif target.get("kind") == "formula":
                target["latex"] = event["submitted_value"]
                target["plain_text"] = event["submitted_plain_text"]
            else:
                raise ReviewApplyError(f"Target {target_ref!r} cannot be edited as text")
            target["review_status"] = "corrected"
        elif decision == "accept":
            target["review_status"] = "accepted"
        elif decision == "reject":
            target["review_status"] = "rejected"
            rejected = True
        else:
            target["review_status"] = "needs_review"

    for container_name in ("answers", "hints"):
        for container in result.get(container_name, []):
            container["review_status"] = aggregate_container_status(container.get("content", []))
            if container["review_status"] == "rejected":
                rejected = True

    verification = result["verification"]
    for event in patch["events"]:
        if event["reviewer"] not in verification["reviewers"]:
            verification["reviewers"].append(event["reviewer"])
    verification["updated_at"] = max(event["created_at"] for event in patch["events"])
    verification["status"] = "rejected" if rejected else "in_review"
    return result


def validate_result(document: dict[str, Any], schema_dir: Path) -> None:
    diagnostics = schema_diagnostics(document, schema_dir)
    if not diagnostics:
        diagnostics.extend(semantic_diagnostics(document))
    errors = [item for item in diagnostics if item.level == "error"]
    if errors:
        details = "; ".join(f"{item.path}: {item.message}" for item in errors)
        raise ReviewApplyError(f"Patched Question IR is invalid: {details}")


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
    parser.add_argument("patch", type=Path)
    parser.add_argument("question", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--patch-schema",
        type=Path,
        default=project_root / "analysis" / "schemas" / "question-review-patch-v1.schema.json",
    )
    parser.add_argument(
        "--schema-dir",
        type=Path,
        default=project_root / "analysis" / "schemas",
    )
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    try:
        patch = load_json(arguments.patch)
        schema = load_json(arguments.patch_schema)
        schema_errors = sorted(
            Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(patch),
            key=lambda item: list(item.path),
        )
        if schema_errors:
            raise ReviewApplyError(
                "Invalid review patch: " + "; ".join(error.message for error in schema_errors)
            )
        question = load_json(arguments.question)
        result = apply_patch(question, patch)
        validate_result(result, arguments.schema_dir)
        if arguments.check:
            print(f"Patch {patch['patch_id']} is applicable")
            return 0
        output = arguments.output or arguments.question
        write_json_atomic(output, result)
    except (ReviewApplyError, ValueError, OSError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from error
    print(f"Applied {len(patch['events'])} events to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
