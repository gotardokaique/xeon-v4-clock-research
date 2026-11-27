"""Confere a estrutura SCA desta amostra e localiza alvos nas janelas ARC."""
import argparse
import json
from pathlib import Path
import struct

if __package__:
    from .inventario_sps import slice_checked
else:
    from inventario_sps import slice_checked


def inspect_sca(data):
    header = slice_checked(data, 0, 0x40)
    kind, header_words, magic, _, end, count, version = struct.unpack_from("<7I", header)
    if (kind, header_words, magic, version) != (0, 0x10, 0x41435324, 1):
        raise ValueError("cabeçalho SCA desconhecido")
    if end < 0x48 or end % 4:
        raise ValueError("comprimento SCA inválido")
    payload = slice_checked(data, 0, end)
    records = []
    offset = header_words * 4
    while offset < len(payload):
        key, words = struct.unpack("<II", slice_checked(payload, offset, 8))
        if words < 2:
            raise ValueError("comprimento de registro SCA inválido")
        size = words * 4
        slice_checked(payload, offset, size)
        records.append({"offset": offset, "key": key, "size": size})
        offset += size
        if key == 0xFFFFFFFF:
            if size != 8 or offset != end:
                raise ValueError("terminador SCA inválido")
            break
    if not records or records[-1]["key"] != 0xFFFFFFFF or count != len(records) + 1:
        raise ValueError("contagem ou terminador SCA inválidos")
    total = sum(word for (word,) in struct.iter_unpack("<I", payload)) & 0xFFFFFFFF
    return {"length": end, "count_including_header": count,
            "header_dword_3c": struct.unpack_from("<I", header, 0x3C)[0],
            "sum_le32": total, "checksum_matches": total == 0xFFFFFFFF,
            "records": records}


def locate_arc(report, address):
    """Cruza flags do manifesto com a entrada da segunda LLUT."""
    table = report["tables"][1]
    base = table["addrbase_field"] + 0x10000000
    index = (address - base) // table["page_size"]
    page = table["pages"][index] if 0 <= index < len(table["pages"]) else None
    modules = report["modules"]
    for module in modules:
        if module["start"] <= address < module["end"]:
            flags = module["flags"]
            rapi_end = module["start"] + ((flags >> 17) & 7) * 0x1000
            kapi_end = rapi_end + ((flags >> 20) & 3) * 0x1000
            window = "RAPI" if address < rapi_end else "KAPI" if address < kapi_end else "module"
            return {"address": address, "module": module["name"], "window": window, "page": page}
    for module in modules:
        memory_size = module.get("field_44", 0)
        if module["end"] <= address < module["start"] + memory_size:
            return {"address": address, "module": module["name"],
                    "window": "runtime_data", "page": page}
    return {"address": address, "module": None, "window": None, "page": page}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--sca", type=Path, required=True)
    cli.add_argument("--opr1-map", type=Path, required=True)
    cli.add_argument("address", type=lambda value: int(value, 0), nargs="+")
    args = cli.parse_args()
    report = json.loads(args.opr1_map.read_text())
    print(json.dumps({"sca": inspect_sca(args.sca.read_bytes()),
                      "arc": [locate_arc(report, address) for address in args.address]}, indent=2))


if __name__ == "__main__":
    main()
