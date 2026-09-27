#!/usr/bin/env python3
"""Render Circuit IR geometry over its immutable source image for human review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageOps


NET_COLORS = (
    (0, 102, 255, 190),
    (0, 155, 105, 190),
    (190, 65, 0, 190),
    (125, 60, 190, 190),
    (195, 0, 105, 190),
    (0, 145, 175, 190),
)


def find_source_image(image_root: Path, uri: str) -> Path:
    uri_path = Path(uri)
    candidates = (image_root / uri_path, image_root / uri_path.name)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Cannot resolve source image {uri!r} below {image_root}")


def load_document(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != "circuit-ir/v1":
        raise ValueError("Overlay renderer requires circuit-ir/v1")
    if document.get("layout", {}).get("coordinate_unit") != "pixel":
        raise ValueError("Overlay renderer currently requires pixel coordinates")
    return document


def point(value: dict[str, Any]) -> tuple[float, float]:
    return float(value["x"]), float(value["y"])


def render_overlay(
    document: dict[str, Any], source_path: Path, output_path: Path
) -> None:
    with Image.open(source_path) as source:
        image = ImageOps.exif_transpose(source).convert("RGBA")

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    layout = document["layout"]
    net_ids = sorted(net["id"] for net in document["nets"])
    net_colors = {
        net_id: NET_COLORS[index % len(NET_COLORS)]
        for index, net_id in enumerate(net_ids)
    }

    for wire in layout["wires"]:
        draw.line(
            [point(item) for item in wire["points"]],
            fill=net_colors[wire["net_id"]],
            width=3,
            joint="curve",
        )

    for symbol in layout["symbols"]:
        bounds = symbol["bounds"]
        rectangle = (
            bounds["x"],
            bounds["y"],
            bounds["x"] + bounds["width"],
            bounds["y"] + bounds["height"],
        )
        draw.rectangle(rectangle, outline=(230, 30, 30, 230), width=2)
        for pin_position in symbol["pin_positions"]:
            x, y = point(pin_position["position"])
            draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(230, 30, 30, 230))

    for port_position in layout["port_positions"]:
        x, y = point(port_position["position"])
        draw.ellipse(
            (x - 4, y - 4, x + 4, y + 4),
            outline=(155, 0, 210, 255),
            width=2,
        )

    for junction in layout["junctions"]:
        x, y = point(junction["position"])
        color = net_colors[junction["net_id"]]
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=color, outline=(0, 115, 0, 255), width=2)

    result = Image.alpha_composite(image, overlay).convert("RGB")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path, format="PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a Circuit IR review overlay.")
    parser.add_argument("circuit", type=Path)
    parser.add_argument("--image-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    document = load_document(args.circuit)
    source_path = find_source_image(args.image_root, document["source_asset"]["uri"])
    render_overlay(document, source_path, args.output)
    print(f"Rendered {args.output}")


if __name__ == "__main__":
    main()
