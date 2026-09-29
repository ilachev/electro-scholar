#!/usr/bin/env python3
"""Validate Technical IR JSON documents at schema and graph-reference levels."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker


SCHEMA_FILES = {
    "observation-ir/v1": "observation-ir-v1.schema.json",
    "circuit-ir/v1": "circuit-ir-v1.schema.json",
    "question-ir/v1": "question-ir-v1.schema.json",
}


@dataclass(frozen=True)
class Diagnostic:
    level: str
    path: str
    message: str


def json_path(parts: Iterable[Any]) -> str:
    result = "$"
    for part in parts:
        result += f"[{part}]" if isinstance(part, int) else f".{part}"
    return result


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: document root must be an object")
    return payload


def load_schema(schema_dir: Path, version: str) -> dict[str, Any]:
    file_name = SCHEMA_FILES.get(version)
    if file_name is None:
        raise ValueError(f"Unsupported schema_version: {version!r}")
    schema = load_json(schema_dir / file_name)
    Draft202012Validator.check_schema(schema)
    return schema


def schema_diagnostics(
    document: dict[str, Any], schema_dir: Path
) -> list[Diagnostic]:
    version = document.get("schema_version")
    if not isinstance(version, str):
        return [Diagnostic("error", "$.schema_version", "Missing schema version")]
    try:
        schema = load_schema(schema_dir, version)
    except (OSError, ValueError) as error:
        return [Diagnostic("error", "$.schema_version", str(error))]
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        Diagnostic("error", json_path(error.absolute_path), error.message)
        for error in sorted(validator.iter_errors(document), key=lambda item: list(item.absolute_path))
    ]


def duplicate_id_diagnostics(
    collections: Iterable[tuple[str, list[dict[str, Any]]]]
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    locations: dict[str, str] = {}
    for collection_name, items in collections:
        for index, item in enumerate(items):
            item_id = item.get("id")
            if not isinstance(item_id, str):
                continue
            location = f"$.{collection_name}[{index}].id"
            previous = locations.get(item_id)
            if previous is not None:
                diagnostics.append(
                    Diagnostic(
                        "error",
                        location,
                        f"Duplicate id {item_id!r}; first declared at {previous}",
                    )
                )
            else:
                locations[item_id] = location
    return diagnostics


def observation_diagnostics(document: dict[str, Any]) -> list[Diagnostic]:
    regions = document.get("regions", [])
    primitives = document.get("primitives", [])
    hypotheses = document.get("hypotheses", [])
    reviews = document.get("review_events", [])
    diagnostics = duplicate_id_diagnostics(
        (
            ("regions", regions),
            ("primitives", primitives),
            ("hypotheses", hypotheses),
            ("review_events", reviews),
        )
    )

    region_ids = {item.get("id") for item in regions}
    primitive_ids = {item.get("id") for item in primitives}
    hypothesis_ids = {item.get("id") for item in hypotheses}
    target_ids = region_ids | primitive_ids | hypothesis_ids

    for index, primitive in enumerate(primitives):
        if primitive.get("region_id") not in region_ids:
            diagnostics.append(
                Diagnostic(
                    "error",
                    f"$.primitives[{index}].region_id",
                    f"Unknown region {primitive.get('region_id')!r}",
                )
            )
    for index, hypothesis in enumerate(hypotheses):
        for ref_index, reference in enumerate(hypothesis.get("input_refs", [])):
            if reference not in target_ids:
                diagnostics.append(
                    Diagnostic(
                        "error",
                        f"$.hypotheses[{index}].input_refs[{ref_index}]",
                        f"Unknown observation reference {reference!r}",
                    )
                )
    for index, review in enumerate(reviews):
        if review.get("target_ref") not in target_ids:
            diagnostics.append(
                Diagnostic(
                    "error",
                    f"$.review_events[{index}].target_ref",
                    f"Unknown review target {review.get('target_ref')!r}",
                )
            )
    return diagnostics


def known_observation_ids(document: dict[str, Any] | None) -> set[str] | None:
    if document is None:
        return None
    return {
        item["id"]
        for key in ("regions", "primitives", "hypotheses", "review_events")
        for item in document.get(key, [])
        if isinstance(item.get("id"), str)
    }


def question_content_nodes(
    document: dict[str, Any],
) -> Iterable[tuple[str, dict[str, Any]]]:
    for index, node in enumerate(document.get("prompt", [])):
        yield f"$.prompt[{index}]", node
    for answer_index, answer in enumerate(document.get("answers", [])):
        for node_index, node in enumerate(answer.get("content", [])):
            yield f"$.answers[{answer_index}].content[{node_index}]", node
    for hint_index, hint in enumerate(document.get("hints", [])):
        for node_index, node in enumerate(hint.get("content", [])):
            yield f"$.hints[{hint_index}].content[{node_index}]", node


def bounds_fit_asset(bounds: dict[str, Any], asset: dict[str, Any]) -> bool:
    width = asset.get("width")
    height = asset.get("height")
    if not isinstance(width, int) or not isinstance(height, int):
        return True
    return (
        bounds.get("x", 0) + bounds.get("width", 0) <= width
        and bounds.get("y", 0) + bounds.get("height", 0) <= height
    )


def question_diagnostics(
    document: dict[str, Any],
    referenced_documents: dict[str, dict[str, Any]] | None = None,
) -> list[Diagnostic]:
    assets = document.get("assets", [])
    producers = document.get("producers", [])
    answers = document.get("answers", [])
    hints = document.get("hints", [])
    checks = document.get("verification", {}).get("checks", [])
    reviews = document.get("review_events", [])
    content = list(question_content_nodes(document))

    duplicate_collections: list[tuple[str, list[dict[str, Any]]]] = [
        ("assets", assets),
        ("producers", producers),
        ("answers", answers),
        ("hints", hints),
        ("verification.checks", checks),
        ("review_events", reviews),
    ]
    duplicate_collections.extend((path.removeprefix("$."), [node]) for path, node in content)
    diagnostics = duplicate_id_diagnostics(duplicate_collections)

    asset_by_id: dict[Any, dict[str, Any]] = {}
    for index, asset in enumerate(assets):
        asset_id = asset.get("asset_id")
        if asset_id in asset_by_id:
            diagnostics.append(
                Diagnostic(
                    "error",
                    f"$.assets[{index}].asset_id",
                    f"Duplicate asset_id {asset_id!r}",
                )
            )
        asset_by_id[asset_id] = asset
        sha256 = asset.get("sha256")
        if isinstance(asset_id, str) and asset_id.startswith("sha256:"):
            if asset_id != f"sha256:{sha256}":
                diagnostics.append(
                    Diagnostic(
                        "error",
                        f"$.assets[{index}].asset_id",
                        "SHA-256 asset_id does not match the declared digest",
                    )
                )
    producer_ids = {item.get("id") for item in producers}
    answer_positions: dict[int, int] = {}
    hint_positions: dict[int, int] = {}

    for index, answer in enumerate(answers):
        position = answer.get("position")
        if isinstance(position, int):
            previous = answer_positions.get(position)
            if previous is not None:
                diagnostics.append(
                    Diagnostic(
                        "error",
                        f"$.answers[{index}].position",
                        f"Answer position {position} is already used at $.answers[{previous}]",
                    )
                )
            answer_positions[position] = index

    for index, hint in enumerate(hints):
        position = hint.get("position")
        if isinstance(position, int):
            previous = hint_positions.get(position)
            if previous is not None:
                diagnostics.append(
                    Diagnostic(
                        "error",
                        f"$.hints[{index}].position",
                        f"Hint position {position} is already used at $.hints[{previous}]",
                    )
                )
            hint_positions[position] = index

    def validate_evidence(path: str, evidence_items: list[dict[str, Any]]) -> None:
        for index, evidence in enumerate(evidence_items):
            evidence_path = f"{path}.evidence[{index}]"
            kind = evidence.get("kind")
            if kind == "source_asset":
                asset = asset_by_id.get(evidence.get("asset_id"))
                if asset is None:
                    diagnostics.append(
                        Diagnostic(
                            "error",
                            f"{evidence_path}.asset_id",
                            f"Unknown asset {evidence.get('asset_id')!r}",
                        )
                    )
                elif "bounds" in evidence and not bounds_fit_asset(evidence["bounds"], asset):
                    diagnostics.append(
                        Diagnostic("error", f"{evidence_path}.bounds", "Bounds exceed asset dimensions")
                    )
            elif kind == "observation" and referenced_documents is not None:
                reference = evidence.get("document_ref")
                observation = referenced_documents.get(reference)
                if observation is None:
                    diagnostics.append(
                        Diagnostic("error", f"{evidence_path}.document_ref", f"Document {reference!r} was not loaded")
                    )
                elif observation.get("schema_version") != "observation-ir/v1":
                    diagnostics.append(
                        Diagnostic(
                            "error",
                            f"{evidence_path}.document_ref",
                            "Referenced document is not Observation IR",
                        )
                    )
                else:
                    known_ids = known_observation_ids(observation) or set()
                    for ref_index, observation_ref in enumerate(evidence.get("observation_refs", [])):
                        if observation_ref not in known_ids:
                            diagnostics.append(
                                Diagnostic(
                                    "error",
                                    f"{evidence_path}.observation_refs[{ref_index}]",
                                    f"Unknown observation reference {observation_ref!r}",
                                )
                            )
            elif kind == "derived_document" and referenced_documents is not None:
                reference = evidence.get("document_ref")
                if reference not in referenced_documents:
                    diagnostics.append(
                        Diagnostic("error", f"{evidence_path}.document_ref", f"Document {reference!r} was not loaded")
                    )

    for path, node in content:
        if node.get("producer_ref") not in producer_ids:
            diagnostics.append(
                Diagnostic(
                    "error",
                    f"{path}.producer_ref",
                    f"Unknown producer {node.get('producer_ref')!r}",
                )
            )
        validate_evidence(path, node.get("evidence", []))

        referenced_asset_fields = [
            field
            for field in ("asset_id", "fallback_asset_id", "rendered_asset_id")
            if field in node
        ]
        for field in referenced_asset_fields:
            if node.get(field) not in asset_by_id:
                diagnostics.append(
                    Diagnostic("error", f"{path}.{field}", f"Unknown asset {node.get(field)!r}")
                )
        if "fallback_bounds" in node:
            fallback_asset = asset_by_id.get(node.get("fallback_asset_id"))
            if fallback_asset is not None and not bounds_fit_asset(node["fallback_bounds"], fallback_asset):
                diagnostics.append(
                    Diagnostic("error", f"{path}.fallback_bounds", "Bounds exceed asset dimensions")
                )
        if "bounds" in node and node.get("kind") == "asset_fragment":
            fragment_asset = asset_by_id.get(node.get("asset_id"))
            if fragment_asset is not None and not bounds_fit_asset(node["bounds"], fragment_asset):
                diagnostics.append(
                    Diagnostic("error", f"{path}.bounds", "Bounds exceed asset dimensions")
                )

        document_ref = node.get("document_ref")
        if document_ref is not None and referenced_documents is not None:
            referenced = referenced_documents.get(document_ref)
            if referenced is None:
                diagnostics.append(
                    Diagnostic("error", f"{path}.document_ref", f"Document {document_ref!r} was not loaded")
                )
            elif node.get("kind") == "circuit":
                if referenced.get("schema_version") != "circuit-ir/v1":
                    diagnostics.append(
                        Diagnostic("error", f"{path}.document_ref", "Referenced document is not Circuit IR")
                    )
                else:
                    if referenced.get("document_id") != document.get("document_id"):
                        diagnostics.append(
                            Diagnostic("error", f"{path}.document_ref", "Circuit document_id does not match question")
                        )
                    state_id = node.get("operating_state_id")
                    known_states = {item.get("id") for item in referenced.get("operating_states", [])}
                    if state_id is not None and state_id not in known_states:
                        diagnostics.append(
                            Diagnostic("error", f"{path}.operating_state_id", f"Unknown circuit state {state_id!r}")
                        )
                    source_hash = referenced.get("source_asset", {}).get("sha256")
                    source_hashes = {
                        item.get("sha256") for item in assets if item.get("role") == "source"
                    }
                    if source_hash not in source_hashes:
                        diagnostics.append(
                            Diagnostic(
                                "error",
                                f"{path}.document_ref",
                                "Circuit source hash does not match question assets",
                            )
                        )

    answer_key = document.get("answer_key", {})
    validate_evidence("$.answer_key", answer_key.get("evidence", []))
    for index, position in enumerate(answer_key.get("positions", [])):
        if position not in answer_positions:
            diagnostics.append(
                Diagnostic(
                    "error",
                    f"$.answer_key.positions[{index}]",
                    f"Unknown answer position {position!r}",
                )
            )

    known_targets = {
        document.get("document_id"),
        answer_key.get("id"),
        *(item.get("id") for item in answers),
        *(item.get("id") for item in hints),
        *(node.get("id") for _, node in content),
        *(item.get("id") for item in checks),
    }
    for index, review in enumerate(reviews):
        if review.get("target_ref") not in known_targets:
            diagnostics.append(
                Diagnostic(
                    "error",
                    f"$.review_events[{index}].target_ref",
                    f"Unknown review target {review.get('target_ref')!r}",
                )
            )

    if document.get("verification", {}).get("status") == "verified":
        verification = document["verification"]
        if not verification.get("reviewers"):
            diagnostics.append(
                Diagnostic(
                    "error",
                    "$.verification.reviewers",
                    "Verified question requires at least one human reviewer",
                )
            )
        if answer_key.get("status") != "verified":
            diagnostics.append(
                Diagnostic("error", "$.answer_key.status", "Verified question requires a verified answer key")
            )
        reviewable = [*answers, *hints, *(node for _, node in content)]
        for item in reviewable:
            if item.get("review_status") not in {"accepted", "corrected"}:
                diagnostics.append(
                    Diagnostic(
                        "error",
                        f"review:{item.get('id')}",
                        "Verified question contains content that was not accepted or corrected",
                    )
                )
        check_status_by_kind = {check.get("kind"): check.get("status") for check in checks}
        required_check_kinds = {"source_match", "answer_key"}
        node_kinds = {node.get("kind") for _, node in content}
        if "text" in node_kinds:
            required_check_kinds.add("text_transcription")
        if "formula" in node_kinds:
            required_check_kinds.add("formula_render")
        if "circuit" in node_kinds:
            required_check_kinds.add("circuit_topology")
        for kind in sorted(required_check_kinds):
            if check_status_by_kind.get(kind) not in {"passed", "waived"}:
                diagnostics.append(
                    Diagnostic(
                        "error",
                        "$.verification.checks",
                        f"Verified question requires a completed {kind!r} check",
                    )
                )
        for check in checks:
            if check.get("status") not in {"passed", "waived"}:
                diagnostics.append(
                    Diagnostic(
                        "error",
                        f"verification:{check.get('id')}",
                        "Verified question contains an incomplete verification check",
                    )
                )
        for path, node in content:
            if node.get("kind") == "formula" and "rendered_asset_id" not in node:
                diagnostics.append(
                    Diagnostic(
                        "error",
                        f"{path}.rendered_asset_id",
                        "Verified formula requires a preserved render-back artifact",
                    )
                )
            if node.get("kind") == "circuit" and referenced_documents is not None:
                circuit = referenced_documents.get(node.get("document_ref"))
                if circuit is not None and circuit.get("verification", {}).get("status") != "human_verified":
                    diagnostics.append(
                        Diagnostic(
                            "error",
                            f"{path}.document_ref",
                            "Verified question requires a human-verified Circuit IR",
                        )
                    )
    return diagnostics


def circuit_diagnostics(
    document: dict[str, Any], observation: dict[str, Any] | None = None
) -> list[Diagnostic]:
    components = document.get("components", [])
    pins = document.get("pins", [])
    ports = document.get("ports", [])
    nets = document.get("nets", [])
    states = document.get("operating_states", [])
    layout = document.get("layout", {})
    diagnostics = duplicate_id_diagnostics(
        (
            ("components", components),
            ("pins", pins),
            ("ports", ports),
            ("nets", nets),
            ("operating_states", states),
            ("layout.wires", layout.get("wires", [])),
            ("layout.junctions", layout.get("junctions", [])),
            ("layout.labels", layout.get("labels", [])),
        )
    )

    component_by_id = {item.get("id"): item for item in components}
    pin_by_id = {item.get("id"): item for item in pins}
    port_ids = {item.get("id") for item in ports}
    net_ids = {item.get("id") for item in nets}

    for index, component in enumerate(components):
        component_id = component.get("id")
        declared_pins = set(component.get("pin_ids", []))
        for pin_id in declared_pins:
            pin = pin_by_id.get(pin_id)
            if pin is None:
                diagnostics.append(
                    Diagnostic(
                        "error",
                        f"$.components[{index}].pin_ids",
                        f"Unknown pin {pin_id!r}",
                    )
                )
            elif pin.get("component_id") != component_id:
                diagnostics.append(
                    Diagnostic(
                        "error",
                        f"$.components[{index}].pin_ids",
                        f"Pin {pin_id!r} belongs to {pin.get('component_id')!r}",
                    )
                )

    for index, pin in enumerate(pins):
        component = component_by_id.get(pin.get("component_id"))
        if component is None:
            diagnostics.append(
                Diagnostic(
                    "error",
                    f"$.pins[{index}].component_id",
                    f"Unknown component {pin.get('component_id')!r}",
                )
            )
        elif pin.get("id") not in component.get("pin_ids", []):
            diagnostics.append(
                Diagnostic(
                    "error",
                    f"$.pins[{index}].id",
                    "Pin is not listed in its component's pin_ids",
                )
            )

    pin_nets: dict[str, str] = {}
    port_nets: dict[str, str] = {}
    for index, net in enumerate(nets):
        net_id = net.get("id")
        if not net.get("pin_ids") and not net.get("port_ids"):
            diagnostics.append(
                Diagnostic("error", f"$.nets[{index}]", "Net has no pins or ports")
            )
        for pin_index, pin_id in enumerate(net.get("pin_ids", [])):
            if pin_id not in pin_by_id:
                diagnostics.append(
                    Diagnostic(
                        "error",
                        f"$.nets[{index}].pin_ids[{pin_index}]",
                        f"Unknown pin {pin_id!r}",
                    )
                )
            elif pin_id in pin_nets:
                diagnostics.append(
                    Diagnostic(
                        "error",
                        f"$.nets[{index}].pin_ids[{pin_index}]",
                        f"Pin already belongs to net {pin_nets[pin_id]!r}",
                    )
                )
            else:
                pin_nets[pin_id] = net_id
        for port_index, port_id in enumerate(net.get("port_ids", [])):
            if port_id not in port_ids:
                diagnostics.append(
                    Diagnostic(
                        "error",
                        f"$.nets[{index}].port_ids[{port_index}]",
                        f"Unknown port {port_id!r}",
                    )
                )
            elif port_id in port_nets:
                diagnostics.append(
                    Diagnostic(
                        "error",
                        f"$.nets[{index}].port_ids[{port_index}]",
                        f"Port already belongs to net {port_nets[port_id]!r}",
                    )
                )
            else:
                port_nets[port_id] = net_id

    for pin_id in sorted(set(pin_by_id) - set(pin_nets)):
        diagnostics.append(Diagnostic("warning", "$.pins", f"Unconnected pin {pin_id!r}"))
    for port_id in sorted(port_ids - set(port_nets)):
        diagnostics.append(Diagnostic("warning", "$.ports", f"Unconnected port {port_id!r}"))

    for state_index, state in enumerate(states):
        seen_components: set[str] = set()
        for item_index, item in enumerate(state.get("component_states", [])):
            component_id = item.get("component_id")
            path = f"$.operating_states[{state_index}].component_states[{item_index}].component_id"
            if component_id not in component_by_id:
                diagnostics.append(Diagnostic("error", path, f"Unknown component {component_id!r}"))
            elif component_id in seen_components:
                diagnostics.append(Diagnostic("error", path, "Component state is declared twice"))
            seen_components.add(component_id)

    seen_symbol_components: set[str] = set()
    for index, symbol in enumerate(layout.get("symbols", [])):
        component_id = symbol.get("component_id")
        if component_id not in component_by_id:
            diagnostics.append(
                Diagnostic(
                    "error",
                    f"$.layout.symbols[{index}].component_id",
                    f"Unknown component {component_id!r}",
                )
            )
        elif component_id in seen_symbol_components:
            diagnostics.append(
                Diagnostic(
                    "error",
                    f"$.layout.symbols[{index}].component_id",
                    "Component has multiple symbol layouts",
                )
            )
        seen_symbol_components.add(component_id)
        for pin_index, pin_position in enumerate(symbol.get("pin_positions", [])):
            pin_id = pin_position.get("pin_id")
            pin = pin_by_id.get(pin_id)
            if pin is None or pin.get("component_id") != component_id:
                diagnostics.append(
                    Diagnostic(
                        "error",
                        f"$.layout.symbols[{index}].pin_positions[{pin_index}].pin_id",
                        f"Pin {pin_id!r} does not belong to symbol component",
                    )
                )

    seen_layout_ports: set[str] = set()
    for index, port_position in enumerate(layout.get("port_positions", [])):
        port_id = port_position.get("port_id")
        path = f"$.layout.port_positions[{index}].port_id"
        if port_id not in port_ids:
            diagnostics.append(Diagnostic("error", path, f"Unknown port {port_id!r}"))
        elif port_id in seen_layout_ports:
            diagnostics.append(Diagnostic("error", path, "Port has multiple layout positions"))
        seen_layout_ports.add(port_id)

    for collection in ("wires", "junctions"):
        for index, item in enumerate(layout.get(collection, [])):
            if item.get("net_id") not in net_ids:
                diagnostics.append(
                    Diagnostic(
                        "error",
                        f"$.layout.{collection}[{index}].net_id",
                        f"Unknown net {item.get('net_id')!r}",
                    )
                )

    target_sets = {
        "component": set(component_by_id),
        "net": net_ids,
        "port": port_ids,
    }
    for index, label in enumerate(layout.get("labels", [])):
        target_type = label.get("target_type")
        if label.get("target_id") not in target_sets.get(target_type, set()):
            diagnostics.append(
                Diagnostic(
                    "error",
                    f"$.layout.labels[{index}].target_id",
                    f"Unknown {target_type} target {label.get('target_id')!r}",
                )
            )

    if observation is not None:
        if observation.get("document_id") != document.get("document_id"):
            diagnostics.append(
                Diagnostic("error", "$.document_id", "Observation document_id does not match")
            )
        observation_sha = observation.get("source_asset", {}).get("sha256")
        circuit_sha = document.get("source_asset", {}).get("sha256")
        if observation_sha != circuit_sha:
            diagnostics.append(
                Diagnostic("error", "$.source_asset.sha256", "Observation source hash does not match")
            )
        observation_ids = known_observation_ids(observation) or set()
        evidenced_items = [*components, *nets, *ports]
        evidenced_items.extend(pin for pin in pins if "evidence" in pin)
        for item in evidenced_items:
            for reference in item.get("evidence", {}).get("observation_refs", []):
                if reference not in observation_ids:
                    diagnostics.append(
                        Diagnostic(
                            "error",
                            f"evidence:{item.get('id')}",
                            f"Unknown observation evidence {reference!r}",
                        )
                    )
    return diagnostics


def semantic_diagnostics(
    document: dict[str, Any],
    observation: dict[str, Any] | None = None,
    referenced_documents: dict[str, dict[str, Any]] | None = None,
) -> list[Diagnostic]:
    version = document.get("schema_version")
    if version == "observation-ir/v1":
        return observation_diagnostics(document)
    if version == "circuit-ir/v1":
        return circuit_diagnostics(document, observation)
    if version == "question-ir/v1":
        return question_diagnostics(document, referenced_documents)
    return []


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Validate Question, Observation, and Circuit IR JSON files."
    )
    parser.add_argument("documents", type=Path, nargs="+")
    parser.add_argument(
        "--schema-dir",
        type=Path,
        default=project_root / "analysis" / "schemas",
    )
    args = parser.parse_args()

    loaded: list[tuple[Path, dict[str, Any]]] = []
    failed_to_load = False
    for path in args.documents:
        try:
            loaded.append((path, load_json(path)))
        except (OSError, ValueError, json.JSONDecodeError) as error:
            print(f"ERROR {path}: {error}")
            failed_to_load = True

    observations = {
        document.get("document_id"): document
        for _, document in loaded
        if document.get("schema_version") == "observation-ir/v1"
    }
    referenced_documents: dict[str, dict[str, Any]] = {}
    for path, document in loaded:
        referenced_documents[str(path)] = document
        referenced_documents[path.as_posix()] = document
        try:
            referenced_documents[path.resolve().relative_to(project_root).as_posix()] = document
        except ValueError:
            pass
    error_count = int(failed_to_load)
    warning_count = 0
    for path, document in loaded:
        diagnostics = schema_diagnostics(document, args.schema_dir)
        if not diagnostics:
            observation = observations.get(document.get("document_id"))
            diagnostics.extend(
                semantic_diagnostics(document, observation, referenced_documents)
            )
        for diagnostic in diagnostics:
            print(f"{diagnostic.level.upper()} {path}:{diagnostic.path}: {diagnostic.message}")
            if diagnostic.level == "error":
                error_count += 1
            else:
                warning_count += 1
        if not diagnostics:
            print(f"OK {path}")

    print(f"Validation complete: {error_count} error(s), {warning_count} warning(s).")
    raise SystemExit(1 if error_count else 0)


if __name__ == "__main__":
    main()
