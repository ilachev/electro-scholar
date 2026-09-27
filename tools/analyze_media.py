#!/usr/bin/env python3
"""Build a reproducible inventory and a diverse review pilot for question images."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sqlite3
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageOps, __version__ as pillow_version


INVENTORY_VERSION = 1
FEATURE_NAMES = (
    "log_area",
    "log_aspect_ratio",
    "grayscale_mean",
    "grayscale_stddev",
    "grayscale_entropy",
    "foreground_fraction",
    "dark_fraction",
    "edge_density",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_path(image_root: Path, database_value: str) -> Path:
    direct = image_root / database_value
    if direct.is_file():
        return direct
    return image_root / Path(database_value).name


def histogram_moments(histogram: list[int], total: int) -> tuple[float, float, float]:
    mean = sum(value * count for value, count in enumerate(histogram)) / total
    variance = sum(((value - mean) ** 2) * count for value, count in enumerate(histogram)) / total
    entropy = -sum(
        (count / total) * math.log2(count / total)
        for count in histogram
        if count
    )
    return mean, math.sqrt(variance), entropy


def edge_density(grayscale: Image.Image) -> float:
    reduced = grayscale.copy()
    reduced.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
    edges = reduced.filter(ImageFilter.FIND_EDGES)
    if edges.width > 2 and edges.height > 2:
        edges = edges.crop((1, 1, edges.width - 1, edges.height - 1))
    histogram = edges.histogram()
    total = edges.width * edges.height
    return sum(histogram[33:]) / total if total else 0.0


def ink_bounds(grayscale: Image.Image) -> dict[str, int] | None:
    foreground = grayscale.point(lambda value: 255 if value < 245 else 0)
    bounds = foreground.getbbox()
    if bounds is None:
        return None
    left, top, right, bottom = bounds
    return {
        "x": left,
        "y": top,
        "width": right - left,
        "height": bottom - top,
    }


def analyze_image(path: Path) -> dict[str, Any]:
    with Image.open(path) as source:
        image_format = source.format
        image = ImageOps.exif_transpose(source)
        width, height = image.size
        mode = image.mode
        grayscale = image.convert("L")
        histogram = grayscale.histogram()

    total = width * height
    mean, stddev, entropy = histogram_moments(histogram, total)
    foreground_count = sum(histogram[:245])
    dark_count = sum(histogram[:65])
    aspect_ratio = width / height

    return {
        "sha256": sha256_file(path),
        "file_bytes": path.stat().st_size,
        "format": image_format,
        "mime_type": "image/jpeg" if image_format == "JPEG" else f"image/{image_format.lower()}",
        "mode": mode,
        "width": width,
        "height": height,
        "aspect_ratio": round(aspect_ratio, 6),
        "orientation": (
            "landscape" if aspect_ratio > 1.05 else "portrait" if aspect_ratio < 0.95 else "square"
        ),
        "ink_bounds": ink_bounds(grayscale),
        "features": {
            "log_area": round(math.log(max(total, 1)), 6),
            "log_aspect_ratio": round(math.log(max(aspect_ratio, 1e-12)), 6),
            "grayscale_mean": round(mean, 6),
            "grayscale_stddev": round(stddev, 6),
            "grayscale_entropy": round(entropy, 6),
            "foreground_fraction": round(foreground_count / total, 6),
            "dark_fraction": round(dark_count / total, 6),
            "edge_density": round(edge_density(grayscale), 6),
        },
    }


def load_questions(database_path: Path) -> list[dict[str, Any]]:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT
                q.id AS question_id,
                s.file_name AS source_file,
                q.source_index,
                q.question_number,
                q.image_file,
                q.extraction_warnings,
                t.position AS topic_position,
                t.name AS topic_name
            FROM questions q
            JOIN sources s ON s.id = q.source_id
            LEFT JOIN topics t ON t.id = q.topic_id
            ORDER BY s.id, q.source_index
            """
        ).fetchall()
    finally:
        connection.close()
    return [dict(row) for row in rows]


def stable_document_id(question: dict[str, Any]) -> str:
    source = Path(question["source_file"]).stem.lower()
    return f"legacy-test:{source}:{question['source_index']:03d}"


