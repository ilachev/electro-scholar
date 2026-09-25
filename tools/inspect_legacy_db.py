#!/usr/bin/env python3
import argparse
import csv
import json
import math
import re
import sqlite3
import struct
from collections import Counter
from pathlib import Path


LEGACY_FILES = [
    "TEST.CFG",
    "TEST1.DAT",
    "TEST2.DAT",
    "STAT/TEST.DAT",
]

INDEX_RECORD_SIZE = 89
INDEX_FIXED_FORMAT = "<II8I4I"
TOPIC_RECORD_SIZE = 40


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    total = len(data)
    counts = Counter(data)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def printable_preview(data: bytes, limit: int = 80) -> str:
    view = data[:limit]
    return "".join(chr(byte) if 32 <= byte <= 126 else "." for byte in view)


def hex_preview(data: bytes, limit: int = 32) -> str:
    return " ".join(f"{byte:02x}" for byte in data[:limit])


def decode_cp1251(decoded: bytes) -> str:
    text = decoded.decode("cp1251", errors="replace")
    replacements = {
        "\x00": " ",
        "\x0c": ",",
        "\x0e": ".",
        "\x1a": " ",
        "\x1d": "=",
        "\x11": "1",
        "\x12": "2",
        "\x13": "3",
        "\x14": "4",
        "\x15": "5",
        "\x16": "6",
        "\x17": "7",
        "\x18": "8",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return " ".join(text.replace("-*", " ").split())


def decode_xor_cp1251(chunk: bytes) -> str:
    if not chunk:
        return ""
    key = chunk[0]
    return decode_cp1251(bytes(byte ^ key for byte in chunk))


def decode_encrypted_pascal(chunk: bytes) -> str:
    if not chunk:
        return ""
    length = chunk[0]
    encoded = chunk[1 : 1 + length]
    if not encoded:
        return ""
    key = encoded[0]
    decoded = bytes(byte ^ key for byte in encoded).lstrip(b"\x00")
    return decoded.decode("cp1251", errors="replace").strip()


def parse_pointer_table(data: bytes, max_entries: int = 32) -> list[tuple[int, int, bool]]:
    entries = []
    file_size = len(data)
    for offset in range(0, min(len(data), max_entries * 8), 8):
        if offset + 8 > len(data):
            break
        block_offset, block_size = struct.unpack_from("<II", data, offset)
        valid = (
            block_offset != 0
            and block_size != 0
            and block_offset < file_size
            and block_offset + block_size <= file_size
        )
        entries.append((block_offset, block_size, valid))
    return entries


def parse_topics(data: bytes, entries: list[tuple[int, int, bool]]) -> list[dict[str, object]]:
    if len(entries) < 2 or not entries[1][2]:
        return []
    offset, size, _ = entries[1]
    if size % TOPIC_RECORD_SIZE != 0:
        return []

    topics = []
    for position in range(size // TOPIC_RECORD_SIZE):
        record = data[
            offset + position * TOPIC_RECORD_SIZE : offset + (position + 1) * TOPIC_RECORD_SIZE
        ]
        start_index, question_count = struct.unpack_from("<II", record)
        topics.append(
            {
                "position": position + 1,
                "start_index": start_index,
                "question_count": question_count,
                "name": decode_encrypted_pascal(record[8:]),
            }
        )
    return topics


def decoded_index_records(data: bytes, index_offset: int, index_size: int) -> list[dict[str, object]]:
    if index_size % INDEX_RECORD_SIZE != 0:
        return []

    index = data[index_offset : index_offset + index_size]
    record_count = index_size // INDEX_RECORD_SIZE
    rows = []
    for record_index in range(record_count):
        record = index[
            record_index * INDEX_RECORD_SIZE : (record_index + 1) * INDEX_RECORD_SIZE
        ]
        text_offset, text_size = struct.unpack_from("<II", record, 0)
        if not (0 < text_offset < len(data) and 0 < text_size < 1_000_000):
            continue
        if text_offset + text_size > len(data):
            continue

        rows.append(
            {
                "record_index": record_index,
                "text_offset": text_offset,
                "text_size": text_size,
                "text": decode_xor_cp1251(data[text_offset : text_offset + text_size]),
            }
        )
    return rows


def parse_database_records(
    data: bytes, index_offset: int, index_size: int
) -> list[dict[str, object]]:
    if index_size % INDEX_RECORD_SIZE != 0:
        return []

    records = []
    index = data[index_offset : index_offset + index_size]
    for record_index in range(index_size // INDEX_RECORD_SIZE):
        record = index[
            record_index * INDEX_RECORD_SIZE : (record_index + 1) * INDEX_RECORD_SIZE
        ]
        (
            question_offset,
            question_size,
            *fixed_values,
        ) = struct.unpack_from(INDEX_FIXED_FORMAT, record, 0)
        answer_sizes = fixed_values[:8]
        hint_1_size, hint_2_size, image_size, _packed_metadata = fixed_values[8:]
        correct_answer_mask = record[52]
        legacy_sequence = struct.unpack_from("<I", record, 53)[0]
        question_label = decode_encrypted_pascal(record[57:])
        number_match = re.search(r"\d+", question_label)
        question_number = int(number_match.group()) if number_match else record_index + 1

        payload_offset = question_offset + question_size
        payload_size = sum(answer_sizes) + hint_1_size + hint_2_size + image_size
        if not (
            0 < question_offset < len(data)
            and 0 < question_size < 1_000_000
            and question_offset + question_size <= len(data)
            and payload_size > 0
            and payload_offset + payload_size <= len(data)
        ):
            continue

        payload = data[payload_offset : payload_offset + payload_size]
        payload_key = payload[0] ^ 0x11
        decoded_payload = bytes(byte ^ payload_key for byte in payload)

        cursor = 0
        answers = []
        answer_markers_valid = True
        for answer_index, answer_size in enumerate(answer_sizes):
            if answer_size == 0:
                answers.append("")
                continue
            answer = decoded_payload[cursor : cursor + answer_size]
            cursor += answer_size
            expected_marker = 0x11 + answer_index
            answer_markers_valid &= bool(answer) and answer[0] == expected_marker
            answers.append(decode_cp1251(answer[1:]).strip())

        hint_1 = decoded_payload[cursor : cursor + hint_1_size]
        cursor += hint_1_size
        hint_2 = decoded_payload[cursor : cursor + hint_2_size]
        cursor += hint_2_size
        packed_image = decoded_payload[cursor : cursor + image_size]
        image = bytes(byte ^ 0x20 for byte in packed_image)
        image_end = image.rfind(b"\xff\xd9")
        image_valid = image.startswith(b"\xff\xd8\xff") and image_end >= 0
        if image_valid:
            image = image[: image_end + 2]

        records.append(
            {
                "record_index": record_index,
                "question_offset": question_offset,
                "question_size": question_size,
                "question": decode_xor_cp1251(
                    data[question_offset : question_offset + question_size]
                ),
                "answer_sizes": list(answer_sizes),
                "answers": answers,
                "hint_1_size": hint_1_size,
                "hint_1": decode_cp1251(hint_1).strip(),
                "hint_2_size": hint_2_size,
                "hint_2": decode_cp1251(hint_2).strip(),
                "image_size": image_size,
                "image": image,
                "image_valid": image_valid,
                "answer_markers_valid": answer_markers_valid,
                "correct_answer_mask": correct_answer_mask,
                "correct_answers": [
                    answer_index + 1
                    for answer_index in range(8)
                    if correct_answer_mask & (1 << answer_index)
                ],
                "legacy_sequence": legacy_sequence,
                "question_label": question_label,
                "question_number": question_number,
            }
        )
    return records


def assign_topics(records: list[dict[str, object]], topics: list[dict[str, object]]) -> None:
    for topic in topics:
        start = int(topic["start_index"])
        end = start + int(topic["question_count"])
        for record in records[start:end]:
            record["topic_position"] = topic["position"]
            record["topic"] = topic["name"]

    for record in records:
        record.setdefault("topic_position", None)
        record.setdefault("topic", "")
        warnings = []
        answer_count = sum(int(size) > 0 for size in record["answer_sizes"])
        mask = int(record["correct_answer_mask"])
        if mask == 0:
            warnings.append("missing_correct_answer")
        if mask >> answer_count:
            warnings.append("correct_answer_out_of_range")
        if not record["answer_markers_valid"]:
            warnings.append("invalid_answer_marker")
        if record["question_number"] != int(record["record_index"]) + 1:
            warnings.append("question_number_mismatch")
        record["warnings"] = warnings


def inspect_index_records(data: bytes, index_offset: int, index_size: int, record_limit: int) -> None:
    rows = decoded_index_records(data, index_offset, index_size)
    if not rows:
        return

    print(f"decoded index records: {len(rows)} records of {INDEX_RECORD_SIZE} bytes")
    shown = 0
    for row in rows:
        print(
            f"  #{row['record_index']:03d}: text_offset=0x{row['text_offset']:08x}, "
            f"size={row['text_size']:>4}, text={str(row['text'])[:160]}"
        )
        shown += 1
        if shown >= record_limit:
            break


def inspect_file(path: Path, record_limit: int) -> list[dict[str, object]]:
    data = path.read_bytes()
    print(f"\n== {path} ==")
    print(f"size: {len(data):,} bytes")
    print(f"entropy: {entropy(data):.3f} bits/byte")
    print(f"head hex: {hex_preview(data)}")
    print(f"head ascii: {printable_preview(data)}")

    entries = parse_pointer_table(data)
    valid_entries = [(i, offset, size) for i, (offset, size, valid) in enumerate(entries) if valid]
    decoded_rows = []
    if valid_entries:
        print("possible <offset,size> table at file start:")
        for index, offset, size in valid_entries[:16]:
            block = data[offset : offset + min(size, 64)]
            print(
                f"  #{index:02d}: offset=0x{offset:08x} ({offset:,}), "
                f"size={size:,}, entropy={entropy(block):.3f}, "
                f"hex={hex_preview(block, 16)}, ascii={printable_preview(block, 48)}"
            )
        first_offset, first_size = valid_entries[0][1], valid_entries[0][2]
        inspect_index_records(data, first_offset, first_size, record_limit)
        decoded_rows = decoded_index_records(data, first_offset, first_size)
    else:
        print("possible <offset,size> table at file start: not detected")
    for row in decoded_rows:
        row["source_file"] = str(path)
    return decoded_rows


def export_records(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["source_file", "record_index", "text_offset", "text_size", "text"],
            dialect="excel-tab",
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nexported decoded records: {path} ({len(rows)} rows)")


def export_sqlite(
    database_path: Path,
    databases: list[tuple[Path, list[dict[str, object]], list[dict[str, object]]]],
) -> None:
    if database_path.exists():
        database_path.unlink()
    connection = sqlite3.connect(database_path)
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE sources (
            id INTEGER PRIMARY KEY,
            file_name TEXT NOT NULL UNIQUE,
            question_count INTEGER NOT NULL
        );

        CREATE TABLE topics (
            id INTEGER PRIMARY KEY,
            source_id INTEGER NOT NULL REFERENCES sources(id),
            position INTEGER NOT NULL,
            start_index INTEGER NOT NULL,
            question_count INTEGER NOT NULL,
            name TEXT NOT NULL,
            UNIQUE(source_id, position)
        );

        CREATE TABLE questions (
            id INTEGER PRIMARY KEY,
            source_id INTEGER NOT NULL REFERENCES sources(id),
            topic_id INTEGER REFERENCES topics(id),
            source_index INTEGER NOT NULL,
            question_number INTEGER NOT NULL,
            question_label TEXT NOT NULL,
            legacy_sequence INTEGER NOT NULL,
            text TEXT NOT NULL,
            hint_1 TEXT NOT NULL,
            hint_2 TEXT NOT NULL,
            image_file TEXT,
            correct_answer_mask INTEGER NOT NULL,
            extraction_warnings TEXT NOT NULL,
            UNIQUE(source_id, source_index)
        );

        CREATE TABLE answers (
            id INTEGER PRIMARY KEY,
            question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
            position INTEGER NOT NULL,
            text TEXT NOT NULL,
            is_correct INTEGER NOT NULL CHECK(is_correct IN (0, 1)),
            UNIQUE(question_id, position)
        );

        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE INDEX questions_topic_idx ON questions(topic_id, source_index);
        CREATE INDEX answers_question_idx ON answers(question_id, position);

        CREATE VIEW question_catalog AS
        SELECT
            q.id,
            s.file_name AS source_file,
            t.name AS topic,
            q.question_number,
            q.text AS question,
            q.image_file,
            q.correct_answer_mask,
            q.extraction_warnings
        FROM questions q
        JOIN sources s ON s.id = q.source_id
        LEFT JOIN topics t ON t.id = q.topic_id;

        CREATE VIEW answer_catalog AS
        SELECT
            q.id AS question_id,
            s.file_name AS source_file,
            t.name AS topic,
            q.question_number,
            a.position AS answer_position,
            a.text AS answer,
            a.is_correct
        FROM answers a
        JOIN questions q ON q.id = a.question_id
        JOIN sources s ON s.id = q.source_id
        LEFT JOIN topics t ON t.id = q.topic_id;
        """
    )
    connection.executemany(
        "INSERT INTO metadata(key, value) VALUES (?, ?)",
        [
            ("format", "Legacy TEST database export"),
            ("schema_version", "1"),
            ("text_encoding", "UTF-8 (converted from Windows-1251)"),
        ],
    )

    for source_path, records, topics in databases:
        cursor = connection.execute(
            "INSERT INTO sources(file_name, question_count) VALUES (?, ?)",
            (source_path.name, len(records)),
        )
        source_id = cursor.lastrowid
        topic_ids = {}
        for topic in topics:
            cursor = connection.execute(
                """
                INSERT INTO topics(source_id, position, start_index, question_count, name)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    topic["position"],
                    topic["start_index"],
                    topic["question_count"],
                    topic["name"],
                ),
            )
            topic_ids[topic["position"]] = cursor.lastrowid

        for record in records:
            image_file = record.get("image_file") or None
            cursor = connection.execute(
                """
                INSERT INTO questions(
                    source_id, topic_id, source_index, question_number, question_label,
                    legacy_sequence, text, hint_1, hint_2, image_file,
                    correct_answer_mask, extraction_warnings
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    topic_ids.get(record["topic_position"]),
                    record["record_index"],
                    record["question_number"],
                    record["question_label"],
                    record["legacy_sequence"],
                    record["question"],
                    record["hint_1"],
                    record["hint_2"],
                    image_file,
                    record["correct_answer_mask"],
                    ",".join(record["warnings"]),
                ),
            )
            question_id = cursor.lastrowid
            connection.executemany(
                """
                INSERT INTO answers(question_id, position, text, is_correct)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        question_id,
                        position,
                        answer,
                        int(bool(record["correct_answer_mask"] & (1 << (position - 1)))),
                    )
                    for position, (answer, answer_size) in enumerate(
                        zip(record["answers"], record["answer_sizes"]), start=1
                    )
                    if answer_size
                ],
            )

    connection.commit()
    connection.close()


