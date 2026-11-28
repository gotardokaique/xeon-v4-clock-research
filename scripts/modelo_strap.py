#!/usr/bin/env python3
"""Modelo offline da decisão e do operando WRMSR em OcInit FFDC647E.

Não avalia se o caminho de execução é alcançável e não acessa hardware.
"""
import argparse
import json


def decisao(msr, gmes2, mei_presente=True):
    if not isinstance(msr, int) or not 0 <= msr < 1 << 64:
        raise ValueError('MSR deve ser inteiro de 64 bits sem sinal')
    if not isinstance(gmes2, int) or not 0 <= gmes2 < 1 << 32:
        raise ValueError('GMES2 deve ser inteiro de 32 bits sem sinal')
    me = gmes2 & 7
    cpu = msr & 3
    escrever = bool(mei_presente and me != cpu)
    operando = msr | me | 8 if escrever else None
    return {'campo_me': me, 'campo_msr': cpu, 'divergencia': me != cpu,
            'escrita_e_handshake': escrever, 'operando_wrmsr': operando,
            'low2_operando': (operando & 3) if escrever else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--msr', required=True, type=lambda x: int(x, 0))
    parser.add_argument('--gmes2', required=True, type=lambda x: int(x, 0))
    parser.add_argument('--mei-ausente', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(decisao(args.msr, args.gmes2, not args.mei_ausente), indent=2))
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
