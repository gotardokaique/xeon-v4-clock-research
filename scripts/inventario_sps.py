"""Extrai volumes de uma imagem SPI Grantley e inventaria seus blocos."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct


def slice_checked(data, offset, size):
    if offset < 0 or size <= 0 or offset + size > len(data):
        raise ValueError(f"intervalo fora da imagem: {offset:#x}+{size:#x}")
    return data[offset:offset + size]


def regions(rom):
    descriptor = slice_checked(rom, 0, 0x1000)
    signature, flmap0 = struct.unpack_from("<II", descriptor, 0x10)
    if signature != 0x0FF0A55A:
        raise ValueError("assinatura do descriptor inválida")
    frba = ((flmap0 >> 16) & 0xFF) << 4
    flreg2, = struct.unpack("<I", slice_checked(descriptor, frba + 8, 4))
    base = (flreg2 & 0x7FFF) << 12
    end = (((flreg2 >> 16) & 0x7FFF) + 1) << 12
    if base < len(descriptor):
        raise ValueError("SPS sobrepõe o descriptor")
    sps = slice_checked(rom, base, end - base)
    tag, count, version, _, header_length = struct.unpack("<4sIBBB", slice_checked(sps, 0x10, 11))
    if (tag, version, header_length) != (b"$FPT", 0x20, 0x30):
        raise ValueError("layout FPT diferente da variante Grantley esperada")
    entries = slice_checked(sps, header_length, count * 0x20)
    found = {"descriptor": (0, None, descriptor)}
    intervals = [(0, header_length + len(entries))]
    for index in range(count):
        name, _, offset, size = struct.unpack_from("<4s4sII", entries, index * 0x20)
        data = slice_checked(sps, offset, size)
        if any(offset < stop and offset + size > start for start, stop in intervals):
            raise ValueError("intervalos FPT sobrepostos")
        intervals.append((offset, offset + size))
        if name in (b"MFSB", b"SCA\0", b"MFS\0"):
            label = name.rstrip(b"\0").decode("ascii")
            if label in found:
                raise ValueError(f"entrada FPT duplicada: {label}")
            found[label] = (base + offset, offset, data)
    if len(found) != 4:
        raise ValueError("faltam volumes SPS esperados")
    return found


def describe(data):
    blocks = [data[offset:offset + 0x1000] for offset in range(0, len(data), 0x1000)]
    return {
        "size": len(data),
        "sha256": sha256(data).hexdigest(),
        "blocks_4k": [
            {"offset": i * 0x1000, "non_ff": len(block) - block.count(0xFF)}
            for i, block in enumerate(blocks)
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sha256", required=True, help="SHA-256 esperado do dump")
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    digest = sha256(rom).hexdigest()
    if digest != args.sha256.lower():
        parser.error("SHA-256 do dump diverge do esperado")
    try:
        selected = regions(rom)
    except ValueError as error:
        parser.error(str(error))
    args.output.mkdir(mode=0o700)
    manifest = {"source_sha256": digest, "source_size": len(rom), "regions": {}}
    for name, (spi, sps, data) in selected.items():
        (args.output / f"{name}.bin").write_bytes(data)
        manifest["regions"][name] = {"spi_offset": spi, "sps_offset": sps, **describe(data)}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
