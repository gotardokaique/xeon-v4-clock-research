#!/usr/bin/env python3
"""Compare imagens PE32 após normalizar apenas ImageBase e relocations HIGHLOW."""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def u16(data, off):
    if off < 0 or off + 2 > len(data):
        raise ValueError('leitura PE fora do arquivo')
    return struct.unpack_from('<H', data, off)[0]


def u32(data, off):
    if off < 0 or off + 4 > len(data):
        raise ValueError('leitura PE fora do arquivo')
    return struct.unpack_from('<I', data, off)[0]


def normalize(data):
    d = bytearray(data)
    if d[:2] != b'MZ':
        raise ValueError('MZ ausente')
    nt = u32(d, 0x3c)
    if d[nt:nt+4] != b'PE\0\0':
        raise ValueError('PE ausente')
    count = u16(d, nt+6)
    optional_size = u16(d, nt+20)
    opt = nt+24
    if u16(d, opt) != 0x10b or optional_size < 144 or count > 96 or opt + optional_size + count*40 > len(d):
        raise ValueError('PE32 ou cabeçalho inválido')
    if u32(d, opt+92) < 6:
        raise ValueError('diretório de relocation ausente')
    image_base = u32(d, opt+28)
    reloc_rva, reloc_size = u32(d, opt+136), u32(d, opt+140)
    if not reloc_rva or not reloc_size:
        raise ValueError('sem relocations')
    sections = []
    for i in range(count):
        off = opt + optional_size + i*40
        va, size, raw = u32(d, off+12), u32(d, off+16), u32(d, off+20)
        if raw > len(d) or size > len(d)-raw:
            raise ValueError('seção fora do arquivo')
        sections.append((va, size, raw))

    def offset(rva, size):
        hits = [raw + rva - va for va, length, raw in sections if rva >= va and rva - va <= length and size <= length - (rva - va)]
        if len(hits) != 1:
            raise ValueError('RVA não mapeado ou ambíguo')
        return hits[0]

    begin = offset(reloc_rva, reloc_size)
    end = begin + reloc_size
    cursor = begin
    sites = []
    while cursor < end:
        if end - cursor < 8:
            raise ValueError('bloco relocation truncado')
        page, length = u32(d, cursor), u32(d, cursor+4)
        if length < 8 or length % 2 or length > end-cursor:
            raise ValueError('tamanho de relocation inválido')
        for pos in range(cursor+8, cursor+length, 2):
            entry = u16(d, pos)
            typ, rel = entry >> 12, entry & 0xfff
            if typ == 0:
                continue
            if typ != 3:
                raise ValueError('tipo relocation diferente de HIGHLOW')
            site = offset(page + rel, 4)
            if site < end and site+4 > begin:
                raise ValueError('relocation sobrepõe tabela')
            if any(site < prior+4 and site+4 > prior for prior in sites):
                raise ValueError('relocations sobrepostas')
            sites.append(site)
        cursor += length
    if not sites:
        raise ValueError('nenhuma relocation HIGHLOW')
    for site in sites:
        struct.pack_into('<I', d, site, (u32(d, site)-image_base) & 0xffffffff)
    struct.pack_into('<I', d, opt+28, 0)
    return bytes(d), {'image_base': image_base, 'relocations': len(sites), 'relocation_file_offsets': sites}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('images', nargs=2, type=Path)
    a = p.parse_args()
    try:
        pairs = [normalize(path.read_bytes()) for path in a.images]
    except (ValueError, OSError) as e:
        p.error(str(e))
    result = []
    for path, (normalized, meta) in zip(a.images, pairs):
        result.append({'path': str(path), 'normalized_sha256': hashlib.sha256(normalized).hexdigest(), **meta})
    print(json.dumps({'equal_normalized': pairs[0][0] == pairs[1][0], 'images': result}, indent=2))

if __name__ == '__main__':
    main()
