"""Cruza registros MFS/SCA, acessos ARC e referências KAPI desta amostra Grantley."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import struct

if __package__:
    from .auditoria_sps import inspect_sca, locate_arc
    from .inventario_sps import slice_checked
else:
    from auditoria_sps import inspect_sca, locate_arc
    from inventario_sps import slice_checked

DIRECTORY_START = 0x14
DIRECTORY_END = 0x55d
DIRECTORY_ENTRY = struct.Struct("<HIHBBB")
PCO_KEY = 0x0a4f4350
PCO_SPANS = ((0x4635, 0x46ff), (0x4704, 0x5000), (0x5002, 0x5060))
TEMPLATES = (0x20041000, 0x20044000)
ARC_LINE = re.compile(r"^([0-9a-f]+):\t[^\t]*\t([a-z0-9_.]+)\t?([^;\t]*)(?:[^;]*;([0-9a-f]{8}))?")
PAYLOAD_LOAD = re.compile(r"r\d+,\[(r1|r20)(?:,(-?(?:0x[0-9a-f]+|\d+)))?\]$")


def directory(data):
    table = slice_checked(data, DIRECTORY_START, DIRECTORY_END - DIRECTORY_START)
    entries = []
    for index, (tag, key, size, flag, group, slot) in enumerate(DIRECTORY_ENTRY.iter_unpack(table)):
        if tag != 0xf0dc or flag != 1 or size == 0:
            raise ValueError(f"entrada MFS inválida no índice {index}")
        entries.append({"index": index, "offset": DIRECTORY_START + index * DIRECTORY_ENTRY.size,
                        "tag": tag, "key": key, "size": size, "flag": flag,
                        "group": group, "slot": slot})
    if len({row["key"] for row in entries}) != len(entries):
        raise ValueError("chave MFS duplicada")
    if len({(row["group"], row["slot"]) for row in entries}) != len(entries):
        raise ValueError("par grupo/slot MFS duplicado")
    return entries


def cross_volume(mfs, mfsb, sca):
    entries = directory(mfs)
    records = {record["key"]: record for record in inspect_sca(sca)["records"]}
    matches = []
    for entry in entries:
        record = records.get(entry["key"])
        if record and entry["size"] == record["size"] - 8:
            start = record["offset"] + 8
            payload = slice_checked(sca, start, entry["size"])
            match = {"index": entry["index"], "key": entry["key"], "sca_payload": start,
                     "contiguous_occurrences": mfs.count(payload)}
            if entry["key"] == PCO_KEY:
                chunks = [slice_checked(mfs, first, end - first) for first, end in PCO_SPANS]
                match.update(mfs_spans=PCO_SPANS, reconstructed=b"".join(chunks) == payload)
            elif match["contiguous_occurrences"] == 1:
                match["mfs_offset"] = mfs.find(payload)
            matches.append(match)
    marker = slice_checked(mfsb, DIRECTORY_END, 8)
    return {"entries": entries, "directory_copy_matches": entries == directory(mfsb),
            "mfsb_boundary": marker.hex(), "groups": dict(Counter(e["group"] for e in entries)),
            "total_size": sum(e["size"] for e in entries), "sca_matches": matches}


def arc_instructions(disassembly):
    for line in disassembly.splitlines():
        match = ARC_LINE.match(line)
        if match:
            address, mnemonic, operands, target = match.groups()
            yield int(address, 16), mnemonic, operands.strip(), int(target, 16) if target else None


def sca_payload_accesses(instructions):
    """Mapeia o braço selecionado pelo ID 0x0a4f4350 até a junção do validador."""
    bases = {"r20": 0}
    accesses = []
    comparisons = []
    for address, mnemonic, operands, _ in instructions:
        if not 0x20053b38 <= address <= 0x2005545a:
            continue
        if (mnemonic, operands) == ("mov_s", "r1,r20"):
            bases["r1"] = bases["r20"]
        elif mnemonic == "add" and operands.startswith("r1,r1,"):
            bases["r1"] += int(operands.split(",")[-1], 0)
        elif mnemonic in ("ld", "ld_s", "ld.as") and (match := PAYLOAD_LOAD.fullmatch(operands)):
            register, displacement = match.groups()
            offset = bases[register] + int(displacement or "0", 0) * (4 if mnemonic == "ld.as" else 1)
            if offset % 4 or not 0 <= offset <= 0xa20:
                raise ValueError(f"leitura fora do payload PCO em {address:#x}")
            accesses.append({"address": address, "offset": offset, "width": 4,
                             "consumer": 0x20053b2a, "operation": "unsigned_compare_all_ones"})
        elif mnemonic == "cmp_s" and operands.endswith(",r4"):
            comparisons.append(address)
    if [entry["offset"] for entry in accesses] != list(range(0, 0xa24, 4)):
        raise ValueError("braço PCO incompleto ou desassemblagem divergente")
    next_loads = [entry["address"] for entry in accesses[1:]] + [0x2005545c]
    if len(comparisons) != len(accesses) or not all(
        entry["address"] < comparison < next_load
        for entry, comparison, next_load in zip(accesses, comparisons, next_loads)
    ):
        raise ValueError("comparações do braço PCO incompletas ou divergentes")
    for entry, comparison in zip(accesses, comparisons):
        entry["comparison"] = comparison
    return accesses


def kapi_references(kernel, instructions, opr1, addresses):
    branches = {vma: (mnemonic, target) for vma, mnemonic, _, target in instructions}
    refs = []
    for address in addresses:
        location = locate_arc(opr1, address)
        offset = address & 0xfff
        matches = []
        if location["window"] == "KAPI" and offset >= 0x18 and (offset - 0x18) % 12 == 0:
            for base in TEMPLATES:
                header = slice_checked(kernel, base - TEMPLATES[0], 12)
                signature, declared_base, limit = struct.unpack("<4sII", header)
                vma = base + offset
                if signature != b"KAPI" or declared_base != base:
                    raise ValueError(f"cabeçalho KAPI divergente em {base:#x}")
                if vma + 12 > limit:
                    continue
                stub = slice_checked(kernel, vma - TEMPLATES[0], 12)
                mnemonic, target = branches.get(vma + 8, (None, None))
                if stub[:4] != b"\x0a\x20\x80\x1f" or mnemonic != "b" or target != base + 0x10:
                    continue
                high, low = struct.unpack("<HH", stub[4:8])
                matches.append({"template": base, "stub": vma, "selector": (high << 16) | low,
                                "dispatcher": target})
        refs.append({"location": location, "page_offset": offset,
                     "slot_candidate": (offset - 0x18) // 12 if matches else None,
                     "template_matches": matches})
    return refs


def interface_slots(data, base, pair, service_id, slots):
    """Valida um par de exportação observado e segue os slots no mesmo módulo."""
    key, table = struct.unpack("<II", slice_checked(data, pair - base, 8))
    if key != service_id or table % 4:
        raise ValueError(f"par de interface divergente em {pair:#x}")
    targets = {}
    for slot in slots:
        target, = struct.unpack("<I", slice_checked(data, table + slot - base, 4))
        slice_checked(data, target - base, 2)
        if target % 2:
            raise ValueError(f"alvo ARC desalinhado em {table + slot:#x}")
        targets[hex(slot)] = target
    return {"id": key, "export_pair": pair, "table": table, "slots": targets}


def matching_window(reference, reference_offset, target, target_offset):
    """Retorna o intervalo idêntico contínuo em torno de uma âncora já localizada."""
    slice_checked(reference, reference_offset, 1)
    slice_checked(target, target_offset, 1)
    left = 0
    while left < min(reference_offset, target_offset):
        if reference[reference_offset - left - 1] != target[target_offset - left - 1]:
            break
        left += 1
    right = 0
    while reference_offset + right < len(reference) and target_offset + right < len(target):
        if reference[reference_offset + right] != target[target_offset + right]:
            break
        right += 1
    return {"offset_before_anchor": left, "offset_from_anchor": right, "length": left + right}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("mfs", "mfsb", "sca", "kernel", "kernel-asm", "policy", "opr1-map", "iccmod",
                 "bup-recovery", "bup-operational"):
        cli.add_argument(f"--{name}", type=Path, required=True)
    args = cli.parse_args()
    instructions = list(arc_instructions(args.kernel_asm.read_text()))
    opl = json.loads(args.opr1_map.read_text())
    kernel = args.kernel.read_bytes()
    policy = args.policy.read_bytes()
    iccmod = args.iccmod.read_bytes()
    common = [{"name": name, "iccm_anchor": 0x964, "bup_anchor": offset,
               **matching_window(iccmod, 0x964, path.read_bytes(), offset)}
              for name, path, offset in (("201f8000", args.bup_recovery, 0xc212),
                                         ("20300000", args.bup_operational, 0x12c4a))]
    print(json.dumps({
        "mfs": cross_volume(args.mfs.read_bytes(), args.mfsb.read_bytes(), args.sca.read_bytes()),
        "sca_accesses": sca_payload_accesses(instructions),
        "kapi": kapi_references(kernel, instructions, opl,
                                (0x200eeab0, 0x200eeabc, 0x200eeac8, 0x2009e018, 0x200ee018,
                                 0x200edcdc)),
        "service_exports": [
            interface_slots(policy, 0x2009f000, 0x200ca014, 0x102f, (4, 0x24)),
            interface_slots(policy, 0x2009f000, 0x200ca088, 0x1033, (0x10,)),
            interface_slots(kernel, TEMPLATES[0], 0x200659c4, 0x1057, (8, 0xc)),
        ],
        "icc_bup": common,
    }, indent=2))


if __name__ == "__main__":
    main()