def build_inventory(database_path: Path, image_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    missing: list[str] = []
    for question in load_questions(database_path):
        if not question["image_file"]:
            missing.append(stable_document_id(question))
            continue
        path = image_path(image_root, question["image_file"])
        if not path.is_file():
            missing.append(str(path))
            continue
        media = analyze_image(path)
        topic_key = f"{question['source_file']}:{question['topic_position']}"
        records.append(
            {
                "document_id": stable_document_id(question),
                "question_id": question["question_id"],
                "source_file": question["source_file"],
                "source_index": question["source_index"],
                "question_number": question["question_number"],
                "topic_key": topic_key,
                "topic_position": question["topic_position"],
                "topic_name": question["topic_name"],
                "extraction_warnings": [
                    warning
                    for warning in question["extraction_warnings"].split(",")
                    if warning
                ],
                "image_path": question["image_file"],
                "asset_id": f"sha256:{media['sha256']}",
                **media,
            }
        )

    if missing:
        preview = ", ".join(missing[:5])
        raise FileNotFoundError(f"Missing {len(missing)} question images: {preview}")
    return records


def standardized_feature_vectors(records: list[dict[str, Any]]) -> dict[str, tuple[float, ...]]:
    columns = {
        name: [float(record["features"][name]) for record in records]
        for name in FEATURE_NAMES
    }
    centers = {name: statistics.fmean(values) for name, values in columns.items()}
    scales = {
        name: statistics.pstdev(values) or 1.0
        for name, values in columns.items()
    }
    return {
        record["document_id"]: tuple(
            (float(record["features"][name]) - centers[name]) / scales[name]
            for name in FEATURE_NAMES
        )
        for record in records
    }


def squared_distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sum((a - b) ** 2 for a, b in zip(left, right))


def select_diverse_pilot(
    records: list[dict[str, Any]], per_topic: int
) -> list[dict[str, Any]]:
    vectors = standardized_feature_vectors(records)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[record["topic_key"]].append(record)

    selected: list[dict[str, Any]] = []
    for topic_key in sorted(groups):
        candidates = sorted(groups[topic_key], key=lambda item: item["document_id"])
        count = min(per_topic, len(candidates))
        centroid = tuple(
            statistics.fmean(vectors[item["document_id"]][index] for item in candidates)
            for index in range(len(FEATURE_NAMES))
        )
        first = min(
            candidates,
            key=lambda item: (
                squared_distance(vectors[item["document_id"]], centroid),
                item["document_id"],
            ),
        )
        chosen = [first]
        remaining = [item for item in candidates if item is not first]
        while len(chosen) < count:
            next_item = max(
                remaining,
                key=lambda item: (
                    min(
                        squared_distance(
                            vectors[item["document_id"]], vectors[pick["document_id"]]
                        )
                        for pick in chosen
                    ),
                    item["document_id"],
                ),
            )
            chosen.append(next_item)
            remaining.remove(next_item)

        for rank, record in enumerate(chosen, start=1):
            selected.append(
                {
                    "document_id": record["document_id"],
                    "asset_id": record["asset_id"],
                    "question_id": record["question_id"],
                    "source_file": record["source_file"],
                    "source_index": record["source_index"],
                    "question_number": record["question_number"],
                    "topic_key": topic_key,
                    "topic_name": record["topic_name"],
                    "image_path": record["image_path"],
                    "selection_rank_in_topic": rank,
                    "selection_reason": (
                        "nearest-to-topic-centroid" if rank == 1 else "max-min-feature-diversity"
                    ),
                }
            )
    return selected


def duplicate_groups(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_hash: dict[str, list[str]] = defaultdict(list)
    for record in records:
        by_hash[record["sha256"]].append(record["document_id"])
    return [
        {"sha256": digest, "document_ids": sorted(document_ids)}
        for digest, document_ids in sorted(by_hash.items())
        if len(document_ids) > 1
    ]


def summary(records: list[dict[str, Any]], pilot: list[dict[str, Any]]) -> dict[str, Any]:
    dimensions = Counter((record["width"], record["height"]) for record in records)
    sources = Counter(record["source_file"] for record in records)
    topics = Counter(record["topic_key"] for record in records)
    return {
        "inventory_version": INVENTORY_VERSION,
        "pillow_version": pillow_version,
        "asset_count": len(records),
        "unique_sha256_count": len({record["sha256"] for record in records}),
        "duplicate_groups": duplicate_groups(records),
        "pilot_count": len(pilot),
        "source_counts": dict(sorted(sources.items())),
        "topic_counts": dict(sorted(topics.items())),
        "dimension_counts": [
            {"width": width, "height": height, "count": count}
            for (width, height), count in sorted(
                dimensions.items(), key=lambda item: (-item[1], item[0])
            )
        ],
        "feature_ranges": {
            name: {
                "min": min(float(record["features"][name]) for record in records),
                "max": max(float(record["features"][name]) for record in records),
            }
            for name in FEATURE_NAMES
        },
    }


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def write_inventory_csv(path: Path, records: list[dict[str, Any]]) -> None:
    fieldnames = [
        "document_id",
        "asset_id",
        "question_id",
        "source_file",
        "source_index",
        "question_number",
        "topic_key",
        "topic_name",
        "image_path",
        "sha256",
        "file_bytes",
        "width",
        "height",
        "aspect_ratio",
        "orientation",
        *FEATURE_NAMES,
        "extraction_warnings",
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    **{name: record.get(name, "") for name in fieldnames},
                    **record["features"],
                    "extraction_warnings": ",".join(record["extraction_warnings"]),
                }
            )


def write_summary_markdown(path: Path, data: dict[str, Any]) -> None:
    dimension_lines = "\n".join(
        f"| {item['width']} x {item['height']} | {item['count']} |"
        for item in data["dimension_counts"][:12]
    )
    topic_lines = "\n".join(
        f"| {topic} | {count} |"
        for topic, count in data["topic_counts"].items()
    )
    text = f"""# Инвентаризация изображений

- Изображений: {data['asset_count']}
- Уникальных SHA-256: {data['unique_sha256_count']}
- Групп полных дубликатов: {len(data['duplicate_groups'])}
- Изображений в пилоте: {data['pilot_count']}

Семантическая классификация намеренно не выполняется эвристиками. Типы
`text`, `formula`, `circuit`, `plot`, `table` и `illustration` фиксируются
человеком в отдельных документах `Observation IR`; повторная генерация
инвентаря не перезаписывает ручную разметку.

## Темы

| Ключ темы | Изображений |
|---|---:|
{topic_lines}

## Частые размеры

| Размер | Изображений |
|---|---:|
{dimension_lines}
"""
    path.write_text(text, encoding="utf-8")


def write_pilot_contact_sheet(
    path: Path,
    pilot: list[dict[str, Any]],
    records: list[dict[str, Any]],
    image_root: Path,
) -> None:
    columns = 5
    cell_width = 260
    preview_height = 164
    label_height = 32
    rows = math.ceil(len(pilot) / columns)
    sheet = Image.new("RGB", (columns * cell_width, rows * (preview_height + label_height)), "white")
    draw = ImageDraw.Draw(sheet)
    records_by_id = {record["document_id"]: record for record in records}

    for index, item in enumerate(pilot):
        column = index % columns
        row = index // columns
        origin_x = column * cell_width
        origin_y = row * (preview_height + label_height)
        record = records_by_id[item["document_id"]]
        source_path = image_path(image_root, record["image_path"])
        with Image.open(source_path) as source:
            preview = ImageOps.contain(
                ImageOps.exif_transpose(source).convert("RGB"),
                (cell_width - 12, preview_height - 12),
                Image.Resampling.LANCZOS,
            )
        image_x = origin_x + (cell_width - preview.width) // 2
        image_y = origin_y + (preview_height - preview.height) // 2
        sheet.paste(preview, (image_x, image_y))
        draw.rectangle(
            (origin_x, origin_y, origin_x + cell_width - 1, origin_y + preview_height + label_height - 1),
            outline="#b8b8b8",
        )
        draw.text(
            (origin_x + 6, origin_y + preview_height + 3),
            item["document_id"],
            fill="black",
        )
        draw.text(
            (origin_x + 6, origin_y + preview_height + 17),
            item["topic_key"],
            fill="#444444",
        )
    sheet.save(path, format="JPEG", quality=90, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inventory question images and select a reproducible review pilot."
    )
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--image-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pilot-per-topic", type=int, default=5)
    args = parser.parse_args()

    if args.pilot_per_topic < 1:
        parser.error("--pilot-per-topic must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    records = build_inventory(args.database, args.image_root)
    pilot = select_diverse_pilot(records, args.pilot_per_topic)
    report = summary(records, pilot)
    report["database_sha256"] = sha256_file(args.database)

    write_json(
        args.output_dir / "inventory.json",
        {
            "inventory_version": INVENTORY_VERSION,
            "database_sha256": report["database_sha256"],
            "assets": records,
        },
    )
    write_inventory_csv(args.output_dir / "inventory.csv", records)
    write_json(
        args.output_dir / "pilot-50.json",
        {
            "selection_version": 1,
            "method": "topic centroid plus greedy max-min over standardized visual features",
            "feature_names": list(FEATURE_NAMES),
            "items": pilot,
        },
    )
    write_json(args.output_dir / "summary.json", report)
    write_summary_markdown(args.output_dir / "SUMMARY.md", report)
    write_pilot_contact_sheet(
        args.output_dir / "pilot-contact-sheet.jpg", pilot, records, args.image_root
    )
    print(
        f"Analyzed {len(records)} images; selected {len(pilot)} pilot items "
        f"across {len(report['topic_counts'])} topics."
    )


if __name__ == "__main__":
    main()
