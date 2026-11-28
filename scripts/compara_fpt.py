#!/usr/bin/env python3
"""Inventário somente leitura de tabelas FPT legadas em regiões explicitamente fornecidas."""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def inspect(data):
    if len(data) < 0x30 or data[0x10:0x14] != b'$FPT':
        raise ValueError('FPT ausente no offset 0x10 da região')
    count, = struct.unpack_from('<I', data, 0x14)
    version, entry_version, header_len = data[0x18:0x1b]
    if (version, entry_version, header_len) != (0x20, 0x10, 0x30):
        raise ValueError('layout FPT não reconhecido')
    if count > 256 or header_len + count * 32 > len(data):
        raise ValueError('tabela FPT truncada ou contagem excessiva')
    entries = []
    for i in range(count):
        pos = header_len + i * 32
        name, owner, offset, size = struct.unpack_from('<4s4sII', data, pos)
        item = {'name_hex': name.hex(), 'name': name.rstrip(b'\0').decode('ascii', 'replace'), 'owner_hex': owner.hex(), 'offset': offset, 'size': size}
        if offset == 0xffffffff:
            item['status'] = 'offset ausente; não é partição física mapeada'
        elif size == 0 or offset > len(data) or size > len(data) - offset:
            raise ValueError(f'entrada {i} fora da região')
        else:
            block = data[offset:offset+size]
            item.update(status='intervalo presente', sha256=hashlib.sha256(block).hexdigest(), non_ff=len(block)-block.count(255))
        entries.append(item)
    return {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'fpt_offset': 0x10, 'version': version, 'entry_version': entry_version, 'entries': entries}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('regions', nargs='+', type=Path, help='arquivos de regiões ME/SPS, não imagem SPI')
    a=p.parse_args()
    try:
        result=[{'path': str(path), **inspect(path.read_bytes())} for path in a.regions]
    except (OSError, ValueError) as exc:
        p.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
