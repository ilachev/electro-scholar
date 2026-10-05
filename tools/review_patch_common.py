"""Shared deterministic primitives for Question IR review patches."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


PATCH_SCHEMA_VERSION = "question-review-patch/v1"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def source_asset_sha256(document: dict[str, Any]) -> str:
    assets = [item for item in document.get("assets", []) if item.get("role") == "source"]
    if len(assets) != 1 or not isinstance(assets[0].get("sha256"), str):
        raise ValueError("Question IR must contain exactly one source asset with SHA-256")
    return assets[0]["sha256"]


def question_targets(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    targets: dict[str, dict[str, Any]] = {}
    collections: Iterable[dict[str, Any]] = (
        list(document.get("prompt", []))
        + [node for answer in document.get("answers", []) for node in answer.get("content", [])]
        + [node for hint in document.get("hints", []) for node in hint.get("content", [])]
        + [document.get("answer_key", {})]
    )
    for target in collections:
        target_id = target.get("id")
        if not isinstance(target_id, str) or not target_id:
            raise ValueError("Every review target must have a non-empty id")
        if target_id in targets:
            raise ValueError(f"Duplicate review target {target_id!r}")
        targets[target_id] = target
    return targets


def target_value(target: dict[str, Any]) -> str:
    kind = target.get("kind")
    if kind == "text":
        return str(target.get("text", ""))
    if kind == "formula":
        return str(target.get("latex", ""))
    if kind == "circuit":
        return str(target.get("document_ref", ""))
    if "positions" in target and "status" in target and "kind" not in target:
        return ", ".join(str(item) for item in target.get("positions", []))
    raise ValueError(f"Unsupported review target kind {kind!r}")


def target_plain_text(target: dict[str, Any]) -> str | None:
    if target.get("kind") == "formula":
        return str(target.get("plain_text", ""))
    return None


def stable_event_id(document_id: str, event: dict[str, Any]) -> str:
    identity = {
        "document_id": document_id,
        "source_event_id": event["source_event_id"],
        "target_ref": event["target_ref"],
        "reviewer": event["reviewer"],
        "decision": event["decision"],
        "comment": event["comment"],
        "original_value": event["original_value"],
        "submitted_value": event["submitted_value"],
        "original_plain_text": event["original_plain_text"],
        "submitted_plain_text": event["submitted_plain_text"],
        "created_at": event["created_at"],
    }
    return f"review:{canonical_sha256(identity)[:24]}"


def patch_identity(patch_without_id: dict[str, Any]) -> str:
    return f"question-review-patch:{canonical_sha256(patch_without_id)[:24]}"
