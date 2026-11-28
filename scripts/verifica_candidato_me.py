#!/usr/bin/env python3
"""Valida, sem produzir imagens, se só a região ME foi substituída."""
import argparse
import hashlib
import hmac
import json
from pathlib import Path
import struct


def digest(data):
    return hashlib.sha256(data).hexdigest()


def validate(original, region, candidate, original_sha, region_sha):
    if not hmac.compare_digest(digest(original), original_sha.lower()):
        raise ValueError('SHA-256 da imagem original não corresponde')
    if not hmac.compare_digest(digest(region), region_sha.lower()):
        raise ValueError('SHA-256 da região fornecida não corresponde')
    if len(original) < 0x1000 or len(candidate) != len(original):
        raise ValueError('tamanho inválido ou divergente')
    signature, flmap0 = struct.unpack_from('<II', original, 0x10)
    if signature != 0x0ff0a55a:
        raise ValueError('assinatura do descriptor inválida')
    frba = ((flmap0 >> 16) & 0xff) << 4
    if frba + 12 > 0x1000:
        raise ValueError('tabela de regiões fora do descriptor')
    bios_reg, flreg = struct.unpack_from('<II', original, frba + 4)
    start = (flreg & 0x7fff) << 12
    end = (((flreg >> 16) & 0x7fff) + 1) << 12
    if start < 0x1000 or end <= start or end > len(original):
        raise ValueError('intervalo ME inválido')
    bios_start = (bios_reg & 0x7fff) << 12
    bios_end = (((bios_reg >> 16) & 0x7fff) + 1) << 12
    if bios_start < 0x1000 or bios_end <= bios_start or bios_end > len(original):
        raise ValueError('intervalo BIOS inválido')
    if start < bios_end and bios_start < end:
        raise ValueError('regiões ME e BIOS sobrepostas')
    if len(region) != end-start:
        raise ValueError('tamanho da região ME incompatível')
    if candidate[:start] != original[:start] or candidate[end:] != original[end:]:
        raise ValueError('diferenças fora da região ME')
    if candidate[start:end] != region:
        raise ValueError('conteúdo ME não coincide integralmente com a região')
    return {'valid': True, 'me_start_spi': start, 'me_end_spi_exclusive': end,
            'original_sha256': digest(original), 'region_sha256': digest(region),
            'candidate_sha256': digest(candidate),
            'warning': 'Validação binária somente; não estabelece compatibilidade ou segurança.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('original', type=Path)
    p.add_argument('region', type=Path)
    p.add_argument('candidate', type=Path)
    p.add_argument('--original-sha256', required=True)
    p.add_argument('--region-sha256', required=True)
    a = p.parse_args()
    try:
        result = validate(a.original.read_bytes(), a.region.read_bytes(), a.candidate.read_bytes(), a.original_sha256, a.region_sha256)
    except (OSError, ValueError) as exc:
        p.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