def export_database(
    export_dir: Path,
    databases: list[tuple[Path, list[dict[str, object]], list[dict[str, object]]]],
) -> None:
    export_dir.mkdir(parents=True, exist_ok=True)
    image_dir = export_dir / "images"
    image_dir.mkdir(exist_ok=True)
    rows = []
    json_rows = []

    topics_rows = []
    for source_path, records, topics in databases:
        source_name = source_path.name
        source_stem = source_path.stem
        topics_rows.extend({"source_file": source_name, **topic} for topic in topics)
        for record in records:
            image_name = f"{source_stem}_{record['record_index']:03d}.jpg"
            image_path = image_dir / image_name
            if record["image_valid"]:
                image_path.write_bytes(record["image"])

            row = {
                "source_file": source_name,
                "record_index": record["record_index"],
                "question_number": record["question_number"],
                "question_label": record["question_label"],
                "legacy_sequence": record["legacy_sequence"],
                "topic": record["topic"],
                "question": record["question"],
                **{
                    f"answer_{index + 1}": answer
                    for index, answer in enumerate(record["answers"])
                },
                "hint_1": record["hint_1"],
                "hint_2": record["hint_2"],
                "correct_answer_mask": record["correct_answer_mask"],
                "correct_answers": ",".join(map(str, record["correct_answers"])),
                "warnings": ",".join(record["warnings"]),
                "image_file": f"images/{image_name}" if record["image_valid"] else "",
            }
            record["image_file"] = row["image_file"]
            rows.append(row)

            json_record = {key: value for key, value in record.items() if key != "image"}
            json_record["source_file"] = source_name
            json_record["image_file"] = row["image_file"]
            json_rows.append(json_record)

    tsv_path = export_dir / "questions.tsv"
    fieldnames = [
        "source_file",
        "record_index",
        "question_number",
        "question_label",
        "legacy_sequence",
        "topic",
        "question",
        *[f"answer_{index}" for index in range(1, 9)],
        "hint_1",
        "hint_2",
        "correct_answer_mask",
        "correct_answers",
        "warnings",
        "image_file",
    ]
    with tsv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, dialect="excel-tab")
        writer.writeheader()
        writer.writerows(rows)

    json_path = export_dir / "questions.json"
    json_path.write_text(
        json.dumps(json_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    topics_path = export_dir / "topics.json"
    topics_path.write_text(
        json.dumps(topics_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    sqlite_path = export_dir / "toe.sqlite"
    export_sqlite(sqlite_path, databases)
    print(
        f"\nexported database: {tsv_path}, {json_path}, {topics_path}, and {sqlite_path} "
        f"({len(rows)} questions, {sum(bool(row['image_file']) for row in rows)} images)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect legacy TEST database files without modifying them.")
    parser.add_argument("legacy_dir", type=Path, help="Path to extracted TEST program directory")
    parser.add_argument(
        "--record-limit",
        type=int,
        default=12,
        help="How many decoded index records to print for each database file.",
    )
    parser.add_argument(
        "--export-records",
        type=Path,
        help="Optional TSV path for all decoded index records.",
    )
    parser.add_argument(
        "--export-database",
        type=Path,
        help="Optional directory for full question, answer, hint, and image export.",
    )
    args = parser.parse_args()

    all_rows = []
    databases = []
    for relative in LEGACY_FILES:
        path = args.legacy_dir / relative
        if path.exists():
            all_rows.extend(inspect_file(path, args.record_limit))
            if path.suffix.upper() == ".DAT" and path.parent == args.legacy_dir:
                data = path.read_bytes()
                entries = parse_pointer_table(data)
                if entries and entries[0][2]:
                    records = parse_database_records(data, entries[0][0], entries[0][1])
                    if records:
                        topics = parse_topics(data, entries)
                        assign_topics(records, topics)
                        databases.append((path, records, topics))
        else:
            print(f"\n== {path} ==\nmissing")

    if args.export_records:
        export_records(args.export_records, all_rows)
    if args.export_database:
        export_database(args.export_database, databases)


if __name__ == "__main__":
    main()
