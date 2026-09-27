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
    document: dict[str, Any], observation: dict[str, Any] | None = None
) -> list[Diagnostic]:
    version = document.get("schema_version")
    if version == "observation-ir/v1":
        return observation_diagnostics(document)
    if version == "circuit-ir/v1":
        return circuit_diagnostics(document, observation)
    return []


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Validate Observation IR and Circuit IR JSON files.")
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
    error_count = int(failed_to_load)
    warning_count = 0
    for path, document in loaded:
        diagnostics = schema_diagnostics(document, args.schema_dir)
        if not diagnostics:
            observation = observations.get(document.get("document_id"))
            diagnostics.extend(semantic_diagnostics(document, observation))
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
