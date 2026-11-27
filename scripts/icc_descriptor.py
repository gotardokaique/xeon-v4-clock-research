#!/usr/bin/env python3
"""Read the ICC initialization list declared by an Intel Flash Descriptor.

This is a read-only parser. It reports raw 32-bit selector/value pairs and
candidate byte slices without assigning undocumented selector semantics.
"""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path
from typing import Any

DESCRIPTOR_SIGNATURE = bytes.fromhex("5aa5f00f")
FLMAP2_RELATIVE = 0x1C
MAX_DESCRIPTOR_SEARCH = 0x1000


class DescriptorError(ValueError):
    pass


def find_descriptor(data: bytes) -> int:
    """Return the descriptor base containing the signature at base + 0x10."""
    limit = min(len(data), MAX_DESCRIPTOR_SEARCH)
    pos = data.find(DESCRIPTOR_SIGNATURE, 0, limit)
    if pos < 0:
        raise DescriptorError("Flash Descriptor signature not found in first 0x1000 bytes")
    if pos < 0x10:
        raise DescriptorError(f"signature at 0x{pos:x} precedes expected map offset 0x10")
    base = pos - 0x10
    if base + FLMAP2_RELATIVE + 4 > len(data):
        raise DescriptorError("truncated Flash Descriptor map")
    return base


def parse_image(data: bytes, label: str = "image") -> dict[str, Any]:
    descriptor_base = find_descriptor(data)
    flmap2 = struct.unpack_from("<I", data, descriptor_base + FLMAP2_RELATIVE)[0]
    ril = (flmap2 >> 24) & 0xFF
    iccriba = (flmap2 >> 16) & 0xFF
    fmsba = flmap2 & 0xFFFF
    table_offset = descriptor_base + (iccriba << 4)
    table_size = ril * 8
    table_end = table_offset + table_size
    if table_end > len(data):
        raise DescriptorError(
            f"ICC list [0x{table_offset:x},0x{table_end:x}) exceeds image size 0x{len(data):x}"
        )

    entries = []
    for index in range(ril):
        offset = table_offset + index * 8
        selector, value = struct.unpack_from("<II", data, offset)
        entries.append(
            {
                "index": index,
                "spi_offset": offset,
                "selector": selector,
                "value": value,
                "selector_bytes_le": data[offset : offset + 4].hex(" "),
                "candidate_slices": {
                    "byte_31_24": selector >> 24,
                    "byte_23_16": (selector >> 16) & 0xFF,
                    "byte_15_8": (selector >> 8) & 0xFF,
                    "byte_7_0": selector & 0xFF,
                    "low_16": selector & 0xFFFF,
                },
            }
        )

    return {
        "label": label,
        "image_size": len(data),
        "descriptor_base": descriptor_base,
        "signature_offset": descriptor_base + 0x10,
        "flmap2": flmap2,
        "ril": ril,
        "iccriba": iccriba,
        "fmsba": fmsba,
        "icc_table_offset": table_offset,
        "icc_table_end_exclusive": table_end,
        "icc_table_size": table_size,
        "table_erased_when_ril_zero": bool(ril == 0 and data[table_offset : table_offset + 8] == b"\xff" * 8),
        "entries": entries,
    }


def parse_image_arg(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("use LABEL=PATH")
    label, path = value.split("=", 1)
    if not label or not path:
        raise argparse.ArgumentTypeError("use non-empty LABEL=PATH")
    return label, Path(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--image",
        action="append",
        type=parse_image_arg,
        required=True,
        metavar="LABEL=PATH",
        help="SPI image to parse; can be supplied more than once",
    )
    args = parser.parse_args()
    results = []
    for label, path in args.image:
        try:
            results.append(parse_image(path.read_bytes(), label))
        except (OSError, DescriptorError) as error:
            parser.error(f"{path}: {error}")
    print(json.dumps({"images": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
