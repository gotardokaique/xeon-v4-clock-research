"""Inventários offline dos marcadores MFSB e das tabelas LLUT de OPR1."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct

if __package__:
    from .inventario_sps import slice_checked
else:
    from inventario_sps import slice_checked

MARKER = bytes.fromhex("01030204")


def volume_map(backup, active, payload_end):
    """Compara a expansão de um prefixo explicitamente delimitado com o MFS."""
    payload = slice_checked(backup, 0, payload_end)
    result = bytearray()
    intervals = []
    differences = []
    start = 0
    while start < len(payload):
        index = payload.find(MARKER, start)
        end = len(payload) if index < 0 else index
        destination = len(result)
        if end > start:
            literal = payload[start:end]
            observed = slice_checked(active, destination, len(literal))
            for i, (before, after) in enumerate(zip(literal, observed)):
                if before != after:
                    differences.append({"mfsb": start + i, "mfs": destination + i,
                                        "expected": before, "actual": after})
            intervals.append({"kind": "literal", "mfsb": start, "mfs": destination,
                              "delta": destination - start, "length": end - start})
            result.extend(literal)
        if index < 0:
            break
        length = int.from_bytes(slice_checked(payload, index + 4, 4), "big")
        destination = len(result)
        padding = slice_checked(active, destination, length)
        if padding != b"\xff" * length:
            raise ValueError(f"lacuna MFS divergente em {destination:#x}")
        intervals.append({"kind": "padding", "mfsb": index, "mfs": destination,
                          "delta": destination - index, "encoded_length": 8,
                          "length": length})
        result.extend(padding)
        start = index + 8

    tail = active[len(result):]
    if tail != b"\xff" * len(tail):
        raise ValueError("cauda MFS contém dados fora da reconstrução")
    if tail:
        intervals.append({"kind": "erased_tail", "mfs": len(result), "length": len(tail)})
        result.extend(tail)
    return {
        "inputs": {"mfsb_sha256": sha256(backup).hexdigest(), "mfs_sha256": sha256(active).hexdigest()},
        "payload_end": payload_end,
        "backup_tail": {"start": payload_end, "size": len(backup) - payload_end,
                        "non_ff_offsets": [i for i in range(payload_end, len(backup)) if backup[i] != 255]},
        "expanded_sha256": sha256(result).hexdigest(),
        "differences": differences,
        "intervals": intervals,
        "mfs_page_candidates": [
            {"mfs": i, "header8": active[i:i + 8].hex(),
             "non_ff": 0x4000 - active[i:i + 0x4000].count(255)}
            for i in range(0, len(active) - 0x3fff, 0x4000)
        ],
    }


def opr1_map(sps):
    header = slice_checked(sps, 0x10, 0x20)
    tag, count = struct.unpack_from("<4sI", header)
    if tag != b"$FPT" or header[8:11] != bytes((0x20, 0x10, 0x30)):
        raise ValueError("FPT diferente da variante Grantley esperada")
    entries = slice_checked(sps, 0x30, count * 0x20)
    partitions = [
        (offset, size) for name, offset, size in struct.iter_unpack("<4s4xII16x", entries)
        if name == b"OPR1"
    ]
    if len(partitions) != 1:
        raise ValueError("esperava uma partição OPR1")
    base, part_size = partitions[0]
    partition = slice_checked(sps, base, part_size)
    if slice_checked(partition, 0x1c, 4) != b"$MN2":
        raise ValueError("manifesto $MN2 ausente")
    manifest_size = struct.unpack_from("<I", partition, 4)[0] * 4
    module_count = struct.unpack_from("<I", partition, 0x20)[0]
    descriptors = slice_checked(partition, manifest_size + 12, module_count * 0x60)
    modules = []
    for i in range(module_count):
        descriptor = descriptors[i * 0x60:(i + 1) * 0x60]
        if descriptor[:4] != b"$MME":
            raise ValueError("descritor $MME inválido")
        name = descriptor[4:20].split(b"\0")[0].decode("ascii")
        address, offset, size, stored, field44, field48, entry, flags = struct.unpack_from(
            "<8I", descriptor, 0x34)
        modules.append({"name": name, "start": address, "end": address + size,
                        "entry_field": entry, "opr1_offset": offset, "stored_size": stored,
                        "field_44": field44, "field_48": field48, "flags": flags,
                        "sha256_field_raw": descriptor[0x14:0x34].hex(),
                        "sha256_digest": descriptor[0x14:0x34][::-1].hex()})
    table_offset = next(m["opr1_offset"] for m in modules if (m["flags"] >> 4) & 7 == 1)
    tables = []
    for _ in range(2):
        header = slice_checked(partition, table_offset, 0x40)
        magic, count, address, spi_field, compressed_size, stored_base = struct.unpack_from("<6I", header)
        if magic != 0x54554C4C:
            raise ValueError("LLUT inválida")
        page_size = struct.unpack_from("<I", header, 0x30)[0]
        if page_size != 0x400:
            raise ValueError("granularidade inesperada")
        raw = slice_checked(partition, table_offset + 0x40, count * 4)
        payload_offset = table_offset + 0x40 + len(raw)
        table = {"opr1_offset": table_offset, "page_size": page_size,
                 "addrbase_field": address, "spibase_field": spi_field,
                 "huffstart_field": stored_base, "hufflen_field": compressed_size, "pages": []}
        for index, (word,) in enumerate(struct.iter_unpack("<I", raw)):
            vma = address + 0x10000000 + index * page_size
            flags = word >> 25
            owners = [m["name"] for m in modules if m["start"] <= vma < m["end"]]
            page = {"index": index, "vma": vma, "flags": flags, "word": word, "owners": owners}
            if flags != 0x40:
                page["stored_address"] = word & 0x1ffffff
                if tables:
                    relative = payload_offset + page["stored_address"] - stored_base
                    slice_checked(partition, relative, 1)
                    page["stream_opr1_offset"] = relative
                    page["stream_sps_offset"] = base + relative
            table["pages"].append(page)
        if tables:
            stream = slice_checked(partition, payload_offset, compressed_size)
            table["stream"] = {"opr1_offset": payload_offset, "size": len(stream)}
        tables.append(table)
        table_offset = payload_offset
    mapped = tables[-1]
    for module in modules:
        if module["stored_size"]:
            size = module["stored_size"]
            slice_checked(partition, module["opr1_offset"], size)
            module["segment_raw"] = {"opr1_offset": module["opr1_offset"], "size": size}
            continue
        segments = []
        for page in mapped["pages"]:
            if module["name"] not in page["owners"]:
                continue
            state = "empty" if page["flags"] == 0x40 else "mapped"
            if segments and segments[-1]["state"] == state:
                segments[-1]["end"] = page["vma"] + mapped["page_size"]
            else:
                segments.append({"state": state, "start": page["vma"],
                                 "end": page["vma"] + mapped["page_size"]})
        module["llut_segments"] = segments
    return {"sps_sha256": sha256(sps).hexdigest(), "opr1_sps_offset": base,
            "opr1_size": part_size, "modules": modules, "tables": tables}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    volumes = commands.add_parser("volumes")
    volumes.add_argument("backup", type=Path)
    volumes.add_argument("active", type=Path)
    volumes.add_argument("--payload-end", type=lambda value: int(value, 0), required=True)
    opr1 = commands.add_parser("opr1")
    opr1.add_argument("sps", type=Path)
    args = cli.parse_args()
    if args.command == "volumes":
        report = volume_map(args.backup.read_bytes(), args.active.read_bytes(), args.payload_end)
    else:
        report = opr1_map(args.sps.read_bytes())
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
